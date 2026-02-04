"""
Interfaz de usuario (menú interactivo).
Punto de entrada principal del programa.
"""

import json
from negociador import BotNegociador
from api_client import APIClient
from config import MODELOS_DISPONIBLES


def mostrar_estado(bot: BotNegociador):
    """Muestra el estado actual del jugador."""
    bot.actualizar_info()
    
    if not bot.info_actual:
        print("✗ No se pudo obtener información")
        return
    
    necesidades = bot.calcular_necesidades()
    excedentes = bot.calcular_excedentes()
    objetivo_ok = bot.objetivo_completado()
    
    print("\n📊 ESTADO ACTUAL")
    print("="*50)
    print(f"💰 Oro: {bot.get_oro()}")
    print(f"✅ Objetivo: {'Completado' if objetivo_ok else 'Pendiente'}")
    print(f"\n🎯 Necesitas: {json.dumps(necesidades, ensure_ascii=False)}")
    print(f"📦 Excedentes: {json.dumps(excedentes, ensure_ascii=False)}")
    
    print(f"\n📋 Recursos completos:")
    print(json.dumps(bot.get_recursos(), indent=2, ensure_ascii=False))


def revisar_buzon(bot: BotNegociador):
    """Revisa y analiza el buzón."""
    cartas = bot.get_cartas_recibidas()
    
    if not cartas:
        print("\n✓ Buzón vacío")
        return
    
    print(f"\n📬 {len(cartas)} cartas:")
    
    for i, carta in enumerate(cartas, 1):
        print(f"\n{'─'*50}")
        print(f"📧 Carta {i}")
        print(f"  De: {carta.get('remi')}")
        print(f"  Asunto: {carta.get('asunto')}")
        print(f"  Mensaje: {carta.get('cuerpo')}")
        
        analisis = bot.analizar_respuesta(carta)
        print(f"\n  🧠 Análisis: {analisis.get('evaluacion', 'N/A')}")
        print(f"  💡 Táctica: {analisis.get('tactica', 'N/A')}")


def enviar_carta_manual(bot: BotNegociador):
    """Envía una carta con propuesta generada por IA."""
    dest = input("Destinatario: ").strip()
    if not dest:
        return
    
    bot.actualizar_info()
    propuesta = bot.generar_propuesta(dest)
    
    print(f"\n📋 PROPUESTA GENERADA:")
    print(f"  Asunto: {propuesta['asunto']}")
    print(f"  Cuerpo: {propuesta['cuerpo']}")
    
    if input("\n¿Enviar? (s/n): ").lower() == 's':
        bot.enviar_carta(dest, propuesta['asunto'], propuesta['cuerpo'])


def enviar_paquete_manual(bot: BotNegociador):
    """Envía un paquete de recursos manualmente."""
    bot.actualizar_info()
    recursos = bot.get_recursos()
    
    print(f"\nTus recursos: {json.dumps(recursos, ensure_ascii=False)}")
    
    dest = input("\nDestinatario: ").strip()
    if not dest:
        return
    
    recursos_enviar = {}
    print("\nIntroduce recursos (escribe 'fin' para terminar):")
    
    while True:
        recurso = input("  Recurso: ").strip().lower()
        if recurso == 'fin':
            break
        if recurso not in recursos:
            print(f"  ⚠️ No tienes {recurso}")
            continue
        
        cantidad = input(f"  Cantidad de {recurso}: ").strip()
        if cantidad.isdigit():
            cant = int(cantidad)
            if cant <= recursos.get(recurso, 0):
                recursos_enviar[recurso] = cant
            else:
                print(f"  ⚠️ Solo tienes {recursos.get(recurso, 0)}")
    
    if recursos_enviar:
        print(f"\n📦 Envío: {recursos_enviar} → {dest}")
        if input("¿Confirmar? (s/n): ").lower() == 's':
            bot.enviar_paquete(dest, recursos_enviar)


def cambiar_modelo(bot: BotNegociador):
    """Cambia el modelo de IA."""
    print(f"\n⚡ CAMBIAR MODELO (actual: {bot.modelo})")
    print("="*50)
    
    for key, (modelo, descripcion) in MODELOS_DISPONIBLES.items():
        print(f"{key}. {modelo:20} {descripcion}")
    print("5. Personalizado")
    
    opcion = input("\nSelecciona (1-5): ").strip()
    
    if opcion in MODELOS_DISPONIBLES:
        bot.modelo = MODELOS_DISPONIBLES[opcion][0]
        print(f"✓ Modelo: {bot.modelo}")
        print(f"💡 Descarga: ollama pull {bot.modelo}")
    elif opcion == "5":
        modelo = input("Nombre del modelo: ").strip()
        if modelo:
            bot.modelo = modelo


def procesar_aceptaciones(bot: BotNegociador):
    """Procesa aceptaciones y ejecuta intercambios."""
    acuerdos = bot.procesar_respuestas()
    
    if not acuerdos:
        print("\n❌ No hay aceptaciones pendientes")
        return
    
    print(f"\n🎉 {len(acuerdos)} aceptación(es)")
    
    for i, acuerdo in enumerate(acuerdos, 1):
        print(f"\n--- Acuerdo {i} ---")
        print(f"De: {acuerdo['remitente']}")
        print(f"Términos: {acuerdo.get('terminos', {})}")
        
        if input(f"\n¿Ejecutar con {acuerdo['remitente']}? (s/n): ").lower() == 's':
            bot._ejecutar_acuerdo(acuerdo)


def menu_bot(alias: str):
    """Menú principal del bot negociador."""
    bot = BotNegociador(alias)
    
    while True:
        print("\n" + "="*60)
        print("🤖 BOT NEGOCIADOR")
        print("="*60)
        print("1. 📊 Ver estado actual")
        print("2. 🚀 Ejecutar campaña automática")
        print("3. 📬 Revisar buzón")
        print("4. ✉️  Enviar carta personalizada")
        print("5. 📦 Enviar paquete de recursos")
        print("6. 🔄 Ciclo completo (automático)")
        print("7. ✅ Procesar aceptaciones")
        print("8. 🧹 Limpiar buzón")
        print("9. 🛡️  Ver lista negra")
        print(f"10. ⚡ Cambiar modelo ({bot.modelo})")
        print("0. Salir")
        print("="*60)
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            mostrar_estado(bot)
        elif opcion == "2":
            bot.ejecutar_campana()
        elif opcion == "3":
            revisar_buzon(bot)
        elif opcion == "4":
            enviar_carta_manual(bot)
        elif opcion == "5":
            enviar_paquete_manual(bot)
        elif opcion == "6":
            rondas = input("Rondas (default 3): ").strip()
            rondas = int(rondas) if rondas.isdigit() else 3
            bot.ciclo_completo(rondas)
        elif opcion == "7":
            procesar_aceptaciones(bot)
        elif opcion == "8":
            mantener = input("Mantener últimas (default 10): ").strip()
            mantener = int(mantener) if mantener.isdigit() else 10
            bot.limpiar_buzon(mantener)
        elif opcion == "9":
            print("\n🛡️ LISTA NEGRA:")
            if bot.lista_negra:
                for p in bot.lista_negra:
                    print(f"  ⚠️ {p}")
            else:
                print("  (vacía)")
        elif opcion == "10":
            cambiar_modelo(bot)
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break


def menu_api():
    """Menú para operaciones básicas de la API."""
    api = APIClient()
    
    while True:
        print("\n" + "="*60)
        print("📡 OPERACIONES API")
        print("="*60)
        print("1. Ver información")
        print("2. Ver jugadores")
        print("3. Crear alias")
        print("4. Eliminar alias")
        print("5. Enviar carta (manual)")
        print("6. Enviar paquete (manual)")
        print("7. Eliminar carta")
        print("0. Volver")
        print("="*60)
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            info = api.get_info()
            if info:
                print(json.dumps(info, indent=2, ensure_ascii=False))
        
        elif opcion == "2":
            gente = api.get_gente()
            print("\n👥 Jugadores:")
            for p in gente:
                print(f"  - {p}")
        
        elif opcion == "3":
            nombre = input("Nombre del alias: ").strip()
            if nombre:
                api.crear_alias(nombre)
        
        elif opcion == "4":
            nombre = input("Alias a eliminar: ").strip()
            if nombre:
                api.eliminar_alias(nombre)
        
        elif opcion == "5":
            remi = input("Remitente: ").strip()
            dest = input("Destinatario: ").strip()
            asunto = input("Asunto: ").strip()
            cuerpo = input("Cuerpo: ").strip()
            if all([remi, dest, asunto, cuerpo]):
                api.enviar_carta(remi, dest, asunto, cuerpo)
        
        elif opcion == "6":
            dest = input("Destinatario: ").strip()
            recursos = {}
            print("Recursos (vacío para terminar):")
            while True:
                r = input("  Recurso: ").strip()
                if not r:
                    break
                c = input(f"  Cantidad de {r}: ").strip()
                if c.isdigit():
                    recursos[r] = int(c)
            if recursos:
                api.enviar_paquete(dest, recursos)
        
        elif opcion == "7":
            uid = input("UID de la carta: ").strip()
            if uid:
                api.eliminar_carta(uid)
        
        elif opcion == "0":
            break


def main():
    """Punto de entrada principal."""
    print("="*60)
    print("🎮 SISTEMA DE NEGOCIACIÓN")
    print("="*60)
    
    while True:
        print("\n1. 🤖 Bot Negociador (IA)")
        print("2. 📡 Operaciones API")
        print("0. Salir")
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            alias = input("\nTu alias: ").strip()
            if alias:
                menu_bot(alias)
        elif opcion == "2":
            menu_api()
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break


if __name__ == "__main__":
    main()
