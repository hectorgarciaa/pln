"""
Cliente para la API del juego.
Centraliza todas las llamadas HTTP.
"""

import requests
from requests.adapters import HTTPAdapter
from typing import Dict, List, Optional
from config import API_BASE_URL


class SourceIPAdapter(HTTPAdapter):
    """HTTPAdapter que bindea a una IP local específica."""
    def __init__(self, source_ip: str, **kwargs):
        self.source_ip = source_ip
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["source_address"] = (self.source_ip, 0)
        super().init_poolmanager(*args, **kwargs)


class APIClient:
    """Cliente para interactuar con la API del juego."""
    
    def __init__(self, base_url: str = None, source_ip: str = None):
        self.base_url = base_url or API_BASE_URL
        self.session = requests.Session()
        if source_ip:
            adapter = SourceIPAdapter(source_ip)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
    
    # =========================================================================
    # INFORMACIÓN
    # =========================================================================
    
    def get_info(self) -> Optional[Dict]:
        """Obtiene información general del jugador."""
        try:
            response = self.session.get(f"{self.base_url}/info")
            if response.status_code == 200:
                return response.json()
            print(f"⚠ Error obteniendo info: {response.status_code}")
            return None
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return None
    
    def get_gente(self) -> List[str]:
        """Obtiene lista de personas disponibles."""
        try:
            response = self.session.get(f"{self.base_url}/gente")
            if response.status_code == 200:
                return response.json()
            print(f"⚠ Error obteniendo gente: {response.status_code}")
            return []
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return []
    
    # =========================================================================
    # ALIAS
    # =========================================================================
    
    def crear_alias(self, nombre: str) -> bool:
        """Crea un nuevo alias."""
        try:
            response = self.session.post(f"{self.base_url}/alias/{nombre}")
            if response.status_code == 200:
                print(f"✓ Alias '{nombre}' creado")
                return True
            print(f"⚠ Error creando alias: {response.status_code}")
            return False
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return False
    
    def eliminar_alias(self, nombre: str) -> bool:
        """Elimina un alias."""
        try:
            response = self.session.delete(f"{self.base_url}/alias/{nombre}")
            if response.status_code == 200:
                print(f"✓ Alias '{nombre}' eliminado")
                return True
            print(f"⚠ Error eliminando alias: {response.status_code}")
            return False
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return False
    
    # =========================================================================
    # CARTAS
    # =========================================================================
    
    def enviar_carta(self, remitente: str, destinatario: str, 
                     asunto: str, cuerpo: str, id_carta: str = None) -> bool:
        """Envía una carta a otro jugador."""
        import time
        
        carta_data = {
            "remi": remitente,
            "dest": destinatario,
            "asunto": asunto,
            "cuerpo": cuerpo,
            "id": id_carta or f"carta_{remitente}_{int(time.time())}"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/carta", json=carta_data)
            if response.status_code == 200:
                return True
            print(f"⚠ Error enviando carta: {response.status_code}")
            return False
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return False
    
    def eliminar_carta(self, uid: str) -> bool:
        """Elimina una carta del buzón."""
        try:
            response = self.session.delete(f"{self.base_url}/mail/{uid}")
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"⚠ Error eliminando carta: {e}")
            return False
    
    # =========================================================================
    # PAQUETES
    # =========================================================================
    
    def enviar_paquete(self, destinatario: str, recursos: Dict[str, int]) -> bool:
        """Envía un paquete de recursos a otro jugador."""
        try:
            # Intentar primero con dest en path (formato más común en este servidor)
            response = self.session.post(
                f"{self.base_url}/paquete/{destinatario}",
                json=recursos
            )
            # Si 404, probar con query param
            if response.status_code == 404:
                response = self.session.post(
                    f"{self.base_url}/paquete",
                    params={"dest": destinatario},
                    json=recursos
                )
            if response.status_code == 200:
                return True
            elif response.status_code == 422:
                print(f"⚠ Error de validación: {response.json()}")
            else:
                print(f"⚠ Error enviando paquete: {response.status_code} - {response.text}")
            return False
        except requests.RequestException as e:
            print(f"⚠ Error de conexión: {e}")
            return False
