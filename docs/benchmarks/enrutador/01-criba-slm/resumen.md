# Criba de SLM: resumen

- Fecha: 2026-11-26 16:58 UTC
- Máquina: AMD Ryzen 7 5800H with Radeon Graphics · GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB · Ollama 0.40.7 · Python 3.14.8
- Preguntas: 15 de las guías + 5 trampa · fragmentos del RAG: 3 · num_ctx: 8192 · temperatura 0

Columnas: **Trampas** = trampas en las que se abstiene (bien). **Abst. en guías** = preguntas de las guías en las que se abstiene (mal).

| Modelo | Parám. | Cuant. | GPU | Español | Formato | Trampas | Abst. en guías | Vacías | s/resp. | tok/s | Logprobs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5:0.8b | 752.39M | Q8_0 | 100 % GPU | 20/20 | 20/20 | 4/5 | 14/15 | 0 | 0.2 | 158 | sí |
| qwen3.5:2b | 1.9B | Q8_0 | 100 % GPU | 20/20 | 16/20 | 3/5 | 1/15 | 0 | 0.7 | 81 | sí |
| qwen3.5:4b | 4.2B | Q4_K_M | 100 % GPU | 20/20 | 17/20 | 5/5 | 0/15 | 0 | 1.3 | 60 | sí |
| gemma4:e2b | 4.6B | Q4_K_M | 100 % GPU | 20/20 | 20/20 | 5/5 | 3/15 | 0 | 0.4 | 152 | sí |
| ministral-3:3b | 3.8B | Q4_K_M | 100 % GPU | 20/20 | 20/20 | 5/5 | 0/15 | 0 | 1.1 | 82 | sí |
| nemotron-3-nano:4b | 4.0B | Q4_K_M | 100 % GPU | 20/20 | 20/20 | 5/5 | 8/15 | 0 | 0.7 | 75 | sí |
| llama3.2:3b | 3.2B | Q4_K_M | 100 % GPU | 20/20 | 1/20 | 5/5 | 11/15 | 0 | 0.4 | 98 | sí |
| granite4:3b | 3.4B | Q4_K_M | 100 % GPU | 20/20 | 18/20 | 4/5 | 0/15 | 0 | 0.8 | 81 | sí |

## Versiones exactas

| Modelo | Familia | Tamaño | Digest |
|---|---|---|---|
| qwen3.5:0.8b | qwen35 | 1.32 GB | `de63045f2975` |
| qwen3.5:2b | qwen35 | 2.68 GB | `0689d44085e0` |
| qwen3.5:4b | qwen35 | 3.32 GB | `d8b0f5e9760c` |
| gemma4:e2b | gemma4 | 4.59 GB | `b37049369adf` |
| ministral-3:3b | mistral3 | 2.95 GB | `f04aa1c738f6` |
| nemotron-3-nano:4b | nemotron_h | 2.84 GB | `d94b6dfae26d` |
| llama3.2:3b | llama | 2.02 GB | `a80c4f17acd5` |
| granite4:3b | granite | 2.1 GB | `89962fcc7523` |
