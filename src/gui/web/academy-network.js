(function (root) {
  'use strict';
  const { Q, L } = root.AcademyContent;
  root.AcademyCourses.push({
    id: 'redes', title: 'Redes y seguridad esencial', subtitle: 'Entiende tu conexión. Protege tu equipo.',
    category: 'Redes', level: 'Intermedio', color: 'blue', symbol: '↗', label: 'CONECTA CON CONFIANZA',
    description: 'Aprende a distinguir problemas de conexión, DNS y servicios. Conoce SSH, permisos de red y hábitos de seguridad para trabajar con más autonomía.',
    requirements: 'Conocer la terminal y los permisos básicos. Algunas consultas dependen de NetworkManager, systemd-resolved u OpenSSH instalados.',
    outcomes: ['Leer direcciones, interfaces y rutas.', 'Diagnosticar conectividad y resolución de nombres.', 'Entender puertos, HTTPS y cortafuegos.', 'Usar SSH y proteger claves y credenciales.'],
    modules: ['Tu conexión por dentro', 'Diagnóstico por capas', 'Servicios y tráfico', 'Acceso remoto seguro', 'Hábitos que protegen'],
    resources: [['Manual de OpenSSH', 'https://www.openssh.com/manual.html'], ['Manual de curl', 'https://curl.se/docs/manpage.html'], ['Documentación de NetworkManager', 'https://networkmanager.dev/docs/api/latest/nmcli.html']],
    lessons: [
      L('Interfaces, direcciones y alcance', [
        'Una interfaz conecta el sistema a una red: Ethernet, Wi-Fi o una conexión virtual. lo es la interfaz de loopback para comunicación local. Una interfaz puede tener varias direcciones. ip -br address presenta un resumen de nombres, estados y direcciones.',
        'La dirección IP identifica una interfaz dentro de un contexto de red. IPv4 usa direcciones como 192.168.1.20; IPv6 usa grupos hexadecimales. 127.0.0.1 y ::1 son loopback: apuntan al mismo equipo. Tener dirección no garantiza acceso a internet ni que DNS funcione.'
      ], 'ip -br address', 'Muestra un resumen de las interfaces y sus direcciones sin modificar la configuración.', 'Distingue la interfaz local lo de la que conecta tu equipo a la red.', [
        Q('¿Qué representa una interfaz de red?', 'Un punto de conexión físico o virtual', 'Una contraseña compartida', 'Un paquete DEB', 'Una carpeta oculta', 'Las interfaces permiten enviar y recibir tráfico.'),
        Q('¿A qué equipo apunta 127.0.0.1?', 'Al equipo local', 'Siempre al router', 'Al DNS público', 'A cualquier equipo vecino', '127.0.0.1 pertenece a loopback.'),
        Q('¿Cuál es la dirección de loopback IPv6?', '::1', '192.168.1.1', '8.8.8.8', '0.0.0.0', '::1 es el loopback de IPv6.'),
        Q('¿Qué consulta ip -br address?', 'Un resumen de interfaces y direcciones', 'El historial de contraseñas', 'Todos los paquetes instalados', 'Los archivos compartidos obligatoriamente', '-br solicita formato breve de las direcciones.'),
        Q('¿Tener una IP garantiza que internet funcione?', 'No, pueden fallar rutas, DNS o servicios', 'Sí, siempre', 'Solo si hay escritorio', 'Solo por usar IPv6', 'La dirección es una parte de la conectividad, no una prueba completa.')
      ]),
      L('Subredes y direcciones privadas', [
        'Un prefijo indica cuántos bits identifican la red. En IPv4, /24 corresponde a la máscara 255.255.255.0. En una red sencilla, 192.168.1.10/24 y 192.168.1.20/24 pertenecen a la misma subred; 192.168.2.20/24 pertenece a otra.',
        'Los rangos privados IPv4 incluyen 10.0.0.0/8, 172.16.0.0/12 y 192.168.0.0/16. No se enrutan globalmente como direcciones públicas. Una red doméstica suele usar NAT para comunicar direcciones privadas con internet. Privado no significa automáticamente seguro frente a otros equipos locales.'
      ], 'ip -4 address', 'Consulta direcciones IPv4 y sus prefijos; observa si pertenecen a un rango privado.', 'Compara 192.168.10.5/24 y 192.168.11.8/24 y decide si son de la misma subred.', [
        Q('¿Qué expresa /24 en una dirección IPv4?', '24 bits de prefijo de red', '24 equipos obligatorios', '24 megabits por segundo', 'El puerto 24', 'El prefijo cuenta bits de red.'),
        Q('¿Qué máscara corresponde a /24 en IPv4?', '255.255.255.0', '255.0.0.0', '255.255.0.0', '0.0.0.0', 'Los primeros 24 bits están activados.'),
        Q('¿Cuál pertenece a un rango IPv4 privado?', '192.168.10.8', '8.8.8.8', '1.1.1.1', '9.9.9.9', '192.168.0.0/16 es un rango privado.'),
        Q('Con /24, ¿qué pareja está en la misma subred?', '192.168.1.10 y 192.168.1.20', '192.168.1.10 y 192.168.2.20', '10.0.1.1 y 10.0.2.1', '172.16.1.1 y 172.16.2.1', 'Con /24 coinciden los primeros tres octetos de esta pareja.'),
        Q('¿Una IP privada garantiza protección ante otros equipos de la LAN?', 'No', 'Sí, cifra todo el tráfico', 'Sí, desactiva todos los puertos', 'Solo si termina en 1', 'El alcance privado no sustituye controles de seguridad.')
      ]),
      L('Rutas, gateway y DHCP', [
        'La tabla de rutas decide por dónde enviar tráfico. La ruta por defecto se utiliza cuando no existe una ruta más específica aplicable. En una red doméstica, su gateway suele ser el router. ip route muestra rutas IPv4 y ip -6 route las de IPv6.',
        'DHCP puede entregar dirección, prefijo, gateway y servidores DNS. Una dirección manual mal elegida puede entrar en conflicto con otro equipo. Antes de cambiar configuración, registra los valores actuales. Tener enlace Wi-Fi no significa haber recibido una configuración IP válida.'
      ], 'ip route\nip -6 route', 'Consulta rutas para ambas familias de direcciones.', 'Busca una línea default y distingue gateway de dirección propia del equipo.', [
        Q('¿Cuándo se usa una ruta por defecto?', 'Cuando no aplica una ruta más específica', 'Para todos los archivos locales', 'Solo antes de arrancar', 'Solo para teclado inalámbrico', 'La selección de rutas prefiere prefijos más específicos.'),
        Q('¿Qué es el gateway en una ruta doméstica habitual?', 'El siguiente salto hacia otras redes', 'La contraseña Wi-Fi', 'El nombre del navegador', 'La memoria del router', 'El gateway es un siguiente salto para alcanzar destinos.'),
        Q('¿Qué puede proporcionar DHCP?', 'Dirección, prefijo, gateway y DNS', 'Solo un fondo de pantalla', 'Todas las contraseñas remotas', 'Un antivirus obligatorio', 'DHCP distribuye parámetros de configuración de red.'),
        Q('¿Qué consulta ip -6 route?', 'La tabla de rutas IPv6', 'Seis archivos al azar', 'La sexta red Wi-Fi exclusivamente', 'Las claves SSH', '-6 selecciona la familia IPv6.'),
        Q('¿Qué riesgo tiene asignar una IP manual ya usada?', 'Un conflicto de direcciones', 'Instalar paquetes sin permiso', 'Cambiar todos los nombres de usuario', 'Aumentar automáticamente la velocidad', 'Dos equipos usando una misma dirección pueden perder conectividad.')
      ]),
      L('Enlace local y NetworkManager', [
        'El diagnóstico comienza cerca: interfaz disponible, enlace activo y configuración IP. nmcli device status consulta dispositivos gestionados por NetworkManager. Un dispositivo no gestionado no necesariamente está roto; puede estar bajo otra configuración.',
        'Una señal Wi-Fi débil, modo avión, cable suelto o asociación fallida son problemas distintos. Confirma el estado antes de cambiar DNS. En una red corporativa puede haber autenticación adicional. No compartas la contraseña Wi-Fi ni exportaciones que la contengan al pedir ayuda.'
      ], 'nmcli device status\nip link', 'Si NetworkManager está instalado, muestra su visión de dispositivos; ip link consulta interfaces del kernel.', 'Ordena estas comprobaciones: enlace, dirección, ruta y resolución de nombres.', [
        Q('¿Qué conviene revisar antes de cambiar DNS ante una desconexión?', 'Enlace y configuración IP', 'Solo el tema de iconos', 'La papelera', 'La versión del editor', 'DNS no soluciona un cable desconectado o falta de enlace.'),
        Q('¿Qué herramienta administra dispositivos de NetworkManager desde terminal?', 'nmcli', 'chmod', 'tar', 'wc', 'nmcli es la interfaz de comandos de NetworkManager.'),
        Q('¿Un dispositivo «no gestionado» en NetworkManager está necesariamente averiado?', 'No, puede estar gestionado de otra forma', 'Sí, siempre', 'Sí, implica fallo físico', 'Solo si es Ethernet', 'El estado describe gestión, no necesariamente salud física.'),
        Q('¿Qué consulta ip link?', 'Interfaces y estado de enlace', 'Enlaces de favoritos web', 'Claves privadas', 'Paquetes eliminados', 'ip link trabaja con dispositivos de red.'),
        Q('¿Qué información evitarías publicar al pedir ayuda con Wi-Fi?', 'La contraseña de la red', 'El nombre genérico de la herramienta', 'El texto de un error sin secretos', 'La familia de distribución', 'La credencial de la red es información privada.')
      ]),
      L('Prueba conectividad con criterio', [
        'ping utiliza mensajes ICMP para probar respuestas y medir tiempos de ida y vuelta. -c limita la cantidad de solicitudes. Probar un gateway conocido ayuda a estudiar el enlace local; probar una IP remota amplía el alcance.',
        'Un ping exitoso no demuestra que un servicio web funcione. Un ping fallido tampoco prueba por sí solo que el equipo remoto esté apagado: ICMP puede filtrarse. Distingue pérdida de paquetes, demora y resolución de nombres; cada dato aporta una parte del diagnóstico.'
      ], 'ping -c 4 127.0.0.1', 'Envía cuatro solicitudes al propio equipo. Es una prueba local, no una prueba de acceso a internet.', 'Explica por qué responder a ping y servir una página HTTPS son comprobaciones diferentes.', [
        Q('¿Qué protocolo usa normalmente ping para sus pruebas?', 'ICMP', 'SMTP', 'FTP exclusivamente', 'SSH', 'ping utiliza solicitudes y respuestas de eco ICMP.'),
        Q('¿Qué limita ping -c 4?', 'El número de solicitudes de eco', 'La contraseña a cuatro letras', 'El puerto a 4', 'La velocidad a cuatro bytes', '-c acota el número de solicitudes enviadas.'),
        Q('¿Qué mide el tiempo mostrado por ping?', 'Tiempo de ida y vuelta de una respuesta', 'Solo velocidad de descarga', 'Tamaño total del disco', 'Duración del arranque', 'La latencia de ida y vuelta no es ancho de banda.'),
        Q('Si un destino no responde a ping, ¿qué posibilidad debes considerar?', 'Que ICMP esté filtrado', 'Que seguro no exista', 'Que seguro el teclado falle', 'Que todos los sitios web estén caídos', 'Un filtro puede impedir eco sin impedir otros servicios.'),
        Q('¿Qué prueba ping a 127.0.0.1?', 'La comunicación local de loopback', 'Toda la conexión con internet', 'El DNS del proveedor', 'La contraseña del router', 'El tráfico de loopback permanece en el equipo.')
      ]),
      L('DNS y resolución de nombres', [
        'DNS traduce nombres a registros, entre ellos direcciones. A se usa para IPv4 y AAAA para IPv6. getent hosts consulta la resolución configurada por el sistema, que puede incluir /etc/hosts además de DNS. Un nombre puede resolver a varias direcciones.',
        'resolvectl status muestra configuración cuando systemd-resolved está disponible. Si una IP es accesible pero un nombre falla, investiga resolución; no concluyas de inmediato que toda la red cayó. /etc/resolv.conf puede ser gestionado automáticamente, así que editarlo a ciegas puede no persistir.'
      ], 'getent hosts example.com\nresolvectl status', 'Consulta un nombre y, si existe systemd-resolved, el estado del resolvedor. La consulta externa requiere conexión.', 'Distingue un fallo de resolución de un fallo de conexión al puerto de un servidor.', [
        Q('¿Qué asocia habitualmente un registro A?', 'Un nombre con una dirección IPv4', 'Una contraseña con una cuenta', 'Un archivo con un permiso', 'Un puerto con una CPU', 'Los registros A contienen direcciones IPv4.'),
        Q('¿Qué familia representa un registro AAAA?', 'IPv6', 'IPv4 únicamente', 'Ethernet sin IP', 'Una versión de SSH', 'AAAA almacena direcciones IPv6.'),
        Q('¿Qué consulta getent hosts?', 'La resolución de nombres configurada en el sistema', 'Solo el uso de CPU', 'Solo paquetes APT', 'Los procesos bloqueados', 'getent utiliza las bases y mecanismos de resolución configurados.'),
        Q('Una IP responde pero su nombre no resuelve. ¿Qué investigarías?', 'La resolución de nombres', 'Solo la batería', 'El formato del disco', 'La configuración de impresora', 'La conectividad por IP y la resolución son capas diferentes.'),
        Q('¿Por qué editar resolv.conf directamente puede no persistir?', 'Puede estar administrado por otro servicio', 'Es siempre de solo lectura física', 'Solo contiene imágenes', 'Se borra con cada ping', 'Gestores de red y resolvedores pueden regenerarlo.')
      ]),
      L('Puertos, TCP y UDP', [
        'Los puertos distinguen servicios de transporte en una dirección. TCP ofrece un flujo con mecanismos de orden y retransmisión; UDP envía datagramas sin esas garantías propias del protocolo. La aplicación puede implementar garantías adicionales sobre UDP.',
        'Un puerto por sí solo no identifica con certeza el programa. HTTPS suele usar TCP 443 y también puede usar QUIC sobre UDP 443. ss -tuln muestra sockets TCP y UDP en escucha o preparados para recibir, con direcciones numéricas. Escuchar no garantiza ser accesible desde internet.'
      ], 'ss -tuln', 'Consulta sockets TCP y UDP locales sin resolver nombres de servicios.', 'Distingue dirección, puerto y protocolo en una línea del resultado.', [
        Q('¿Para qué sirve un puerto de transporte?', 'Distinguir servicios en una dirección', 'Identificar una carpeta', 'Medir tamaño de RAM', 'Guardar contraseñas', 'Los puertos ayudan a dirigir tráfico a aplicaciones.'),
        Q('¿Qué proporciona TCP?', 'Un flujo con orden y retransmisión', 'Solo datagramas sin orden propio', 'Cifrado obligatorio siempre', 'Resolución DNS integrada', 'TCP ofrece transporte fiable orientado a conexión.'),
        Q('¿Qué caracteriza a UDP por sí mismo?', 'Datagramas sin garantía propia de entrega u orden', 'Un flujo idéntico a TCP', 'Cifrado obligatorio', 'Un sistema de archivos', 'Las aplicaciones pueden añadir mecanismos sobre UDP.'),
        Q('¿Qué consulta ss -tuln?', 'Sockets locales TCP y UDP con direcciones numéricas', 'Solo archivos grandes', 'Paquetes por actualizar', 'Contraseñas SSH', 'Las opciones seleccionan protocolos, escucha y formato numérico.'),
        Q('¿Un puerto en escucha implica acceso desde internet?', 'No, intervienen enlace, rutas y filtros', 'Sí, siempre', 'Solo si el puerto es impar', 'Sí, aunque no haya red', 'Escucha local y accesibilidad remota no son equivalentes.')
      ]),
      L('Direcciones de escucha y cortafuegos', [
        'Un servicio unido a 127.0.0.1 acepta conexiones por loopback; 0.0.0.0 suele representar todas las interfaces IPv4 locales. Escuchar en todas puede ampliar exposición a la red. Las reglas de cortafuegos filtran tráfico según criterios como dirección, protocolo y puerto.',
        'UFW es una interfaz de administración de reglas disponible en muchas instalaciones Ubuntu. sudo ufw status verbose consulta su estado. Antes de habilitar o modificar un cortafuegos por acceso remoto, conserva una vía de recuperación y permite la conexión que necesitas. Un filtro no reemplaza autenticación ni actualizaciones.'
      ], 'ss -ltn\nsudo ufw status verbose', 'Consulta sockets TCP en escucha y, si UFW está instalado, sus reglas y estado. No habilita el cortafuegos.', 'Explica qué diferencia de alcance hay entre un servicio ligado a 127.0.0.1 y a 0.0.0.0.', [
        Q('¿Qué alcance tiene una escucha en 127.0.0.1?', 'Loopback local', 'Toda internet por definición', 'Solo la red Wi-Fi de invitados', 'Todos los equipos IPv6', 'La dirección loopback limita ese socket a comunicación local.'),
        Q('¿Qué suele indicar 0.0.0.0 como dirección de escucha IPv4?', 'Todas las interfaces IPv4 locales', 'Ninguna interfaz', 'Una sola web remota', 'Solo IPv6', 'Es una dirección comodín al enlazar sockets IPv4.'),
        Q('¿Qué hace un cortafuegos?', 'Filtrar tráfico según reglas', 'Guardar todos los archivos automáticamente', 'Cifrar cualquier aplicación', 'Reemplazar el gestor de paquetes', 'Controla el tráfico permitido según su política.'),
        Q('¿Qué consulta ufw status verbose?', 'Estado y reglas resumidas de UFW', 'Activa UFW siempre', 'Borra todas las reglas', 'Cambia la contraseña SSH', 'status consulta; no habilita por sí solo.'),
        Q('Antes de cambiar reglas por SSH, ¿qué debes prever?', 'Mantener acceso y una vía de recuperación', 'Cerrar toda vía de administración sin probar', 'Borrar la clave pública', 'Desinstalar el navegador', 'Una regla equivocada puede cortar la sesión o impedir reconectar.')
      ]),
      L('HTTP, HTTPS y curl', [
        'HTTP define solicitudes y respuestas web. Un código 200 suele indicar éxito, 404 recurso no encontrado y 500 un fallo del servidor. HTTPS incorpora TLS para proteger la conexión y autenticar el servidor según certificados y confianza configurada.',
        'curl -I solicita cabeceras usando HEAD. --max-time limita el tiempo total permitido para la transferencia. Un certificado válido no garantiza que el negocio del sitio sea honesto; sí aporta verificación de la conexión al nombre solicitado. Evita saltar validaciones de certificados para «arreglar» un error sin entenderlo.'
      ], 'curl -I --max-time 10 https://example.com', 'Solicita cabeceras con un límite total de diez segundos. Requiere acceso a la red.', 'Distingue un fallo de DNS, uno de certificado y una respuesta HTTP 404.', [
        Q('¿Qué suele significar HTTP 404?', 'Recurso no encontrado', 'Contraseña correcta', 'Disco formateado', 'Conexión cifrada garantizada', '404 describe ausencia del recurso solicitado.'),
        Q('¿Qué añade HTTPS al uso de HTTP?', 'Protección TLS para la conexión', 'Una garantía de honestidad comercial', 'Un respaldo local automático', 'Permisos de root', 'TLS protege transporte y autentica el servidor según la confianza configurada.'),
        Q('¿Qué solicita curl -I normalmente?', 'Cabeceras mediante HEAD', 'Instalar el sitio', 'La contraseña del servidor', 'Cambiar DNS', '-I pide cabeceras sin descargar el cuerpo habitual.'),
        Q('¿Para qué sirve --max-time 10 en curl?', 'Limitar a diez segundos el tiempo total de transferencia', 'Descargar diez archivos siempre', 'Usar puerto 10', 'Reintentar sin límite', 'Acota el tiempo de la operación.'),
        Q('¿Un sitio con certificado válido es necesariamente honesto?', 'No, la autenticación de conexión no garantiza su conducta', 'Sí, siempre', 'Solo si usa IPv4', 'Sí, por usar puerto 443', 'La validez técnica de TLS no certifica la honestidad del contenido.')
      ]),
      L('SSH: cliente, servidor e identidad', [
        'SSH permite acceso remoto cifrado. El cliente inicia la conexión y el servidor la recibe. ssh usuario@servidor solicita entrar con esa cuenta remota. El puerto habitual es 22, pero puede configurarse otro con -p.',
        'La primera conexión muestra una huella de clave del servidor. Verifícala mediante una fuente confiable antes de aceptarla. known_hosts recuerda identidades de servidores; una advertencia por cambio puede indicar reinstalación legítima o un problema de identidad. No la borres automáticamente sin comprobar la causa.'
      ], 'ssh -V', 'Consulta la versión del cliente OpenSSH local, sin conectarse a otro equipo.', 'Describe qué datos necesitarías para conectar a una máquina de práctica: cuenta, dirección, puerto y huella.', [
        Q('En SSH, ¿quién inicia normalmente la conexión?', 'El cliente', 'El servidor siempre', 'El gestor de paquetes', 'La papelera', 'El cliente contacta con el servicio remoto.'),
        Q('En ssh ana@equipo, ¿qué representa ana?', 'La cuenta remota solicitada', 'El nombre del disco', 'El puerto', 'La contraseña en texto', 'El prefijo antes de @ especifica el usuario remoto.'),
        Q('¿Cuál es el puerto habitual de SSH?', '22', '80', '53', '443 exclusivamente', '22 es el puerto convencional; puede cambiarse.'),
        Q('¿Qué contiene known_hosts?', 'Identidades conocidas de servidores', 'Tus claves privadas necesariamente', 'Todas las contraseñas del sistema', 'Una lista de paquetes', 'Permite detectar cambios de clave de un servidor conocido.'),
        Q('¿Qué haces ante una huella SSH que cambió inesperadamente?', 'Verificar el cambio antes de confiar', 'Aceptarla siempre sin revisar', 'Compartir tu clave privada', 'Desactivar todo cifrado', 'El cambio puede ser legítimo o señalar otro destino; hay que comprobarlo.')
      ]),
      L('Claves públicas y privadas', [
        'La autenticación SSH con claves usa un par. La clave pública puede instalarse en el servidor; la privada debe quedar bajo tu control. Una frase de paso protege el uso de la clave privada almacenada. Compartir el archivo .pub no equivale a compartir el archivo privado.',
        'authorized_keys contiene claves públicas autorizadas para una cuenta remota. ssh-agent puede mantener claves disponibles durante una sesión y reducir solicitudes repetidas de frase de paso. Mantén permisos y respaldo adecuados, y revoca claves si una privada se expone.'
      ], 'ls -ld ~/.ssh\nls ~/.ssh/*.pub', 'Consulta la carpeta y nombres de claves públicas, si existen. No muestra el contenido de claves privadas.', 'Explica qué archivo puedes entregar al administrador del servidor y cuál debe permanecer privado.', [
        Q('¿Qué parte del par se comparte para autorizar acceso?', 'La clave pública', 'La privada', 'Ambas obligatoriamente', 'La contraseña de root', 'La pública puede instalarse en la cuenta remota.'),
        Q('¿Qué debe mantenerse en secreto?', 'La clave privada', 'El nombre genérico de SSH', 'La extensión .pub', 'El puerto convencional', 'La privada permite demostrar tu identidad.'),
        Q('¿Qué protege una frase de paso de la clave?', 'El uso de la clave privada almacenada', 'Todo el servidor por sí sola', 'La dirección IP pública', 'El catálogo APT', 'Añade protección al archivo privado en reposo.'),
        Q('¿Para qué sirve authorized_keys?', 'Listar claves públicas autorizadas para una cuenta', 'Guardar paquetes descargados', 'Enumerar todas las redes Wi-Fi', 'Conservar el historial de CPU', 'El servidor comprueba claves autorizadas para autenticar.'),
        Q('Si se expone una clave privada, ¿qué corresponde hacer?', 'Revocar su acceso y generar un par nuevo', 'Publicarla también en más lugares', 'Cambiar solo el color del terminal', 'Renombrar el archivo y seguir igual', 'La identidad comprometida debe dejar de aceptarse.')
      ]),
      L('Transferencia de archivos por SSH', [
        'scp copia archivos entre rutas locales y remotas mediante SSH. Una ruta remota suele tener usuario@host:ruta. sftp ofrece una sesión para transferir archivos y gestionar rutas. En ambos casos necesitas credenciales válidas y permisos en el destino.',
        'Antes de transferir, comprueba origen, destino y posibles sobrescrituras. scp usa -P mayúscula para el puerto; ssh utiliza -p minúscula. Cifrar el transporte no corrige una ruta errónea ni sustituye verificar el archivo recibido. Las transferencias requieren conectividad y espacio disponible.'
      ], 'scp nota.txt usuario@servidor:Documentos/', 'Ejemplo para copiar un archivo a un servidor propio o autorizado; sustituye cuenta y host antes de usarlo.', 'Identifica qué parte del ejemplo es local y cuál remota. Explica cómo verificarías el resultado.', [
        Q('¿Qué indica usuario@host:ruta en scp?', 'Un destino u origen remoto', 'Una contraseña literal', 'Solo una carpeta local obligatoriamente', 'Un paquete instalable', 'El formato señala cuenta, equipo y ruta remota.'),
        Q('¿Qué alternativa ofrece una sesión interactiva de transferencia sobre SSH?', 'sftp', 'grep', 'chmod', 'df', 'sftp permite navegar y transferir mediante el protocolo correspondiente.'),
        Q('¿Qué opción de scp selecciona un puerto?', '-P mayúscula', '-p minúscula con ese significado', '--cpu', '-z siempre', 'scp distingue -P para puerto de -p para preservar atributos.'),
        Q('¿Cifrar la transferencia evita sobrescribir una ruta equivocada?', 'No', 'Sí, siempre', 'Solo con archivos de texto', 'Solo si el servidor es Linux', 'La protección del transporte no valida tu intención sobre el destino.'),
        Q('¿Qué debes comprobar tras transferir un archivo importante?', 'Que llegó completo al destino correcto', 'Solo el color del icono', 'Que se cerró la ventana', 'Que cambió la contraseña', 'Verificar destino e integridad confirma la operación.')
      ]),
      L('Contraseñas, MFA y mínimo privilegio', [
        'Usa credenciales diferentes para servicios distintos y un gestor de contraseñas para administrarlas. Una frase larga y no reutilizada reduce riesgos frente a adivinación y filtraciones de otros sitios. No pegues tokens en capturas, notas públicas ni comandos que puedan quedar en el historial.',
        'MFA combina factores, por ejemplo una contraseña y una llave física. Dos contraseñas no son necesariamente dos factores. El mínimo privilegio concede solo el acceso requerido y por el tiempo necesario. Guarda códigos de recuperación de MFA en un lugar seguro para evitar perder acceso.'
      ], 'id', 'Consulta tu identidad y grupos para entender qué permisos podría tener tu sesión.', 'Revisa conceptualmente qué cuentas usas y cuáles admiten MFA, sin escribir sus contraseñas en los apuntes.', [
        Q('¿Por qué evitar reutilizar una contraseña?', 'Una filtración puede comprometer otras cuentas', 'Porque Linux no permite repetir letras', 'Porque siempre cambia el DNS', 'Porque consume más disco', 'Las credenciales filtradas pueden probarse en otros servicios.'),
        Q('¿Qué ejemplo combina factores distintos?', 'Contraseña y llave física de seguridad', 'Dos contraseñas del mismo tipo', 'Dos nombres de usuario', 'Dos pestañas de navegador', 'MFA combina categorías de autenticación diferentes.'),
        Q('¿Qué significa mínimo privilegio?', 'Conceder solo los permisos necesarios', 'Dar root a todos para simplificar', 'Eliminar todas las cuentas', 'Usar siempre la misma contraseña', 'Limitar acceso reduce el impacto de errores o compromisos.'),
        Q('¿Dónde evitarías pegar un token privado?', 'En un comando que quede en historial compartido', 'En el gestor seguro previsto para secretos', 'En una configuración privada con acceso restringido cuando corresponda', 'En el mecanismo seguro del servicio', 'El historial puede exponer secretos a lectores posteriores.'),
        Q('¿Para qué conservar códigos de recuperación de MFA?', 'Recuperar acceso si pierdes el factor habitual', 'Desactivar todas las contraseñas públicas', 'Aumentar la velocidad de red', 'Cambiar el disco de arranque', 'Los códigos ofrecen una vía de recuperación y deben protegerse.')
      ]),
      L('Actualizaciones, origen e integridad', [
        'Las actualizaciones pueden corregir vulnerabilidades y errores. Instala desde fuentes que puedas identificar y que correspondan a tu distribución. Una descarga por HTTPS protege la conexión, pero no basta para demostrar que cualquier ejecutable sea adecuado o legítimo.',
        'sha256sum calcula una huella del contenido. Para verificar integridad necesitas comparar con un valor esperado obtenido de una fuente confiable; calcular una huella sin referencia no autentica nada. Un comando que descarga y ejecuta código directamente merece revisar primero el origen y el contenido.'
      ], 'sha256sum archivo-de-practica.txt', 'Calcula el resumen SHA-256 de un archivo existente; no lo modifica.', 'Explica de dónde obtendrías una suma de referencia antes de verificar una imagen de instalación.', [
        Q('¿Qué pueden corregir las actualizaciones de software?', 'Errores y vulnerabilidades', 'Siempre todos los fallos de hardware', 'La falta de electricidad', 'Cualquier cable roto', 'Las actualizaciones de software corrigen problemas dentro de su alcance.'),
        Q('¿Qué calcula sha256sum?', 'Una huella del contenido del archivo', 'Su contraseña de cifrado', 'La velocidad de internet', 'Su permiso de ejecución', 'SHA-256 resume los bytes en una huella.'),
        Q('¿Qué necesitas además de calcular una huella para verificar una descarga?', 'Un valor esperado de una fuente confiable', 'Cambiar su extensión', 'Abrirla como root', 'Moverla a /tmp siempre', 'Sin referencia confiable, la huella no prueba autenticidad.'),
        Q('¿HTTPS garantiza que un ejecutable descargado sea seguro?', 'No', 'Sí, cualquier ejecutable', 'Solo si pesa poco', 'Solo si tiene icono', 'La protección de transporte no certifica el comportamiento del software.'),
        Q('¿Qué harías antes de ejecutar un script descargado?', 'Verificar origen y revisar su contenido y propósito', 'Ejecutarlo siempre con sudo inmediatamente', 'Ocultar todos los errores', 'Compartir tu contraseña con el autor', 'Comprender el código y su origen permite evaluar la acción.')
      ]),
      L('Caso práctico: una web no abre', [
        'Ordena la investigación por capas: enlace, dirección IP, ruta, resolución de nombres y servicio. Si otros sitios funcionan, quizá el problema sea específico del destino. Si el nombre resuelve y el servidor responde con 503, hay evidencia de un fallo o indisponibilidad del servicio HTTP, no de ausencia total de red.',
        'Registra mensajes exactos, hora y alcance del problema. Evita cambiar varias capas simultáneamente; podrías ocultar la causa. Tras una corrección, repite la misma prueba y compara. Los filtros, proxies, VPN y portales cautivos pueden afectar solo parte del tráfico.'
      ], 'ip -br address\nip route\ngetent hosts example.com\ncurl -I --max-time 10 https://example.com', 'Secuencia de consultas desde configuración local hasta una petición web externa. Cada salida responde una pregunta distinta.', 'Para «IP válida, ruta presente, nombre resuelto, respuesta HTTP 503», redacta una conclusión sin afirmar que toda internet está caída.', [
        Q('¿Qué orden de diagnóstico suele ser útil?', 'Enlace, IP, ruta, DNS y servicio', 'Reinstalar, borrar, preguntar', 'DNS siempre antes de comprobar cable', 'Cambiar contraseñas como primer paso universal', 'Avanzar por capas ayuda a localizar el fallo.'),
        Q('Recibes HTTP 503 del destino. ¿Qué evidencia tienes?', 'El servidor o intermediario respondió con indisponibilidad', 'No existe ninguna conectividad IP', 'El teclado está desconectado', 'DNS siempre está roto', 'Una respuesta HTTP ya demuestra que se alcanzó un interlocutor HTTP.'),
        Q('Si otras webs funcionan, ¿qué conviene investigar?', 'El destino o las rutas y reglas que lo afectan', 'Suponer que toda internet está caída', 'Borrar todos los documentos', 'Formatear por defecto', 'El alcance del fallo orienta hacia componentes específicos.'),
        Q('¿Por qué anotar hora y error exacto?', 'Para correlacionar pruebas y registros', 'Para cambiar automáticamente la red', 'Para instalar controladores siempre', 'Para ocultar el diagnóstico', 'Son datos reproducibles útiles para comparar y pedir ayuda.'),
        Q('¿Qué harías tras una corrección de red?', 'Repetir la prueba que fallaba', 'Asumir éxito sin probar', 'Cambiar otras cinco opciones', 'Borrar todos los registros', 'La prueba final confirma el comportamiento esperado.')
      ])
    ]
  });
})(globalThis);
