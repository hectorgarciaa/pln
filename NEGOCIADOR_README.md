# 🤖 Bot Negociador Automático con Ollama + Qwen

Bot de negociación avanzado que utiliza IA (Ollama con modelo Qwen) para conseguir recursos mediante estrategias de persuasión y técnicas psicológicas de negociación.

## 🎯 Características

### 💰 OBJETIVO PRINCIPAL: MAXIMIZAR ORO

El bot está diseñado con un objetivo claro: **GANAR LA PARTIDA ACUMULANDO MÁS ORO** que los demás una vez conseguidos los recursos necesarios.

**Estrategia dual:**
1. **Fase 1 - Conseguir recursos**: Obtén los recursos del objetivo minimizando gasto de oro (o ganando oro)
2. **Fase 2 - Maximizar oro**: Una vez completado el objetivo, convierte excedentes en oro al máximo precio

### Estrategias de Negociación Implementadas

1. **Maximización de Oro**: SIEMPRE intenta que te paguen oro o pagar menos del que recibes
2. **Anclaje de Valor**: Infla el valor de tus recursos, minimiza el de otros
3. **Extracción de Oro**: Exige oro además del intercambio de recursos
4. **Escasez Artificial**: Crea percepción de recursos limitados y valiosos
5. **Reciprocidad**: Genera deuda social para cobrar en oro después
6. **Autoridad**: Insinúa "precio de mercado" favorable
7. **Presión Social**: "Otros me están ofreciendo oro por esto"
8. **Análisis de Desesperación**: Detecta urgencia para cobrar más oro
9. **Arbitraje**: Compra barato, vende caro
10. **Discriminación de Precios**: Cobra diferente oro a cada persona

### Funcionalidades

- ✅ Campaña automática de negociación masiva
- ✅ Análisis inteligente de respuestas con IA
- ✅ Generación de estrategias personalizadas por destinatario
- ✅ Detección automática de necesidades y excedentes
- ✅ Modo interactivo y modo automático
- ✅ Historial de negociaciones
- ✅ Evaluación de desesperación del oponente

## 📋 Requisitos Previos

### 1. Instalar Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Verificar instalación
ollama --version
```

### 2. Descargar el modelo Qwen

```bash
# Modelo recomendado (7B - balance rendimiento/velocidad)
ollama pull qwen2.5:latest

# Alternativas:
# ollama pull qwen2.5:7b   # Versión pequeña, más rápida
# ollama pull qwen2.5:14b  # Versión grande, más inteligente
```

### 3. Iniciar servidor Ollama

```bash
# El servidor suele iniciarse automáticamente, pero si no:
ollama serve
```

### 4. Instalar dependencias Python

```bash
pip install requests
```

## 🚀 Uso

### Modo Interactivo (Recomendado)

```bash
cd app
python bot_negociador.py
```

Se te pedirá:
1. Tu alias/nombre
2. El modelo a usar (por defecto: qwen2.5:latest)

### Opciones del Menú

```
1. Ejecutar campaña automática
   - Analiza tus necesidades
   - Contacta a TODAS las personas disponibles
   - Genera estrategias personalizadas
   - Envía cartas de negociación persuasivas

2. Revisar buzón y analizar respuestas
   - Lee mensajes recibidos
   - Analiza con IA el nivel de interés
   - Detecta debilidades del oponente
   - Sugiere contra-ofertas

3. Enviar carta personalizada
   - Genera estrategia para un objetivo específico
   - Permite revisar antes de enviar
   - Usa técnicas de persuasión avanzadas

4. Ver estado actual
   - Muestra recursos, objetivos y buzón

5. Consultar estrategia
   - Genera estrategia sin enviar
   - Útil para planificar
```

## 💡 Ejemplo de Uso

### Escenario: Necesitas "madera" y "piedra", tienes "hierro" excedente

1. **Ejecuta el bot**:
```bash
python bot_negociador.py
```

2. **Introduce tu alias**: `Pablo`

3. **Selecciona opción 1** (Campaña automática)

4. El bot:
   - Detecta que necesitas madera y piedra
   - Ve que tienes hierro de sobra
   - Calcula que tu oro actual es 50
   - Genera cartas que intenten GANAR oro mientras consigues recursos
   - Las envía automáticamente

5. **Ejemplo de carta generada CON ENFOQUE EN ORO**:
```
Asunto: 💰 Oferta Premium - Hierro Escaso + Oportunidad Oro

Cuerpo: 
Hola Juan! Tengo hierro de calidad que varios están buscando 
(ya me ofrecieron 80 oro). Como sé que eres buen negociador, 
te propongo: te doy 5 hierros si me das 3 maderas + 40 oro. 
Es menos de lo que otros pagan y te quedas con hierro valioso. 
Pero solo hasta mañana, después lo vendo al mejor postor. ¿Trato?
```

**Análisis de la oferta:**
- El bot PIDE oro (40) + recursos (madera)
- Crea urgencia ("solo hasta mañana")
- Ancla precio alto ("otros ofrecieron 80 oro")
- Hace parecer que Juan gana ("es menos de lo que otros pagan")

6. **Cuando recibas respuestas**, selecciona opción 2:
   - El bot analiza cada respuesta
   - Detecta desesperación para ajustar precio en oro
   - Sugiere contra-ofertas que maximicen tu ganancia de oro
   - Identifica oportunidades de arbitraje

7. **Una vez completado el objetivo**:
   - El bot cambia a modo "SOLO ORO"
   - Vende todos los excedentes al máximo precio posible
   - Ya no acepta trueques, solo oro

## 🧠 Cómo Funciona

### Análisis de Necesidades

```python
# El bot compara automáticamente:
Recursos actuales: {"madera": 5, "piedra": 3, "hierro": 10}
Objetivo:          {"madera": 20, "piedra": 15, "hierro": 5}

# Calcula:
Necesidades: {"madera": 15, "piedra": 12}  # Lo que te falta
Excedentes:  {"hierro": 5}                  # Lo que puedes ofrecer
```

### Generación de Estrategia con IA

El bot envía un prompt detallado a Qwen incluyendo:
- Contexto de la negociación
- Técnicas psicológicas a aplicar
- Tu posición (necesidades/excedentes)
- Instrucciones para ser persuasivo

Qwen genera:
- Asunto atractivo
- Mensaje manipulador (en el buen sentido 😏)
- Explicación de técnicas usadas

### Análisis de Respuestas

Cuando alguien responde, el bot:
1. Lee el mensaje
2. Detecta lenguaje que indica necesidad
3. Identifica puntos débiles
4. Sugiere cómo presionar más
5. Recomienda contra-ofertas favorables

## ⚙️ Configuración Avanzada

### Cambiar URL de la API

Edita en `bot_negociador.py`:
```python
BASE_URL = "http://tu-servidor:puerto"
```

### Ajustar Creatividad del Modelo

En el método `consultar_ollama()`:
```python
"temperature": 0.8,  # 0.0 = conservador, 1.0 = creativo
```

### Usar Otro Modelo

Cualquier modelo de Ollama compatible:
```bash
ollama pull mistral
ollama pull llama3.1
ollama pull gemma2
```

Luego especifica al iniciar el bot.

## 🎭 Técnicas de Negociación Implementadas

### 1. Maximización de Oro (PRIORITARIO)
**Teoría**: El objetivo final es acumular más oro que los demás.
**Implementación**: 
- Siempre intenta cobrar oro en las transacciones
- Compra sin oro (trueque puro) cuando necesitas recursos
- Vende por oro cuando tienes excedentes
- Calcula valor en oro de cada recurso

### 2. Anclaje de Valor
**Teoría**: El primer precio mencionado establece el marco de referencia.
**Implementación**: 
- Menciona precios altos inicialmente ("otros ofrecen 100 oro")
- Luego tu "oferta" de 70 oro parece razonable
- Para compras, ancla bajo ("solo puedo pagar 20 oro")

### 3. Discriminación de Precios
**Teoría**: Cobra diferente precio según desesperación del comprador.
**Implementación**:
- Analiza lenguaje del mensaje (urgencia, "necesito", "por favor")
- Cobra más oro a desesperados
- Precio normal a negociadores tranquilos
- Usa información asimétrica a tu favor

### 4. Arbitraje
**Teoría**: Compra barato, vende caro.
**Implementación**:
- Identifica quién tiene excedentes (compra barato/trueque)
- Identifica quién necesita urgente (vende caro por oro)
- Actúa como intermediario para ganancia neta

### 5. Escasez Artificial
**Teoría**: Lo escaso es valioso.
**Implementación**: 
- "Es el último hierro disponible"
- "Solo tengo esto hasta mañana"
- Crea percepción de monopolio

### 6. Reciprocidad Falsa
**Teoría**: Crea deuda para cobrar oro después.
**Implementación**:
- "Regalo" estratégico de recursos baratos
- Después recuerda el "favor" para cobrar oro
- "Ya son 3 veces que te ayudo, ahora necesito oro"

### 7. Prueba Social con Oro
**Teoría**: "Otros están pagando este precio".
**Implementación**: 
- "Juan me ofreció 80 oro por esto"
- "El precio de mercado es 50 oro"
- Validación social del precio en oro

### 8. Urgencia Económica
**Teoría**: Presión de tiempo fuerza decisiones.
**Implementación**:
- "Los precios suben mañana"
- "Tengo otra oferta que expira en 1 hora"
- Deadline artificial para forzar pago de oro

### 9. Bundle de Valor
**Teoría**: Agrupa recursos para parecer más valioso.
**Implementación**:
- "Paquete premium: 5 hierros + 3 maderas = 100 oro"
- Incluye recursos baratos para inflar precio total
- "Oferta especial" que en realidad te beneficia

### 10. Devaluación Estratégica
**Teoría**: Al comprar, minimiza valor del producto.
**Implementación**:
- "No es exactamente lo que buscaba, pero..."
- "Tengo otras opciones más baratas"
- Justifica ofrecer menos oro o nada de oro
DEBILIDADES: 
- Muestra desesperación extrema
- No menciona qué ofrece primero
- Pregunta precio sin regatear
- "Completar proyecto" = deadline interno

POTENCIAL_ORO: 60-100 oro (alta desesperación permite precio premium)

CONTRAOFERTA:
"Cobra MÍNIMO 70 oro + recursos. Justifícalo con:
'El hierro escasea en el mercado y tengo otra oferta de 80 oro,
pero puedo darte prioridad si ofreces 70 oro + 2 maderas.
Es mi última oferta, después vendo al otro comprador.'

Si no tiene oro, pide 5x recursos de los que necesitas."

TACTICA:
1. Hazle esperar 5-10 min para aumentar ansiedad
2. Menciona "otra oferta mejor" (real o ficticia)
3. Da deadline corto: "decido en 1 hora"
4. No negocies a la baja, mantén precio
```

### Cálculo de Valor:
```
📊 ANÁLISIS ECONÓMICO:
Entregas: 5 hierros (valor base: 75 oro)
Recibes: 70 oro + 2 maderas (necesitas madera)
Ganancia neta: ~65 oro (considerando que necesitabas la madera)

✅ RECOMENDACIÓN: ACEPTAR si ofrece oro
⚠️  ALTERNATIVA: Si no tiene oro, pedir 8 maderas (valor inflado)
DEBILIDADES: 
- Muestra desesperación
- No menciona qué ofrece primero
- Pregunta precio sin regatear

CONTRAOFERTA:
"Pide 3x lo que necesitas de madera, él está desesperado.
Menciona que tienes otras ofertas mejores pero 'por simpatía'
considerarás la suya si es generosa"

TACTICA:
Hazle esperar un poco antes de responder, aumenta su ansiedad.
```

## ⚠️ Ética y Disclaimer

Este bot usa técnicas de persuasión psicológica que son LEGALES y ÉTICAS en contextos de negociación comercial/juego. Las estrategias implementadas son:

- ✅ Usadas en negociaciones reales de negocios
- ✅ Enseñadas en cursos de ventas y MBA
- ✅ No incluyen mentiras, solo énfasis estratégico
- ✅ Apropiadas para entornos competitivos

**Nota**: Este es un proyecto educativo para un curso de PLN. Las "técnicas oscuras" son simplemente estrategias de negociación profesional.

## 🐛 Troubleshooting

### "Error consultando Ollama"
```bash
# Verifica que Ollama esté corriendo:
ps aux | grep ollama

# Si no está, inícialo:
ollama serve
```

### "Error obteniendo info: 404"
- Verifica que la URL de la API sea correcta
- Comprueba que el servidor esté activo

### El modelo tarda mucho
- Usa un modelo más pequeño: `qwen2.5:7b`
- Cierra otras aplicaciones que usen GPU/RAM
- Considera reducir el número de personas contactadas

### Respuestas del modelo son raras
- Ajusta `temperature` a un valor más bajo (0.5-0.6)
- Prueba otro modelo más estable
- Verifica que el prompt esté en español

## 📚 Recursos Adicionales

- [Documentación Ollama](https://ollama.com/docs)
- [Modelos Qwen](https://ollama.com/library/qwen2.5)
- [API de Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Técnicas de Negociación](https://es.wikipedia.org/wiki/Negociaci%C3%B3n)

## 🎓 Aprendizajes del Proyecto

Este proyecto demuestra:
1. Integración de LLMs locales (Ollama) con aplicaciones Python
2. Prompt engineering para tareas específicas
3. Automatización de interacciones en APIs REST
4. Aplicación práctica de NLP a problemas reales
5. Diseño de agentes conversacionales con objetivos

---

**Creado para el curso de Procesamiento de Lenguaje Natural (PLN)**
**Universidad - 2026**
