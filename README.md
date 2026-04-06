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

Con `uv`:

```bash
uv sync
uv run python -m spacy download es_core_news_lg
```

Si quieres cambiar parámetros de chunking o ranking, copia `p4/.env.example` a `p4/.env` y ajusta las variables `QUIJOTE_*`. La búsqueda semántica de esta entrega está diseñada para usarse con `es_core_news_lg`.

## Ejecución en Linux

La entrada principal es:

```bash
uv run python -m p4.main
```

Sin subcomandos, se abre la TUI.

## Regenerar recursos

Regenerar chunks:

```bash
uv run python -m p4.main build-chunks
```

Regenerar índice clásico:

```bash
uv run python -m p4.main build-classical
```

Regenerar embeddings:

```bash
uv run python -m p4.main build-semantic
```

Reconstruir todo:

```bash
uv run python -m p4.main build-all
```

Reconstruir solo la parte obligatoria sin embeddings:

```bash
uv run python -m p4.main build-all --no-semantic
```

## Lanzar la TUI

```bash
uv run python -m p4.main tui
```

La TUI permite:

- seleccionar modo clásica o semántica
- escribir consultas
- navegar resultados ordenados con teclado
- ver score, metadatos y fragmento recuperado
- reconstruir recursos desde la propia interfaz

## Uso de los modos de búsqueda

Búsqueda clásica:

```bash
uv run python -m p4.main search "molinos de viento" --mode classical
```

Búsqueda semántica:

```bash
uv run python -m p4.main search "episodios sobre locura y caballería" --mode semantic
```

## Configuración

Los valores por defecto viven en [p4/settings.toml](/home/pablo/Uni/PLN/pln/p4/settings.toml). Se pueden sobreescribir con variables de entorno `QUIJOTE_*` o con un fichero `p4/.env`.

Parámetros importantes:

- modelo de spaCy
- tamaño y overlap de chunks
- `top_k`
- batch de embeddings semánticos con spaCy
- rutas de artefactos persistidos

## Estructura del proyecto

```text
p4/
├── app/
│   ├── cli.py
│   ├── config.py
│   ├── ingestion.py
│   ├── preprocessing.py
│   ├── chunking.py
│   ├── classical_search.py
│   ├── semantic_search.py
│   ├── services.py
│   ├── rag.py
│   └── tui/
├── artifacts/
├── logs/
├── quijote/
│   └── quijote.html
├── .env.example
├── settings.toml
└── main.py
```

## Limitaciones conocidas

- La búsqueda semántica depende de tener instalado `es_core_news_lg`, porque el modelo pequeño de spaCy no ofrece vectores semánticos suficientes para esta entrega.
- El repositorio no incluye modelos de IA, solo el corpus y el código para regenerar índices y embeddings.
- Si cambian el corpus, el modelo de spaCy o los parámetros de chunking, hay que reconstruir los artefactos.
- RAG no forma parte del flujo obligatorio y permanece desactivado.

## Comandos útiles

```bash
uv run python -m p4.main status
uv run python -m p4.main build-all --no-semantic
uv run python -m p4.main build-semantic
uv run python -m p4.main tui
```

## Monorepo y `uv`

Si en este repositorio conviven `p1`, `p2`, `p3` y `p4` con dependencias distintas, la forma más estable de trabajar con `uv` no es compartir un solo entorno para todo. Lo recomendable es que cada práctica sea un proyecto independiente con su propio `pyproject.toml` y su propio `uv.lock`.

Patrón recomendado:

```text
repo/
├── p1/
│   ├── pyproject.toml
│   └── uv.lock
├── p2/
│   ├── pyproject.toml
│   └── uv.lock
├── p3/
│   ├── pyproject.toml
│   └── uv.lock
└── p4/
    ├── pyproject.toml
    └── uv.lock
```

Entonces usarías:

```bash
uv sync --project p4
uv run --project p4 python -m p4.main tui
```

o entrando en cada carpeta:

```bash
cd p4
uv sync
uv run python -m p4.main tui
```

Eso evita que una práctica rompa a otra por versiones incompatibles. El estado actual del repo deja `uv` configurado para `p4` desde la raíz. Si quieres, en otro paso puedo convertir todo el repo a ese formato por-práctica.
