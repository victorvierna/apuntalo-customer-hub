# RAG: búsqueda en la ayuda (`modules/rag/`)

Busca en las guías de ayuda de Apúntalo los fragmentos que responden a una pregunta. **Solo
busca**: no llama a ningún modelo ni redacta respuestas. Devuelve los fragmentos con su
puntuación y el modelo que elija el enrutador los usa para contestar. Si no encuentra nada,
devuelve una lista vacía, y entonces el asistente no debe responder (regla del `AGENTS.md`).

```
data/faqs/ayuda/*.md ─> chunker.py ─> ~225 trozos ─> índice FTS5 en memoria
                         (trocea)                       (shared/db/faq_index.py)
                                                                │
pregunta ──────────────> search.py ─────────────────────────────┘─> [Hit, Hit, …] o []
```

Ahora mismo la búsqueda es **por palabras** (BM25 con SQLite FTS5) y solo usa la librería
estándar. La evaluación ya ha justificado pasar a una búsqueda **híbrida** (BM25 + embeddings con
`multilingual-e5-small`, fusionadas con RRF): ver `docs/decisions/0002-rag-busqueda-hibrida.md`.
Está pendiente de implementar.

## Archivos

| Archivo | Qué hace |
|---|---|
| `search.py` | `HelpIndex`: lo único que deberían usar los demás módulos. `HelpIndex.load()` lee las guías y `search(pregunta, k=5)` devuelve los `Hit`. |
| `chunker.py` | Trocea las guías por secciones. Funciones puras. |
| `evaluate.py` | Mide si la búsqueda encuentra la guía correcta con el conjunto de evaluación. |
| `tests/` | Tests con `unittest` y guías inventadas (`helpers.py`). |
| `shared/db/faq_index.py` | El SQL de FTS5 (todo el SQL va en `shared/db/`). |
| `shared/types/rag.py` | `Chunk` (un trozo) y `Hit` (un resultado). |

## Las guías

- `data/faqs/ayuda/`: guías de ayuda de Apúntalo en Markdown, más `imagenes/`. Revisión del
  16-11-2026. **Es lo único que se indexa.**
- `data/faqs/evaluacion-ayuda/`: 104 preguntas con su respuesta esperada. **No se indexa
  nunca**: si el buscador viera las respuestas de referencia, la evaluación no mediría nada. Va
  junto a `ayuda/` porque sus referencias son rutas relativas (`../ayuda/...`). Un test
  comprueba que no entra en el índice.

Para actualizar la ayuda basta con sustituir los archivos. El índice se vuelve a crear al
arrancar.

## Troceo

Las guías tienen un título `#`, secciones `##` y preguntas frecuentes `###`. Se trocean por esa
estructura, no por número de palabras:

- Cada `##` o `###` con texto es un trozo. El texto anterior al primer `##` es la introducción
  de la guía.
- Un título sin texto propio (un `##` seguido directamente de `###`) no da trozo, pero aparece en
  el título de sus hijos: `Bonos de sesiones › Preguntas frecuentes › ¿Caduca el bono?`.
- Las tablas y listas nunca se parten.
- Se salta `README.md`, porque es solo el índice de títulos y coincidiría con cualquier búsqueda.
- En el índice se quitan los destinos de los enlaces (`../09-recordatorios/...`), que añadirían
  palabras que el lector no ve, y se conserva la descripción de las imágenes.

Cada trozo tiene un identificador estable (`ref`), relativo a `data/faqs/`:
`ayuda/13-cobros-a-clientes/cobros.md#que-significan-las-tres-cifras`. Es lo que se guardará en
`faq_retrievals.faq_ref` (`database.md`, 6.7). Si dos títulos se repiten en una guía, el segundo
lleva `-2`.

## Búsqueda

- **Índice en memoria, no en la base de datos.** Crearlo tarda milisegundos, así que se rehace
  al arrancar y nunca puede estar desactualizado respecto a las guías. Tampoco cambia el esquema de
  la base de datos principal. Habría que guardarlo en disco si crearlo fuera caro (por ejemplo,
  con embeddings o con muchos más documentos).
- **Tokenizador `unicode61 remove_diacritics 2`**: "cítas", "Citas" y "citas" son la misma
  palabra.
- **Palabras unidas con OR.** Por defecto FTS5 exige todas las palabras (AND), y un mensaje
  corto e informal rara vez las comparte todas con una guía. BM25 ya pone primero los trozos que
  coinciden en más palabras y en las más raras.
- **Se quitan las palabras vacías** ("el", "de", "cómo", "hola"…). Un saludo solo no encuentra
  nada.
- **Cada palabra va entre comillas**, así lo que escribe el cliente (`NOT`, `*`, `"`) se busca
  como texto y nunca se interpreta como sintaxis de FTS5.
- **`score`**: el `bm25()` de FTS5 es negativo (cuanto más negativo, mejor). Se le cambia el
  signo para que más alto signifique más relevante. **Solo es comparable dentro de la misma
  búsqueda**, no entre preguntas distintas.
- **Todavía no hay umbral de "esto no está en la ayuda".** Es trabajo del RAG, no del
  enrutador, porque el RAG se ejecuta después de que el enrutador decida (decisión 0002). Con BM25
  no se puede poner, porque su puntuación no es comparable entre preguntas; se pondrá sobre el
  coseno de los embeddings.

Limitación conocida: solo coinciden palabras exactas. "Creo" no encuentra "crear", y "me han
cobrado dos veces" no encuentra "cobro duplicado".

## Evaluación

```
python -m modules.rag.evaluate                 # tabla de métricas
python -m modules.rag.evaluate --failures      # + preguntas cuya guía no sale en el top 3
python -m modules.rag.evaluate --out storage/rag-eval.json   # resultados completos (no van a git)
```

Hace cada pregunta de `preguntas.jsonl` y comprueba si las guías de su campo `referencias` salen
arriba. No llama a ningún modelo ni lee las respuestas esperadas. Se puntúa **por guía**, porque
el conjunto de evaluación indica guías y no secciones: varias secciones de la misma guía cuentan
una vez, en la posición de la primera.

- **Recall@k**: proporción de las guías esperadas que salen entre las k primeras (media de las
  preguntas).
- **MRR**: media de 1 / posición de la primera guía esperada (0 si no sale).

Resultado de partida (BM25, 17-11-2026, 33 guías y 225 trozos):

| Conjunto | n | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Todas | 104 | 0,486 | 0,744 | 0,827 | 0,656 |
| responder | 88 | 0,540 | 0,801 | 0,864 | 0,699 |
| aclarar | 9 | 0,333 | 0,593 | 0,667 | 0,575 |
| abstenerse_dato_cuenta | 7 | 0,000 | 0,214 | 0,571 | 0,221 |

Cómo leerlo:

- La métrica es estricta. Varias guías tratan el mismo tema: por ejemplo, "Quiero repetir una
  cita todas las semanas" encuentra primero `19-recorridos/gestionar-citas-recurrentes.md`, que lo
  explica, pero la referencia es `07-agenda-y-citas/citas.md`. Esos casos cuentan como fallo
  aunque el trozo encontrado sirva.
- Las preguntas `abstenerse_dato_cuenta` piden datos o acciones que el asistente no tiene ("¿Puedes
  confirmar que pagó?"). Ahí lo importante no es la búsqueda, sino que el sistema no afirme nada.
- Las preguntas del conjunto están bien redactadas. Los mensajes reales de Instagram serán más
  cortos y con faltas, así que esta cifra seguramente es optimista.

## Pendiente

- Probar mejoras con la evaluación antes de adoptarlas: cortar las palabras a su raíz (que
  "creo" encuentre "crear"), dar más peso al título, devolver la guía entera en vez de la sección.
- Implementar la búsqueda híbrida decidida en la 0002 (BM25 + `multilingual-e5-small` con RRF)
  y el umbral de abstención sobre el coseno.
- Escribir los resultados en `faq_retrievals` cuando exista el paso que genera la respuesta.
- Añadir preguntas con el estilo real de los mensajes de Instagram.
