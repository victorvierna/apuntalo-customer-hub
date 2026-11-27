# Criba de SLM: respuestas

Para puntuar a mano: 2 = correcta, 1 = parcial, 0 = incorrecta o inventada (rúbrica de `data/faqs/evaluacion-ayuda/README.md`).

## AYUDA-001 · Quiero una agenda para una nueva profesional. ¿Por dónde empiezo?

**Esperado (responder):** Con la cuenta del propietario, abre Agendas > Nueva agenda, introduce nombre y teléfono si corresponde y pulsa Crear. Revisa antes el aviso de coste adicional y configura sus servicios y horarios.

Fragmentos: `ayuda/19-recorridos/incorporar-profesional.md`, `ayuda/20-guias-visuales/pantallas-comentadas.md#crear-una-agenda`, `ayuda/18-ayuda/ayuda.md#a-quien-escribo-si-quiero-cambiar-una-cita-o-pedir-una-devolucion`

- **qwen3.5:0.8b** (0.12 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (0.88 s): Para crear una agenda para una nueva profesional, debes ir a **Agendas > Nueva agenda** desde el panel de control del negocio. En esta pantalla verás un aviso sobre costes adicionales y podrás introducir los datos del profesional (nombre y teléfono) antes de crear la agenda.  CONFIANZA: 0.95
- **qwen3.5:4b** (1.13 s): Para empezar, ve a **Agendas > Nueva agenda** desde la aplicación. Allí podrás introducir el nombre y teléfono de la nueva agenda. Si necesitas que otra persona tenga su propia cuenta, tendrás que crear una nueva agenda en lugar de compartir la existente.  CONFIANZA: 0.9
- **gemma4:e2b** (0.49 s): Para crear una agenda, desde **Agendas > Nueva agenda**, revisa los siguientes elementos: **Aviso de coste adicional**, **Nombre** y **Teléfono**, e introduce los datos de la agenda que vas a crear. El nombre es necesario para crear la agenda.  CONFIANZA: 1.0
- **ministral-3:3b** (1.48 s): Empieza por ir a **Agendas > Nueva agenda** y sigue estos pasos: 1. Revisa el **aviso de coste adicional** (si aplica). 2. Introduce el **nombre** y **teléfono** de la nueva agenda. 3. Haz clic en **Crear** (el nombre es obligatorio).  Luego, sigue el recorrido para **incorporar al profesional** (que incluye preparar horarios y servicios).  ¿Quieres que te explique cómo compartir una agenda existente en lugar de crear una nueva? CONFIANZA: 0.9
- **nemotron-3-nano:4b** (0.57 s): Empiezas desde la pantalla de "Crear agenda", donde introduces el nombre y el teléfono de la agenda y luego creas la agenda. CONFIANZA: 1
- **llama3.2:3b** (0.73 s): Para crear una agenda para una nueva profesional, empieza en **Agendas > Nueva agenda**. Introduce el nombre y el teléfono de la agenda que vas a crear. Luego, crea la agenda y, una vez creada, puedes compartir la agenda existente sin crear una nueva.
- **granite4:3b** (0.85 s): Empiezas creando una nueva agenda en **Agendas > Nueva agenda**. Asegúrate de introducir el nombre y teléfono de la profesional. Ten en cuenta que crear otra agenda puede cambiar la suscripción y compartir una agenda existente es otra tarea. CONFIANZA: 0.9

## AYUDA-010 · Voy a cerrar por vacaciones. ¿Se cancelan solas las citas?

**Esperado (responder):** Configura el periodo en Agendas > Descansos > Nuevo descanso. Revisa y gestiona aparte las citas existentes; cerrar disponibilidad no sustituye cancelarlas o cambiarlas.

Fragmentos: `ayuda/19-recorridos/vacaciones-y-horario-verano.md#cerrar-durante-unas-vacaciones`, `ayuda/17-guia-del-cliente/reservar.md#perfil-y-avisos`, `ayuda/20-guias-visuales/pantallas-comentadas.md#cambiar-el-horario-de-un-dia`

- **qwen3.5:0.8b** (0.24 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (0.23 s): NO_LO_SE
- **qwen3.5:4b** (1.08 s): No, las citas no se cancelan solas. Debes revisar cada cita afectada y acordar su cambio o cancelación con tus clientes.  CONFIANZA: 1
- **gemma4:e2b** (0.48 s): No, el cierre modifica la disponibilidad. Debes revisar cada cita afectada y acordar su cambio o cancelación. CONFIANZA: 1.0
- **ministral-3:3b** (0.75 s): No, las citas **no se cancelan automáticamente** al cerrar por vacaciones. Debes gestionarlas tú con cada negocio afectado.  CONFIANZA: 0
- **nemotron-3-nano:4b** (0.72 s): NO_LA_CANCELAN_SOLAS. CONFIANZA: 1
- **llama3.2:3b** (0.28 s): NO_LO_SE
- **granite4:3b** (0.65 s): No, las citas no se cancelan solas. Debes gestionarlas con cada negocio. CONFIANZA: 0.9

## AYUDA-014 · ¿Dónde preparo un nuevo servicio?

**Esperado (responder):** Abre Servicios y crea un servicio. Define nombre, duración y precio, revisa agendas disponibles y si los clientes pueden reservarlo; guarda y comprueba su presentación.

Fragmentos: `ayuda/05-servicios/servicios.md`, `ayuda/05-servicios/servicios.md#combos-de-servicios`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#por-que-el-informe-mensual-no-coincide-con-los-cobros`

- **qwen3.5:0.8b** (0.36 s): [1] Crear y organizar servicios › Abre **Servicios** en el menú y pulsa **Crear servicio** o **Nuevo servicio**. NO_LO_SE  CONFIANZA: 0.9
- **qwen3.5:2b** (0.91 s): Para preparar un nuevo servicio, debes abrir el menú **Servicios** y pulsar **Crear servicio** o **Nuevo servicio**. Luego introduce el nombre, duración, precio, descripción, color y categoría correspondientes antes de guardar.  CONFIANZA: 0.95
- **qwen3.5:4b** (0.95 s): En el menú, pulsa **Servicios** y luego selecciona **Crear servicio** o **Nuevo servicio**.  CONFIANZA: 1
- **gemma4:e2b** (0.46 s): Para crear un nuevo servicio, abre **Servicios** en el menú y pulsa **Crear servicio** o **Nuevo servicio**. CONFIANZA: 1
- **ministral-3:3b** (0.69 s): En el apartado **Servicios** del menú, pulsa **Crear servicio** o **Nuevo servicio**.  CONFIANZA: 1
- **nemotron-3-nano:4b** (0.91 s): En el menú, abre **Servicios** y pulsa **Crear servicio** o **Nuevo servicio**. CONFIANZA: 1
- **llama3.2:3b** (0.55 s): Abre **Servicios** en el menú y pulsa **Crear servicio** o **Nuevo servicio**.
- **granite4:3b** (0.62 s): En el menú, abre **Servicios** y pulsa **Crear servicio** o **Nuevo servicio**.

## AYUDA-020 · Quiero cancelar.

**Esperado (aclarar):** Aclara si quieres cancelar una cita, la suscripción de Apúntalo o una solicitud de pago; el procedimiento y sus consecuencias son distintos.

Fragmentos: `ayuda/18-ayuda/ayuda.md#a-quien-escribo-si-quiero-cambiar-una-cita-o-pedir-una-devolucion`, `ayuda/19-recorridos/cancelar-con-pago-o-bono.md#cancelar-una-solicitud-de-pago-devuelve-dinero`, `ayuda/14-precios-y-suscripcion/suscripcion.md#cancelar-el-plan-cancela-tambien-las-citas`

- **qwen3.5:0.8b** (0.16 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.47 s): ¿Por qué quieres cancelar? ¿Una cita específica o tu suscripción al servicio?  CONFIANZA: 0.95
- **qwen3.5:4b** (0.88 s): ¿Qué tipo de cancelación deseas realizar? ¿Quieres cancelar una cita específica, un pago recibido o tu suscripción al servicio?  CONFIANZA: 0.5
- **gemma4:e2b** (0.26 s): ¿Qué quieres cancelar? CONFIANZA: 0.5
- **ministral-3:3b** (1.31 s): Para cancelar una cita, escribe a **el negocio que presta el servicio** (no a Apúntalo) y sigue sus indicaciones sobre condiciones y cobro.  Si es una **solicitud de pago pendiente**, cancelarla **no devuelve dinero** (es solo retirar la solicitud, no un reembolso).  ¿Quieres cancelar una cita concreta o una suscripción? CONFIANZA: **0.8**
- **nemotron-3-nano:4b** (0.63 s): ¿A quién escribo si quiero cancelar una cita o pedir una devolución?   CONFIANZA: 1
- **llama3.2:3b** (0.15 s): NO_LO_SE
- **granite4:3b** (0.47 s): Quiero cancelar una cita. ¿Es una solicitud de pago o un pago recibido? CONFIANZA: 0.9

## AYUDA-025 · Quiero conectar el calendario de mi agenda.

**Esperado (responder):** En Agendas > Datos busca Google Calendar, pulsa Conectar Google Calendar o Continuar con Google, autoriza y comprueba una cita en ambos calendarios.

Fragmentos: `ayuda/10-google-calendar/sincronizacion.md#profesionales`, `ayuda/18-ayuda/ayuda.md#a-quien-escribo-si-quiero-cambiar-una-cita-o-pedir-una-devolucion`, `ayuda/10-google-calendar/sincronizacion.md#conectar-calendar-importa-los-clientes-de-mi-telefono`

- **qwen3.5:0.8b** (0.19 s): NO_LO_SE CONFIANZA: 1/1
- **qwen3.5:2b** (0.98 s): Para conectar tu calendario, debes ir a **Google Calendar**, pulsar **Conectar Google Calendar** o **Continuar con Google**, autorizar el permiso y comprobar que la cuenta esté conectada. Las citas de Apúntalo se reflejarán en ese calendario.  CONFIANZA: 0.95
- **qwen3.5:4b** (1.88 s): Para conectar tu calendario, abre **Agendas**, selecciona la agenda y entra en **Datos**. Allí pulsa **Conectar Google Calendar** o **Continuar con Google**, autoriza el permiso y comprueba que la cuenta aparezca conectada. Se creará un calendario llamado "Apúntalo agenda" seguido del nombre de tu agenda, donde se reflejarán las citas y eventos.  CONFIANZA: 1
- **gemma4:e2b** (0.6 s): Para conectar Google Calendar, abre **Agendas**, selecciona la agenda y entra en **Datos**. Luego, en **Google Calendar**, pulsa **Conectar Google Calendar** o **Continuar con Google**. Autoriza el permiso de calendario y comprueba que la cuenta aparezca conectada. Si se te pide volver a autorizar, reconecta con la cuenta que corresponde. CONFIANZA: 1
- **ministral-3:3b** (1.82 s): Para conectar el calendario de tu agenda con **Apúntalo**, sigue estos pasos: 1. Ve a **Google Calendar** > **Profesionales**. 2. Selecciona tu agenda y entra en **Datos**. 3. Conecta tu calendario con Google (autoriza permisos) y verifica que aparezca la cuenta vinculada.  El calendario creado en Google se llamará **"Apúntalo agenda" + nombre de tu agenda**. Revisa citas y eventos en ambos antes de confirmar.  **¿Quieres saber cómo desconectar o qué hacer con cancelaciones?** CONFIANZA: 0.9
- **nemotron-3-nano:4b** (0.5 s): NO_LO_SE. CONFIANZA: 0
- **llama3.2:3b** (1.56 s): Para conectar el calendario de tu agenda, sigue estos pasos:  1. Abre **Agendas**, selecciona la agenda y entra en **Datos**. 2. En **Google Calendar**, pulsa **Conectar Google Calendar** o **Continuar con Google**. 3. Autoriza el permiso de calendario y comprueba que la cuenta aparezca conectada. Si se pide volver a autorizar, reconecta con la cuenta que corresponde. 4. Comprueba una cita y un evento en ambos calendarios después de conectar.  CONFIANZA: 1
- **granite4:3b** (1.75 s): Para conectar el calendario de tu agenda, sigue estos pasos:  1. Abre **Agendas**, selecciona la agenda y entra en **Datos**. 2. En **Google Calendar**, pulsa **Conectar Google Calendar** o **Continuar con Google**. 3. Autoriza el permiso de calendario y comprueba que la cuenta aparezca conectada. Si se pide volver a autorizar, reconecta con la cuenta que corresponde. 4. Comprueba una cita y un evento en ambos calendarios después de conectar.  CONFIANZA: 0.9

## AYUDA-031 · Quiero salir de la lista de espera como cliente.

**Esperado (responder):** Abre Mi lista de espera y usa Salir de la lista para la solicitud correspondiente.

Fragmentos: `ayuda/11-lista-de-espera/lista.md#ofertas-para-el-cliente`, `ayuda/11-lista-de-espera/lista.md`, `ayuda/11-lista-de-espera/lista.md#puedo-anadir-una-solicitud-desde-la-ficha-del-cliente`

- **qwen3.5:0.8b** (0.17 s): NO_LO_SE CONFIANZA: 0.9
- **qwen3.5:2b** (0.43 s): Sí, puedes salir de la lista de espera desde "Mi lista de espera".  CONFIANZA: 1
- **qwen3.5:4b** (0.98 s): Para salir de la lista de espera como cliente, debes pulsar el botón **Salir de la lista** desde la sección **Mi lista de espera**.  CONFIANZA: 1.0
- **gemma4:e2b** (0.3 s): Puede usar **Salir de la lista** desde **Mi lista de espera**. CONFIANZA: 1
- **ministral-3:3b** (0.53 s): Sí, puedes salir de la lista de espera desde **"Mi lista de espera"** en la página de reserva.  **CONFIANZA:** 1
- **nemotron-3-nano:4b** (0.47 s): NO_LO_SE CONFIANZA: 0
- **llama3.2:3b** (0.15 s): NO_LO_SE
- **granite4:3b** (0.64 s): Para salir de la lista de espera como cliente, debes ir a **Mi lista de espera** y seleccionar la opción **Salir de la lista**. CONFIANZA: 0.9

## AYUDA-034 · ¿Cancelar una cita devuelve siempre la sesión del bono?

**Esperado (responder):** No siempre. La cancelación dentro del plazo gratuito devuelve las sesiones; una cancelación tardía protegida puede conservarlas. El negocio debe revisar la decisión mostrada al archivar.

Fragmentos: `ayuda/19-recorridos/cancelar-con-pago-o-bono.md#cancelar-una-solicitud-de-pago-devuelve-dinero`, `ayuda/19-recorridos/cancelar-con-pago-o-bono.md#revisar-antes-de-cancelar`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#como-se-cuenta-una-cita-pagada-con-un-bono`

- **qwen3.5:0.8b** (0.21 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.8 s): No, cancelar una cita no devuelve automáticamente el bono; solo cancela la solicitud pendiente. Si hay un pago o garantía asociado, se debe seguir el proceso de reembolso correspondiente.  CONFIANZA: 0.95
- **qwen3.5:4b** (2.0 s): No, cancelar una cita no devuelve siempre la sesión del bono. Según los fragmentos, devolver una sesión y reembolsar dinero son acciones diferentes, y el informe de actividad no reparte automáticamente el importe del bono entre sus sesiones ni resta la cobertura del bono para convertirlo en dinero cobrado. Además, si la cita combina bono y dinero, devolver uno no devuelve automáticamente al otro.  CONFIANZA: 0.9
- **gemma4:e2b** (0.34 s): NO_LO_SE CONFIANZA: 1.0
- **ministral-3:3b** (1.84 s): No, **cancelar una cita no devuelve automáticamente la sesión del bono**. Solo se devuelve lo que hayas pagado en efectivo o que no esté vinculado al bono. Si la cita usa sesiones de un bono, debes revisar si hay combinaciones (ej. parte del servicio cubierto por bono y otra parte pagada).  **Ejemplo:** Si el bono cubre el 100% del servicio (30 €), cancelar no devolverá el bono, solo el dinero pagado por el servicio.  CONFIANZA: **0.7**
- **nemotron-3-nano:4b** (0.92 s): NO_LA_SESIÓN_DE_BONO_NO_SE_VUELVE_AUTOMÁTICAMENTE. CONFIANZA: 1
- **llama3.2:3b** (0.23 s): NO_LO_SE
- **granite4:3b** (0.66 s): Cancelar una cita no devuelve automáticamente la sesión del bono. Es una acción diferente al reembolso de dinero. CONFIANZA: 0.9

## AYUDA-040 · ¿Cómo devuelvo un cobro?

**Esperado (responder):** Con acceso de propietario o administrador a Cobros, abre Cobros de la cita, usa Reembolsar cuando esté disponible, revisa el importe y confirma. Comprueba si está en curso o realizado.

Fragmentos: `ayuda/13-cobros-a-clientes/cobros.md#un-enlace-enviado-demuestra-que-el-cliente-ha-pagado`, `ayuda/19-recorridos/cliente-dice-que-ha-pagado.md#si-faltan-controles`, `ayuda/18-ayuda/ayuda.md#a-quien-escribo-si-quiero-cambiar-una-cita-o-pedir-una-devolucion`

- **qwen3.5:0.8b** (0.18 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.53 s): No se puede devolver un cobro directamente desde la aplicación; debes contactar al negocio para gestionar la devolución. CONFIANZA: 0.5
- **qwen3.5:4b** (1.0 s): Para devolver un cobro, debes escribir al negocio que presta el servicio, ya que es quien debe gestionar la devolución y decidir sobre el cobro.  CONFIANZA: 0.8
- **gemma4:e2b** (0.25 s): NO_LO_SE CONFIANZA: 0.0
- **ministral-3:3b** (1.83 s): Para devolver un cobro, **no puedes hacerlo directamente en Apúntalo**. Debes seguir estos pasos según el estado del pago: 1. Revisa el estado del cobro en tu panel. 2. Si el pago está en duda, usa **"Actualizar cobros"** antes de enviar una solicitud. 3. Si el negocio lo permite, usa **"Reembolsar"** (solo si tienes permisos y el estado lo permite).  El negocio debe gestionar la devolución de forma externa a la plataforma.  **¿Quieres saber cómo gestionar la devolución desde el negocio?** CONFIANZA: **0.8**
- **nemotron-3-nano:4b** (0.54 s): NO_LO_SE   CONFIANZA: 0
- **llama3.2:3b** (0.37 s): NO_LO_SE.  Pregunta: ¿Qué debo hacer si no puedo gestionar el cobro?
- **granite4:3b** (0.5 s): Para devolver un cobro, debes usar la opción **Reembolsar**. CONFIANZA: 0.9

## AYUDA-045 · ¿Cancelar la suscripción borra mi negocio?

**Esperado (responder):** Cancelar la suscripción y eliminar el negocio son acciones diferentes. Revisa la fecha de finalización del plan; la eliminación del negocio tiene su propio proceso.

Fragmentos: `ayuda/14-precios-y-suscripcion/suscripcion.md#cancelar-el-plan-cancela-tambien-las-citas`, `ayuda/02-negocio/datos-y-pagina.md#cancelar-la-suscripcion-elimina-el-negocio`, `ayuda/14-precios-y-suscripcion/suscripcion.md#cancelar-o-reactivar`

- **qwen3.5:0.8b** (0.18 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.72 s): No, cancelar la suscripción no elimina tu negocio. Solo cancela las citas y debes revisar si el plan vuelve a estar activo o si queda en modo solo lectura. CONFIANZA: 0.95
- **qwen3.5:4b** (2.03 s): No, cancelar la suscripción no borra ni elimina tu negocio. Según los fragmentos, cancelar la suscripción no es una orden de eliminar el negocio; para ello se debe utilizar la opción "Eliminar cuenta", que inicia un proceso diferente y exige revisar las consecuencias. En cambio, al cancelar la suscripción, solo se detiene la renovación del plan (aplicándose al final del periodo), aunque en modo solo lectura puedas consultar la agenda.  CONFIANZA: 1
- **gemma4:e2b** (0.34 s): No son la misma operación. Eliminar cuenta inicia la eliminación del negocio y exige revisar sus propias consecuencias. CONFIANZA: 1.0
- **ministral-3:3b** (0.81 s): No, cancelar la suscripción **no borra tu negocio**. Solo detiene el acceso a funciones como crear/editar citas, pero las reservas online siguen activas hasta el final del periodo.  CONFIANZA: **0.9**
- **nemotron-3-nano:4b** (0.59 s): NO_LO_SE. CONFIANZA: 1
- **llama3.2:3b** (0.39 s): NO_LO_SE.  Pregunta: ¿Qué sucede con el negocio al cancelar la suscripción?
- **granite4:3b** (0.66 s): No, cancelar la suscripción no borra el negocio. Eliminar la cuenta es una operación diferente que requiere revisar las consecuencias.  CONFIANZA: 1

## AYUDA-048 · ¿Dónde descargo la factura de Apúntalo?

**Esperado (responder):** En Mi negocio > Suscripción > Gestionar suscripción abre Facturas y elige Ver factura o Descargar factura. Si aparece PDF no disponible, vuelve a consultar más tarde. Debe consultarlo el propietario del negocio.

Fragmentos: `ayuda/14-precios-y-suscripcion/pagos-y-complementos.md#por-que-no-puedo-descargar-una-factura`, `ayuda/14-precios-y-suscripcion/pagos-y-complementos.md#cambiar-la-tarjeta-o-reintentar-un-pago`, `ayuda/14-precios-y-suscripcion/suscripcion.md#datos-facturas-y-pago-pendiente`

- **qwen3.5:0.8b** (0.19 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.81 s): Para descargar una factura, debes ir a **Facturas**, elegir **Ver factura** o **Descargar factura**. Si aparece el mensaje "PDF no disponible", vuelve a consultar más tarde.  CONFIANZA: 0.95
- **qwen3.5:4b** (1.69 s): Para descargar la factura de Apúntalo, ve a **Pagos y facturas**, selecciona la entrada correspondiente y pulsa **Descargar factura**. Si aparece el mensaje **"PDF no disponible"**, significa que aún no hay un archivo descargable para esa entrada; en ese caso, debes volver a consultarla más tarde.  CONFIANZA: 0.9
- **gemma4:e2b** (0.4 s): Para descargar una factura, abre **Facturas**, elige **Ver factura** o **Descargar factura** cuando el PDF esté disponible. CONFIANZA: 1.0
- **ministral-3:3b** (1.4 s): En la sección **"Facturas"** dentro de **"Pagos y facturas"**, selecciona **"Ver factura"** o **"Descargar factura"** (solo estará disponible si el PDF está disponible).  Si ves **"PDF no disponible"**, vuelve a consultarla más tarde.  **¿Quieres confirmar si la factura está en "Pagos y facturas" o en "Facturas" dentro de otra sección?** CONFIANZA: 0.5
- **nemotron-3-nano:4b** (0.62 s): NO_LO_SE   CONFIANZA: 0
- **llama3.2:3b** (0.21 s): NO_LO_SE
- **granite4:3b** (0.78 s): Descargar factura de Apúntalo: En **Facturas**, elige **Descargar factura**. Si indica **PDF no disponible**, vuelve a consultar más tarde. CONFIANZA: 0.9

## AYUDA-053 · ¿Qué significa ticket medio por cita?

**Esperado (responder):** Es la facturación registrada dividida entre las citas realizadas. Por ejemplo, 200 euros en 10 citas dan 20 euros por cita; no expresa beneficio.

Fragmentos: `ayuda/19-recorridos/revisar-el-mes.md#leer-los-resultados-en-orden`, `ayuda/15-informes/informe-mensual.md#interpretar-las-cifras`, `ayuda/19-recorridos/cliente-dice-que-ha-pagado.md#que-hacer-segun-el-resultado`

- **qwen3.5:0.8b** (0.32 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (1.1 s): El ticket medio por cita es la facturación registrada dividida entre el número total de citas realizadas, sin incluir las ausencias ni los servicios con precio cero. Por ejemplo, si se facturaron 200 € en 10 citas, el ticket medio es de 20 € por cita.
- **qwen3.5:4b** (2.15 s): El **ticket medio por cita** es la facturación registrada dividida entre el número de citas realizadas. Por ejemplo, si hay 200 € en facturación y 10 citas realizadas, el ticket medio es de 20 € por cita. Este dato no representa el beneficio ni el dinero cobrado, sino que relaciona la facturación con las citas completadas.  CONFIANZA: 1
- **gemma4:e2b** (0.69 s): El ticket medio por cita divide la facturación entre las citas realizadas. Por ejemplo, 600 € y 20 citas dan 30 € por cita; no son 30 € de beneficio. CONFIANZA: 1
- **ministral-3:3b** (1.17 s): Es el importe **facturado por cada cita realizada**, calculado dividiendo la facturación total entre el número de citas completadas (ejemplo: 200 € / 10 citas = 20 € por cita).  CONFIANZA: **1**
- **nemotron-3-nano:4b** (1.49 s): El ticket medio por cita es el importe de facturación dividido entre el número de citas realizadas. Por ejemplo, 200 € en 10 citas equivalen a 20 € por cita. CONFIANZA: 1
- **llama3.2:3b** (1.05 s): El ticket medio por cita es la facturación registrada dividida entre las citas realizadas. Por ejemplo, si se registró una facturación de 200 € en 10 citas, el ticket medio por cita sería de 20 € por cita.
- **granite4:3b** (1.56 s): El ticket medio por cita es el importe promedio que se factura por cada cita realizada. Se calcula dividiendo la facturación total registrada entre el número de citas realizadas. Por ejemplo, si se ha registrado una facturación de 200 euros en 10 citas, el ticket medio por cita sería de 20 euros. CONFIANZA: 1.

## AYUDA-058 · No me llega el código para entrar como cliente.

**Esperado (responder):** Revisa el número y prueba SMS si se ofrece; si abriste el enlace dentro de Instagram, prueba Safari o Chrome. Respeta el tiempo indicado tras demasiados intentos.

Fragmentos: `ayuda/17-guia-del-cliente/reservar.md#entrar-y-reservar`, `ayuda/14-precios-y-suscripcion/pagos-y-complementos.md#aplicar-un-cupon`, `ayuda/17-guia-del-cliente/reservar.md`

- **qwen3.5:0.8b** (0.23 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (1.04 s): Si no recibes el código, revisa si estás usando WhatsApp o SMS y prueba la alternativa de SMS si aparece. Si abriste el enlace dentro de Instagram y falla el acceso, ábrelo en Safari o Chrome. Espera el tiempo indicado si has hecho demasiados intentos.  CONFIANZA: 0
- **qwen3.5:4b** (1.57 s): Si no recibes el código, revisa el número de móvil introducido y prueba la alternativa de SMS si aparece. Si abriste el enlace desde Instagram y falla el acceso, ábrelo en Safari o Chrome. Espera el tiempo indicado si has realizado demasiados intentos.  CONFIANZA: 1
- **gemma4:e2b** (0.32 s): Si no llega el código, revisa el número y prueba la alternativa de SMS si aparece. CONFIANZA: 1.0
- **ministral-3:3b** (0.71 s): ¿Has introducido correctamente el número de móvil que aparece en tu reserva? ¿Has probado recibirlo por SMS en lugar de WhatsApp?  CONFIANZA: 0
- **nemotron-3-nano:4b** (0.67 s): NO_LO_SE   CONFIANZA: 0
- **llama3.2:3b** (0.23 s): NO_LO_SE
- **granite4:3b** (0.72 s): ¿Has abierto el enlace dentro de Instagram o has abierto el enlace en un navegador como Safari o Chrome? CONFIANZA: 0.8

## AYUDA-069 · Mi servicio cuesta 60 €. Recibí 15 € de señal online y 45 € en efectivo. ¿Qué debería contar como cobrado online en este ejemplo?

**Esperado (responder):** 15 €, si no hay otros pagos online. Los 45 € en efectivo se comprueban en su registro correspondiente; no se añaden automáticamente al resumen online. El precio del servicio sigue siendo 60 €.

Fragmentos: `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#ejemplos-para-no-contar-dos-veces`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#puedo-dar-por-cobrado-el-resto-porque-la-reserva-tiene-una-senal`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md`

- **qwen3.5:0.8b** (0.22 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (0.81 s): Si el precio es de 60 €, la señal de 15 € y el resto de 45 € son cifras distintas, por lo que el total a considerar es de 60 €. CONFIANZA: 1
- **qwen3.5:4b** (2.66 s): En este caso, el importe que debes contar como "Cobrado online" es **15 €**.  La señal de 15 € se registra en la columna "Cobrado online". Los 45 € pagados en efectivo no se añaden automáticamente a este resumen; deben revisarse en su registro correspondiente. Por lo tanto, el total cobrado online sigue siendo solo la cantidad ingresada por ese método (la señal), sin duplicar ni sumar los pagos de otro tipo para obtener un total ficticio de 60 € en esta columna específica.  CONFIANZA: 1
- **gemma4:e2b** (0.36 s): 60 €  CONFIANZA: 1.0
- **ministral-3:3b** (0.97 s): Según los ejemplos, en tu caso **solo debes contar los 15 € de señal online** como cobrado online. El 45 € en efectivo no se suma automáticamente al resumen online.  CONFIANZA: 0.9
- **nemotron-3-nano:4b** (0.78 s): El cobrado online sería 15 €. CONFIANZA: 1
- **llama3.2:3b** (0.49 s): NO_LO_SE.  Pregunta: ¿Cuál es el importe cobrado online en este ejemplo?
- **granite4:3b** (0.79 s): Contaría 15 € como cobrado online. El resto de 45 € pagado en efectivo no se cuenta como cobrado online. CONFIANZA: 0.9

## AYUDA-080 · He subido un servicio de 30 € a 35 €. ¿Las citas que ya estaban creadas pasan a 35 €?

**Esperado (responder):** No automáticamente. Conservan el precio guardado en la cita. Si has acordado cambiar una reserva concreta, abre esa cita y revisa su precio y sus cobros o bonos antes de editarla.

Fragmentos: `ayuda/21-cambios-y-cifras/cambios-en-citas-existentes.md#subir-un-precio-o-cambiar-una-duracion`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#que-fecha-corresponde-a-cada-cifra`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#como-se-cuenta-una-cita-pagada-con-un-bono`

- **qwen3.5:0.8b** (0.29 s): NO_LO_SE CONFIANZA: 1/1
- **qwen3.5:2b** (1.11 s): No, las citas existentes no cambian automáticamente de precio. Solo se actualizan si se modifica expresamente la reserva anterior o se crea una nueva cita con ese nuevo precio. La aplicación no cambia por sí sola el dinero cobrado ni crea devoluciones al modificar un catálogo.  CONFIANZA: 0.95
- **qwen3.5:4b** (1.47 s): No, las citas existentes no pasan automáticamente al nuevo precio (35 €) solo por haber modificado el catálogo. Solo si editas expresamente cada reserva individualmente para cambiar su importe se actualizará.  CONFIANZA: 1
- **gemma4:e2b** (0.7 s): No, la reserva que ya tenía guardados 30 € no pasa a 35 € solo por cambiar el catálogo. Una nueva cita puede tomar el precio de 35 €. Si editas expresamente la reserva anterior para cobrar otro importe, revisa y confirma esa operación por separado. CONFIANZA: 1.0
- **ministral-3:3b** (1.14 s): No, las citas existentes **no** pasan automáticamente a 35 € al subir el precio del servicio a 35 €. Debes **editar manualmente** cada cita que ya tenga ese servicio para actualizar su precio.  CONFIANZA: **0**
- **nemotron-3-nano:4b** (0.85 s): NO_LO_SE. CONFIANZA: 0
- **llama3.2:3b** (0.39 s): NO_LO_SE
- **granite4:3b** (1.4 s): No, las citas que ya estaban creadas no pasan a 35 € solo por cambiar el catálogo. Una nueva cita puede tomar el precio de 35 €. Si editas expresamente la reserva anterior para cobrar otro importe, revisa y confirma esa operación por separado. CONFIANZA: 0.9

## AYUDA-098 · Moví una sesión recurrente al jueves. ¿Las siguientes ya quedan los jueves?

**Esperado (responder):** Cambiar una cita concreta no cambia por sí mismo toda la pauta. Para cambiar las siguientes, abre Cita recurrente > Abrir en Copilot, indica desde qué fecha y revisa la propuesta, incluidos los ajustes particulares que se conserven.

Fragmentos: `ayuda/07-agenda-y-citas/citas.md#una-cita-recurrente-se-reserva-entera-desde-el-primer-dia`, `ayuda/19-recorridos/gestionar-citas-recurrentes.md#crear-una-pauta`, `ayuda/19-recorridos/gestionar-citas-recurrentes.md#cambiar-solo-una-cita`

- **qwen3.5:0.8b** (0.24 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.86 s): No, mover una cita a un día específico no garantiza que las siguientes se mantengan en ese mismo día. Solo se conserva lo que haya sido movido manualmente hasta el momento del cambio de pauta.  CONFIANZA: 0.95
- **qwen3.5:4b** (1.46 s): No, mover una sola sesión no implica que las siguientes se repitan con ese nuevo día. Para cambiar la pauta general, debes modificarla explícitamente; de lo contrario, solo esa cita específica tendrá el cambio aplicado.  CONFIANZA: 0.9
- **gemma4:e2b** (0.34 s): NO_LO_SE CONFIANZA: 0.0
- **ministral-3:3b** (1.48 s): No, las siguientes citas **no** se ajustan automáticamente al cambio de día a jueves. Solo la sesión que modificaste se adapta a esa fecha. Las citas posteriores mantendrán su frecuencia original (ej. cada semana) a menos que se modifique la pauta completa.  **¿Quieres confirmar si la pauta original seguía siendo semanal o si había otro intervalo?** CONFIANZA: 0.
- **nemotron-3-nano:4b** (0.75 s): NO_LO_SE. CONFIANZA: 0
- **llama3.2:3b** (0.29 s): NO_LO_SE
- **granite4:3b** (1.14 s): Las siguientes citas recurrentes se crearán en los jueves, pero solo si la propuesta indica que se conservan los cambios realizados. Comprueba la propuesta para asegurarte de que las citas se ajusten al nuevo día de la semana. CONFIANZA: 0.8

## TRAMPA-1 · ¿Tenéis integración con Holded para facturar?

**Esperado (abstenerse):** NO_LO_SE

Fragmentos: `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#estos-importes-sustituyen-mi-facturacion-o-contabilidad`, `ayuda/13-cobros-a-clientes/cobros.md#preparar-los-cobros-online`

- **qwen3.5:0.8b** (0.21 s): NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (0.21 s): NO_LO_SE
- **qwen3.5:4b** (0.47 s): NO_LO_SE
- **gemma4:e2b** (0.29 s): NO_LO_SE CONFIANZA: 1.0
- **ministral-3:3b** (0.57 s): NO_LO_SE.  ¿Quieres saber si hay integración con algún otro servicio de facturación? CONFIANZA: 0
- **nemotron-3-nano:4b** (0.59 s): NO_LO_SE CONFIANZA: 0
- **llama3.2:3b** (0.51 s): NO_LO_SE.  Pregunta: ¿Qué tipo de comisión cobra Apúntalo en relación con los cobros a clientes?
- **granite4:3b** (0.53 s): No tengo información sobre la integración con Holded para facturar. CONFIANZA: 0.3

## TRAMPA-2 · ¿Hay app de Apúntalo para Android TV?

**Esperado (abstenerse):** NO_LO_SE

Fragmentos: `ayuda/01-primeros-pasos/empezar.md#moverse-e-instalar`, `ayuda/01-primeros-pasos/empezar.md#por-que-no-veo-instalar-aplicacion`, `ayuda/10-google-calendar/sincronizacion.md#desconectar-calendar-borra-mis-citas-de-apuntalo`

- **qwen3.5:0.8b** (0.23 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.48 s): No hay información sobre una aplicación específica para Android TV en los fragmentos proporcionados.  CONFIANZA: 0.5
- **qwen3.5:4b** (0.57 s): NO_LO_SE CONFIANZA: 0
- **gemma4:e2b** (0.28 s): NO_LO_SE CONFIANZA: 1.0
- **ministral-3:3b** (0.59 s): NO_LO_SE.  ¿Quieres saber si hay una versión específica para dispositivos Android TV o si solo se usa la versión web? CONFIANZA: 0
- **nemotron-3-nano:4b** (0.66 s): NO_LO_SE CONFIANZA: 0
- **llama3.2:3b** (0.21 s): NO_LO_SE
- **granite4:3b** (0.37 s): NO_LO_SE CONFIANZA: 0.2

## TRAMPA-3 · ¿Apúntalo ya cumple con Verifactu?

**Esperado (abstenerse):** NO_LO_SE

Fragmentos: `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#que-fecha-corresponde-a-cada-cifra`, `ayuda/10-google-calendar/sincronizacion.md#desconectar-calendar-borra-mis-citas-de-apuntalo`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#como-se-cuenta-una-cita-pagada-con-un-bono`

- **qwen3.5:0.8b** (0.26 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.46 s): No, los fragmentos no responden a esta pregunta específica.  CONFIANZA: 0
- **qwen3.5:4b** (0.57 s): NO_LO_SE
- **gemma4:e2b** (0.37 s): NO_LO_SE CONFIANZA: 1.0
- **ministral-3:3b** (0.98 s): NO_LO_SE.  ¿Podrías confirmar si se trata de algún requisito específico de facturación o cumplimiento normativo que mencionan en los fragmentos? (Ej: facturación electrónica, registro de cobros, etc.).  CONFIANZA: 0
- **nemotron-3-nano:4b** (0.75 s): NO_LO_SE CONFIANZA: 0
- **llama3.2:3b** (0.33 s): NO_LO_SE
- **granite4:3b** (0.61 s): No hay información sobre Verifactu en los fragmentos proporcionados. CONFIANZA: 0.

## TRAMPA-4 · ¿Mis clientes pueden pagar la señal con Bizum?

**Esperado (abstenerse):** NO_LO_SE

Fragmentos: `ayuda/20-guias-visuales/pantallas-comentadas.md#confirmar-una-reserva-con-senal`, `ayuda/21-cambios-y-cifras/como-se-cuentan-los-importes.md#puedo-dar-por-cobrado-el-resto-porque-la-reserva-tiene-una-senal`, `ayuda/05-servicios/servicios.md#por-que-no-aparece-ordenar`

- **qwen3.5:0.8b** (0.27 s): Sí, los clientes pueden pagar la señal con Bizum. NO_LO_SE CONFIANZA: 0.8
- **qwen3.5:2b** (1.13 s): Sí, según el fragmento [2], puedes dar por cobrado el resto si el cliente ha recibido el pago total y se han verificado los servicios y bonos. Sin embargo, debes comprobar cada pago individualmente para asegurar que todos los montos (servicios, señal e impuestos) están correctamente registrados en la reserva.  CONFIANZA: 0.95
- **qwen3.5:4b** (0.46 s): NO_LO_SE
- **gemma4:e2b** (0.28 s): NO_LO_SE CONFIANZA: 0.0
- **ministral-3:3b** (0.64 s): NO_LO_SE.  ¿Quieres saber si la señal de 15 € puede pagarse con Bizum en el proceso de reserva? CONFIANZA: 0
- **nemotron-3-nano:4b** (0.65 s): NO_LO_SE   CONFIANZA: 0
- **llama3.2:3b** (0.24 s): NO_LO_SE
- **granite4:3b** (0.82 s): Los clientes pueden pagar la señal con Bizum si el negocio lo permite y la ordenación está disponible para ellos. No hay una respuesta específica en los fragmentos proporcionados. CONFIANZA: 0.3

## TRAMPA-5 · ¿Se puede conectar Apúntalo con Shopify?

**Esperado (abstenerse):** NO_LO_SE

Fragmentos: `ayuda/10-google-calendar/sincronizacion.md#profesionales`, `ayuda/06-clientes/clientes.md#se-importaran-todos-mis-contactos-al-conectar-la-sincronizacion`, `ayuda/06-clientes/clientes.md#importar-contactos-de-google`

- **qwen3.5:0.8b** (0.26 s): NO_LO_SE CONFIANZA: 0.5
- **qwen3.5:2b** (0.28 s): NO_LO_SE.
- **qwen3.5:4b** (0.72 s): NO_LO_SE CONFIANZA: 0
- **gemma4:e2b** (0.38 s): NO_LO_SE CONFIANZA: 1.0
- **ministral-3:3b** (0.67 s): NO_LO_SE.  ¿Quieres saber si hay alguna conexión entre **Apúntalo** y otra plataforma como **Shopify**? CONFIANZA: 0
- **nemotron-3-nano:4b** (0.74 s): NO_LO_SE CONFIANZA: 0
- **llama3.2:3b** (0.23 s): NO_LO_SE
- **granite4:3b** (0.28 s): No_LO_SE.
