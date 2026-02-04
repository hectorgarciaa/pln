import requests

# 1. Definimos los datos
base_url = "http://147.96.81.252:7719"

url = f"{base_url}/gente"

try:
    response = requests.get(url)

    # 4. Verificamos el resultado
    if response.status_code == 200:
        print("Respuesta del servidor:", response.json())
        
    else:
        print(f"Error inesperado: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error de conexión: {e}")