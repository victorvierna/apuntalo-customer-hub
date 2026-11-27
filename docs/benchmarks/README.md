# Benchmarks

Resultados de los experimentos del TFG. Cada experimento tiene su carpeta y deja todo lo necesario
para repetirlo y para escribir la memoria sin depender de nadie:

| Fichero | Qué contiene | Quién lo escribe |
|---|---|---|
| `resumen.md` | Tabla de resultados, máquina, versiones exactas de los modelos y parámetros | El script |
| `resultados.jsonl` | Los datos en bruto: una fila por modelo y pregunta | El script |
| `respuestas.md` | Las respuestas completas, para leerlas y puntuarlas | El script |
| `*.svg` | Figuras para la memoria, generadas desde `resultados.jsonl` | Un script |
| `informe.md` | Qué se quería averiguar, qué se ha visto, qué se decide y por qué | Una persona |

Un experimento no está terminado hasta que tiene `informe.md`. Si se repite (otro modelo, otra
máquina), se crea una carpeta nueva o se añade una sección al informe con la fecha: los resultados
anteriores no se borran.

## Enrutador

Orden y objetivos en `docs/architecture/enrutador-alternativas.md` (sección 5).

| # | Experimento | Carpeta | Script | Estado |
|---|---|---|---|---|
| 1 | Criba de SLM: 8 modelos, 20 preguntas | `enrutador/01-criba-slm/` | `python -m modules.router.benchmark.criba_slm` | Hecho (2026-11-26). Finalistas: qwen3.5:4b, ministral-3:3b, granite4:3b, gemma4:e2b |
| 2 | SLM finalistas: calidad, confianza y % que va al LLM | — | — | Pendiente |
| 3 | Clasificador de intención (A–D) | — | — | Pendiente (necesita el dataset) |
| 4 | RAG con y sin datos | — | — | Pendiente |
| 5 | Ahorro final frente a "siempre LLM" y "siempre SLM" | — | — | Pendiente (necesita mensajes reales) |
