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
}

MODELO_DEFAULT = "qwen3-vl:8b"

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

# Recursos conocidos en el juego
RECURSOS_CONOCIDOS = [
    'oro', 'madera', 'piedra', 'comida', 'hierro', 'trigo',
    'carbon', 'agua', 'plata', 'cobre', 'diamante', 'lana',
    'tela', 'cuero', 'cristal', 'acero'
]

# Detección de robos
PALABRAS_SOSPECHOSAS = [
    'gratis', 'regalo', 'error del sistema', 'bug', 'primero',
    'confía', 'urgente ahora', 'última oportunidad', 'solo hoy',
    'envía ya', 'transfiero después', 'prometo'
]

PALABRAS_ACEPTACION = [
    'acepto', 'trato hecho', 'de acuerdo', 'ok', 'vale', 'perfecto',
    'hecho', 'me parece bien', 'aceptado', 'sí', 'claro', 'por supuesto',
    'enviado', 'te envío', 'ahí va', 'recibido', 'gracias por'
]

PALABRAS_RECHAZO = [
    'no acepto', 'no me interesa', 'no gracias', 'rechazo', 'no puedo',
    'muy caro', 'demasiado', 'no tengo', 'no quiero'
]
