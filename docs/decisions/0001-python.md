# 0001 · Python como lenguaje del backend

- **Fecha:** 2026-11-11
- **Estado:** propuesta (se acepta al mergear la PR que la añade)

## Contexto

El stack no estaba decidido, pero el primer código del proyecto ya está en Python:
`shared/db/init_db.py` (PR #5), que crea la base de datos SQLite con la librería estándar.
El siguiente paso es el adaptador de Instagram (`modules/channels/instagram/`), que lanza
`instagram-cli` como un programa aparte y lee su salida en JSON. Hace falta fijar el lenguaje
antes de escribirlo.

## Decisión

1. **Python 3.11 o superior** para todo el código del backend (`modules/`, `shared/`).
2. **Primero la librería estándar.** Cualquier dependencia externa se consulta antes con el
   equipo (regla del AGENTS.md).
3. **Tests con `unittest`**, que viene con Python. Se ejecutan desde la raíz del repo con
   `python -m unittest`.
4. `instagram-cli` es una herramienta externa escrita en TypeScript (Node.js 22 o superior).
   No forma parte del código de Python: el adaptador la ejecuta como un proceso aparte.

## Por qué

- **Ya lo usamos** en el script de la base de datos, que funciona solo con la librería estándar.
- **SQLite y JSON** vienen incluidos (`sqlite3`, `json`), igual que lanzar procesos (`subprocess`).
  Para la primera parte del MVP no hace falta instalar nada.
- **Las librerías de IA** (clientes de modelos, embeddings para el RAG) tienen su mejor
  soporte en Python.
- **3.11** es una versión estable y extendida, para que nadie del equipo tenga problemas.
- **`unittest`** evita añadir una dependencia solo para los tests. Si más adelante hace falta
  algo más cómodo (por ejemplo, `pytest`), se puede cambiar: `pytest` ejecuta también los
  tests escritos con `unittest`.

## Pendiente

- Framework web para el dashboard (`modules/platform/`).
- Gestor de dependencias y entorno virtual (`venv` + `requirements.txt`, `uv`…), cuando
  aparezca la primera dependencia.
