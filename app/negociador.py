"""
Bot Negociador con Tools/Function Calling.

═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA CON TOOLS:
═══════════════════════════════════════════════════════════════════════════════

En lugar de usar regex/palabras clave para decidir acciones, el modelo LLM
decide QUÉ FUNCIÓN LLAMAR basándose en el contexto.

TOOLS DISPONIBLES:
┌────────────────────┬─────────────────────────────────────────────────────────┐
│ Tool               │ Descripción                                             │
├────────────────────┼─────────────────────────────────────────────────────────┤
│ ver_estado         │ Consulta recursos, oro y objetivo actual                │
│ ver_jugadores      │ Lista jugadores disponibles para negociar               │
│ enviar_carta       │ Envía propuesta de negociación a un jugador             │
│ enviar_paquete     │ Transfiere recursos a otro jugador                      │
│ analizar_oferta    │ Evalúa si una oferta recibida es buena o mala           │
│ detectar_robo      │ Verifica si un mensaje es intento de estafa             │
└────────────────────┴─────────────────────────────────────────────────────────┘

FLUJO DE EJEMPLO:
    Usuario: "Negocia con Pedro para conseguir madera"
    
    Modelo → tool: ver_estado()
            ← {recursos: {oro: 100}, necesidades: {madera: 50}}
    
    Modelo → tool: enviar_carta(dest="Pedro", asunto="...", cuerpo="...")
            ← {exito: true}
    
    Modelo → "He enviado una propuesta a Pedro ofreciendo oro por madera"

═══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
from typing import Dict, List, Optional

from config import (
    RECURSOS_CONOCIDOS, PALABRAS_SOSPECHOSAS,
    PALABRAS_ACEPTACION, PALABRAS_RECHAZO, MODELO_DEFAULT
)
from api_client import APIClient
from ollama_client import OllamaClient


class BotNegociador:
    """
    Bot de negociación con soporte de Tools.
    
    El modelo LLM puede llamar a funciones reales para:
    - Consultar estado del juego
    - Enviar cartas y paquetes
    - Analizar ofertas
    """
    
    def __init__(self, alias: str, modelo: str = MODELO_DEFAULT):
        self.alias = alias
        self.api = APIClient()
        self.ia = OllamaClient(modelo)
        
        # Estado
        self.info_actual: Optional[Dict] = None
        self.gente: List[str] = []
        
        # Seguridad
        self.lista_negra: List[str] = []
        self.historial: List[Dict] = []
        
        # REGISTRAR TODAS LAS TOOLS
        # Esto le dice al modelo qué funciones puede usar
        self._registrar_tools()
    
    # =========================================================================
    # REGISTRO DE TOOLS - Define qué puede hacer el agente
    # =========================================================================
    
    def _registrar_tools(self):
        """
        Registra las tools que el modelo puede invocar.
        
        Cada tool tiene:
        - nombre: identificador único
        - descripcion: el modelo usa esto para decidir cuándo usarla
        - parametros: JSON Schema de los argumentos
        - funcion: método Python a ejecutar
        """
        
        # TOOL 1: Ver estado actual (recursos, oro, objetivo)
        self.ia.registrar_tool(
            nombre="ver_estado",
            descripcion="Obtiene el estado actual: recursos disponibles, oro, objetivo y qué falta para completarlo. Usar antes de negociar para saber qué necesitas.",
            parametros={"type": "object", "properties": {}, "required": []},
            funcion=self._tool_ver_estado
        )
        
        # TOOL 2: Ver jugadores disponibles
        self.ia.registrar_tool(
            nombre="ver_jugadores",
            descripcion="Lista todos los jugadores disponibles para negociar. Usar para saber a quién contactar.",
            parametros={"type": "object", "properties": {}, "required": []},
            funcion=self._tool_ver_jugadores
        )
        
        # TOOL 3: Enviar carta de negociación
        self.ia.registrar_tool(
            nombre="enviar_carta",
            descripcion="Envía una carta/mensaje a otro jugador para negociar. Usar para proponer intercambios.",
            parametros={
                "type": "object",
                "properties": {
                    "destinatario": {
                        "type": "string",
                        "description": "Nombre del jugador destinatario"
                    },
                    "asunto": {
                        "type": "string",
                        "description": "Asunto breve de la carta"
                    },
                    "cuerpo": {
                        "type": "string",
                        "description": "Contenido del mensaje (max 200 caracteres)"
                    }
                },
                "required": ["destinatario", "asunto", "cuerpo"]
            },
            funcion=self._tool_enviar_carta
        )
        
        # TOOL 4: Enviar paquete de recursos
        self.ia.registrar_tool(
            nombre="enviar_paquete",
            descripcion="Transfiere recursos a otro jugador. SOLO usar cuando hay un acuerdo confirmado. Verificar primero que tenemos los recursos.",
            parametros={
                "type": "object",
                "properties": {
                    "destinatario": {
                        "type": "string",
                        "description": "Nombre del jugador que recibirá los recursos"
                    },
                    "recursos": {
                        "type": "object",
                        "description": "Diccionario con recursos a enviar, ej: {'oro': 50, 'madera': 100}"
                    }
                },
                "required": ["destinatario", "recursos"]
            },
            funcion=self._tool_enviar_paquete
        )
        
        # TOOL 5: Ver buzón (cartas recibidas)
        self.ia.registrar_tool(
            nombre="ver_buzon",
            descripcion="Muestra las cartas/mensajes recibidos de otros jugadores. Usar para ver respuestas a nuestras propuestas.",
            parametros={"type": "object", "properties": {}, "required": []},
            funcion=self._tool_ver_buzon
        )
        
        # TOOL 6: Analizar si una oferta es buena
        self.ia.registrar_tool(
            nombre="analizar_oferta",
            descripcion="Analiza una oferta recibida y determina si es beneficiosa o no.",
            parametros={
                "type": "object",
                "properties": {
                    "remitente": {
                        "type": "string",
                        "description": "Quién envió la oferta"
                    },
                    "mensaje": {
                        "type": "string",
                        "description": "Contenido del mensaje a analizar"
                    }
                },
                "required": ["remitente", "mensaje"]
            },
            funcion=self._tool_analizar_oferta
        )
        
        # TOOL 7: Verificar si es intento de robo
        self.ia.registrar_tool(
            nombre="verificar_seguridad",
            descripcion="Verifica si un mensaje es sospechoso o intento de robo/estafa. Usar antes de aceptar ofertas de desconocidos.",
            parametros={
                "type": "object",
                "properties": {
                    "remitente": {
                        "type": "string",
                        "description": "Quién envió el mensaje"
                    },
                    "mensaje": {
                        "type": "string",
                        "description": "Contenido a verificar"
                    }
                },
                "required": ["remitente", "mensaje"]
            },
            funcion=self._tool_verificar_seguridad
        )
    
    # =========================================================================
    # IMPLEMENTACIÓN DE TOOLS - Funciones que el modelo puede llamar
    # =========================================================================
    
    def _tool_ver_estado(self) -> Dict:
        """Tool: Devuelve estado actual del jugador."""
        self.info_actual = self.api.get_info()
        
        if not self.info_actual:
            return {"error": "No se pudo conectar a la API"}
        
        recursos = self.info_actual.get('Recursos', {})
        objetivo = self.info_actual.get('Objetivo', {})
        
        # Calcular qué falta
        necesidades = {}
        for rec, cant_obj in objetivo.items():
            actual = recursos.get(rec, 0)
            if actual < cant_obj:
                necesidades[rec] = cant_obj - actual
        
        # Calcular excedentes
        excedentes = {}
        for rec, actual in recursos.items():
            obj = objetivo.get(rec, 0)
            if actual > obj:
                excedentes[rec] = actual - obj
        
        return {
            "recursos": recursos,
            "oro": recursos.get('oro', 0),
            "objetivo": objetivo,
            "necesidades": necesidades,  # Lo que falta para ganar
            "excedentes": excedentes,    # Lo que sobra (podemos vender)
            "objetivo_completado": len(necesidades) == 0
        }
    
    def _tool_ver_jugadores(self) -> Dict:
        """Tool: Lista jugadores disponibles."""
        self.gente = self.api.get_gente()
        
        # Filtrar: quitar nuestro alias y lista negra
        disponibles = [
            p for p in self.gente 
            if p != self.alias and p not in self.lista_negra
        ]
        
        return {
            "jugadores": disponibles,
            "total": len(disponibles),
            "lista_negra": self.lista_negra
        }
    
    def _tool_enviar_carta(self, destinatario: str, asunto: str, cuerpo: str) -> Dict:
        """Tool: Envía una carta de negociación."""
        # Verificar que no está en lista negra
        if destinatario in self.lista_negra:
            return {
                "exito": False,
                "error": f"{destinatario} está en lista negra, no se puede contactar"
            }
        
        exito = self.api.enviar_carta(self.alias, destinatario, asunto, cuerpo)
        
        if exito:
            self.historial.append({
                "tipo": "carta_enviada",
                "destinatario": destinatario,
                "asunto": asunto,
                "timestamp": time.time()
            })
        
        return {
            "exito": exito,
            "destinatario": destinatario,
            "mensaje": f"Carta enviada a {destinatario}" if exito else "Error al enviar"
        }
    
    def _tool_enviar_paquete(self, destinatario: str, recursos: Dict) -> Dict:
        """Tool: Envía un paquete de recursos."""
        # Verificar lista negra
        if destinatario in self.lista_negra:
            return {
                "exito": False,
                "error": f"{destinatario} está en lista negra"
            }
        
        # Verificar que tenemos los recursos
        self.info_actual = self.api.get_info()
        mis_recursos = self.info_actual.get('Recursos', {}) if self.info_actual else {}
        
        for rec, cant in recursos.items():
            if mis_recursos.get(rec, 0) < cant:
                return {
                    "exito": False,
                    "error": f"No tienes suficiente {rec}. Tienes {mis_recursos.get(rec, 0)}, necesitas {cant}"
                }
        
        exito = self.api.enviar_paquete(destinatario, recursos)
        
        if exito:
            self.historial.append({
                "tipo": "paquete_enviado",
                "destinatario": destinatario,
                "recursos": recursos,
                "timestamp": time.time()
            })
        
        return {
            "exito": exito,
            "destinatario": destinatario,
            "recursos_enviados": recursos if exito else None,
            "mensaje": f"Paquete enviado a {destinatario}" if exito else "Error al enviar"
        }
    
    def _tool_ver_buzon(self) -> Dict:
        """Tool: Muestra cartas recibidas."""
        self.info_actual = self.api.get_info()
        
        if not self.info_actual:
            return {"error": "No se pudo conectar"}
        
        buzon = self.info_actual.get('Buzon', {})
        
        # Filtrar solo las dirigidas a nosotros
        cartas = []
        for uid, carta in buzon.items():
            if carta.get('dest') == self.alias:
                cartas.append({
                    "uid": uid,
                    "de": carta.get('remi', 'Desconocido'),
                    "asunto": carta.get('asunto', ''),
                    "mensaje": carta.get('cuerpo', '')
                })
        
        return {
            "cartas": cartas,
            "total": len(cartas)
        }
    
    def _tool_analizar_oferta(self, remitente: str, mensaje: str) -> Dict:
        """Tool: Analiza si una oferta es beneficiosa."""
        # Obtener nuestro estado actual
        estado = self._tool_ver_estado()
        necesidades = estado.get('necesidades', {})
        excedentes = estado.get('excedentes', {})
        
        # Buscar recursos mencionados en el mensaje
        recursos_mencionados = []
        mensaje_lower = mensaje.lower()
        for rec in RECURSOS_CONOCIDOS:
            if rec in mensaje_lower:
                recursos_mencionados.append(rec)
        
        # Determinar si nos conviene
        nos_conviene = False
        razon = ""
        
        for rec in recursos_mencionados:
            if rec in necesidades:
                nos_conviene = True
                razon = f"Ofrecen {rec} que necesitamos"
                break
        
        # Detectar si piden algo que no podemos dar
        for rec in excedentes.keys():
            if rec in mensaje_lower:
                razon += f". Podemos dar {rec} (excedente)"
        
        return {
            "remitente": remitente,
            "recursos_mencionados": recursos_mencionados,
            "nos_conviene": nos_conviene,
            "razon": razon or "No se detectaron recursos relevantes",
            "necesidades_actuales": necesidades,
            "excedentes_actuales": excedentes
        }
    
    def _tool_verificar_seguridad(self, remitente: str, mensaje: str) -> Dict:
        """Tool: Verifica si un mensaje es sospechoso."""
        mensaje_lower = mensaje.lower()
        
        # Contar palabras sospechosas
        alertas = [
            palabra for palabra in PALABRAS_SOSPECHOSAS 
            if palabra in mensaje_lower
        ]
        
        es_sospechoso = len(alertas) >= 2
        
        if es_sospechoso and remitente not in self.lista_negra:
            self.lista_negra.append(remitente)
        
        return {
            "remitente": remitente,
            "es_sospechoso": es_sospechoso,
            "alertas_detectadas": alertas,
            "en_lista_negra": remitente in self.lista_negra,
            "recomendacion": "NO NEGOCIAR" if es_sospechoso else "Parece seguro"
        }
    
    # =========================================================================
    # INTERFAZ PRINCIPAL - Modo agente con tools
    # =========================================================================
    
    def ejecutar_agente(self, instruccion: str) -> str:
        """
        Ejecuta el agente con una instrucción en lenguaje natural.
        
        El modelo decidirá qué tools usar para cumplir la instrucción.
        
        Ejemplos de instrucciones:
        - "Negocia con todos para conseguir madera"
        - "Revisa el buzón y responde a las ofertas"
        - "Envía 50 oro a Pedro"
        - "Analiza la seguridad de los mensajes recibidos"
        """
        # Prompt del sistema que explica el contexto al modelo
        sistema = f"""Eres un agente negociador en un juego de recursos.
Tu alias es: {self.alias}

OBJETIVO: Conseguir recursos para completar tu objetivo mediante negociación justa.

REGLAS:
- Usa ver_estado() primero para saber qué necesitas
- Sé amable y justo en las negociaciones
- NUNCA envíes recursos sin un acuerdo claro
- Verifica seguridad antes de aceptar ofertas sospechosas
- Los de lista negra son estafadores, ignóralos

Usa las tools disponibles para ejecutar acciones reales."""

        mensajes = [
            {"role": "system", "content": sistema},
            {"role": "user", "content": instruccion}
        ]
        
        print(f"\n🤖 Ejecutando: {instruccion}")
        print("-" * 50)
        
        resultado = self.ia.consultar_con_tools(mensajes)
        
        # Mostrar tools usadas
        if resultado["tools_usadas"]:
            print(f"\n📋 Tools ejecutadas:")
            for tool in resultado["tools_usadas"]:
                print(f"  • {tool['nombre']}({tool['args']}) → {tool['resultado']}")
        
        return resultado["respuesta"]
    
    # =========================================================================
    # MÉTODOS DE CONVENIENCIA (para el menú)
    # =========================================================================
    
    @property
    def modelo(self) -> str:
        return self.ia.modelo
    
    @modelo.setter
    def modelo(self, value: str):
        self.ia.modelo = value
    
    def actualizar_info(self):
        self.info_actual = self.api.get_info()
        return self.info_actual
    
    def get_recursos(self) -> Dict:
        if not self.info_actual:
            self.actualizar_info()
        return self.info_actual.get('Recursos', {}) if self.info_actual else {}
    
    def get_oro(self) -> int:
        return self.get_recursos().get('oro', 0)
    
    def calcular_necesidades(self) -> Dict:
        estado = self._tool_ver_estado()
        return estado.get('necesidades', {})
    
    def calcular_excedentes(self) -> Dict:
        estado = self._tool_ver_estado()
        return estado.get('excedentes', {})
    
    def objetivo_completado(self) -> bool:
        estado = self._tool_ver_estado()
        return estado.get('objetivo_completado', False)
    
    def get_cartas_recibidas(self) -> List[Dict]:
        resultado = self._tool_ver_buzon()
        return resultado.get('cartas', [])
    
    def limpiar_buzon(self, mantener: int = 10):
        """Limpia el buzón."""
        buzon = self._tool_ver_buzon()
        cartas = buzon.get('cartas', [])
        
        if len(cartas) > mantener:
            for carta in cartas[:-mantener]:
                self.api.eliminar_carta(carta['uid'])
            print(f"✓ Buzón limpiado, {mantener} cartas mantenidas")
