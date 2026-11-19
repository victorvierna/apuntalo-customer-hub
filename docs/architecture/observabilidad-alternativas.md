# Alternativas de diseño para logs, métricas de salud, reproducibilidad y resiliencia

> **Estado:** estudio para revisión (borrador). No es una decisión: lo que se elija irá a
> `docs/decisions/` cuando se haya discutido.
> **Fecha:** 2026-11-19
> **Alcance:** cómo registra el sistema lo que hace (`modules/logging/`), cómo sabemos si está
> sano, cómo se reproduce una decisión pasada y cómo aguanta los fallos. Cubre todos los
> módulos del núcleo y el adaptador de Instagram. Quedan fuera el diseño del dashboard y la
> retención de datos (RGPD, `database.md` decisión abierta 2), aunque se señala dónde les afecta.

---

## 1. Contexto: qué tenemos ya

Antes de elegir nada conviene ver que **una parte grande del "logging" ya está diseñada**, solo
que como tablas de la base de datos y no como "logs" en el sentido clásico.

| Ya existe | Dónde | Qué cubre |
|---|---|---|
| Registro de cada decisión | `processing_runs`, `routing_decisions`, `model_calls`, `faq_retrievals`, `run_messages` (`database.md` 6.5–6.13) | Qué se decidió, con qué modelo, coste, latencia, FAQ usadas. Solo inserciones. |
| Métricas de negocio del MVP | `database.md` sección 10 | % resuelto por el asistente, coste, derivaciones, latencia de cada fase… |
| Cola con reintentos | `inbound_queue` + `modules/gateway/worker.py` | `attempts`, `MAX_ATTEMPTS = 3`, estado `failed` como "cola de errores". |
| Atomicidad ante caídas | `transaction()` + una transacción por ráfaga | Si el gateway cae a mitad, se deshace todo y se reintenta. |
| Idempotencia | `UNIQUE (channel_account_id, message_external_id)` | Las relecturas del canal no duplican mensajes ni respuestas. |
| Trabajo pendiente que sobrevive a una caída | `processing_runs.finished_at IS NULL` (`shared/db/runs.py`) | Lo aceptado y sin contestar se retoma tras reiniciar. |
| Simulación de umbrales sin re-ejecutar | `routing_decisions.scores` + `threshold` | Reproducción "contrafactual" del enrutador. |
| Reloj inyectable | `run_once(conn, now=...)` | Los tests son deterministas respecto al tiempo. |
| Logs técnicos | `logging.getLogger(__name__)` en `worker.py` y `send_patch.py` | Solo dos sitios, sin configurar (sin formato, destino ni nivel). |

Lo que **falta** es justo lo que no es "una decisión sobre un mensaje":

- **Logs técnicos útiles:** qué hizo cada proceso, con qué error y en qué contexto, en un
  formato que se pueda buscar y relacionar con un `run_id`.
- **Salud del sistema:** ¿está vivo el lector de Instagram? ¿Caducó la sesión? ¿Se está
  atascando la cola? Hoy nada de eso queda registrado ni avisa a nadie.
- **Reproducibilidad completa:** se guarda qué se decidió, pero no **con qué versión** del
  código, del prompt, de la configuración y de las FAQ, ni el texto exacto que vio y devolvió
  el modelo.
- **Resiliencia más allá de la cola:** los reintentos son inmediatos (sin espera), no se
  distingue un error pasajero de uno permanente, no hay protección si un proveedor o
  instagram-cli empiezan a fallar en bucle, y el envío de respuestas aún no está diseñado.

### 1.1 Restricciones que condicionan las alternativas

| Restricción | De dónde sale | Consecuencia |
|---|---|---|
| Primero la librería estándar; toda dependencia se consulta | `0001-python.md`, `AGENTS.md` | Cada alternativa se valora también "sin instalar nada". |
| Una sola máquina, SQLite con un único escritor | `database.md` 2 y 8 | Escribir logs muy frecuentes en la BD compite con el pipeline. |
| Volumen bajo (decenas o cientos de mensajes al día) | Una cuenta secundaria de Instagram | No hace falta infraestructura pensada para millones de eventos. |
| Las conversaciones son datos personales | `AGENTS.md`, `database.md` 12 | Los logs **no** pueden llevar texto de clientes a sitios sin control (archivos sueltos, servicios externos). |
| Canal no oficial (instagram-cli) | `docs/modules/instagram.md` | Reintentar sin freno puede provocar un bloqueo de la cuenta: la resiliencia también es **no insistir**. |
| Núcleo independiente del canal + adaptadores | `AGENTS.md` | La instrumentación debe seguir el mismo patrón: el código llama a una interfaz propia y el "dónde se envía" es intercambiable. |

### 1.2 Vocabulario

Para el TFG conviene separar cuatro cosas que en el día a día se llaman todas "logs":

| Término | Pregunta que responde | Ejemplo aquí |
|---|---|---|
| **Registro de dominio** (auditoría) | ¿Qué decidió el sistema y por qué? | Fila en `processing_runs` con `outcome = 'handed_off'`. |
| **Log técnico** (evento) | ¿Qué hizo el proceso y qué falló? | `instagram-cli timeout tras 30 s leyendo la cuenta 2`. |
| **Métrica** (serie temporal agregada) | ¿Cómo está el sistema ahora y cómo evoluciona? | Edad del mensaje pendiente más antiguo: 14 s. |
| **Traza** | ¿Por dónde pasó **este** mensaje y cuánto tardó cada paso? | Lector → cola → gateway → enrutador → modelo → envío, con tiempos. |

La **observabilidad** es la capacidad de responder preguntas nuevas sobre el sistema a partir
de esas cuatro señales sin tener que cambiar el código. Este documento propone alternativas
para cada una y cómo encajan.

---

## 2. Pilar 1 — Logs técnicos

### 2.1 Requisitos

1. **Estructurados:** cada línea es un objeto (JSON), no una frase. Se puede filtrar por
   campo (`run_id = 42`, `level = ERROR`, `component = poller`).
2. **Correlacionados:** cada línea lleva el contexto en el que ocurre (`run_id`,
   `conversation_id`, cuenta, ciclo del lector) **sin pasarlo a mano** en cada llamada.
3. **Sin datos personales por defecto:** ids internos sí; texto de mensajes, nombres de
   usuario o tokens, no. Si hace falta el texto, se va a la BD por el `run_id`.
4. **Con la versión:** cada línea (o al menos cada arranque) dice qué versión del código
   corre (hash de git).
5. **No pueden tumbar el sistema:** si el destino del log falla (disco lleno), el pipeline
   sigue.

### 2.2 Alternativa L1 — `logging` de la librería estándar + formato JSON propio

`logging` ya se usa. Le falta configuración en un único sitio:

- Un `Formatter` de ~30 líneas que convierte cada `LogRecord` en JSON (`ts`, `level`,
  `logger`, `msg`, `exc`, `version` y los campos de contexto).
- Contexto con `contextvars`: un gestor `with log_context(run_id=42, conversation_id=7):`
  y un `Filter` que añade esos campos a cada registro. Funciona igual con hilos y con
  `asyncio` si algún día se usa.
- Destino: **salida estándar** (en Docker la recoge `docker logs` y cualquier herramienta
  posterior) y, opcionalmente, archivo con `RotatingFileHandler` en `storage/logs/`
  (que git ya ignora).
- `QueueHandler` + `QueueListener` (también estándar) para que escribir el log no bloquee
  el pipeline aunque el disco vaya lento.
- Un filtro de redacción que elimina claves sensibles (`text`, `username`, `token`…).

```json
{"ts":"2026-11-19T10:02:11.402Z","level":"ERROR","logger":"modules.gateway.worker",
 "msg":"gateway failed on burst","run_id":null,"account_id":1,"conversation_external_id":"340282…",
 "attempt":2,"error_type":"OperationalError","version":"bfa2c21"}
```

| A favor | En contra |
|---|---|
| Cero dependencias; ya se usa. | Hay que escribir y testear el formateador y el contexto (poco código). |
| Todas las librerías de terceros ya escriben en `logging`: sus logs salen en el mismo formato. | La API (`logger.info("...", extra={...})`) es algo verbosa. |
| JSON por salida estándar es lo que entienden Loki, Elastic, CloudWatch… si se crece. | Buscar en los archivos es con `grep`/`jq` hasta que haya otra herramienta. |

### 2.3 Alternativa L2 — `structlog`

Librería que hace lo mismo que L1 con una API más cómoda (`log.bind(run_id=42)`,
procesadores encadenados, redacción, salida JSON o en color para desarrollo). Se integra con
`logging`, así que no rompe lo existente.

| A favor | En contra |
|---|---|
| Menos código propio; diseño muy probado. | Primera dependencia del proyecto: obliga a decidir gestor de dependencias (`0001-python.md`, pendiente). |
| Muy buena experiencia en desarrollo (salida legible). | Lo que aporta sobre L1 es comodidad, no capacidad. |

### 2.4 Alternativa L3 — Logs dentro de SQLite (tabla `app_events`)

Guardar también los logs técnicos en la base de datos, junto al registro de dominio.

| A favor | En contra |
|---|---|
| Todo en un sitio; el dashboard los muestra con SQL; se unen por `run_id`. | **Compite por el único escritor de SQLite** con el pipeline (`busy_timeout`). |
| Copia de seguridad única. | Si el fallo es de la propia BD (bloqueada, disco lleno, corrupta), **se pierde justo el log que lo explica**. |
| | Mezcla datos operativos (se borran pronto) con históricos (no se borran). |

**Variante razonable:** solo los eventos importantes y poco frecuentes (arranques, sesión de
Instagram caducada, cambios de estado del *circuit breaker*, alertas) van a una tabla, y el
resto a salida estándar. Esa tabla es en realidad parte de las métricas de salud (sección 3).

### 2.5 Alternativa L4 — OpenTelemetry (logs + trazas + métricas)

OpenTelemetry (OTel) es el estándar abierto de la industria para instrumentar código. El
código usa su API (`tracer.start_as_current_span("gateway.process_burst")`) y un *SDK*
exporta las señales por el protocolo OTLP a un **colector**, que las reparte a donde sea:
Grafana Tempo/Jaeger (trazas), Loki (logs), Prometheus (métricas).

| A favor | En contra |
|---|---|
| Un único modelo para las tres señales y correlación automática (`trace_id` en cada log). | Varias dependencias (`opentelemetry-api`, `-sdk`, exportadores) y **varios contenedores** (colector + backends). |
| Independiente del proveedor: se cambia el destino sin tocar el código. | Mucha infraestructura para el volumen de este proyecto. |
| Muy defendible en un TFG: es lo que se usa en producción hoy. | La API de logs de OTel en Python es la parte menos madura. |
| Tiene convenciones específicas para llamadas a LLM (*GenAI semantic conventions*). | Más superficie que mantener para un equipo de dos personas. |

### 2.6 Una nota sobre trazas

Con un único proceso y un pipeline lineal, buena parte del valor de una traza ya lo da el
esquema: `processing_runs.started_at/finished_at`, `routing_decisions.latency_ms` y
`model_calls.latency_ms` son los "tramos" (*spans*) de cada ejecución. Lo que falta es:

- El tramo **antes** del run (lector → cola: `inbound_queue.enqueued_at − fecha del canal`)
  y **después** (envío de la respuesta).
- Un identificador que siga al mensaje desde que el lector lo lee hasta que se envía la
  respuesta. Propuesta: el `run_id` como identificador de correlación a partir del gateway,
  y antes de él el id de la fila de la cola. Si se adopta OTel, el `trace_id` se guardaría en
  `processing_runs` para saltar de la BD a la traza.

### 2.7 Comparativa de logs técnicos

| Criterio | L1 stdlib JSON | L2 structlog | L3 SQLite | L4 OpenTelemetry |
|---|---|---|---|---|
| Dependencias | Ninguna | 1 | Ninguna | Varias + contenedores |
| Esfuerzo inicial | Bajo | Bajo | Medio | Alto |
| Correlación con `run_id` | Sí (contextvars) | Sí | Sí (SQL) | Sí, automática |
| Riesgo para el pipeline | Muy bajo | Muy bajo | Medio | Bajo |
| Sirve si cae la BD | Sí | Sí | **No** | Sí |
| Valor para el TFG | Medio | Medio | Bajo | Alto |
| Camino de crecimiento | A L4 sin cambiar llamadas si hay fachada propia | A L4 | Difícil | — |

---

## 3. Pilar 2 — Métricas de salud

### 3.1 Qué es "estar sano" en este sistema

Se propone medir con dos marcos clásicos y uno propio:

- **RED** (*Rate, Errors, Duration*) para el pipeline: cuántos mensajes entran, cuántos
  fallan, cuánto tardan.
- **Las cuatro señales doradas** de Google SRE (latencia, tráfico, errores, **saturación**):
  añade la saturación, que aquí es la cola atascada y la BD bloqueada.
- **Invariantes del producto**: reglas que **nunca** deben romperse. Son lo más
  característico de este sistema y lo más interesante para el TFG:
  - Ninguna respuesta enviada sin FAQ que la respalde (`faq_retrievals`).
  - Ningún mensaje contestado dos veces.
  - Ningún mensaje aceptado sin contestar ni derivar pasado cierto tiempo.
  - Nada contestado a una persona bloqueada o en una conversación que lleva un humano.

### 3.2 Indicadores propuestos (SLI) y objetivos de ejemplo (SLO)

Los objetivos son ejemplos para discutir, no decisiones.

| # | Indicador (SLI) | Cómo se calcula | Objetivo de ejemplo (SLO) |
|---|---|---|---|
| S1 | **Frescura**: tiempo desde que el cliente escribe hasta que recibe respuesta o se deriva | fecha del canal del último mensaje de la ráfaga → envío/handoff | 95 % < 2 min (depende del intervalo del lector) |
| S2 | **Éxito del pipeline** | runs con `outcome <> 'failed'` / runs terminados | ≥ 99 % semanal |
| S3 | **Cola sana** | edad del `pending` más antiguo; nº de filas `failed` | < 1 min; 0 `failed` sin revisar |
| S4 | **Runs atascados** | `accepted` con `finished_at IS NULL` y más de N min | 0 |
| S5 | **Lector vivo**, por cuenta | última lectura correcta de instagram-cli | < 3 × intervalo del lector |
| S6 | **Sesión de Instagram válida**, por cuenta | último error `no_session` frente a última lectura correcta | Válida |
| S7 | **Proveedores de modelos** | `model_calls.status` ≠ `ok`, `is_fallback`, p95 de `latency_ms` por modelo | errores < 2 %; p95 < 5 s |
| S8 | **Coste** | `SUM(cost_micros)` del día | < presupuesto diario |
| S9 | **Invariante "nunca inventa"** | respuestas enviadas sin filas en `faq_retrievals` | 0, siempre |
| S10 | **Deriva de calidad** | % de derivaciones por `low_confidence`/`out_of_faq` frente a la media de 7 días | Avisar si sube mucho (FAQ desactualizadas) |
| S11 | **Base de datos** | tamaño del archivo y del WAL, espacio libre en disco, `PRAGMA quick_check` diario | Disco > 20 % libre; `ok` |

Ejemplos de consultas sobre el esquema actual:

```sql
-- S3: edad del mensaje pendiente más antiguo (en segundos)
SELECT (julianday('now') - julianday(MIN(enqueued_at))) * 86400 AS oldest_pending_s
FROM inbound_queue WHERE status = 'pending';

-- S4: runs aceptados sin terminar desde hace más de 10 minutos
SELECT COUNT(*) FROM processing_runs
WHERE gateway_result = 'accepted' AND finished_at IS NULL
  AND started_at < strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-10 minutes');

-- S9: respuestas del asistente sin FAQ que las respalden (debe ser 0)
SELECT COUNT(*) FROM processing_runs r
WHERE r.outcome = 'replied' AND r.action = 'answer'
  AND NOT EXISTS (SELECT 1 FROM faq_retrievals f WHERE f.run_id = r.id);
```

Algunas señales **no salen del esquema actual** (S5, S6, S11 y la parte de envío de S1):
hay que empezar a registrarlas.

### 3.3 Alternativa M1 — Métricas calculadas con SQL al vuelo

Las consultas de 3.2 se guardan como vistas (`CREATE VIEW health_…`) o funciones en
`shared/db/`, y el dashboard y un comando de diagnóstico las ejecutan cuando se piden.

| A favor | En contra |
|---|---|
| Cero infraestructura; una única fuente de verdad. | Solo hay "ahora": no hay histórico de cosas que no se guardan (p. ej. cómo estaba la cola ayer a las 10). |
| Encaja con lo existente (`database.md` sección 10). | No avisa a nadie: alguien tiene que mirar. |
| Fácil de testear con `unittest` y una BD temporal. | Lo que no está en la BD (lector vivo, disco) no se ve. |

### 3.4 Alternativa M2 — M1 + latidos + muestras periódicas + vigilante, todo en SQLite

Amplía M1 con tres piezas pequeñas y sin dependencias:

1. **Latidos (`component_heartbeats`):** cada componente (lector por cuenta, gateway,
   enrutador, envío) actualiza su fila al terminar cada ciclo: `last_seen_at`,
   `last_ok_at`, `last_error`, `consecutive_failures`. Es estado operativo, no histórico,
   así que **sí se actualiza** (excepción explícita a "el logging solo recibe inserciones").
   Resuelve S5 y S6.
2. **Muestras (`health_samples`):** un proceso vigilante evalúa cada minuto las métricas de
   3.2 y guarda una fila por métrica (`metric`, `labels`, `value`, `sampled_at`). Da
   histórico barato (≈1 500 filas al día por métrica; se compactan o borran pasados N días).
3. **Vigilante + alertas (`alerts`):** el mismo proceso compara con los umbrales y abre o
   cierra alertas (`firing` → `resolved`) para no repetir el aviso. Notifica por correo
   (`smtplib`) o por un bot de Telegram/Slack (`urllib`), ambos en la librería estándar.
   El dashboard muestra un semáforo (ok / degradado / caído).

Además, un endpoint `GET /healthz` (vivo) y `GET /readyz` (listo: BD accesible, sesión válida)
para que Docker reinicie el contenedor si se cuelga (ver 5.6). Se puede servir con
`http.server` o con el framework del dashboard cuando se elija.

| A favor | En contra |
|---|---|
| Sin dependencias; cubre detección **y** aviso. | Reimplementa en pequeño lo que hace Prometheus + Alertmanager. |
| Histórico consultable con SQL, junto a los datos de dominio. | El vigilante comparte la BD: si la BD está caída, no puede avisar (necesita un aviso "último recurso" fuera de la BD, p. ej. un `try/except` que manda el correo). |
| Muy explicable en un TFG: se diseña cada pieza. | Las gráficas hay que hacerlas en el dashboard. |

### 3.5 Alternativa M3 — Prometheus + Grafana + Alertmanager

La aplicación expone `GET /metrics` en el formato de texto de Prometheus. Prometheus lo lee
cada X segundos, guarda las series, Grafana las dibuja y Alertmanager avisa.

- El formato es texto simple: se puede generar **a mano** desde las consultas SQL (patrón
  "exportador SQL") sin la librería `prometheus_client`, o usar esa librería para
  histogramas de latencia en memoria.
- Se añaden tres contenedores al `docker/`.

| A favor | En contra |
|---|---|
| Estándar de facto; Grafana da gráficas y alertas listas, incluidas alertas por **ritmo de consumo del presupuesto de error** (*burn rate*) de los SLO. | 3 servicios más que configurar, actualizar y asegurar. |
| Histórico y percentiles sin escribir nada en SQLite. | Las métricas de dominio siguen saliendo de SQLite: hay dos sitios donde mirar. |
| Mucho material de referencia para la memoria del TFG. | Para el volumen de mensajes, es infraestructura sobredimensionada. |

### 3.6 Alternativa M4 — OpenTelemetry Metrics

Igual que M3 pero instrumentando con OTel (ver L4) y exportando al colector, que a su vez
alimenta Prometheus. Solo tiene sentido si se elige L4 para logs y trazas.

### 3.7 Comparativa de métricas de salud

| Criterio | M1 SQL | M2 SQL + vigilante | M3 Prometheus | M4 OTel |
|---|---|---|---|---|
| Dependencias / servicios | 0 / 0 | 0 / 0 | 0–1 / 3 | Varias / 4+ |
| Histórico | No | Sí (SQLite) | Sí | Sí |
| Alertas | No | Sí (propias) | Sí (Alertmanager) | Sí |
| Ve el lector y el disco | No | Sí | Sí | Sí |
| Funciona si cae la BD | No | Parcial | Sí | Sí |
| Esfuerzo | Bajo | Medio | Medio-alto | Alto |
| Valor para el TFG | Bajo | Alto (diseño propio) | Alto (estándar) | Alto |

---

## 4. Pilar 3 — Reproducibilidad

### 4.1 Qué significa reproducir aquí

Hay que distinguir tres niveles, porque con modelos de IA no son lo mismo:

| Nivel | Pregunta | ¿Es posible? |
|---|---|---|
| **R-a. Explicar** | ¿Qué vio y qué hizo el sistema en el run 42? | Sí, si se guardan entradas, versiones y salidas. |
| **R-b. Re-ejecutar de forma determinista** | Si vuelvo a pasar el run 42 por el código, con las respuestas del modelo **grabadas**, ¿sale lo mismo? | Sí, si todo lo no determinista (reloj, modelo, aleatoriedad) se graba e inyecta. |
| **R-c. Repetir con el modelo** | Si vuelvo a preguntar al modelo, ¿contesta lo mismo? | **No garantizado**: incluso con temperatura 0 los proveedores no son deterministas. Se **mide** (tasa de acuerdo), no se asume. |

La consecuencia de diseño es clara: **la reproducibilidad se consigue grabando, no
recalculando**. Todo lo que no sea determinista se guarda en el momento.

### 4.2 Qué falta hoy para cada nivel

| Hace falta | ¿Está? | Hueco |
|---|---|---|
| Mensajes de entrada exactos | Sí (`run_messages` → `messages`) | — |
| Historial que vio el enrutador | Parcial | `RouteRequest.history` (últimos 6) se reconstruye de `messages`, pero si se editan o borran mensajes después, cambia. |
| Versión del código | No | Ningún registro dice qué commit corría. |
| Configuración vigente (umbrales, ventana de ráfaga, `MAX_ATTEMPTS`, modelos) | Parcial | Solo `routing_decisions.threshold` y `router_version`. |
| Versión de las FAQ | No | `faq_retrievals.faq_ref` apunta a una FAQ que puede haber cambiado. |
| Prompt exacto y parámetros del modelo (temperatura, semilla, `max_tokens`) | No | `model_calls` guarda tokens y coste, no el contenido. |
| Salida cruda del modelo | Parcial | Solo la respuesta **enviada** (`reply_message_id`). Las bloqueadas por el gateway de salida se pierden. |
| Reloj | Sí en el gateway (`now` inyectable) | Mantener la convención en el resto de módulos. |

### 4.3 Alternativa P1 — Sellado de versiones

Añadir a cada run (y a cada `model_call`) las versiones con las que se ejecutó:

- `code_version`: hash de git (se lee al arrancar o se inyecta en la imagen de Docker).
- `config_hash`: hash de la configuración efectiva (umbrales, ventana, modelos…), con la
  configuración completa guardada **una vez** por hash en una tabla `config_snapshots`.
- `faq_version`: hash del contenido de `data/faqs/` (o el commit que la modificó por última vez).
- `prompt_version` en `model_calls` (como ya hace `router_version`).

| A favor | En contra |
|---|---|
| Muy barato (unas columnas y una tabla pequeña); sin datos personales nuevos. | Explica (R-a) pero no permite re-ejecutar (R-b) sin el contenido del modelo. |
| Permite comparar métricas **entre versiones** (antes/después de cambiar un prompt). | Requiere cambio de esquema (versión 5). |

### 4.4 Alternativa P2 — P1 + grabación de entradas/salidas de los modelos

Guardar el *prompt* completo, los parámetros y la respuesta cruda de cada llamada, en una
tabla aparte (`model_call_payloads`) o en archivos comprimidos en `storage/`, enlazados por
`model_call_id`. Las partes repetidas (prompt de sistema, FAQ) se guardan una vez por hash
(*content-addressed*) para no multiplicar el tamaño.

Con esto se puede construir un **arnés de repetición** (*replay*):

```
python -m tools.replay --run 42             # R-b: modelo grabado → debe salir idéntico
python -m tools.replay --run 42 --live      # R-c: modelo real → compara y mide acuerdo
python -m tools.replay --since 2026-11-01 --threshold 0.6   # contrafactual en lote
```

(Los comandos son ilustrativos; no existen.) Es el patrón "grabar y reproducir" de los
tests con *cassettes*: los runs de producción, anonimizados, se convierten en **casos de
regresión**. Cada cambio de prompt, umbral o FAQ se evalúa contra ellos antes de mergear.

| A favor | En contra |
|---|---|
| Habilita R-b y R-c; convierte producción en un banco de pruebas. | Guarda **texto de clientes** dentro del prompt: necesita política de retención y anonimización (decisión abierta 2 de `database.md`). |
| Permite depurar respuestas bloqueadas que hoy se pierden. | Más volumen en la BD (bajo para este tráfico, pero crece). |
| Muy buen material experimental para el TFG. | Hay que diseñar el arnés: inyectar cliente de modelo y reloj en todos los módulos. |

### 4.5 Alternativa P3 — *Event sourcing* (diario de eventos)

Cada paso emite un evento inmutable a una tabla `events` (`MessageEnqueued`,
`BurstAccepted`, `RouteDecided`, `FaqRetrieved`, `ReplySent`…) y el estado (conversaciones,
runs) se **deriva** de los eventos. La reproducción es literal: re-aplicar el diario.

| A favor | En contra |
|---|---|
| Reproducibilidad total y auditoría perfecta. | **Duplica** lo que ya hacen las tablas de dominio (que son, en la práctica, un diario parcial). |
| Muy interesante académicamente. | Rediseño profundo del acceso a datos ya implementado (gateway, cola). |
| | Complejidad (versionado de eventos, proyecciones) desproporcionada para el MVP. |

### 4.6 Alternativa P4 — Herramientas de observabilidad de LLM (Langfuse, Phoenix…)

Plataformas que registran prompts, respuestas, costes y evaluaciones de cada llamada a un
modelo, con interfaz para explorarlas y conjuntos de datos para evaluar.

| A favor | En contra |
|---|---|
| Interfaz lista para ver cada llamada, versionar prompts y lanzar evaluaciones. | Autoalojarlas pide varios servicios (p. ej. Langfuse usa PostgreSQL y ClickHouse). En la nube, **los mensajes de clientes salen a un tercero**. |
| | Solapa con `model_calls`, que ya existe. |

### 4.7 Comparativa de reproducibilidad

| Criterio | P1 versiones | P2 + grabación | P3 event sourcing | P4 herramienta LLM |
|---|---|---|---|---|
| R-a explicar | Sí | Sí | Sí | Sí (solo modelos) |
| R-b re-ejecutar determinista | No | **Sí** | Sí | No |
| R-c medir repetibilidad del modelo | No | **Sí** | Sí | Parcial |
| Datos personales nuevos | No | Sí | Sí | Sí (y fuera) |
| Esfuerzo | Bajo | Medio | Muy alto | Medio + infraestructura |
| Encaja con lo existente | Sí | Sí | No | Parcial |

---

## 5. Pilar 4 — Resiliencia ante fallos

### 5.1 Catálogo de fallos

Para el TFG conviene partir de un catálogo explícito (*análisis de modos de fallo*) y
decir, para cada uno, cómo se **detecta**, cómo se **contiene** y cómo se **recupera**.

| # | Fallo | Probabilidad | Hoy | Propuesta |
|---|---|---|---|---|
| F1 | Caída del proceso a mitad de ráfaga | Media | ✅ Transacción única, se reintenta | Mantener; añadir prueba de inyección de fallos |
| F2 | Caída tras enviar la respuesta y antes de registrarla | Baja | ❌ Envío no diseñado | Bandeja de salida + reconciliación (5.5) |
| F3 | instagram-cli: timeout o error pasajero | Alta | Parcial (timeout del subproceso) | Reintento con espera exponencial + *circuit breaker* |
| F4 | Sesión de Instagram caducada | Media | Error tipado (`error_no_session`) | No reintentar; alerta inmediata; parar el lector de esa cuenta |
| F5 | Bloqueo o límite de Instagram por insistir | Media | ❌ | *Circuit breaker* + límite de ritmo por cuenta |
| F6 | Proveedor del modelo caído, lento o con error | Alta | Diseñado (`status`, `is_fallback`) | Timeouts + *fallback* SLM → LLM → **derivar a Bárbara** |
| F7 | Mensaje "venenoso" (dato que siempre rompe el código) | Baja | Tras 3 intentos → `failed` | Clasificar errores: permanentes van a `failed` al primer intento |
| F8 | BD ocupada (`SQLITE_BUSY`) | Media | `busy_timeout = 5000` | Tratar como error pasajero (reintento con espera) |
| F9 | Disco lleno / BD corrupta | Baja | ❌ | Métrica S11 + copias periódicas + `quick_check` |
| F10 | Presupuesto de modelos agotado o gasto anómalo | Baja | ❌ | Métrica S8 + corte automático (todo pasa a derivar) |
| F11 | Proceso vivo pero colgado (bucle, bloqueo) | Baja | ❌ | Latidos (M2) + `healthcheck` de Docker que lo reinicia |

### 5.2 Principio rector: degradación segura

La regla de producto da el criterio de resiliencia: **ante la duda, derivar a una persona;
nunca inventar y nunca callar.** En cada fallo, el sistema baja un escalón en vez de caer:

```
respuesta con SLM ─fallo─> respuesta con LLM ─fallo─> plantilla + derivar a Bárbara ─fallo─> queda pendiente y alerta
```

El último escalón ("queda pendiente") ya existe gracias a `finished_at IS NULL`. Lo que se
mide (S1, S2, S4) es cuántas veces se baja cada escalón.

### 5.3 Reintentos: hoy y alternativas

Hoy un fallo suma un intento y la ráfaga sigue `pending`: **se reintenta en la siguiente
vuelta del bucle**, sin espera. Si el fallo es pasajero pero dura más que tres vueltas, el
mensaje acaba en `failed` aunque se habría recuperado.

| Alternativa | Qué cambia | Comentario |
|---|---|---|
| **Espera exponencial con *jitter*** | Columna `next_attempt_at` en `inbound_queue`; la consulta de conversaciones listas la respeta. | Estándar; evita martillear un recurso caído. |
| **Clasificar errores** | Excepciones del código propio marcadas como `TransientError` / `PermanentError`. Las permanentes van directas a `failed`. | Evita gastar intentos en mensajes venenosos (F7). |
| **Reprocesar desde el dashboard** | Acción "reintentar" que devuelve filas `failed` a `pending` con `attempts = 0`. | La cola de errores sirve de poco si nadie puede vaciarla. |
| Librería de reintentos (`tenacity`) | Decoradores listos. | Dependencia para algo que son ~20 líneas propias. |

### 5.4 *Circuit breaker* para dependencias externas

Si instagram-cli o un proveedor fallan N veces seguidas, se **abre el circuito**: durante un
tiempo no se les llama (se deriva o se espera) y después se prueba una sola llamada
(*half-open*). El estado se guarda en `component_heartbeats` (M2) para que sobreviva a un
reinicio y el dashboard lo muestre. En Instagram, además de proteger el sistema, **protege la
cuenta** de un bloqueo por insistencia (F5).

### 5.5 El envío: el punto más delicado

Enviar una respuesta es el único efecto que **no se puede deshacer** y Instagram no ofrece
una clave de idempotencia. Si el proceso cae entre "enviado" y "registrado", al reiniciar no
se sabe si el cliente la recibió:

| Estrategia | Riesgo | Cuándo |
|---|---|---|
| *At-most-once* (registrar "enviando" antes, no reintentar si quedó a medias) | El cliente se queda sin respuesta | — |
| *At-least-once* (reintentar si no consta) | El cliente recibe **dos** respuestas | — |
| **Bandeja de salida + reconciliación** | Mínimo | Recomendado |

La tercera es el patrón *transactional outbox*: la respuesta se escribe en una tabla
`outbound_queue` dentro de la misma transacción que cierra el run; un emisor la envía y la
marca `sent`. Si al reiniciar hay una fila "enviando" sin confirmar, el emisor **lee el hilo**
en Instagram (como ya hace `read_after_send` en los tests del adaptador) para comprobar si
el mensaje está antes de reenviar. `database.md` 6.14 ya anticipa este diseño.

### 5.6 Supervisión de procesos

- **Docker:** `restart: unless-stopped` + `HEALTHCHECK` que llama a `/healthz` o comprueba el
  latido. Si el proceso está colgado (F11), Docker lo reinicia.
- **Arranque seguro:** al iniciar, el proceso registra versión y configuración (P1), revisa
  runs abiertos y filas "enviando", y solo entonces empieza a leer.
- **Copias de seguridad de la BD (F9):** `VACUUM INTO` programado (estándar, ya documentado
  en `database.md` 12) o Litestream (replica SQLite continuamente a otro disco o a S3; es un
  binario aparte, no una librería de Python).

### 5.7 Cómo demostrar que es resiliente: inyección de fallos

La resiliencia no se afirma, se prueba. Propuesta de batería de tests (`unittest`, sin
dependencias) que inyecta cada fallo del catálogo y comprueba las **invariantes** de 3.1:

| Experimento | Inyección | Se comprueba |
|---|---|---|
| Caída a mitad de ráfaga | Excepción en un paso del pipeline | Nada guardado a medias; se reintenta; una sola respuesta |
| Caída entre envío y registro | Excepción tras `send` | Tras reiniciar, no hay doble envío |
| CLI intermitente | Fallos con probabilidad p | Ningún mensaje perdido; el circuito se abre y se cierra |
| Sesión caducada | Fixture `error_no_session.json` | Alerta abierta en < 1 ciclo; sin reintentos en bucle |
| Proveedor caído | Cliente de modelo que siempre falla | Todo acaba derivado; S9 sigue en 0 |
| BD ocupada | Otra conexión con `BEGIN IMMEDIATE` | Reintento con espera; sin `failed` espurios |

Métricas del experimento, útiles para la memoria: **tiempo hasta detectar** (MTTD), **tiempo
hasta recuperar** (MTTR), % de fallos detectados por las alertas, mensajes perdidos o
duplicados (deben ser 0) y **sobrecoste** de la instrumentación (latencia y tamaño de la BD).

---

## 6. Lo que comparten todas las alternativas

### 6.1 Una fachada propia en `modules/logging/`

Igual que el núcleo no habla con Instagram sino con un adaptador, el código no debería
llamar directamente a `logging`, a `structlog` ni a OpenTelemetry, sino a una interfaz
mínima propia:

```python
from modules.logging import log, span, metric

with span("gateway.process_burst", run_id=run_id):     # contexto + duración
    log.info("burst accepted", messages=len(burst))     # evento estructurado
    metric.increment("gateway_bursts_total", result="accepted")
```

La primera implementación escribe JSON por salida estándar (L1) y latidos/muestras en
SQLite (M2). Si más adelante se adopta OpenTelemetry, se cambia **la implementación de la
fachada**, no las llamadas repartidas por los módulos. Es el mismo argumento de arquitectura
que el del canal, y se defiende bien en el TFG.

> **Ojo con el nombre:** un paquete propio llamado `logging` puede tapar el `logging` de la
> librería estándar si algún script se ejecuta con `modules/` como directorio del script
> (`sys.path[0]`). Con imports absolutos desde la raíz (`python -m …`) no pasa, pero conviene
> tenerlo en cuenta o valorar otro nombre (p. ej. `modules/observability/`). Cambiar la
> estructura de carpetas requiere acordarlo antes (`AGENTS.md`).

### 6.2 Separar datos personales de datos técnicos

| Destino | Puede llevar texto de clientes | Retención |
|---|---|---|
| Tablas de dominio (SQLite) | Sí | Política RGPD (pendiente) |
| Grafana leyendo SQLite (sección 8) | Sí; aceptado de momento (*backoffice* de una sola persona) | La de las tablas de dominio |
| Grabaciones de modelos (P2) | Sí | Igual o más corta; candidatas a anonimizar |
| Logs técnicos (stdout/archivos) | **No** (redacción por defecto) | Corta (p. ej. 14 días, rotación) |
| Métricas y alertas | **No** | Larga (son agregados) |

### 6.3 Inyección de lo no determinista

Mantener en todos los módulos la convención del gateway: el reloj (`now`), el cliente del
modelo y cualquier aleatoriedad se **pasan** como parámetro. Es lo que hace posibles los
tests de 5.7 y el arnés de 4.4.

---

## 7. Recomendación preliminar

Una propuesta por fases que empieza sin dependencias y deja abierto el camino al estándar:

| Fase | Qué | Alternativas | Dependencias |
|---|---|---|---|
| **1. Base** | Fachada en `modules/logging/`; logs JSON con contexto y redacción por salida estándar; sellado de versiones; clasificación de errores y espera exponencial en la cola | L1 + P1 + 5.3 | Ninguna |
| **2. Salud** | Latidos, muestras periódicas, vigilante con alertas (correo/Telegram), `/healthz`, semáforo en el dashboard; SLI de 3.2 como vistas SQL | M2 | Ninguna |
| **3. Resiliencia** | *Circuit breaker* para instagram-cli y modelos; bandeja de salida con reconciliación; supervisión en Docker; copias de la BD; batería de inyección de fallos | 5.4–5.7 | Ninguna |
| **4. Reproducibilidad** | Grabación de entradas/salidas de modelos con retención; arnés de repetición; casos de regresión desde producción | P2 | Ninguna |
| **5. Estándar (opcional)** | Cambiar la implementación de la fachada a OpenTelemetry y añadir colector + Grafana (Prometheus/Loki/Tempo) en `docker/`. Comparar con la fase 2 como experimento del TFG. Plan detallado en la sección 8 | L4 + M4 | Varias (consultar) |

Por qué este orden:

- **Las fases 1–4 no necesitan dependencias** y cubren los tres objetivos (salud,
  reproducibilidad, resiliencia) con un diseño propio que se puede explicar pieza a pieza.
- **La fase 5 convierte la elección en un experimento:** "observabilidad a medida sobre
  SQLite" frente a "pila estándar OpenTelemetry", comparadas por esfuerzo, sobrecoste,
  tiempo de detección y capacidad de diagnóstico. Eso da al TFG una evaluación cuantitativa
  en vez de una simple elección.
- **Event sourcing (P3) y las herramientas de LLM externas (P4) se descartan** para el MVP:
  la primera duplica lo que ya existe y la segunda saca datos de clientes o añade mucha
  infraestructura. Se pueden citar en la memoria como alternativas valoradas.

### 7.1 Cambios de esquema que implicaría (versión 5, a discutir)

- `processing_runs`: `code_version`, `config_hash`, `faq_version`.
- `model_calls`: `prompt_version`, parámetros (`temperature`, `seed` si el proveedor lo admite).
- Nuevas: `config_snapshots`, `component_heartbeats`, `health_samples`, `alerts`;
  `model_call_payloads` (fase 4); `outbound_queue` (con el envío).
- `inbound_queue`: `next_attempt_at`.

---

## 8. Plan de implementación de la pila Grafana (camino hacia OpenTelemetry)

Si se aprueba usar contenedores extra (decisión abierta 1), esta es la forma de montar
Grafana + Prometheus + Loki sobre lo que ya hay, **con la misma forma que tendrá con
OpenTelemetry**, para que la migración (fase 5) cambie solo cómo salen las señales de la app.

### 8.1 Arquitectura antes de OTel

```
                ┌────────────── App (Python, solo librería estándar) ──────────────┐
                │  modules/logging/  (fachada: log, metric, span)                   │
                │     │                     │                                       │
                │  logs JSON → stdout    GET /metrics (formato texto Prometheus)    │
                └─────┼─────────────────────┼───────────────────────────────────────┘
                      │                     │                       storage/*.db
                Docker (logs)               │                            │
                ┌─────▼─────┐         ┌─────▼──────┐                     │
                │  Alloy    │         │ Prometheus │  (métricas)         │
                │ (colector)│         └─────┬──────┘                     │
                └─────┬─────┘               │                            │
                      ▼                     ▼                            ▼
                 ┌────────┐           ┌──────────────────────────────────────┐
                 │  Loki  │ ────────> │ Grafana: paneles + alertas           │
                 └────────┘  (logs)   │ fuentes: Prometheus, Loki, SQLite    │
                                      └──────────────────────────────────────┘
```

| Señal | Herramienta | Pregunta que responde |
|---|---|---|
| Métricas de salud (series temporales) | Prometheus | ¿Cómo está el sistema y cómo evoluciona? Cola, latencias, errores, lector vivo. |
| Logs técnicos | Loki | ¿Qué pasó en el run 42? ¿Por qué falló el lector? |
| Datos de negocio | SQLite, con el plugin `frser-sqlite-datasource` de Grafana | Coste por modelo, motivos de derivación, % resuelto (`database.md` sección 10). |
| Trazas (después) | Tempo | Por dónde pasó un mensaje y cuánto tardó cada paso. |

**Por qué Alloy y no Promtail:** Promtail (el recolector clásico de Loki) está obsoleto y sin
soporte; su sustituto es Grafana Alloy, que además es la distribución de Grafana del
**colector de OpenTelemetry**. Usarlo desde el principio hace que pasar a OTel sea activar un
receptor OTLP en su configuración, sin añadir ni quitar contenedores.

### 8.2 Pasos

1. **Instrumentar la app (sin dependencias).**
   - Fachada `modules/logging/` (6.1): todo el código la usa; nadie llama a una librería
     directamente.
   - Logs JSON por salida estándar con `logging` + formateador propio + contexto en
     `contextvars` (`run_id`, `conversation_id`, `component`). Docker los recoge.
   - `GET /metrics` con `http.server`, con dos tipos de métricas:
     - **En memoria** (contadores e histogramas): ráfagas por resultado, latencia de cada
       llamada a un modelo, fallos de instagram-cli.
     - **Calculadas con SQL en cada lectura** (patrón "exportador SQL"): edad del pendiente
       más antiguo, runs atascados, filas `failed`, coste del día. Así S3, S4 y S8 salen de la
       BD sin guardar nada nuevo.
   - El formato de texto de Prometheus se genera a mano sin problema; lo único laborioso
     son los histogramas (buckets acumulados, `_sum` y `_count`).
   - Comprobación manual: `curl` al endpoint y `docker logs … | jq`.
2. **Prometheus + Grafana en `docker/`.**
   - Prometheus lee `/metrics` cada 15–30 s.
   - **Todo como código, versionado en git:** `prometheus.yml`, fuentes de datos, paneles y
     alertas de Grafana por *provisioning*, nunca configurados a mano en la interfaz.
     Cualquiera reproduce el entorno con un comando.
   - Estructura orientativa (cambiar carpetas se acuerda antes, `AGENTS.md`):
     ```
     docker/observability/
       prometheus/prometheus.yml, rules/*.yml
       alloy/config.alloy
       loki/config.yml
       grafana/provisioning/{datasources,dashboards,alerting}/
       grafana/dashboards/*.json
     ```
3. **Alloy + Loki para los logs.**
   - Alloy lee los logs de los contenedores (`loki.source.docker`) y los envía a Loki.
   - **Etiquetas pocas y fijas** (`service`, `component`, `level`). **Nunca** `run_id` ni
     otros ids como etiqueta: cada valor distinto crea una serie y Loki (igual que
     Prometheus) se degrada. Los ids van dentro del JSON y se filtran al consultar:
     `{service="apuntalo-core"} | json | run_id = "42"`.
   - Retención corta (p. ej. 14 días).
4. **SQLite como fuente de Grafana (datos de negocio).**
   - El plugin abre `storage/apuntalo-marketing-platform.db` en solo lectura.
   - **Ojo con WAL:** aunque solo lea, necesita poder escribir el archivo `-shm`; montar el
     volumen como solo lectura puede fallar. Hay que probarlo.
   - Reparto: lo que cambia minuto a minuto (salud) en Prometheus; el histórico y el
     análisis (negocio) en SQLite. No se duplica nada.
   - **Datos de clientes en Grafana:** con esta fuente, Grafana puede leer conversaciones.
     **De momento no es un problema**: es una herramienta de *backoffice* administrada por
     una sola persona y los datos no los manejan varias personas. Si eso cambia (más
     usuarios, acceso externo), conviene que los paneles consulten solo **vistas agregadas**
     (`v_cost_daily`, `v_handoff_reasons`…) y revisarlo junto con la decisión de RGPD
     (`database.md`, decisión abierta 2).
5. **Paneles** (JSON versionado):
   1. **Salud:** RED + saturación de la cola; semáforo por componente (lector por cuenta,
      gateway, modelos, envío).
   2. **Negocio:** coste, % resuelto, derivaciones, acuerdo clasificador/árbitro.
   3. **Depuración de un run:** variable `run_id` → sus filas de SQLite y sus logs de Loki
     en la misma pantalla (con un enlace desde el campo `run_id`).
6. **Alertas y SLO.**
   - Grafana Alerting (ahorra el contenedor de Alertmanager) o reglas de Prometheus;
     en ambos casos, reglas como archivos en git.
   - Alertar por síntomas: sesión caducada, lector parado, runs atascados, invariante S9
     distinta de 0, coste sobre presupuesto.
   - SLO con alertas por **ritmo de consumo del presupuesto de error** (*multi-window
     burn rate*, libro de SRE de Google).
7. **Validar con inyección de fallos** (5.7) con la pila levantada: para cada fallo, tiempo
   hasta que salta la alerta (MTTD) y si el panel permite ver la causa.

### 8.3 Preparar hoy la migración a OTel

| Decisión de ahora | Por qué ayuda luego |
|---|---|
| Fachada propia en `modules/logging/` | Se cambia su implementación, no las llamadas de los módulos. |
| **Nombres de métricas y atributos según las convenciones semánticas de OTel**, incluidas las de GenAI (`gen_ai.client.operation.duration`, `gen_ai.client.token.usage`, `gen_ai.request.model`…) | Los paneles y alertas siguen funcionando tras migrar (OTel traduce `gen_ai.client.token.usage` a `gen_ai_client_token_usage_total` al exportar a Prometheus). |
| Atributos de recurso: `service.name`, `service.version` (hash de git), `deployment.environment` | Son los que OTel añade a cada señal; hoy van como etiquetas o campos del JSON. |
| Alloy como colector desde el principio | El receptor OTLP se activa en su configuración. |
| `span(...)` en la fachada aunque al principio solo mida duración y escriba un log | Cuando haya trazas, cada `span` ya marcado pasa a ser un tramo real. |
| Columna `trace_id` reservada en `processing_runs` (esquema v5) | Saltar de una fila de la BD a su traza en Tempo. |

### 8.4 Migración a OTel (fase 5)

```
App ──OTLP──> Alloy ──┬──> Prometheus  (receptor OTLP nativo desde la v3)
                      ├──> Loki        (ingesta OTLP nativa desde la v3)
                      └──> Tempo       (nuevo: trazas)
```

1. Añadir `opentelemetry-api`, `opentelemetry-sdk` y el exportador OTLP (consultar antes,
   `0001-python.md`; obliga a elegir gestor de dependencias).
2. Cambiar la implementación de la fachada: `metric` → `Meter`, `span` → `Tracer`, `log`
   sigue en `logging` + `LoggingHandler` de OTel (cada log lleva `trace_id` solo).
3. Activar `otelcol.receiver.otlp` en Alloy y enviar cada señal a su destino.
4. **Ejecutar las dos vías en paralelo** (`/metrics` + stdout frente a OTLP), comparar los
   mismos paneles y medir el sobrecoste: es el experimento "a medida frente a estándar" de
   la sección 7.
5. Aprovechar lo nuevo: correlación automática log ↔ traza y *exemplars* (de un pico de
   latencia a la traza concreta que lo causó).
6. Retirar `/metrics` y la recogida de stdout cuando esté validado.

### 8.5 Consideraciones

- No hay dependencias de Python hasta la migración a OTel, pero sí **cuatro contenedores
  nuevos** (Grafana, Prometheus, Loki, Alloy): es una decisión de stack (decisión abierta 1).
- A este volumen la pila cabe en un servidor pequeño; conviene medir el consumo real de
  memoria antes de dimensionar la máquina.
- Grafana **nunca expuesto a internet sin autenticación**.

---

## 9. Decisiones abiertas

1. **¿Se permiten dependencias o contenedores extra para la observabilidad?** Condiciona
   L2/L4 y M3/M4 y el plan de la sección 8. Si no, todo se queda en las fases 1–4.
2. **¿Dónde se despliega?** (un VPS, una máquina de la oficina…). Afecta a si los logs van
   solo a salida estándar o también a archivos, y a cómo se hacen las copias de la BD.
3. **Canal de alertas y destinatario:** correo, Telegram, Slack… ¿A quién avisa: al equipo
   técnico, a Bárbara o a ambos, y para qué alertas?
4. **Objetivos (SLO) concretos** de la tabla 3.2, en especial la frescura (S1), que depende
   del intervalo del lector (`gateway.md`, decisión abierta 1).
5. **¿Se graban los prompts y respuestas completos (P2)?** Y con qué retención y
   anonimización. Va ligado a la decisión abierta 2 de `database.md` (RGPD).
6. **Nombre del módulo:** mantener `modules/logging/` o renombrarlo (ver 6.1).
7. **Foco del TFG:** si el peso está en salud, en reproducibilidad o en resiliencia, para
   decidir qué fase se evalúa con más profundidad y con qué experimentos.
