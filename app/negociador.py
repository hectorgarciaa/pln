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
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from config import RECURSOS_CONOCIDOS, MODELO_DEFAULT
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
        """Usa IA para detectar si un mensaje es un intento de estafa/robo."""
        prompt = f"""Analiza si este mensaje de un juego de intercambio de recursos es un intento de ESTAFA o ROBO.

MENSAJE DE "{remitente}": "{mensaje}"

Señales de estafa: pedir que envíes recursos primero sin garantía, prometer cosas imposibles,
usar urgencia o presión, ofrecer cosas gratis sin motivo, mencionar bugs o errores del sistema,
pedir confianza ciega, etc.

Responde SOLO con un JSON: {{"es_estafa": true/false, "razon": "explicación breve"}}
No escribas nada más."""

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)

        try:
            # Buscar JSON en la respuesta
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}') + 1
            if inicio != -1 and fin > inicio:
                resultado = json.loads(respuesta[inicio:fin])
                if resultado.get('es_estafa', False):
                    self._log("ALERTA", f"IA detecta posible estafa de {remitente}",
                              {"razon": resultado.get('razon', 'Sin detalle')})
                    if remitente not in self.lista_negra:
                        self.lista_negra.append(remitente)
                    return True
        except (json.JSONDecodeError, Exception) as e:
            self._log("ERROR", f"Error al analizar estafa con IA: {e}")

        return False
    
    def _es_aceptacion(self, mensaje: str) -> bool:
        """Usa IA para detectar si un mensaje acepta un intercambio."""
        prompt = f"""En un juego de intercambio de recursos, analiza si este mensaje es una ACEPTACIÓN de un trato propuesto.

MENSAJE: "{mensaje}"

Una aceptación puede ser directa ("acepto", "trato hecho") o indirecta ("te envío los recursos", "perfecto").
Un rechazo es lo contrario ("no me interesa", "no acepto", "muy caro").
Si es una propuesta nueva (no una respuesta a un trato), NO es una aceptación.

Responde SOLO con un JSON: {{"es_aceptacion": true/false, "razon": "explicación breve"}}
No escribas nada más."""

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)

        try:
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}') + 1
            if inicio != -1 and fin > inicio:
                resultado = json.loads(respuesta[inicio:fin])
                return resultado.get('es_aceptacion', False)
        except (json.JSONDecodeError, Exception) as e:
            self._log("ERROR", f"Error al analizar aceptación con IA: {e}")

        return False
    
    def _analizar_mensaje_completo(self, remitente: str, mensaje: str,
                                     necesidades: Dict, excedentes: Dict) -> Dict:
        """
        Usa IA para analizar completamente un mensaje de negociación.
        Determina qué tipo de mensaje es, qué recursos se mencionan,
        y si debemos aceptar, rechazar o contraofertar.
        """
        mis_recursos = self.info_actual.get('Recursos', {}) if self.info_actual else {}

        prompt = f"""Eres un asistente de un juego de intercambio de recursos. Analiza este mensaje.

MENSAJE DE "{remitente}": "{mensaje}"

MI SITUACIÓN:
- Recursos que tengo: {json.dumps(mis_recursos)}
- Recursos que NECESITO conseguir: {json.dumps(necesidades)}
- Recursos que me SOBRAN y puedo dar: {json.dumps(excedentes)}

Determina:
1. ¿Qué recursos OFRECE el remitente? (lo que me daría a mí)
2. ¿Qué recursos PIDE el remitente? (lo que quiere que yo le dé)
3. ¿Debo aceptar? Acepta SOLO si:
   - Me ofrecen algo que NECESITO
   - Lo que me piden es algo que me SOBRA o que puedo permitirme dar
   - NO me piden algo que yo también necesito
4. Si no debo aceptar pero me ofrecen algo útil, sugiere una contraoferta con mis excedentes.

Responde SOLO con un JSON (sin texto extra):
{{{{
  "ofrecen": {{"recurso": cantidad}},
  "piden": {{"recurso": cantidad}},
  "aceptar": true/false,
  "razon": "explicación breve",
  "contraoferta": true/false,
  "contraoferta_dar": {{"recurso": cantidad}},
  "contraoferta_pedir": {{"recurso": cantidad}}
}}}}"""

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)

        try:
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}') + 1
            if inicio != -1 and fin > inicio:
                return json.loads(respuesta[inicio:fin])
        except (json.JSONDecodeError, Exception) as e:
            self._log("ERROR", f"Error parseando respuesta IA: {e}")

        # Si la IA falla completamente, rechazar por seguridad
        return {
            "ofrecen": {},
            "piden": {},
            "aceptar": False,
            "razon": "No se pudo analizar el mensaje",
            "contraoferta": False,
            "contraoferta_dar": {},
            "contraoferta_pedir": {}
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

    def _generar_texto_propuesta_ia(self, destinatario: str, necesidades: Dict,
                                     excedentes: Dict, oro: int) -> Optional[Dict]:
        """
        Usa IA para generar el texto de una propuesta de negociación.
        La lógica de qué ofrecer/pedir se mantiene programática para ser precisa.
        """
        propuesta = self._generar_propuesta(destinatario, necesidades, excedentes, oro)
        if not propuesta:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in propuesta['_ofrezco'].items())
        pido_str = ", ".join(f"{c} {r}" for r, c in propuesta['_pido'].items())

        prompt = f"""Genera un mensaje corto y amigable para proponer un intercambio en un juego.

DESTINATARIO: {destinatario}
YO SOY: {self.alias}
OFREZCO: {ofrezco_str}
PIDO: {pido_str}

El mensaje debe:
- Ser breve (2-3 frases máximo)
- Incluir exactamente las etiquetas [OFREZCO] y [PIDO] con las cantidades
- Terminar diciendo que responda con [ACEPTO] si le interesa
- Ser educado

Escribe SOLO el mensaje, nada más."""

        texto = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)

        # Si la IA genera algo, usamos su texto pero mantenemos los datos internos
        if texto and not texto.startswith("Error"):
            propuesta['cuerpo'] = texto
            propuesta['asunto'] = f"Intercambio: mi {ofrezco_str} por tu {pido_str}"

        return propuesta
    
    # =========================================================================
    # LOOP PRINCIPAL DEL AGENTE
    # =========================================================================
    
    def _procesar_buzon(self, necesidades: Dict, excedentes: Dict) -> int:
        """
        Procesa todas las cartas del buzón usando IA para todo el análisis.

        Flujo para cada carta:
        1. ¿Es de alguien en lista negra? → Ignorar
        2. ¿Es un intento de estafa? (IA) → Bloquear
        3. ¿Es una aceptación de un trato? (IA) → Ejecutar acuerdo pendiente
        4. Analizar contenido completo (IA) → Aceptar / Contraofertar / Rechazar

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

            # Paso 1: ¿Es intento de estafa? (IA)
            if self._es_intento_robo(mensaje, remitente):
                cartas_procesadas.append(uid)
                continue

            # Paso 2: ¿Es una aceptación? (IA)
            if self._es_aceptacion(mensaje):
                self._log("ANALISIS", f"IA detecta que {remitente} ACEPTA intercambio")
                if self._responder_aceptacion(remitente, mensaje):
                    intercambios += 1
                cartas_procesadas.append(uid)
                continue

            # Paso 3: Análisis completo del mensaje con IA
            analisis = self._analizar_mensaje_completo(remitente, mensaje, necesidades, excedentes)
            ofrecen = analisis.get('ofrecen', {})
            piden = analisis.get('piden', {})
            aceptar = analisis.get('aceptar', False)
            razon = analisis.get('razon', '')
            quiere_contraoferta = analisis.get('contraoferta', False)

            self._log("ANALISIS", f"IA analizó carta de {remitente}", {
                "ofrecen": ofrecen,
                "piden": piden,
                "aceptar": aceptar,
                "razon": razon
            })

            if aceptar and piden:
                # La IA dice que aceptemos → enviar lo que piden
                self._log("DECISION", f"ACEPTO oferta de {remitente}, envío {piden}")
                if self._enviar_paquete(remitente, piden):
                    self._enviar_carta(
                        remitente,
                        f"Re: {asunto}",
                        f"[ACEPTO] Trato hecho! Te envié {piden}. Espero mis {ofrecen}. Saludos, {self.alias}"
                    )
                    intercambios += 1
                else:
                    self._log("ERROR", f"No pude enviar paquete a {remitente}")

            elif quiere_contraoferta and excedentes:
                # La IA sugiere contraofertar
                contra_dar = analisis.get('contraoferta_dar', {})
                contra_pedir = analisis.get('contraoferta_pedir', {})

                if contra_dar and contra_pedir:
                    contra = self._generar_contraoferta(remitente, ofrecen, necesidades, excedentes)
                    if contra:
                        self._log("DECISION", f"CONTRAOFERTA a {remitente}", {
                            "ofrezco": contra['_ofrezco'],
                            "pido": contra['_pido']
                        })
                        if self._enviar_carta(remitente, contra['asunto'], contra['cuerpo']):
                            acuerdo = {
                                "recursos_dar": contra['_ofrezco'],
                                "recursos_pedir": contra['_pido'],
                                "timestamp": time.time()
                            }
                            if remitente not in self.acuerdos_pendientes:
                                self.acuerdos_pendientes[remitente] = []
                            self.acuerdos_pendientes[remitente].append(acuerdo)
                else:
                    self._log("DECISION", f"RECHAZO oferta de {remitente} ({razon})")
                    self._enviar_carta(
                        remitente, f"Re: {asunto}",
                        f"No me interesa ese intercambio por ahora. Saludos, {self.alias}"
                    )

            elif ofrecen or piden:
                # Hay una propuesta pero la IA dijo que no aceptemos
                self._log("DECISION", f"RECHAZO oferta de {remitente} ({razon})")
                self._enviar_carta(
                    remitente,
                    f"Re: {asunto}",
                    f"No me interesa ese intercambio por ahora. Saludos, {self.alias}"
                )

            else:
                # Mensaje sin propuesta clara
                self._log("INFO", f"Mensaje de {remitente} sin propuesta clara: {razon}")

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
