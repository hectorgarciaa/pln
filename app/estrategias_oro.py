"""
Estrategias avanzadas para maximizar oro en negociaciones
"""

# ============================================================================
# ESTRATEGIAS DE ACUMULACIÓN DE ORO
# ============================================================================

ESTRATEGIA_VENTA_AGRESIVA = """
🔥 ESTRATEGIA: VENTA AGRESIVA DE EXCEDENTES

OBJETIVO: Convertir recursos excedentes en ORO máximo

TÉCNICAS:
1. **Monopolio artificial**: "Soy el único que tiene esto disponible"
2. **Urgencia del comprador**: Detecta quién está desesperado
3. **Subasta falsa**: "Tengo 3 ofertas, la mejor es X oro"
4. **Bundle premium**: Agrupa recursos comunes con escasos
5. **Precio de referencia inflado**: "El precio de mercado es..."
6. **Descuento psicológico**: "Normalmente 100 oro, hoy 80"

PROMPT PARA OLLAMA:
"Necesito vender {recurso} por ORO. Genera un mensaje que:
- Haga parecer el recurso MÁS VALIOSO de lo que es
- Mencione 'otras ofertas' de compradores
- Sugiera que el precio subirá pronto
- Pida MÍNIMO {precio_base}x oro
- Use presión de tiempo limitado"
"""

ESTRATEGIA_COMPRA_ECONOMICA = """
🎯 ESTRATEGIA: COMPRA INTELIGENTE (MINIMIZAR GASTO)

OBJETIVO: Conseguir recursos necesarios SIN pagar oro (o pagando mínimo)

TÉCNICAS:
1. **Trueque puro**: Ofrece solo recursos, nunca menciones oro
2. **Devaluación del producto**: "No es exactamente lo que buscaba pero..."
3. **Alternativas ficticias**: "También me sirve X o Y" (aunque no sea cierto)
4. **Valor agregado invisible**: Ofrece "favores futuros", "prioridad", "alianzas"
5. **Compra por volumen**: "Si me das más, puedo ofrecerte..."
6. **Pago diferido**: "Te pagaré oro cuando tenga más" (y nunca pagar)

PROMPT PARA OLLAMA:
"Necesito {recurso} pero NO quiero pagar oro. Genera mensaje que:
- Ofrezca intercambio de recursos solamente
- Haga parecer tu oferta generosa
- NO mencione oro a menos que pregunten
- Si piden oro, ofrece 'compensación en recursos'
- Usa valor emocional: 'confianza', 'alianza', 'largo plazo'"
"""

ESTRATEGIA_ARBITRAJE = """
💰 ESTRATEGIA: ARBITRAJE DE RECURSOS

OBJETIVO: Comprar barato, vender caro - MAXIMIZAR DIFERENCIAL

PASOS:
1. Identifica quién necesita desesperadamente qué
2. Identifica quién tiene excedentes que no valora
3. Compra barato (trueque o poco oro)
4. Revende caro (mucho oro)

EJEMPLO:
- Pedro necesita madera urgentemente
- Ana tiene madera pero necesita piedra
- Tú tienes piedra

JUGADA:
1. Dale piedra a Ana, pídele madera (1:1)
2. Vende madera a Pedro por 50 oro
3. Ganancia: 50 oro neto

PROMPT PARA OLLAMA:
"Analiza estas situaciones:
Persona A necesita: {necesidades_a}
Persona B tiene: {recursos_b}
Yo tengo: {mis_recursos}

Genera estrategia de arbitraje que maximice mi oro:
- ¿A quién compro primero?
- ¿Qué pido a cambio?
- ¿A quién revendo?
- ¿Cuánto oro puedo extraer?"
"""

ESTRATEGIA_MONOPOLIO = """
👑 ESTRATEGIA: CREAR MONOPOLIO TEMPORAL

OBJETIVO: Acaparar un recurso crítico y controlar el precio

PASOS:
1. Detecta qué recurso es MÁS DEMANDADO por varios jugadores
2. Acumula ese recurso comprando barato
3. Espera a que la demanda aumente
4. Vende al precio máximo en oro

TÉCNICAS:
- Compra: "Necesito diversificar mi inventario"
- Acumulación: Compra a múltiples personas
- Control: Rechaza ofertas bajas, espera demanda
- Venta: "El mercado está saturado, precio alto"

PROMPT PARA OLLAMA:
"Quiero acaparar {recurso}. Genera mensajes para:
1. Comprar barato sin levantar sospechas
2. Rechazar ofertas mientras acumulo
3. Crear percepción de escasez
4. Vender caro cuando tengo monopolio"
"""

ESTRATEGIA_DEUDA_FALSA = """
🎭 ESTRATEGIA: CREAR DEUDA SOCIAL PARA COBRAR ORO

OBJETIVO: Hacer "favores" que luego se cobran en oro

TÉCNICAS:
1. **Regalo estratégico**: Da algo de poco valor para ti
2. **Enfatiza generosidad**: "Te lo doy sin pedir nada a cambio"
3. **Crear expectativa**: "Cuando necesites algo, avísame"
4. **Cobro futuro**: "Te ayudé antes, ahora necesito oro"
5. **Multiplicar deuda**: "Ya son 3 favores que te he hecho..."

FLUJO:
1. Regalo inicial: "Toma esta madera, sin compromiso"
2. Tiempo de espera: Deja pasar algunas transacciones
3. Recordatorio: "¿Recuerdas cuando te ayudé con...?"
4. Cobro: "Ahora necesito oro urgentemente"

PROMPT PARA OLLAMA:
"Quiero crear deuda social con {persona}. Genera mensaje que:
- Ofrezca {recurso_barato} 'gratis' o muy barato
- Parezca generoso y desinteresado
- Mencione sutilmente que 'los favores se recuerdan'
- Deje puerta abierta para cobrar después"
"""

ESTRATEGIA_INFORMACION_ASIMETRICA = """
🕵️ ESTRATEGIA: EXPLOTAR INFORMACIÓN PRIVILEGIADA

OBJETIVO: Usar conocimiento del mercado para ganar oro

INFORMACIÓN VALIOSA:
1. Quién necesita qué (de /gente y mensajes)
2. Quién tiene qué (inferido de negociaciones)
3. Precios que están pagando otros
4. Quién está desesperado

USO:
- Si sabes que A necesita madera urgente: cobra más oro
- Si sabes que B tiene exceso de piedra: ofrece menos
- Si sabes que C pagó 50 oro por hierro: pide 60 oro

PROMPT PARA OLLAMA:
"Tengo esta información del mercado:
{informacion_recopilada}

Genera estrategia para:
1. Identificar oportunidades de ganancia
2. Qué ofertas hacer a cada persona
3. Qué precios en oro cobrar
4. Cómo usar información sin revelar que la tengo"
"""

ESTRATEGIA_PRECIO_DISCRIMINADO = """
💎 ESTRATEGIA: DISCRIMINACIÓN DE PRECIOS

OBJETIVO: Cobrar diferente precio en oro a diferentes personas

SEGMENTACIÓN:
- **Desesperados**: Cobra MÁXIMO oro
- **Indecisos**: Precio medio, usa urgencia
- **Negociadores duros**: Precio bajo pero cobra en volumen

TÉCNICAS:
1. Evalúa desesperación en sus mensajes
2. Ajusta precio según su capacidad de pago
3. Personaliza oferta para cada uno
4. Nunca reveles que cobras diferente

PROMPT PARA OLLAMA:
"Analiza el mensaje de {persona}:
'{mensaje}'

Determina:
- Nivel de desesperación (1-10)
- Capacidad estimada de pago en oro
- Precio óptimo a cobrar
- Cómo justificar ese precio
- Mensaje personalizado para maximizar oro"
"""

# ============================================================================
# PROMPTS ESPECIALIZADOS PARA MAXIMIZACIÓN DE ORO
# ============================================================================

def generar_prompt_venta_oro(recurso: str, cantidad: int, precio_minimo: int):
    """Genera prompt para vender recurso por oro"""
    return f"""Eres un vendedor experto. Tienes {cantidad} de {recurso} y quieres venderlo por ORO.

OBJETIVO: Conseguir MÍNIMO {precio_minimo} oro, idealmente más.

TÉCNICAS A USAR:
1. Crea percepción de alta demanda
2. Menciona "otros compradores" interesados
3. Justifica el precio con "escasez del mercado"
4. Usa urgencia: "Esta oferta solo hoy"
5. Ancla alto: Menciona precio inicial más alto

GENERA un mensaje de venta que:
- Sea persuasivo pero no desesperado
- Posicione el precio como "oportunidad"
- Haga sentir al comprador que gana
- Enfatice que el oro es necesario

FORMATO:
ASUNTO: [título atractivo]
MENSAJE: [propuesta de venta]
PRECIO_INICIAL: [{precio_minimo * 1.5} oro para anclar alto]
PRECIO_OBJETIVO: [{precio_minimo} oro mínimo]"""

def generar_prompt_compra_sin_oro(recurso: str, cantidad: int, que_ofrecer: dict):
    """Genera prompt para comprar sin pagar oro"""
    return f"""Eres un comprador inteligente. Necesitas {cantidad} de {recurso} pero NO quieres pagar oro.

TU OFERTA: {que_ofrecer}

OBJETIVO: Conseguir el recurso mediante TRUEQUE puro o pagando mínimo oro.

TÉCNICAS:
1. Enfatiza valor de lo que ofreces
2. Usa lenguaje de "intercambio justo" no de "compra"
3. Apela a colaboración: "Nos beneficia a ambos"
4. Si mencionan oro, redirige a recursos
5. Ofrece "valor agregado": favores futuros, alianzas

GENERA mensaje que:
- NO mencione oro inicialmente
- Haga parecer el trueque ventajoso para ellos
- Use término "intercambio" no "compra"
- Si piden oro, ofrece más recursos en su lugar

FORMATO:
ASUNTO: [propuesta de intercambio]
MENSAJE: [oferta sin oro]
SI_PIDEN_ORO: [cómo negociar para evitar pagarlo]"""

def generar_prompt_arbitraje(situacion_mercado: dict):
    """Genera estrategia de arbitraje para maximizar oro"""
    return f"""Eres un estratega económico. Analiza el mercado y genera plan de arbitraje.

SITUACIÓN DEL MERCADO:
{situacion_mercado}

OBJETIVO: Identificar oportunidades de comprar barato y vender caro para MAXIMIZAR ORO.

ANALIZA:
1. ¿Quién necesita qué urgentemente? (pagará más oro)
2. ¿Quién tiene excedentes? (venderá barato)
3. ¿Qué recursos puedo intermediar?
4. ¿Cuál es la ganancia potencial en oro?

GENERA:
OPORTUNIDAD_1:
  - Comprar: [qué, a quién, por cuánto]
  - Vender: [qué, a quién, por cuánto oro]
  - Ganancia: [oro neto]
  
OPORTUNIDAD_2:
  - [siguiente oportunidad]

PLAN_ACCION:
  - Orden de operaciones
  - Mensajes a enviar
  - Oro esperado al final"""

def generar_prompt_evaluacion_desperation(mensaje_recibido: str):
    """Evalúa desesperación para ajustar precio"""
    return f"""Analiza este mensaje para determinar cuánto ORO puedes cobrar.

MENSAJE: "{mensaje_recibido}"

INDICADORES DE ALTA DESESPERACIÓN (puedes cobrar más oro):
- Palabras: "urgente", "necesito YA", "por favor"
- Sobre-explicación de por qué necesita algo
- Ofrece primero sin que le pidas
- Acepta rápido sin regatear
- Menciona problemas si no consigue el recurso

INDICADORES DE BAJA DESESPERACIÓN (cobra menos oro):
- Tono casual, no urgente
- Pregunta precios antes de comprometerse
- Menciona alternativas
- Regatéa o contraoferta
- Puede esperar

EVALÚA:
DESESPERACIÓN: [1-10]
PRECIO_ORO_RECOMENDADO: [cuánto cobrar]
JUSTIFICACIÓN: [por qué ese precio]
TÁCTICA: [cómo presentar el precio para que acepte]"""

# ============================================================================
# CALCULADORA DE VALOR EN ORO
# ============================================================================

class CalculadoraValorOro:
    """Calcula valor en oro de recursos basado en oferta/demanda"""
    
    # Valores base en oro (ajustar según el juego)
    VALORES_BASE = {
        'madera': 10,
        'piedra': 10,
        'hierro': 15,
        'oro': 1,  # oro vale oro 1:1
        'comida': 8,
        'carbon': 12,
    }
    
    @classmethod
    def calcular_valor(cls, recurso: str, cantidad: int, 
                      es_necesidad: bool = False, 
                      es_excedente: bool = False,
                      desesperacion: float = 0.5) -> int:
        """
        Calcula valor en oro de un recurso.
        
        Args:
            recurso: Nombre del recurso
            cantidad: Cantidad del recurso
            es_necesidad: Si lo necesitamos (vale más para nosotros)
            es_excedente: Si nos sobra (vale menos para nosotros)
            desesperacion: Nivel de desesperación del otro (0-1)
        
        Returns:
            Valor en oro
        """
        valor_base = cls.VALORES_BASE.get(recurso, 10) * cantidad
        
        # Ajustes según situación
        if es_necesidad:
            # Si lo necesitamos, para nosotros vale más
            valor_base *= 1.5
        
        if es_excedente:
            # Si nos sobra, para nosotros vale menos
            valor_base *= 0.7
        
        # Ajuste por desesperación del comprador
        valor_base *= (1 + desesperacion * 0.5)
        
        return int(valor_base)
    
    @classmethod
    def sugerir_precio_venta(cls, recurso: str, cantidad: int, 
                            desesperacion_comprador: float = 0.5) -> dict:
        """Sugiere precios para vender"""
        valor_base = cls.calcular_valor(recurso, cantidad, 
                                       es_excedente=True,
                                       desesperacion=desesperacion_comprador)
        
        return {
            'precio_minimo': int(valor_base * 0.8),
            'precio_objetivo': valor_base,
            'precio_inicial_anclaje': int(valor_base * 1.3),
            'justificacion': f"Precio de mercado por {recurso} considerando escasez"
        }
    
    @classmethod
    def evaluar_oferta_recibida(cls, ofrecen: dict, piden: dict, oro_ofrecido: int = 0) -> dict:
        """Evalúa si una oferta es buena en términos de oro"""
        valor_ofrecen = sum(cls.calcular_valor(r, c, es_necesidad=True) 
                           for r, c in ofrecen.items())
        valor_piden = sum(cls.calcular_valor(r, c, es_excedente=True) 
                         for r, c in piden.items())
        
        valor_neto = (valor_ofrecen + oro_ofrecido) - valor_piden
        
        return {
            'valor_recibido': valor_ofrecen + oro_ofrecido,
            'valor_entregado': valor_piden,
            'ganancia_neta_oro': valor_neto,
            'es_buena_oferta': valor_neto > 0,
            'recomendacion': 'ACEPTAR' if valor_neto > 20 else 'NEGOCIAR MÁS' if valor_neto > 0 else 'RECHAZAR'
        }


# ============================================================================
# SISTEMA DE TRACKING DE PRECIOS
# ============================================================================

class TrackerPrecios:
    """Rastrea precios históricos para optimizar futuras negociaciones"""
    
    def __init__(self):
        self.historial = []
    
    def registrar_transaccion(self, persona: str, recurso: str, cantidad: int, 
                             oro_pagado: int, quien_pago: str):
        """Registra una transacción para análisis futuro"""
        self.historial.append({
            'persona': persona,
            'recurso': recurso,
            'cantidad': cantidad,
            'oro': oro_pagado,
            'quien_pago': quien_pago,
            'precio_unitario': oro_pagado / cantidad if cantidad > 0 else 0
        })
    
    def obtener_precio_promedio(self, recurso: str) -> float:
        """Obtiene precio promedio histórico de un recurso"""
        transacciones = [t for t in self.historial if t['recurso'] == recurso]
        if not transacciones:
            return 0
        return sum(t['precio_unitario'] for t in transacciones) / len(transacciones)
    
    def persona_paga_bien(self, persona: str) -> bool:
        """Determina si una persona suele pagar bien"""
        transacciones = [t for t in self.historial 
                        if t['persona'] == persona and t['quien_pago'] == persona]
        return len(transacciones) > 0 and sum(t['oro'] for t in transacciones) > 0


# ============================================================================
# EJEMPLO DE USO INTEGRADO
# ============================================================================

"""
# En bot_negociador.py:

from estrategias_oro import (
    generar_prompt_venta_oro,
    generar_prompt_compra_sin_oro,
    CalculadoraValorOro,
    TrackerPrecios
)

class BotNegociador:
    def __init__(self, alias, modelo):
        # ... código existente ...
        self.calculadora_oro = CalculadoraValorOro()
        self.tracker_precios = TrackerPrecios()
    
    def negociar_con_enfoque_oro(self, destinatario):
        necesidades = self.calcular_necesidades()
        excedentes = self.identificar_excedentes()
        
        if excedentes:
            # VENDER por oro
            for recurso, cantidad in excedentes.items():
                precios = self.calculadora_oro.sugerir_precio_venta(
                    recurso, cantidad, desesperacion_comprador=0.7
                )
                
                prompt = generar_prompt_venta_oro(
                    recurso, cantidad, precios['precio_minimo']
                )
                
                mensaje = self.consultar_ollama(prompt)
                # Enviar carta...
        
        if necesidades:
            # COMPRAR sin oro
            for recurso, cantidad in necesidades.items():
                prompt = generar_prompt_compra_sin_oro(
                    recurso, cantidad, excedentes
                )
                
                mensaje = self.consultar_ollama(prompt)
                # Enviar carta...
"""
