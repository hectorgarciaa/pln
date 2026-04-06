# Práctica 3

Implementación del conversor `UTF-8 <-> PLNCG26`.

## Uso con uv

Desde la raíz del repositorio:

```bash
uv sync --project p3
uv run --project p3 python p3/main.py --help
```

Comandos principales:

```bash
uv run --project p3 python p3/main.py encode p3/principal.bin --offset 77
uv run --project p3 python p3/main.py decode p3/principal.bin --offset 77
uv run --project p3 python p3/main.py detect p3/principal.bin
```
