"""Wrapper de entrada para ejecutar la práctica 3 desde el monorepo."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("fdi-pln-2602-p3.py")),
        run_name="__main__",
    )
