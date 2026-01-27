import requests
import json

BASE_URL = "http://147.96.81.252:8000"

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
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break
        else:
            print("\n✗ Opción no válida. Por favor, selecciona una opción del menú.")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
