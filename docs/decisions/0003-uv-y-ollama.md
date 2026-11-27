# 0003 · Dependencias con `uv` y SLM locales con Ollama

- **Fecha:** 2026-11-26
- **Estado:** propuesta (se acepta al mergear la PR que la añade)

## Contexto

Hasta ahora todo el código usa solo la librería estándar, y el gestor de dependencias quedó
pendiente en la 0001. El benchmark del enrutador necesita librerías (scikit-learn, SetFit, e5) y un
programa que ejecute varios SLM en local para compararlos.

## Decisión

1. **`uv` como gestor de dependencias.** `pyproject.toml` en la raíz, versiones fijadas en
   `uv.lock` y Python fijado a 3.12 en `.python-version` (el mínimo sigue siendo 3.11).
2. **Las dependencias del benchmark van en el grupo `bench`**, así no se instalan en producción:
   `uv sync` instala lo de producción y `uv sync --group bench` añade el benchmark.
3. **Ollama para ejecutar los SLM.** No es una dependencia de Python: es un programa aparte que
   se instala en la máquina y se llama por HTTP.
4. **El cliente de modelos usa la API compatible con OpenAI** y se escribe con la librería
   estándar (`urllib`). `llama-server` (llama.cpp) habla la misma API, así que cambiar de uno a
   otro es cambiar una URL.

## Por qué

| Gestor | ✅ | ❌ |
|---|---|---|
| `venv` + `pip` | Viene con Python | No fija las versiones de las dependencias indirectas ni la versión de Python |
| **`uv`** | Rápido, fija versiones y Python, grupos de dependencias | Hay que instalarlo |
| Poetry | Muy conocido | Más lento y con más configuración que `uv` |

| Ejecutar SLM | ✅ | ❌ |
|---|---|---|
| **Ollama** | `ollama pull <modelo>` y listo. Da `logprobs` | Menos control. Los modelos con modo "pensar" hay que configurarlos (ver abajo) |
| llama.cpp | Todo el control | Más manual (compilar, descargar modelos) |
| vLLM / transformers | Acceso total al modelo | Piden más memoria de la que tenemos (6 GB de GPU) |

## Prueba hecha

Con `qwen3:1.7b` y `gemma3:1b`, una pregunta que está en la guía de bonos y otra que no:

- **Ollama devuelve la probabilidad de cada token** en los dos modelos, que es lo que necesita una
  de las formas de medir la confianza del enrutador.
- **Qwen3 tiene modo "pensar":** si no se desactiva (`"think": false`), gasta todos los tokens
  pensando y devuelve una respuesta vacía.
- **Ollama usa por defecto un contexto de 4096 tokens.** Con varios fragmentos del RAG puede
  quedarse corto, así que hay que fijar `num_ctx`.
- **Ejemplo del problema que debe medir el benchmark:** a "¿Tenéis integración con Holded?",
  Qwen3 contestó "No, no tenéis integración con Holded", **inventado**, y con una probabilidad
  media por token de 0,98. La probabilidad de los tokens por sí sola no detecta este error.
- El paquete de Ollama instalado no usa la GPU (todo fue en CPU: 0,7–1,4 s por respuesta con 1,7B).
  Para usar la GPU en Arch hay que instalar `ollama-cuda`.

## Pendiente

- Preguntar si el servidor de producción tendrá GPU. Si no, el benchmark debe medir también la
  latencia de cada SLM en CPU.
- Primeras dependencias del grupo `bench`: se añaden en la PR del benchmark.
