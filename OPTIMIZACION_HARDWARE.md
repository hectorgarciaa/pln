# 🚀 Optimización para Hardware Lento

## 🔧 Problema: Ollama es muy lento (timeouts)

### Soluciones Rápidas

#### 1. Usar modelo más pequeño (RECOMENDADO)
```bash
# Descargar modelo ligero (más rápido)
ollama pull qwen2.5:3b    # 1.9 GB - MUY RÁPIDO

# O el mediano
ollama pull qwen2.5:7b    # 4.7 GB - Balance
```

Luego en el bot, cuando pregunte el modelo, escribe:
```
¿Qué modelo usar? [qwen2.5:7b]: qwen2.5:3b
```

#### 2. Configurar variables de entorno de Ollama
```bash
# En una terminal (antes de 'ollama serve'):
export OLLAMA_NUM_PARALLEL=1        # Solo 1 request a la vez
export OLLAMA_MAX_LOADED_MODELS=1   # Solo 1 modelo en memoria
export OLLAMA_FLASH_ATTENTION=1     # Optimización de memoria

# Luego iniciar Ollama:
ollama serve
```

#### 3. Limitar uso de CPU/GPU
```bash
# Si tienes GPU pero es lenta:
export OLLAMA_NUM_GPU=0   # Forzar CPU (a veces más estable)

# O limitar capas en GPU:
export OLLAMA_NUM_GPU=10  # Solo 10 capas en GPU
```

#### 4. El bot ya funciona sin IA
El bot ahora **genera mensajes inteligentes** incluso si Ollama es lento:
- Usa tus necesidades reales
- Genera ofertas específicas
- Detecta robos por palabras clave
- Solo usa IA para casos complejos

### Ejemplo de mensajes SIN IA del bot actualizado:

**Necesitas trigo (5):**
```
Asunto: 💰 Necesito trigo - Oferta en oro
Cuerpo: Hola Juan! Busco 5 de trigo. Tengo 4 madera para 
intercambiar + oro si hace falta. ¿Tienes disponible? 
Responde con tu precio.
```

**Tienes excedente de madera (4):**
```
Asunto: 💎 Vendo madera - Solo Oro
Cuerpo: Hola Pedro! Vendo 4 madera. Precio: 40 oro (negociable). 
Varios interesados, responde pronto si quieres.
```

## 📊 Comparativa de Modelos

| Modelo | Tamaño | Velocidad | Calidad | Recomendado para |
|--------|--------|-----------|---------|------------------|
| qwen2.5:3b | 1.9 GB | ⚡⚡⚡ Muy rápido | ⭐⭐⭐ Bueno | CPU lenta, portátiles |
| qwen2.5:7b | 4.7 GB | ⚡⚡ Rápido | ⭐⭐⭐⭐ Muy bueno | PC normal, GPU básica |
| qwen2.5:14b | 8.9 GB | ⚡ Normal | ⭐⭐⭐⭐⭐ Excelente | GPU potente |

## 🎯 Configuración Óptima por Hardware

### Laptop/CPU débil
```bash
ollama pull qwen2.5:3b
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_NUM_GPU=0
ollama serve
```

### PC normal
```bash
ollama pull qwen2.5:7b
export OLLAMA_NUM_PARALLEL=2
ollama serve
```

### PC potente con GPU
```bash
ollama pull qwen2.5:14b
ollama serve
```

## 🔍 Verificar rendimiento

```bash
# Test rápido de velocidad:
time ollama run qwen2.5:3b "Hola, responde en 5 palabras"

# Si tarda más de 10 segundos, tu hardware es lento
# Usa qwen2.5:3b obligatoriamente
```

## ⚡ El Bot Optimizado

Cambios aplicados:
- ✅ Timeout aumentado a 120s
- ✅ Genera mensajes inteligentes sin IA si es lenta
- ✅ Indicador de progreso "⏳ Consultando IA..."
- ✅ Detección de robos por palabras clave (rápido)
- ✅ Solo usa IA para casos complejos
- ✅ Limita respuestas a 300 tokens (más rápido)

**Ahora funciona bien en hardware lento!** 🎉
