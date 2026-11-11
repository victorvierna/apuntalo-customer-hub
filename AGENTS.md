# AGENTS.md

## Proyecto
Dashboard interno para gestionar respuestas automatizadas a los mensajes de clientes
que llegan a una cuenta secundaria de Instagram de Apúntalo. Cualquier mensaje que
necesite intervención humana se deriva a Bárbara (equipo de Apúntalo).

- Backend en **Python 3.11 o superior**, priorizando la librería estándar (ver `docs/decisions/0001-python.md`).
  El resto del stack (framework web, gestor de dependencias) está pendiente: no asumas frameworks ni dependencias.
- Regla de producto: el asistente de Instagram solo responde con información de las FAQ;
  si no la tiene, deriva a una persona (handoff). Nunca inventa respuestas.

## Arquitectura
- Núcleo independiente del canal + un adaptador por canal.
- Solo `modules/channels/<canal>/` puede contener código específico de un canal (p. ej. Instagram).
- Diagramas en `docs/architecture/`.
- Decisiones técnicas (qué se eligió y por qué), numeradas en `docs/decisions/`.

## Estructura
- `data/faqs/` — base de conocimiento (FAQ oficiales). Nunca datos reales de clientes.
- `docker/` — instrucciones para arrancar todo en cualquier máquina.
- `env/` — secretos locales (tokens, API keys). Git lo ignora.
- `modules/`
  - `channels/` — código concreto de cada canal (ahora solo `instagram/`).
  - `gateway/` — entrada única al núcleo; decide si el asistente puede contestar o no.
  - `handoff/` — si el asistente no puede contestar, deriva la conversación a una persona.
  - `logging/` — registra cada mensaje, respuesta, modelo, coste y derivación para depurar y medir el MVP.
  - `models/` — clientes de los modelos de IA; el router decide cuál usar.
  - `platform/` — dashboard interno: bandeja de conversaciones y gestión de la derivación.
  - `rag/` — busca en `data/faqs/` la información para responder; si no la encuentra, devuelve vacío.
  - `router/` — escoge el mejor modelo para contestar según la entrada.
- `shared/` — código usado por 2 o más módulos: `config/`, `db/`, `types/`, `utils/`.
  - `db/` — acceso a la base de datos SQLite; `init_db.py` crea el esquema.
- `storage/` — datos locales generados en ejecución, como la base de datos
  `apuntalo-marketing-platform.db`. Contiene datos reales de clientes: git lo ignora.

## Base de datos
- SQLite. Arquitectura y esquema en `docs/architecture/database.md`.
- Archivo por defecto: `storage/apuntalo-marketing-platform.db`. Se puede cambiar con la
  variable de entorno `DATABASE_PATH`; las rutas relativas son relativas a la raíz del repo.
- Los archivos `.db` nunca se suben a git.

## Comandos
- Crear la base de datos: `python shared/db/init_db.py` (solo usa la librería estándar).
- Tests: `python -m unittest` desde la raíz del repo (usa `unittest`, de la librería estándar).
- TODO: el resto (instalación, ejecución) está pendiente. No inventes esos comandos.

## Git y Pull Requests
- Nunca se hace commit directo a `main`; todo entra por Pull Request.
- Ramas desde `main` con prefijo: `feature/`, `fix/`, `docs/`, `ci/` (p. ej. `docs/agents-md`).
- Commits en inglés con Conventional Commits: `tipo(ámbito opcional): descripción`
  (tipos: feat, fix, docs, chore, ci, refactor, test). Ej: `docs(architecture): add c2 diagram`.
- Commits pequeños y con un solo propósito.
- Cada PR necesita la revisión del otro miembro del equipo antes de mergear.
- Toda PR usa la plantilla `.github/pull_request_template.md`, completa y escrita
  para que el revisor la entienda sin leer el código.
- Si el cambio se ve (interfaz, flujos), añade capturas o un vídeo corto.
  Si eres un agente de IA, indica dónde debe añadirlas una persona.

## Cómo trabajar
- Pregunta antes de: añadir dependencias, elegir stack/frameworks, cambiar la estructura
  de carpetas, tocar `env/` o secretos, o hacer cualquier acción en `main` o en remoto.
- Si una petición es ambigua, pregunta en vez de suponer.
- Las decisiones de arquitectura se documentan en `docs/architecture/`;
  las tareas y el seguimiento del sprint, en Notion.
- Si cambias la estructura o las convenciones, actualiza este AGENTS.md en el mismo PR.

## Notion (gestión del proyecto)
- Tareas y sprints: base de datos "Tareas" del workspace de Apúntalo Marketing Platform.
- Antes de empezar una tarea, búscala en Notion y lee su descripción y criterios de aceptación.
  Si el código y Notion se contradicen, pregunta.
- No cambies estados, responsables ni fechas en Notion sin que te lo pidan.
- Si no tienes acceso a Notion, dilo y pide a la persona que te pegue la tarea.

## Seguridad
- Los secretos van en `env/` (o `.env`), jamás en el código como texto plano.
