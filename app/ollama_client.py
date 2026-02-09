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
CONTROL DE PENSAMIENTO (modelos qwen3):
═══════════════════════════════════════════════════════════════════════════════

  Los modelos qwen3 generan bloques <think>...</think> antes de responder.
  Este cliente detecta esos bloques y:
    1. Si DISABLE_THINK=True → añade /no_think al prompt para evitarlos.
    2. Si DISABLE_THINK=False → permite pensar pero corta si supera
       THINK_TIMEOUT segundos y extrae la respuesta parcial.
    3. Siempre limpia los bloques <think> de la respuesta final.

═══════════════════════════════════════════════════════════════════════════════
"""

import re
import time
import requests
import json
from config import OLLAMA_URL, OLLAMA_PARAMS, THINK_TIMEOUT, DISABLE_THINK


# Modelos que soportan bloques <think>
_MODELOS_CON_THINK = ('qwen3',)


class OllamaClient:
    """
    Cliente para consultas a Ollama con control de pensamiento.
    """
    
    def __init__(self, modelo: str):
        self.modelo = modelo
        self.url = f"{OLLAMA_URL}/api/generate"
        # ¿Este modelo usa bloques <think>?
        self.soporta_think = any(m in modelo.lower() for m in _MODELOS_CON_THINK)
    
    @staticmethod
    def _limpiar_think(texto: str) -> str:
        """
        Elimina bloques <think>...</think> de la respuesta.
        También elimina <think> sin cerrar (pensamiento cortado).
        """
        # Eliminar bloques completos <think>...</think>
        limpio = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
        # Eliminar <think> sin cerrar (modelo cortado a mitad de pensamiento)
        limpio = re.sub(r'<think>.*', '', limpio, flags=re.DOTALL)
        return limpio.strip()
    
    def _preparar_prompt(self, prompt: str) -> str:
        """
        Si DISABLE_THINK está activo y el modelo lo soporta,
        añade /no_think para desactivar el pensamiento.
        """
        if DISABLE_THINK and self.soporta_think:
            return f"/no_think\n{prompt}"
        return prompt
    
    def consultar(self, prompt: str, timeout: int = 60, 
                  mostrar_progreso: bool = True) -> str:
        """
        Envía un prompt a Ollama y devuelve la respuesta.
        
        Si el modelo se queda "pensando" (bloque <think>) más de
        THINK_TIMEOUT segundos, corta la generación y devuelve
        lo que haya generado hasta el momento (sin el bloque think).
        
        Args:
            prompt: El texto a enviar
            timeout: Timeout total en segundos
            mostrar_progreso: Si mostrar el progreso de generación
            
        Returns:
            La respuesta generada (sin bloques <think>)
        """
        prompt = self._preparar_prompt(prompt)
        
        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": True,  # Siempre streaming para controlar pensamiento
            **OLLAMA_PARAMS
        }
        
        try:
            respuesta_completa = ""
            dentro_de_think = False
            think_inicio = None
            pensamiento_cortado = False
            
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
                            
                            # ── Detección de <think> ──
                            if '<think>' in chunk.lower():
                                dentro_de_think = True
                                think_inicio = time.time()
                                if mostrar_progreso:
                                    print("🧠 (pensando...) ", end='', flush=True)
                            
                            if '</think>' in chunk.lower():
                                dentro_de_think = False
                                think_inicio = None
                                if mostrar_progreso:
                                    print("✓", end=' ', flush=True)
                            
                            # ── Timeout de pensamiento ──
                            if dentro_de_think and think_inicio:
                                tiempo_pensando = time.time() - think_inicio
                                if tiempo_pensando > THINK_TIMEOUT:
                                    pensamiento_cortado = True
                                    if mostrar_progreso:
                                        print(f" ✂ cortado ({tiempo_pensando:.0f}s)", flush=True)
                                    # Cerramos la conexión para parar la generación
                                    break
                            
                            # Solo mostrar tokens fuera de <think>
                            if mostrar_progreso and not dentro_de_think:
                                # Mostrar solo la parte fuera de think
                                texto_visible = self._limpiar_think(chunk)
                                if texto_visible:
                                    print(texto_visible, end='', flush=True)
                            
                            if data.get('done'):
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            if mostrar_progreso:
                print()  # Nueva línea al final
            
            # Limpiar bloques <think> de la respuesta
            respuesta_limpia = self._limpiar_think(respuesta_completa)
            
            if pensamiento_cortado and not respuesta_limpia:
                # El modelo se cortó mientras pensaba y no generó respuesta útil.
                # Reintentar con /no_think si el modelo lo soporta.
                if self.soporta_think:
                    if mostrar_progreso:
                        print("  🔄 Reintentando sin pensamiento...", flush=True)
                    return self._consultar_sin_think(prompt, timeout, mostrar_progreso)
                return "Error: El modelo se quedó pensando sin generar respuesta"
            
            return respuesta_limpia
                
        except requests.exceptions.Timeout:
            return "Error: Timeout - El modelo tardó demasiado en responder"
        except requests.exceptions.RequestException as e:
            return f"Error de conexión: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _consultar_sin_think(self, prompt: str, timeout: int = 60,
                             mostrar_progreso: bool = False) -> str:
        """
        Reintento forzando /no_think para modelos que se quedaron
        atascados pensando.
        """
        # Añadir /no_think si no lo tiene ya
        if not prompt.strip().startswith('/no_think'):
            prompt = f"/no_think\n{prompt}"
        
        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            **OLLAMA_PARAMS
        }
        
        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            respuesta = data.get('response', '').strip()
            return self._limpiar_think(respuesta)
        except Exception as e:
            return f"Error (reintento sin think): {str(e)}"
    
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
