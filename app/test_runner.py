#!/usr/bin/env python3
"""
Script de Orquestación — lanza N bots negociadores en paralelo.

Cada bot se ejecuta como un subproceso independiente de main.py con un alias
único (Bot_1, Bot_2, …).  La salida de cada uno se redirige a un fichero de
log individual dentro de la carpeta ./logs/.

Uso:
    python test_runner.py                       # 3 bots por defecto
    python test_runner.py -n 5                  # 5 bots
    python test_runner.py -n 2 --modelo llama3.2:3b --debug
    python test_runner.py -n 4 --prefijo Agent  # Agent_1, Agent_2, …
    python test_runner.py -n 3 --consola        # salida coloreada por terminal

Cierre limpio con Ctrl+C: envía SIGTERM a todos los hijos y espera.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuración por defecto ───────────────────────────────────────────────
DEFAULT_N = 1
DEFAULT_MODELO = "qwen3-vl:8b"
DEFAULT_MAX_RONDAS = 10
DEFAULT_PAUSA = 30
DEFAULT_PREFIJO = "Bot"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
MAIN_SCRIPT = Path(__file__).resolve().parent / "main.py"

# Colores ANSI para modo consola (hasta 8 bots; luego se repiten)
COLORES = [
    "\033[92m",   # verde
    "\033[94m",   # azul
    "\033[93m",   # amarillo
    "\033[95m",   # magenta
    "\033[96m",   # cian
    "\033[91m",   # rojo
    "\033[97m",   # blanco brillante
    "\033[33m",   # naranja/marrón
]
RESET = "\033[0m"


def crear_directorio_logs():
    """Crea la carpeta de logs si no existe."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def construir_comando(alias: str, args: argparse.Namespace) -> list[str]:
    """Construye la lista de argumentos para lanzar un bot."""
    cmd = [
        sys.executable, str(MAIN_SCRIPT),
        "--alias", alias,
        "--modelo", args.modelo,
        "--max-rondas", str(args.max_rondas),
        "--pausa", str(args.pausa),
    ]
    if args.debug:
        cmd.append("--debug")
    return cmd


def lanzar_modo_logs(aliases: list[str], args: argparse.Namespace):
    """
    Lanza todos los bots redirigiendo stdout+stderr a archivos de log.
    """
    crear_directorio_logs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    procesos: list[tuple[str, subprocess.Popen, object]] = []

    # Entorno con PYTHONUNBUFFERED para que los logs se escriban en tiempo real
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    for alias in aliases:
        log_path = LOGS_DIR / f"{alias}_{timestamp}.log"
        log_file = open(log_path, "w", encoding="utf-8")

        cmd = construir_comando(alias, args)
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(MAIN_SCRIPT.parent),
            env=env,
            # Crear nuevo grupo de proceso para poder matar limpiamente
            preexec_fn=os.setsid if sys.platform != "win32" else None,
        )
        procesos.append((alias, proc, log_file))
        print(f"  ✅ {alias}  (PID {proc.pid})  →  {log_path}")

    return procesos


def lanzar_modo_consola(aliases: list[str], args: argparse.Namespace):
    """
    Lanza todos los bots con salida a terminal, añadiendo un prefijo coloreado.
    Se usa un hilo lector por bot (línea a línea) que antepone [Bot_N].
    """
    import threading

    procesos: list[tuple[str, subprocess.Popen, None]] = []
    hilos: list[threading.Thread] = []

    # Entorno con PYTHONUNBUFFERED para salida en tiempo real
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    def lector(alias: str, stream, color: str):
        """Lee líneas del subproceso y las imprime con prefijo coloreado."""
        prefijo = f"{color}[{alias}]{RESET} "
        try:
            for linea in iter(stream.readline, ""):
                if linea:
                    print(f"{prefijo}{linea}", end="", flush=True)
        except ValueError:
            pass  # stream cerrado
        finally:
            stream.close()

    for i, alias in enumerate(aliases):
        color = COLORES[i % len(COLORES)]
        cmd = construir_comando(alias, args)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(MAIN_SCRIPT.parent),  # line-buffered
            env=env,
            preexec_fn=os.setsid if sys.platform != "win32" else None,
        )
        procesos.append((alias, proc, None))
        print(f"  {color}✅ {alias}{RESET}  (PID {proc.pid})")

        t = threading.Thread(target=lector, args=(alias, proc.stdout, color), daemon=True)
        t.start()
        hilos.append(t)

    return procesos


def matar_procesos(procesos: list):
    """Envía SIGTERM/SIGKILL a todos los procesos hijos."""
    for alias, proc, log_file in procesos:
        if proc.poll() is None:  # sigue vivo
            try:
                # Matar el grupo de proceso completo
                if sys.platform != "win32":
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
            except (ProcessLookupError, OSError):
                pass

    # Dar un momento para que terminen
    time.sleep(1)

    for alias, proc, log_file in procesos:
        if proc.poll() is None:
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, OSError):
                pass

        if log_file and not log_file.closed:
            log_file.close()


def esperar_procesos(procesos: list):
    """Espera a que todos los procesos terminen normalmente."""
    for alias, proc, log_file in procesos:
        proc.wait()
        if log_file and not log_file.closed:
            log_file.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Lanza N bots negociadores en paralelo para pruebas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-n", type=int, default=DEFAULT_N,
        help=f"Número de bots a lanzar (default: {DEFAULT_N})"
    )
    parser.add_argument(
        "--prefijo", type=str, default=DEFAULT_PREFIJO,
        help=f"Prefijo para los nombres de los bots (default: '{DEFAULT_PREFIJO}')"
    )
    parser.add_argument(
        "--modelo", type=str, default=DEFAULT_MODELO,
        help=f"Modelo de IA (default: {DEFAULT_MODELO})"
    )
    parser.add_argument(
        "--debug", action="store_true", default=True,
        help="Activar modo debug en todos los bots (activado por defecto)"
    )
    parser.add_argument(
        "--no-debug", action="store_true", default=False,
        help="Desactivar modo debug"
    )
    parser.add_argument(
        "--max-rondas", type=int, default=DEFAULT_MAX_RONDAS,
        help=f"Rondas máximas por bot (default: {DEFAULT_MAX_RONDAS})"
    )
    parser.add_argument(
        "--pausa", type=int, default=DEFAULT_PAUSA,
        help=f"Pausa entre rondas en segundos (default: {DEFAULT_PAUSA})"
    )
    parser.add_argument(
        "--consola", action="store_true", default=False,
        help="Mostrar salida coloreada en terminal en vez de logs a archivos"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    aliases = [f"{args.prefijo}_{i}" for i in range(1, args.n + 1)]

    if args.n > 1:
        print("\n" + "⚠" * 30)
        print("⚠  ADVERTENCIA: La API del juego solo soporta 1 alias activo")
        print("   por cuenta. Lanzar múltiples bots hará que se sobreescriban")
        print("   mutuamente. Se recomienda usar -n 1 (por defecto).")
        print("⚠" * 30 + "\n")

    print("=" * 60)
    print("🚀 ORQUESTADOR DE BOTS NEGOCIADORES")
    print("=" * 60)
    print(f"  Bots:       {args.n}  ({', '.join(aliases)})")
    print(f"  Modelo:     {args.modelo}")
    print(f"  Debug:      {'SÍ' if args.debug else 'NO'}")
    print(f"  Max rondas: {args.max_rondas}")
    print(f"  Pausa:      {args.pausa}s")
    print(f"  Salida:     {'consola (coloreada)' if args.consola else f'archivos en {LOGS_DIR}/'}")
    print("=" * 60)
    print("\n🔧 Lanzando bots...\n")

    if args.consola:
        procesos = lanzar_modo_consola(aliases, args)
    else:
        procesos = lanzar_modo_logs(aliases, args)

    print(f"\n{'=' * 60}")
    print("✅ Todos los bots lanzados. Pulsa Ctrl+C para detenerlos.")
    print(f"{'=' * 60}\n")

    # ─── Gestión de señales para cierre limpio ────────────────────────────
    detenido = False

    def handler_sigint(signum, frame):
        nonlocal detenido
        if detenido:
            return
        detenido = True
        print(f"\n\n{'=' * 60}")
        print("⏹️  Ctrl+C recibido — deteniendo todos los bots...")
        print(f"{'=' * 60}")
        matar_procesos(procesos)
        # Resumen
        print("\n📊 RESUMEN FINAL:")
        for alias, proc, _ in procesos:
            rc = proc.returncode
            estado = "✅ OK" if rc == 0 else f"⚠️  código {rc}" if rc else "🛑 forzado"
            print(f"  {alias:15} PID {proc.pid:>7}  →  {estado}")
        print()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler_sigint)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handler_sigint)

    # ─── Esperar a que terminen normalmente ───────────────────────────────
    try:
        esperar_procesos(procesos)
    except KeyboardInterrupt:
        handler_sigint(None, None)

    print(f"\n{'=' * 60}")
    print("🏁 Todos los bots han terminado.")
    print(f"{'=' * 60}")
    if not args.consola:
        print(f"\n📂 Logs disponibles en: {LOGS_DIR}/")

    # Resumen
    print("\n📊 RESUMEN FINAL:")
    for alias, proc, _ in procesos:
        rc = proc.returncode
        estado = "✅ OK" if rc == 0 else f"⚠️  código {rc}"
        print(f"  {alias:15} PID {proc.pid:>7}  →  {estado}")
    print()


if __name__ == "__main__":
    main()
