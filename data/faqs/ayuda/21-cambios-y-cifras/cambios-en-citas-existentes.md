# Qué cambia en las citas existentes cuando modificas una configuración

Una cita ya creada conserva sus propios datos. Cambiar un servicio o un horario no equivale a editar todas sus citas. Sin embargo, algunos ajustes, como la antelación de recordatorios, sí pueden afectar a citas futuras existentes. Comprueba qué estás cambiando antes de guardar.

## Resumen por tipo de cambio

| Cambio | Nuevas reservas o usos | Citas y operaciones que ya existen |
|---|---|---|
| Precio o duración de un servicio | Se utiliza la configuración vigente; al crear una cita del negocio, puede proponerse la duración habitual de ese cliente. | No se cambia automáticamente el precio ni la duración guardados en cada cita. |
| Nombre de un servicio | El catálogo presenta el nuevo nombre. | Renombrar el catálogo no reescribe las citas; al editar una cita, algunos nombres pueden actualizarse. |
| Componentes de un servicio compuesto | Se usa la composición actual. Los cambios de precio o duración de una parte pueden actualizar el combo del catálogo. | Las citas ya creadas conservan su composición guardada; editar el catálogo no las reconstruye. |
| Horario, descanso o cierre de un día | Cambian los huecos que se ofrecen. | Las citas no se trasladan ni se cancelan automáticamente. |
| Agendas que ofrecen un servicio o permisos de reserva online | Cambia quién o dónde puede reservarlo. | No se reasignan ni se eliminan las citas existentes. |
| Señal, garantía o desactivación de protección | Cambian las condiciones de las nuevas reservas a las que se aplique. | Los cobros y garantías anteriores conservan sus condiciones. No se devuelven ni se cobran automáticamente por cambiar el ajuste. |
| Antelación de recordatorio o confirmaciones automáticas | Se aplica la configuración vigente. | Se revisan las citas futuras confirmadas cuyo recordatorio todavía no se ha enviado. No se vuelve a enviar por este motivo uno ya notificado. |
| Suscripción | Cambia el acceso de gestión según el estado y la fecha indicados. | Cancelar el plan no cancela las citas ni elimina el negocio. |
| Saldo, vigencia o eliminación de un bono | Puede cambiar si el bono sirve para nuevas citas. | Hay comprobaciones para proteger las citas que ya lo usan; eliminar el bono conserva esas citas y su historial. |

## Subir un precio o cambiar una duración

1. En **Servicios**, abre el servicio y modifica su precio o duración. Guarda.
2. Si querías cambiar únicamente el catálogo, no necesitas editar las citas anteriores.
3. Si también has acordado cambiar una cita existente, abre **Citas**, busca esa reserva y revisa sus servicios, duración y precio. Modifica esa cita y comprueba el resultado antes de comunicarlo al cliente.
4. Si tiene un cobro, garantía o bono, revisa además **Cobros** y el bono utilizado. La aplicación puede impedir un cambio incompatible con operaciones ya realizadas o pendientes.

**Ejemplo:** subes un servicio de 30 € a 35 €. La reserva que ya tenía guardados 30 € no pasa a 35 € solo por cambiar el catálogo. Una nueva cita puede tomar el precio de 35 €. Si editas expresamente la reserva anterior para cobrar otro importe, revisa y confirma esa operación por separado.

Cambiar el precio de una cita no modifica por sí solo el dinero que ya se cobró ni crea una devolución. Un precio, una solicitud de cobro y un pago recibido son conceptos distintos. Consulta [cobros a clientes](../13-cobros-a-clientes/cobros.md).

Al crear una cita para alguien que ya acudió, puede proponerse una duración utilizada anteriormente con ese cliente y servicio. Por eso una duración distinta de la del catálogo no demuestra que el cambio del servicio haya fallado. Comprueba el tiempo propuesto antes de guardar.

## Renombrar servicios y modificar composiciones

Las citas conservan el nombre y los servicios con los que se guardaron. Cambiar el nombre del catálogo no es una orden de renombrar todo el historial. Al abrir y guardar cambios de una cita, la presentación puede recoger nombres actuales: no uses el nombre como única forma de identificar una reserva.

Si cambias el precio o la duración de un servicio que forma parte de un combo desde **Servicios**, revisa también el combo del catálogo:

- Su duración se recalcula a partir de las partes y sus descansos.
- Si el precio del combo coincidía con la suma de las partes, puede actualizarse con la nueva suma.
- Si tenía un precio diferente, se conserva ese importe personalizado.

Esto afecta al catálogo. No sustituye los servicios ni recalcula en bloque las citas compuestas ya guardadas. Si editas una de esas citas, revisa todos sus tramos, profesionales, tiempos y precio final antes de confirmar. Consulta [crear y organizar servicios](../05-servicios/servicios.md).

## Cerrar un día, cambiar horarios o retirar un profesional de un servicio

1. Cambia el horario desde **Agendas > Horarios**, el descanso desde **Agendas > Descansos** o el día concreto desde **Citas > Cambiar horario del día**, según lo que necesites.
2. Vuelve a **Citas** y revisa las reservas de las fechas afectadas.
3. Acuerda y gestiona por separado los cambios o cancelaciones necesarios. No des por avisado al cliente porque hayas cerrado el día.
4. Comprueba que la página de reservas ofrece los huecos adecuados para las nuevas citas.

**Ejemplo:** ya hay una cita el viernes a las 17:00 y cambias la jornada para terminar a las 15:00. La cita no desaparece ni se mueve sola. Hay que decidir qué hacer con ella.

Del mismo modo, desmarcar una agenda en un servicio no traslada sus reservas a otra persona. Retirar el acceso de un usuario tampoco cambia el profesional asignado a cada cita. Para una sustitución, revisa las citas y los permisos como tareas separadas.

Si modificas una cita concreta, comprueba sus profesionales, servicios, horario y condiciones de pago después del cambio. En una cita con varias partes puede haber más de una agenda implicada.

## Activar o quitar señales y garantías

Configurar **Protección de reservas** no sirve para cobrar a todas las personas que ya tenían cita. Tampoco desactivar la protección devuelve automáticamente señales ni anula garantías anteriores: esas operaciones mantienen sus condiciones.

Antes de actuar sobre una cita existente:

1. Abre la cita y entra en **Cobros**.
2. Revisa qué se solicitó, qué se recibió y si hay garantía o una operación pendiente.
3. Usa la acción específica que corresponda, como solicitar cobro o reembolsar, si tienes permiso. No repitas una operación cuyo resultado aún no esté confirmado.

Si cambias ajustes mientras un cliente está terminando una reserva, no presupongas qué condiciones está aceptando. Comprueba la cita y el cobro resultantes. Para las dudas sobre un pago concreto, sigue [el recorrido «el cliente dice que ya ha pagado»](../19-recorridos/cliente-dice-que-ha-pagado.md).

## Cambiar recordatorios: una excepción importante

Desde **Agendas > Ajustes** puedes modificar la antelación de los recordatorios y las confirmaciones automáticas. Estos cambios revisan también las citas futuras ya creadas que estén confirmadas y todavía no consten como notificadas.

- No hace falta crear otra cita para aplicar el nuevo ajuste a una cita pendiente de recordar.
- Un recordatorio ya enviado no se retira ni se vuelve a enviar automáticamente por cambiar la antelación.
- Un mensaje adicional nuevo puede aparecer al preparar próximos recordatorios; no cambia el texto que el cliente ya recibió.
- Si la cita está muy próxima, no interpretes el cambio como garantía de envío inmediato. Comprueba su estado y usa las opciones de recordatorio adicional cuando proceda.

Aquí «cita confirmada» significa que la reserva ha terminado de crearse, no que el cliente haya respondido que asistirá. Consulta [recordatorios y notificaciones](../09-recordatorios-y-notificaciones/recordatorios.md).

## Cambiar bonos, suscripción o una serie de citas

**Bonos.** Ajustar un saldo no debe confundirse con devolver una sesión de una cita concreta. Tampoco puedes acortar libremente la vigencia si deja fuera citas futuras que ya usan el bono, ni reducir el saldo por debajo de sesiones retenidas en una reserva pendiente. Si la aplicación bloquea el cambio, revisa primero esas reservas. **Eliminar bono** lo retira de nuevas citas, pero conserva las citas que ya lo usan y su historial. Consulta [bonos de sesiones](../12-bonos/bonos.md).

**Suscripción.** Cancelarla no elimina citas ni cancela cobros a clientes. Revisa la fecha de fin del periodo y el posible modo de solo lectura; cancelar el plan y eliminar el negocio son acciones distintas. Consulta [suscripción](../14-precios-y-suscripcion/suscripcion.md).

**Series.** Las citas recurrentes tienen una configuración propia. Cambiar el catálogo no equivale a cambiar el precio, duración o pauta de una serie ya preparada. Si necesitas modificar una serie, solicita expresamente el cambio y revisa desde qué fecha y a qué citas se aplicará. Una incidencia o una cita que no pueda modificarse exige comprobar el resultado, no asumir que cambió toda la serie. Consulta [gestionar citas recurrentes](../19-recorridos/gestionar-citas-recurrentes.md).

## Preguntas frecuentes

### ¿Puedo actualizar todas las citas antiguas cambiando el servicio?

No. El catálogo y las citas guardadas son distintos. Modifica solo las citas que realmente deban cambiar y revisa su impacto en cobros, bonos e informes.

### ¿Si desactivo las reservas online desaparecen las citas de mis clientes?

No. La configuración controla nuevas reservas; no sustituye la gestión de las citas existentes.

### ¿Si corrijo una cita pasada puede cambiar lo que se cuenta de ese mes?

Los cálculos de actividad utilizan los datos de las citas. Corregir precio, servicios o asistencia puede cambiar los resultados cuando vuelvan a calcularse. Un PDF que ya recibiste no se modifica dentro del correo. Consulta [informe mensual](../15-informes/informe-mensual.md) y distingue esa actividad del dinero cobrado.

### ¿Qué debo revisar antes de dar un cambio por terminado?

Comprueba una cita afectada, las fechas a las que querías aplicar el cambio y, cuando corresponda, la página de reservas, el cobro y el bono. Guardar una configuración no demuestra por sí solo que una cita se haya movido, un cliente haya recibido un mensaje o se haya devuelto dinero.
