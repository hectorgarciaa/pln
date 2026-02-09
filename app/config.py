"""
Configuración centralizada del proyecto.
"""

# URLs de las APIs
API_BASE_URL = "http://127.0.0.1:7719"
OLLAMA_URL = "http://127.0.0.1:11434"

# Modelos de IA disponibles
MODELOS_DISPONIBLES = {
    "1": ("llama3.2:3b", "⚡⚡⚡ ULTRA RÁPIDO (3-5s)"),
    "2": ("qwen3-vl:8b", "⚡⚡ Balance (5-10s)"),
    "3": ("qwen2.5:7b", "⚡ Calidad (10-15s)"),
    "4": ("phi3:mini", "⚡⚡⚡ Muy rápido (3-5s)"),
    "5": ("qwen3:8b", "solo Texto"),
}

MODELO_DEFAULT = "qwen3:8b"

# Parámetros de Ollama optimizados para velocidad
OLLAMA_PARAMS = {
    "temperature": 0.3,
    "top_p": 0.7,
    "top_k": 20,
    "repeat_penalty": 1.2,
    "num_predict": 100,      
    "num_ctx": 2048,         
    "num_gpu": 1,            
    "num_thread": 8,         
    "stop": ["\n\n", "---"],
}

# Control de pensamiento para modelos qwen3
# Máx. segundos que se permite al modelo "pensar" (bloques <think>)
THINK_TIMEOUT = 10
# Si True, desactiva el pensamiento en modelos que lo soportan (añade /no_think)
DISABLE_THINK = False

# Recursos conocidos en el juego (usado para generar propuestas)
RECURSOS_CONOCIDOS = [
    'oro', 'madera', 'piedra', 'comida', 'hierro', 'trigo',
    'carbon', 'agua', 'plata', 'cobre', 'diamante', 'lana',
    'tela', 'cuero', 'cristal', 'acero', 'ladrillos', 'arroz',
    'queso', 'pan', 'leche', 'carne', 'pescado', 'fruta',
    'verdura', 'sal', 'azucar', 'miel', 'vino', 'cerveza'
]

# NOTA: La detección de estafas, aceptaciones y rechazos se hace
# completamente mediante el modelo de IA (Ollama), sin listas de palabras.
