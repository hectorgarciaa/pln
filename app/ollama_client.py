"""
Cliente Ollama para consultas de IA (librería oficial).

═══════════════════════════════════════════════════════════════════════════════
USO:
═══════════════════════════════════════════════════════════════════════════════

    from ollama_client import OllamaClient
    
    ia = OllamaClient("qwen3:8b")
    
    # Consulta simple (con progreso en pantalla)
    respuesta = ia.consultar("¿Cómo estás?")
    
    # Consulta silenciosa (sin imprimir nada)
    respuesta = ia.consultar("...", mostrar_progreso=False)

═══════════════════════════════════════════════════════════════════════════════
CONTROL DE PENSAMIENTO (modelos qwen3):
═══════════════════════════════════════════════════════════════════════════════

  Los modelos qwen3 generan bloques <think>...</think> antes de responder.
  Este cliente detecta esos bloques y:
    1. Si DISABLE_THINK=True → añade /no_think al prompt para evitarlos.
    2. Si DISABLE_THINK=False → permite pensar pero corta si supera
       THINK_TIMEOUT segundos y reintenta con /no_think.
    3. Siempre limpia los bloques <think> de la respuesta final.

═══════════════════════════════════════════════════════════════════════════════
"""

import re
import time
import ollama
from config import OLLAMA_URL, OLLAMA_PARAMS, THINK_TIMEOUT, DISABLE_THINK


# Modelos que soportan bloques <think>
_MODELOS_CON_THINK = ('qwen3',)


class OllamaClient:
    """
    Cliente para consultas a Ollama con control de pensamiento.
    Usa la librería oficial `ollama` en vez de requests.
    """
    
    def __init__(self, modelo: str):
        self.modelo = modelo
        # Crear cliente apuntando al host configurado
        self.client = ollama.Client(host=OLLAMA_URL)
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
        THINK_TIMEOUT segundos, corta la generación y reintenta
        con /no_think para obtener respuesta directa.
        
        Args:
            prompt: El texto a enviar
            timeout: Timeout total en segundos
            mostrar_progreso: Si mostrar el progreso de generación
            
        Returns:
            La respuesta generada (sin bloques <think>)
        """
        prompt = self._preparar_prompt(prompt)
        
        try:
            if mostrar_progreso:
                return self._consultar_streaming(prompt, timeout)
            else:
                return self._consultar_simple(prompt, timeout)
        except ollama.ResponseError as e:
            return f"Error del modelo: {e.error}"
        except ollama.RequestError as e:
            return f"Error de conexión con Ollama: {e}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _consultar_streaming(self, prompt: str, timeout: int) -> str:
        """
        Consulta con streaming: muestra la respuesta en tiempo real
        y controla el tiempo de pensamiento.
        """
        respuesta_completa = ""
        dentro_de_think = False
        think_inicio = None
        pensamiento_cortado = False
        inicio_global = time.time()
        
        stream = self.client.generate(
            model=self.modelo,
            prompt=prompt,
            stream=True,
            options=OLLAMA_PARAMS
        )
        
        for chunk in stream:
            texto = chunk.get('response', '')
            respuesta_completa += texto
            
            # ── Timeout global ──
            if time.time() - inicio_global > timeout:
                print("\n⏱ Timeout general alcanzado")
                break
            
            # ── Detección de <think> ──
            if '<think>' in texto.lower() and not dentro_de_think:
                dentro_de_think = True
                think_inicio = time.time()
                print("🧠 (pensando...) ", end='', flush=True)
            
            if '</think>' in texto.lower() and dentro_de_think:
                dentro_de_think = False
                think_inicio = None
                print("✓", end=' ', flush=True)
            
            # ── Timeout de pensamiento ──
            if dentro_de_think and think_inicio:
                tiempo_pensando = time.time() - think_inicio
                if tiempo_pensando > THINK_TIMEOUT:
                    pensamiento_cortado = True
                    print(f" ✂ cortado ({tiempo_pensando:.0f}s)", flush=True)
                    break
            
            # Solo mostrar tokens fuera de <think>
            if not dentro_de_think:
                texto_visible = self._limpiar_think(texto)
                if texto_visible:
                    print(texto_visible, end='', flush=True)
            
            if chunk.get('done'):
                break
        
        print()  # Nueva línea al final
        
        # Limpiar bloques <think> de la respuesta
        respuesta_limpia = self._limpiar_think(respuesta_completa)
        
        if pensamiento_cortado and not respuesta_limpia:
            # Se cortó pensando sin generar respuesta útil → reintentar
            if self.soporta_think:
                print("  🔄 Reintentando sin pensamiento...", flush=True)
                return self._consultar_sin_think(prompt, timeout)
            return "Error: El modelo se quedó pensando sin generar respuesta"
        
        return respuesta_limpia
    
    def _consultar_simple(self, prompt: str, timeout: int) -> str:
        """Consulta sin streaming: devuelve respuesta completa de golpe."""
        response = self.client.generate(
            model=self.modelo,
            prompt=prompt,
            stream=False,
            options=OLLAMA_PARAMS
        )
        return self._limpiar_think(response.get('response', ''))
    
    def _consultar_sin_think(self, prompt: str, timeout: int) -> str:
        """
        Reintento forzando /no_think para modelos que se quedaron
        atascados pensando.
        """
        if not prompt.strip().startswith('/no_think'):
            prompt = f"/no_think\n{prompt}"
        
        try:
            response = self.client.generate(
                model=self.modelo,
                prompt=prompt,
                stream=False,
                options=OLLAMA_PARAMS
            )
            return self._limpiar_think(response.get('response', ''))
        except Exception as e:
            return f"Error (reintento sin think): {str(e)}"
    
    def ping(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            self.client.list()
            return True
        except Exception:
            return False
