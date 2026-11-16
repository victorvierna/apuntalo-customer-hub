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

### Entrada: un mensaje leído del canal

El adaptador de Instagram no recibe avisos de mensajes nuevos: alguien tiene que leer las
conversaciones recientes cada cierto tiempo y pasar cada mensaje al gateway (ver decisiones
abiertas). Cada mensaje llega con lo necesario para situarlo:

| Dato | De dónde sale | Para qué lo usa el gateway |
|---|---|---|
| Cuenta propia | `channel_accounts` (la cuenta de instagram-cli que leyó el mensaje) | Saber en qué cuenta entró y desde cuál responder. |
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
- El mensaje queda guardado y el dashboard lo muestra marcado como bloqueado.
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
| `modules/gateway/pipeline.py` | La lista de comprobaciones y el bucle que las ejecuta. |
| `modules/gateway/checks.py` | Una función por comprobación (sección 4). |
| `modules/gateway/tests/` | Un test por comprobación y uno del flujo completo, con una base de datos SQLite temporal. |
| `shared/types/gateway.py` | `InboundMessage` (cuenta + conversación + mensaje), `GatewayContext`, `GatewayResult` (los mismos valores que el `CHECK` de `gateway_result`) y `GatewayDecision`. En `shared/` porque los usan el gateway, el enrutador y el logging. |
| `shared/db/` | Acceso a `people`, `contacts`, `blocks`, `conversations` y `messages`. El dashboard también lo usará (bloquear, fusionar personas). |

Ninguno de estos archivos puede importar nada de `modules/channels/`.

## 9. Decisiones abiertas

1. **¿Quién llama al gateway?** Hace falta un proceso que, cada cierto tiempo, lea las
   conversaciones recientes de cada cuenta con el adaptador y pase cada mensaje al gateway.
   Falta decidir dónde vive (no encaja en ningún módulo actual) y cada cuánto lee: cada
   comando de instagram-cli tarda unos 5–6 s.
2. **Conversaciones que lleva una persona:** `gateway_result` no tiene un valor para "la
   conversación está en `waiting_human`". Propuesta: añadir `human_owned` al `CHECK`
   (cambio de esquema).
3. **Mensaje nuevo en una conversación `closed`:** propuesta: se reabre (`status = 'bot'`) y
   se procesa como cualquier otro.
4. **Mensajes de personas bloqueadas:** la propuesta es guardarlos (para auditoría y para la
   métrica de mensajes bloqueados). Si se prefiere no guardar datos de personas bloqueadas,
   no quedaría registro en `processing_runs`. Tiene que seguir la política de retención
   (RGPD) de `database.md`.
5. **Conversaciones de grupo:** si `participants` tiene más de una persona, no está claro a
   quién atribuir el mensaje. Propuesta: derivarlas siempre a Bárbara.
6. **Prompt injection, rate limits y timeouts:** están en el C2 pero no se diseñan aquí. Irán
   como comprobaciones nuevas en la lista (sección 3), después de `apply_content_policy`.
