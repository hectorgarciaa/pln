import requests

base_url = "http://147.96.81.252:8000"

def enviar_carta(remi, dest, asunto, cuerpo, id_carta):
    """
    Envía una carta mediante POST /carta
    
    Args:
        remi: Remitente
        dest: Destinatario
        asunto: Asunto de la carta
        cuerpo: Cuerpo de la carta
        id_carta: ID de la carta
    """
    url = f"{base_url}/carta"
    
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
            print("¡Carta enviada con éxito!")
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
    enviar_carta("Juan", "María", "Saludo", "Hola, ¿cómo estás?", "001")
