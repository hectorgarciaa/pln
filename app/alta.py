import requests

# 1. Definimos los datos
base_url = "http://147.96.81.252:7719"
nombre_alias = "J.L. Abalos"

# 2. Construimos la URL completa (Path Parameter)
# La URL final será: http://147.96.81.252:7719/alias/Abalos
url = f"{base_url}/alias/{nombre_alias}"

try:
    # 3. Hacemos la petición POST
    # Como el dato va en la URL, no necesitamos pasar argumentos 'json' ni 'data'
    response = requests.post(url)

    # 4. Verificamos el resultado
    if response.status_code == 200:
        print("¡Alias añadido con éxito!")
        print("Respuesta del servidor:", response.json())
        
    elif response.status_code == 422:
        print("Error de validación (422). El formato del nombre podría ser incorrecto.")
        print("Detalle:", response.json())
        
    else:
        print(f"Error inesperado: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error de conexión: {e}")