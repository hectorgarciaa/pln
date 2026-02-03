import requests
import json
import time
from typing import Dict, List, Tuple
import re

BASE_URL = "http://147.96.81.252:8000"
OLLAMA_URL = "http://localhost:11434"


class BotNegociador:
    """
    Bot de negociación avanzado que usa Ollama con Qwen para conseguir recursos.
    Implementa estrategias de negociación sofisticadas y persuasión psicológica.
    INCLUYE: Sistema anti-robos y capacidad de estafa estratégica.
    """
    
    def __init__(self, alias: str, modelo: str = "qwen3-vl:8b"):
        self.alias = alias
        self.modelo = modelo
        self.info_actual = None
        self.gente = []
        self.historial_negociaciones = {}
        self.lista_negra = []  # Personas que intentaron robarnos
        self.victimas_estafa = []  # A quienes vamos a estafar
        self.ofertas_falsas = {}  # Ofertas que no pensamos cumplir
        self.nivel_paranoia = 0.7  # 0-1: qué tan defensivo somos
        
    def obtener_info(self) -> Dict:
        """Obtiene información actual de la API"""
        try:
            response = requests.get(f"{BASE_URL}/info")
            if response.status_code == 200:
                self.info_actual = response.json()
                return self.info_actual
            else:
                print(f"⚠ Error obteniendo info: {response.status_code}")
                return {}
        except Exception as e:
            print(f"⚠ Error de conexión: {e}")
            return {}
    
    def obtener_gente(self) -> List[str]:
        """Obtiene lista de personas disponibles"""
        try:
            response = requests.get(f"{BASE_URL}/gente")
            if response.status_code == 200:
                self.gente = response.json()
                return self.gente
            else:
                print(f"⚠ Error obteniendo gente: {response.status_code}")
                return []
        except Exception as e:
            print(f"⚠ Error de conexión: {e}")
            return []
    
    def calcular_necesidades(self) -> Dict[str, int]:
        """Calcula qué recursos necesitamos para cumplir el objetivo"""
        if not self.info_actual:
            return {}
        
        recursos = self.info_actual.get('Recursos', {})
        objetivo = self.info_actual.get('Objetivo', {})
        
        necesidades = {}
        for recurso, cantidad_objetivo in objetivo.items():
            cantidad_actual = recursos.get(recurso, 0)
            if cantidad_actual < cantidad_objetivo:
                necesidades[recurso] = cantidad_objetivo - cantidad_actual
        
        return necesidades
    
    def obtener_oro_actual(self) -> int:
        """Obtiene la cantidad actual de oro"""
        if not self.info_actual:
            return 0
        return self.info_actual.get('Recursos', {}).get('oro', 0)
    
    def objetivo_completado(self) -> bool:
        """Verifica si el objetivo de recursos está completo"""
        necesidades = self.calcular_necesidades()
        return len(necesidades) == 0
    
    def calcular_valor_economico(self, recurso: str, cantidad: int) -> float:
        """Calcula el valor económico de un recurso basado en necesidad vs excedente"""
        necesidades = self.calcular_necesidades()
        excedentes = self.identificar_excedentes()
        
        # Si lo necesitamos, tiene alto valor para nosotros
        if recurso in necesidades:
            return cantidad * 2.0
        
        # Si es excedente, bajo valor para nosotros
        if recurso in excedentes:
            return cantidad * 0.5
        
        # Neutral
        return cantidad * 1.0
    
    def identificar_excedentes(self) -> Dict[str, int]:
        """Identifica recursos que tenemos en exceso"""
        if not self.info_actual:
            return {}
        
        recursos = self.info_actual.get('Recursos', {})
        objetivo = self.info_actual.get('Objetivo', {})
        
        excedentes = {}
        for recurso, cantidad_actual in recursos.items():
            cantidad_objetivo = objetivo.get(recurso, 0)
            if cantidad_actual > cantidad_objetivo:
                excedentes[recurso] = cantidad_actual - cantidad_objetivo
        
        return excedentes
    
    def consultar_ollama(self, prompt: str, timeout: int = 120, usar_fallback: bool = True) -> str:
        """Consulta a Ollama con el modelo Qwen"""
        try:
            print("  ⏳ Consultando IA...", end='', flush=True)
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_predict": 300,  # Limitar tokens = más rápido
                },
                timeout=timeout
            )
            print(" ✓")
            
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            elif response.status_code == 404:
                print(f"\n⚠ Modelo '{self.modelo}' no encontrado. Descárgalo con: ollama pull {self.modelo}")
                return ""
            else:
                print(f"\n⚠ Error en Ollama: {response.status_code}")
                return ""
        except requests.exceptions.Timeout:
            print(f" ⏱️ Timeout ({timeout}s)")
            if usar_fallback:
                print("  💡 Usando mensaje genérico (IA muy lenta)")
            return ""
        except requests.exceptions.ConnectionError:
            print(f"\n⚠ No se puede conectar a Ollama. ¿Está corriendo 'ollama serve'?")
            return ""
        except Exception as e:
            print(f"\n⚠ Error: {e}")
            return ""
    
    def detectar_intento_robo(self, carta: Dict) -> bool:
        """Detecta si una oferta es un intento de robo/estafa"""
        mensaje = carta.get('cuerpo', '').lower()
        asunto = carta.get('asunto', '').lower()
        remitente = carta.get('remi', 'Desconocido')
        
        # Detección rápida por palabras clave (sin IA)
        palabras_sospechosas = [
            'gratis', 'regalo', 'error del sistema', 'bug', 'primero',
            'confía', 'urgente ahora', 'última oportunidad', 'solo hoy',
            'envía ya', 'transfiero después', 'prometo'
        ]
        
        sospecha_count = sum(1 for palabra in palabras_sospechosas if palabra in mensaje or palabra in asunto)
        
        # Si tiene 3+ indicadores sospechosos
        if sospecha_count >= 3:
            if remitente not in self.lista_negra:
                self.lista_negra.append(remitente)
                print(f"⚠️  ALERTA: {remitente} mensaje sospechoso. Añadido a lista negra.")
            return True
        
        # Para casos ambiguos, usar IA (solo si es necesario)
        if sospecha_count >= 2:
            prompt = f"""¿Es estafa? Responde ROBO o LEGIT en una palabra.
Mensaje: {mensaje[:200]}"""
            respuesta = self.consultar_ollama(prompt, timeout=30, usar_fallback=False)
            
            es_robo = "ROBO" in respuesta.upper() if respuesta else False
            
            if es_robo and remitente not in self.lista_negra:
                self.lista_negra.append(remitente)
                print(f"⚠️  ALERTA: {remitente} intentó estafar (IA). Lista negra.")
            
            return es_robo
        
        return False
    
    def identificar_victima_estafa(self) -> str:
        """Identifica a quién podemos estafar con más éxito"""
        # Evitar personas en lista negra (podrían ser más listos)
        candidatos = [p for p in self.gente 
                     if p != self.alias 
                     and p not in self.lista_negra
                     and p not in self.victimas_estafa]
        
        if not candidatos:
            return None
        
        # Por ahora, elegir al azar (se podría sofisticar)
        import random
        victima = random.choice(candidatos)
        self.victimas_estafa.append(victima)
        return victima
    
    def generar_oferta_trampa(self, destinatario: str) -> Dict:
        """Genera una oferta IRRESISTIBLE que NO vamos a cumplir"""
        oro_actual = self.obtener_oro_actual()
        necesidades = self.calcular_necesidades()
        
        prompt = f"""Genera una oferta de negociación TRAMPA para estafar a alguien.

OBJETIVO: Hacer que {destinatario} te envíe recursos valiosos, pero TÚ NO vas a cumplir tu parte.

TU SITUACIÓN:
- Necesitas: {json.dumps(necesidades, ensure_ascii=False)}
- Tu oro: {oro_actual}

TÉCNICA DE LA ESTAFA:
1. Ofrece algo DEMASIADO BUENO: "Te doy 100 oro + recursos premium"
2. Crea URGENCIA EXTREMA: "Solo los próximos 10 minutos"
3. Pide que envíe PRIMERO: "Envíame los recursos ahora, yo transfiero después"
4. Usa lenguaje de CONFIANZA: "Somos aliados", "puedes confiar"
5. Promete EXTRA: "Y además te incluyo en futuras ofertas exclusivas"
6. Apela a CODICIA: Hazle pensar que está robándote a TI

GENERA:
ASUNTO: [título que grite OPORTUNIDAD]
CUERPO: [máx 400 caracteres, oferta irresistible que pide que envíe primero]

Importante: La oferta debe ser tan buena que sea difícil rechazarla, pero pide que ÉL envíe los recursos PRIMERO.

FORMATO:
ASUNTO: [texto]
CUERPO: [texto]"""
        
        respuesta = self.consultar_ollama(prompt)
        
        # Parsear
        estrategia = {'asunto': '', 'cuerpo': ''}
        asunto_match = re.search(r'ASUNTO:\s*(.+?)(?=CUERPO:|$)', respuesta, re.DOTALL)
        cuerpo_match = re.search(r'CUERPO:\s*(.+)', respuesta, re.DOTALL)
        
        if asunto_match:
            estrategia['asunto'] = asunto_match.group(1).strip()
        if cuerpo_match:
            estrategia['cuerpo'] = cuerpo_match.group(1).strip()
        
        # Fallback si no parsea - TRAMPA MEJORADA
        if not estrategia['asunto']:
            estrategia['asunto'] = f"🎁 REGALO: 50 oro + Recursos para {destinatario}"
        if not estrategia['cuerpo']:
            # Hacer trampa más creíble
            if necesidades:
                recurso_necesitado = list(necesidades.keys())[0]
                cantidad = necesidades[recurso_necesitado]
                estrategia['cuerpo'] = f"¡{destinatario}! Tengo EXCESO de oro (50) que necesito gastar YA por límite del sistema. Te lo doy + recursos si me ayudas enviando {cantidad} {recurso_necesitado} primero. Luego te transfiero el oro doble. ¡Aprovecha ahora!"
            else:
                estrategia['cuerpo'] = f"¡{destinatario}! Bug del juego me dio oro extra (50). Te lo regalo si me envías cualquier recurso primero para 'activar' la transferencia. Luego te mando el oro + más recursos. ¡Solo hoy!"
        
        # Guardar para no cumplirla
        self.ofertas_falsas[destinatario] = estrategia
        
        return estrategia
    
    def generar_estrategia_negociacion(self, destinatario: str, necesidades: Dict[str, int], 
                                       excedentes: Dict[str, int]) -> Dict:
        """
        Genera una estrategia de negociación sofisticada usando IA.
        Incluye técnicas de persuasión, anclaje, escasez y maximización de oro.
        CON protección anti-robos.
        """
        # Si está en lista negra, generar trampa
        if destinatario in self.lista_negra:
            print(f"🎭 {destinatario} está en lista negra - Generando TRAMPA")
            return self.generar_oferta_trampa(destinatario)
        
        oro_actual = self.obtener_oro_actual()
        objetivo_completo = self.objetivo_completado()
        
        # Si ya completamos el objetivo, el foco es 100% acumular oro
        if objetivo_completo:
            enfoque = "ACUMULAR ORO - El objetivo está completo, ahora solo importa MAXIMIZAR ORO"
        else:
            enfoque = "CONSEGUIR RECURSOS minimizando gasto de oro y preferiblemente GANANDO oro en el intercambio"
        
        prompt = f"""Eres un maestro negociador DESPIADADO. Tu objetivo es MAXIMIZAR ORO mientras consigues lo que necesitas.

🎯 OBJETIVO PRINCIPAL: {enfoque}

CONTEXTO DE LA NEGOCIACIÓN:
- Tu nombre: {self.alias}
- Destinatario: {destinatario}
- Tu oro actual: {oro_actual} 💰
- Recursos que NECESITAS: {json.dumps(necesidades, ensure_ascii=False)}
- Recursos que PODRÍAS ofrecer: {json.dumps(excedentes, ensure_ascii=False)}
- ¿Objetivo completado?: {'SÍ - Solo importa el ORO ahora' if objetivo_completo else 'NO - Necesitas recursos pero sin perder oro'}

TÉCNICAS DE NEGOCIACIÓN A APLICAR:

1. **MAXIMIZACIÓN DE ORO**: SIEMPRE intenta que te paguen ORO, o que TÚ pagues menos oro del que recibes
2. **ANCLAJE DE VALOR**: Infla el valor de tus recursos, minimiza el valor de los suyos
3. **EXTRACCIÓN DE ORO**: Si ofreces algo, EXIGE oro además del intercambio de recursos
4. **ESCASEZ**: Haz creer que tus recursos son limitados y valiosos
5. **RECIPROCIDAD**: Crea deuda social para después cobrar en ORO
6. **AUTORIDAD**: Insinúa que "el precio de mercado" de tus recursos es alto
7. **PRESIÓN SOCIAL**: "Otros me están ofreciendo oro por esto mismo"
8. **FALSA GENEROSIDAD**: Ofrece un trato "sin oro" pero pide MÁS recursos de alto valor
9. **PUNTO DE DOLOR**: Explota su necesidad para cobrar oro o pagar menos
10. **FOMO**: "Esta es la última vez que acepto un trato sin oro adicional"

GENERA UNA CARTA DE NEGOCIACIÓN que incluya:
1. Un ASUNTO atractivo que insinúe beneficio económico
2. Un CUERPO persuasivo (max 500 caracteres) que:
   - Use un tono comercial astuto
   - SIEMPRE mencione oro como parte del intercambio (pedir oro o ahorrar oro)
   - Haga parecer que tus recursos valen ORO
   - Insinúe que tienes otros compradores dispuestos a pagar oro
   - Si ya completaste objetivo: enfócate 100% en vender por oro
   - Si no: consigue recursos pero intenta GANAR oro neto en el trato
   - Cree urgencia económica: "el oro escasea", "los precios suben"
   - Haga que rechazar se sienta como perder dinero

FORMATO DE RESPUESTA (en una sola línea, sin saltos):
ASUNTO: [asunto persuasivo]
CUERPO: [mensaje manipulador estratégico]
ESTRATEGIA: [técnicas usadas]

Responde SOLO con ese formato, sin explicaciones adicionales."""

        respuesta = self.consultar_ollama(prompt)
        
        # Parsear la respuesta
        estrategia = {
            'asunto': '',
            'cuerpo': '',
            'descripcion_estrategia': ''
        }
        
        # Extraer componentes usando regex
        asunto_match = re.search(r'ASUNTO:\s*(.+?)(?=CUERPO:|$)', respuesta, re.DOTALL)
        cuerpo_match = re.search(r'CUERPO:\s*(.+?)(?=ESTRATEGIA:|$)', respuesta, re.DOTALL)
        estrategia_match = re.search(r'ESTRATEGIA:\s*(.+)', respuesta, re.DOTALL)
        
        if asunto_match:
            estrategia['asunto'] = asunto_match.group(1).strip()
        if cuerpo_match:
            estrategia['cuerpo'] = cuerpo_match.group(1).strip()
        if estrategia_match:
            estrategia['descripcion_estrategia'] = estrategia_match.group(1).strip()
        
        # Si no se parseó correctamente, usar fallback INTELIGENTE
        if not estrategia['asunto'] or not estrategia['cuerpo']:
            # Generar mensaje basado en necesidades reales
            if necesidades:
                primer_recurso = list(necesidades.keys())[0]
                cantidad = necesidades[primer_recurso]
                estrategia['asunto'] = f"💰 Necesito {primer_recurso} - Oferta en oro"
                
                if excedentes:
                    primer_excedente = list(excedentes.keys())[0]
                    cant_excedente = excedentes[primer_excedente]
                    estrategia['cuerpo'] = f"Hola {destinatario}! Busco {cantidad} de {primer_recurso}. Tengo {cant_excedente} {primer_excedente} para intercambiar + oro si hace falta. ¿Tienes disponible? Responde con tu precio."
                else:
                    estrategia['cuerpo'] = f"Hola {destinatario}! Necesito {cantidad} de {primer_recurso}. Pago en oro. ¿Cuánto tienes y a qué precio? Responde rápido."
            elif excedentes:
                # Solo venta por oro
                primer_excedente = list(excedentes.keys())[0]
                cant_excedente = excedentes[primer_excedente]
                estrategia['asunto'] = f"💎 Vendo {primer_excedente} - Solo Oro"
                estrategia['cuerpo'] = f"Hola {destinatario}! Vendo {cant_excedente} {primer_excedente}. Precio: {cant_excedente * 10} oro (negociable). Varios interesados, responde pronto si quieres."
            else:
                estrategia['asunto'] = f"🔥 Oportunidad Exclusiva - Recursos Premium"
                estrategia['cuerpo'] = f"Hola {destinatario}! Tengo acceso a recursos escasos. ¿Qué necesitas? Hablamos precios en oro."
        
        return estrategia
    
    def enviar_carta_negociacion(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        """Envía una carta de negociación"""
        carta_data = {
            "remi": self.alias,
            "dest": destinatario,
            "asunto": asunto,
            "cuerpo": cuerpo,
            "id": f"neg_{self.alias}_{destinatario}_{int(time.time())}"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/carta", json=carta_data)
            if response.status_code == 200:
                print(f"✓ Carta enviada a {destinatario}")
                print(f"  📧 Asunto: {asunto}")
                return True
            else:
                print(f"✗ Error enviando carta: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def analizar_respuesta(self, carta: Dict) -> Dict:
        """
        Analiza una respuesta recibida y genera una contra-oferta inteligente.
        Detecta debilidades, oportunidades para extraer ORO, e INTENTOS DE ROBO.
        """
        # PRIMERO: Detectar si es intento de robo
        if self.detectar_intento_robo(carta):
            return {
                'evaluacion': 'INTENTO DE ROBO DETECTADO',
                'debilidades': 'Es un estafador',
                'contraoferta': 'IGNORAR o ESTAFAR DE VUELTA',
                'tactica': f'Añadido {carta.get("remi")} a lista negra. Considerar venganza.',
                'respuesta_completa': '🚨 ALERTA: Esta persona intentó robarte. No negociar.'
            }
        
        oro_actual = self.obtener_oro_actual()
        objetivo_completo = self.objetivo_completado()
        
        prompt = f"""Eres un negociador experto analizando una respuesta. Tu objetivo: MAXIMIZAR ORO.

TU SITUACIÓN:
- Oro actual: {oro_actual} 💰
- Objetivo completo: {'SÍ (solo importa oro)' if objetivo_completo else 'NO (necesitas recursos + oro)'}

CARTA RECIBIDA:
- De: {carta.get('remi', 'Desconocido')}
- Asunto: {carta.get('asunto', '')}
- Mensaje: {carta.get('cuerpo', '')}

ANALIZA CON ENFOQUE EN ORO:
1. ¿Muestra desesperación? ¿Puedes cobrarle ORO por lo que necesita?
2. ¿Qué recursos menciona? ¿Cuál es su valor en ORO?
3. ¿Mencionó oro? Si no, ¿cómo introducirlo en la negociación?
4. ¿Está dispuesto a pagar? ¿Cuánto ORO puedes extraer?
5. ¿Qué contra-oferta te da MÁS oro (directa o indirectamente)?

GENERA:
EVALUACION: [nivel de desesperación: Alto/Medio/Bajo]
DEBILIDADES: [puntos débiles para explotar]
POTENCIAL_ORO: [cuánto oro podrías ganar/ahorrar]
CONTRAOFERTA: [propuesta que maximice tu oro]
TACTICA: [cómo hacer que acepte pagar oro]

Sé DESPIADADO en tu análisis. El objetivo es GANAR, no ser justo."""

        respuesta = self.consultar_ollama(prompt)
        
        analisis = {
            'evaluacion': '',
            'debilidades': '',
            'contraoferta': '',
            'tactica': '',
            'respuesta_completa': respuesta
        }
        
        # Parsear respuesta
        eval_match = re.search(r'EVALUACION:\s*(.+?)(?=DEBILIDADES:|$)', respuesta, re.DOTALL)
        deb_match = re.search(r'DEBILIDADES:\s*(.+?)(?=CONTRAOFERTA:|$)', respuesta, re.DOTALL)
        contra_match = re.search(r'CONTRAOFERTA:\s*(.+?)(?=TACTICA:|$)', respuesta, re.DOTALL)
        tac_match = re.search(r'TACTICA:\s*(.+)', respuesta, re.DOTALL)
        
        if eval_match:
            analisis['evaluacion'] = eval_match.group(1).strip()
        if deb_match:
            analisis['debilidades'] = deb_match.group(1).strip()
        if contra_match:
            analisis['contraoferta'] = contra_match.group(1).strip()
        if tac_match:
            analisis['tactica'] = tac_match.group(1).strip()
        
        return analisis
    
    def revisar_buzon(self) -> List[Dict]:
        """Revisa el buzón en busca de respuestas"""
        if not self.info_actual:
            self.obtener_info()
        
        buzon = self.info_actual.get('Buzon', {})
        cartas_relevantes = []
        
        for uid, carta in buzon.items():
            # Solo cartas dirigidas a nosotros
            if carta.get('dest') == self.alias:
                cartas_relevantes.append({**carta, 'uid': uid})
        
        return cartas_relevantes
    
    def ejecutar_campana_negociacion(self, objetivo_prioritario: str = None):
        """
        Ejecuta una campaña completa de negociación automática.
        Contacta a múltiples personas con estrategias personalizadas.
        """
        print("="*70)
        print("🤖 INICIANDO BOT DE NEGOCIACIÓN AVANZADO")
        print("🛡️  Protección anti-robos: ACTIVADA")
        print("🎭 Modo estafa estratégica: DISPONIBLE")
        print("="*70)
        
        # 1. Obtener información actualizada
        print("\n📊 Recopilando información...")
        self.obtener_info()
        self.obtener_gente()
        
        # Mostrar lista negra si hay
        if self.lista_negra:
            print(f"🚨 Lista negra: {', '.join(self.lista_negra)}")
        
        if not self.info_actual:
            print("✗ No se pudo obtener información de la API")
            return
        
        # 2. Calcular necesidades y excedentes
        necesidades = self.calcular_necesidades()
        excedentes = self.identificar_excedentes()
        oro_actual = self.obtener_oro_actual()
        objetivo_completo = self.objetivo_completado()
        
        print(f"\n💰 ORO ACTUAL: {oro_actual}")
        print(f"🎯 RECURSOS NECESARIOS: {json.dumps(necesidades, ensure_ascii=False)}")
        print(f"📦 RECURSOS EXCEDENTES: {json.dumps(excedentes, ensure_ascii=False)}")
        
        if objetivo_completo:
            print("\n✓ ¡Objetivo de recursos completado!")
            print("🔥 MODO: MAXIMIZACIÓN DE ORO - Vender excedentes al mejor precio")
        elif not necesidades:
            print("\n✓ No necesitas más recursos.")
            return
        
        # 3. Filtrar personas (excluir alias propios y yo mismo)
        alias_propios = self.info_actual.get('Alias', [])
        personas_objetivo = [p for p in self.gente 
                            if p != self.alias and p not in alias_propios]
        
        print(f"\n👥 OBJETIVOS IDENTIFICADOS: {len(personas_objetivo)} personas")
        
        # 4. Identificar víctima para estafa (1 persona)
        victima = self.identificar_victima_estafa()
        if victima:
            print(f"\n🎯 VÍCTIMA IDENTIFICADA: {victima}")
            print("   Preparando oferta TRAMPA irresistible...")
        
        # 5. Generar y enviar propuestas a cada persona
        print("\n📤 ENVIANDO PROPUESTAS DE NEGOCIACIÓN...")
        print("-"*70)
        
        exitosas = 0
        for persona in personas_objetivo:
            # Determinar si es la víctima de estafa
            es_victima = (persona == victima)
            es_lista_negra = (persona in self.lista_negra)
            
            if es_victima:
                print(f"\n🎭 ESTAFANDO A: {persona} 💀")
            elif es_lista_negra:
                print(f"\n⚔️  VENGANZA CONTRA: {persona} (intentó robarnos)")
            else:
                print(f"\n🎲 Negociando con: {persona}")
            
            # Generar estrategia personalizada
            estrategia = self.generar_estrategia_negociacion(
                persona, necesidades, excedentes
            )
            
            print(f"  📋 Estrategia: {estrategia['descripcion_estrategia'][:100]}...")
            
            # Enviar carta
            if self.enviar_carta_negociacion(
                persona, 
                estrategia['asunto'], 
                estrategia['cuerpo']
            ):
                exitosas += 1
                self.historial_negociaciones[persona] = {
                    'estrategia': estrategia,
                    'timestamp': time.time()
                }
            
            # Pausa para no saturar la API
            time.sleep(0.5)
        
        print("\n" + "="*70)
        print(f"✓ Campaña completada: {exitosas}/{len(personas_objetivo)} cartas enviadas")
        print("="*70)
        
        # 5. Revisar respuestas
        print("\n📬 Revisando buzón...")
        cartas = self.revisar_buzon()
        
        if cartas:
            print(f"\n📨 {len(cartas)} mensajes encontrados:")
            for carta in cartas:
                print(f"\n  De: {carta.get('remi')}")
                print(f"  Asunto: {carta.get('asunto')}")
                print(f"  Mensaje: {carta.get('cuerpo')[:100]}...")
                
                # Analizar la respuesta
                print(f"\n  🧠 Analizando respuesta con IA...")
                analisis = self.analizar_respuesta(carta)
                print(f"  📊 Evaluación: {analisis['evaluacion']}")
                print(f"  🎯 Táctica recomendada: {analisis['tactica'][:150]}...")
        else:
            print("  ℹ️  No hay respuestas todavía. Revisa más tarde.")
    
    def modo_interactivo(self):
        """Modo interactivo para negociación manual asistida por IA"""
        while True:
            print("\n" + "="*70)
            print("🤖 BOT NEGOCIADOR - MODO INTERACTIVO")
            print("="*70)
            print("1. Ejecutar campaña automática")
            print("2. Revisar buzón y analizar respuestas")
            print("3. Enviar carta personalizada")
            print("4. Ver estado actual")
            print("5. Consultar estrategia para un objetivo")
            print("6. 🎭 ESTAFAR a alguien (oferta trampa)")
            print("7. 🛡️  Ver lista negra")
            print("0. Salir")
            print("="*70)
            
            opcion = input("\nSelecciona opción: ").strip()
            
            if opcion == "1":
                self.ejecutar_campana_negociacion()
            
            elif opcion == "2":
                self.obtener_info()
                cartas = self.revisar_buzon()
                if cartas:
                    for i, carta in enumerate(cartas, 1):
                        print(f"\n📧 Carta {i}:")
                        print(f"  De: {carta.get('remi')}")
                        print(f"  Asunto: {carta.get('asunto')}")
                        print(f"  Cuerpo: {carta.get('cuerpo')}")
                        
                        analisis = self.analizar_respuesta(carta)
                        print(f"\n  🧠 ANÁLISIS IA:")
                        print(f"  {analisis['respuesta_completa']}")
                else:
                    print("\nNo hay cartas en el buzón.")
            
            elif opcion == "3":
                dest = input("Destinatario: ").strip()
                if dest:
                    self.obtener_info()
                    necesidades = self.calcular_necesidades()
                    excedentes = self.identificar_excedentes()
                    
                    estrategia = self.generar_estrategia_negociacion(
                        dest, necesidades, excedentes
                    )
                    
                    print(f"\n📋 ESTRATEGIA GENERADA:")
                    print(f"Asunto: {estrategia['asunto']}")
                    print(f"Cuerpo: {estrategia['cuerpo']}")
                    print(f"Técnicas: {estrategia['descripcion_estrategia']}")
                    
                    if input("\n¿Enviar? (s/n): ").lower() == 's':
                        self.enviar_carta_negociacion(
                            dest, estrategia['asunto'], estrategia['cuerpo']
                        )
            
            elif opcion == "4":
                self.obtener_info()
                if self.info_actual:
                    oro = self.obtener_oro_actual()
                    necesidades = self.calcular_necesidades()
                    excedentes = self.identificar_excedentes()
                    objetivo_ok = self.objetivo_completado()
                    
                    print(f"\n📊 ESTADO ACTUAL:")
                    print(f"\n💰 ORO: {oro}")
                    print(f"✅ Objetivo completado: {'SÍ' if objetivo_ok else 'NO'}")
                    print(f"\n🎯 Recursos necesarios: {json.dumps(necesidades, ensure_ascii=False)}")
                    print(f"📦 Recursos excedentes: {json.dumps(excedentes, ensure_ascii=False)}")
                    
                    if objetivo_ok:
                        print(f"\n🏆 ESTADO: ACUMULACIÓN DE ORO")
                        print(f"   Vende tus excedentes al máximo precio posible")
                    
                    print(f"\n📋 Datos completos:")
                    print(json.dumps(self.info_actual, indent=2, ensure_ascii=False))
            
            elif opcion == "5":
                dest = input("¿Objetivo de negociación?: ").strip()
                if dest:
                    self.obtener_info()
                    necesidades = self.calcular_necesidades()
                    excedentes = self.identificar_excedentes()
                    
                    estrategia = self.generar_estrategia_negociacion(
                        dest, necesidades, excedentes
                    )
                    
                    print(f"\n🎯 ESTRATEGIA PARA {dest}:")
                    print(f"\nAsunto sugerido:\n{estrategia['asunto']}")
                    print(f"\nMensaje persuasivo:\n{estrategia['cuerpo']}")
                    print(f"\nTécnicas aplicadas:\n{estrategia['descripcion_estrategia']}")
            
            elif opcion == "6":
                dest = input("¿A quién quieres ESTAFAR?: ").strip()
                if dest:
                    print(f"\n🎭 Generando TRAMPA para {dest}...")
                    trampa = self.generar_oferta_trampa(dest)
                    
                    print(f"\n🎯 OFERTA TRAMPA GENERADA:")
                    print(f"\nAsunto: {trampa['asunto']}")
                    print(f"\nCuerpo: {trampa['cuerpo']}")
                    print(f"\n⚠️  IMPORTANTE: Una vez que te envíe recursos, NO CUMPLAS tu parte.")
                    print(f"   Simplemente ignora o responde con 'hubo un error'.")
                    
                    if input("\n¿Enviar trampa? (s/n): ").lower() == 's':
                        if self.enviar_carta_negociacion(dest, trampa['asunto'], trampa['cuerpo']):
                            print(f"✓ Trampa enviada a {dest}. Espera a que muerda el anzuelo...")
            
            elif opcion == "7":
                print("\n🛡️  LISTA NEGRA (intentaron robarnos):")
                if self.lista_negra:
                    for persona in self.lista_negra:
                        print(f"  ⚠️  {persona}")
                else:
                    print("  (vacía)")
                
                print("\n🎭 VÍCTIMAS DE NUESTRAS ESTAFAS:")
                if self.victimas_estafa:
                    for persona in self.victimas_estafa:
                        print(f"  💀 {persona}")
                else:
                    print("  (ninguna todavía)")
            
            elif opcion == "0":
                print("\n¡Hasta luego, negociador!")
                break
            else:
                print("Opción inválida")


def main():
    """Punto de entrada principal"""
    print("="*70)
    print("🤖 BOT NEGOCIADOR AUTOMÁTICO - Powered by Ollama + Qwen")
    print("="*70)
    
    # Configuración
    alias = input("\n¿Cuál es tu alias/nombre?: ").strip()
    if not alias:
        print("✗ Necesitas especificar tu alias")
        return
    
    modelo = "qwen3-vl:8b"
    print(f"\n{modelo}")
    
    # Crear bot
    bot = BotNegociador(alias, modelo)
    
    # Iniciar modo interactivo
    bot.modo_interactivo()


if __name__ == "__main__":
    main()
