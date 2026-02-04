import requests

base_url = "http://147.96.81.252:7719"

def eliminar_mail(uid):
    """
    Elimina un mail mediante DELETE /mail/{uid}
    
    Args:
        uid: ID único del mail a eliminar
    """
    url = f"{base_url}/mail/{uid}"
    
    try:
        response = requests.delete(url)
        
        if response.status_code == 200:
            print(f"Mail con UID '{uid}' eliminado correctamente.")
            print("Respuesta:", response.json())
        elif response.status_code == 422:
            print("Error de validación (422). El UID podría no existir o ser inválido.")
            print(response.json())
        else:
            print(f"Error inesperado: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    # Ejemplo de uso
    eliminar_mail("mail123")
