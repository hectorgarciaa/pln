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
    
    def __init__(self, alias: str, modelo: str = MODELO_DEFAULT, debug: bool = False,
                 api_url: str = None, source_ip: str = None):
        self.alias = alias
        self.api = APIClient(base_url=api_url, source_ip=source_ip)
        self.ia = OllamaClient(modelo)
        self.debug = debug
        
        # Estado
        self.modo = ModoAgente.CONSEGUIR_OBJETIVO
        self.info_actual: Optional[Dict] = None
        self.gente: List[str] = []
        
        # Seguridad y tracking
        self.lista_negra: List[str] = []
        self.contactados_esta_ronda: List[str] = []
        self.acuerdos_pendientes: Dict[str, List[Dict]] = {}  # persona -> [acuerdos]
        self.intercambios_realizados: List[Dict] = []
        self.cartas_vistas: set = set()  # UIDs ya procesados para evitar reprocesar
        
        # Rotación de propuestas
        self.ronda_actual: int = 0
        self.propuesta_index: int = 0  # para rotar recursos entre rondas
        
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

Reglas:
- Acepta SOLO si me ofrecen algo que NECESITO.
- Rechaza si me piden algo que yo también necesito o no tengo de sobra.
- Rechaza si me ofrecen algo que ya tengo de sobra.

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
        
        # Fallback: decisión basada en análisis real de necesidades/excedentes
        recursos_mencionados = self._extraer_recursos_mensaje(mensaje)
        
        # Separar lo que nos ofrecen vs lo que nos piden del contexto del mensaje
        # Heurística: recursos que necesitamos y aparecen en el mensaje → nos los ofrecen
        nos_ofrecen_algo_util = any(r in necesidades for r in recursos_mencionados)
        # Recursos que aparecen y que nosotros tenemos de sobra → probablemente nos los piden
        nos_piden_algo_que_sobra = any(r in excedentes for r in recursos_mencionados)
        # Rechazar si nos ofrecen algo que ya tenemos de sobra
        nos_ofrecen_algo_que_sobra = all(r in excedentes or r not in necesidades for r in recursos_mencionados)
        
        aceptar = nos_ofrecen_algo_util and not nos_ofrecen_algo_que_sobra
        
        if aceptar:
            razon = "Nos ofrecen recursos que necesitamos"
        elif nos_ofrecen_algo_que_sobra and recursos_mencionados:
            razon = "Solo mencionan recursos que ya tenemos de sobra"
        else:
            razon = "No relevante para nuestras necesidades"
        
        return {
            "aceptar": aceptar,
            "razon": razon,
            "recursos_pedir": {},
            "recursos_dar": {}
        }
    
    # =========================================================================
    # GENERACIÓN DE PROPUESTAS
    # =========================================================================

    def _generar_propuesta(self, destinatario: str, necesidades: Dict,
                           excedentes: Dict, oro: int) -> Optional[Dict[str, str]]:
        """
        Genera una propuesta de negociación con formato estructurado.

        Las propuestas incluyen etiquetas [OFREZCO] y [PIDO] para que el
        receptor pueda parsear exactamente qué se intercambia y decidir
        de forma automática.
        
        Rota los recursos ofrecidos/pedidos entre rondas para cubrir
        todas las combinaciones posibles.
        """

        ofrezco: Dict[str, int] = {}
        pido: Dict[str, int] = {}

        if excedentes and necesidades:
            # Rotar qué recurso pedimos y ofrecemos en cada propuesta
            lista_necesidades = list(necesidades.keys())
            lista_excedentes = list(excedentes.keys())
            
            idx_pido = self.propuesta_index % len(lista_necesidades)
            idx_ofrezco = self.propuesta_index % len(lista_excedentes)
            self.propuesta_index += 1
            
            recurso_pido = lista_necesidades[idx_pido]
            cantidad_pido = min(necesidades[recurso_pido], 3)  # máx 3 por propuesta
            recurso_ofrezco = lista_excedentes[idx_ofrezco]
            cantidad_ofrezco = min(excedentes[recurso_ofrezco], cantidad_pido + 1)  # oferta generosa
            ofrezco = {recurso_ofrezco: cantidad_ofrezco}
            pido = {recurso_pido: cantidad_pido}
        elif necesidades and oro > 2:
            # Comprar con oro
            recurso_pido = list(necesidades.keys())[0]
            cantidad_pido = min(necesidades[recurso_pido], 2)
            precio = cantidad_pido * 2  # 2 oro por recurso
            ofrezco = {"oro": min(precio, oro)}
            pido = {recurso_pido: cantidad_pido}
        elif excedentes:
            # Vender excedentes por oro
            recurso_ofrezco = list(excedentes.keys())[0]
            cantidad_ofrezco = min(excedentes[recurso_ofrezco], 3)
            ofrezco = {recurso_ofrezco: cantidad_ofrezco}
            pido = {"oro": cantidad_ofrezco}
        else:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in ofrezco.items())
        pido_str = ", ".join(f"{c} {r}" for r, c in pido.items())

        cuerpo = (
            f"Hola {destinatario}! Te propongo un intercambio:\n"
            f"[OFREZCO] {ofrezco_str}\n"
            f"[PIDO] {pido_str}\n"
            f"Si te interesa, responde con [ACEPTO]. Saludos, {self.alias}"
        )

        return {
            "asunto": f"Intercambio: mi {ofrezco_str} por tu {pido_str}",
            "cuerpo": cuerpo,
            "_ofrezco": ofrezco,
            "_pido": pido,
        }
    
    def _generar_contraoferta(self, destinatario: str, 
                              ofrecen: Dict[str, int],
                              necesidades: Dict, excedentes: Dict) -> Optional[Dict]:
        """
        Genera una contraoferta cuando el otro ofrece algo útil
        pero pide algo que no tenemos. Ofrecemos nuestros excedentes a cambio.
        """
        # Lo que queremos del otro: de lo que nos ofrecen, ¿qué necesitamos?
        pido = {}
        for rec, cant in ofrecen.items():
            if rec in necesidades:
                pido[rec] = min(cant, necesidades[rec])
        
        if not pido:
            return None
        
        # Lo que ofrecemos: nuestros excedentes
        ofrezco = {}
        cantidad_total_pido = sum(pido.values())
        cantidad_ofrecida = 0
        for rec, cant in excedentes.items():
            if cantidad_ofrecida >= cantidad_total_pido + 1:  # generoso
                break
            c = min(cant, cantidad_total_pido + 1 - cantidad_ofrecida)
            ofrezco[rec] = c
            cantidad_ofrecida += c
        
        if not ofrezco:
            return None
        
        ofrezco_str = ", ".join(f"{c} {r}" for r, c in ofrezco.items())
        pido_str = ", ".join(f"{c} {r}" for r, c in pido.items())
        
        cuerpo = (
            f"Hola {destinatario}! Vi tu oferta pero no tengo lo que pides. "
            f"Te hago una contrapropuesta:\n"
            f"[OFREZCO] {ofrezco_str}\n"
            f"[PIDO] {pido_str}\n"
            f"Si te interesa, responde con [ACEPTO]. Saludos, {self.alias}"
        )
        
        return {
            "asunto": f"Contrapropuesta: mi {ofrezco_str} por tu {pido_str}",
            "cuerpo": cuerpo,
            "_ofrezco": ofrezco,
            "_pido": pido,
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

        # Buscar si tenemos acuerdos pendientes con esta persona
        if remitente in self.acuerdos_pendientes and self.acuerdos_pendientes[remitente]:
            # Tomar el acuerdo más antiguo (FIFO)
            acuerdo = self.acuerdos_pendientes[remitente].pop(0)
            recursos_a_enviar = acuerdo.get('recursos_dar', {})

            # Limpiar la key si no quedan más acuerdos
            if not self.acuerdos_pendientes[remitente]:
                del self.acuerdos_pendientes[remitente]

            if recursos_a_enviar:
                self._log("DECISION", f"Ejecutando acuerdo con {remitente}: envío {recursos_a_enviar}")

                # Refrescar estado para comprobar que aún tenemos los recursos
                self._actualizar_estado()

                if self._enviar_paquete(remitente, recursos_a_enviar):
                    return True
                else:
                    self._log("ERROR", f"No se pudo enviar paquete a {remitente}")

        self._log("INFO", f"Aceptación de {remitente} sin acuerdo pendiente registrado")
        return False

    def _parsear_oferta_estructurada(self, mensaje: str) -> Optional[Dict]:
        """
        Parsea etiquetas [OFREZCO] y [PIDO] de un mensaje.

        Returns:
            {"ofrecen": {"recurso": cant}, "piden": {"recurso": cant}} o None
        """
        ofrecen = {}
        piden = {}

        # Buscar [OFREZCO] ... y [PIDO] ...
        ofrezco_match = re.search(r'\[OFREZCO\]\s*(.+?)(?:\n|\[|$)', mensaje, re.IGNORECASE)
        pido_match = re.search(r'\[PIDO\]\s*(.+?)(?:\n|\[|$)', mensaje, re.IGNORECASE)

        if not ofrezco_match or not pido_match:
            return None

        # Parsear "3 madera, 2 oro" etc.
        patron = r'(\d+)\s+(\w+)'
        for cant, recurso in re.findall(patron, ofrezco_match.group(1)):
            ofrecen[recurso.lower()] = int(cant)
        for cant, recurso in re.findall(patron, pido_match.group(1)):
            piden[recurso.lower()] = int(cant)

        if ofrecen and piden:
            return {"ofrecen": ofrecen, "piden": piden}
        return None

    def _evaluar_oferta(self, ofrecen: Dict[str, int], piden: Dict[str, int],
                        necesidades: Dict, excedentes: Dict) -> bool:
        """
        Decide si aceptar una oferta basándose en necesidades/excedentes.
        Acepta si:
        - Lo que nos ofrecen es algo que necesitamos
        - Lo que nos piden es algo que nos sobra (no algo que también necesitamos)
        - Tenemos suficientes recursos para dar
        """
        # ¿Nos ofrecen algo que necesitamos?
        nos_ayuda = any(r in necesidades for r in ofrecen)
        # ¿Nos piden algo que nos sobra o podemos permitirnos?
        mis_recursos = self.info_actual.get('Recursos', {}) if self.info_actual else {}
        podemos_dar = all(mis_recursos.get(r, 0) >= c for r, c in piden.items())
        # ¿Nos piden algo que también necesitamos? → rechazar
        nos_piden_algo_que_necesitamos = any(r in necesidades for r in piden)
        # ¿Nos ofrecen algo que ya nos sobra? → no tan útil
        nos_ofrecen_algo_que_sobra = all(r not in necesidades for r in ofrecen)

        return nos_ayuda and podemos_dar and not nos_piden_algo_que_necesitamos and not nos_ofrecen_algo_que_sobra
    
    # =========================================================================
    # LOOP PRINCIPAL DEL AGENTE
    # =========================================================================
    
    def _procesar_buzon(self, necesidades: Dict, excedentes: Dict) -> int:
        """
        Procesa todas las cartas del buzón.

        Flujo:
        - Carta con [OFREZCO]/[PIDO]: evaluar y si conviene → enviar paquete + responder [ACEPTO]
        - Carta con [ACEPTO]: buscar acuerdo pendiente → enviar nuestro paquete
        - Otra carta: analizar con IA (fallback)
        - Si nos piden algo que no tenemos pero ofrecen algo útil → contraoferta

        Returns:
            Número de intercambios realizados
        """
        buzon = self.info_actual.get('Buzon', {}) if self.info_actual else {}
        intercambios = 0
        cartas_procesadas = []

        for uid, carta in buzon.items():
            # Deduplicar: no reprocesar cartas ya vistas
            carta_id = carta.get('id', uid)
            if carta_id in self.cartas_vistas:
                cartas_procesadas.append(uid)
                continue
            self.cartas_vistas.add(carta_id)

            remitente = carta.get('remi', 'Desconocido')
            mensaje = carta.get('cuerpo', '')
            asunto = carta.get('asunto', '')

            self._log("RECEPCION", f"Carta de {remitente}", {
                "asunto": asunto,
                "mensaje": mensaje[:150]
            })

            # Ignorar lista negra
            if remitente in self.lista_negra:
                self._log("ALERTA", f"Ignorando {remitente} (lista negra)")
                cartas_procesadas.append(uid)
                continue

            # Detectar robo
            if self._es_intento_robo(mensaje, remitente):
                cartas_procesadas.append(uid)
                continue

            # ── Caso 1: mensaje con [ACEPTO] → ejecutar acuerdo pendiente ──
            if '[ACEPTO]' in mensaje.upper() or self._es_aceptacion(mensaje):
                self._log("ANALISIS", f"{remitente} ACEPTA intercambio")
                if self._responder_aceptacion(remitente, mensaje):
                    intercambios += 1
                cartas_procesadas.append(uid)
                continue

            # ── Caso 2: propuesta estructurada con [OFREZCO]/[PIDO] ──
            oferta = self._parsear_oferta_estructurada(mensaje)
            if oferta:
                ofrecen = oferta['ofrecen']  # lo que el otro nos da
                piden = oferta['piden']      # lo que el otro nos pide

                self._log("ANALISIS", f"Propuesta de {remitente}", {
                    "nos_ofrecen": ofrecen,
                    "nos_piden": piden
                })

                if self._evaluar_oferta(ofrecen, piden, necesidades, excedentes):
                    # ¡Aceptamos! Enviar lo que nos piden
                    self._log("DECISION", f"ACEPTO oferta de {remitente}, envío {piden}")
                    if self._enviar_paquete(remitente, piden):
                        # Confirmar con carta
                        self._enviar_carta(
                            remitente,
                            f"Re: {asunto}",
                            f"[ACEPTO] Trato hecho! Te envié {piden}. Espero mis {ofrecen}. Saludos, {self.alias}"
                        )
                        intercambios += 1
                    else:
                        self._log("ERROR", f"No pude enviar paquete a {remitente}")
                else:
                    # Evaluar si merece una contraoferta:
                    # ¿Nos ofrecen algo que necesitamos pero piden algo que no tenemos?
                    nos_ofrecen_algo_util = any(r in necesidades for r in ofrecen)
                    if nos_ofrecen_algo_util and excedentes:
                        # Generar contraoferta con lo que SÍ tenemos
                        contra = self._generar_contraoferta(remitente, ofrecen, necesidades, excedentes)
                        if contra:
                            self._log("DECISION", f"CONTRAOFERTA a {remitente}", {
                                "ofrezco": contra['_ofrezco'],
                                "pido": contra['_pido']
                            })
                            if self._enviar_carta(remitente, contra['asunto'], contra['cuerpo']):
                                # Registrar como acuerdo pendiente
                                acuerdo = {
                                    "recursos_dar": contra['_ofrezco'],
                                    "recursos_pedir": contra['_pido'],
                                    "timestamp": time.time()
                                }
                                if remitente not in self.acuerdos_pendientes:
                                    self.acuerdos_pendientes[remitente] = []
                                self.acuerdos_pendientes[remitente].append(acuerdo)
                        else:
                            self._log("DECISION", f"RECHAZO oferta de {remitente} (no puedo contraofertar)")
                            self._enviar_carta(
                                remitente, f"Re: {asunto}",
                                f"No me interesa ese intercambio por ahora. Saludos, {self.alias}"
                            )
                    else:
                        self._log("DECISION", f"RECHAZO oferta de {remitente}")
                        self._enviar_carta(
                            remitente,
                            f"Re: {asunto}",
                            f"No me interesa ese intercambio por ahora. Saludos, {self.alias}"
                        )

                cartas_procesadas.append(uid)
                continue

            # ── Caso 3: mensaje libre → análisis con IA ──
            analisis = self._analizar_oferta_con_ia(remitente, mensaje, necesidades, excedentes)
            self._log("ANALISIS", f"IA analizó carta de {remitente}", {
                "aceptar": analisis.get('aceptar'),
                "razon": analisis.get('razon')
            })
            cartas_procesadas.append(uid)

        # Limpiar buzón de cartas procesadas
        for uid in cartas_procesadas:
            self.api.eliminar_carta(uid)

        return intercambios
    
    def _enviar_propuestas(self, necesidades: Dict, excedentes: Dict, oro: int):
        """Envía propuestas estructuradas a jugadores no contactados."""
        jugadores = self._obtener_jugadores_disponibles()

        # Filtrar ya contactados esta ronda
        jugadores = [j for j in jugadores if j not in self.contactados_esta_ronda]

        if not jugadores:
            self._log("INFO", "No hay jugadores a quienes enviar propuestas esta ronda")
            return

        # Limitar a 3 por ronda para no saturar
        jugadores = jugadores[:3]

        for jugador in jugadores:
            propuesta = self._generar_propuesta(jugador, necesidades, excedentes, oro)

            if propuesta is None:
                self._log("INFO", f"No se generó propuesta para {jugador}")
                continue

            if self._enviar_carta(jugador, propuesta['asunto'], propuesta['cuerpo']):
                self.contactados_esta_ronda.append(jugador)

                # Guardar acuerdo pendiente: cuando nos digan [ACEPTO],
                # nosotros enviamos lo que ofrecimos (_ofrezco)
                acuerdo = {
                    "recursos_dar": propuesta['_ofrezco'],
                    "recursos_pedir": propuesta['_pido'],
                    "timestamp": time.time()
                }
                if jugador not in self.acuerdos_pendientes:
                    self.acuerdos_pendientes[jugador] = []
                self.acuerdos_pendientes[jugador].append(acuerdo)
                self._log("INFO", f"Acuerdo pendiente con {jugador}: dar={propuesta['_ofrezco']}, pedir={propuesta['_pido']}")

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
        
        self.ronda_actual += 1
        
        # Limpiar acuerdos pendientes viejos (>5 minutos)
        ahora = time.time()
        for persona in list(self.acuerdos_pendientes.keys()):
            self.acuerdos_pendientes[persona] = [
                a for a in self.acuerdos_pendientes[persona]
                if ahora - a.get('timestamp', 0) < 300
            ]
            if not self.acuerdos_pendientes[persona]:
                del self.acuerdos_pendientes[persona]
        
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
