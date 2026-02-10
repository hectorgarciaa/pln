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
import time
from enum import Enum
from typing import Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import RECURSOS_CONOCIDOS, MODELO_DEFAULT
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
    """Respuesta de la IA al analizar un mensaje de negociación."""
    ofrecen: Dict[str, int] = Field(default_factory=dict)
    piden: Dict[str, int] = Field(default_factory=dict)
    aceptar: bool = False
    razon: str = ""
    contraoferta: bool = False
    contraoferta_dar: Dict[str, int] = Field(default_factory=dict)
    contraoferta_pedir: Dict[str, int] = Field(default_factory=dict)


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
        # Nivel DEBUG solo si se pidió explícitamente
        if not debug:
            logger.disable("negociador")

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
        """Usa IA para detectar si un mensaje es un intento de estafa."""
        prompt = (
            f'Analiza si este mensaje de un juego de intercambio de recursos '
            f'es un intento de ESTAFA o ROBO.\n\n'
            f'MENSAJE DE "{remitente}": "{mensaje}"\n\n'
            f'Señales de estafa: pedir que envíes recursos primero sin garantía, '
            f'prometer cosas imposibles, usar urgencia o presión, ofrecer cosas '
            f'gratis sin motivo, mencionar bugs o errores del sistema, '
            f'pedir confianza ciega, etc.\n\n'
            f'Responde SOLO con un JSON: {{"es_estafa": true/false, "razon": "explicación breve"}}\n'
            f'No escribas nada más.'
        )

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
        datos = self._parsear_json_ia(respuesta)
        if datos is None:
            return False

        try:
            resultado = RespuestaEstafa(**datos)
        except ValidationError as e:
            self._log("ERROR", f"Respuesta IA inválida (estafa): {e}")
            return False

        if resultado.es_estafa:
            self._log("ALERTA", f"IA detecta posible estafa de {remitente}",
                      {"razon": resultado.razon})
            if remitente not in self.lista_negra:
                self.lista_negra.append(remitente)
            return True

        return False

    def _es_aceptacion(self, mensaje: str) -> bool:
        """Usa IA para detectar si un mensaje acepta un intercambio."""
        prompt = (
            f'En un juego de intercambio de recursos, analiza si este mensaje '
            f'es una ACEPTACIÓN de un trato propuesto.\n\n'
            f'MENSAJE: "{mensaje}"\n\n'
            f'Una aceptación puede ser directa ("acepto", "trato hecho") o indirecta '
            f'("te envío los recursos", "perfecto").\n'
            f'Un rechazo es lo contrario ("no me interesa", "no acepto", "muy caro").\n'
            f'Si es una propuesta nueva (no una respuesta a un trato), NO es una aceptación.\n\n'
            f'Responde SOLO con un JSON: {{"es_aceptacion": true/false, "razon": "explicación breve"}}\n'
            f'No escribas nada más.'
        )

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
        datos = self._parsear_json_ia(respuesta)
        if datos is None:
            return False

        try:
            resultado = RespuestaAceptacion(**datos)
            return resultado.es_aceptacion
        except ValidationError as e:
            self._log("ERROR", f"Respuesta IA inválida (aceptación): {e}")
            return False

    def _analizar_mensaje_completo(self, remitente: str, mensaje: str,
                                   necesidades: Dict, excedentes: Dict) -> RespuestaAnalisis:
        """Analiza completamente un mensaje con IA y devuelve modelo validado."""
        mis_recursos = self.info_actual.get("Recursos", {}) if self.info_actual else {}

        prompt = (
            f'Eres un asistente de un juego de intercambio de recursos. '
            f'Analiza este mensaje.\n\n'
            f'MENSAJE DE "{remitente}": "{mensaje}"\n\n'
            f'MI SITUACIÓN:\n'
            f'- Recursos que tengo: {json.dumps(mis_recursos)}\n'
            f'- Recursos que NECESITO conseguir: {json.dumps(necesidades)}\n'
            f'- Recursos que me SOBRAN y puedo dar: {json.dumps(excedentes)}\n\n'
            f'Determina:\n'
            f'1. ¿Qué recursos OFRECE el remitente?\n'
            f'2. ¿Qué recursos PIDE el remitente?\n'
            f'3. ¿Debo aceptar? Solo si me ofrecen algo que NECESITO y piden algo que me SOBRA.\n'
            f'4. Si no, ¿sugiero contraoferta con mis excedentes?\n\n'
            f'Responde SOLO con un JSON:\n'
            f'{{"ofrecen": {{"recurso": cantidad}}, "piden": {{"recurso": cantidad}}, '
            f'"aceptar": true/false, "razon": "breve", '
            f'"contraoferta": true/false, '
            f'"contraoferta_dar": {{"recurso": cantidad}}, '
            f'"contraoferta_pedir": {{"recurso": cantidad}}}}'
        )

        respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
        datos = self._parsear_json_ia(respuesta)

        if datos:
            try:
                return RespuestaAnalisis(**datos)
            except ValidationError as e:
                self._log("ERROR", f"Respuesta IA inválida (análisis): {e}")

        # Fallback seguro
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

    def _generar_texto_propuesta_ia(self, destinatario: str, necesidades: Dict,
                                     excedentes: Dict, oro: int) -> Optional[Dict]:
        """Usa IA para redactar la propuesta (la lógica es programática)."""
        propuesta = self._generar_propuesta(destinatario, necesidades, excedentes, oro)
        if not propuesta:
            return None

        ofrezco_str = ", ".join(f"{c} {r}" for r, c in propuesta["_ofrezco"].items())
        pido_str = ", ".join(f"{c} {r}" for r, c in propuesta["_pido"].items())

        prompt = (
            f"Genera un mensaje corto y amigable para proponer un intercambio.\n\n"
            f"DESTINATARIO: {destinatario}\nYO SOY: {self.alias}\n"
            f"OFREZCO: {ofrezco_str}\nPIDO: {pido_str}\n\n"
            f"El mensaje debe incluir [OFREZCO] y [PIDO] con las cantidades "
            f"y terminar diciendo que responda con [ACEPTO].\nEscribe SOLO el mensaje."
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

    def _procesar_buzon(self, necesidades: Dict, excedentes: Dict) -> int:
        """Procesa todas las cartas del buzón usando IA."""
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

            # ── Lista negra ──
            if remitente in self.lista_negra:
                self._log("ALERTA", f"Ignorando {remitente} (lista negra)")
                cartas_procesadas.append(uid)
                continue

            # ── Paso 1: ¿Estafa? ──
            if self._es_intento_robo(mensaje, remitente):
                cartas_procesadas.append(uid)
                continue

            # ── Paso 2: ¿Aceptación? ──
            if self._es_aceptacion(mensaje):
                self._log("ANALISIS", f"IA detecta que {remitente} ACEPTA intercambio")
                if self._responder_aceptacion(remitente, mensaje):
                    intercambios += 1
                cartas_procesadas.append(uid)
                continue

            # ── Paso 3: Análisis completo ──
            analisis = self._analizar_mensaje_completo(remitente, mensaje, necesidades, excedentes)

            self._log("ANALISIS", f"IA analizó carta de {remitente}", {
                "ofrecen": analisis.ofrecen, "piden": analisis.piden,
                "aceptar": analisis.aceptar, "razon": analisis.razon,
            })

            if analisis.aceptar and analisis.piden:
                self._log("DECISION", f"ACEPTO oferta de {remitente}, envío {analisis.piden}")
                if self._enviar_paquete(remitente, analisis.piden):
                    self._enviar_carta(
                        remitente, f"Re: {asunto}",
                        f"[ACEPTO] Trato hecho! Te envié {analisis.piden}. "
                        f"Espero mis {analisis.ofrecen}. Saludos, {self.alias}",
                    )
                    intercambios += 1
                else:
                    self._log("ERROR", f"No pude enviar paquete a {remitente}")

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
                        f"No me interesa ese intercambio por ahora. Saludos, {self.alias}",
                    )

            elif analisis.ofrecen or analisis.piden:
                self._log("DECISION", f"RECHAZO oferta de {remitente} ({analisis.razon})")
                self._enviar_carta(
                    remitente, f"Re: {asunto}",
                    f"No me interesa ese intercambio por ahora. Saludos, {self.alias}",
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
