# Arquitectura del gateway (`modules/gateway/`)

> **Estado:** propuesta para revisión (borrador). Todavía no hay código.
> **Fecha:** 2026-11-16
> **Depende de:** esquema v2 de la base de datos (`people`, `contacts`, `blocks`), ver
> `docs/architecture/database.md`.
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

Propuesta de tabla (todavía no está en el esquema: se añadirá a `database.md` en la PR del
código, como versión 3):

```sql
CREATE TABLE inbound_queue (
  id                  INTEGER PRIMARY KEY,
  channel_account_id  INTEGER NOT NULL REFERENCES channel_accounts(id),
  payload             TEXT NOT NULL,   -- JSON: ChannelConversation + ChannelMessage
  status              TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processing', 'done', 'failed')),
  attempts            INTEGER NOT NULL DEFAULT 0,
  error               TEXT,
  enqueued_at         TEXT NOT NULL,
  started_at          TEXT,
  finished_at         TEXT
) STRICT;
```

- Para coger trabajo, el gateway marca un lote como `processing` en una sola sentencia
  (`UPDATE … WHERE status = 'pending' … RETURNING`). Así dos procesos del gateway nunca cogen
  el mismo mensaje.
- Un mensaje que lleva demasiado tiempo en `processing` (el proceso se cayó) vuelve a
  `pending`. Tras varios fallos (`attempts`) pasa a `failed` y el dashboard lo muestra.
- **El lector encola también mensajes que ya conoce** (vuelve a leer las conversaciones
  recientes cada vez). No pasa nada: el gateway los descarta en `store_message` (4.4). Para
  que la cola no crezca sin control, el lector puede guardar hasta qué mensaje leyó en cada
  conversación y no volver a encolar los anteriores.
- **Las respuestas** pueden seguir el mismo patrón en sentido contrario (una cola de salida
  que un script envía con instagram-cli). Se diseñará con el envío de respuestas.

### Entrada del gateway: un mensaje de la cola

Cada elemento de la cola trae lo necesario para situar el mensaje:

| Dato | De dónde sale | Para qué lo usa el gateway |
|---|---|---|
| Cuenta propia | `inbound_queue.channel_account_id` (la cuenta de instagram-cli que leyó el mensaje) | Saber en qué cuenta entró y desde cuál responder. |
| `ChannelConversation` | `adapter.list_conversations()` | El `external_id` de la conversación y el **nombre de usuario** del contacto (`participants`). El nombre de usuario que da `read` suele ser genérico (`User_<id>`), así que el bueno es este. |
| `ChannelMessage` | `adapter.read_messages()` | El mensaje: `external_id`, `sender_external_id` (el `userId` numérico), `direction`, `content_type`, `body`, `created_at`. |

### Salida: una decisión

| Resultado | Qué significa | Qué pasa después |
|---|---|---|
| `accepted` | El mensaje puede ir al asistente. | Pasa al enrutador con el contexto (sección 7). |
| `accepted` + derivación | Puede seguir, pero el asistente no sabe leerlo (foto, vídeo, audio…). | Se crea un `handoff` con `reason = 'unsupported_content'`. |
| `blocked_contact` | La persona tiene un bloqueo activo. | Nada. No se contesta. El mensaje queda guardado y el dashboard lo marca. |
| Conversación de Bárbara | La conversación está en `waiting_human`. | No se contesta; el mensaje aparece en la bandeja de Bárbara (ver 4.6). |
| Parado sin procesar | Mensaje duplicado o mensaje saliente. | Nada, y sin fila en `processing_runs` (ver 4.1 y 4.4). |

Cada mensaje entrante nuevo deja una fila en `processing_runs` con su `gateway_result`, para
medir cuántos se aceptan, se bloquean, etc.

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
 1. ignore_outgoing       ¿lo enviamos nosotros?                → guardar y parar
 2. resolve_identity      ¿quién es? (persona + identidad)      → ctx.person_id, is_new_*
 3. resolve_conversation  ¿en qué conversación?                 → ctx.conversation
 4. store_message         ¿ya lo teníamos?                      → duplicado: parar
 5. reject_if_blocked     ¿tiene un bloqueo activo?             → blocked_contact
 6. stop_if_human_owned   ¿la conversación la lleva Bárbara?    → parar
 7. apply_content_policy  ¿el asistente puede leerlo?           → derivar / solo guardar
 (más adelante) rate_limit, prompt_injection
 8. accepted                                                     → enrutador
```

**Por qué la identidad va antes que el bloqueo**, aunque la prioridad sea "primero bloqueado,
luego primera vez": el bloqueo es de la **persona**, y para saber quién es la persona hay que
resolver su identidad primero. Y para que quede registrado que se rechazó un mensaje, el
mensaje tiene que estar guardado (`processing_runs.message_id` es obligatorio). La decisión de
bloquear sigue siendo la primera que puede parar el mensaje.

Los pasos 2 a 4, y la creación de la fila de `processing_runs`, van en **una única
transacción** (`BEGIN IMMEDIATE`). Así no quedan datos a medias si el proceso se cae, y dos
lecturas del mismo mensaje a la vez no crean dos personas ni dos contactos. La transacción es
corta: dentro no se llama a ningún modelo ni a Instagram.

### 4.1 `ignore_outgoing`

El adaptador lee también los mensajes que enviamos nosotros (el asistente, o Bárbara desde la
app de Instagram). Se guardan en `messages` (`direction = 'out'`, sin duplicados) para que el
hilo del dashboard esté completo, pero no se procesan: no generan `processing_runs`. Es lo que
ya dice `modules/handoff/policy.py` (`Direction.OUT` → `STORE_ONLY`).

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

Si es nuevo, se crea la fila de `processing_runs` (`started_at`) y se sigue.

### 4.5 `reject_if_blocked`

Ver la sección 6.

### 4.6 `stop_if_human_owned`

Si `conversations.status = 'waiting_human'`, la conversación ya está derivada y el asistente
**no** debe contestar: el mensaje solo se guarda y aparece en la bandeja de Bárbara. Ver
decisiones abiertas (falta un valor de `gateway_result` para este caso).

### 4.7 `apply_content_policy`

Usa `modules/handoff/policy.decide()`, que ya existe:

| `Handling` | Qué hace el gateway |
|---|---|
| `ASSISTANT` (texto) | Sigue hacia el enrutador. |
| `HANDOFF` (foto, vídeo, audio, no soportado) | Crea un `handoff` con `reason = 'unsupported_content'` y pasa la conversación a `waiting_human`. |
| `STORE_ONLY` (reacción, p. ej. un ❤️) | Para. Se ve en el dashboard; nadie tiene que responder. |

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
- `processing_runs.gateway_result = 'blocked_contact'`, con `finished_at`.
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

Cuando el mensaje se acepta, el enrutador recibe el contexto:

| Dato | Para qué |
|---|---|
| Mensaje (`message_id`, `body`, `content_type`) | Lo que hay que responder. |
| `conversation_id` y cuenta | Dónde y desde qué cuenta responder. |
| `person_id` | Quién es, sea cual sea el canal. |
| `is_new_person`, `is_new_identity` | Si es la primera vez (sección 5). |
| `run_id` | Para registrar sus llamadas a modelos y, si hace falta, proponer un bloqueo. |
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

## 8. Estructura de código propuesta

Se confirmará en la PR del código. Todo con la librería estándar (`docs/decisions/0001-python.md`).

| Ruta | Qué contiene |
|---|---|
| `modules/channels/instagram/poller.py` | El lector: cada cierto tiempo lee cada cuenta con el adaptador y encola los mensajes (sección 2). |
| `modules/gateway/worker.py` | Lee de la cola los mensajes pendientes y los pasa por el pipeline. |
| `modules/gateway/pipeline.py` | La lista de comprobaciones y el bucle que las ejecuta. |
| `modules/gateway/checks.py` | Una función por comprobación (sección 4). |
| `modules/gateway/tests/` | Un test por comprobación y uno del flujo completo, con una base de datos SQLite temporal. |
| `shared/types/gateway.py` | `InboundMessage` (cuenta + conversación + mensaje), `GatewayContext`, `GatewayResult` (los mismos valores que el `CHECK` de `gateway_result`) y `GatewayDecision`. En `shared/` porque los usan el gateway, el enrutador y el logging. |
| `shared/db/` | Acceso a `people`, `contacts`, `blocks`, `conversations`, `messages` e `inbound_queue`. El dashboard también lo usará (bloquear, fusionar personas, ver mensajes fallidos de la cola). |

Ninguno de estos archivos puede importar nada de `modules/channels/`.

## 9. Decisiones abiertas

1. **Cada cuánto se ejecutan el lector y el gateway.** Cada comando de instagram-cli tarda
   unos 5–6 s y `inbox` devuelve como mucho 10 conversaciones, así que el intervalo del
   lector marca el tiempo mínimo de respuesta. Falta decidirlo con pruebas reales, y también
   cómo se arrancan los dos scripts (cron, un proceso que no termina, Docker…).
2. **Conversaciones que lleva una persona:** `gateway_result` no tiene un valor para "la
   conversación está en `waiting_human`". Propuesta: añadir `human_owned` al `CHECK`
   (cambio de esquema, junto con `inbound_queue`).
3. **Cuándo se cierra una conversación (pendiente de definir).** Al cerrarse se genera su
   resumen (`conversation_summaries`, que ya existe en el esquema) y queda archivada hasta que
   la persona vuelva a escribir. Falta definir:
   - qué la cierra: Bárbara a mano, un tiempo sin mensajes, que el asistente dé la consulta
     por resuelta…;
   - qué hace el gateway cuando llega un mensaje a una conversación cerrada: reabrirla o
     empezar una conversación nueva. Hoy solo puede haber una fila por hilo del canal
     (`UNIQUE (channel_account_id, external_id)`), así que reabrir es lo que encaja con el
     esquema actual;
   - en ambos casos, el resumen archivado llega al enrutador como contexto previo (sección 7).

### Decidido

- ~~**¿Quién llama al gateway?**~~ **✅ (2026-11-16):** un lector que se ejecuta cada cierto
  tiempo y una cola en la base de datos (sección 2).
- ~~**Mensajes de personas bloqueadas**~~ **✅ (2026-11-16):** se guardan, para auditoría y
  métricas (sección 6.1).
- ~~**Conversaciones de grupo**~~ **✅ (2026-11-16):** fuera del MVP. El lector no encola
  conversaciones con más de un participante, así que nunca llegan al gateway.

### Fuera de este documento

- **Prompt injection, rate limits y timeouts:** están en el C2 pero no se diseñan aquí. Irán
  como comprobaciones nuevas en la lista (sección 3), después de `apply_content_policy`.
