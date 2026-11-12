# Arquitectura de la base de datos

> **Estado:** propuesta para revisión (borrador)
> **Fecha:** 2026-11-11
> **Motor:** SQLite
> **Alcance:** esquema de datos del núcleo (conversaciones, procesamiento, logging y derivación a Bárbara)

---

## 1. Contexto

La plataforma recibe mensajes de clientes (o no clientes) por la cuenta secundaria de
Instagram de Apúntalo y decide si el asistente puede responder con información de las FAQ
o si debe derivar a una persona (Bárbara). El flujo, según el diagrama C2
(`docs/architecture/c2.png`), es:

```
Instagram → Gateway (filtra) → Enrutador (decide) → Modelo + RAG (responde)
                                         └──→ si no puede: Consulta a Bárbara
                                                     └──→ ¿Añadir al RAG?
```

La base de datos tiene que dar soporte a tres necesidades:

1. **El dashboard** (`modules/platform/`): bandeja de conversaciones y gestión de derivaciones.
2. **El logging** (`modules/logging/`): registrar cada mensaje, respuesta, modelo, coste y
   derivación para depurar y medir el MVP.
3. **La derivación** (`modules/handoff/`): saber qué conversaciones esperan a una persona,
   quién las atiende y qué se decide con el conocimiento nuevo.

## 2. Por qué SQLite

- **Sin servidor:** la base de datos es un único archivo. No hay que desplegar, mantener ni
  asegurar un servicio aparte.
- **Fiable:** las transacciones ACID garantizan un estado consistente aunque el proceso se
  caiga en mitad de una escritura.
- **Independiente del stack:** todos los lenguajes tienen driver, así que no condiciona la
  elección de tecnología, que sigue pendiente.

**Cuándo habría que migrar a PostgreSQL:** si hay varios servidores escribiendo a la vez,
mucha concurrencia de escrituras sostenida o necesidad de acceder a la BD por red desde
otros servicios. Para que esa migración sea sencilla, usaremos SQL lo más estándar posible
y concentraremos el acceso a datos en un único sitio del código.

## 3. Principios de diseño

| Principio | Qué significa en el esquema |
|---|---|
| **Núcleo independiente del canal** | Ninguna tabla tiene columnas propias de Instagram. Cada entidad externa se identifica con `channel` + `external_id`. Añadir otro canal (p. ej. WhatsApp) no obliga a cambiar el esquema. |
| **Tres capas separadas** | (1) Conversación: lo que ve el dashboard. (2) Procesamiento: cómo decidió el sistema. (3) Intervención humana. Así la bandeja queda limpia y el logging se puede consultar por separado. |
| **Trazabilidad de "nunca inventa"** | Cada respuesta del asistente se puede rastrear hasta las FAQ que la justificaron y el modelo que la generó. |
| **El logging solo recibe inserciones** | Las tablas de procesamiento y los resúmenes de tickets no se actualizan ni se borran: son un histórico fiable para las métricas. |
| **Idempotencia** | Si el canal reenvía un mismo mensaje (con instagram-cli el adaptador consulta el canal cada cierto tiempo y vuelve a leer mensajes que ya tenemos), no se procesa ni se responde dos veces. |
| **Tablas `STRICT`** | SQLite permite por defecto guardar cualquier tipo en cualquier columna. Con `STRICT` se rechazan los tipos incorrectos y se evitan datos corruptos silenciosos. |
| **`CHECK` en los estados** | Los campos con un conjunto cerrado de valores (estados, tipos) se validan en la propia BD, no solo en el código. |

## 4. Convenciones generales

- **Claves primarias:** `id INTEGER PRIMARY KEY` en todas las tablas. En SQLite es el
  identificador interno de fila (`rowid`), así que es lo más eficiente y es autoincremental.
- **Fechas:** `TEXT` en ISO-8601 y siempre en UTC (`2026-11-10T14:30:00Z`). SQLite no tiene
  un tipo fecha. ISO-8601 se lee a simple vista al depurar, se ordena bien como texto y lo
  entienden las funciones de fecha de SQLite. La conversión a hora local se hace solo al
  mostrarla en el dashboard.
- **Booleanos:** `INTEGER` con valores `0` / `1` (SQLite no tiene tipo booleano).
- **Dinero:** `INTEGER` en millonésimas de dólar (*micros*). Sumar números en coma flotante
  (`REAL`) acumula errores de redondeo, y el coste por llamada a un modelo suele ser una
  fracción muy pequeña de céntimo.
- **Nombres:** tablas y columnas en inglés y en `snake_case`, igual que el código y los commits.
- **`created_at` en todas las tablas:** permite auditar cuándo apareció cada dato y
  ordenar cronológicamente.

## 5. Diagrama de entidades

```
channel_accounts ─┐
                  ├──< conversations ──< messages
contacts ─────────┘         │                │ (cada mensaje entrante)
                            │                └──< processing_runs ──< model_calls
                            │                            └──────────< faq_retrievals
                            ├──< conversation_summaries >── model_calls (el que generó el resumen)
                            └──< handoffs >── users (OPCIONAL, pendiente de revisión)

──<  = relación uno a muchos
```

## 6. Tablas y justificación de cada campo

### 6.1 `channel_accounts` — cuentas propias que gestionamos

Instagram-cli controla varias cuentas. Aunque el MVP use solo la secundaria, guardar a qué
cuenta llegó cada conversación evita tener que rehacer el esquema cuando se añadan más.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `channel` | TEXT | Canal de la cuenta (`'instagram'`). Mantiene el núcleo genérico. |
| `external_id` | TEXT | Id de la cuenta en el canal. Lo necesita el adaptador para saber en nombre de qué cuenta responder. |
| `handle` | TEXT | Nombre visible (p. ej. `@apuntalo_ayuda`) para que el dashboard muestre en qué cuenta entró cada conversación. |
| `created_at` | TEXT | Auditoría. |

`UNIQUE (channel, external_id)` impide registrar dos veces la misma cuenta.

### 6.2 `contacts` — la persona que nos escribe

Se separa de la conversación porque la misma persona puede abrir varias conversaciones a lo
largo del tiempo, y conviene ver su historial completo.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `channel` | TEXT | Canal por el que nos contacta. |
| `external_id` | TEXT | Id del usuario en el canal. Es lo que devuelve el adaptador del canal y se usa para encontrar al contacto existente. En Instagram es el `userId` numérico, no el nombre de usuario, porque el nombre puede cambiar. |
| `display_name` | TEXT, opcional | Nombre que mostrar en la bandeja. Puede faltar si el canal no lo da. |
| `is_customer` | INTEGER, opcional | El diagrama distingue "cliente o no cliente". `1` = cliente, `0` = no cliente, `NULL` = no se sabe todavía. Usar `NULL` evita afirmar algo que no sabemos. |
| `is_blocked` | INTEGER (booleano), por defecto `0` | `1` si el contacto está bloqueado por alguna de nuestras cuentas. El dashboard lo señala para que nadie intente responderle, y el asistente no debe enviarle mensajes. A diferencia de `is_customer`, aquí siempre sabemos el valor (por defecto no está bloqueado), así que es `NOT NULL`. Solo indica *si* está bloqueado, no *por qué cuenta* (ver decisiones abiertas). |
| `created_at` | TEXT | Primera vez que nos escribió. |

`UNIQUE (channel, external_id)`: una persona en un canal es un único contacto.

### 6.3 `conversations` — un hilo de mensajes

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `channel_account_id` | FK → `channel_accounts` | En qué cuenta nuestra entró la conversación, y por tanto desde cuál hay que responder. |
| `contact_id` | FK → `contacts` | Con quién hablamos. |
| `status` | TEXT + CHECK | **Quién lleva ahora la conversación:** `bot` (responde el asistente), `waiting_human` (derivada, el bot **no** debe contestar) o `closed`. Es el campo clave para la bandeja de Bárbara y para que el gateway sepa si puede dejar responder al asistente. |
| `external_id` | TEXT | Id de la conversación en el canal (en Instagram, el id del hilo). Lo necesita el adaptador para leer y enviar mensajes en esa conversación, y para saber si una conversación del canal ya existe en la BD. |
| `last_message_at` | TEXT | Ordenar la bandeja por actividad reciente sin tener que calcular el último mensaje de cada conversación en cada consulta. Es un dato redundante a propósito, por rendimiento. |
| `created_at` | TEXT | Cuándo empezó la conversación. |

`UNIQUE (channel_account_id, external_id)`: una conversación del canal es una única fila,
aunque el adaptador la lea muchas veces.

### 6.4 `messages` — cada mensaje, en ambas direcciones

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `conversation_id` | FK → `conversations` | Conversación a la que pertenece. |
| `direction` | TEXT + CHECK | `in` (nos llega) / `out` (enviamos). Permite filtrar los entrantes, que son los que disparan el procesamiento. |
| `author` | TEXT + CHECK | `contact`, `assistant` o `human`. Distingue si una respuesta saliente la escribió el bot o una persona. Es imprescindible para medir cuánto resuelve el asistente por sí solo. |
| `author_user_id` | FK → `users`, opcional | Qué persona del equipo respondió, si `author = 'human'`. |
| `content_type` | TEXT + CHECK | `text`, `image` (foto), `video`, `audio` (nota de voz), `reaction` (p. ej. un ❤️ enviado como mensaje) o `unsupported` (publicación compartida, reel, enlace…: contenido que el canal no nos deja leer). Qué se hace con cada tipo lo decide `modules/handoff/policy.py`: hoy el asistente solo intenta responder a `text`, `reaction` solo se guarda y el resto se deriva con `reason = 'unsupported_content'`. Separar foto, vídeo y audio permite cambiar esa regla cuando haya modelos que lean imágenes o transcriban audio. |
| `body` | TEXT, opcional | Texto del mensaje. Obligatorio si `content_type = 'text'` (lo garantiza un `CHECK`). En `reaction` es el emoji. En `unsupported` guarda la descripción que da el canal (p. ej. `[Unsupported Type: xma_media_share]`) para que Bárbara sepa qué tipo de mensaje era. Falta en `image`, `video` y `audio`. |
| `media_path` | TEXT, opcional | Ruta del archivo descargado, relativa a `storage/` (p. ej. `media/<id>.jpg`). Contiene datos de clientes: nunca va a git. |
| `external_id` | TEXT, opcional | Id del mensaje en el canal. Sirve para detectar duplicados y para referenciarlo al responder. Es opcional porque un mensaje saliente no lo tiene hasta que el canal confirma el envío. |
| `delivery_status` | TEXT, opcional | Para salientes: `sent` / `failed`. Si el canal rechaza el envío, el dashboard puede avisar y permitir reintentar. |
| `created_at` | TEXT | Orden cronológico del hilo. En los mensajes del canal es la fecha que da el canal (`timestamp`), no la hora a la que los guardamos; así el orden es correcto aunque el adaptador los lea con retraso. |

`UNIQUE (conversation_id, external_id)`: **idempotencia**. El adaptador de Instagram lee las
conversaciones recientes cada cierto tiempo y recibe otra vez mensajes que ya guardó; la
inserción falla y el mensaje no se procesa ni se contesta dos veces. Por eso el adaptador no
necesita fiarse de los campos "no leído" o "última actividad" del canal, que no son fiables
(por ejemplo, una solicitud de mensaje aceptada en la app llega como leída).

### 6.5 `processing_runs` — decisión del Gateway y del Enrutador

Una fila por cada mensaje entrante procesado. Se separa de `messages` porque describe
**cómo** decidió el sistema, no **qué** se dijo, y porque un mismo mensaje podría
reprocesarse (por ejemplo, tras un error).

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `message_id` | FK → `messages` | Mensaje entrante que se procesó. |
| `gateway_result` | TEXT + CHECK | Resultado del gateway: `accepted`, `blocked_injection`, `rate_limited`, `timeout` o `error`. El diagrama asigna al gateway evitar *prompt injection* y gestionar *timeouts* y *rate limits*. Este campo permite medir con qué frecuencia ocurre cada caso. |
| `intent` | TEXT + CHECK, opcional | Clasificación de la entrada según el diagrama: `faq`, `request` (petición) u `out_of_faq` (fuera de FAQ). Es opcional porque si el gateway bloquea el mensaje, no llega a clasificarse. |
| `action` | TEXT + CHECK, opcional | Salida decidida: `answer` (responder duda), `request` (realizar petición), `deny` (denegar servicio) o `handoff` (consultar a Bárbara). Es la base de la métrica principal: % de mensajes que resuelve el asistente. |
| `reply_message_id` | FK → `messages`, opcional | Respuesta que se envió como resultado, si la hubo. Une la pregunta con su respuesta para depurar. |
| `error` | TEXT, opcional | Detalle técnico si algo falló, para depurar sin tener que buscar en otros logs. |
| `started_at` | TEXT | Inicio del procesamiento. |
| `finished_at` | TEXT, opcional | Fin del procesamiento. La diferencia con `started_at` da el tiempo de respuesta de extremo a extremo. Vacío = el proceso no terminó (posible caída). |

### 6.6 `model_calls` — cada llamada a un modelo de IA

Un procesamiento puede implicar varias llamadas (p. ej. una del router para decidir y otra
del modelo que responde), así que van en una tabla propia. Aquí también se registra la
llamada que genera el resumen al cerrar un ticket (ver 6.10), para que **todo** el gasto en
modelos esté en una sola tabla.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `run_id` | FK → `processing_runs`, opcional | Procesamiento al que pertenece. Solo puede faltar en los resúmenes, que no responden a un mensaje entrante sino al cierre de un ticket. Un `CHECK` obliga a rellenarlo en cualquier otro caso. |
| `purpose` | TEXT + CHECK | Para qué se llamó: `routing`, `answer` o `summary`. Permite separar el coste de decidir, el de responder y el de resumir. |
| `provider` | TEXT | Proveedor del modelo. El router puede escoger entre varios. |
| `model` | TEXT | Modelo concreto. Permite comparar calidad y coste entre modelos, que es justo lo que tiene que optimizar el router. |
| `input_tokens` | INTEGER, opcional | Tokens de entrada. Es la base del coste y sirve para detectar prompts demasiado grandes. |
| `output_tokens` | INTEGER, opcional | Tokens de salida. |
| `cost_micros` | INTEGER, opcional | Coste en millonésimas de dólar. Se guarda calculado en el momento porque los precios de los modelos cambian, y así el histórico refleja lo que costó de verdad. |
| `latency_ms` | INTEGER, opcional | Tiempo que tardó el modelo. Ayuda a detectar el origen de respuestas lentas y a configurar *timeouts*. |
| `created_at` | TEXT | Momento de la llamada; permite agregar costes por día o por semana. |

### 6.7 `faq_retrievals` — qué FAQ devolvió el RAG

Es la **prueba de que el asistente no inventa**: cada respuesta queda ligada a las FAQ en las
que se basó. Si un procesamiento no tiene filas aquí, el RAG no encontró información, y lo
correcto es que haya acabado en `handoff`.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `run_id` | FK → `processing_runs` | Procesamiento al que pertenece la búsqueda. |
| `faq_ref` | TEXT | Referencia a la FAQ dentro de `data/faqs/` (ruta o identificador). Es texto y no una FK porque las FAQ viven como archivos versionados, no en la BD. |
| `score` | REAL, opcional | Relevancia devuelta por el buscador. Permite ajustar a partir de qué umbral se considera que "hay información". |
| `rank` | INTEGER | Posición en los resultados (1 = más relevante). |

### 6.8 `users` — personas del equipo que usan el dashboard ⚠️ OPCIONAL / PENDIENTE DE REVISIÓN

> **Pendiente de revisión:** todavía no sabemos si esta tabla será necesaria. Se mantiene en
> la propuesta, pero no se debe dar por cerrada. Mientras solo atienda Bárbara y no haya
> login en el dashboard, se puede aplazar. Si se descarta, también desaparecen las columnas
> que dependen de ella: `messages.author_user_id` y `handoffs.assigned_user_id`.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `name` | TEXT | Nombre que mostrar (p. ej. "Bárbara"). |
| `email` | TEXT UNIQUE | Identifica de forma única a la persona y sirve como base si más adelante se añade login o se notifican derivaciones por correo. |
| `created_at` | TEXT | Auditoría. |

Si el dashboard acaba teniendo autenticación propia, esta tabla necesitará más campos
(rol, credenciales gestionadas por el sistema de autenticación, etc.).

### 6.9 `handoffs` — consulta a Bárbara y decisión sobre el RAG

Representa la parte verde del diagrama: consulta a Bárbara → respuesta → ¿añadir al RAG?

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `conversation_id` | FK → `conversations` | Conversación derivada. |
| `run_id` | FK → `processing_runs`, opcional | Procesamiento que provocó la derivación, para entender por qué el bot no pudo responder. Es opcional porque una persona puede tomar la conversación manualmente desde el dashboard. |
| `reason` | TEXT | Motivo: `out_of_faq`, `request`, `low_confidence`, `unsupported_content` (audio, foto, publicación… que el asistente no puede leer) o `manual`. Saber por qué se deriva indica qué FAQ faltan o qué hay que mejorar. |
| `status` | TEXT + CHECK | `pending` → `answered` → `closed`. Es la bandeja de trabajo de Bárbara. |
| `assigned_user_id` | FK → `users`, opcional | Quién la atiende. Hoy es Bárbara, pero así no queda fijado en el esquema. |
| `answer_message_id` | FK → `messages`, opcional | Mensaje con el que se respondió al cliente. Une la derivación con su resolución. |
| `kb_decision` | TEXT + CHECK, opcional | Respuesta a "¿añadir al RAG?": `add` o `skip`. `NULL` = sin decidir todavía. Permite listar las respuestas pendientes de convertir en FAQ. |
| `created_at` | TEXT | Momento de la derivación. |
| `answered_at` | TEXT, opcional | Momento de la respuesta. `answered_at − created_at` = tiempo de respuesta humana, una métrica clave del MVP. |
| `closed_at` | TEXT, opcional | Cierre de la derivación. |

### 6.10 `conversation_summaries` — resumen de cada ticket cerrado

Cuando una conversación (ticket) se cierra, es decir, cuando `conversations.status` pasa a
`closed`, un modelo genera un resumen del ticket y se guarda aquí como un log. Sirve para que
el equipo entienda un caso de un vistazo sin leer todo el hilo, para tener contexto si el
contacto vuelve a escribir y para revisar en bloque qué tipo de consultas llegan.

Como el resto de logs, **solo recibe inserciones**. Si una conversación se reabre y se vuelve
a cerrar, se genera un resumen nuevo y el anterior se conserva. Por eso es una tabla aparte y
no una columna en `conversations`: una columna se sobrescribiría y perderíamos el histórico.

| Campo | Tipo | Por qué existe |
|---|---|---|
| `id` | INTEGER PK | Identificador interno. |
| `conversation_id` | FK → `conversations` | Ticket resumido. Una conversación puede tener varios resúmenes si se reabre. |
| `last_message_id` | FK → `messages` | Último mensaje incluido en el resumen. Marca hasta dónde llega: si el ticket se reabre, el siguiente resumen sabe desde qué mensaje empezar, y se puede comprobar qué vio exactamente el modelo. |
| `summary` | TEXT | Texto del resumen. |
| `model_call_id` | FK → `model_calls` | Llamada al modelo que generó el resumen. Así el modelo, los tokens, el coste y la latencia quedan registrados en el mismo sitio que el resto de llamadas, sin duplicar esas columnas aquí. |
| `created_at` | TEXT | Momento en que se generó el resumen, que coincide con el cierre del ticket. |

## 7. Índices

| Índice | Para qué consulta |
|---|---|
| `messages(conversation_id, created_at)` | Mostrar el hilo de una conversación en orden. |
| `conversations(status, last_message_at)` | Bandeja del dashboard filtrada por estado y ordenada por actividad. |
| `handoffs(status, created_at)` | Derivaciones pendientes, de la más antigua a la más reciente. |
| `processing_runs(message_id)` | Ir de un mensaje a cómo se procesó. |
| `model_calls(run_id)` | Ir de un procesamiento a sus llamadas y su coste. |
| `conversation_summaries(conversation_id, created_at)` | Ver los resúmenes de un ticket en orden. |

No se añaden más índices hasta que una consulta real lo necesite: cada índice ralentiza las escrituras.

## 8. Configuración de SQLite

Se aplica en cada conexión:

```sql
PRAGMA journal_mode = WAL;    -- permite leer mientras se escribe (dashboard + procesamiento a la vez)
PRAGMA foreign_keys = ON;     -- SQLite NO valida las claves foráneas por defecto
PRAGMA busy_timeout = 5000;   -- esperar hasta 5 s si hay otra escritura, en vez de fallar al momento
```

## 9. Esquema completo (DDL)

```sql
CREATE TABLE channel_accounts (
  id           INTEGER PRIMARY KEY,
  channel      TEXT NOT NULL,
  external_id  TEXT NOT NULL,
  handle       TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  UNIQUE (channel, external_id)
) STRICT;

CREATE TABLE contacts (
  id            INTEGER PRIMARY KEY,
  channel       TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  display_name  TEXT,
  is_customer   INTEGER CHECK (is_customer IN (0, 1)),
  is_blocked    INTEGER NOT NULL DEFAULT 0 CHECK (is_blocked IN (0, 1)),
  created_at    TEXT NOT NULL,
  UNIQUE (channel, external_id)
) STRICT;

-- OPCIONAL / PENDIENTE DE REVISIÓN: puede que no sea necesaria (ver 6.8)
CREATE TABLE users (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  created_at  TEXT NOT NULL
) STRICT;

CREATE TABLE conversations (
  id                  INTEGER PRIMARY KEY,
  channel_account_id  INTEGER NOT NULL REFERENCES channel_accounts(id),
  contact_id          INTEGER NOT NULL REFERENCES contacts(id),
  status              TEXT NOT NULL DEFAULT 'bot'
                      CHECK (status IN ('bot', 'waiting_human', 'closed')),
  external_id         TEXT NOT NULL,
  last_message_at     TEXT NOT NULL,
  created_at          TEXT NOT NULL,
  UNIQUE (channel_account_id, external_id)
) STRICT;

CREATE TABLE messages (
  id               INTEGER PRIMARY KEY,
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
  direction        TEXT NOT NULL CHECK (direction IN ('in', 'out')),
  author           TEXT NOT NULL CHECK (author IN ('contact', 'assistant', 'human')),
  author_user_id   INTEGER REFERENCES users(id),
  content_type     TEXT NOT NULL DEFAULT 'text'
                   CHECK (content_type IN ('text', 'image', 'video', 'audio',
                                          'reaction', 'unsupported')),
  body             TEXT,
  media_path       TEXT,
  external_id      TEXT,
  delivery_status  TEXT CHECK (delivery_status IN ('sent', 'failed')),
  created_at       TEXT NOT NULL,
  UNIQUE (conversation_id, external_id),
  CHECK (content_type <> 'text' OR body IS NOT NULL)
) STRICT;

CREATE TABLE processing_runs (
  id                INTEGER PRIMARY KEY,
  message_id        INTEGER NOT NULL REFERENCES messages(id),
  gateway_result    TEXT NOT NULL
                    CHECK (gateway_result IN ('accepted', 'blocked_injection', 'rate_limited', 'timeout', 'error')),
  intent            TEXT CHECK (intent IN ('faq', 'request', 'out_of_faq')),
  action            TEXT CHECK (action IN ('answer', 'request', 'deny', 'handoff')),
  reply_message_id  INTEGER REFERENCES messages(id),
  error             TEXT,
  started_at        TEXT NOT NULL,
  finished_at       TEXT
) STRICT;

CREATE TABLE model_calls (
  id             INTEGER PRIMARY KEY,
  run_id         INTEGER REFERENCES processing_runs(id),
  purpose        TEXT NOT NULL CHECK (purpose IN ('routing', 'answer', 'summary')),
  provider       TEXT NOT NULL,
  model          TEXT NOT NULL,
  input_tokens   INTEGER,
  output_tokens  INTEGER,
  cost_micros    INTEGER,
  latency_ms     INTEGER,
  created_at     TEXT NOT NULL,
  CHECK (run_id IS NOT NULL OR purpose = 'summary')
) STRICT;

CREATE TABLE conversation_summaries (
  id               INTEGER PRIMARY KEY,
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
  last_message_id  INTEGER NOT NULL REFERENCES messages(id),
  summary          TEXT NOT NULL,
  model_call_id    INTEGER NOT NULL REFERENCES model_calls(id),
  created_at       TEXT NOT NULL
) STRICT;

CREATE TABLE faq_retrievals (
  id       INTEGER PRIMARY KEY,
  run_id   INTEGER NOT NULL REFERENCES processing_runs(id),
  faq_ref  TEXT NOT NULL,
  score    REAL,
  rank     INTEGER NOT NULL
) STRICT;

CREATE TABLE handoffs (
  id                 INTEGER PRIMARY KEY,
  conversation_id    INTEGER NOT NULL REFERENCES conversations(id),
  run_id             INTEGER REFERENCES processing_runs(id),
  reason             TEXT NOT NULL
                     CHECK (reason IN ('out_of_faq', 'request', 'low_confidence',
                                       'unsupported_content', 'manual')),
  status             TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'answered', 'closed')),
  assigned_user_id   INTEGER REFERENCES users(id),
  answer_message_id  INTEGER REFERENCES messages(id),
  kb_decision        TEXT CHECK (kb_decision IN ('add', 'skip')),
  created_at         TEXT NOT NULL,
  answered_at        TEXT,
  closed_at          TEXT
) STRICT;

CREATE INDEX idx_messages_conv       ON messages(conversation_id, created_at);
CREATE INDEX idx_conversations_inbox ON conversations(status, last_message_at);
CREATE INDEX idx_handoffs_status     ON handoffs(status, created_at);
CREATE INDEX idx_runs_message        ON processing_runs(message_id);
CREATE INDEX idx_model_calls_run     ON model_calls(run_id);
CREATE INDEX idx_summaries_conv      ON conversation_summaries(conversation_id, created_at);
```

## 10. Métricas del MVP que salen directamente del esquema

| Métrica | De dónde sale |
|---|---|
| % de mensajes resueltos por el asistente | `processing_runs` con `action = 'answer'` / total |
| % de derivaciones y motivo | `handoffs.reason`, agrupado |
| Coste por día y por modelo | `SUM(model_calls.cost_micros)` agrupado por fecha y `model` |
| Tiempo de respuesta del bot | `processing_runs.finished_at − started_at` |
| Tiempo de respuesta de Bárbara | `handoffs.answered_at − created_at` |
| Intentos de *prompt injection* bloqueados | `processing_runs` con `gateway_result = 'blocked_injection'` |
| Conocimiento pendiente de añadir a las FAQ | `handoffs` con `kb_decision = 'add'` |

## 11. Versión mínima para el primer sprint

Si se quiere empezar con menos tablas:

- **Imprescindibles:** `contacts`, `conversations`, `messages`, `processing_runs`,
  `model_calls`, `handoffs`, `faq_retrievals`, `conversation_summaries`.
- **Aplazables:** `channel_accounts` (mientras solo haya una cuenta). Se añade más adelante
  con una migración.
- **Opcional / pendiente de revisión:** `users`. No está decidido si será necesaria (ver 6.8).

`faq_retrievals` se mantiene desde el principio porque es la evidencia de que cada respuesta
se basa en una FAQ.

## 12. Operación

- **Ubicación (decidido el 2026-11-11):**
  - El archivo de la base de datos es `storage/apuntalo-marketing-platform.db`. El nombre es
    largo a propósito, para no confundirlo con otras bases de datos de Apúntalo.
  - La ruta se puede cambiar con la variable de entorno `DATABASE_PATH` (por ejemplo, en
    `env/`). Las rutas relativas se resuelven desde la raíz del repositorio.
  - El script que crea el esquema es `shared/db/init_db.py`. Va en `shared/` porque la base
    de datos la usan varios módulos (`logging`, `handoff`, `platform`…). Se ejecuta con
    `python shared/db/init_db.py`, solo usa la librería estándar de Python y se puede
    ejecutar varias veces sin problema: guarda la versión del esquema en
    `PRAGMA user_version` y solo lo aplica una vez.
- **El archivo `.db` contiene conversaciones reales de clientes.** Nunca va a git:
  `.gitignore` excluye `storage/` y los archivos `*.db`, `*.db-wal` y `*.db-shm`. Tampoco
  puede ir en `data/faqs/`.
- **Copias de seguridad:** nunca copiar el archivo mientras la app escribe. Usar
  `sqlite3 storage/apuntalo-marketing-platform.db ".backup copia.db"` o `VACUUM INTO 'copia.db'`.
- **Docker:** `storage/` debe montarse como volumen persistente, y no en un sistema de archivos
  de red (NFS/SMB), donde el bloqueo de archivos de SQLite no es fiable.
- **Migraciones:** el esquema se versiona desde el primer día, con la herramienta del stack
  que se elija o con `PRAGMA user_version` y scripts numerados. `ALTER TABLE` en SQLite es
  limitado y algunos cambios obligan a recrear la tabla, así que es importante tenerlo
  controlado.

## 13. Decisiones abiertas

1. **¿Qué ocurre cuando Bárbara decide "Sí, añadir al RAG"?**
   - *Opción A (recomendada para el MVP):* la BD solo registra la decisión (`kb_decision = 'add'`)
     y alguien incorpora la FAQ a `data/faqs/` mediante una PR. Hay una única fuente de verdad,
     versionada y revisada.
   - *Opción B:* las FAQ pasan a vivir en la base de datos. Es más inmediato, pero se pierde
     la revisión por PR.
2. **Retención de datos (RGPD):** cuánto tiempo se guardan los mensajes y si se anonimizan
   pasado un tiempo. Los resúmenes de tickets también contienen datos personales y deben
   seguir la misma política.
3. **¿Hace falta la tabla `users`?** Está marcada como opcional. Depende de si el dashboard
   tendrá login y de si atenderá más gente aparte de Bárbara.
4. ~~**Ubicación en el repositorio**~~ **✅ Decidido (2026-11-11):** base de datos en
   `storage/apuntalo-marketing-platform.db` y código en `shared/db/`. Ver sección 12.
   Ya está reflejado en `AGENTS.md`.
5. **Clasificación cliente / no cliente:** cómo se rellena `contacts.is_customer` (¿se
   pregunta, se cruza con otra fuente, lo marca Bárbara?).
6. **Bloqueos por cuenta:** `contacts.is_blocked` indica si el contacto está bloqueado por
   *alguna* de nuestras cuentas, pero no por cuál. Si hace falta saberlo (por ejemplo, si
   está bloqueado en una cuenta y no en otra), habría que añadir una tabla intermedia
   contacto–cuenta. También hay que decidir quién lo marca: el adaptador del canal
   automáticamente o una persona desde el dashboard.
