import requests
import json
import time
from typing import Dict, List, Tuple, Optional
import re

BASE_URL = "http://147.96.81.252:7719"
OLLAMA_URL = "http://localhost:11434"


class BotNegociador:
    """
    Bot de negociación amigable que usa Ollama con Qwen para conseguir recursos.
    Implementa estrategias de negociación colaborativas y justas.
    INCLUYE: Sistema anti-robos para protección.
    """
    
    def __init__(self, alias: str, modelo: str = "qwen3-vl:8b"):
        self.alias = alias
        self.modelo = modelo
        self.info_actual = None
        self.gente = []
        self.historial_negociaciones = {}
        self.lista_negra = []  # Personas que intentaron robarnos
        self.acuerdos_pendientes = {}  # Acuerdos negociados pendientes de ejecutar
        self.intercambios_realizados = []  # Historial de intercambios completados
        
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
    
    def consultar_ollama(self, prompt: str, timeout: int = 60, usar_fallback: bool = True) -> str:
        """Consulta a Ollama con el modelo Qwen - OPTIMIZADO PARA VELOCIDAD"""
        try:
            print("  ⏳ Consultando IA...", end='', flush=True)
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    # PARÁMETROS OPTIMIZADOS PARA VELOCIDAD:
                    "temperature": 0.3,        # Más bajo = más rápido y determinista (0.1-0.5)
                    "top_p": 0.7,             # Más bajo = respuestas más enfocadas
                    "top_k": 20,              # Limita opciones de tokens
                    "repeat_penalty": 1.2,    # Evita repeticiones
                    "num_predict": 150,       # Máximo 150 tokens (respuestas cortas)
                    "num_ctx": 1024,          # Contexto reducido = más rápido
                    "stop": ["\n\n", "---"],  # Para en saltos de línea dobles
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
        """Detecta si una oferta es un intento de robo"""
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
            prompt = f"""¿Es robo? Responde ROBO o LEGIT en una palabra.
Mensaje: {mensaje[:200]}"""
            respuesta = self.consultar_ollama(prompt, timeout=30, usar_fallback=False)
            
            es_robo = "ROBO" in respuesta.upper() if respuesta else False
            
            if es_robo and remitente not in self.lista_negra:
                self.lista_negra.append(remitente)
                print(f"⚠️  ALERTA: {remitente} intentó robar (IA). Lista negra.")
            
            return es_robo
        
        return False
    

    def enviar_paquete(self, destinatario: str, recursos: Dict[str, int]) -> bool:
        """
        Envía un paquete de recursos a otro jugador.
        
        Args:
            destinatario: Nombre del destinatario
            recursos: Diccionario con recursos a enviar (ej: {"oro": 100, "madera": 50})
        
        Returns:
            True si el envío fue exitoso
        """
        if not recursos:
            print("⚠️ No hay recursos para enviar")
            return False
        
        # Verificar que tenemos los recursos suficientes
        self.obtener_info()
        mis_recursos = self.info_actual.get('Recursos', {})
        
        for recurso, cantidad in recursos.items():
            if mis_recursos.get(recurso, 0) < cantidad:
                print(f"⚠️ No tienes suficiente {recurso} (tienes {mis_recursos.get(recurso, 0)}, necesitas {cantidad})")
                return False
        
        try:
            response = requests.post(
                f"{BASE_URL}/paquete",
                params={"dest": destinatario},
                json=recursos
            )
            
            if response.status_code == 200:
                print(f"✅ Paquete enviado a {destinatario}: {recursos}")
                self.intercambios_realizados.append({
                    'tipo': 'enviado',
                    'destinatario': destinatario,
                    'recursos': recursos,
                    'timestamp': time.time()
                })
                return True
            elif response.status_code == 422:
                print(f"⚠️ Error de validación: {response.json()}")
                return False
            else:
                print(f"⚠️ Error enviando paquete: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️ Error de conexión: {e}")
            return False
    
    def detectar_aceptacion(self, carta: Dict) -> Optional[Dict]:
        """
        Detecta si un mensaje contiene una aceptación de intercambio.
        Extrae los términos del acuerdo si los hay.
        
        Returns:
            Dict con los términos del acuerdo o None si no hay aceptación
        """
        mensaje = carta.get('cuerpo', '').lower()
        remitente = carta.get('remi', '')
        
        # Palabras que indican aceptación
        palabras_aceptacion = [
            'acepto', 'trato hecho', 'de acuerdo', 'ok', 'vale', 'perfecto',
            'hecho', 'me parece bien', 'aceptado', 'sí', 'claro', 'por supuesto',
            'enviado', 'te envío', 'ahí va', 'recibido', 'gracias por'
        ]
        
        # Palabras que indican rechazo
        palabras_rechazo = [
            'no acepto', 'no me interesa', 'no gracias', 'rechazo', 'no puedo',
            'muy caro', 'demasiado', 'no tengo', 'no quiero'
        ]
        
        # Verificar rechazo primero
        for palabra in palabras_rechazo:
            if palabra in mensaje:
                return None
        
        # Verificar aceptación
        hay_aceptacion = any(palabra in mensaje for palabra in palabras_aceptacion)
        
        if not hay_aceptacion:
            # Usar IA para casos ambiguos
            prompt = f"""¿Este mensaje acepta un intercambio? Responde solo ACEPTA o RECHAZA.
Mensaje: {mensaje[:200]}"""
            respuesta = self.consultar_ollama(prompt, timeout=30, usar_fallback=False)
            hay_aceptacion = "ACEPTA" in respuesta.upper() if respuesta else False
        
        if hay_aceptacion:
            # Intentar extraer términos del acuerdo
            terminos = self.extraer_terminos_intercambio(mensaje)
            return {
                'remitente': remitente,
                'aceptacion': True,
                'terminos': terminos,
                'mensaje_original': carta.get('cuerpo', '')
            }
        
        return None
    
    def extraer_terminos_intercambio(self, mensaje: str) -> Dict:
        """
        Extrae los recursos y cantidades mencionados en un mensaje.
        
        Returns:
            Dict con 'ofrece' y 'pide' que contienen los recursos
        """
        recursos_conocidos = ['oro', 'madera', 'piedra', 'comida', 'hierro', 'trigo', 
                             'carbon', 'agua', 'plata', 'cobre', 'diamante', 'lana',
                             'tela', 'cuero', 'cristal', 'acero']
        
        terminos = {'ofrece': {}, 'pide': {}}
        
        # Buscar patrones como "100 oro", "50 de madera", etc.
        patron = r'(\d+)\s*(?:de\s+)?(' + '|'.join(recursos_conocidos) + r')'
        matches = re.findall(patron, mensaje.lower())
        
        for cantidad, recurso in matches:
            # Por defecto, asumimos que lo que menciona es lo que ofrece
            terminos['ofrece'][recurso] = int(cantidad)
        
        # Si no se encontró nada, usar IA
        if not terminos['ofrece']:
            prompt = f"""Del mensaje, extrae recursos y cantidades. Formato: RECURSO:CANTIDAD
Mensaje: {mensaje[:200]}
Respuesta (ej: oro:100, madera:50):"""
            
            respuesta = self.consultar_ollama(prompt, timeout=30, usar_fallback=False)
            if respuesta:
                # Parsear respuesta de IA
                for match in re.findall(r'(\w+):(\d+)', respuesta.lower()):
                    recurso, cantidad = match
                    if recurso in recursos_conocidos:
                        terminos['ofrece'][recurso] = int(cantidad)
        
        return terminos
    
    def ejecutar_intercambio(self, acuerdo: Dict) -> bool:
        """
        Ejecuta un intercambio acordado enviando los recursos.
        
        Args:
            acuerdo: Dict con 'remitente' y 'terminos' del intercambio
        
        Returns:
            True si el intercambio se ejecutó correctamente
        """
        remitente = acuerdo.get('remitente')
        terminos = acuerdo.get('terminos', {})
        
        if not remitente:
            print("⚠️ No se especificó el remitente")
            return False
        
        # Verificar si está en lista negra
        if remitente in self.lista_negra:
            print(f"🚨 {remitente} está en la lista negra. No se ejecutará el intercambio.")
            return False
        
        # Determinar qué debemos enviar nosotros
        # Esto depende de lo que habíamos ofrecido en la negociación
        if remitente in self.historial_negociaciones:
            negociacion = self.historial_negociaciones[remitente]
            # Buscar en el cuerpo del mensaje qué ofrecimos
            cuerpo = negociacion.get('estrategia', {}).get('cuerpo', '')
            nuestros_terminos = self.extraer_terminos_intercambio(cuerpo)
            
            if nuestros_terminos.get('ofrece'):
                print(f"\n📦 Preparando envío a {remitente}:")
                print(f"   Recursos: {nuestros_terminos['ofrece']}")
                
                confirmacion = input("\n¿Confirmar envío? (s/n): ").lower()
                if confirmacion == 's':
                    return self.enviar_paquete(remitente, nuestros_terminos['ofrece'])
                else:
                    print("❌ Envío cancelado")
                    return False
        
        # Si no hay historial, preguntar qué enviar
        print(f"\n📦 Intercambio con {remitente}")
        print("No se encontró un acuerdo previo. ¿Qué deseas enviar?")
        
        self.obtener_info()
        excedentes = self.identificar_excedentes()
        print(f"Tus excedentes: {excedentes}")
        
        recursos_a_enviar = {}
        while True:
            recurso = input("Recurso a enviar (o 'fin' para terminar): ").strip().lower()
            if recurso == 'fin':
                break
            cantidad = input(f"Cantidad de {recurso}: ").strip()
            if cantidad.isdigit():
                recursos_a_enviar[recurso] = int(cantidad)
        
        if recursos_a_enviar:
            return self.enviar_paquete(remitente, recursos_a_enviar)
        
        return False
    
    def procesar_respuestas_automatico(self) -> List[Dict]:
        """
        Procesa automáticamente las respuestas del buzón.
        Detecta aceptaciones y ejecuta intercambios.
        
        Returns:
            Lista de acuerdos detectados
        """
        self.obtener_info()
        cartas = self.revisar_buzon()
        
        acuerdos_detectados = []
        
        print(f"\n📬 Procesando {len(cartas)} mensajes...")
        
        for carta in cartas:
            remitente = carta.get('remi', 'Desconocido')
            
            # Saltar lista negra
            if remitente in self.lista_negra:
                print(f"⚠️ Ignorando mensaje de {remitente} (lista negra)")
                continue
            
            # Detectar si es un intento de robo
            if self.detectar_intento_robo(carta):
                print(f"🚨 Intento de robo detectado de {remitente}")
                continue
            
            # Detectar si es una aceptación
            acuerdo = self.detectar_aceptacion(carta)
            
            if acuerdo:
                print(f"\n✅ ACEPTACIÓN DETECTADA de {remitente}!")
                print(f"   Mensaje: {carta.get('cuerpo', '')[:100]}...")
                
                if acuerdo.get('terminos', {}).get('ofrece'):
                    print(f"   Términos detectados: {acuerdo['terminos']}")
                
                acuerdos_detectados.append(acuerdo)
                self.acuerdos_pendientes[remitente] = acuerdo
            else:
                # No es aceptación, analizar como contraoferta
                print(f"\n💬 Mensaje de {remitente}: {carta.get('cuerpo', '')[:80]}...")
                analisis = self.analizar_respuesta(carta)
                print(f"   Evaluación: {analisis.get('evaluacion', 'Sin evaluar')}")
        
        if acuerdos_detectados:
            print(f"\n🎉 {len(acuerdos_detectados)} acuerdo(s) pendiente(s) de ejecutar")
            
        return acuerdos_detectados
    
    def ciclo_negociacion_completo(self, max_rondas: int = 3):
        """
        Ejecuta un ciclo completo de negociación:
        1. Envía propuestas
        2. Espera respuestas
        3. Detecta aceptaciones
        4. Ejecuta intercambios
        
        Args:
            max_rondas: Número máximo de rondas de negociación
        """
        print("="*70)
        print("🔄 CICLO DE NEGOCIACIÓN COMPLETO")
        print("="*70)
        
        for ronda in range(1, max_rondas + 1):
            print(f"\n{'='*70}")
            print(f"📍 RONDA {ronda} de {max_rondas}")
            print("="*70)
            
            # 1. Ejecutar campaña de negociación
            self.ejecutar_campana_negociacion()
            
            # 2. Esperar respuestas
            print(f"\n⏳ Esperando respuestas (30 segundos)...")
            time.sleep(30)
            
            # 3. Procesar respuestas
            acuerdos = self.procesar_respuestas_automatico()
            
            # 4. Ejecutar intercambios pendientes
            if acuerdos:
                print(f"\n📦 EJECUTANDO INTERCAMBIOS...")
                for acuerdo in acuerdos:
                    print(f"\n→ Procesando acuerdo con {acuerdo['remitente']}...")
                    self.ejecutar_intercambio(acuerdo)
            
            # 5. Verificar si completamos el objetivo
            self.obtener_info()
            if self.objetivo_completado():
                print(f"\n🏆 ¡OBJETIVO COMPLETADO en ronda {ronda}!")
                break
            
            # Pausa entre rondas
            if ronda < max_rondas:
                print(f"\n⏳ Pausa antes de la siguiente ronda...")
                time.sleep(10)
        
        # Resumen final
        print("\n" + "="*70)
        print("📊 RESUMEN DE NEGOCIACIONES")
        print("="*70)
        print(f"Intercambios realizados: {len(self.intercambios_realizados)}")
        for intercambio in self.intercambios_realizados:
            print(f"  → {intercambio['tipo']} a {intercambio.get('destinatario', 'N/A')}: {intercambio['recursos']}")
        
        self.obtener_info()
        print(f"\nEstado final:")
        print(f"  Oro: {self.obtener_oro_actual()}")
        print(f"  Objetivo completado: {'✅ SÍ' if self.objetivo_completado() else '❌ NO'}")

    
    def generar_estrategia_negociacion(self, destinatario: str, necesidades: Dict[str, int], 
                                       excedentes: Dict[str, int]) -> Dict:
        """
        Genera una estrategia de negociación sofisticada usando IA.
        Incluye técnicas de persuasión, anclaje, escasez y maximización de oro.
        CON protección anti-robos.
        """
        oro_actual = self.obtener_oro_actual()
        objetivo_completo = self.objetivo_completado()
        
        # Si ya completamos el objetivo, el foco es vender excedentes
        if objetivo_completo:
            enfoque = "VENDER excedentes de forma justa"
        else:
            enfoque = "INTERCAMBIAR recursos de forma colaborativa"
        
        prompt = f"""Negociador amigable y justo. Objetivo: {enfoque}

Tú: {self.alias}, Oro: {oro_actual}
Destinatario: {destinatario}
Necesitas: {json.dumps(necesidades, ensure_ascii=False)}
Tienes: {json.dumps(excedentes, ensure_ascii=False)}

Genera carta amigable (max 200 chars):
- Tono colaborativo
- Intercambio justo
- Beneficio mutuo

FORMATO:
ASUNTO: [título amigable]
CUERPO: [mensaje colaborativo]"""
        
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
        
        # Si no se parseó correctamente, usar fallback COLABORATIVO
        if not estrategia['asunto'] or not estrategia['cuerpo']:
            # Generar mensaje basado en necesidades reales
            if necesidades:
                primer_recurso = list(necesidades.keys())[0]
                cantidad = necesidades[primer_recurso]
                estrategia['asunto'] = f"🤝 Propuesta de intercambio - {primer_recurso}"
                
                if excedentes:
                    primer_excedente = list(excedentes.keys())[0]
                    cant_excedente = excedentes[primer_excedente]
                    estrategia['cuerpo'] = f"Hola {destinatario}! Busco {cantidad} de {primer_recurso}. Tengo {cant_excedente} {primer_excedente} para intercambiar. ¿Te interesa un trueque justo? ¡Saludos!"
                else:
                    estrategia['cuerpo'] = f"Hola {destinatario}! Necesito {cantidad} de {primer_recurso}. Puedo pagar en oro a precio justo. ¿Tienes disponible? ¡Gracias!"
            elif excedentes:
                # Solo oferta de venta
                primer_excedente = list(excedentes.keys())[0]
                cant_excedente = excedentes[primer_excedente]
                estrategia['asunto'] = f"💼 Ofrezco {primer_excedente}"
                estrategia['cuerpo'] = f"Hola {destinatario}! Tengo {cant_excedente} {primer_excedente} disponible. Si te interesa, hablamos precio justo. ¡Saludos!"
            else:
                estrategia['asunto'] = f"👋 Hola desde {self.alias}"
                estrategia['cuerpo'] = f"Hola {destinatario}! ¿Qué recursos tienes disponibles? Podemos hacer un intercambio colaborativo. ¡Saludos!"
        
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
        Analiza una respuesta recibida y genera una contra-oferta constructiva.
        Detecta oportunidades para intercambios justos y INTENTOS DE ROBO.
        """
        # PRIMERO: Detectar si es intento de robo
        if self.detectar_intento_robo(carta):
            return {
                'evaluacion': 'INTENTO DE ROBO DETECTADO',
                'debilidades': 'Intentó robarnos',
                'contraoferta': 'IGNORAR - No es confiable',
                'tactica': f'Añadido {carta.get("remi")} a lista negra. No negociar.',
                'respuesta_completa': '🚨 ALERTA: Esta persona intentó robarte. No negociar.'
            }
        
        oro_actual = self.obtener_oro_actual()
        objetivo_completo = self.objetivo_completado()
        
        prompt = f"""Analiza oferta. Responde colaborativo.

Oro actual: {oro_actual}
De: {carta.get('remi')}
Mensaje: {carta.get('cuerpo')[:150]}

Respuesta corta:
EVALUACION: [interesante/no interesante]
TACTICA: [cómo responder]"""
        
        respuesta = self.consultar_ollama(prompt)
        
        analisis = {
            'evaluacion': '',
            'debilidades': '',
            'contraoferta': '',
            'tactica': '',
            'respuesta_completa': respuesta
        }
        
        # Parsear respuesta
        eval_match = re.search(r'EVALUACION:\s*(.+?)(?=TACTICA:|$)', respuesta, re.DOTALL)
        tac_match = re.search(r'TACTICA:\s*(.+)', respuesta, re.DOTALL)
        
        if eval_match:
            analisis['evaluacion'] = eval_match.group(1).strip()
        if tac_match:
            analisis['tactica'] = tac_match.group(1).strip()
        
        return analisis
    
    def revisar_buzon(self, auto_limpiar: bool = False) -> List[Dict]:
        """Revisa el buzón en busca de respuestas"""
        if not self.info_actual:
            self.obtener_info()
        
        buzon = self.info_actual.get('Buzon', {})
        cartas_relevantes = []
        
        # Avisar si el buzón está muy lleno
        if len(buzon) > 50:
            print(f"\n⚠️  BUZÓN LLENO: {len(buzon)} cartas")
            if auto_limpiar:
                print("🧹 Activando limpieza automática...")
                self.limpiar_buzon_automatico()
                self.obtener_info()
                buzon = self.info_actual.get('Buzon', {})
        
        for uid, carta in buzon.items():
            # Solo cartas dirigidas a nosotros
            if carta.get('dest') == self.alias:
                cartas_relevantes.append({**carta, 'uid': uid})
        
        return cartas_relevantes
    
    def borrar_carta(self, uid: str) -> bool:
        """Elimina una carta del buzón por su UID"""
        try:
            response = requests.delete(f"{BASE_URL}/mail/{uid}")
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            print(f"✗ Error borrando carta: {e}")
            return False
    
    def limpiar_buzon_automatico(self, mantener_ultimas: int = 10):
        """Limpieza automática inteligente del buzón"""
        if not self.info_actual:
            self.obtener_info()
        
        buzon = self.info_actual.get('Buzon', {})
        
        if not buzon:
            print("\n✓ El buzón está vacío")
            return
        
        print(f"\n🧹 Limpieza automática del buzón ({len(buzon)} cartas)...")
        
        borradas = 0
        importantes = []
        
        for uid, carta in buzon.items():
            remitente = carta.get('remi', 'Desconocido')
            
            # Borrar cartas de lista negra automáticamente
            if remitente in self.lista_negra:
                print(f"  🗑️  Borrando carta de {remitente} (lista negra)")
                if self.borrar_carta(uid):
                    borradas += 1
                continue
            
            # Borrar cartas que no son para nosotros
            if carta.get('dest') != self.alias:
                if self.borrar_carta(uid):
                    borradas += 1
                continue
            
            # Guardar las demás como importantes
            importantes.append((uid, carta))
        
        # Si aún hay muchas, borrar las más antiguas
        if len(importantes) > mantener_ultimas:
            print(f"  📦 Manteniendo solo las {mantener_ultimas} más recientes...")
            # Borrar las primeras (más antiguas)
            cartas_a_borrar = importantes[:-mantener_ultimas]
            
            for uid, carta in cartas_a_borrar:
                if self.borrar_carta(uid):
                    borradas += 1
        
        print(f"\n✓ {borradas} cartas eliminadas automáticamente")
        restantes = len(importantes) - (len(importantes) - mantener_ultimas if len(importantes) > mantener_ultimas else 0)
        print(f"📬 Buzón: {restantes} cartas restantes")
    
    def ejecutar_campana_negociacion(self, objetivo_prioritario: str = None):
        """
        Ejecuta una campaña completa de negociación automática.
        Contacta a múltiples personas con estrategias personalizadas.
        """
        print("="*70)
        print("🤖 INICIANDO BOT DE NEGOCIACIÓN COLABORATIVO")
        print("🛡️  Protección anti-robos: ACTIVADA")
        print("🤝 Modo: Intercambios justos y colaborativos")
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
        
        # 4. Generar y enviar propuestas a cada persona
        print("\n📤 ENVIANDO PROPUESTAS DE NEGOCIACIÓN...")
        print("-"*70)
        
        exitosas = 0
        for persona in personas_objetivo:
            es_lista_negra = (persona in self.lista_negra)
            
            if es_lista_negra:
                print(f"\n⚠️  EVITANDO: {persona} (lista negra)")
                continue
            else:
                print(f"\n🤝 Negociando con: {persona}")
            
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
            print("5. 🛡️  Ver lista negra")
            print(f"6. ⚡ Cambiar modelo (actual: {self.modelo})")
            print("7. 🧹 Limpieza automática del buzón")
            print("8. 📦 Enviar paquete de recursos")
            print("9. 🔄 Ciclo de negociación completo (auto)")
            print("10. ✅ Procesar aceptaciones y ejecutar intercambios")
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
                print("\n🛡️  LISTA NEGRA (intentaron robarnos):")
                if self.lista_negra:
                    for persona in self.lista_negra:
                        print(f"  ⚠️  {persona}")
                else:
                    print("  (vacía - nadie ha intentado robar)")
            
            elif opcion == "6":
                print("\n⚡ CAMBIAR MODELO")
                print("="*50)
                print(f"Modelo actual: {self.modelo}")
                print("\nModelos disponibles:")
                print("1. llama3.2:3b       [⚡⚡⚡ ULTRA RÁPIDO - 3-5s]")
                print("2. qwen3-vl:8b       [⚡⚡  Balance - 5-10s]")
                print("3. qwen2.5:7b        [⚡   Calidad - 10-15s]")
                print("4. phi3:mini         [⚡⚡⚡ Muy rápido - 3-5s]")
                print("5. Personalizado     [Escribe el nombre]")
                print("="*50)
                
                modelo_opcion = input("Selecciona modelo (1-5): ").strip()
                
                modelos = {
                    "1": "llama3.2:3b",
                    "2": "qwen3-vl:8b",
                    "3": "qwen2.5:7b",
                    "4": "phi3:mini"
                }
                
                if modelo_opcion in modelos:
                    modelo_anterior = self.modelo
                    self.modelo = modelos[modelo_opcion]
                    print(f"\n✓ Modelo cambiado: {modelo_anterior} → {self.modelo}")
                    print(f"💡 Tip: Asegúrate de tener el modelo descargado: ollama pull {self.modelo}")
                elif modelo_opcion == "5":
                    modelo_custom = input("Nombre del modelo: ").strip()
                    if modelo_custom:
                        self.modelo = modelo_custom
                        print(f"\n✓ Modelo cambiado a: {self.modelo}")
                else:
                    print("\n✗ Opción inválida")
            
            elif opcion == "7":
                print("\n🧹 LIMPIEZA AUTOMÁTICA DEL BUZÓN")
                print("="*50)
                mantener = input("¿Cuántas cartas mantener? (default 10): ").strip()
                mantener = int(mantener) if mantener.isdigit() else 10
                
                self.obtener_info()
                buzon = self.info_actual.get('Buzon', {})
                print(f"\nCartas actuales: {len(buzon)}")
                
                if len(buzon) > 0:
                    confirmar = input(f"¿Proceder con limpieza automática? (s/n): ").lower()
                    if confirmar == 's':
                        self.limpiar_buzon_automatico(mantener_ultimas=mantener)
                    else:
                        print("\n✗ Limpieza cancelada")
                else:
                    print("\n✓ El buzón ya está vacío")
            
            elif opcion == "8":
                print("\n📦 ENVIAR PAQUETE DE RECURSOS")
                print("="*50)
                
                self.obtener_info()
                mis_recursos = self.info_actual.get('Recursos', {})
                print(f"\nTus recursos actuales: {json.dumps(mis_recursos, ensure_ascii=False)}")
                
                dest = input("\nDestinatario: ").strip()
                if not dest:
                    print("✗ Debes especificar un destinatario")
                    continue
                
                recursos_a_enviar = {}
                print("\nIntroduce los recursos a enviar (escribe 'fin' para terminar):")
                
                while True:
                    recurso = input("  Recurso: ").strip().lower()
                    if recurso == 'fin':
                        break
                    if recurso not in mis_recursos:
                        print(f"  ⚠️ No tienes {recurso}")
                        continue
                    cantidad = input(f"  Cantidad de {recurso}: ").strip()
                    if cantidad.isdigit():
                        cant_int = int(cantidad)
                        if cant_int <= mis_recursos.get(recurso, 0):
                            recursos_a_enviar[recurso] = cant_int
                        else:
                            print(f"  ⚠️ Solo tienes {mis_recursos.get(recurso, 0)} de {recurso}")
                
                if recursos_a_enviar:
                    print(f"\n📦 Resumen del envío:")
                    print(f"   Destinatario: {dest}")
                    print(f"   Recursos: {recursos_a_enviar}")
                    
                    confirmar = input("\n¿Confirmar envío? (s/n): ").lower()
                    if confirmar == 's':
                        self.enviar_paquete(dest, recursos_a_enviar)
                    else:
                        print("✗ Envío cancelado")
                else:
                    print("✗ No se especificaron recursos")
            
            elif opcion == "9":
                print("\n🔄 CICLO DE NEGOCIACIÓN COMPLETO")
                print("="*50)
                print("Este modo ejecuta automáticamente:")
                print("  1. Envía propuestas de negociación")
                print("  2. Espera respuestas")
                print("  3. Detecta aceptaciones")
                print("  4. Ejecuta intercambios")
                print("="*50)
                
                rondas = input("\n¿Cuántas rondas máximo? (default 3): ").strip()
                rondas = int(rondas) if rondas.isdigit() else 3
                
                confirmar = input(f"\n¿Iniciar ciclo de {rondas} rondas? (s/n): ").lower()
                if confirmar == 's':
                    self.ciclo_negociacion_completo(max_rondas=rondas)
                else:
                    print("✗ Ciclo cancelado")
            
            elif opcion == "10":
                print("\n✅ PROCESAR ACEPTACIONES E INTERCAMBIOS")
                print("="*50)
                
                acuerdos = self.procesar_respuestas_automatico()
                
                if acuerdos:
                    print(f"\n🎉 Se detectaron {len(acuerdos)} aceptación(es)")
                    
                    for i, acuerdo in enumerate(acuerdos, 1):
                        print(f"\n--- Acuerdo {i} ---")
                        print(f"De: {acuerdo['remitente']}")
                        print(f"Términos: {acuerdo.get('terminos', {})}")
                        
                        ejecutar = input(f"\n¿Ejecutar intercambio con {acuerdo['remitente']}? (s/n): ").lower()
                        if ejecutar == 's':
                            self.ejecutar_intercambio(acuerdo)
                else:
                    print("\n❌ No se detectaron aceptaciones en el buzón")
                
                # Mostrar acuerdos pendientes
                if self.acuerdos_pendientes:
                    print(f"\n📋 Acuerdos pendientes: {len(self.acuerdos_pendientes)}")
                    for persona, acuerdo in self.acuerdos_pendientes.items():
                        print(f"  → {persona}")
            
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
