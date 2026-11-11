# Adaptador de Instagram (`modules/channels/instagram/`)

Es la única parte del proyecto que sabe que existe Instagram. Lanza
[instagram-cli](https://github.com/supreme-gg-gg/instagram-cli) (cliente no oficial, MIT),
lee su JSON y lo traduce a los tipos comunes de `shared/types/messages.py`
(`ChannelConversation`, `ChannelMessage`). El resto del sistema solo trabaja con esos tipos.

```
Instagram ⇄ instagram-cli ⇄ cli.py → mapper.py → adapter.py ⇄ resto del sistema
            (programa aparte)  ejecuta   traduce    lo que usan los demás
```

Solo habla con Instagram: **no guarda nada en la base de datos, no decide respuestas y no
deriva conversaciones**. Eso es trabajo de otros módulos.

## Archivos

| Archivo | Qué hace |
|---|---|
| `adapter.py` | `InstagramAdapter`: lo único que deberían usar los demás módulos. |
| `cli.py` | `InstagramCli`: ejecuta instagram-cli (sin shell) y devuelve el `data` de su JSON. |
| `mapper.py` | Traduce el JSON a los tipos comunes. Funciones puras, sin red. |
| `errors.py` | Errores del adaptador (todos heredan de `InstagramCliError`). |
| `tests/` | Tests con `unittest` y respuestas de ejemplo (`fixtures/`, datos inventados). |

## Uso

```python
from pathlib import Path
from modules.channels.instagram import InstagramAdapter, InstagramAuthError

instagram = InstagramAdapter()

for conversation in instagram.list_conversations():
    for message in instagram.read_messages(conversation.external_id):
        ...  # ChannelMessage: content_type, body, direction, created_at...

message_id = instagram.send_text(conversation.external_id, "¡Hola!")
photo = instagram.download_media(conversation.external_id, message.external_id,
                                 Path("storage/media") / message.external_id)
```

Para usar una cuenta concreta: `InstagramAdapter(InstagramCli(account="nombre_de_usuario"))`.

| Método | Comando de instagram-cli | Devuelve |
|---|---|---|
| `list_conversations(limit=20)` | `inbox` | `list[ChannelConversation]` |
| `read_messages(id, limit=20)` | `read <id>` (sin marcar como visto) | `list[ChannelMessage]`, del más antiguo al más nuevo |
| `send_text(id, texto)` | `send <id> --text=...` | id del mensaje enviado |
| `download_media(id, id_mensaje, destino)` | `read <id> --message-id=... --download=...` | ruta final del archivo (instagram-cli añade la extensión) |

Cada comando tarda unos **5–6 s**.

## Cómo se traduce cada mensaje

| Lo que envía el cliente | `itemType` en instagram-cli | `content_type` | `body` |
|---|---|---|---|
| Texto | `text` | `text` | el texto |
| Foto o vídeo de la galería | `media` | `media` | `None` (se descarga con `download_media`) |
| Audio | `placeholder` | `unsupported` | `[Unsupported Type: voice_media]` |
| Publicación compartida | `placeholder` / `media_share` | `unsupported` | `[Unsupported Type: xma_media_share]` / `[media_share]` |
| Reel o foto temporal | `placeholder` | `unsupported` | `[Instagram CLI successfully blocked a brainrot]` |
| Reacción | `placeholder` | `unsupported` | `[Sent a ❤️]` |
| Enlace | `link` | `unsupported` | `[link]` (instagram-cli no incluye la URL en el JSON) |
| Cualquier tipo nuevo | — | `unsupported` | `[<itemType>]` |

El asistente solo responde a `text`. Todo lo demás se deriva a una persona
(`handoffs.reason = 'unsupported_content'`); el `body` le dice qué tipo de mensaje era.

## Reglas importantes (comprobadas con mensajes reales)

- **No detectar mensajes nuevos con `unread` ni con `last_activity_at`.** Una solicitud
  de mensaje aceptada en la app aparece como leída y con su fecha antigua. Hay que leer las
  conversaciones recientes y dejar que la base de datos descarte los mensajes que ya tiene
  (`UNIQUE (conversation_id, external_id)`).
- **Solicitudes de mensaje:** no se ven hasta que alguien las acepta desde la app.
- **El contacto se identifica por `sender_external_id`** (el `userId` numérico). El nombre de
  usuario que da `read` suele ser genérico (`User_<id>`); el nombre real viene en
  `ChannelConversation.participants`.
- **Solo se aceptan ids de conversación numéricos (20 dígitos o más).** Con cualquier otra
  cosa, instagram-cli busca por nombre aproximado y puede incluso empezar una conversación
  con otra persona. El adaptador lanza `ValueError` antes de ejecutar nada.
- `inbox` devuelve como mucho **10 conversaciones**, aunque se pida más.
- Leer no marca la conversación como vista.

## Errores

| Error | Cuándo | Qué hacer |
|---|---|---|
| `InstagramAuthError` | No hay sesión, ha caducado o Instagram pide verificación | Una persona ejecuta `instagram-cli auth login --username <cuenta>` en una terminal |
| `InstagramCliNotFoundError` | instagram-cli no está instalado | Ver "Instalación" |
| `InstagramCliTimeoutError` | No responde en 60 s | Reintentar más tarde |
| `InstagramFormatError` | El JSON no tiene el formato esperado | Probablemente instagram-cli se actualizó: revisar `mapper.py` |
| `InstagramCliError` | Cualquier otro error de instagram-cli | Mirar el mensaje |

## Instalación de instagram-cli

Requiere **Node.js 22 o superior**. Probado con la versión **2.1.0**.

```bash
npm install -g --prefix ~/.local @i7m/instagram-cli@2.1.0   # sin sudo; ~/.local/bin debe estar en el PATH
cd ~/.local/lib/node_modules/@i7m/instagram-cli && npx patch-package   # ver nota
instagram-cli --version
```

**Nota:** las versiones recientes de npm bloquean el script de instalación del paquete, que
aplica dos parches. Uno actualiza la versión de la app de Instagram con la que se identifica
(sin él usa una de 2019 y el inicio de sesión puede fallar o parecer sospechoso). Por eso hay
que ejecutar `npx patch-package` a mano.

### Iniciar sesión (una vez, a mano)

```bash
instagram-cli auth login --username <cuenta_secundaria>
```

Se hace en una **terminal interactiva**: no funciona desde scripts ni desde el `!` de Claude
Code. La sesión se guarda en `~/.instagram-cli/users/` y el adaptador la reutiliza.

## Seguridad

- Usar **solo la cuenta secundaria**. instagram-cli no es oficial: hay un riesgo bajo de que
  Instagram restrinja la cuenta.
- `~/.instagram-cli/` da acceso completo a la cuenta sin contraseña: nunca se copia al repo
  ni a `env/`.
- Los mensajes y las fotos descargadas son datos de clientes: van en `storage/` (ignorado por
  git). Los `fixtures` de los tests tienen datos **inventados**.
- Los argumentos se pasan como lista y sin shell, y en forma `--opcion=valor`: el texto de un
  mensaje nunca se interpreta como comando ni como opción.
- No consultar con un intervalo menor de 30–60 s.

## Tests

```bash
python -m unittest            # desde la raíz del repo; no necesitan red ni instagram-cli
```

Los fixtures reproducen la estructura exacta de instagram-cli 2.1.0. Si se actualiza
instagram-cli, hay que comprobar que su JSON sigue igual y actualizar los fixtures si cambia.
