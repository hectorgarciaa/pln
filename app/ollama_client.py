"""
Cliente Ollama para consultas de IA.

═══════════════════════════════════════════════════════════════════════════════
USO:
═══════════════════════════════════════════════════════════════════════════════

    from ollama_client import OllamaClient
    
    ia = OllamaClient("qwen3-vl:8b")
    
    # Consulta simple
    respuesta = ia.consultar("¿Cómo estás?")
    
    # Consulta sin mostrar progreso
    respuesta = ia.consultar("...", mostrar_progreso=False)

═══════════════════════════════════════════════════════════════════════════════
"""

import requests
import json
from config import OLLAMA_URL, OLLAMA_PARAMS


class OllamaClient:
    """
    Cliente simple para consultas a Ollama.
    """
    
    def __init__(self, modelo: str):
        self.modelo = modelo
        self.url = f"{OLLAMA_URL}/api/generate"
    
    def consultar(self, prompt: str, timeout: int = 60, 
                  mostrar_progreso: bool = True) -> str:
        """
        Envía un prompt a Ollama y devuelve la respuesta.
        
        Args:
            prompt: El texto a enviar
            timeout: Timeout en segundos
            mostrar_progreso: Si mostrar el progreso de generación
            
        Returns:
            La respuesta generada
        """
        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": mostrar_progreso,  # Streaming solo si mostramos progreso
            **OLLAMA_PARAMS
        }
        
        try:
            if mostrar_progreso:
                # Con streaming
                respuesta_completa = ""
                
                with requests.post(
                    self.url, 
                    json=payload, 
                    timeout=timeout,
                    stream=True
                ) as response:
                    response.raise_for_status()
                    
                    for linea in response.iter_lines(decode_unicode=True):
                        if linea:
                            try:
                                data = json.loads(linea)
                                chunk = data.get('response', '')
                                respuesta_completa += chunk
                                print(chunk, end='', flush=True)
                                
                                if data.get('done'):
                                    break
                            except json.JSONDecodeError:
                                continue
                
                print()  # Nueva línea al final
                return respuesta_completa.strip()
            
            else:
                # Sin streaming
                payload["stream"] = False
                
                response = requests.post(
                    self.url, 
                    json=payload, 
                    timeout=timeout
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get('response', '').strip()
                
        except requests.exceptions.Timeout:
            return "Error: Timeout - El modelo tardó demasiado en responder"
        except requests.exceptions.RequestException as e:
            return f"Error de conexión: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def ping(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            response = requests.get(
                f"{OLLAMA_URL}/api/tags", 
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
