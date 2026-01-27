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
    print("3. GET /info/{usuario} - Ver materiales de un usuario")
    print("4. Robar materiales de un usuario")
    print("5. POST /alias/{nombre} - Añadir un alias")
    print("6. DELETE /alias/{nombre} - Eliminar un alias")
    print("7. POST /carta - Enviar una carta")
    print("8. POST /paquete - Enviar un paquete")
    print("9. DELETE /mail/{uid} - Eliminar un mail")
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
            return data  # Retornar la lista para uso interno
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")
        return None

def get_user_info():
    """GET /info/{usuario} - Obtiene los materiales/recursos de un usuario específico"""
    # Primero obtenemos la lista de usuarios
    url_gente = f"{BASE_URL}/gente"
    try:
        response_gente = requests.get(url_gente)
        if response_gente.status_code != 200:
            print(f"✗ Error al obtener lista de usuarios: {response_gente.status_code}")
            return
        
        usuarios = response_gente.json()
        print("\n--- Usuarios disponibles ---")
        for i, usuario in enumerate(usuarios, 1):
            print(f"{i}. {usuario}")
        
        # Pedimos al usuario que seleccione
        usuario = input("\nIntroduce el nombre del usuario: ").strip()
        if not usuario:
            print("✗ El nombre de usuario no puede estar vacío")
            return
        
        # Intentamos obtener información del usuario
        url = f"{BASE_URL}/info/{usuario}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Información de '{usuario}':")
            
            # Mostrar recursos si existen
            if "Recursos" in data:
                print("\n  Recursos/Materiales:")
                recursos = data["Recursos"]
                if recursos:
                    for recurso, cantidad in recursos.items():
                        print(f"    • {recurso}: {cantidad}")
                else:
                    print("    (Sin recursos)")
            
            # Mostrar objetivo si existe
            if "Objetivo" in data:
                print("\n  Objetivo:")
                objetivo = data["Objetivo"]
                if objetivo:
                    for recurso, cantidad in objetivo.items():
                        print(f"    • {recurso}: {cantidad}")
                else:
                    print("    (Sin objetivos definidos)")
            
            # Mostrar alias si existen
            if "Alias" in data:
                print(f"\n  Alias: {', '.join(data['Alias']) if data['Alias'] else 'ninguno'}")
            
            # Mostrar información del buzón si existe
            if "Buzon" in data:
                num_mensajes = len(data["Buzon"])
                print(f"\n  Mensajes en buzón: {num_mensajes}")
            
        elif response.status_code == 404:
            print(f"✗ Usuario '{usuario}' no encontrado")
        elif response.status_code == 422:
            print(f"✗ Error de validación (422)")
            print("Detalle:", response.json())
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")

def robar_materiales():
    """Ver materiales de un usuario y robarlos enviando un paquete con cantidades negativas"""
    # Primero obtenemos la lista de usuarios
    url_gente = f"{BASE_URL}/gente"
    try:
        response_gente = requests.get(url_gente)
        if response_gente.status_code != 200:
            print(f"✗ Error al obtener lista de usuarios: {response_gente.status_code}")
            return
        
        usuarios = response_gente.json()
        print("\n--- Usuarios disponibles ---")
        for i, usuario in enumerate(usuarios, 1):
            print(f"{i}. {usuario}")
        
        # Pedimos al usuario que seleccione
        victima = input("\nIntroduce el nombre del usuario a robar: ").strip()
        if not victima:
            print("✗ El nombre de usuario no puede estar vacío")
            return
        
        # Obtenemos información del usuario objetivo
        url_info = f"{BASE_URL}/info/{victima}"
        response_info = requests.get(url_info)
        
        if response_info.status_code == 200:
            data = response_info.json()
            print(f"\n Recursos disponibles de '{victima}':")
            
            if "Recursos" in data and data["Recursos"]:
                recursos = data["Recursos"]
                recursos_list = list(recursos.items())
                
                for i, (recurso, cantidad) in enumerate(recursos_list, 1):
                    print(f"{i}. {recurso}: {cantidad}")
                
                print("\n--- Selecciona qué robar ---")
                recursos_robar = {}
                
                while True:
                    print("\nOpciones:")
                    print("1. Robar un recurso específico")
                    print("2. Robar TODOS los recursos")
                    print("3. Finalizar y enviar paquete")
                    print("0. Cancelar")
                    
                    opcion = input("\nSelecciona una opción: ").strip()
                    
                    if opcion == "1":
                        # Robar recurso específico
                        recurso_nombre = input("\nNombre del recurso a robar: ").strip()
                        if recurso_nombre in recursos:
                            try:
                                cantidad_max = recursos[recurso_nombre]
                                print(f"Cantidad disponible: {cantidad_max}")
                                cantidad = int(input(f"Cantidad a robar (máximo {cantidad_max}): ").strip())
                                
                                if cantidad > 0 and cantidad <= cantidad_max:
                                    recursos_robar[recurso_nombre] = -cantidad  # Negativo para robar
                                    print(f"✓ Añadido: robar {cantidad} de {recurso_nombre}")
                                else:
                                    print(f"✗ Cantidad inválida. Debe ser entre 1 y {cantidad_max}")
                            except ValueError:
                                print("✗ La cantidad debe ser un número entero")
                        else:
                            print(f"✗ El recurso '{recurso_nombre}' no existe o no está disponible")
                    
                    elif opcion == "2":
                        # Robar todos los recursos
                        for recurso, cantidad in recursos.items():
                            if cantidad > 0:
                                recursos_robar[recurso] = -cantidad
                        print(f"✓ Preparado para robar TODOS los recursos: {recursos_robar}")
                    
                    elif opcion == "3":
                        # Enviar paquete
                        if not recursos_robar:
                            print("✗ No has seleccionado ningún recurso para robar")
                            continue
                        
                        print(f"\n Enviando paquete de robo a '{victima}'...")
                        print(f"Recursos: {recursos_robar}")
                        
                        url_paquete = f"{BASE_URL}/paquete"
                        params = {"dest": victima}
                        
                        response_paquete = requests.post(url_paquete, params=params, json=recursos_robar)
                        
                        if response_paquete.status_code == 200:
                            print("\n✓ ¡Robo exitoso!")
                            print("Respuesta:", response_paquete.json())
                        elif response_paquete.status_code == 422:
                            print(f"\n✗ Error de validación (422)")
                            print("Detalle:", response_paquete.json())
                        else:
                            print(f"\n✗ Error {response_paquete.status_code}: {response_paquete.text}")
                        
                        return
                    
                    elif opcion == "0":
                        print("Operación cancelada")
                        return
                    else:
                        print("✗ Opción no válida")
            else:
                print("✗ Este usuario no tiene recursos para robar")
        
        elif response_info.status_code == 404:
            print(f"✗ Usuario '{victima}' no encontrado")
        else:
            print(f"✗ Error {response_info.status_code}: {response_info.text}")
    
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
            get_user_info()
        elif opcion == "4":
            robar_materiales()
        elif opcion == "5":
            add_alias()
        elif opcion == "6":
            delete_alias()
        elif opcion == "7":
            send_carta()
        elif opcion == "8":
            send_paquete()
        elif opcion == "9":
            delete_mail()
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break
        else:
            print("\n✗ Opción no válida. Por favor, selecciona una opción del menú.")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
