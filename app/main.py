"""
Interfaz de usuario.
Punto de entrada principal del programa.

Uso interactivo:
    python main.py

Uso automático (para lanzar desde test_runner.py):
    python main.py --alias Bot_1 --modelo llama3.2:3b --debug --max-rondas 10 --pausa 15
"""

import sys
import argparse
import json
from negociador import AgenteNegociador
from api_client import APIClient
from config import MODELOS_DISPONIBLES, MODELO_DEFAULT


def menu_agente(alias: str):
    """
    Menú del bot negociador autónomo (modo interactivo).
    """
    print("\n" + "="*60)
    print("🤖 CONFIGURACIÓN DEL AGENTE")
    print("="*60)
    
    # Modelo
    print(f"\n1. Modelo de IA:")
    for key, (modelo, desc) in MODELOS_DISPONIBLES.items():
        marca = " ←" if modelo == MODELO_DEFAULT else ""
        print(f"   {key}. {modelo:20} {desc}{marca}")
    
    opcion_modelo = input(f"\nSelecciona modelo (1-4) [default: 1]: ").strip() or "1"
    modelo = MODELOS_DISPONIBLES.get(opcion_modelo, (MODELO_DEFAULT, ""))[0]
    
    # Debug
    debug_input = input("\n¿Activar modo DEBUG? (s/n) [default: s]: ").strip().lower() or "s"
    debug = debug_input == "s"
    
    # Max rondas
    rondas_input = input("\nMáximo de rondas (default: 10): ").strip()
    max_rondas = int(rondas_input) if rondas_input.isdigit() else 10
    
    # Pausa entre rondas
    pausa_input = input("Segundos entre rondas (default: 30): ").strip()
    pausa = int(pausa_input) if pausa_input.isdigit() else 30
    
    # Confirmar
    print("\n" + "="*60)
    print("📋 RESUMEN DE CONFIGURACIÓN")
    print("="*60)
    print(f"  Alias: {alias}")
    print(f"  Modelo: {modelo}")
    print(f"  Debug: {'ACTIVADO' if debug else 'desactivado'}")
    print(f"  Max rondas: {max_rondas}")
    print(f"  Pausa entre rondas: {pausa}s")
    print("="*60)
    
    if input("\n¿Iniciar agente? (s/n): ").strip().lower() != 's':
        return
    
    _ejecutar_agente(alias, modelo, debug, max_rondas, pausa, interactivo=True)


def _ejecutar_agente(alias: str, modelo: str, debug: bool,
                     max_rondas: int, pausa: int, interactivo: bool = False):
    """
    Crea y ejecuta el agente negociador.

    Args:
        alias: Nombre del bot.
        modelo: Modelo de IA a usar.
        debug: Activar modo debug.
        max_rondas: Máximo de rondas.
        pausa: Segundos entre rondas.
        interactivo: Si True, muestra menú post-ejecución.
    """
    agente = AgenteNegociador(alias, modelo, debug)
    agente.pausa_entre_rondas = pausa
    
    try:
        agente.ejecutar(max_rondas)
    except KeyboardInterrupt:
        print("\n\n⏹️ Agente detenido por el usuario")
        agente._mostrar_resumen()

    if not interactivo:
        return

    # Opciones post-ejecución (solo en modo interactivo)
    while True:
        print("\n" + "="*60)
        print("📜 OPCIONES POST-EJECUCIÓN")
        print("="*60)
        print("1. Ver log completo")
        print("2. Ver log (últimas 50)")
        print("3. Ver lista negra")
        print("4. Continuar ejecución")
        print("0. Salir")
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            agente.ver_log(len(agente.log))
        elif opcion == "2":
            agente.ver_log(50)
        elif opcion == "3":
            print("\n🛡️ LISTA NEGRA:")
            if agente.lista_negra:
                for p in agente.lista_negra:
                    print(f"  ⚠️ {p}")
            else:
                print("  (vacía)")
        elif opcion == "4":
            rondas = input("Rondas adicionales (default: 5): ").strip()
            rondas = int(rondas) if rondas.isdigit() else 5
            try:
                agente.ejecutar(rondas)
            except KeyboardInterrupt:
                print("\n⏹️ Detenido")
                agente._mostrar_resumen()
        elif opcion == "0":
            break


def menu_api():
    """Menú para operaciones manuales de la API."""
    api = APIClient()
    
    while True:
        print("\n" + "="*60)
        print("📡 OPERACIONES API (MANUAL)")
        print("="*60)
        print("1. Ver mi información")
        print("2. Ver jugadores")
        print("3. Crear alias")
        print("4. Eliminar alias")
        print("5. Enviar carta")
        print("6. Enviar paquete")
        print("7. Eliminar carta")
        print("0. Volver")
        print("="*60)
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            info = api.get_info()
            if info:
                print("\n📊 INFORMACIÓN:")
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
                print(f"✓ Alias '{nombre}' creado")
        
        elif opcion == "4":
            nombre = input("Alias a eliminar: ").strip()
            if nombre:
                api.eliminar_alias(nombre)
                print(f"✓ Alias '{nombre}' eliminado")
        
        elif opcion == "5":
            remi = input("Remitente (tu alias): ").strip()
            dest = input("Destinatario: ").strip()
            asunto = input("Asunto: ").strip()
            cuerpo = input("Cuerpo: ").strip()
            if all([remi, dest, asunto, cuerpo]):
                if api.enviar_carta(remi, dest, asunto, cuerpo):
                    print("✓ Carta enviada")
                else:
                    print("✗ Error al enviar")
        
        elif opcion == "6":
            dest = input("Destinatario: ").strip()
            recursos = {}
            print("Recursos (Enter vacío para terminar):")
            while True:
                r = input("  Recurso: ").strip()
                if not r:
                    break
                c = input(f"  Cantidad de {r}: ").strip()
                if c.isdigit():
                    recursos[r] = int(c)
            if recursos:
                if api.enviar_paquete(dest, recursos):
                    print(f"✓ Paquete enviado: {recursos}")
                else:
                    print("✗ Error al enviar")
        
        elif opcion == "7":
            uid = input("UID de la carta: ").strip()
            if uid:
                api.eliminar_carta(uid)
                print(f"✓ Carta {uid} eliminada")
        
        elif opcion == "0":
            break


def parse_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Agente Negociador Autónomo para fdi-pln-butler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  Modo interactivo (menú):
    python main.py

  Lanzar bot directamente:
    python main.py --alias Bot_1
    python main.py --alias Bot_1 --modelo llama3.2:3b --debug --max-rondas 15 --pausa 20
        """
    )
    parser.add_argument(
        "--alias", type=str, default=None,
        help="Nombre/alias del bot. Si se proporciona, se ejecuta en modo automático (sin menú interactivo)."
    )
    parser.add_argument(
        "--modelo", type=str, default=MODELO_DEFAULT,
        help=f"Modelo de IA a usar (default: {MODELO_DEFAULT})"
    )
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Activar modo debug (muestra cada decisión del agente)"
    )
    parser.add_argument(
        "--max-rondas", type=int, default=10,
        help="Número máximo de rondas de negociación (default: 10)"
    )
    parser.add_argument(
        "--pausa", type=int, default=30,
        help="Segundos de espera entre rondas (default: 30)"
    )
    return parser.parse_args()


def main():
    """Punto de entrada principal."""
    args = parse_args()

    # ─── Modo automático (CLI) ───────────────────────────────────────────
    if args.alias:
        print(f"🤖 Iniciando bot '{args.alias}' en modo automático...")
        _ejecutar_agente(
            alias=args.alias,
            modelo=args.modelo,
            debug=args.debug,
            max_rondas=args.max_rondas,
            pausa=args.pausa,
            interactivo=False,
        )
        return

    # ─── Modo interactivo (menú) ─────────────────────────────────────────
    print("="*60)
    print("🎮 SISTEMA DE NEGOCIACIÓN AUTÓNOMO")
    print("="*60)
    print("\nEl agente negociará automáticamente para:")
    print("  1️⃣  Conseguir los recursos objetivo")
    print("  2️⃣  Maximizar el oro vendiendo excedentes")
    print("\nActivando DEBUG verás todo lo que hace el agente:")
    print("  📤 Cartas enviadas")
    print("  📥 Cartas recibidas")
    print("  🔍 Análisis de ofertas")
    print("  🧠 Decisiones tomadas")
    print("  🔄 Intercambios ejecutados")
    print("="*60)
    
    while True:
        print("\n1. 🤖 INICIAR AGENTE AUTÓNOMO")
        print("2. 📡 Operaciones API (manual)")
        print("0. Salir")
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == "1":
            alias = input("\nTu alias para negociar: ").strip()
            if alias:
                menu_agente(alias)
        elif opcion == "2":
            menu_api()
        elif opcion == "0":
            print("\n¡Hasta luego!")
            break


if __name__ == "__main__":
    main()
