"""
Agente Negociador Autónomo.

═══════════════════════════════════════════════════════════════════════════════
FUNCIONAMIENTO:
═══════════════════════════════════════════════════════════════════════════════

El agente ejecuta un LOOP AUTÓNOMO hasta completar el objetivo:

    ┌─────────────────────────────────────────────────────────────┐
    │                    LOOP PRINCIPAL                           │
    │                                                             │
    │  1. VER ESTADO → ¿Qué necesito? ¿Qué me sobra?             │
    │                                                             │
    │  2. REVISAR BUZÓN → Analizar ofertas recibidas              │
    │     • ¿Es buena oferta? → Aceptar + enviar paquete         │
    │     • ¿Es intento de robo? → Ignorar + lista negra         │
    │                                                             │
    │  3. ENVIAR PROPUESTAS → Contactar jugadores                 │
    │     • Proponer intercambios justos                          │
    │     • Ofrecer excedentes por lo que necesitamos            │
    │                                                             │
    │  4. ESPERAR → Dar tiempo a respuestas                       │
    │                                                             │
    │  5. ¿OBJETIVO COMPLETADO?                                   │
    │     • NO → Volver a paso 1                                  │
    │     • SÍ → Cambiar a MODO MAXIMIZAR ORO                    │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘

MODO DEBUG:
- Muestra cada decisión del agente
- Log de cartas enviadas/recibidas
- Análisis de cada oferta
- Intercambios ejecutados

═══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from config import (
    RECURSOS_CONOCIDOS, PALABRAS_SOSPECHOSAS,
    PALABRAS_ACEPTACION, PALABRAS_RECHAZO, MODELO_DEFAULT
)
from api_client import APIClient
from ollama_client import OllamaClient


class ModoAgente(Enum):
    """Estados del agente."""
    CONSEGUIR_OBJETIVO = "conseguir_objetivo"
    MAXIMIZAR_ORO = "maximizar_oro"
    COMPLETADO = "completado"


@dataclass
class LogEntry:
    """Entrada de log para debug."""
    timestamp: float
    tipo: str  # ENVIO, RECEPCION, ANALISIS, DECISION, INTERCAMBIO
    mensaje: str
    detalles: Optional[Dict] = None


class AgenteNegociador:
    """
    Agente autónomo que negocia para conseguir recursos.
    
    Uso:
        agente = AgenteNegociador("MiAlias", debug=True)
        agente.ejecutar()  # Corre hasta completar objetivo
    """
    
    def __init__(self, alias: str, modelo: str = MODELO_DEFAULT, debug: bool = False):
        self.alias = alias
        self.api = APIClient()
        self.ia = OllamaClient(modelo)
        self.debug = debug
        
        # Estado
        self.modo = ModoAgente.CONSEGUIR_OBJETIVO
        self.info_actual: Optional[Dict] = None
        self.gente: List[str] = []
        
        # Seguridad y tracking
        self.lista_negra: List[str] = []
        self.contactados_esta_ronda: List[str] = []
        self.acuerdos_pendientes: Dict[str, Dict] = {}  # persona -> términos acordados
        self.intercambios_realizados: List[Dict] = []
        
        # Log para debug
        self.log: List[LogEntry] = []
        
        # Configuración
        self.pausa_entre_acciones = 1  # segundos
        self.pausa_entre_rondas = 30   # segundos para esperar respuestas
        self.max_rondas = 10
    
    # =========================================================================
    # LOGGING / DEBUG
    # =========================================================================
    
    def _log(self, tipo: str, mensaje: str, detalles: Dict = None):
        """Registra una acción en el log."""
        entry = LogEntry(
            timestamp=time.time(),
            tipo=tipo,
            mensaje=mensaje,
            detalles=detalles
        )
        self.log.append(entry)
        
        if self.debug:
            icono = {
                "ENVIO": "📤",
                "RECEPCION": "📥",
                "ANALISIS": "🔍",
                "DECISION": "🧠",
                "INTERCAMBIO": "🔄",
                "ALERTA": "⚠️",
                "EXITO": "✅",
                "ERROR": "❌",
                "INFO": "ℹ️"
            }.get(tipo, "•")
            
            print(f"  {icono} [{tipo}] {mensaje}")
            if detalles and self.debug:
                for k, v in detalles.items():
                    print(f"      {k}: {v}")
    
    # =========================================================================
    # CONSULTAS DE ESTADO
    # =========================================================================
    
    def _actualizar_estado(self) -> Dict:
        """Obtiene y procesa el estado actual."""
        self.info_actual = self.api.get_info()
        self.gente = self.api.get_gente()
        
        if not self.info_actual:
            return {}
        
        recursos = self.info_actual.get('Recursos', {})
        objetivo = self.info_actual.get('Objetivo', {})
        
        # Calcular necesidades (lo que falta)
        necesidades = {}
        for rec, cant_obj in objetivo.items():
            actual = recursos.get(rec, 0)
            if actual < cant_obj:
                necesidades[rec] = cant_obj - actual
        
        # Calcular excedentes (lo que sobra)
        excedentes = {}
        for rec, actual in recursos.items():
            if rec == 'oro':
                continue  # El oro no se considera excedente
            obj = objetivo.get(rec, 0)
            if actual > obj:
                excedentes[rec] = actual - obj
        
        return {
            "recursos": recursos,
            "oro": recursos.get('oro', 0),
            "objetivo": objetivo,
            "necesidades": necesidades,
            "excedentes": excedentes,
            "objetivo_completado": len(necesidades) == 0
        }
    
    def _obtener_jugadores_disponibles(self) -> List[str]:
        """Devuelve jugadores que podemos contactar."""
        alias_propios_raw = self.info_actual.get('Alias', []) if self.info_actual else []
        
        # La API puede devolver un string o una lista — normalizar a lista
        if isinstance(alias_propios_raw, str):
            alias_propios = [alias_propios_raw]
        else:
            alias_propios = alias_propios_raw
        
        disponibles = [
            p for p in self.gente
            if p != self.alias 
            and p not in alias_propios
            and p not in self.lista_negra
        ]
        
        if not disponibles:
            self._log("INFO", f"No hay jugadores disponibles (gente={self.gente}, mis_alias={alias_propios}, lista_negra={self.lista_negra})")
        
        return disponibles
    
    # =========================================================================
    # ANÁLISIS DE MENSAJES
    # =========================================================================
    
    def _es_intento_robo(self, mensaje: str, remitente: str) -> bool:
        """Detecta si un mensaje es sospechoso."""
        mensaje_lower = mensaje.lower()
        
        alertas = [p for p in PALABRAS_SOSPECHOSAS if p in mensaje_lower]
        
        if len(alertas) >= 2:
            self._log("ALERTA", f"Posible robo de {remitente}", {"alertas": alertas})
            if remitente not in self.lista_negra:
                self.lista_negra.append(remitente)
            return True
        
        return False
    
    def _es_aceptacion(self, mensaje: str) -> bool:
        """Detecta si un mensaje acepta un intercambio."""
        mensaje_lower = mensaje.lower()
        
        # Verificar rechazo primero
        if any(p in mensaje_lower for p in PALABRAS_RECHAZO):
            return False
        
        # Verificar aceptación
        return any(p in mensaje_lower for p in PALABRAS_ACEPTACION)
    
    def _extraer_recursos_mensaje(self, mensaje: str) -> Dict[str, int]:
        """Extrae recursos y cantidades mencionados en un mensaje."""
        recursos = {}
        mensaje_lower = mensaje.lower()
        
        # Patrón: "100 oro", "50 de madera", etc.
        patron = r'(\d+)\s*(?:de\s+)?(' + '|'.join(RECURSOS_CONOCIDOS) + r')'
        for cantidad, recurso in re.findall(patron, mensaje_lower):
            recursos[recurso] = int(cantidad)
        
        return recursos
    
    def _analizar_oferta_con_ia(self, remitente: str, mensaje: str, 
                                 necesidades: Dict, excedentes: Dict) -> Dict:
        """Usa IA para analizar una oferta compleja."""
        prompt = f"""Analiza esta oferta de negociación.

OFERTA DE: {remitente}
MENSAJE: {mensaje}

MIS NECESIDADES (lo que me falta): {json.dumps(necesidades)}
MIS EXCEDENTES (lo que me sobra): {json.dumps(excedentes)}

Responde SOLO en este formato JSON:
{{"aceptar": true/false, "razon": "explicación breve", "recursos_pedir": {{}}, "recursos_dar": {{}}}}"""
        
        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
        
        try:
            # Intentar parsear JSON de la respuesta
            json_match = re.search(r'\{.*\}', respuesta, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback: decisión simple basada en palabras clave
        recursos_mencionados = self._extraer_recursos_mensaje(mensaje)
        nos_conviene = any(r in necesidades for r in recursos_mencionados)
        
        return {
            "aceptar": nos_conviene,
            "razon": "Contiene recursos que necesitamos" if nos_conviene else "No relevante",
            "recursos_pedir": {},
            "recursos_dar": {}
        }
    
    # =========================================================================
    # GENERACIÓN DE PROPUESTAS
    # =========================================================================
    
    def _generar_propuesta(self, destinatario: str, necesidades: Dict, 
                           excedentes: Dict, oro: int) -> Dict[str, str]:
        """Genera una propuesta de negociación."""
        
        # Si tenemos excedentes, ofrecer intercambio
        if excedentes and necesidades:
            recurso_necesito = list(necesidades.keys())[0]
            cantidad_necesito = necesidades[recurso_necesito]
            recurso_ofrezco = list(excedentes.keys())[0]
            cantidad_ofrezco = min(excedentes[recurso_ofrezco], cantidad_necesito)
            
            return {
                "asunto": f"Intercambio: mi {recurso_ofrezco} por tu {recurso_necesito}",
                "cuerpo": f"Hola {destinatario}! Tengo {cantidad_ofrezco} {recurso_ofrezco} de sobra. "
                         f"¿Tienes {cantidad_necesito} {recurso_necesito}? Podemos hacer un intercambio justo. Saludos!"
            }
        
        # Si solo necesitamos, ofrecer oro
        elif necesidades and oro > 0:
            recurso_necesito = list(necesidades.keys())[0]
            cantidad_necesito = necesidades[recurso_necesito]
            
            return {
                "asunto": f"Compro {recurso_necesito}",
                "cuerpo": f"Hola {destinatario}! Necesito {cantidad_necesito} {recurso_necesito}. "
                         f"Puedo pagar en oro. ¿Cuánto pides? Saludos!"
            }
        
        # Si solo tenemos excedentes (modo maximizar oro)
        elif excedentes:
            recurso_vendo = list(excedentes.keys())[0]
            cantidad_vendo = excedentes[recurso_vendo]
            
            return {
                "asunto": f"Vendo {recurso_vendo}",
                "cuerpo": f"Hola {destinatario}! Tengo {cantidad_vendo} {recurso_vendo} disponible. "
                         f"¿Te interesa? Acepto oro. Saludos!"
            }
        
        # Fallback
        return {
            "asunto": "Propuesta de colaboración",
            "cuerpo": f"Hola {destinatario}! ¿Qué recursos tienes disponibles? Podemos negociar. Saludos!"
        }
    
    # =========================================================================
    # ACCIONES
    # =========================================================================
    
    def _enviar_carta(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        """Envía una carta de negociación."""
        exito = self.api.enviar_carta(self.alias, destinatario, asunto, cuerpo)
        
        self._log("ENVIO", f"Carta a {destinatario}", {
            "asunto": asunto,
            "cuerpo": cuerpo[:100] + "..." if len(cuerpo) > 100 else cuerpo,
            "exito": exito
        })
        
        return exito
    
    def _enviar_paquete(self, destinatario: str, recursos: Dict[str, int]) -> bool:
        """Envía un paquete de recursos."""
        # Verificar que tenemos los recursos
        mis_recursos = self.info_actual.get('Recursos', {}) if self.info_actual else {}
        
        for rec, cant in recursos.items():
            if mis_recursos.get(rec, 0) < cant:
                self._log("ERROR", f"No hay suficiente {rec}", {
                    "necesario": cant,
                    "disponible": mis_recursos.get(rec, 0)
                })
                return False
        
        exito = self.api.enviar_paquete(destinatario, recursos)
        
        self._log("INTERCAMBIO", f"Paquete a {destinatario}", {
            "recursos": recursos,
            "exito": exito
        })
        
        if exito:
            self.intercambios_realizados.append({
                "tipo": "enviado",
                "destinatario": destinatario,
                "recursos": recursos,
                "timestamp": time.time()
            })
        
        return exito
    
    def _responder_aceptacion(self, remitente: str, mensaje_original: str) -> bool:
        """Responde a una aceptación enviando los recursos acordados."""
        
        # Buscar si tenemos un acuerdo pendiente con esta persona
        if remitente in self.acuerdos_pendientes:
            acuerdo = self.acuerdos_pendientes[remitente]
            recursos_a_enviar = acuerdo.get('recursos_dar', {})
            
            if recursos_a_enviar:
                self._log("DECISION", f"Ejecutando acuerdo con {remitente}", {
                    "recursos": recursos_a_enviar
                })
                
                if self._enviar_paquete(remitente, recursos_a_enviar):
                    del self.acuerdos_pendientes[remitente]
                    return True
        
        # Si no hay acuerdo previo, extraer del mensaje qué debemos enviar
        # Esto es más complejo - por ahora solo confirmamos
        self._log("INFO", f"Aceptación de {remitente} sin acuerdo previo registrado")
        
        return False
    
    # =========================================================================
    # LOOP PRINCIPAL DEL AGENTE
    # =========================================================================
    
    def _procesar_buzon(self, necesidades: Dict, excedentes: Dict) -> int:
        """
        Procesa todas las cartas del buzón.
        
        Returns:
            Número de intercambios realizados
        """
        buzon = self.info_actual.get('Buzon', {}) if self.info_actual else {}
        intercambios = 0
        
        for uid, carta in buzon.items():
            # Solo cartas para nosotros
            if carta.get('dest') != self.alias:
                continue
            
            remitente = carta.get('remi', 'Desconocido')
            mensaje = carta.get('cuerpo', '')
            asunto = carta.get('asunto', '')
            
            self._log("RECEPCION", f"Carta de {remitente}", {
                "asunto": asunto,
                "mensaje": mensaje[:100] + "..." if len(mensaje) > 100 else mensaje
            })
            
            # Ignorar lista negra
            if remitente in self.lista_negra:
                self._log("ALERTA", f"Ignorando {remitente} (lista negra)")
                continue
            
            # Detectar robo
            if self._es_intento_robo(mensaje, remitente):
                continue
            
            # Detectar aceptación
            if self._es_aceptacion(mensaje):
                self._log("ANALISIS", f"{remitente} ACEPTA intercambio")
                
                if self._responder_aceptacion(remitente, mensaje):
                    intercambios += 1
                continue
            
            # Analizar oferta
            analisis = self._analizar_oferta_con_ia(remitente, mensaje, necesidades, excedentes)
            
            self._log("ANALISIS", f"Oferta de {remitente}", {
                "aceptar": analisis.get('aceptar'),
                "razon": analisis.get('razon')
            })
            
            if analisis.get('aceptar'):
                # Guardar acuerdo pendiente
                self.acuerdos_pendientes[remitente] = {
                    "recursos_dar": analisis.get('recursos_dar', {}),
                    "recursos_pedir": analisis.get('recursos_pedir', {}),
                    "timestamp": time.time()
                }
                
                # Enviar aceptación
                self._enviar_carta(
                    remitente,
                    f"Re: {asunto}",
                    f"¡Acepto tu propuesta! Envío los recursos acordados. Saludos, {self.alias}"
                )
        
        return intercambios
    
    def _enviar_propuestas(self, necesidades: Dict, excedentes: Dict, oro: int):
        """Envía propuestas a jugadores no contactados."""
        jugadores = self._obtener_jugadores_disponibles()
        
        # Filtrar ya contactados esta ronda
        jugadores = [j for j in jugadores if j not in self.contactados_esta_ronda]
        
        if not jugadores:
            self._log("INFO", "No hay jugadores a quienes enviar propuestas esta ronda")
            return
        
        # Limitar a 5 por ronda para no saturar
        jugadores = jugadores[:5]
        
        for jugador in jugadores:
            propuesta = self._generar_propuesta(jugador, necesidades, excedentes, oro)
            
            if self._enviar_carta(jugador, propuesta['asunto'], propuesta['cuerpo']):
                self.contactados_esta_ronda.append(jugador)
            
            time.sleep(self.pausa_entre_acciones)
    
    def _ejecutar_ronda(self) -> bool:
        """
        Ejecuta una ronda completa de negociación.
        
        Returns:
            True si el objetivo está completado
        """
        print(f"\n{'═'*60}")
        print(f"📍 RONDA - Modo: {self.modo.value}")
        print(f"{'═'*60}")
        
        # 1. Actualizar estado
        estado = self._actualizar_estado()
        
        if not estado:
            self._log("ERROR", "No se pudo conectar a la API")
            return False
        
        necesidades = estado['necesidades']
        excedentes = estado['excedentes']
        oro = estado['oro']
        objetivo_completado = estado['objetivo_completado']
        
        self._log("INFO", "Estado actual", {
            "oro": oro,
            "necesidades": necesidades,
            "excedentes": excedentes,
            "objetivo_completado": objetivo_completado
        })
        
        # 2. Verificar si cambiar de modo
        if objetivo_completado and self.modo == ModoAgente.CONSEGUIR_OBJETIVO:
            self._log("EXITO", "¡OBJETIVO COMPLETADO! Cambiando a modo MAXIMIZAR ORO")
            self.modo = ModoAgente.MAXIMIZAR_ORO
        
        # Si estamos maximizando oro y no hay excedentes, terminamos
        if self.modo == ModoAgente.MAXIMIZAR_ORO and not excedentes:
            self._log("EXITO", "No hay más excedentes para vender")
            self.modo = ModoAgente.COMPLETADO
            return True
        
        # 3. Procesar buzón (respuestas, ofertas)
        self._log("INFO", "Procesando buzón...")
        intercambios = self._procesar_buzon(necesidades, excedentes)
        
        if intercambios > 0:
            self._log("EXITO", f"{intercambios} intercambio(s) realizado(s)")
            # Actualizar estado después de intercambios
            estado = self._actualizar_estado()
            necesidades = estado['necesidades']
            excedentes = estado['excedentes']
        
        # 4. Enviar propuestas si aún necesitamos algo
        if necesidades or (self.modo == ModoAgente.MAXIMIZAR_ORO and excedentes):
            self._log("INFO", "Enviando propuestas...")
            self._enviar_propuestas(necesidades, excedentes, estado['oro'])
        
        # 5. Reset contactados para siguiente ronda
        self.contactados_esta_ronda = []
        
        return estado['objetivo_completado'] and self.modo == ModoAgente.COMPLETADO
    
    def ejecutar(self, max_rondas: int = None):
        """
        Ejecuta el agente hasta completar el objetivo.
        
        Args:
            max_rondas: Límite de rondas (None = usar self.max_rondas)
        """
        max_rondas = max_rondas or self.max_rondas
        
        print("="*60)
        print("🤖 AGENTE NEGOCIADOR AUTÓNOMO")
        print("="*60)
        print(f"Alias: {self.alias}")
        print(f"Modelo: {self.ia.modelo}")
        print(f"Debug: {'ACTIVADO' if self.debug else 'desactivado'}")
        print(f"Max rondas: {max_rondas}")
        print("="*60)
        
        # Registrar alias en la API para que otros jugadores nos vean
        if not self.api.crear_alias(self.alias):
            print(f"⚠ No se pudo crear el alias '{self.alias}', puede que ya exista.")
        
        for ronda in range(1, max_rondas + 1):
            print(f"\n🔄 RONDA {ronda}/{max_rondas}")
            
            completado = self._ejecutar_ronda()
            
            if completado:
                break
            
            if ronda < max_rondas:
                print(f"\n⏳ Esperando {self.pausa_entre_rondas}s para respuestas...")
                time.sleep(self.pausa_entre_rondas)
        
        # Resumen final
        self._mostrar_resumen()
    
    def _mostrar_resumen(self):
        """Muestra resumen de la ejecución."""
        print("\n" + "="*60)
        print("📊 RESUMEN DE EJECUCIÓN")
        print("="*60)
        
        estado = self._actualizar_estado()
        
        print(f"\n💰 Oro final: {estado.get('oro', 0)}")
        print(f"🎯 Objetivo: {'✅ COMPLETADO' if estado.get('objetivo_completado') else '❌ PENDIENTE'}")
        
        if estado.get('necesidades'):
            print(f"📋 Aún falta: {estado['necesidades']}")
        
        print(f"\n🔄 Intercambios realizados: {len(self.intercambios_realizados)}")
        for i in self.intercambios_realizados:
            print(f"   → {i['destinatario']}: {i['recursos']}")
        
        print(f"\n🛡️ Lista negra: {len(self.lista_negra)} personas")
        if self.lista_negra:
            for p in self.lista_negra:
                print(f"   ⚠️ {p}")
        
        if self.debug:
            print(f"\n📜 Total entradas en log: {len(self.log)}")
    
    def ver_log(self, ultimos: int = 20):
        """Muestra las últimas entradas del log."""
        print(f"\n📜 LOG (últimas {ultimos} entradas):")
        print("-"*60)
        
        for entry in self.log[-ultimos:]:
            t = time.strftime("%H:%M:%S", time.localtime(entry.timestamp))
            print(f"[{t}] {entry.tipo}: {entry.mensaje}")
            if entry.detalles:
                for k, v in entry.detalles.items():
                    print(f"         {k}: {v}")
