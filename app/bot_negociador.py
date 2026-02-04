import requests
import json
import time
from typing import Dict, List, Tuple
import re

BASE_URL = "http://147.96.81.252:8000"
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
            print("5. Consultar estrategia para un objetivo")
            print("6. 🛡️  Ver lista negra")
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
                print("\n🛡️  LISTA NEGRA (intentaron robarnos):")
                if self.lista_negra:
                    for persona in self.lista_negra:
                        print(f"  ⚠️  {persona}")
                else:
                    print("  (vacía - nadie ha intentado robar)")
            
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
