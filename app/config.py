"""
Configuración centralizada del proyecto.

Usa pydantic BaseModel para validar tipos y valores por defecto.
Se puede sobreescribir cualquier campo al instanciar Settings().
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Tuple


class OllamaParams(BaseModel):
    """Parámetros de generación para Ollama."""
    temperature: float = 0.3
    top_p: float = 0.7
    top_k: int = 20
    repeat_penalty: float = 1.2
    num_predict: int = 100
    num_ctx: int = 2048
    num_gpu: int = 1
    num_thread: int = 8
    stop: List[str] = ["\n\n", "---"]


class Settings(BaseModel):
    """Configuración global del proyecto — todos los valores son validados."""

    # ── URLs ─────────────────────────────────────────────────────────────
    api_base_url: str = "http://127.0.0.1:7719"
    ollama_url: str = "http://127.0.0.1:11434"

    # ── Modelos de IA ────────────────────────────────────────────────────
    modelos_disponibles: Dict[str, Tuple[str, str]] = {
        "1": ("llama3.2:3b", "⚡⚡⚡ ULTRA RÁPIDO (3-5s)"),
        "2": ("qwen3-vl:8b", "⚡⚡ Balance (5-10s)"),
        "3": ("qwen2.5:7b", "⚡ Calidad (10-15s)"),
        "4": ("phi3:mini", "⚡⚡⚡ Muy rápido (3-5s)"),
        "5": ("qwen3:8b", "solo Texto"),
    }
    modelo_default: str = "qwen3:8b"

    # ── Parámetros de Ollama ─────────────────────────────────────────────
    ollama_params: OllamaParams = OllamaParams()

    # ── Control de pensamiento (modelos qwen3) ───────────────────────────
    think_timeout: int = Field(default=25, description="Máx. segundos de <think>")
    disable_think: bool = Field(default=False, description="Forzar /no_think")

    # ── Recursos conocidos en el juego ───────────────────────────────────
    recursos_conocidos: List[str] = [
        "oro", "madera", "piedra", "comida", "hierro", "trigo",
        "carbon", "agua", "plata", "cobre", "diamante", "lana",
        "tela", "cuero", "cristal", "acero", "ladrillos", "arroz",
        "queso", "pan", "leche", "carne", "pescado", "fruta",
        "verdura", "sal", "azucar", "miel", "vino", "cerveza",
    ]


# ── Instancia global (importar esta) ────────────────────────────────────
settings = Settings()

# ── Alias de compatibilidad (acceso directo sin cambiar los imports) ─────
API_BASE_URL = settings.api_base_url
OLLAMA_URL = settings.ollama_url
MODELOS_DISPONIBLES = settings.modelos_disponibles
MODELO_DEFAULT = settings.modelo_default
OLLAMA_PARAMS = settings.ollama_params.model_dump()
THINK_TIMEOUT = settings.think_timeout
DISABLE_THINK = settings.disable_think
RECURSOS_CONOCIDOS = settings.recursos_conocidos
