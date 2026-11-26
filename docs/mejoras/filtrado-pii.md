# Mejora: filtrado de datos personales (PII)

> **Estado:** mejora prevista para **después del MVP**. Antes hay que tener una versión
> end-to-end funcionando (lector → gateway → enrutador → RAG → modelo → envío). Este documento recoge el
> problema y lo ya hablado para no perderlo; no hay que implementarlo todavía.
> **Fecha:** 2026-11-26
> **Relacionado:** `docs/architecture/observabilidad-alternativas.md` (sección 2.8.6 y pilar 3),
> `docs/decisions/0002-rag-busqueda-hibrida.md`, `database.md` (decisión abierta 2, RGPD).

---

## 1. El problema

El sistema guarda y mueve mensajes de clientes. Además de la tabla `messages`, que Bárbara
necesita tal cual, hay otros sitios por los que se pueden propagar datos personales
(PII: nombres, teléfonos, emails, DNI, nombres de usuario…):

| Dónde | Cómo llegan | Qué pasa hoy (MVP) |
|---|---|---|
| **Logs técnicos** | Mensajes y trazas de excepciones (sección 2) | Se registran completos: riesgo aceptado en 2.8.6 c |
| **Grabaciones de prompts y respuestas** (modo `full`) | La respuesta cruda del modelo puede repetir datos ("Hola Laura…") | Sin filtrar, con TTL |
| **Proveedores de modelos** (API externa) | Cada prompt lleva el mensaje del cliente | Se envía sin filtrar |
| **Casos límite conservados** (modo `edge`, futuro) | Grabaciones que se guardan mucho tiempo | Aún no existe |

Durante el MVP esto se cubre con TTL, acceso de una sola persona y la lista blanca de campos
en los logs. Esta mejora añade un **filtro de PII** para reducir la exposición.

## 2. Por dónde se cuelan datos en las excepciones (casos reales)

Una traza de Python no incluye los valores de las variables, pero sí **el mensaje de cada
excepción**. En el código actual del adaptador de Instagram:

**a) Errores de instagram-cli que copian su salida** (`modules/channels/instagram/cli.py`):

```python
raise InstagramCliError(
    f"instagram-cli did not return JSON (exit code {process.returncode}). "
    f"stderr: {stderr or '(empty)'}"          # últimos 300 caracteres
)
```

El stderr puede llevar nombres de usuario o títulos de conversación (en Instagram, el título
es el nombre de la persona).

**b) El error que devuelve instagram-cli se reenvía tal cual:** `raise InstagramCliError(message)`.

**c) Tiempo de espera agotado al enviar (el más delicado).** `adapter.py` envía con
`["send", conversation_id, f"--text={text}"]`. Si se agota el tiempo, `cli.py` lanza
`InstagramCliTimeoutError(...) from exc`, y la excepción encadenada de `subprocess` incluye
**el comando entero**:

```
subprocess.TimeoutExpired: Command '['instagram-cli', 'send', '340282…',
  '--text=Hola Laura, tu matrícula del curso…', '--output=json', '--username=…']'
  timed out after 30 seconds
```

Ahí aparecen la respuesta al cliente, el id de la conversación y la cuenta.

También pasa con excepciones de la librería estándar: un `KeyError` muestra la clave que
faltaba e `int("…")` el valor que no pudo convertir.

## 3. Lo que se propone

### 3.1 Logs: excepciones filtradas + logs raw temporales

Sustituye a la decisión 2.8.6 c (excepciones completas, riesgo aceptado).

- **Logs principales:** las excepciones se registran completas, pero con `error_message` y
  `traceback` **filtrados**. Lo que se pierde para depurar se recupera con el `run_id` en la
  base de datos, mientras dure su retención: el log dice qué falló; la BD, con qué datos.
- **Logs raw (opcional):** las líneas de nivel `ERROR` o superior se escriben **también sin
  filtrar** en `storage/logs/raw/`, con un **TTL de 72 h** (cubre un fin de semana). No se
  copian después: los dos handlers escriben a la vez desde el mismo evento.

```
                 ┌─> handler principal ─ filtro PII ─> stderr (+ LOG_DIR)        14 días
log.exception ───┤
                 └─> handler "raw" ──── sin filtro ──> storage/logs/raw/*.log    72 h
                     (solo ERROR o más grave)
```

Condiciones de los logs raw:

1. **Solo a archivo, nunca a stderr**: Docker y journald guardarían una copia con su propia
   retención. Solo existen si se define un directorio (p. ej. `LOG_RAW_DIR`).
2. **El TTL lo garantiza el trabajo periódico de limpieza**, no la rotación:
   `TimedRotatingFileHandler` solo borra archivos viejos cuando escribe una línea nueva, y
   puede pasar días sin errores.
3. **La redacción va en el formateador de cada handler**, sin modificar el registro. Si un
   `Filter` modificara el registro, el handler raw recibiría el texto ya filtrado (o el
   principal, el texto sin filtrar), según el orden.
4. **Fuera de Loki y de las copias de seguridad**: Alloy no lee `storage/logs/raw/` y las
   copias la excluyen. Si no, el TTL real sería el de la copia.
5. **Permisos restringidos** (solo el usuario del proceso).

Descartado: filtrar los logs después de escribirlos. stderr ya está en Docker, journald o
Loki y no se puede volver a filtrar; reescribir archivos en uso es frágil; y guardarlos en
SQLite para filtrarlos con SQL es la alternativa L3, ya descartada.

### 3.2 Filtro de los logs: reglas estructurales + regex (opción C)

Se aplica en el formateador del handler principal, sobre `error_message` y `traceback`. Los
demás campos ya los protege la lista blanca y `msg` es siempre una frase fija.

**Capa 1, reglas estructurales** para los formatos que construimos nosotros. Son exactas:

| Regla | Antes | Después |
|---|---|---|
| `--text=` | `'--text=Hola Laura, tu matrícula…'` | `'--text=[REDACTED]'` |
| `--username=` | `'--username=apuntalo_cuenta2'` | `'--username=[REDACTED]'` |
| stderr de instagram-cli | `stderr: <hasta 300 caracteres>` | `stderr: [REDACTED]` |

**Capa 2, regex** para datos con formato fijo: teléfonos españoles, emails, DNI/NIE (con letra
de control), IBAN, tarjetas (con Luhn) y `@menciones`.

Detalles que importan:

- **Números aislados.** Los ids de conversación de Instagram tienen unas 39 cifras: una regex
  de teléfono o de tarjeta encontraría coincidencias dentro y taparía nuestros propios ids. Hay
  que exigir que no haya otra cifra delante ni detrás (`(?<!\d)…(?!\d)`).
- **Tests con los casos reales** de la sección 2. Deben taparse el texto y la cuenta del
  `TimeoutExpired`, el stderr y los teléfonos, emails y DNI en varios formatos. **No** deben
  taparse los ids de conversación, los hashes de git ni las fechas.
- **Limitación conocida:** un nombre propio que llegue por una fuente que no conocemos no lo
  detectan ni las reglas ni las regex. Cuando aparezca una fuente nueva de texto libre en los
  errores, se añade su regla estructural (cerrado por defecto, ampliado a conciencia).

Descartados para los logs, por ahora:

- **Solo regex:** no cubre el caso c (nombres dentro de `--text=`).
- **Modelo NER en el logger:** ver 3.4.

### 3.3 Un módulo de PII compartido

Las regex sirven tanto para los logs como para las grabaciones, así que viven en un único
módulo (p. ej. `modules/observability/pii.py`) y cada uso combina las capas que necesita:

```python
redact(text, layers=("structural", "regex"))            # logs
redact(text, layers=("known", "regex", "ner"))          # grabaciones
redact(text, layers=("structural", "regex", "ner"))     # logs, si la evaluación lo justifica
```

| Capa | Qué hace |
|---|---|
| `structural` | Reglas para nuestros formatos (`--text=`, `--username=`, stderr) |
| `known` | Sustituye por coincidencia exacta el nombre de usuario y el nombre de perfil del remitente, que ya están en la BD |
| `regex` | Teléfonos, emails, DNI/NIE, IBAN, tarjetas, `@menciones` |
| `ner` | Modelo de reconocimiento de entidades para nombres, lugares y direcciones |

### 3.4 Modelo NER: Presidio o GLiNER, decidido con una evaluación

| | Presidio (Microsoft) | GLiNER (Hugging Face) |
|---|---|---|
| Qué es | Un framework: regex propias + un modelo NER intercambiable | Un modelo NER genérico, con variantes para PII y multilingües |
| Modelo | spaCy por defecto; en español, `es_core_news_sm` ocupa decenas de MB y **no necesita PyTorch** | Basado en transformers: **necesita PyTorch**, del orden de cientos de MB |
| Velocidad en CPU | Milisegundos por línea | Decenas de milisegundos por línea |

Por qué no entra ya en los logs:

1. **Dependencias:** el proyecto aún no tiene gestor de dependencias (`0001-python.md`). En el
   logger, la dependencia entraría en **todos** los procesos, incluido el lector, que no la
   necesita. Toda dependencia se consulta antes con el equipo (`AGENTS.md`).
2. **Lo conocido ya está cubierto** por las reglas estructurales. El modelo solo aporta en
   nombres que lleguen por fuentes desconocidas, poco frecuentes en excepciones.
3. **El logger no puede fallar:** si el modelo no carga, hace falta la regex igualmente.
4. **No sabemos aún cuál funciona** con mensajes de Instagram en español (minúsculas, emojis,
   abreviaturas).

Plan:

1. Cuando haya grabaciones que conservar (modo `edge`), se evalúan **Presidio con spaCy
   pequeño, GLiNER y solo regex** con mensajes reales etiquetados a mano, como en la `0002`.
   Se mide cuántos datos detecta cada uno (lo más importante: no dejarse ninguno), cuánto tapa
   de más y cuánto tarda.
2. Con los resultados se decide qué modelo usan las grabaciones y si la capa `ner` se activa
   también en los logs (con una variable de entorno). Si gana Presidio con spaCy pequeño, el
   coste en los logs es bajo.

Siempre **en local**: nunca la API de inferencia de Hugging Face, que enviaría los mensajes a
un tercero (mismo criterio que la `0002`).

### 3.5 Grabaciones de prompts y respuestas

- **Modo `full`** (puesta a punto, temporal, con TTL): el prompt se guarda como plantilla +
  referencias a `messages`, así que no copia el texto del cliente. La **respuesta del modelo**
  se filtra al guardarla. Consecuencia: la grabación ya no es la salida exacta; para
  reproducir (R-b) se compara texto filtrado con texto filtrado.
- **Modo `edge`** (futuro): solo casos límite (derivaciones, puntuación cerca del umbral,
  respuestas bloqueadas, errores, correcciones de Bárbara). Se graba todo durante 48–72 h y
  la limpieza conserva y seudonimiza los casos límite con las tres capas (`known`, `regex`,
  `ner`); el resto se borra.

### 3.6 Filtrar antes de los modelos (posible mejora, la más ambiciosa)

Hoy los modelos (SLM y LLM) reciben el texto **original**. La alternativa es filtrar entre el
gateway y el enrutador:

```
gateway ──guarda original──> messages (para Bárbara)
   │
   └─> filtro PII ─> enrutador ─> RAG ─> modelo (API externa) ─> grabaciones
```

- **A favor:** es la mitigación más fuerte frente a los proveedores de modelos (el prompt
  sale sin identificadores) y las grabaciones nacen seudonimizadas.
- **Riesgo:** puede empeorar las respuestas si tapa lo que hace falta para contestar
  ("¿Tenéis academia en [LOCATION]?").

Condiciones si se adopta:

1. Tapar **solo identificadores de personas** (nombres, teléfonos, emails, DNI, direcciones
   concretas, usuarios), no ciudades ni organizaciones.
2. Si el filtro falla, **derivar a Bárbara** antes que enviar el texto sin filtrar
   (degradación segura, sección 5.2 del estudio de observabilidad).
3. **Evaluarlo antes** con las 104 preguntas de la `0002`, con y sin filtro, y comprobar que
   el RAG y el enrutador no empeoran.
4. Toca el gateway y el enrutador: decidirlo con todo el equipo.

### 3.7 Mejora en el origen

Que `cli.py` no encadene el comando completo en `InstagramCliTimeoutError` (`from None`, o
guardando solo el subcomando). Es una PR pequeña e independiente; el filtro de los logs
seguiría como red de seguridad.

## 4. Lo que el filtro no resuelve

- **Identificadores indirectos combinados** ("la de 2.º de Medicina de Murcia que se apuntó el
  martes"): ningún filtro los detecta bien.
- **Categorías especiales** (salud, discapacidad…, artículo 9 del RGPD): "Tengo TDAH, ¿hay
  adaptaciones?" no lleva identificadores, pero es un dato protegido en cuanto se asocia a
  quien lo envía. Filtrarlo rompería respuestas legítimas.
- **El vínculo con la cuenta:** en nuestra BD, un texto filtrado sigue enlazado a
  `conversation_id` y `person_id`. Para nosotros sigue siendo un dato personal; el filtro
  **seudonimiza, no anonimiza**.

Por eso el filtro **se suma** a las demás medidas (TTL, plantilla + referencias, acceso de una
sola persona, contratos con proveedores) y no sustituye a ninguna.

## 5. Relación con el RGPD

El RGPD no se cumple con una pieza técnica, sino con el conjunto. Pendientes que este filtro
no cubre:

| Responsable | Pendiente |
|---|---|
| Equipo (código) | Retención de `messages` y de los resúmenes de tickets (`database.md`, decisión 2) |
| Equipo (código) | Retención de las copias de seguridad (≤ la de `messages`) |
| Equipo (código) | TTL de las grabaciones del modo `full` y criterio de salida |
| Equipo (código) | Borrar todo lo de una persona cuando lo pida |
| Equipo (código) | Limitar `docker logs` (`max-size`, `max-file`); `PRAGMA secure_delete` y `auto_vacuum` en SQLite |
| Apúntalo | Base legal para guardar mensajes y usarlos en control de calidad |
| Apúntalo | Política de privacidad: asistente automático, finalidad y plazos |
| Apúntalo | Contratos con los proveedores de modelos (retención, no entrenar, transferencias fuera de la UE) |
| Apúntalo | Categorías especiales y menores, si los hay |
| Apúntalo | Registro de actividades de tratamiento |

## 6. Orden propuesto (después del MVP)

| Paso | Qué | Depende de |
|---|---|---|
| 1 | Mejora en el origen (`cli.py`, 3.7) | Nada; se puede hacer en cualquier momento |
| 2 | Módulo `pii.py` con capas `structural` y `regex`, y sus tests (3.2, 3.3) | Fachada de `modules/observability/` |
| 3 | Excepciones filtradas + logs raw de 72 h (3.1), sustituyendo a 2.8.6 c | Paso 2 y el trabajo de limpieza |
| 4 | Respuestas del modelo filtradas en las grabaciones (3.5) | Paso 2 y las grabaciones |
| 5 | Evaluación Presidio / GLiNER / regex y capa `ner` (3.4) | Gestor de dependencias decidido |
| 6 | Modo `edge` con seudonimización (3.5) | Paso 5 |
| 7 | Filtrar antes de los modelos (3.6) | Paso 5 y acuerdo del equipo |
