import requests

base_url = "http://147.96.81.252:7719"

def enviar_paquete(dest, recursos):
    """
    Envía un paquete mediante POST /paquete
    
    Args:
        dest: Destinatario (query parameter)
        recursos: Diccionario con los recursos a enviar (ej: {"oro": 100, "madera": 50})
    """
    url = f"{base_url}/paquete"
    
    # El destinatario va como query parameter
    params = {"dest": dest}
    
    try:
        # Los recursos van en el body como JSON
        response = requests.post(url, params=params, json=recursos)
        
        if response.status_code == 200:
            print("¡Paquete enviado con éxito!")
            print("Respuesta del servidor:", response.json())
        elif response.status_code == 422:
            print("Error de validación (422). Verifica los datos.")
            print("Detalle:", response.json())
        else:
            print(f"Error inesperado: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    # Ejemplo de uso
    recursos = {"oro": 100, "madera": 50, "comida": 30}
    enviar_paquete("María", recursos)
