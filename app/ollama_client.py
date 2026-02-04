"""
Cliente para Ollama con soporte para Tools/Function Calling.

═══════════════════════════════════════════════════════════════════════════════
CÓMO FUNCIONA TOOLS (Function Calling):
═══════════════════════════════════════════════════════════════════════════════

1. REGISTRO: Defines funciones con nombre, descripción y parámetros (JSON Schema)
2. ENVÍO: Mandas prompt + lista de tools disponibles al modelo
3. DECISIÓN: El modelo decide SI usar una tool y CUÁL, devuelve "tool_calls"
4. EJECUCIÓN: Ejecutas la función Python localmente con los argumentos del modelo
5. FEEDBACK: Devuelves el resultado al modelo para que continúe
6. RESPUESTA: El modelo genera respuesta final usando los resultados

Ejemplo de flujo:
    Usuario: "Envía 50 oro a Pedro"
    Modelo → tool_call: enviar_paquete(destinatario="Pedro", recursos={"oro": 50})
    Sistema → ejecuta función → {"exito": true}
    Modelo → "He enviado 50 de oro a Pedro correctamente"

═══════════════════════════════════════════════════════════════════════════════
"""

import requests
import json
from typing import Optional, List, Dict, Any, Callable
from config import OLLAMA_URL, OLLAMA_PARAMS


class OllamaClient:
    """Cliente para Ollama con soporte para tools."""
    
    def __init__(self, modelo: str = "qwen3-vl:8b"):
        self.modelo = modelo
        self.url = OLLAMA_URL
        
        # REGISTRO DE TOOLS:
        # - tools_registry: mapea nombre → función Python a ejecutar
        # - tools_definitions: esquemas JSON que se envían a Ollama
        self.tools_registry: Dict[str, Callable] = {}
        self.tools_definitions: List[Dict] = []
    
    # =========================================================================
    # REGISTRO DE TOOLS
    # =========================================================================
    
    def registrar_tool(self, nombre: str, descripcion: str, 
                       parametros: Dict, funcion: Callable):
        """
        Registra una tool que el modelo puede invocar.
        
        La DESCRIPCIÓN es crucial: el modelo la usa para decidir cuándo usar la tool.
        Los PARÁMETROS usan JSON Schema para validación.
        
        Ejemplo:
            client.registrar_tool(
                nombre="enviar_paquete",
                descripcion="Envía recursos a otro jugador. Usar cuando el usuario quiera transferir recursos.",
                parametros={
                    "type": "object",
                    "properties": {
                        "destinatario": {"type": "string", "description": "Nombre del jugador"},
                        "recursos": {"type": "object", "description": "Dict recurso: cantidad"}
                    },
                    "required": ["destinatario", "recursos"]
                },
                funcion=mi_funcion_enviar
            )
        """
        self.tools_registry[nombre] = funcion
        
        # Formato OpenAI-compatible (Ollama lo soporta)
        self.tools_definitions.append({
            "type": "function",
            "function": {
                "name": nombre,
                "description": descripcion,
                "parameters": parametros
            }
        })
    
    def limpiar_tools(self):
        """Elimina todas las tools registradas."""
        self.tools_registry.clear()
        self.tools_definitions.clear()
    
    # =========================================================================
    # CONSULTA SIMPLE (sin tools)
    # =========================================================================
    
    def consultar(self, prompt: str, timeout: int = 60, 
                  mostrar_progreso: bool = True) -> str:
        """Consulta simple sin tools - para preguntas directas."""
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
            return ""
                
        except Exception as e:
            if mostrar_progreso:
                print(f" ✗ {e}")
            return ""
    
    # =========================================================================
    # CONSULTA CON TOOLS (modo agente)
    # =========================================================================
    
    def consultar_con_tools(self, mensajes: List[Dict], 
                            max_iteraciones: int = 5,
                            mostrar_progreso: bool = True) -> Dict:
        """
        Consulta al modelo permitiendo que use tools.
        
        LOOP DEL AGENTE:
        ┌─────────────────────────────────────────────────────┐
        │  1. Enviar mensajes + tools a Ollama                │
        │  2. ¿Modelo quiere usar tool? ─────────────────────┐│
        │     │ SÍ: ejecutar tool, agregar resultado, GOTO 1 ││
        │     │ NO: devolver respuesta final                 ││
        │  └─────────────────────────────────────────────────┘│
        └─────────────────────────────────────────────────────┘
        
        Args:
            mensajes: [{"role": "user", "content": "..."}, ...]
            max_iteraciones: límite para evitar loops infinitos
        
        Returns:
            {"respuesta": "...", "tools_usadas": [...]}
        """
        tools_usadas = []
        mensajes_actuales = mensajes.copy()
        
        for i in range(max_iteraciones):
            if mostrar_progreso:
                print(f"  🔄 Iteración {i+1}...", end='', flush=True)
            
            try:
                # PASO 1: Enviar a Ollama con tools disponibles
                response = requests.post(
                    f"{self.url}/api/chat",
                    json={
                        "model": self.modelo,
                        "messages": mensajes_actuales,
                        "tools": self.tools_definitions if self.tools_definitions else None,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Bajo = más determinista para tools
                            "num_predict": 500,
                        }
                    },
                    timeout=120
                )
                
                if response.status_code != 200:
                    print(f" ✗ Error {response.status_code}")
                    break
                
                data = response.json()
                message = data.get("message", {})
                
                # PASO 2: ¿El modelo quiere usar tools?
                tool_calls = message.get("tool_calls", [])
                
                if not tool_calls:
                    # NO HAY TOOLS → Respuesta final
                    if mostrar_progreso:
                        print(" ✓ Respuesta final")
                    return {
                        "respuesta": message.get("content", ""),
                        "tools_usadas": tools_usadas
                    }
                
                # PASO 3: Ejecutar cada tool solicitada
                for tool_call in tool_calls:
                    nombre = tool_call.get("function", {}).get("name", "")
                    args = tool_call.get("function", {}).get("arguments", {})
                    
                    # Parsear args si viene como string
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            args = {}
                    
                    if mostrar_progreso:
                        print(f" 🔧 {nombre}({args})", end='')
                    
                    # Ejecutar la función Python real
                    resultado = self._ejecutar_tool(nombre, args)
                    
                    tools_usadas.append({
                        "nombre": nombre,
                        "args": args,
                        "resultado": resultado
                    })
                    
                    # PASO 4: Agregar resultado a la conversación
                    # El modelo verá esto y decidirá qué hacer
                    mensajes_actuales.append(message)
                    mensajes_actuales.append({
                        "role": "tool",
                        "content": json.dumps(resultado, ensure_ascii=False)
                    })
                
                if mostrar_progreso:
                    print()
                    
            except Exception as e:
                print(f" ✗ Error: {e}")
                break
        
        return {
            "respuesta": "Se alcanzó el límite de iteraciones",
            "tools_usadas": tools_usadas
        }
    
    def _ejecutar_tool(self, nombre: str, args: Dict) -> Any:
        """Ejecuta una tool registrada con los argumentos dados."""
        if nombre not in self.tools_registry:
            return {"error": f"Tool '{nombre}' no existe"}
        
        try:
            funcion = self.tools_registry[nombre]
            return funcion(**args)
        except Exception as e:
            return {"error": str(e)}
    
    def cambiar_modelo(self, nuevo_modelo: str):
        self.modelo = nuevo_modelo
