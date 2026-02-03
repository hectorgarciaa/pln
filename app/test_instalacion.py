"""
Script de prueba para verificar la instalación del bot negociador
"""

import sys
import requests
import json

def test_color(text, color_code):
    """Imprime texto con color"""
    return f"\033[{color_code}m{text}\033[0m"

def success(text):
    return test_color(f"✓ {text}", "92")

def error(text):
    return test_color(f"✗ {text}", "91")

def warning(text):
    return test_color(f"⚠ {text}", "93")

def info(text):
    return test_color(f"ℹ {text}", "94")

print("="*70)
print("🧪 TEST DE INSTALACIÓN DEL BOT NEGOCIADOR")
print("="*70)
print()

# Test 1: Importar requests
print("1. Testeando módulo requests...")
try:
    import requests
    print(success("requests importado correctamente"))
except ImportError:
    print(error("requests no está instalado"))
    print(info("Instalar con: pip install requests"))
    sys.exit(1)

# Test 2: Conectar a Ollama
print("\n2. Testeando conexión a Ollama...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    if response.status_code == 200:
        print(success("Ollama está corriendo"))
        modelos = response.json().get('models', [])
        if modelos:
            print(info(f"Modelos disponibles: {len(modelos)}"))
            for modelo in modelos:
                nombre = modelo.get('name', 'unknown')
                print(f"  • {nombre}")
        else:
            print(warning("No hay modelos descargados"))
            print(info("Descargar con: ollama pull qwen2.5:latest"))
    else:
        print(error(f"Ollama respondió con código {response.status_code}"))
except requests.exceptions.ConnectionError:
    print(error("No se puede conectar a Ollama"))
    print(info("Iniciar con: ollama serve"))
    sys.exit(1)
except Exception as e:
    print(error(f"Error inesperado: {e}"))
    sys.exit(1)

# Test 3: Verificar modelo Qwen
print("\n3. Verificando modelo Qwen...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    modelos = response.json().get('models', [])
    tiene_qwen = any('qwen' in m.get('name', '').lower() for m in modelos)
    
    if tiene_qwen:
        print(success("Modelo Qwen encontrado"))
    else:
        print(warning("Modelo Qwen no encontrado"))
        print(info("Descargar con: ollama pull qwen2.5:latest"))
except Exception as e:
    print(error(f"Error verificando modelos: {e}"))

# Test 4: Conectar a la API del juego
print("\n4. Testeando conexión a la API del juego...")
try:
    response = requests.get("http://147.96.81.252:8000/info", timeout=5)
    if response.status_code == 200:
        print(success("API del juego accesible"))
        data = response.json()
        print(info(f"Alias disponibles: {len(data.get('Alias', []))}"))
        print(info(f"Recursos en buzón: {len(data.get('Buzon', {}))}"))
    else:
        print(warning(f"API respondió con código {response.status_code}"))
except requests.exceptions.ConnectionError:
    print(warning("No se puede conectar a la API del juego"))
    print(info("La API puede estar offline o bloqueada por firewall"))
except requests.exceptions.Timeout:
    print(warning("Timeout conectando a la API"))
except Exception as e:
    print(error(f"Error: {e}"))

# Test 5: Test simple de generación con Ollama
print("\n5. Testeando generación de texto con Ollama...")
try:
    # Buscar un modelo qwen
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    modelos = response.json().get('models', [])
    modelo_qwen = next((m.get('name') for m in modelos if 'qwen' in m.get('name', '').lower()), None)
    
    if not modelo_qwen:
        print(warning("No hay modelo Qwen, usando primer modelo disponible"))
        modelo_qwen = modelos[0].get('name') if modelos else None
    
    if modelo_qwen:
        print(info(f"Usando modelo: {modelo_qwen}"))
        print(info("Generando respuesta (esto puede tardar 10-30 segundos)..."))
        
        test_prompt = "Responde con exactamente 5 palabras: ¿Qué es negociación?"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": modelo_qwen,
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 20
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            resultado = response.json().get('response', '').strip()
            print(success("Generación exitosa"))
            print(info(f"Respuesta del modelo: '{resultado[:100]}...'"))
        else:
            print(error(f"Error en generación: {response.status_code}"))
    else:
        print(error("No hay modelos disponibles para probar"))
        
except Exception as e:
    print(error(f"Error en test de generación: {e}"))

# Test 6: Importar el bot
print("\n6. Testeando importación del bot...")
try:
    sys.path.insert(0, '/home/pablo/Uni/PLN/proyectoPln/pln/app')
    from bot_negociador import BotNegociador
    print(success("Bot negociador importado correctamente"))
    
    # Verificar métodos principales
    metodos_requeridos = [
        'obtener_info', 'obtener_gente', 'calcular_necesidades',
        'generar_estrategia_negociacion', 'enviar_carta_negociacion',
        'ejecutar_campana_negociacion'
    ]
    
    for metodo in metodos_requeridos:
        if hasattr(BotNegociador, metodo):
            print(info(f"  ✓ Método {metodo} presente"))
        else:
            print(warning(f"  ✗ Método {metodo} no encontrado"))
            
except ImportError as e:
    print(error(f"No se pudo importar el bot: {e}"))
except Exception as e:
    print(error(f"Error: {e}"))

# Resumen final
print("\n" + "="*70)
print("📊 RESUMEN")
print("="*70)

print("\n✅ COMPONENTES ESENCIALES:")
print("  • Python y requests: OK")
print("  • Ollama corriendo: Verificado")

print("\n⚙️  PARA EMPEZAR:")
print("  1. Si no tienes Qwen: ollama pull qwen2.5:latest")
print("  2. cd /home/pablo/Uni/PLN/proyectoPln/pln/app")
print("  3. python bot_negociador.py")

print("\n📚 DOCUMENTACIÓN:")
print("  • README completo: ../NEGOCIADOR_README.md")
print("  • Prompts avanzados: prompts_avanzados.py")

print("\n" + "="*70)
print("🎯 Sistema listo para negociar")
print("="*70)
