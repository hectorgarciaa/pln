"""
Servicio de análisis de mensajes de negociación usando salida estructurada.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.settings import ModelSettings

from ..core.config import OLLAMA_URL


class RespuestaUnificada(BaseModel):
    """Respuesta única de la IA: aceptación + extracción en 1 llamada."""

    es_aceptacion: bool = False
    ofrecen: Dict[str, int] = Field(default_factory=dict)
    piden: Dict[str, int] = Field(default_factory=dict)
    razon: str = ""

    from pydantic import field_validator

    @field_validator("ofrecen", "piden", mode="before")
    @classmethod
    def _coerce_to_dict(cls, v) -> Dict[str, int]:
        if isinstance(v, dict):
            return {str(k): int(val) for k, val in v.items() if val is not None}
        return {}


class AnalisisMensajesService:
    """Encapsula la llamada al modelo para analizar cartas."""

    def __init__(self, modelo: str):
        ollama_base = OLLAMA_URL.rstrip("/") + "/v1"
        ai_provider = OllamaProvider(base_url=ollama_base)
        ai_model = OpenAIChatModel(modelo, provider=ai_provider)
        ai_settings = ModelSettings(
            temperature=0.3,
            top_p=0.7,
            max_tokens=512,
        )

        self._agente = Agent(
            ai_model,
            output_type=RespuestaUnificada,
            system_prompt=(
                "Eres un analizador de mensajes en un juego de intercambio de recursos.\n"
                "Analiza el mensaje y responde con TODOS estos campos:\n\n"
                "1) es_aceptacion: ¿El mensaje ACEPTA un trato previo?\n"
                "   - SÍ si contiene frases como: 'acepto el trato', 'trato hecho',\n"
                "     'te he enviado', 'cerramos el trato', 'acepto tu propuesta',\n"
                "     'de acuerdo', 'perfecto, te envío'.\n"
                "   - NO si es: rechazo, propuesta nueva, 'si aceptas dime',\n"
                "     'no me conviene', 'por ahora no', 'no me interesa'.\n\n"
                "2) ofrecen / piden: EXTRAER recursos del mensaje.\n"
                '   - "ofrecen" = lo que el remitente ofrece DAR (lo que yo recibiría).\n'
                '   - "piden" = lo que el remitente quiere RECIBIR (lo que yo daría).\n'
                "   - Solo recursos y cantidades EXPLÍCITOS. NO inventes.\n"
                "   - Si hay ambigüedad o falta cantidad explícita, omítelo.\n"
                "   - Normaliza recursos en minúsculas y sin espacios extra.\n"
                "   - Rechazo, saludo o no-propuesta → ofrecen={}, piden={}.\n\n"
                "3) razon: explicación breve de tu análisis.\n\n"
                'Ejemplo: "yo te doy 2 madera y tú me das 3 piedra"\n'
                "→ es_aceptacion=false, "
                'ofrecen={"madera": 2}, piden={"piedra": 3}'
            ),
            model_settings=ai_settings,
            retries=2,
        )

    @staticmethod
    def _resumen_contexto(recursos: Optional[Dict[str, int]], limite: int = 8) -> str:
        if not recursos:
            return "ninguno"
        items = sorted(recursos.items(), key=lambda kv: (-kv[1], kv[0]))[:limite]
        return ", ".join(f"{rec}:{cant}" for rec, cant in items)

    def analizar(
        self,
        remitente: str,
        mensaje: str,
        asunto: str = "",
        necesidades: Optional[Dict[str, int]] = None,
        excedentes: Optional[Dict[str, int]] = None,
        modo_agente: str = "",
    ) -> RespuestaUnificada:
        prompt_usuario = (
            "Analiza este mensaje y produce salida estructurada.\n\n"
            f"REMITENTE: {remitente}\n"
            f"ASUNTO: {asunto or '(sin asunto)'}\n"
            f"MODO_AGENTE: {modo_agente or '(desconocido)'}\n"
            f"NECESIDADES_PRINCIPALES: {self._resumen_contexto(necesidades)}\n"
            f"EXCEDENTES_PRINCIPALES: {self._resumen_contexto(excedentes)}\n\n"
            "MENSAJE:\n"
            f"{mensaje}\n\n"
            "Recuerda: no inventes cantidades ni recursos."
        )
        result = self._agente.run_sync(prompt_usuario)
        return result.output
