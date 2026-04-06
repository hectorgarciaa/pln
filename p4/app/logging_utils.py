"""Configuración centralizada de logging."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def configure_logging(logs_dir: Path) -> None:
    """Configura salida a consola y fichero rotado."""

    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    )
    logger.add(
        logs_dir / "quijote_ir.log",
        level="DEBUG",
        rotation="1 MB",
        retention=3,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
    )
