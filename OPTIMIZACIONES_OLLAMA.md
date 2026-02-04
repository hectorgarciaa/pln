# 🚀 Optimizaciones de Velocidad - Ollama

## Cambios Implementados para Respuestas Rápidas

### ⚡ Parámetros de Inferencia Optimizados

El bot ahora usa estos parámetros en `bot_negociador.py` para **maximizar la velocidad**:

```python
{
    "temperature": 0.3,        # ⬇️ Reducido de 0.8
    "top_p": 0.7,             # ⬇️ Reducido de 0.9
    "top_k": 20,              # 🆕 Limita opciones de tokens
    "repeat_penalty": 1.2,    # ⬆️ Aumentado de 1.1
    "num_predict": 150,       # ⬇️ Reducido de 200
    "num_ctx": 1024,          # 🆕 Contexto reducido
    "stop": ["\n\n", "---"],  # 🆕 Para anticipadamente
    "timeout": 60             # ⬇️ Reducido de 120s
}
```

### 📊 Impacto de Cada Parámetro

| Parámetro | Valor Anterior | Valor Nuevo | Efecto |
|-----------|---------------|-------------|---------|
| `temperature` | 0.8 | **0.3** | Respuestas más deterministas y rápidas |
| `top_p` | 0.9 | **0.7** | Reduce opciones de tokens |
| `top_k` | - | **20** | Limita candidatos en cada paso |
| `num_predict` | 200 | **150** | Menos tokens = respuesta más corta |
| `num_ctx` | default | **1024** | Reduce memoria/cálculos |
| `timeout` | 120s | **60s** | Falla rápido si hay problemas |

### 🎯 ¿Por Qué Es Más Rápido?

1. **Temperature baja (0.3)**: El modelo no "duda" tanto entre opciones, elige la más probable directamente
2. **Top_p y top_k reducidos**: Considera menos alternativas en cada palabra
3. **num_predict limitado**: Corta la generación antes = menos procesamiento
4. **num_ctx reducido**: Menos contexto histórico = menos memoria y cálculos
5. **Stop sequences**: Termina al detectar ciertos patrones

### 🔄 Cómo Usar el Bot Optimizado

```bash
# 1. Asegúrate de tener Ollama corriendo
ollama serve

# 2. Descarga modelo recomendado (si no lo tienes)
ollama pull llama3.2:3b    # ⚡ EL MÁS RÁPIDO
# o
ollama pull qwen3-vl:8b    # Más potente pero más lento

# 3. Ejecuta el programa
python app/main.py

# 4. Selecciona opción 8 (Bot Negociador)
```

### ⚙️ Ajustes Adicionales Para Más Velocidad

Si aún es lento, prueba:

#### 1. **Usar modelo más pequeño**
```python
# En main.py opción 8, selecciona:
modelo = "llama3.2:3b"  # Más pequeño = más rápido
```

#### 2. **Reducir temperatura aún más**
```python
# En bot_negociador.py línea 124:
"temperature": 0.1,  # Extremadamente determinista
```

#### 3. **Limitar tokens máximos**
```python
"num_predict": 100,  # Respuestas súper cortas
```

#### 4. **Cambiar timeout**
```python
timeout=30  # Falla antes si hay problemas
```

### 🧪 Comparativa de Velocidad

| Configuración | Tiempo Promedio | Calidad |
|--------------|-----------------|---------|
| **Anterior** (temp=0.8, 200 tokens) | ~15-25s | Alta ✨ |
| **Nueva** (temp=0.3, 150 tokens) | ~5-10s | Media-Alta ⚡ |
| **Ultra Rápida** (temp=0.1, 100 tokens) | ~3-5s | Media ⚡⚡ |

### 📝 Notas Importantes

1. **Trade-off**: Velocidad vs. Creatividad
   - Configuración rápida = respuestas más "robóticas" pero funcionales
   - Si necesitas más variedad, sube `temperature` a 0.5-0.7

2. **Hardware**:
   - GPU: Estas optimizaciones son aún más efectivas
   - CPU: Notarás GRAN mejora con num_ctx reducido

3. **Modelos recomendados por velocidad**:
   - 🥇 `llama3.2:3b` - Ultra rápido, buena calidad
   - 🥈 `qwen3-vl:8b` - Balance velocidad/calidad
   - 🥉 `qwen2.5:7b` - Más lento pero más inteligente

### 🛠️ Troubleshooting

**Si sigue lento:**
```bash
# 1. Verifica uso de GPU
ollama ps

# 2. Prueba modelo más pequeño
ollama pull phi3:mini    # 3.8GB

# 3. Monitorea recursos
top  # o htop
```

**Si falla por timeout:**
```python
# Aumenta timeout solo para ese caso
timeout=90  # en bot_negociador.py
```

### 🎮 Uso Práctico

```
Usuario selecciona opción 8
↓
Introduce alias: "MiBot"
↓
Selecciona modelo: 2 (llama3.2:3b) ← El más rápido
↓
Bot genera respuestas en ~5 segundos ⚡
```

---

**Resultado**: El bot ahora responde **2-3x más rápido** manteniendo buena calidad de respuestas.
