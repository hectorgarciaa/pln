"""
Agente Negociador Autónomo.

Ejecuta un loop de rondas hasta completar el objetivo del juego:
  1. Actualizar estado  → ¿Qué necesito? ¿Qué me sobra?
  2. Revisar buzón      → Analizar ofertas (IA), aceptar / rechazar
  3. Enviar propuestas  → Contactar jugadores con intercambios
  4. Esperar            → Dar tiempo a respuestas
  5. ¿Objetivo?         → Cambiar a modo MAXIMIZAR ORO o fin

Usa loguru para logging, rich para la interfaz de terminal y
pydantic para validar las respuestas JSON de la IA.
"""

import json
import os
import re as _re
import sys
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from config import RECURSOS_CONOCIDOS, MODELO_DEFAULT, OLLAMA_URL
from api_client import APIClient
from ollama_client import OllamaClient

# ── Rich console compartida ─────────────────────────────────────────────
console = Console()


# =========================================================================
# MODELOS PYDANTIC — respuestas de la IA
# =========================================================================

class RespuestaEstafa(BaseModel):
    """Respuesta de la IA al analizar posibles estafas."""
    es_estafa: bool = False
    razon: str = ""


class RespuestaAceptacion(BaseModel):
    """Respuesta de la IA al detectar aceptaciones."""
    es_aceptacion: bool = False
    razon: str = ""


class RespuestaAnalisis(BaseModel):
    """Respuesta de la IA al analizar un mensaje de negociación.

    Usa validadores para tolerar respuestas malformadas de la IA
    (p.ej. contraoferta_pedir como lista en vez de dict).
    """
    ofrecen: Dict[str, int] = Field(default_factory=dict)
    piden: Dict[str, int] = Field(default_factory=dict)
    aceptar: bool = False
    razon: str = ""
    contraoferta: bool = False
    contraoferta_dar: Dict[str, int] = Field(default_factory=dict)
    contraoferta_pedir: Dict[str, int] = Field(default_factory=dict)

    from pydantic import field_validator

    @field_validator("ofrecen", "piden", "contraoferta_dar", "contraoferta_pedir", mode="before")
    @classmethod
    def _coerce_to_dict(cls, v: Any) -> Dict[str, int]:
        """Convierte valores no-dict a dict vacío en vez de fallar."""
        if isinstance(v, dict):
            # Asegurar que las claves son str y valores int
            return {str(k): int(val) for k, val in v.items() if val is not None}
        return {}


# =========================================================================
# ENUMS
# =========================================================================

class ModoAgente(Enum):
    """Estados del agente."""
    CONSEGUIR_OBJETIVO = "conseguir_objetivo"
    MAXIMIZAR_ORO = "maximizar_oro"
    COMPLETADO = "completado"


# =========================================================================
# AGENTE
# =========================================================================

class AgenteNegociador:
    """
    Agente autónomo que negocia para conseguir recursos.

    Uso:
        agente = AgenteNegociador("MiAlias", debug=True)
        agente.ejecutar()
    """

    def __init__(self, alias: str, modelo: str = MODELO_DEFAULT, debug: bool = False,
                 api_url: str = None, source_ip: str = None):
        self.alias = alias
        self.api = APIClient(base_url=api_url, source_ip=source_ip)
        self.ia = OllamaClient(modelo)
        self.debug = debug

        # ── Agentes pydantic_ai (structured output) ────────────────────
        _ai_model = f"ollama:{modelo}"
        _ai_settings = ModelSettings(
            temperature=0.3,
            top_p=0.7,
            max_tokens=512,
        )

        self._agente_aceptacion = Agent(
            _ai_model,
            result_type=RespuestaAceptacion,
            system_prompt=(
                "Eres un analizador de mensajes en un juego de intercambio de recursos.\n"
                "Determina si el mensaje del usuario es una ACEPTACIÓN de un trato propuesto.\n\n"
                "Aceptación directa: 'acepto', 'trato hecho', 'de acuerdo'.\n"
                "Aceptación indirecta: 'te envío los recursos', 'perfecto, enviado'.\n"
                "NO es aceptación: rechazos ('no me conviene', 'no acepto'), "
                "propuestas nuevas, ni frases como 'si aceptas, dime'.\n"
                "Responde de forma concisa."
            ),
            model_settings=_ai_settings,
            retries=2,
        )

        self._agente_estafa = Agent(
            _ai_model,
            result_type=RespuestaEstafa,
            system_prompt=(
                "Eres un detector de estafas en un juego de intercambio de recursos.\n"
                "Señales de estafa: pedir enviar recursos primero sin garantía, "
                "prometer cosas imposibles, urgencia/presión, cosas gratis sin motivo, "
                "mencionar bugs del sistema, pedir confianza ciega.\n"
                "Un intercambio legítimo propone dar X a cambio de Y.\n"
                "Responde de forma concisa."
            ),
            model_settings=_ai_settings,
            retries=2,
        )

        self._agente_analisis = Agent(
            _ai_model,
            result_type=RespuestaAnalisis,
            system_prompt=(
                "Eres un analizador de mensajes en un juego de intercambio de recursos.\n"
                "Tu ÚNICA tarea es EXTRAER qué ofrece y qué pide el remitente.\n\n"
                "REGLAS:\n"
                '- "ofrecen" = lo que el remitente ofrece DAR (lo que yo recibiría).\n'
                '- "piden" = lo que el remitente quiere RECIBIR (lo que yo daría).\n'
                "- Solo incluye recursos y cantidades EXPLÍCITOS en el mensaje.\n"
                "- Rechazo, saludo o no-propuesta → ofrecen={}, piden={}.\n"
                "- NO inventes datos. Pon aceptar=false SIEMPRE.\n\n"
                'Ejemplo: "yo te doy 2 madera y tú me das 3 piedra"\n'
                '→ ofrecen={"madera": 2}, piden={"piedra": 3}'
            ),
            model_settings=_ai_settings,
            retries=2,
        )

        # Estado
        self.modo = ModoAgente.CONSEGUIR_OBJETIVO
        self.info_actual: Optional[Dict] = None
        self.gente: List[str] = []

        # Seguridad y tracking
        self.lista_negra: List[str] = []
        self.contactados_esta_ronda: List[str] = []
        self.acuerdos_pendientes: Dict[str, List[Dict]] = {}
        self.intercambios_realizados: List[Dict] = []
        self.cartas_vistas: set = set()

        # Rotación de propuestas
        self.ronda_actual: int = 0
        self.propuesta_index: int = 0

        # Configuración
        self.pausa_entre_acciones = 1
        self.pausa_entre_rondas = 30
        self.max_rondas = 10

        # ── Configurar loguru ────────────────────────────────────────────
        # Limpiar handlers previos (evitar duplicados en multi-bot)
        logger.remove()

        # Consola: solo si debug
        if debug:
            logger.add(sys.stderr, level="DEBUG",
                       format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                              "<level>{level: <8}</level> | "
                              "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                              "<level>{message}</level>")

        # Fichero: SIEMPRE (logs/{alias}.log)
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{alias}.log")
        logger.add(
            log_path,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
            enqueue=True,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                   "{name}:{function}:{line} - {message}",
        )
        logger.info(f"Logs guardados en {log_path}")

    # =====================================================================
    # LOGGING
    # =====================================================================

    def _log(self, tipo: str, mensaje: str, detalles: Dict = None):
        """Registra una acción con loguru."""
        icono = {
            "ENVIO": "📤", "RECEPCION": "📥", "ANALISIS": "🔍",
            "DECISION": "🧠", "INTERCAMBIO": "🔄", "ALERTA": "⚠️",
            "EXITO": "✅", "ERROR": "❌", "INFO": "ℹ️",
        }.get(tipo, "•")

        extra = f" | {detalles}" if detalles else ""
        log_msg = f"{icono} [{tipo}] {mensaje}{extra}"

        # Mapear tipo → nivel loguru
        nivel = {
            "ERROR": "error", "ALERTA": "warning", "EXITO": "success",
        }.get(tipo, "debug")

        logger.opt(depth=1).log(nivel.upper(), log_msg)

        # Siempre mostrar en consola si debug está activo
        if self.debug:
            console.print(f"  {log_msg}")

    # =====================================================================
    # CONSULTAS DE ESTADO
    # =====================================================================

    def _actualizar_estado(self) -> Dict:
        """Obtiene y procesa el estado actual."""
        self.info_actual = self.api.get_info()
        self.gente = self.api.get_gente()

        if not self.info_actual:
            return {}

        recursos = self.info_actual.get("Recursos", {})
        objetivo = self.info_actual.get("Objetivo", {})

        necesidades = {}
        for rec, cant_obj in objetivo.items():
            actual = recursos.get(rec, 0)
            if actual < cant_obj:
                necesidades[rec] = cant_obj - actual

        excedentes = {}
        for rec, actual in recursos.items():
            if rec == "oro":
                continue
            obj = objetivo.get(rec, 0)
            if actual > obj:
                excedentes[rec] = actual - obj

        return {
            "recursos": recursos,
            "oro": recursos.get("oro", 0),
            "objetivo": objetivo,
            "necesidades": necesidades,
            "excedentes": excedentes,
            "objetivo_completado": len(necesidades) == 0,
        }

    def _obtener_jugadores_disponibles(self) -> List[str]:
        """Devuelve jugadores que podemos contactar."""
        alias_propios_raw = self.info_actual.get("Alias", []) if self.info_actual else []
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
            self._log("INFO", "No hay jugadores disponibles",
                      {"gente": self.gente, "mis_alias": alias_propios})

        return disponibles

    # =====================================================================
    # ANÁLISIS DE MENSAJES (IA + pydantic)
    # =====================================================================

    def _parsear_json_ia(self, respuesta: str) -> Optional[dict]:
        """Extrae el primer objeto JSON de una respuesta de texto."""
        inicio = respuesta.find("{")
        fin = respuesta.rfind("}") + 1
        if inicio != -1 and fin > inicio:
            try:
                return json.loads(respuesta[inicio:fin])
            except json.JSONDecodeError:
                pass
        return None

    def _es_intento_robo(self, mensaje: str, remitente: str) -> bool:
        """Usa pydantic_ai para detectar si un mensaje es un intento de estafa."""
        try:
            result = self._agente_estafa.run_sync(
                f'Mensaje de "{remitente}": "{mensaje}"'
            )
            self._log("DEBUG", f"IA estafa: {result.data.model_dump()}")

            if result.data.es_estafa:
                self._log("ALERTA", f"IA detecta posible estafa de {remitente}",
                          {"razon": result.data.razon})
                if remitente not in self.lista_negra:
                    self.lista_negra.append(remitente)
                return True
            return False
        except Exception as e:
            self._log("ERROR", f"Error pydantic_ai (estafa): {e}")
            return False

    def _es_aceptacion(self, mensaje: str) -> bool:
        """Usa pydantic_ai para detectar si un mensaje acepta un intercambio."""
        try:
            result = self._agente_aceptacion.run_sync(mensaje)
            self._log("DEBUG", f"IA aceptación: {result.data.model_dump()}")
            return result.data.es_aceptacion
        except Exception as e:
            self._log("ERROR", f"Error pydantic_ai (aceptación): {e}")
            return False

    def _decidir_aceptar_programatico(self, ofrecen: Dict[str, int],
                                       piden: Dict[str, int],
                                       necesidades: Dict, excedentes: Dict) -> tuple:
        """Decide si aceptar con lógica determinista. Devuelve (bool, str)."""
        if not ofrecen or not piden:
            return False, "oferta incompleta (falta ofrecen o piden)"

        me_ofrecen_lo_que_necesito = any(r in necesidades for r in ofrecen)
        piden_solo_excedentes = all(
            r in excedentes and excedentes[r] >= c
            for r, c in piden.items() if c > 0
        )

        if me_ofrecen_lo_que_necesito and piden_solo_excedentes:
            return True, "ofrecen lo que necesito y piden lo que me sobra"
        if not me_ofrecen_lo_que_necesito:
            return False, "no ofrecen nada de lo que necesito"
        return False, "piden recursos que no me sobran o no tengo suficientes"

    def _analizar_mensaje_completo(self, remitente: str, mensaje: str,
                                   necesidades: Dict, excedentes: Dict) -> RespuestaAnalisis:
        """Analiza un mensaje con pydantic_ai y decide programáticamente.

        Flujo:
        1. pydantic_ai EXTRAE ofrecen/piden (structured output validado)
        2. _decidir_aceptar_programatico() decide si aceptar
        """
        try:
            result = self._agente_analisis.run_sync(
                f'Mensaje de "{remitente}":\n{mensaje}'
            )
            analisis = result.data
            self._log("DEBUG",
                      f"IA análisis: ofrecen={analisis.ofrecen}, piden={analisis.piden}")

            # Forzar aceptar=False: la IA solo extrae, nosotros decidimos
            analisis.aceptar = False
            aceptar, razon = self._decidir_aceptar_programatico(
                analisis.ofrecen, analisis.piden, necesidades, excedentes)
            analisis.aceptar = aceptar
            analisis.razon = razon
            return analisis
        except Exception as e:
            self._log("ERROR", f"Error pydantic_ai (análisis): {e}")
            return RespuestaAnalisis(razon="No se pudo analizar el mensaje")

    # =====================================================================
    # GENERACIÓN DE PROPUESTAS
    # =====================================================================

    def _generar_propuesta(self, destinatario: str, necesidades: Dict,
                           excedentes: Dict, oro: int) -> Optional[Dict[str, str]]:
        """Genera una propuesta con etiquetas [OFREZCO] / [PIDO]."""
        ofrezco: Dict[str, int] = {}
        pido: Dict[str, int] = {}

        if excedentes and necesidades:
            lista_necesidades = list(necesidades.keys())
            lista_excedentes = list(excedentes.keys())
            idx_pido = self.propuesta_index % len(lista_necesidades)
            idx_ofrezco = self.propuesta_index % len(lista_excedentes)
            self.propuesta_index += 1
            recurso_pido = lista_necesidades[idx_pido]
            cantidad_pido = min(necesidades[recurso_pido], 3)
            recurso_ofrezco = lista_excedentes[idx_ofrezco]
            cantidad_ofrezco = min(excedentes[recurso_ofrezco], cantidad_pido + 1)
            ofrezco = {recurso_ofrezco: cantidad_ofrezco}
            pido = {recurso_pido: cantidad_pido}
        elif necesidades and oro > 2:
            recurso_pido = list(necesidades.keys())[0]
            cantidad_pido = min(necesidades[recurso_pido], 2)
            precio = cantidad_pido * 2
            ofrezco = {"oro": min(precio, oro)}
            pido = {recurso_pido: cantidad_pido}
        elif excedentes:
            recurso_ofrezco = list(excedentes.keys())[0]
            cantidad_ofrezco = min(excedentes[recurso_ofrezco], 3)
            ofrezco = {recurso_ofrezco: cantidad_ofrezco}
            pido = {"oro": cantidad_ofrezco}
        else:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in ofrezco.items())
        pido_str = ", ".join(f"{c} {r}" for r, c in pido.items())

        cuerpo = (
            f"Hola {destinatario}, soy {self.alias}. "
            f"Te propongo un intercambio: "
            f"yo te doy {ofrezco_str} y tú me das {pido_str}. "
            f"¿Qué te parece? Si aceptas, dime y cerramos el trato."
        )

        return {
            "asunto": f"Propuesta: mi {ofrezco_str} por tu {pido_str}",
            "cuerpo": cuerpo,
            "_ofrezco": ofrezco,
            "_pido": pido,
        }

    def _generar_contraoferta(self, destinatario: str,
                              ofrecen: Dict[str, int],
                              necesidades: Dict, excedentes: Dict) -> Optional[Dict]:
        """Genera contraoferta cuando la oferta original no nos sirve."""
        pido = {}
        for rec, cant in ofrecen.items():
            if rec in necesidades:
                pido[rec] = min(cant, necesidades[rec])
        if not pido:
            return None

        ofrezco = {}
        cantidad_total_pido = sum(pido.values())
        cantidad_ofrecida = 0
        for rec, cant in excedentes.items():
            if cantidad_ofrecida >= cantidad_total_pido + 1:
                break
            c = min(cant, cantidad_total_pido + 1 - cantidad_ofrecida)
            ofrezco[rec] = c
            cantidad_ofrecida += c
        if not ofrezco:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in ofrezco.items())
        pido_str = ", ".join(f"{c} {r}" for r, c in pido.items())

        cuerpo = (
            f"Hola {destinatario}, soy {self.alias}. "
            f"Vi tu oferta pero no tengo lo que pides. "
            f"Te hago una contrapropuesta: "
            f"yo te doy {ofrezco_str} y tú me das {pido_str}. "
            f"¿Te interesa? Dime si aceptas."
        )

        return {
            "asunto": f"Contrapropuesta: mi {ofrezco_str} por tu {pido_str}",
            "cuerpo": cuerpo,
            "_ofrezco": ofrezco,
            "_pido": pido,
        }

    def _generar_texto_propuesta_ia(self, destinatario: str, necesidades: Dict,
                                     excedentes: Dict, oro: int) -> Optional[Dict]:
        """Usa IA para redactar la propuesta (la lógica es programática)."""
        propuesta = self._generar_propuesta(destinatario, necesidades, excedentes, oro)
        if not propuesta:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in propuesta["_ofrezco"].items())
        pido_str = ", ".join(f"{c} {r}" for r, c in propuesta["_pido"].items())

        prompt = (
            f"Genera un mensaje corto, amigable y natural para proponer un intercambio "
            f"de recursos en un juego.\n\n"
            f"DESTINATARIO: {destinatario}\nYO SOY: {self.alias}\n"
            f"OFREZCO: {ofrezco_str}\nPIDO: {pido_str}\n\n"
            f"El mensaje debe dejar MUY CLARO qué ofreces y qué pides, "
            f"con las cantidades exactas. Escríbelo como un humano, sin etiquetas "
            f"ni formatos especiales. Termina pidiendo confirmación.\n"
            f"Escribe SOLO el mensaje, nada más."
        )

        texto = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
        if texto and not texto.startswith("Error"):
            propuesta["cuerpo"] = texto
            propuesta["asunto"] = f"Intercambio: mi {ofrezco_str} por tu {pido_str}"
        return propuesta

    # =====================================================================
    # ACCIONES
    # =====================================================================

    def _enviar_carta(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        """Envía una carta de negociación."""
        exito = self.api.enviar_carta(self.alias, destinatario, asunto, cuerpo)
        self._log("ENVIO", f"Carta a {destinatario}", {
            "asunto": asunto,
            "cuerpo": cuerpo[:100] + "…" if len(cuerpo) > 100 else cuerpo,
            "exito": exito,
        })
        return exito

    def _enviar_paquete(self, destinatario: str, recursos: Dict[str, int]) -> bool:
        """Envía un paquete de recursos."""
        mis_recursos = self.info_actual.get("Recursos", {}) if self.info_actual else {}
        for rec, cant in recursos.items():
            if mis_recursos.get(rec, 0) < cant:
                self._log("ERROR", f"No hay suficiente {rec}",
                          {"necesario": cant, "disponible": mis_recursos.get(rec, 0)})
                return False

        exito = self.api.enviar_paquete(destinatario, recursos)
        self._log("INTERCAMBIO", f"Paquete a {destinatario}",
                  {"recursos": recursos, "exito": exito})

        if exito:
            self.intercambios_realizados.append({
                "tipo": "enviado",
                "destinatario": destinatario,
                "recursos": recursos,
                "timestamp": time.time(),
            })
        return exito

    def _responder_aceptacion(self, remitente: str, mensaje_original: str) -> bool:
        """Responde a una aceptación enviando los recursos acordados."""
        if remitente in self.acuerdos_pendientes and self.acuerdos_pendientes[remitente]:
            acuerdo = self.acuerdos_pendientes[remitente].pop(0)
            recursos_a_enviar = acuerdo.get("recursos_dar", {})

            if not self.acuerdos_pendientes[remitente]:
                del self.acuerdos_pendientes[remitente]

            if recursos_a_enviar:
                self._log("DECISION", f"Ejecutando acuerdo con {remitente}: envío {recursos_a_enviar}")
                self._actualizar_estado()
                if self._enviar_paquete(remitente, recursos_a_enviar):
                    return True
                else:
                    self._log("ERROR", f"No se pudo enviar paquete a {remitente}")

        self._log("INFO", f"Aceptación de {remitente} sin acuerdo pendiente registrado")
        return False

    # =====================================================================
    # LOOP PRINCIPAL
    # =====================================================================

    # ── helpers de filtrado rápido (sin IA) ────────────────────────────
    _RE_RECHAZO = _re.compile(
        r'no me interesa|no acepto|no puedo aceptar|rechaz|no,? gracias'
        r'|no tengo lo que|no necesito|no quiero|paso de',
        _re.IGNORECASE,
    )
    _RE_PROPUESTA = _re.compile(
        r'\b(ofrezco|te doy|te ofrezco|propongo|intercambi|cambi|pido|'
        r'necesito|quiero|busco|doy .* por|a cambio de|\d+\s+\w+.*por)',
        _re.IGNORECASE,
    )

    def _es_carta_sistema(self, remitente: str, mensaje: str) -> bool:
        """Devuelve True para notificaciones del sistema (no son propuestas)."""
        if remitente.lower() in ("sistema", "server", "butler"):
            return True
        if _re.match(r'(?i)^(has recibido|recursos generados|paquete|\s*$)', mensaje.strip()):
            return True
        return False

    def _es_rechazo_simple(self, mensaje: str) -> bool:
        """Detecta rechazos textuales sin necesidad de IA."""
        # Si contiene alguna propuesta de intercambio, NO es rechazo simple
        if self._RE_PROPUESTA.search(mensaje):
            return False
        return bool(self._RE_RECHAZO.search(mensaje))

    def _es_mensaje_corto_sin_propuesta(self, mensaje: str) -> bool:
        """Detecta mensajes muy cortos que no contienen propuesta."""
        limpio = mensaje.strip()
        if len(limpio) < 15:  # "ok", "gracias", "hola"
            return not self._RE_PROPUESTA.search(limpio)
        return False

    def _procesar_buzon(self, necesidades: Dict, excedentes: Dict) -> int:
        """Procesa todas las cartas del buzón usando IA para lenguaje natural."""
        buzon = self.info_actual.get("Buzon", {}) if self.info_actual else {}
        intercambios = 0
        cartas_procesadas = []

        for uid, carta in buzon.items():
            carta_id = carta.get("id", uid)
            if carta_id in self.cartas_vistas:
                cartas_procesadas.append(uid)
                continue
            self.cartas_vistas.add(carta_id)

            remitente = carta.get("remi", "Desconocido")
            mensaje = carta.get("cuerpo", "")
            asunto = carta.get("asunto", "")

            self._log("RECEPCION", f"Carta de {remitente}",
                      {"asunto": asunto, "mensaje": mensaje[:150]})

            # ── Filtro 0: cartas del Sistema → ignorar ──
            if self._es_carta_sistema(remitente, mensaje):
                self._log("INFO", f"Carta del sistema de '{remitente}' — ignorada")
                cartas_procesadas.append(uid)
                continue

            # ── Lista negra ──
            if remitente in self.lista_negra:
                self._log("ALERTA", f"Ignorando {remitente} (lista negra)")
                cartas_procesadas.append(uid)
                continue

            # ── Filtro 1: rechazos simples → no gastar IA ──
            if self._es_rechazo_simple(mensaje):
                self._log("INFO", f"Rechazo de {remitente} — ignorado (sin IA)")
                cartas_procesadas.append(uid)
                continue

            # ── Filtro 2: mensajes muy cortos sin propuesta ──
            if self._es_mensaje_corto_sin_propuesta(mensaje):
                self._log("INFO", f"Mensaje corto de {remitente} sin propuesta — ignorado")
                cartas_procesadas.append(uid)
                continue

            # ── Paso 1: ¿Aceptación? (IA para lenguaje natural) ──
            if self._es_aceptacion(mensaje):
                self._log("ANALISIS", f"{remitente} ACEPTA intercambio")
                if self._responder_aceptacion(remitente, mensaje):
                    intercambios += 1
                cartas_procesadas.append(uid)
                continue

            # ── Paso 2: ¿Estafa? ──
            if self._es_intento_robo(mensaje, remitente):
                cartas_procesadas.append(uid)
                continue

            # ── Paso 3: Análisis completo (regex fast-path + IA) ──
            analisis = self._analizar_mensaje_completo(
                remitente, mensaje, necesidades, excedentes)

            self._log("ANALISIS", f"Carta de {remitente} analizada", {
                "ofrecen": analisis.ofrecen, "piden": analisis.piden,
                "aceptar": analisis.aceptar, "razon": analisis.razon,
            })

            # ── Decisión: aceptar ──
            if analisis.aceptar and analisis.piden:
                # VALIDAR antes de enviar: ¿me piden cosas que realmente me sobran?
                self._actualizar_estado()
                mis_recursos = self.info_actual.get("Recursos", {}) if self.info_actual else {}
                # Recalcular excedentes con estado fresco
                estado_fresco = self._actualizar_estado()
                excedentes_frescos = estado_fresco.get("excedentes", {}) if estado_fresco else {}

                envio_valido = True
                recursos_a_enviar: Dict[str, int] = {}
                for rec, cant in analisis.piden.items():
                    if cant <= 0:
                        continue
                    disponible = mis_recursos.get(rec, 0)
                    excedente_rec = excedentes_frescos.get(rec, 0)
                    if disponible >= cant and excedente_rec >= cant:
                        recursos_a_enviar[rec] = cant
                    else:
                        self._log("ALERTA",
                                  f"No puedo enviar {cant} {rec} a {remitente}: "
                                  f"disponible={disponible}, excedente={excedente_rec}")
                        envio_valido = False

                if envio_valido and recursos_a_enviar:
                    self._log("DECISION", f"ACEPTO oferta de {remitente}, envío {recursos_a_enviar}")
                    if self._enviar_paquete(remitente, recursos_a_enviar):
                        ofrecen_str = ", ".join(f"{c} {r}" for r, c in analisis.ofrecen.items())
                        enviado_str = ", ".join(f"{c} {r}" for r, c in recursos_a_enviar.items())
                        self._enviar_carta(
                            remitente, f"Re: {asunto}",
                            f"Acepto el trato. Te he enviado {enviado_str}. "
                            f"Espero recibir {ofrecen_str} de tu parte. "
                            f"Saludos, {self.alias}",
                        )
                        intercambios += 1
                    else:
                        self._log("ERROR", f"No pude enviar paquete a {remitente}")
                elif not recursos_a_enviar:
                    self._log("DECISION",
                              f"Oferta de {remitente} parecía aceptable pero "
                              f"no hay recursos válidos para enviar — rechazada")
                else:
                    self._log("DECISION",
                              f"Oferta de {remitente} rechazada: "
                              f"no tengo suficientes excedentes para enviar {analisis.piden}")

            elif analisis.contraoferta and excedentes:
                if analisis.contraoferta_dar and analisis.contraoferta_pedir:
                    contra = self._generar_contraoferta(
                        remitente, analisis.ofrecen, necesidades, excedentes)
                    if contra:
                        self._log("DECISION", f"CONTRAOFERTA a {remitente}",
                                  {"ofrezco": contra["_ofrezco"], "pido": contra["_pido"]})
                        if self._enviar_carta(remitente, contra["asunto"], contra["cuerpo"]):
                            acuerdo = {
                                "recursos_dar": contra["_ofrezco"],
                                "recursos_pedir": contra["_pido"],
                                "timestamp": time.time(),
                            }
                            if remitente not in self.acuerdos_pendientes:
                                self.acuerdos_pendientes[remitente] = []
                            self.acuerdos_pendientes[remitente].append(acuerdo)
                else:
                    self._log("DECISION", f"RECHAZO oferta de {remitente} ({analisis.razon})")
                    self._enviar_carta(
                        remitente, f"Re: {asunto}",
                        f"Gracias por la oferta, {remitente}, pero por ahora "
                        f"no me conviene ese intercambio. Saludos, {self.alias}",
                    )

            elif analisis.ofrecen or analisis.piden:
                self._log("DECISION", f"RECHAZO oferta de {remitente} ({analisis.razon})")
                self._enviar_carta(
                    remitente, f"Re: {asunto}",
                    f"Gracias por la oferta, {remitente}, pero por ahora "
                    f"no me conviene ese intercambio. Saludos, {self.alias}",
                )
            else:
                self._log("INFO", f"Mensaje de {remitente} sin propuesta clara: {analisis.razon}")

            cartas_procesadas.append(uid)

        for uid in cartas_procesadas:
            self.api.eliminar_carta(uid)

        return intercambios

    def _enviar_propuestas(self, necesidades: Dict, excedentes: Dict, oro: int):
        """Envía propuestas a jugadores no contactados (máx 3/ronda)."""
        jugadores = self._obtener_jugadores_disponibles()
        jugadores = [j for j in jugadores if j not in self.contactados_esta_ronda]

        if not jugadores:
            self._log("INFO", "No hay jugadores a quienes enviar propuestas esta ronda")
            return

        jugadores = jugadores[:3]

        for jugador in jugadores:
            propuesta = self._generar_propuesta(jugador, necesidades, excedentes, oro)
            if propuesta is None:
                self._log("INFO", f"No se generó propuesta para {jugador}")
                continue

            if self._enviar_carta(jugador, propuesta["asunto"], propuesta["cuerpo"]):
                self.contactados_esta_ronda.append(jugador)
                acuerdo = {
                    "recursos_dar": propuesta["_ofrezco"],
                    "recursos_pedir": propuesta["_pido"],
                    "timestamp": time.time(),
                }
                if jugador not in self.acuerdos_pendientes:
                    self.acuerdos_pendientes[jugador] = []
                self.acuerdos_pendientes[jugador].append(acuerdo)
                self._log("INFO", f"Acuerdo pendiente con {jugador}: "
                          f"dar={propuesta['_ofrezco']}, pedir={propuesta['_pido']}")

            time.sleep(self.pausa_entre_acciones)

    def _ejecutar_ronda(self) -> bool:
        """Ejecuta una ronda completa de negociación."""
        console.rule(f"[bold]📍 RONDA — Modo: {self.modo.value}[/bold]")

        self.ronda_actual += 1

        # Limpiar acuerdos viejos (>5 min)
        ahora = time.time()
        for persona in list(self.acuerdos_pendientes.keys()):
            self.acuerdos_pendientes[persona] = [
                a for a in self.acuerdos_pendientes[persona]
                if ahora - a.get("timestamp", 0) < 300
            ]
            if not self.acuerdos_pendientes[persona]:
                del self.acuerdos_pendientes[persona]

        # 1. Actualizar estado
        estado = self._actualizar_estado()
        if not estado:
            self._log("ERROR", "No se pudo conectar a la API")
            return False

        necesidades = estado["necesidades"]
        excedentes = estado["excedentes"]
        oro = estado["oro"]
        objetivo_completado = estado["objetivo_completado"]

        self._log("INFO", "Estado actual", {
            "oro": oro, "necesidades": necesidades,
            "excedentes": excedentes, "objetivo_completado": objetivo_completado,
        })

        # 2. ¿Cambiar de modo?
        if objetivo_completado and self.modo == ModoAgente.CONSEGUIR_OBJETIVO:
            self._log("EXITO", "¡OBJETIVO COMPLETADO! → modo MAXIMIZAR ORO")
            self.modo = ModoAgente.MAXIMIZAR_ORO

        if self.modo == ModoAgente.MAXIMIZAR_ORO and not excedentes:
            self._log("EXITO", "No hay más excedentes para vender")
            self.modo = ModoAgente.COMPLETADO
            return True

        # 3. Procesar buzón
        self._log("INFO", "Procesando buzón…")
        intercambios = self._procesar_buzon(necesidades, excedentes)

        if intercambios > 0:
            self._log("EXITO", f"{intercambios} intercambio(s) realizado(s)")
            estado = self._actualizar_estado()
            necesidades = estado["necesidades"]
            excedentes = estado["excedentes"]

        # 4. Enviar propuestas
        if necesidades or (self.modo == ModoAgente.MAXIMIZAR_ORO and excedentes):
            self._log("INFO", "Enviando propuestas…")
            self._enviar_propuestas(necesidades, excedentes, estado["oro"])

        # 5. Reset contactados
        self.contactados_esta_ronda = []

        return estado["objetivo_completado"] and self.modo == ModoAgente.COMPLETADO

    def ejecutar(self, max_rondas: int = None):
        """Ejecuta el agente hasta completar el objetivo."""
        max_rondas = max_rondas or self.max_rondas

        console.print(Panel.fit(
            f"[bold]🤖 AGENTE NEGOCIADOR AUTÓNOMO[/bold]\n\n"
            f"  Alias:      [cyan]{self.alias}[/]\n"
            f"  Modelo:     [cyan]{self.ia.modelo}[/]\n"
            f"  Debug:      [{'green' if self.debug else 'dim'}]"
            f"{'ACTIVADO' if self.debug else 'desactivado'}[/]\n"
            f"  Max rondas: [cyan]{max_rondas}[/]",
            border_style="bright_blue",
        ))

        if not self.api.crear_alias(self.alias):
            console.print(f"[yellow]⚠ No se pudo crear el alias '{self.alias}', "
                          f"puede que ya exista.[/]")

        for ronda in range(1, max_rondas + 1):
            console.print(f"\n[bold cyan]🔄 RONDA {ronda}/{max_rondas}[/]")

            completado = self._ejecutar_ronda()
            if completado:
                break

            if ronda < max_rondas:
                console.print(
                    f"\n[dim]⏳ Esperando {self.pausa_entre_rondas}s para respuestas…[/]")
                time.sleep(self.pausa_entre_rondas)

        self._mostrar_resumen()

    # =====================================================================
    # VISUALIZACIÓN (rich)
    # =====================================================================

    def _mostrar_resumen(self):
        """Muestra resumen de la ejecución con rich."""
        estado = self._actualizar_estado()

        # ── Tabla de resumen ─────────────────────────────────────────────
        table = Table(title="📊 Resumen de Ejecución", border_style="bright_blue",
                      show_header=False, padding=(0, 2))
        table.add_column("Campo", style="bold")
        table.add_column("Valor")

        table.add_row("💰 Oro final", str(estado.get("oro", 0)))

        obj_ok = estado.get("objetivo_completado", False)
        table.add_row("🎯 Objetivo",
                      "[green]✅ COMPLETADO[/]" if obj_ok else "[red]❌ PENDIENTE[/]")

        if estado.get("necesidades"):
            table.add_row("📋 Aún falta", str(estado["necesidades"]))

        table.add_row("🔄 Intercambios", str(len(self.intercambios_realizados)))
        table.add_row("🛡️ Lista negra", str(len(self.lista_negra)))

        console.print()
        console.print(table)

        # ── Detalle de intercambios ──────────────────────────────────────
        if self.intercambios_realizados:
            console.print("\n[bold]Intercambios realizados:[/]")
            for i in self.intercambios_realizados:
                console.print(f"   → {i['destinatario']}: {i['recursos']}")

        if self.lista_negra:
            console.print("\n[bold]Lista negra:[/]")
            for p in self.lista_negra:
                console.print(f"   ⚠️  {p}")

    def ver_log(self, ultimos: int = 20):
        """Muestra las últimas entradas del log (compatibilidad)."""
        console.print(f"\n[bold]📜 LOG (últimas {ultimos} entradas):[/]")
        console.rule()
        # En el nuevo sistema, loguru ya se encarga. Mostramos mensaje.
        console.print("[dim]El log completo se encuentra en los handlers de loguru.[/]")
        console.print("[dim]Si debug está activo, todo se muestra en consola.[/]")
