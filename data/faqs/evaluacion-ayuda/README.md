# Preguntas para evaluar el asistente de ayuda

Este paquete permite comprobar si el asistente responde de forma útil y fiel a las guías de Apúntalo. Contiene 104 preguntas con una respuesta de referencia, artículos de apoyo y errores que debe evitar. Las personas, cantidades y situaciones de los ejemplos son ficticias.

La evaluación corresponde a un asistente que **solo consulta documentación**. No tiene acceso a cuentas, agendas, cobros ni datos personales y no puede realizar acciones. El asistente que pueda existir dentro de Apúntalo tiene un alcance diferente.

## Qué compartir

Entrega juntas las carpetas `ayuda/` y `evaluacion-ayuda/`, conservando sus nombres y su posición una junto a la otra. Así funcionan las referencias a los artículos. No hace falta compartir el repositorio ni el registro interno de revisión.

`preguntas.jsonl` tiene una pregunta por línea. Cada línea es un objeto con estos campos:

- `id`: identificador estable del caso.
- `pregunta`: consulta que se presenta al asistente.
- `conducta_esperada`: responder, aclarar antes de decidir o abstenerse de afirmar datos de la cuenta.
- `respuesta_esperada`: contenido que debe transmitir; no tiene que repetirlo literalmente.
- `referencias`: artículos que respaldan la respuesta.
- `criterios`: aspectos que deben estar presentes.
- `errores_a_evitar`: afirmaciones o instrucciones que invalidan la respuesta.

Las respuestas de referencia son material de evaluación. **No las incluyáis entre los documentos que consulta el asistente durante la prueba**: el objetivo es comprobar que sabe encontrar y utilizar las guías.

## Cómo probarlo

1. Carga las guías de `ayuda/` en el sistema que estáis preparando.
2. Presenta cada pregunta sin mostrarle la respuesta de referencia. Usa una conversación nueva para cada caso, salvo que estés probando expresamente preguntas de seguimiento.
3. Guarda la respuesta y los artículos que haya utilizado.
4. Compara el sentido de la respuesta con los criterios y errores. Acepta distintas palabras o pasos equivalentes que estén respaldados por las guías.
5. Repite los casos que fallen después de corregir la documentación o el sistema. Conserva la pregunta y el identificador para poder comparar.

Cuando deba aclarar, basta con una pregunta concreta que resuelva la ambigüedad. Puede añadir orientación condicional sin elegir por el usuario. Cuando deba abstenerse de afirmar un dato privado, debe explicar la limitación y dónde consultarlo; no basta con responder «no lo sé».

## Puntuación sencilla

- **2 — Correcta:** responde o pide la aclaración adecuada, cumple los criterios y no inventa información.
- **1 — Parcial:** orienta bien, pero omite un paso o una condición relevante sin inducir una acción peligrosa.
- **0 — Incorrecta:** contradice una regla, mezcla recorridos, inventa datos o asegura haber ejecutado una acción.

Además de la puntuación, anota por separado si hay un error que podría causar un cobro duplicado, una cancelación equivocada, pérdida de datos o una falsa confirmación de pago. Uno de esos errores requiere revisión aunque la puntuación general sea alta.

No evaluéis por coincidencia literal ni penalicéis respuestas breves que resuelvan la pregunta. Revisad tanto la respuesta como sus referencias: un artículo citado debe respaldar lo que se afirma.

## Cobertura y límites

Hay preguntas sobre agendas y permisos, horarios, servicios, citas, contactos, Google Calendar, lista de espera, bonos, cobros, suscripción, informes y experiencia del cliente. Incluye casos de cálculo de señales y devoluciones, comisiones, bonos, fechas de cobro y actividad, y efectos de cambios sobre citas existentes. También hay consultas ambiguas y peticiones que exigen datos o acciones ajenos a un asistente documental.

Las guías no permiten confirmar saldos, facturas personales, próximos cargos ni disponibilidad en tiempo real. Los precios exactos de suscripción y tarifas externas no se evalúan con cifras fijas. Las pruebas no acreditan por sí solas que todas las pantallas se hayan comprobado visualmente ni que se hayan cubierto todas las variantes.

Tras la primera ronda, añadid preguntas reales anonimizadas que no estén ya representadas. Reservad algunas para la evaluación final y evitad modificar sus respuestas esperadas para hacer pasar una respuesta incorrecta del asistente.

La ampliación incluye efectos de cambios sobre citas existentes, interpretación de importes y fechas, búsquedas sin duplicados, sustitución de profesionales, personalización de fichas y gestión de pautas recurrentes.
