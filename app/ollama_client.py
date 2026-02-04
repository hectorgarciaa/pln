"""
Cliente para Ollama (IA local).
"""

import requests
from typing import Optional
from config import OLLAMA_URL, OLLAMA_PARAMS


class OllamaClient:
    """Cliente para interactuar con Ollama."""
    
    def __init__(self, modelo: str = "qwen3-vl:8b"):
        self.modelo = modelo
        self.url = OLLAMA_URL
    
    def consultar(self, prompt: str, timeout: int = 60, 
                  mostrar_progreso: bool = True) -> str:
        """
        Envía un prompt a Ollama y devuelve la respuesta.
        
        Args:
            prompt: El texto a enviar al modelo
            timeout: Tiempo máximo de espera en segundos
            mostrar_progreso: Si mostrar indicador de progreso
        
        Returns:
            La respuesta del modelo o cadena vacía si hay error
        """
        try:
            if mostrar_progreso:
                print("  ⏳ Consultando IA...", end='', flush=True)
            
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    **OLLAMA_PARAMS
                },
                timeout=timeout
            )
            
            if mostrar_progreso:
                print(" ✓")
            
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            elif response.status_code == 404:
                print(f"\n⚠ Modelo '{self.modelo}' no encontrado.")
                print(f"  Descárgalo con: ollama pull {self.modelo}")
                return ""
            else:
                print(f"\n⚠ Error en Ollama: {response.status_code}")
                return ""
                
        except requests.exceptions.Timeout:
            if mostrar_progreso:
                print(f" ⏱️ Timeout ({timeout}s)")
            return ""
        except requests.exceptions.ConnectionError:
            print(f"\n⚠ No se puede conectar a Ollama.")
            print("  ¿Está corriendo 'ollama serve'?")
            return ""
        except Exception as e:
            print(f"\n⚠ Error: {e}")
            return ""
    
    def cambiar_modelo(self, nuevo_modelo: str):
        """Cambia el modelo de IA."""
        self.modelo = nuevo_modelo
        print(f"✓ Modelo cambiado a: {self.modelo}")
