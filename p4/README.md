# Quijote IR TUI

Aplicación de recuperación de información para la práctica 4 de PLN sobre *Don Quijote de la Mancha*. El proyecto prioriza la parte obligatoria de la rúbrica: preprocesado completo, búsqueda clásica, búsqueda semántica con vectores de spaCy, arquitectura modular y una interfaz principal interactiva en terminal con `textual`.

> Asignatura: Procesamiento del Lenguaje Natural, UCM  
> Curso: 2025-2026

## Integrantes

- Héctor García Rincón
- Pablo Manuel Rodríguez Sosa

## Descripción

La aplicación trabaja sobre el HTML del Quijote incluido en el repositorio, extrae capítulos, construye chunks sustanciales con solapamiento configurable, aplica un pipeline lingüístico homogéneo a corpus y consulta, y permite recuperar pasajes relevantes mediante:

- búsqueda clásica con TF-IDF propio implementado con `numpy`
- búsqueda semántica con embeddings generados localmente con spaCy `es_core_news_lg`

RAG queda expresamente fuera del flujo principal. El proyecto solo deja ese punto encapsulado y desactivado por defecto para una extensión futura.

## Requisitos

- Linux
- Python 3.12 o superior
- `uv` instalado
- Modelo de spaCy en español: `es_core_news_lg`

## Instalación

Desde la raíz del monorepo:

```bash
uv sync --project p4
uv run --project p4 python -m spacy download es_core_news_lg
```

Si quieres cambiar parámetros de chunking o ranking, copia `p4/.env.example` a `p4/.env` y ajusta las variables `QUIJOTE_*`.

## Ejecución

La entrada principal es:

```bash
uv run --project p4 python -m p4.main
```

Sin subcomandos, se abre la TUI.

## Regenerar recursos

```bash
uv run --project p4 python -m p4.main build-chunks
uv run --project p4 python -m p4.main build-classical
uv run --project p4 python -m p4.main build-semantic
uv run --project p4 python -m p4.main build-all
uv run --project p4 python -m p4.main build-all --no-semantic
```

## Lanzar la TUI

```bash
uv run --project p4 python -m p4.main tui
```

## Uso de los modos de búsqueda

```bash
uv run --project p4 python -m p4.main search "molinos de viento" --mode classical
uv run --project p4 python -m p4.main search "episodios sobre locura y caballería" --mode semantic
```

## Estructura

```text
p4/
├── app/
├── artifacts/
├── logs/
├── quijote/
├── .env.example
├── pyproject.toml
├── settings.toml
└── main.py
```

## Limitaciones conocidas

- La búsqueda semántica depende de `es_core_news_lg`.
- El repositorio no incluye modelos, solo el código y el corpus.
- Si cambian corpus, configuración o modelo, hay que regenerar artefactos.
- RAG no forma parte del flujo obligatorio y permanece desactivado.
