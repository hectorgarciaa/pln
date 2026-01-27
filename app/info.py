import requests

# Definimos la URL del endpoint
url = "http://147.96.81.252:8000/info"

try:
    # Realizamos la petición GET
    # No se requieren parámetros según la documentación
    response = requests.get(url)

    # Verificamos si la petición fue exitosa (código 200)
    if response.status_code == 200:
        # Convertimos la respuesta JSON a un diccionario de Python
        data = response.json()
        
        # Imprimimos el resultado completo
        print("Respuesta exitosa:")
        print(data)
        
        # Ejemplo de cómo acceder a los datos según tu esquema:
        if "Alias" in data:
            print(f"\nAlias: {data['Alias']}")
            
        if "Buzon" in data:
            print(f"Contenido del Buzón: {data['Buzon']}")
            
    else:
        print(f"Error en la petición: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    # Captura errores de conexión, DNS, etc.
    print(f"Ocurrió un error de conexión: {e}")