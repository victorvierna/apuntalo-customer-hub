# Cómo se cuentan los importes: servicios, cobros, bonos e informes

Una cita puede tener un precio de 60 €, una señal pagada de 15 € y un resto de 45 € pendiente de resolver. Son cifras distintas. Para revisar tus ingresos, identifica primero qué representa cada pantalla; sumar todos esos números contaría parte del importe dos veces.

## Qué mirar según la pregunta

| Quiero saber… | Dónde mirarlo | Qué representa |
|---|---|---|
| Cuánto vale el servicio reservado | Detalle de la cita | El precio de los servicios de esa cita. No demuestra que se hayan pagado. |
| Cuánto se ha cobrado online por esa cita | Abre la cita y entra en **Cobros** | Pagos recibidos, solicitudes, garantías y devoluciones de esa cita. Comprueba el estado de cada operación. |
| Cuánto se ha cobrado online en el negocio | **Cobros > Resumen** | Los importes acumulados del negocio; no es automáticamente el total de este mes. |
| Cuánto llegará o ha llegado al banco | **Cobros > Ingresos**, cuando tu acceso lo permita | Los ingresos de la cuenta de cobros. No los sustituyas por la cifra de **Neto online**. |
| Qué actividad tuvo una agenda en un mes | Informe mensual de esa agenda | Citas, servicios y sus importes, con las condiciones explicadas en [Informe mensual](../15-informes/informe-mensual.md). |
| Cuántas sesiones le quedan a un cliente | **Clientes > ficha del cliente > Bonos** | Sesiones y movimientos del bono. Una sesión no es un nuevo cobro de dinero. |

**Cobros** requiere acceso de propietario o administrador y disponibilidad de la función. Los datos bancarios y los ingresos corresponden al titular de la cuenta. Si una cuenta agrupa varios centros, el resumen local muestra el centro que estás consultando; la gestión de la cuenta compartida puede tener un alcance mayor.

## Qué significan las tres cifras del resumen

- **Cobrado online** suma los pagos online completados: incluye señales, pagos solicitados y cargos de garantía que se hayan cobrado. No suma una solicitud sin pagar ni una tarjeta guardada como garantía.
- **Devuelto o descontado** suma reembolsos registrados y cantidades descontadas por disputas perdidas. Una disputa abierta se avisa por separado; no significa por sí sola que se haya perdido.
- **Neto online** es **Cobrado online menos Devuelto o descontado**.

**Neto online no descuenta las comisiones de Apúntalo y Stripe.** Tampoco equivale al beneficio del negocio ni al importe de una transferencia bancaria. Para revisar comisiones, ingresos y documentos, entra en los apartados correspondientes de **Cobros** con la cuenta autorizada.

Si el resumen muestra un error, usa **Reintentar**. Un resumen que no ha cargado no significa que tus cobros sean cero.

## Ejemplos para no contar dos veces

Los siguientes casos son independientes. Los importes son ficticios y suponen que no hay otras operaciones.

| Caso | Cobrado online | Devuelto o descontado | Neto online | Cómo interpretarlo |
|---|---:|---:|---:|---|
| Servicio de 60 € con señal online de 15 €; el resto aún no se ha pagado | 15 € | 0 € | 15 € | Hay 15 € cobrados online; el servicio sigue teniendo un precio de 60 €. |
| Mismo servicio: señal de 15 € y resto de 45 € pagado en efectivo | 15 € | 0 € | 15 € | El efectivo debe revisarse en su registro correspondiente. No se añade automáticamente a este resumen online. |
| Mismo servicio: señal de 15 € y otro pago online completado de 45 € | 60 € | 0 € | 60 € | Son 60 € en total, no 75 €. La señal ya forma parte de esos 60 €. |
| Tarjeta guardada como garantía hasta 30 €, sin cargo realizado | 0 € | 0 € | 0 € | Tener permiso para un posible cargo no es haber cobrado. |
| Se cobra una garantía de 20 € | 20 € | 0 € | 20 € | Cuenta el cargo completado de 20 €, no el máximo autorizado si era mayor. |
| Se reciben 60 € y después se reembolsan 15 € | 60 € | 15 € | 45 € | El cobro original permanece en Cobrado online; la devolución se resta por separado. |
| Se reciben 60 € y una disputa perdida descuenta 60 € | 60 € | 60 € | 0 € | El resumen refleja la cantidad descontada; las comisiones y otros costes se consultan aparte. |

Antes de repetir una solicitud o un reembolso, comprueba el resultado de la operación anterior. Si está sin confirmar, usa **Actualizar cobros** en la cita. Consulta [qué hacer cuando el cliente dice que ha pagado](../19-recorridos/cliente-dice-que-ha-pagado.md).

## Cómo se cuenta una cita pagada con un bono

El bono lleva un control de sesiones. Aplicar una sesión a una cita no debe interpretarse como cobrar otra vez el dinero con el que se adquirió el bono.

El informe de actividad utiliza el precio guardado en los servicios de la cita. No reparte automáticamente el importe con el que se compró el bono entre sus sesiones. Tampoco resta la cobertura del bono para convertir ese indicador en dinero cobrado ese día.

**Ejemplo:** una cita tiene un servicio de 30 € y una sesión de bono cubre ese servicio. Si la cita cumple las condiciones del informe, aporta 30 € al indicador de actividad por servicios. Consumir esa sesión no añade por sí mismo 30 € a **Cobrado online**. Son dos medidas diferentes.

Si la cita combina un servicio cubierto por bono y otro que debe pagarse, revisa ambos: sesiones utilizadas y dinero solicitado o recibido. No sumes el valor cubierto por el bono como si fuera otro pago online.

Devolver una sesión y reembolsar dinero también son acciones diferentes. Consulta [cancelar una cita con pago o bono](../19-recorridos/cancelar-con-pago-o-bono.md) antes de decidir qué devolver.

## Qué fecha corresponde a cada cifra

El informe mensual organiza la actividad por las fechas de las citas y por la agenda correspondiente. No utiliza la fecha de la señal como fecha de prestación del servicio.

En el asistente de Apúntalo, cuando se ofrece un resumen diario de cobros online, los importes corresponden al día en que Apúntalo registra el movimiento, según la zona horaria del negocio. Las solicitudes pendientes y disputas abiertas que acompañan esa tarjeta describen lo que está pendiente en ese momento; no son necesariamente solicitudes creadas ese día.

**Ejemplo:** se paga una señal el 30 de noviembre para una cita del 4 de diciembre. El cobro y la actividad de la cita pertenecen a momentos distintos. Si el movimiento de la señal queda registrado el 30 de noviembre, se verá en los cobros online de ese día; el servicio corresponde a la actividad de diciembre si cumple las condiciones del informe.

Una devolución posterior tampoco cambia la fecha del cobro original. Si se cobra en noviembre y se devuelve en diciembre, los movimientos diarios aparecerán en sus días de registro. El **Resumen** acumulado mostrará ambos importes, sin convertirlo por ello en un informe mensual.

## Por qué el informe mensual no coincide con los cobros

El informe cuenta actividad con servicios y precios válidos. Los cobros cuentan dinero online. Pueden diferir sin que haya un error:

- Una cita realizada puede pagarse en efectivo o mediante un TPV externo.
- Una señal puede recibirse antes del mes de la cita.
- Una cita cubierta por bono puede tener valor de servicio sin generar un nuevo cobro.
- Un reembolso puede ocurrir después de realizar el servicio.
- Una ausencia puede tener un cargo de garantía, aunque no cuente como cita realizada.
- El informe puede corresponder a una sola agenda y el resumen de cobros al negocio completo.

Un reembolso por sí solo no convierte una cita realizada en una ausencia ni cambia su precio. Si hay un error en los datos de actividad, revisa la cita; no cambies su precio solo para hacer que dos informes distintos coincidan.

## Preguntas frecuentes

### ¿«Neto online» es lo que gano?

No. No descuenta las comisiones ni los gastos del negocio. Sirve para relacionar cobros online con cantidades devueltas o descontadas.

### ¿Puedo dar por cobrado el resto porque la reserva tiene una señal?

No. Comprueba cada pago recibido. Que el servicio cueste 60 € y tenga 15 € de señal no demuestra que los otros 45 € estén pagados.

### ¿El resumen incluye efectivo, transferencias o mi TPV externo?

No debes interpretarlo así: **Cobrado online** refleja los pagos online gestionados por Apúntalo. Comprueba los pagos de otros medios en sus registros. Una nota como «pagado en efectivo» no equivale a una operación de cobro online.

### ¿Un reembolso en curso ya demuestra que el cliente recibió el dinero?

No. Revisa el estado final y el recibo correspondiente. No prometas una fecha bancaria basándote únicamente en que se ha solicitado el reembolso.

### ¿Puedo sumar el informe mensual y el resumen de cobros?

No para obtener ingresos totales: una misma cita puede aparecer en ambos con significados distintos y la sumarías dos veces. Revisa primero qué concepto, periodo y agenda o negocio representa cada cifra.

### ¿Estos importes sustituyen mi facturación o contabilidad?

No. Usa cada pantalla para revisar lo que describe y los documentos correspondientes para tu gestión. El precio de un servicio, un recibo de pago online y el informe de actividad no son el mismo documento. El negocio sigue siendo responsable de facturar a sus clientes.
