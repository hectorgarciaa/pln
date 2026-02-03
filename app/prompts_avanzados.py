"""
Ejemplos de Prompts Avanzados para el Bot Negociador

Este archivo contiene prompts especializados que puedes integrar
para mejorar aún más las capacidades del bot.
"""

# ============================================================================
# PROMPT: ANÁLISIS DE PERSONALIDAD
# ============================================================================
PROMPT_ANALISIS_PERSONALIDAD = """Analiza el estilo de comunicación del siguiente mensaje para identificar el tipo de personalidad del negociador y ajustar la estrategia:

MENSAJE: {mensaje}

Identifica:
1. TIPO DE PERSONALIDAD:
   - Analítico: Usa datos, lógico, detallista
   - Conductor: Directo, orientado a resultados
   - Expresivo: Emocional, entusiasta
   - Amable: Colaborativo, evita conflictos

2. MOTIVADORES PRINCIPALES:
   - Lógica/Datos
   - Poder/Control
   - Reconocimiento social
   - Seguridad/Estabilidad
   - Beneficio económico

3. PUNTOS DE PRESIÓN:
   - ¿Qué le hace tomar decisiones rápidas?
   - ¿Qué argumentos le persuaden más?

4. ESTRATEGIA AJUSTADA:
   - Tono a usar (formal/informal/técnico)
   - Tipo de argumentos (lógicos/emocionales/sociales)
   - Velocidad de negociación (rápida/pausada)

RESPONDE EN FORMATO:
PERSONALIDAD: [tipo]
MOTIVADORES: [lista]
PRESIÓN: [técnicas específicas]
ESTRATEGIA: [cómo negociar con esta persona]
"""

# ============================================================================
# PROMPT: GENERACIÓN DE OFERTAS ASIMÉTRICAS
# ============================================================================
PROMPT_OFERTA_ASIMETRICA = """Crea una oferta que PAREZCA equilibrada pero te beneficie desproporcionadamente.

TU SITUACIÓN:
- Necesitas: {necesidades}
- Puedes ofrecer: {excedentes}
- Objetivo: Maximizar ganancia

TÉCNICAS A USAR:
1. **Bundling**: Agrupa recursos de bajo valor para ti como "paquete valioso"
2. **Anclaje de valor**: Menciona un "valor de mercado" inflado de lo que ofreces
3. **Descuento ficticio**: Ofrece un "descuento especial" desde un precio inflado
4. **Garantías vagas**: Promete "apoyo futuro" o "prioridad en futuros tratos"
5. **Urgencia artificial**: Limita el tiempo de la oferta
6. **Dilución de pérdidas**: Divide lo que pides en "pequeños pagos"

GENERA UNA OFERTA que:
- Pida {multiplicador}x lo que necesitas
- Ofrezca {fraccion}x de lo que estás dispuesto a dar
- Use lenguaje que haga parecer el trato justo
- Incluya elementos no cuantificables (favores, prioridad, etc.)

FORMATO:
OFERTA: [texto de la propuesta]
VALOR_REAL_TU: [cuánto ganas realmente]
VALOR_PERCIBIDO_ELLOS: [cuánto creen que ganan]
RATIO_BENEFICIO: [tu_beneficio / su_beneficio]
"""

# ============================================================================
# PROMPT: COUNTER-OFFER AGRESIVO
# ============================================================================
PROMPT_COUNTER_AGRESIVO = """Has recibido una contra-oferta. Genera una respuesta que PAREZCA considerar su propuesta pero realmente mejore tu posición.

SU OFERTA: {oferta_recibida}

TÉCNICAS DE RESPUESTA:
1. **Falsa consideración**: "He analizado tu propuesta cuidadosamente..."
2. **Reframe**: Reformula su oferta para que parezca menos atractiva
3. **Nuevo anclaje**: Introduce un "dato nuevo" que justifique pedir más
4. **Concesión falsa**: "Renuncia" a algo que nunca ibas a dar
5. **Presión de alternativas**: Menciona "otra oferta muy interesante que tengo"
6. **Deadline**: Introduce urgencia para que decida rápido

GENERA:
RESPUESTA: [mensaje que parezca constructivo pero presione más]
NUEVA_DEMANDA: [pide más de lo original]
JUSTIFICACIÓN: [razón aparentemente lógica]
TÉCNICA_USADA: [explica la manipulación]
"""

# ============================================================================
# PROMPT: DETECCIÓN DE BLUFF
# ============================================================================
PROMPT_DETECTAR_BLUFF = """Analiza este mensaje para detectar si están BLUFFEANDO (mintiendo sobre su posición):

MENSAJE: {mensaje}

INDICADORES DE BLUFF:
1. **Sobre-justificación**: Explican demasiado por qué no pueden hacer algo
2. **Lenguaje absoluto**: "Nunca", "imposible", "no tengo nada de eso"
3. **Evitar especificidad**: Respuestas vagas cuando preguntas detalles
4. **Presión inversa**: Intentan que TÚ te apures en decidir
5. **Deflexión**: Cambian de tema cuando preguntas algo directo
6. **Sobre-emocionalidad**: Reacciones exageradas

ANÁLISIS:
PROBABILIDAD_BLUFF: [0-100%]
INDICADORES_DETECTADOS: [lista]
SU_POSICION_REAL: [estimación de lo que realmente tienen/quieren]
COMO_EXPLOTAR: [cómo usar esta información]
PREGUNTA_TRAMPA: [pregunta para confirmar el bluff]
"""

# ============================================================================
# PROMPT: CIERRE AGRESIVO
# ============================================================================
PROMPT_CIERRE_AGRESIVO = """La negociación ha durado suficiente. Genera un mensaje de CIERRE que fuerce una decisión favorable.

CONTEXTO: {contexto_negociacion}

TÉCNICAS DE CIERRE:
1. **Ultimátum suave**: "Esta es mi última oferta, después busco otras opciones"
2. **Beneficio vs pérdida**: Enfatiza lo que PIERDE si no acepta
3. **Escasez extrema**: "Otra persona está interesada en esto"
4. **Ahora o nunca**: "Solo puedo garantizar esto si decides HOY"
5. **Compromiso forzado**: "Para seguir hablando necesito que comprometas [algo pequeño]"
6. **Resumen sesgado**: Resume la negociación enfatizando tu generosidad

GENERA UN CIERRE que:
- Parezca razonable pero presione fuerte
- Use FOMO (fear of missing out)
- Incluya un deadline concreto
- Haga que rechazar se sienta como una pérdida

FORMATO:
MENSAJE_CIERRE: [texto del mensaje]
DEADLINE: [tiempo límite]
PLAN_B: [qué hacer si rechazan]
"""

# ============================================================================
# PROMPT: CONSTRUCCIÓN DE RAPPORT
# ============================================================================
PROMPT_CONSTRUIR_RAPPORT = """Genera un mensaje inicial que construya RAPPORT (conexión personal) antes de negociar.

DESTINATARIO: {destinatario}
OBJETIVO_FINAL: {objetivo}

TÉCNICAS:
1. **Puntos en común**: Inventa conexiones plausibles
2. **Halago sutil**: Reconoce algo "que has oído" de ellos
3. **Vulnerabilidad falsa**: Comparte un "problema" menor para generar confianza
4. **Historia compartida**: Crea narrativa de "estamos en el mismo equipo"
5. **Humor apropiado**: Comentario ligero que reduzca tensión
6. **Personalización**: Usa detalles específicos (aunque sean inventados)

GENERA:
MENSAJE_INICIAL: [texto que construya conexión]
TRANSICION: [cómo pasar de rapport a negociación]
TONO: [amigable pero no débil]
"""

# ============================================================================
# PROMPT: RECUPERACIÓN DE NEGOCIACIÓN FALLIDA
# ============================================================================
PROMPT_RECUPERAR_NEGOCIACION = """Una negociación ha ido mal. Genera una estrategia de RECUPERACIÓN.

QUÉ PASÓ: {contexto_fallo}

OPCIONES DE RECUPERACIÓN:
1. **Disculpa estratégica**: "Malinterpreté tus necesidades..."
2. **Nueva información**: "Acabo de conseguir acceso a..."
3. **Cambio de términos**: "He repensado mi posición..."
4. **Tercero ficticio**: "He hablado con alguien que sugirió..."
5. **Time-out táctico**: Espera y vuelve con "nueva perspectiva"
6. **Redefinición de beneficio**: Ofrece algo completamente diferente

GENERA:
MENSAJE_RECUPERACION: [cómo reabrir la conversación]
NUEVA_PROPUESTA: [oferta modificada]
APRENDIZAJE: [qué evitar en el futuro]
"""

# ============================================================================
# PROMPT: MULTI-PARTY NEGOTIATION
# ============================================================================
PROMPT_NEGOCIACION_MULTIPLE = """Estás negociando con MÚLTIPLES personas simultáneamente. Genera estrategia de orquestación.

PARTES: {lista_partes}
TUS_NECESIDADES: {necesidades}

ESTRATEGIA MULTI-PARTY:
1. **Información asimétrica**: Da información diferente a cada uno
2. **Competición artificial**: "Fulano me ofreció X, ¿tú puedes mejorar?"
3. **Coaliciones temporales**: Alianza con uno contra otro
4. **Arbitraje falso**: "El consenso es que el valor justo es..."
5. **Divide y conquista**: Negocia por separado, consolida después

GENERA:
MENSAJE_PARA_A: [personalizado para primera parte]
MENSAJE_PARA_B: [personalizado para segunda parte]
COMO_USAR_TENSIÓN: [cómo hacer que compitan]
ORDEN_OPTIMO: [a quién contactar primero]
"""

# ============================================================================
# PROMPT: ANÁLISIS DE PODER RELATIVO
# ============================================================================
PROMPT_ANALISIS_PODER = """Analiza la DINÁMICA DE PODER en esta negociación.

TU_POSICIÓN: {tu_situacion}
SU_POSICIÓN: {su_situacion}

FACTORES DE PODER:
1. **BATNA** (Best Alternative To Negotiated Agreement)
   - ¿Quién tiene mejores alternativas?
2. **Urgencia temporal**
   - ¿Quién necesita cerrar rápido?
3. **Información**
   - ¿Quién sabe más sobre el valor real?
4. **Recursos**
   - ¿Quién tiene más opciones?
5. **Reputación**
   - ¿Quién tiene más que perder?

ANÁLISIS:
BALANCE_PODER: [Ellos 0-100 Tú]
VENTAJAS_TUYAS: [lista]
DEBILIDADES_TUYAS: [lista]
COMO_NIVELAR: [estrategias para mejorar tu posición]
ZONA_ACUERDO: [rango probable de acuerdo]
OBJETIVO_REALISTA: [mejor resultado alcanzable]
"""

# ============================================================================
# FUNCIONES HELPER PARA INTEGRAR LOS PROMPTS
# ============================================================================

def generar_prompt_personalizado(tipo_prompt, **kwargs):
    """
    Genera un prompt personalizado basado en el tipo y parámetros.
    
    Args:
        tipo_prompt: Tipo de prompt a usar
        **kwargs: Parámetros específicos del prompt
    
    Returns:
        str: Prompt formateado
    """
    prompts = {
        'personalidad': PROMPT_ANALISIS_PERSONALIDAD,
        'oferta_asimetrica': PROMPT_OFERTA_ASIMETRICA,
        'counter_agresivo': PROMPT_COUNTER_AGRESIVO,
        'detectar_bluff': PROMPT_DETECTAR_BLUFF,
        'cierre_agresivo': PROMPT_CIERRE_AGRESIVO,
        'construir_rapport': PROMPT_CONSTRUIR_RAPPORT,
        'recuperar': PROMPT_RECUPERAR_NEGOCIACION,
        'multi_party': PROMPT_NEGOCIACION_MULTIPLE,
        'analisis_poder': PROMPT_ANALISIS_PODER,
    }
    
    prompt_template = prompts.get(tipo_prompt, "")
    return prompt_template.format(**kwargs)


# ============================================================================
# EJEMPLO DE INTEGRACIÓN EN bot_negociador.py
# ============================================================================

"""
Para integrar estos prompts en tu bot_negociador.py:

1. Importa este módulo:
   from prompts_avanzados import generar_prompt_personalizado

2. Usa los prompts en tus métodos:

   # Antes de negociar, construir rapport:
   prompt = generar_prompt_personalizado(
       'construir_rapport',
       destinatario='Juan',
       objetivo='conseguir madera'
   )
   respuesta = self.consultar_ollama(prompt)

   # Para contra-ofertas agresivas:
   prompt = generar_prompt_personalizado(
       'counter_agresivo',
       oferta_recibida='Te doy 5 maderas por 10 hierros'
   )
   respuesta = self.consultar_ollama(prompt)

   # Para detectar si están mintiendo:
   prompt = generar_prompt_personalizado(
       'detectar_bluff',
       mensaje='No tengo madera para dar, es imposible'
   )
   respuesta = self.consultar_ollama(prompt)
"""

# ============================================================================
# CONFIGURACIÓN DE PARÁMETROS ÓPTIMOS
# ============================================================================

CONFIGURACION_OLLAMA = {
    # Para análisis (necesita precisión)
    'analisis': {
        'temperature': 0.3,
        'top_p': 0.9,
        'top_k': 40,
    },
    
    # Para creatividad (generación de mensajes)
    'creativo': {
        'temperature': 0.8,
        'top_p': 0.95,
        'top_k': 50,
    },
    
    # Para agresividad (contra-ofertas, cierres)
    'agresivo': {
        'temperature': 0.7,
        'top_p': 0.9,
        'top_k': 45,
    }
}
