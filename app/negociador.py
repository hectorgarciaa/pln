"""
Bot Negociador - Sistema de negociación automática con IA.

Este módulo contiene la lógica principal del bot que negocia
recursos con otros jugadores usando Ollama como motor de IA.
"""

import json
import re
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
    Bot de negociación que usa IA para conseguir recursos.
    
    Características:
    - Negociación automática con múltiples jugadores
    - Detección de intentos de robo
    - Intercambio de recursos cuando hay acuerdo
    - Lista negra de jugadores no confiables
    """
    
    def __init__(self, alias: str, modelo: str = MODELO_DEFAULT):
        self.alias = alias
        self.api = APIClient()
        self.ia = OllamaClient(modelo)
        
        # Estado
        self.info_actual: Optional[Dict] = None
        self.gente: List[str] = []
        
        # Historial y seguridad
        self.historial_negociaciones: Dict = {}
        self.lista_negra: List[str] = []
        self.acuerdos_pendientes: Dict = {}
        self.intercambios_realizados: List[Dict] = []
    
    # =========================================================================
    # PROPIEDADES Y ESTADO
    # =========================================================================
    
    @property
    def modelo(self) -> str:
        return self.ia.modelo
    
    @modelo.setter
    def modelo(self, value: str):
        self.ia.modelo = value
    
    def actualizar_info(self) -> Dict:
        """Actualiza y devuelve la información del jugador."""
        self.info_actual = self.api.get_info()
        return self.info_actual or {}
    
    def actualizar_gente(self) -> List[str]:
        """Actualiza y devuelve la lista de jugadores."""
        self.gente = self.api.get_gente()
        return self.gente
    
    def get_recursos(self) -> Dict[str, int]:
        """Devuelve los recursos actuales."""
        if not self.info_actual:
            self.actualizar_info()
        return self.info_actual.get('Recursos', {}) if self.info_actual else {}
    
    def get_objetivo(self) -> Dict[str, int]:
        """Devuelve el objetivo de recursos."""
        if not self.info_actual:
            self.actualizar_info()
        return self.info_actual.get('Objetivo', {}) if self.info_actual else {}
    
    def get_oro(self) -> int:
        """Devuelve la cantidad de oro actual."""
        return self.get_recursos().get('oro', 0)
    
    def get_buzon(self) -> Dict:
        """Devuelve el buzón de cartas."""
        if not self.info_actual:
            self.actualizar_info()
        return self.info_actual.get('Buzon', {}) if self.info_actual else {}
    
    # =========================================================================
    # CÁLCULOS DE RECURSOS
    # =========================================================================
    
    def calcular_necesidades(self) -> Dict[str, int]:
        """Calcula qué recursos necesitamos para el objetivo."""
        recursos = self.get_recursos()
        objetivo = self.get_objetivo()
        
        necesidades = {}
        for recurso, cantidad_objetivo in objetivo.items():
            cantidad_actual = recursos.get(recurso, 0)
            if cantidad_actual < cantidad_objetivo:
                necesidades[recurso] = cantidad_objetivo - cantidad_actual
        
        return necesidades
    
    def calcular_excedentes(self) -> Dict[str, int]:
        """Calcula qué recursos tenemos en exceso."""
        recursos = self.get_recursos()
        objetivo = self.get_objetivo()
        
        excedentes = {}
        for recurso, cantidad_actual in recursos.items():
            cantidad_objetivo = objetivo.get(recurso, 0)
            if cantidad_actual > cantidad_objetivo:
                excedentes[recurso] = cantidad_actual - cantidad_objetivo
        
        return excedentes
    
    def objetivo_completado(self) -> bool:
        """Verifica si el objetivo está completo."""
        return len(self.calcular_necesidades()) == 0
    
    # =========================================================================
    # DETECCIÓN DE SEGURIDAD
    # =========================================================================
    
    def detectar_robo(self, carta: Dict) -> bool:
        """Detecta si un mensaje es un intento de robo."""
        mensaje = carta.get('cuerpo', '').lower()
        asunto = carta.get('asunto', '').lower()
        remitente = carta.get('remi', 'Desconocido')
        
        # Contar palabras sospechosas
        texto_completo = mensaje + " " + asunto
        coincidencias = sum(
            1 for palabra in PALABRAS_SOSPECHOSAS 
            if palabra in texto_completo
        )
        
        # 3+ coincidencias = sospechoso
        if coincidencias >= 3:
            self._agregar_lista_negra(remitente, "mensaje sospechoso")
            return True
        
        # 2 coincidencias = verificar con IA
        if coincidencias >= 2:
            prompt = f"¿Es robo? Responde ROBO o LEGIT.\nMensaje: {mensaje[:200]}"
            respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
            
            if respuesta and "ROBO" in respuesta.upper():
                self._agregar_lista_negra(remitente, "detectado por IA")
                return True
        
        return False
    
    def _agregar_lista_negra(self, persona: str, razon: str):
        """Agrega una persona a la lista negra."""
        if persona not in self.lista_negra:
            self.lista_negra.append(persona)
            print(f"⚠️ {persona} añadido a lista negra ({razon})")
    
    # =========================================================================
    # DETECCIÓN DE ACEPTACIONES
    # =========================================================================
    
    def detectar_aceptacion(self, carta: Dict) -> Optional[Dict]:
        """Detecta si un mensaje acepta un intercambio."""
        mensaje = carta.get('cuerpo', '').lower()
        remitente = carta.get('remi', '')
        
        # Verificar rechazo primero
        if any(palabra in mensaje for palabra in PALABRAS_RECHAZO):
            return None
        
        # Verificar aceptación
        hay_aceptacion = any(
            palabra in mensaje for palabra in PALABRAS_ACEPTACION
        )
        
        # Si no está claro, usar IA
        if not hay_aceptacion:
            prompt = f"¿Acepta intercambio? Responde ACEPTA o RECHAZA.\nMensaje: {mensaje[:200]}"
            respuesta = self.ia.consultar(prompt, timeout=30, mostrar_progreso=False)
            hay_aceptacion = respuesta and "ACEPTA" in respuesta.upper()
        
        if hay_aceptacion:
            return {
                'remitente': remitente,
                'aceptacion': True,
                'terminos': self._extraer_terminos(mensaje),
                'mensaje_original': carta.get('cuerpo', '')
            }
        
        return None
    
    def _extraer_terminos(self, mensaje: str) -> Dict:
        """Extrae recursos y cantidades de un mensaje."""
        terminos = {'ofrece': {}, 'pide': {}}
        
        # Buscar patrones: "100 oro", "50 de madera"
        patron = r'(\d+)\s*(?:de\s+)?(' + '|'.join(RECURSOS_CONOCIDOS) + r')'
        for cantidad, recurso in re.findall(patron, mensaje.lower()):
            terminos['ofrece'][recurso] = int(cantidad)
        
        return terminos
    
    # =========================================================================
    # ENVÍO DE CARTAS Y PAQUETES
    # =========================================================================
    
    def enviar_carta(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        """Envía una carta de negociación."""
        exito = self.api.enviar_carta(self.alias, destinatario, asunto, cuerpo)
        if exito:
            print(f"✓ Carta enviada a {destinatario}")
        return exito
    
    def enviar_paquete(self, destinatario: str, recursos: Dict[str, int]) -> bool:
        """Envía un paquete de recursos."""
        if not recursos:
            print("⚠️ No hay recursos para enviar")
            return False
        
        # Verificar recursos suficientes
        mis_recursos = self.get_recursos()
        for recurso, cantidad in recursos.items():
            if mis_recursos.get(recurso, 0) < cantidad:
                print(f"⚠️ No tienes suficiente {recurso}")
                return False
        
        if self.api.enviar_paquete(destinatario, recursos):
            print(f"✅ Paquete enviado a {destinatario}: {recursos}")
            self.intercambios_realizados.append({
                'tipo': 'enviado',
                'destinatario': destinatario,
                'recursos': recursos,
                'timestamp': time.time()
            })
            return True
        return False
    
    # =========================================================================
    # GENERACIÓN DE ESTRATEGIAS
    # =========================================================================
    
    def generar_propuesta(self, destinatario: str) -> Dict[str, str]:
        """Genera una propuesta de negociación para un destinatario."""
        necesidades = self.calcular_necesidades()
        excedentes = self.calcular_excedentes()
        oro = self.get_oro()
        
        enfoque = "VENDER excedentes" if self.objetivo_completado() else "INTERCAMBIAR"
        
        prompt = f"""Negociador amigable. Objetivo: {enfoque}

Tú: {self.alias}, Oro: {oro}
Destinatario: {destinatario}
Necesitas: {json.dumps(necesidades, ensure_ascii=False)}
Tienes: {json.dumps(excedentes, ensure_ascii=False)}

Genera carta (max 200 chars):
ASUNTO: [título]
CUERPO: [mensaje]"""
        
        respuesta = self.ia.consultar(prompt)
        
        # Parsear respuesta
        asunto = self._extraer_campo(respuesta, 'ASUNTO', 'CUERPO')
        cuerpo = self._extraer_campo(respuesta, 'CUERPO', None)
        
        # Fallback si falla el parseo
        if not asunto or not cuerpo:
            return self._generar_propuesta_fallback(destinatario, necesidades, excedentes)
        
        return {'asunto': asunto, 'cuerpo': cuerpo}
    
    def _extraer_campo(self, texto: str, campo: str, siguiente: Optional[str]) -> str:
        """Extrae un campo de la respuesta de la IA."""
        patron = rf'{campo}:\s*(.+?)(?={siguiente}:|$)' if siguiente else rf'{campo}:\s*(.+)'
        match = re.search(patron, texto, re.DOTALL)
        return match.group(1).strip() if match else ''
    
    def _generar_propuesta_fallback(self, dest: str, necesidades: Dict, excedentes: Dict) -> Dict:
        """Genera propuesta sin IA."""
        if necesidades:
            recurso = list(necesidades.keys())[0]
            cantidad = necesidades[recurso]
            
            if excedentes:
                exc = list(excedentes.keys())[0]
                exc_cant = excedentes[exc]
                return {
                    'asunto': f"🤝 Intercambio - {recurso}",
                    'cuerpo': f"Hola {dest}! Busco {cantidad} {recurso}. "
                             f"Tengo {exc_cant} {exc} para intercambiar. ¿Te interesa?"
                }
            return {
                'asunto': f"🤝 Busco {recurso}",
                'cuerpo': f"Hola {dest}! Necesito {cantidad} {recurso}. "
                         f"Puedo pagar en oro. ¿Tienes disponible?"
            }
        
        if excedentes:
            exc = list(excedentes.keys())[0]
            exc_cant = excedentes[exc]
            return {
                'asunto': f"💼 Ofrezco {exc}",
                'cuerpo': f"Hola {dest}! Tengo {exc_cant} {exc}. "
                         f"¿Te interesa? Hablamos precio."
            }
        
        return {
            'asunto': f"👋 Hola de {self.alias}",
            'cuerpo': f"Hola {dest}! ¿Qué recursos tienes? Podemos intercambiar."
        }
    
    # =========================================================================
    # ANÁLISIS DE RESPUESTAS
    # =========================================================================
    
    def analizar_respuesta(self, carta: Dict) -> Dict:
        """Analiza una respuesta recibida."""
        # Primero verificar si es robo
        if self.detectar_robo(carta):
            return {
                'evaluacion': '🚨 INTENTO DE ROBO',
                'tactica': f'{carta.get("remi")} añadido a lista negra.',
                'respuesta_completa': 'No negociar con esta persona.'
            }
        
        prompt = f"""Analiza oferta. Responde breve.

De: {carta.get('remi')}
Mensaje: {carta.get('cuerpo', '')[:150]}

EVALUACION: [interesante/no interesante]
TACTICA: [cómo responder]"""
        
        respuesta = self.ia.consultar(prompt)
        
        return {
            'evaluacion': self._extraer_campo(respuesta, 'EVALUACION', 'TACTICA'),
            'tactica': self._extraer_campo(respuesta, 'TACTICA', None),
            'respuesta_completa': respuesta
        }
    
    # =========================================================================
    # GESTIÓN DEL BUZÓN
    # =========================================================================
    
    def get_cartas_recibidas(self) -> List[Dict]:
        """Obtiene cartas dirigidas a nosotros."""
        self.actualizar_info()
        buzon = self.get_buzon()
        
        return [
            {**carta, 'uid': uid}
            for uid, carta in buzon.items()
            if carta.get('dest') == self.alias
        ]
    
    def limpiar_buzon(self, mantener: int = 10):
        """Limpia el buzón manteniendo las últimas N cartas."""
        buzon = self.get_buzon()
        
        if not buzon:
            print("✓ Buzón vacío")
            return
        
        print(f"🧹 Limpiando buzón ({len(buzon)} cartas)...")
        
        borradas = 0
        importantes = []
        
        for uid, carta in buzon.items():
            remitente = carta.get('remi', '')
            
            # Borrar cartas de lista negra
            if remitente in self.lista_negra:
                if self.api.eliminar_carta(uid):
                    borradas += 1
                continue
            
            # Borrar cartas que no son para nosotros
            if carta.get('dest') != self.alias:
                if self.api.eliminar_carta(uid):
                    borradas += 1
                continue
            
            importantes.append((uid, carta))
        
        # Borrar las más antiguas si hay demasiadas
        if len(importantes) > mantener:
            for uid, _ in importantes[:-mantener]:
                if self.api.eliminar_carta(uid):
                    borradas += 1
        
        print(f"✓ {borradas} cartas eliminadas")
    
    # =========================================================================
    # CAMPAÑAS DE NEGOCIACIÓN
    # =========================================================================
    
    def ejecutar_campana(self):
        """Ejecuta una campaña de negociación contactando a todos."""
        print("="*60)
        print("🤖 CAMPAÑA DE NEGOCIACIÓN")
        print("="*60)
        
        self.actualizar_info()
        self.actualizar_gente()
        
        if not self.info_actual:
            print("✗ No se pudo conectar a la API")
            return
        
        # Mostrar estado
        necesidades = self.calcular_necesidades()
        excedentes = self.calcular_excedentes()
        
        print(f"\n💰 Oro: {self.get_oro()}")
        print(f"🎯 Necesitas: {json.dumps(necesidades, ensure_ascii=False)}")
        print(f"📦 Excedentes: {json.dumps(excedentes, ensure_ascii=False)}")
        
        if self.lista_negra:
            print(f"🚨 Lista negra: {', '.join(self.lista_negra)}")
        
        # Filtrar personas
        alias_propios = self.info_actual.get('Alias', [])
        personas = [
            p for p in self.gente
            if p != self.alias 
            and p not in alias_propios
            and p not in self.lista_negra
        ]
        
        print(f"\n👥 Contactando {len(personas)} personas...")
        print("-"*60)
        
        exitosas = 0
        for persona in personas:
            print(f"\n🤝 {persona}")
            propuesta = self.generar_propuesta(persona)
            
            if self.enviar_carta(persona, propuesta['asunto'], propuesta['cuerpo']):
                exitosas += 1
                self.historial_negociaciones[persona] = {
                    'propuesta': propuesta,
                    'timestamp': time.time()
                }
            
            time.sleep(0.5)  # No saturar API
        
        print(f"\n{'='*60}")
        print(f"✓ {exitosas}/{len(personas)} cartas enviadas")
    
    def procesar_respuestas(self) -> List[Dict]:
        """Procesa respuestas y detecta aceptaciones."""
        cartas = self.get_cartas_recibidas()
        acuerdos = []
        
        print(f"\n📬 Procesando {len(cartas)} mensajes...")
        
        for carta in cartas:
            remitente = carta.get('remi', 'Desconocido')
            
            if remitente in self.lista_negra:
                print(f"⚠️ Ignorando {remitente} (lista negra)")
                continue
            
            if self.detectar_robo(carta):
                continue
            
            acuerdo = self.detectar_aceptacion(carta)
            if acuerdo:
                print(f"✅ ACEPTACIÓN de {remitente}!")
                acuerdos.append(acuerdo)
                self.acuerdos_pendientes[remitente] = acuerdo
            else:
                analisis = self.analizar_respuesta(carta)
                print(f"💬 {remitente}: {analisis.get('evaluacion', 'Sin evaluar')}")
        
        return acuerdos
    
    def ciclo_completo(self, rondas: int = 3):
        """Ejecuta un ciclo completo de negociación."""
        print("="*60)
        print("🔄 CICLO DE NEGOCIACIÓN COMPLETO")
        print("="*60)
        
        for ronda in range(1, rondas + 1):
            print(f"\n📍 RONDA {ronda}/{rondas}")
            
            self.ejecutar_campana()
            
            print("\n⏳ Esperando respuestas (30s)...")
            time.sleep(30)
            
            acuerdos = self.procesar_respuestas()
            
            if acuerdos:
                print("\n📦 Procesando acuerdos...")
                for acuerdo in acuerdos:
                    self._ejecutar_acuerdo(acuerdo)
            
            self.actualizar_info()
            if self.objetivo_completado():
                print(f"\n🏆 ¡OBJETIVO COMPLETADO!")
                break
            
            if ronda < rondas:
                time.sleep(10)
        
        self._mostrar_resumen()
    
    def _ejecutar_acuerdo(self, acuerdo: Dict):
        """Ejecuta un acuerdo de intercambio."""
        remitente = acuerdo.get('remitente')
        
        if remitente in self.lista_negra:
            print(f"🚨 {remitente} está en lista negra")
            return
        
        if remitente in self.historial_negociaciones:
            propuesta = self.historial_negociaciones[remitente].get('propuesta', {})
            cuerpo = propuesta.get('cuerpo', '')
            terminos = self._extraer_terminos(cuerpo)
            
            if terminos.get('ofrece'):
                print(f"📦 Envío a {remitente}: {terminos['ofrece']}")
                confirmar = input("¿Confirmar? (s/n): ").lower()
                if confirmar == 's':
                    self.enviar_paquete(remitente, terminos['ofrece'])
    
    def _mostrar_resumen(self):
        """Muestra resumen de las negociaciones."""
        print("\n" + "="*60)
        print("📊 RESUMEN")
        print("="*60)
        print(f"Intercambios: {len(self.intercambios_realizados)}")
        for i in self.intercambios_realizados:
            print(f"  → {i['destinatario']}: {i['recursos']}")
        print(f"\nOro actual: {self.get_oro()}")
        print(f"Objetivo: {'✅ Completado' if self.objetivo_completado() else '❌ Pendiente'}")
