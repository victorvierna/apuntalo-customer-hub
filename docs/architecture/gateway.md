# Arquitectura del gateway (`modules/gateway/`)

> **Estado:** primera versión implementada en `modules/gateway/` (sin lector ni enrutador).
> **Fecha:** 2026-11-16 (actualizado el 2026-11-17 con el código)
> **Depende de:** esquema v4 de la base de datos (`people`, `contacts`, `blocks`,
> `inbound_queue`, `run_messages`, `routing_decisions`), ver `docs/architecture/database.md`.
> **Alcance:** qué hace el gateway, en qué orden y qué guarda. No cubre el enrutador, el RAG
> ni el envío de respuestas.

---

## 1. Contexto

El gateway es la **entrada única al núcleo**. Todo mensaje que lee un adaptador de canal pasa
por él antes de llegar al enrutador. Según el diagrama C2 (`docs/architecture/c2.png`):

```
Cliente ─MD─> instagram-cli ─> Adaptador de Instagram ─> GATEWAY ─> Enrutador ─> Modelo + RAG
                               modules/channels/          modules/      │
                               instagram/                 gateway/      └─> Handoff (Bárbara)
                                                              │
                                                              └─> Log (processing_runs)
```

**Qué hace:** decide si un mensaje puede seguir hacia el asistente. Es un control barato, sin
modelos de IA, que va antes de gastar dinero en el enrutador. Sus dos primeras
comprobaciones son:

1. **¿La persona que escribe está bloqueada?** En cualquier canal o en cualquiera de nuestras
   cuentas. Si lo está, no se le contesta.
2. **¿Es la primera vez que nos escribe?** Distinguiendo si es una persona nueva o una
   persona conocida que escribe desde otra cuenta o canal (y de la que hay contexto previo).

Además guarda el mensaje sin duplicados, respeta las conversaciones que ya lleva una persona
y aplica la política de tipos de contenido. Más adelante tendrá también lo que el C2 le
asigna: *prompt injection*, *rate limits* y *timeouts*.

**Qué no hace:**
- No responde ni clasifica la intención del mensaje (eso es del enrutador).
- No habla con Instagram: solo recibe tipos de `shared/types/`, así que no sabe de qué canal
  viene el mensaje. Es la regla de AGENTS.md: núcleo independiente del canal.
- No sincroniza los bloqueos de Instagram (eso lo hace el adaptador, ver 6.3).

## 2. Entrada y salida

### Cómo llegan los mensajes: una cola en la base de datos

El adaptador de Instagram no recibe avisos de mensajes nuevos: hay que leer las
conversaciones recientes cada cierto tiempo. **Decidido (2026-11-16):** el gateway se conecta
con instagram-cli a través de un script que se ejecuta cada cierto tiempo y de una cola
guardada en la base de datos:

```
instagram-cli ──> Lector de Instagram ──encola──> inbound_queue ──lee──> Gateway (worker)
                  modules/channels/instagram/     (SQLite)               modules/gateway/
                  (cada N segundos, por cuenta)
```

- **Lector** (específico de Instagram, así que vive en `modules/channels/instagram/`): cada
  cierto tiempo, por cada cuenta, llama a `list_conversations()` y `read_messages()` y
  escribe cada mensaje en la cola, ya traducido a los tipos comunes de `shared/types/`. No
  decide nada ni toca `contacts`, `conversations` ni `messages`.
- **Gateway** (independiente del canal): cada cierto tiempo lee de la cola los mensajes
  pendientes y los pasa por sus comprobaciones (sección 4).

**Por qué una cola y no llamar al gateway directamente:**
- **Separa los ritmos.** Cada comando de instagram-cli tarda unos 5–6 s. El lector puede ir
  despacio sin frenar al gateway, y si el gateway falla los mensajes siguen en la cola.
- **No se pierde nada si algo se cae.** Un mensaje pasa a "hecho" solo cuando el gateway
  termina. Si el proceso se cae a medias, se vuelve a intentar.
- **Sirve para cualquier canal.** Otro canal solo necesita su propio lector que escriba en la
  misma cola.
- **SQLite basta.** No hace falta instalar un sistema de colas aparte (Redis, RabbitMQ…), y
  la cola queda en el mismo archivo que el resto de datos, con las mismas copias de seguridad.

La tabla está en el esquema v4 (`database.md`, 6.14):

```sql
CREATE TABLE inbound_queue (
  id                        INTEGER PRIMARY KEY,
  channel_account_id        INTEGER NOT NULL REFERENCES channel_accounts(id),
  conversation_external_id  TEXT NOT NULL,
  message_external_id       TEXT NOT NULL,
  is_backfill               INTEGER NOT NULL DEFAULT 0 CHECK (is_backfill IN (0, 1)),
  payload                   TEXT NOT NULL CHECK (json_valid(payload)),  -- ChannelConversation + ChannelMessage
  status                    TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'processing', 'done', 'failed')),
  attempts                  INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  error                     TEXT,
  enqueued_at               TEXT NOT NULL,
  started_at                TEXT,
  finished_at               TEXT,
  UNIQUE (channel_account_id, message_external_id),
  CHECK (status = 'pending' OR started_at IS NOT NULL),
  CHECK (status NOT IN ('done', 'failed') OR finished_at IS NOT NULL)
) STRICT;
```

Respecto a la primera propuesta, tiene tres columnas más. Las tres resuelven problemas que
aparecían al combinar la cola con las ráfagas y con la primera sincronización:

| Columna | Problema que resuelve |
|---|---|
| `conversation_external_id` | Agrupar por conversación los mensajes que llegan seguidos (ráfagas, ver más abajo) con un índice, sin abrir el JSON. |
| `message_external_id` + `UNIQUE` | El lector relee las conversaciones recientes en cada pasada. Con el `UNIQUE`, encolar un mensaje que ya está es `INSERT … ON CONFLICT DO NOTHING` y no crea fila. Sin esto, cada relectura parecería un mensaje nuevo, la ráfaga nunca llegaría a los segundos de silencio que espera el gateway y la cola crecería sin control. Por eso el lector ya no necesita guardar hasta qué mensaje leyó. |
| `is_backfill` | En la primera sincronización, todos los mensajes antiguos son nuevos para la base de datos y el asistente los contestaría. El lector los marca como historial: el gateway los guarda, pero no los contesta. |

- **Ráfagas.** En Instagram es habitual escribir una consulta en varios mensajes seguidos
  ("hola" / "una duda" / "¿cuánto cuesta?"). El gateway no coge mensajes sueltos, sino **todos
  los `pending` de una conversación** cuando esa conversación lleva unos segundos sin mensajes
  nuevos (propuesta: 8 s, contados con `enqueued_at`). Así se contesta una sola vez.
- **Cada ráfaga se procesa en una sola transacción** (`BEGIN IMMEDIATE`): leer sus filas,
  guardar los mensajes, decidir, crear el procesamiento y marcar las filas como `done`. Como
  dentro no se llama a ningún modelo ni a Instagram, es muy corta. `BEGIN IMMEDIATE` coge el
  bloqueo de escritura al empezar, así dos procesos del gateway nunca procesan la misma ráfaga.
- **Por qué así (y no marcando primero la ráfaga como `processing`):** si el gateway se cae a
  mitad, la base de datos deshace todo y las filas siguen `pending`, con sus mensajes sin
  guardar. Al reintentar, los mensajes se ven como nuevos y se contestan. Con el estado
  intermedio `processing`, un reintento encontraba los mensajes ya guardados, los tomaba por
  relecturas y el cliente se quedaba sin respuesta. Por eso el gateway no usa `processing` (el
  valor sigue en el `CHECK` del esquema, sin uso).
- **Lo que queda por contestar no depende de la cola.** Una ráfaga aceptada deja un
  procesamiento abierto (`processing_runs.finished_at` vacío) en la misma transacción en la
  que se marca `done`. Si el sistema se cae mientras se piensa o se envía la respuesta, al
  reiniciar se retoma desde esos procesamientos abiertos (`shared/db/runs.py`,
  `unfinished_accepted_runs`).
- Si una ráfaga falla (p. ej. un `payload` mal formado), no se guarda nada y sus filas suman un
  intento (`attempts`). Tras 3 intentos pasan a `failed` y el dashboard las muestra. Un fallo
  no frena las ráfagas de otras conversaciones.
- **Las respuestas** pueden seguir el mismo patrón en sentido contrario (una cola de salida
  que un script envía con instagram-cli). Se diseñará con el envío de respuestas.

### Entrada del gateway: una ráfaga de la cola

El gateway recibe uno o varios elementos de la cola de la misma conversación. Cada uno trae lo
necesario para situar su mensaje:

| Dato | De dónde sale | Para qué lo usa el gateway |
|---|---|---|
| Cuenta propia | `inbound_queue.channel_account_id` (la cuenta de instagram-cli que leyó el mensaje) | Saber en qué cuenta entró y desde cuál responder. |
| `ChannelConversation` | `adapter.list_conversations()` | El `external_id` de la conversación y el **nombre de usuario** del contacto (`participants`). El nombre de usuario que da `read` suele ser genérico (`User_<id>`), así que el bueno es este. |
| `ChannelMessage` | `adapter.read_messages()` | El mensaje: `external_id`, `sender_external_id` (el `userId` numérico), `direction`, `content_type`, `body`, `created_at`. |
| Historial | `inbound_queue.is_backfill` | Si es `1`, se guarda pero no se contesta. |

### Salida: una decisión

| `gateway_result` | Qué significa | Qué pasa después (`outcome`) |
|---|---|---|
| `accepted` | La ráfaga puede ir al asistente. | Pasa al enrutador con el contexto (sección 7). El `outcome` lo decide lo que venga después. |
| `unsupported_content` | El asistente no sabe leer algo de la ráfaga (foto, vídeo, audio…). | Se crea un `handoff` con `reason = 'unsupported_content'` (`handed_off`). |
| `store_only` | Solo hay contenido que nadie tiene que contestar (p. ej. una reacción). | Nada (`stored_only`). Se ve en el dashboard. |
| `blocked_contact` | La persona tiene un bloqueo activo. | Nada. No se contesta (`stored_only`). El mensaje queda guardado y el dashboard lo marca. |
| `human_owned` | La conversación está en `waiting_human`: la lleva Bárbara. | No se contesta (`stored_only`); el mensaje aparece en la bandeja de Bárbara (ver 4.6). |
| Parado sin procesar | Mensaje duplicado, saliente o de historial (`is_backfill`). | Nada, y sin fila en `processing_runs` (ver 4.1 y 4.4). |

Cada ráfaga con al menos un mensaje entrante nuevo deja **una** fila en `processing_runs` con
su `gateway_result`, y sus mensajes quedan enlazados en `run_messages`. Así se mide cuántas se
aceptan, se bloquean, etc.

## 3. Diseño: una cadena de comprobaciones

El gateway es una **lista ordenada de comprobaciones**. Cada una recibe un contexto y hace una
de estas dos cosas:

- **continuar**, quizá añadiendo datos al contexto (por ejemplo, `person_id`), o
- **parar** con un resultado.

```
para cada comprobación de la lista:
    resultado = comprobación(contexto)
    si resultado es "parar":
        registrar y devolver resultado
devolver "accepted" con el contexto
```

**Por qué así y no una función larga con `if`s:**
- Cada comprobación se escribe y se prueba por separado (con `unittest`, sin el resto).
- El orden se ve en un único sitio: la lista.
- Añadir lo que falta del C2 (rate limit, prompt injection) es añadir un elemento a la lista,
  sin tocar las demás.

Un motor de reglas configurable sería demasiado para el MVP.

## 4. Las comprobaciones, en orden

```
 0. take_burst            coger la ráfaga de la cola (2)        → uno o varios mensajes
    para cada mensaje de la ráfaga:
 1. ignore_outgoing       ¿lo enviamos nosotros?                → guardar y descartar
 2. resolve_identity      ¿quién es? (persona + identidad)      → ctx.person_id, is_new_*
 3. resolve_conversation  ¿en qué conversación?                 → ctx.conversation
 4. store_message         ¿ya lo teníamos? ¿es historial?       → duplicado / historial: descartar
    con los mensajes entrantes nuevos que queden (si no queda ninguno, parar):
 5. reject_if_blocked     ¿tiene un bloqueo activo?             → blocked_contact
 6. stop_if_human_owned   ¿la conversación la lleva Bárbara?    → parar
 7. apply_content_policy  ¿el asistente puede leerlo?           → derivar / solo guardar
 (más adelante) rate_limit, prompt_injection
 8. accepted                                                     → enrutador
```

**Por qué la identidad va antes que el bloqueo**, aunque la prioridad sea "primero bloqueado,
luego primera vez": el bloqueo es de la **persona**, y para saber quién es la persona hay que
resolver su identidad primero. Y para que quede registrado que se rechazó un mensaje, el
mensaje tiene que estar guardado (`run_messages` enlaza el procesamiento con mensajes que ya
están en `messages`). La decisión de bloquear sigue siendo la primera que puede parar el
mensaje.

Los pasos 1 a 4 se hacen **por mensaje**; los pasos 5 a 8, **una vez por ráfaga**: todos los
mensajes de una ráfaga son de la misma conversación y, por tanto, de la misma persona.

Los pasos 0 a 8 de una ráfaga van en **una única transacción** (`BEGIN IMMEDIATE`, ver la
sección 2). Así no quedan datos a medias si el proceso se cae, y dos lecturas del mismo mensaje
a la vez no crean dos personas ni dos contactos. La transacción es corta: dentro no se llama a
ningún modelo ni a Instagram.

En el código, los pasos 1 a 4 están en `ingest.py` (`store_burst`) y los pasos 5 a 7 en
`checks.py`. Los mensajes de la ráfaga se guardan en el orden en que se enviaron
(`created_at` del canal), no en el que se encolaron.

### 4.1 `ignore_outgoing`

El adaptador lee también los mensajes que enviamos nosotros (el asistente, o Bárbara desde la
app de Instagram). Se guardan en `messages` (`direction = 'out'`, sin duplicados) para que el
hilo del dashboard esté completo, pero no se procesan: no generan `processing_runs`. Es lo que
ya dice `modules/handoff/policy.py` (`Direction.OUT` → `STORE_ONLY`).

Un saliente que no tenemos guardado no lo envió el asistente (el asistente guardará lo que
envíe), así que lo escribió una persona desde la app: se guarda con `author = 'human'`.

**Salientes a personas que no están en la base de datos (decidido el 2026-11-17): fuera del
MVP.** Para crear una conversación hace falta su contacto, y en un saliente el remitente
somos nosotros (`inbox` solo da nombres de usuario, no el `userId`). Pasa si escribimos
primero a alguien que nunca nos ha escrito, o con el historial de un hilo que empezamos
nosotros. La captación de clientes no está en el MVP, así que esas filas se marcan `done` sin
guardar el mensaje y con una nota en `inbound_queue.error`. Si la persona contesta después, se
crea la conversación con su mensaje. Después del MVP, la idea es exportar las conversaciones
que ya existen como base de datos inicial.

Las conversaciones de grupo, que no deberían llegar porque el lector no las encola, se tratan
igual: se marcan `done` sin guardar nada y con una nota.

### 4.2 `resolve_identity` — ¿quién es y es la primera vez?

Ver la sección 5.

### 4.3 `resolve_conversation`

Busca la conversación por `(channel_account_id, external_id)`. Si no existe, la crea con
`status = 'bot'`. Actualiza `last_message_at`.

### 4.4 `store_message` — idempotencia

```sql
INSERT INTO messages (conversation_id, direction, author, content_type, body,
                      external_id, created_at)
VALUES (?, 'in', 'contact', ?, ?, ?, ?)
ON CONFLICT (conversation_id, external_id) DO NOTHING
RETURNING id;
```

Si no devuelve fila, el mensaje ya estaba guardado: el adaptador lo ha vuelto a leer (pasa
siempre, porque lee las conversaciones recientes cada vez). **Se para sin hacer nada más:** ni
`processing_runs` nueva ni respuesta. Esto evita contestar dos veces al mismo mensaje.

Si es nuevo y es **historial** (`is_backfill = 1`), se queda guardado y se descarta: el
dashboard tiene el hilo completo, pero el asistente no contesta mensajes antiguos.

Cuando ya están guardados todos los mensajes de la ráfaga, si queda al menos un mensaje
entrante nuevo, se crea **una** fila de `processing_runs` (`started_at`) y una fila de
`run_messages` por cada uno de esos mensajes, y se sigue. Si no queda ninguno (todo eran
relecturas, salientes o historial), se para sin crear procesamiento.

### 4.5 `reject_if_blocked`

Ver la sección 6.

### 4.6 `stop_if_human_owned`

Si `conversations.status = 'waiting_human'`, la conversación ya está derivada y el asistente
**no** debe contestar: el mensaje solo se guarda y aparece en la bandeja de Bárbara.
`gateway_result = 'human_owned'` y `outcome = 'stored_only'` (valor añadido en el esquema v3).

### 4.7 `apply_content_policy`

Usa `modules/handoff/policy.decide()`, que ya existe, con cada mensaje de la ráfaga:

| `Handling` | Qué hace el gateway |
|---|---|
| `ASSISTANT` (texto) | Sigue hacia el enrutador. |
| `HANDOFF` (foto, vídeo, audio, no soportado) | Crea un `handoff` con `reason = 'unsupported_content'` y pasa la conversación a `waiting_human` (`gateway_result = 'unsupported_content'`). |
| `STORE_ONLY` (reacción, p. ej. un ❤️) | Para (`gateway_result = 'store_only'`). Se ve en el dashboard; nadie tiene que responder. |

Si la ráfaga mezcla tipos, manda el más restrictivo:
1. Si algún mensaje es `HANDOFF`, se deriva toda la ráfaga. Una pregunta con una foto que el
   asistente no puede ver no se puede contestar bien.
2. Si no, y algún mensaje es `ASSISTANT`, sigue hacia el enrutador con el texto de esos
   mensajes. Las reacciones se ignoran.
3. Si todo son `STORE_ONLY`, se para.

## 5. Identidad: ¿quién es y es la primera vez?

La regla está definida en `database.md` (6.2). Pasos, dentro de la transacción:

```sql
-- 1. ¿Conocemos esta identidad?
SELECT id, person_id FROM contacts WHERE channel = ? AND external_id = ?;

-- 2. Si no: ¿hay otra identidad del mismo canal con el mismo nombre de usuario?
SELECT person_id FROM contacts
WHERE channel = ? AND username = ?
ORDER BY created_at DESC
LIMIT 1;

-- 3. Si tampoco: persona nueva
INSERT INTO people (display_name, created_at) VALUES (?, ?) RETURNING id;

-- 4. En los casos 2 y 3: identidad nueva
INSERT INTO contacts (person_id, channel, external_id, username, display_name, created_at)
VALUES (?, ?, ?, ?, ?, ?);
```

El nombre de usuario se guarda sin `@` y en minúsculas (la base de datos rechaza mayúsculas).
Si una identidad conocida llega con otro nombre de usuario (lo ha cambiado), se actualiza
`contacts.username`.

Resultado en el contexto:

| Caso | `is_new_person` | `is_new_identity` | Qué significa |
|---|---|---|---|
| Identidad conocida | no | no | Ya nos ha escrito desde aquí. |
| Identidad nueva, enlazada por `username` | no | sí | Nos conoce, pero escribe desde otra cuenta o canal. **Hay contexto previo que cargar.** |
| Identidad nueva, persona nueva | sí | sí | Primera vez que nos escribe por cualquier sitio. |

El gateway **no decide** qué se hace con esto (dar la bienvenida, preguntar si es cliente…):
solo lo pasa al enrutador.

Entre canales distintos no hay un dato común fiable, así que el gateway nunca enlaza dos
canales: lo hace Bárbara desde el dashboard.

## 6. Bloqueo

### 6.1 La comprobación

```sql
SELECT EXISTS (
  SELECT 1 FROM blocks WHERE person_id = ? AND status = 'active'
);
```

Usa el índice parcial `idx_blocks_active`, así que es rápida aunque se haga en cada mensaje.
Como el bloqueo es de la persona, cubre el caso principal: alguien bloqueado en nuestra
cuenta A que escribe a la cuenta B (o por otro canal) se detecta y no recibe respuesta.

Si está bloqueada:
- `processing_runs.gateway_result = 'blocked_contact'`, con `outcome = 'stored_only'` y
  `finished_at`.
- No se contesta ni se llama a ningún modelo.
- **El mensaje se guarda** (decidido el 2026-11-16), para auditoría y para medir cuántos
  mensajes de personas bloqueadas llegan. El dashboard lo muestra marcado como bloqueado.
  Sigue la política de retención (RGPD) de `database.md`, que todavía está pendiente.
- **El bloqueo es solo interno:** el gateway no bloquea a nadie en Instagram.

### 6.2 Qué cuenta como bloqueo

Solo `status = 'active'`. Una propuesta del enrutador (`proposed`) **no** bloquea hasta que
Bárbara la confirma, así un error del modelo no deja a un cliente sin respuesta. Un bloqueo
quitado (`lifted`) o una propuesta rechazada (`rejected`) tampoco cuentan.

### 6.3 Quién crea los bloqueos (fuera del gateway)

| Origen | Quién | Dónde se implementa |
|---|---|---|
| `channel` | Bloqueo detectado en una cuenta de Instagram | Adaptador de Instagram (falta comprobar si instagram-cli da la lista de bloqueados). |
| `human` | Bárbara | Dashboard (`modules/platform/`). |
| `router` | El enrutador, como propuesta | Enrutador (`modules/router/`). Bárbara la confirma o rechaza desde el dashboard. |

## 7. Qué recibe el enrutador

Cuando la ráfaga se acepta, el enrutador recibe un `RouteRequest` con este contexto:

| Dato | Para qué |
|---|---|
| `run_id` | Para registrar sus decisiones (`routing_decisions`), sus llamadas a modelos y, si hace falta, proponer un bloqueo. |
| `message_ids` | Los mensajes de la ráfaga (los mismos que en `run_messages`). |
| `text` | El texto de los mensajes `ASSISTANT` de la ráfaga, unidos en orden. Es lo que hay que responder. |
| `conversation_id` y cuenta | Dónde y desde qué cuenta responder. |
| `history` | Los últimos mensajes de **esta** conversación (los dos sentidos), para entender la ráfaga en contexto, p. ej. "¿y el de inglés?". Propuesta: los 6 últimos. |
| `person_id` | Quién es, sea cual sea el canal. |
| `is_new_person`, `is_new_identity` | Si es la primera vez (sección 5). |
| `is_customer` | `people.is_customer`, si se sabe. |
| Contexto previo | Resúmenes de las otras conversaciones de la persona, en cualquier cuenta o canal. |

El contexto previo sale de esta consulta (el enrutador puede limitarla a las más recientes):

```sql
SELECT cv.id, ca.channel, ca.handle, cs.summary, cs.created_at
FROM contacts ct
JOIN conversations cv          ON cv.contact_id = ct.id
JOIN channel_accounts ca       ON ca.id = cv.channel_account_id
JOIN conversation_summaries cs ON cs.conversation_id = cv.id
WHERE ct.person_id = ?
  AND cv.id <> ?            -- la conversación actual no
ORDER BY cs.created_at DESC;
```

**Qué devuelve el enrutador** (`RouteDecision`), resumido. El detalle de cada campo está en
`database.md`, 6.5 y 6.13:

| Dato | Valores |
|---|---|
| `intent` | `faq`, `request`, `out_of_faq` |
| `topic`, `complexity` | Temática de la consulta y complejidad estimada (0–1) |
| `action` | `answer`, `request`, `deny`, `handoff` |
| `tier` | `slm`, `llm` o `none` (`deny` y `handoff` usan plantillas, sin modelo) |
| `decided_by` | `rule`, `classifier` o `arbiter` (el LLM al que se consulta si el clasificador duda) |
| `confidence`, `scores`, `threshold`, `router_version`, `latency_ms` | Cómo se tomó la decisión, por fase (`routing_decisions`) |
| Propuesta de bloqueo | Opcional, con motivo: una fila `blocks` con `source = 'router'` y `status = 'proposed'` |

## 8. Estructura del código

Todo con la librería estándar (`docs/decisions/0001-python.md`).

| Ruta | Qué contiene |
|---|---|
| `modules/gateway/worker.py` | `run_once()`: busca las conversaciones con la ráfaga lista y procesa cada una en su transacción. Aquí están la ventana de la ráfaga (`BURST_WINDOW`, 8 s) y los intentos (`MAX_ATTEMPTS`, 3). |
| `modules/gateway/pipeline.py` | `process_burst()`: guarda la ráfaga, pasa las comprobaciones y crea el procesamiento (y la derivación, si hace falta). |
| `modules/gateway/ingest.py` | Pasos 1 a 4: guardar la ráfaga (identidad, conversación y mensajes, sin duplicados). |
| `modules/gateway/identity.py` | Sección 5: quién es y si es la primera vez. |
| `modules/gateway/checks.py` | Pasos 5 a 7: una función por comprobación y la lista `CHECKS`. |
| `modules/gateway/tests/` | Tests de la identidad y del flujo completo, con una base de datos SQLite temporal creada con `init_db`. |
| `shared/types/gateway.py` | `GatewayResult` y `Outcome` (los mismos valores que los `CHECK` de `processing_runs`) y `GatewayDecision`. |
| `shared/types/queue.py` | `QueuedMessage` y el formato JSON del `payload` de la cola (`encode_payload` / `decode_payload`), que comparten el lector y el gateway. |
| `shared/db/` | Todo el SQL: `connection.py` (conexión, transacciones y formato de fechas), `queue.py`, `contacts.py` (personas, identidades y bloqueos), `conversations.py` (conversaciones, mensajes y derivaciones) y `runs.py` (procesamientos). |

Ningún archivo del gateway importa nada de `modules/channels/`.

**Pendiente, en otras PR:**
- `modules/channels/instagram/poller.py`, el lector que encola (sección 2).
- `shared/types/routing.py` con `RouteRequest` y `RouteDecision` (sección 7), junto con el
  enrutador. Mientras no exista, las ráfagas aceptadas quedan como procesamientos abiertos.
- Cómo se arranca el gateway (decisión abierta 1). Hoy solo existe `run_once()`.

## 9. Decisiones abiertas

1. **Cada cuánto se ejecutan el lector y el gateway.** Cada comando de instagram-cli tarda
   unos 5–6 s y `inbox` devuelve como mucho 10 conversaciones, así que el intervalo del
   lector marca el tiempo mínimo de respuesta. Falta decidirlo con pruebas reales, y también
   cómo se arrancan los dos scripts (cron, un proceso que no termina, Docker…).
2. **Ventana de la ráfaga:** cuántos segundos sin mensajes nuevos espera el gateway
   (propuesta: 8 s). Depende del intervalo del lector (decisión 1): si el lector pasa cada
   20 s, dos mensajes seguidos pueden caer en pasadas distintas, y la ventana tiene que
   cubrirlo.
3. **Cuándo se cierra una conversación (pendiente de definir).** Al cerrarse se genera su
   resumen (`conversation_summaries`, que ya existe en el esquema) y queda archivada hasta que
   la persona vuelva a escribir. Falta definir:
   - qué la cierra: Bárbara a mano, un tiempo sin mensajes, que el asistente dé la consulta
     por resuelta…;
   - qué hace el gateway cuando llega un mensaje a una conversación cerrada: reabrirla o
     empezar una conversación nueva. Hoy solo puede haber una fila por hilo del canal
     (`UNIQUE (channel_account_id, external_id)`), así que reabrir es lo que encaja con el
     esquema actual. **Mientras se decide, el código la reabre** (`status = 'bot'`);
   - en ambos casos, el resumen archivado llega al enrutador como contexto previo (sección 7).
4. **Respuesta enviada dos veces tras una caída.** Si el sistema se cae justo después de
   enviar una respuesta y antes de cerrar su procesamiento, al reiniciar se retomaría y se
   enviaría otra vez. Antes de reenviar hay que comprobar si la respuesta ya está en la
   conversación (el adaptador tiene `is_delivered`). Es del envío de respuestas, no del
   gateway.

### Decidido

- ~~**¿Quién llama al gateway?**~~ **✅ (2026-11-16):** un lector que se ejecuta cada cierto
  tiempo y una cola en la base de datos (sección 2).
- ~~**Mensajes de personas bloqueadas**~~ **✅ (2026-11-16):** se guardan, para auditoría y
  métricas (sección 6.1).
- ~~**Conversaciones que lleva una persona**~~ **✅ (2026-11-16):** `gateway_result =
  'human_owned'`, añadido en el esquema v3 (sección 4.6).
- ~~**Mensajes repetidos en la cola, ráfagas e historial**~~ **✅ (2026-11-16):** `UNIQUE` por
  mensaje, agrupación por conversación e `is_backfill` (sección 2). Cómo detecta el lector el
  historial: `database.md`, decisión abierta 14.
- ~~**Conversaciones de grupo**~~ **✅ (2026-11-16):** fuera del MVP. El lector no encola
  conversaciones con más de un participante, así que nunca llegan al gateway.
- ~~**Caída a mitad de una ráfaga**~~ **✅ (2026-11-17):** cada ráfaga va en una sola
  transacción, y lo que queda por contestar son los procesamientos abiertos (sección 2).
- ~~**Salientes a personas que no están en la base de datos**~~ **✅ (2026-11-17):** fuera del
  MVP; se descartan con una nota (sección 4.1).

### Fuera de este documento

- **Prompt injection, rate limits y timeouts:** están en el C2 pero no se diseñan aquí. Irán
  como comprobaciones nuevas en la lista (sección 3), después de `apply_content_policy`.
