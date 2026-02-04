import requests
import json
from bot_negociador import BotNegociador

BASE_URL = "http://147.96.81.252:7719"

def mostrar_menu():
    """Muestra el menú principal con todas las opciones disponibles"""
    print("\n" + "="*60)
    print("API - MENÚ PRINCIPAL")
    print("="*60)
    print("1. GET /info - Obtener información general")
    print("2. GET /gente - Obtener lista de personas")
    print("3. POST /alias/{nombre} - Añadir un alias")
    print("4. DELETE /alias/{nombre} - Eliminar un alias")
    print("5. POST /carta - Enviar una carta")
    print("6. POST /paquete - Enviar un paquete")
    print("7. DELETE /mail/{uid} - Eliminar un mail")
    print("8. 🤖 BOT NEGOCIADOR - Negociación automática con IA")
    print("0. Salir")
    print("="*60)

def get_info():
    """GET /info - Obtiene información general"""
    url = f"{BASE_URL}/info"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Información obtenida con éxito:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def get_gente():
    """GET /gente - Obtiene la lista de personas"""
    url = f"{BASE_URL}/gente"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Lista de personas:")
            for persona in data:
                print(f"  - {persona}")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def add_alias():
    """POST /alias/{nombre} - Añade un alias"""
    nombre = input("Introduce el nombre del alias: ").strip()
    if not nombre:
        print("✗ El nombre no puede estar vacío")
        return
    
    url = f"{BASE_URL}/alias/{nombre}"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print(f"✓ Alias '{nombre}' añadido con éxito")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def delete_alias():
    """DELETE /alias/{nombre} - Elimina un alias"""
    nombre = input("Introduce el nombre del alias a eliminar: ").strip()
    if not nombre:
        print("✗ El nombre no puede estar vacío")
        return
    
    url = f"{BASE_URL}/alias/{nombre}"
    try:
        response = requests.delete(url)
        if response.status_code == 200:
            print(f"✓ Alias '{nombre}' eliminado correctamente")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def send_carta():
    """POST /carta - Envía una carta"""
    print("\n--- Enviar Carta ---")
    remi = input("Remitente: ").strip()
    dest = input("Destinatario: ").strip()
    asunto = input("Asunto: ").strip()
    cuerpo = input("Cuerpo del mensaje: ").strip()
    id_carta = input("ID de la carta: ").strip()
    
    if not all([remi, dest, asunto, cuerpo, id_carta]):
        print("✗ Todos los campos son obligatorios")
        return
    
    url = f"{BASE_URL}/carta"
    carta_data = {
        "remi": remi,
        "dest": dest,
        "asunto": asunto,
        "cuerpo": cuerpo,
        "id": id_carta
    }
    
    try:
        response = requests.post(url, json=carta_data)
        if response.status_code == 200:
            print("✓ Carta enviada con éxito")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def send_paquete():
    """POST /paquete - Envía un paquete"""
    print("\n--- Enviar Paquete ---")
    dest = input("Destinatario: ").strip()
    if not dest:
        print("✗ El destinatario es obligatorio")
        return
    
    print("\nIntroduce los recursos (deja vacío para terminar):")
    recursos = {}
    while True:
        recurso = input("  Nombre del recurso (o Enter para terminar): ").strip()
        if not recurso:
            break
        try:
            cantidad = int(input(f"  Cantidad de {recurso}: ").strip())
            recursos[recurso] = cantidad
        except ValueError:
            print("  ✗ La cantidad debe ser un número entero")
    
    if not recursos:
        print("✗ Debes especificar al menos un recurso")
        return
    
    url = f"{BASE_URL}/paquete"
    params = {"dest": dest}
    
    try:
        response = requests.post(url, params=params, json=recursos)
        if response.status_code == 200:
            print("✓ Paquete enviado con éxito")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def delete_mail():
    """DELETE /mail/{uid} - Elimina un mail"""
    uid = input("Introduce el UID del mail a eliminar: ").strip()
    if not uid:
        print("✗ El UID no puede estar vacío")
        return
    
    url = f"{BASE_URL}/mail/{uid}"
    try:
        response = requests.delete(url)
        if response.status_code == 200:
            print(f"✓ Mail con UID '{uid}' eliminado correctamente")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def ejecutar_bot_negociador():
    """🤖 Ejecuta el bot negociador con IA (Ollama)"""
    print("\n" + "="*60)
    print("🤖 BOT NEGOCIADOR - IA con Ollama")
    print("="*60)
    
    alias = input("Introduce tu alias/nombre: ").strip()
    if not alias:
        print("✗ El alias no puede estar vacío")
        return
    
    # Opciones de modelo
    print("\nModelos disponibles:")
    print("1. qwen3-vl:8b (Recomendado - Rápido)")
    print("2. llama3.2:3b (Alternativa - Más rápido aún)")
    print("3. qwen2.5:7b (Alternativa)")
    modelo_opcion = input("Selecciona modelo (1-3) [1]: ").strip() or "1"
    
    modelos = {
        "1": "qwen3-vl:8b",
        "2": "llama3.2:3b",
        "3": "qwen2.5:7b"
    }
    modelo = modelos.get(modelo_opcion, "qwen3-vl:8b")
    
    print(f"\n⚙️  Configuración:")
    print(f"   Alias: {alias}")
    print(f"   Modelo: {modelo}")
    print(f"   Optimización: VELOCIDAD (temp=0.3, max_tokens=150)")
    print("\n💡 Tip: Asegúrate de tener Ollama corriendo ('ollama serve')\n")
    
    try:
        # Crear instancia del bot
        bot = BotNegociador(alias=alias, modelo=modelo)
        
        # Menú del bot
        while True:
            print("\n" + "-"*60)
            print("OPCIONES DEL BOT:")
            print("1. 📊 Ver estado actual")
            print("2. 🎯 Iniciar negociación automática")
            print("3. 📬 Revisar buzón y analizar ofertas")
            print("4. 🔄 Ejecutar ciclo completo (negociar + revisar)")
            print("0. ⬅️  Volver al menú principal")
            print("-"*60)
            
            opcion_bot = input("Opción: ").strip()
            
            if opcion_bot == "1":
                # Ver estado
                print("\n📊 Obteniendo información...")
                info = bot.obtener_info()
                if info:
                    print("\n✓ Estado actual:")
                    print(f"  Recursos: {info.get('Recursos', {})}")
                    print(f"  Objetivo: {info.get('Objetivo', {})}")
                    print(f"  Oro: {bot.obtener_oro_actual()}")
                    necesidades = bot.calcular_necesidades()
                    print(f"  Necesitas: {necesidades if necesidades else 'Objetivo completo ✓'}")
                    excedentes = bot.identificar_excedentes()
                    print(f"  Excedentes: {excedentes if excedentes else 'Ninguno'}")
            
            elif opcion_bot == "2":
                # Negociación automática
                print("\n🎯 Iniciando negociación...")
                max_personas = input("¿A cuántas personas contactar? [3]: ").strip() or "3"
                try:
                    max_personas = int(max_personas)
                except ValueError:
                    max_personas = 3
                
                bot.obtener_info()
                gente = bot.obtener_gente()
                
                if not gente:
                    print("✗ No hay personas disponibles")
                    continue
                
                print(f"\nPersonas disponibles: {len(gente)}")
                print(f"Contactando a las primeras {min(max_personas, len(gente))}...\n")
                
                contactados = 0
                for persona in gente[:max_personas]:
                    if persona == alias:
                        continue
                    
                    print(f"\n📤 Negociando con {persona}...")
                    necesidades = bot.calcular_necesidades()
                    excedentes = bot.identificar_excedentes()
                    
                    estrategia = bot.generar_estrategia_negociacion(
                        destinatario=persona,
                        necesidades=necesidades,
                        excedentes=excedentes
                    )
                    
                    if bot.enviar_carta_negociacion(
                        destinatario=persona,
                        asunto=estrategia['asunto'],
                        cuerpo=estrategia['cuerpo']
                    ):
                        contactados += 1
                        print(f"  💬 Mensaje: {estrategia['cuerpo'][:80]}...")
                
                print(f"\n✓ Proceso completo: {contactados} cartas enviadas")
            
            elif opcion_bot == "3":
                # Revisar buzón
                print("\n📬 Revisando buzón...")
                bot.obtener_info()
                buzon = bot.info_actual.get('Buzon', {})
                
                if not buzon:
                    print("✓ Buzón vacío")
                    continue
                
                print(f"\n📨 Tienes {len(buzon)} mensajes:")
                for uid, carta in buzon.items():
                    print(f"\n  UID: {uid}")
                    print(f"  De: {carta.get('remi')}")
                    print(f"  Asunto: {carta.get('asunto')}")
                    print(f"  Mensaje: {carta.get('cuerpo')[:100]}...")
                    
                    analizar = input("  ¿Analizar con IA? (s/n): ").strip().lower()
                    if analizar == 's':
                        analisis = bot.analizar_respuesta(carta)
                        print(f"\n  🤖 Análisis:")
                        print(f"     Evaluación: {analisis.get('evaluacion', 'N/A')}")
                        print(f"     Táctica: {analisis.get('tactica', 'N/A')}")
            
            elif opcion_bot == "4":
                # Ciclo completo
                print("\n🔄 Ejecutando ciclo completo...\n")
                print("Paso 1/2: Negociación automática")
                bot.obtener_info()
                gente = bot.obtener_gente()
                
                for i, persona in enumerate(gente[:3], 1):
                    if persona == alias:
                        continue
                    print(f"  [{i}] Contactando {persona}...")
                    necesidades = bot.calcular_necesidades()
                    excedentes = bot.identificar_excedentes()
                    estrategia = bot.generar_estrategia_negociacion(persona, necesidades, excedentes)
                    bot.enviar_carta_negociacion(persona, estrategia['asunto'], estrategia['cuerpo'])
                
                print("\nPaso 2/2: Revisión de buzón")
                bot.obtener_info()
                buzon = bot.info_actual.get('Buzon', {})
                print(f"  Mensajes en buzón: {len(buzon)}")
                
                print("\n✓ Ciclo completo finalizado")
            
            elif opcion_bot == "0":
                print("\n⬅️  Volviendo al menú principal...")
                break
            
            else:
                print("\n✗ Opción no válida")
    
    except Exception as e:
        print(f"\n✗ Error ejecutando bot: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Función principal del programa"""
    print("Bienvenido a la interfaz de la API")
    
    while True:
        mostrar_menu()
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            get_info()
        elif opcion == "2":
            get_gente()
        elif opcion == "3":
            add_alias()
        elif opcion == "4":
            delete_alias()
        elif opcion == "5":
            send_carta()
        elif opcion == "6":
            send_paquete()
        elif opcion == "7":
            delete_mail()
        elif opcion == "8":
            ejecutar_bot_negociador()
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break
        else:
            print("\n✗ Opción no válida. Por favor, selecciona una opción del menú.")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
