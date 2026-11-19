# Clientes y contactos

La ficha de cliente reúne sus datos, notas y citas. El acceso al listado depende de los permisos concedidos por el negocio.

## Crear, buscar y editar

1. Abre **Clientes** y busca por los datos disponibles en la lista, o elige crear un cliente.
2. Introduce sus datos y guarda. Comprueba el teléfono: sin él no podrá recibir recordatorios de cita.
3. Abre la ficha para consultar **Datos del cliente**, **Notas personales**, **Notas internas** y las citas mostradas. Edita los datos y guarda cuando sea necesario.
4. La opción **Puede pedir citas** controla si ese cliente puede reservar. Revisa su estado si no puede hacerlo.

Si aparece un aviso de teléfono duplicado, busca primero el contacto existente y revisa sus datos antes de crear otro. Para eliminar un cliente usa la acción de eliminación en su ficha y confirma. Si tiene citas o cobros pendientes, resuélvelos antes; una cita cancelada puede seguir visible en su historial.

## Importar contactos de Google

En **Clientes**, elige **Importar**, continúa con Google y autoriza el acceso. Busca y selecciona los contactos que quieras y pulsa **Importar seleccionados**. Comprueba el resultado; si la importación es parcial, puedes reintentar lo que falta. Si la ventana no se abre, permite ventanas emergentes; si caducó la autorización, vuelve a conectar.

Importar copia los contactos elegidos. La sincronización de Google Contacts es una opción distinta, cuyo acceso puede concederse en **Usuarios con acceso** mediante **Configurar Google Contacts**. En **Clientes**, pulsa **Personalizar clientes** y abre **Contactos de Google**: pulsa **Conectar**, autoriza la cuenta y comprueba que figure **Conectado**. Apúntalo envía nombres y teléfonos; los cambios de nombre se sincronizan en ambos sentidos. No importa automáticamente otros contactos ni borra contactos de Google. Para cambiar la cuenta usa **Cambiar cuenta**; para detenerlo, **Desconectar**. La desconexión conserva los contactos y la etiqueta de Google. Si aparece **Vuelve a conectar Google**, pulsa **Volver a autorizar**. Google Calendar gestiona eventos, no sustituye la importación de clientes; consulta [Google Calendar](../10-google-calendar/sincronizacion.md).

## Añadir información propia a las fichas

Cuando el negocio dispone de campos personalizados o fichas asociadas, el propietario y los administradores pueden configurarlos desde **Clientes > Personalizar clientes** (botón de tres puntos).

1. En **Campos del cliente**, pulsa **Añadir**. Escribe el nombre, elige **Texto**, **Número** o **Fecha** y pulsa **Crear campo**. Por ejemplo, puedes crear «Preferencia de contacto» como texto. **Cumpleaños** tiene su propia opción para añadirlo cuando está disponible.
2. Vuelve a la ficha de un cliente para completar esa información. Si un campo vacío no se ve, revisa **Más** o **Mostrar campos vacíos**.
3. Si necesitas información separada para una mascota o un coche de un mismo cliente, usa **Fichas asociadas > Nueva**, escribe un nombre singular, como «Mascota», y pulsa **Crear ficha**. Después configura sus campos y añade las fichas concretas desde el cliente.

Cuando aparece **Etiquetas** en la ficha, usa **Buscar o crear etiqueta** para elegir una existente o crearla. Quitar una etiqueta de una ficha no equivale a eliminar el cliente.

Si no ves estas opciones, comprueba primero con el propietario si están disponibles en el negocio y si tu cuenta puede configurarlas. Poder editar datos de un cliente no implica poder cambiar los campos de todas las fichas. La conexión de **Contactos de Google**, aunque comparte la pantalla de personalización, tiene su propio permiso.

## Preguntas frecuentes y opciones que no aparecen

### ¿Por qué no veo «Clientes» en el menú?
El propietario y los administradores tienen acceso al listado. En una cuenta básica, el propietario puede retirar ese permiso. Pídele que lo revise en **Agendas > Usuarios con acceso**; usar otra agenda no concede por sí solo ese acceso.

### ¿Por qué puedo importar contactos, pero no configurar la sincronización?
Son funciones distintas. La sincronización de Google Contacts la configura el propietario o un administrador al que se haya concedido **Configurar Google Contacts**. Tener acceso al listado no basta para conectar o cambiar esa cuenta de Google.

### ¿Se importarán todos mis contactos al conectar la sincronización?
No. Para traer contactos elegidos a Apúntalo, usa **Importar**. La conexión de sincronización no sustituye esa selección. [Google Calendar](../10-google-calendar/sincronizacion.md) se ocupa de citas y eventos, no de importar contactos.
