# Bot Negociador Autónomo (PLN)

Bot para negociar intercambios de recursos en `fdi-pln-butler`.

## Requisitos
- Python 3.12+
- Ollama en ejecución
- Servidor Butler en ejecución

## Instalación
```bash
uv sync
```

Modelo recomendado:
```bash
ollama pull qwen3:8b
```

## Ejecución
Un bot (menú interactivo):
```bash
uv run app/main.py
```

Un bot (modo automático):
```bash
uv run app/main.py --alias MiBot --debug
```

Varios bots:
```bash
uv run app/test_runner.py -n 3 --consola
```

## Arquitectura (actual)
Se eliminó la duplicidad de entrypoints: ahora la CLI real vive solo en:
- `app/main.py`
- `app/test_runner.py`

Estructura:
```text
app/
├── main.py                           # CLI principal (1 bot)
├── test_runner.py                    # CLI orquestador (N bots)
└── pln_bot/
    ├── agente/
    │   ├── negociador.py
    │   └── ronda.py
    ├── core/
    │   └── config.py
    ├── negociacion/
    │   ├── gestor_acuerdos.py
    │   ├── procesador_buzon.py
    │   ├── utilidades_mensajes.py
    │   ├── constructor_propuestas.py
    │   └── enviador_propuestas.py
    └── services/
        ├── api_client.py
        ├── ollama_client.py
        └── analysis.py
```

## Flujo de datos
1. `main.py` crea `AgenteNegociador`.
2. El agente consulta estado con `services/api_client.py`.
3. Procesa cartas con `negociacion/procesador_buzon.py`.
4. Decide con LLM + tools en `services/analysis.py`.
5. Construye/envía propuestas con `negociacion/constructor_propuestas.py` y `negociacion/enviador_propuestas.py`.
6. Ejecuta acuerdos pendientes y validaciones de seguridad en `negociacion/gestor_acuerdos.py`.

## Estrategia IA (clásica + moderna)
- IA clásica: filtros rápidos por regex para sistema/rechazos/aceptaciones en `negociacion/utilidades_mensajes.py`.
- IA moderna: análisis estructurado + decisión con salida tipada (`RespuestaUnificada`) en `services/analysis.py`.
- Tools del LLM: `consultar_necesidad`, `consultar_excedente`, `consultar_stock`, `consultar_objetivo`, `puedo_entregar`.
- Prompt adaptativo: el análisis incluye asunto, modo del agente, necesidades y excedentes para contextualizar cada carta.
- Control de coste/riesgo: solo se llama al LLM cuando los filtros clásicos no bastan.

## Configuración
Archivo central:
- `app/pln_bot/core/config.py`

Variables clave:
- `FDI_PLN__BUTLER_ADDRESS`
- `api_base_url`
- `ollama_url`
- `modelo_default`

## Opciones CLI
`app/main.py`:
- `--alias`, `-a`
- `--modelo`, `-m`
- `--debug`, `-d`
- `--max-rondas`, `-r`
- `--pausa`, `-p`
- `--api-url`

`app/test_runner.py`:
- `-n`
- `--prefijo`
- `--modelo`, `-m`
- `--debug / --no-debug`, `-d`
- `--max-rondas`, `-r`
- `--pausa`, `-p`
- `--consola`
