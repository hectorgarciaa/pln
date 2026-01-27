import requests

base_url = "http://147.96.81.252:8000"
nombre_alias = "Abalos"

# Construimos la URL: http://147.96.81.252:8000/alias/Abalos
url = f"{base_url}/alias/{nombre_alias}"

try:
    # Usamos el método .delete()
    response = requests.delete(url)

    if response.status_code == 200:
        print(f"El alias '{nombre_alias}' ha sido eliminado correctamente.")
        print("Respuesta:", response.json())
        
    elif response.status_code == 422:
        print("Error de validación (422). Quizás el nombre no existe o el formato es erróneo.")
        print(response.json())
        
    else:
        print(f"Error inesperado: {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"Error de conexión: {e}")