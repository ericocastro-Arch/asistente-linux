(function (root) {
  'use strict';
  const { Q, L } = root.AcademyContent;
  root.AcademyCourses.push({
    id: 'administracion', title: 'Administra tu sistema', subtitle: 'Un Linux ordenado, estable y bajo tu control.',
    category: 'Sistema', level: 'Intermedio', color: 'peach', symbol: '{ }', label: 'CONTROL Y AUTONOMÍA',
    description: 'Entiende paquetes, permisos, servicios y almacenamiento. Aprende a diagnosticar con datos y a planificar cambios recuperables en Debian y Ubuntu con systemd.',
    requirements: 'Manejo básico de la terminal. Para practicar consultas, Debian o Ubuntu con systemd; las operaciones administrativas pueden requerir permisos.',
    outcomes: ['Gestionar paquetes y reconocer sus estados.', 'Interpretar permisos, propietarios y grupos.', 'Consultar servicios y registros con systemd.', 'Diagnosticar recursos y preparar una recuperación.'],
    modules: ['Paquetes sin misterio', 'Identidades y acceso', 'Procesos y servicios', 'Discos y mantenimiento', 'Operación responsable'],
    resources: [['Referencia de Debian: paquetes', 'https://www.debian.org/doc/manuals/debian-reference/ch02.en.html'], ['Manual de systemctl', 'https://www.freedesktop.org/software/systemd/man/latest/systemctl.html']],
    lessons: [
      L('Repositorios y metadatos de APT', [
        'APT utiliza índices de repositorios para conocer paquetes, versiones y dependencias. apt update descarga índices nuevos; no actualiza por sí solo todos los programas. Las fuentes se configuran en /etc/apt/sources.list y archivos de /etc/apt/sources.list.d, incluidos los formatos .list y .sources.',
        'Una actualización de índices con errores puede dejar información parcial o antigua. Lee el mensaje antes de seguir. Las firmas ayudan a verificar la autenticidad del repositorio, pero no convierten cualquier fuente en adecuada para tu distribución. Evita mezclar versiones o distribuciones sin un plan.'
      ], 'apt-cache policy', 'Muestra prioridades y orígenes conocidos usando los metadatos locales, sin instalar paquetes.', 'Explica la diferencia entre actualizar el catálogo de una biblioteca y reemplazar los libros que ya tienes.', [
        Q('¿Qué hace apt update?', 'Actualiza índices de paquetes', 'Actualiza siempre todos los programas instalados', 'Borra todos los paquetes antiguos', 'Reinicia el equipo', 'update obtiene metadatos; instalar versiones nuevas es otra operación.'),
        Q('¿Dónde pueden definirse fuentes APT?', '/etc/apt/sources.list.d', '/dev/apt-only', '/home/packages-obligatorio', '/tmp/kernel', 'APT acepta archivos de fuentes en ese directorio.'),
        Q('¿Qué ayuda a comprobar la firma de un repositorio?', 'La autenticidad e integridad de metadatos firmados', 'Que todo programa sea adecuado a cualquier distribución', 'Que nunca existan fallos de software', 'Que no se necesite red', 'La firma comprueba origen e integridad, no compatibilidad universal.'),
        Q('Si apt update muestra errores, ¿qué conviene hacer?', 'Revisar cuáles índices fallaron', 'Suponer que todos se actualizaron', 'Borrar /var/lib/dpkg', 'Desactivar toda verificación permanentemente', 'Algunos índices pueden no haberse renovado.'),
        Q('¿Qué muestra apt-cache policy sin instalar?', 'Orígenes y prioridades conocidas', 'Las contraseñas guardadas', 'El brillo de pantalla', 'Todos los archivos personales', 'policy permite inspeccionar la selección de paquetes y sus fuentes.')
      ]),
      L('Instalar, actualizar y simular', [
        'apt install paquete prepara una instalación y resuelve dependencias. apt upgrade actualiza paquetes instalados según las reglas de APT. apt full-upgrade puede eliminar paquetes si necesita resolver cambios de dependencias. Revisa la lista de cambios, descargas y espacio antes de confirmar.',
        'apt-get -s simula una operación sin aplicarla; sirve para estudiar qué haría el gestor con los índices actuales. La simulación no garantiza que una ejecución futura tenga el mismo resultado, porque pueden cambiar índices y estado. En scripts suele preferirse apt-get por su interfaz orientada a automatización.'
      ], 'apt-get -s install vlc', 'Simula instalar VLC con los metadatos actuales. No descarga ni instala el paquete.', 'Busca en la simulación qué dependencias se añadirían y cómo sabrías si algo se eliminaría.', [
        Q('¿Qué opción de apt-get simula una operación?', '-s', '-y como simulación', '--purge siempre', '--download-root', '-s muestra operaciones previstas sin aplicarlas.'),
        Q('¿Qué operación puede eliminar paquetes para resolver una actualización amplia?', 'apt full-upgrade', 'apt search', 'apt show', 'apt-cache policy', 'full-upgrade permite resolver cambios incluso mediante eliminaciones.'),
        Q('¿Qué conviene revisar antes de confirmar una instalación?', 'Paquetes añadidos, eliminados y espacio requerido', 'Solo el nombre del tema visual', 'Solo el fabricante del teclado', 'La lista de fondos de pantalla', 'El resumen permite entender el alcance de la operación.'),
        Q('¿Qué herramienta APT suele preferirse en scripts?', 'apt-get', 'El buscador del navegador', 'La papelera', 'Un comando aleatorio de escritorio', 'apt-get está orientado a automatización y mantiene una interfaz más apropiada para scripts.'),
        Q('¿Una simulación garantiza un resultado idéntico en una semana?', 'No, pueden cambiar índices y estado', 'Sí, bloquea todas las versiones', 'Sí, instala en secreto', 'Solo si se cierra la terminal', 'La simulación refleja las condiciones de ese momento.')
      ]),
      L('Eliminar paquetes y distinguir formatos', [
        'apt remove retira un paquete y suele conservar su configuración de sistema. apt purge elimina además la configuración gestionada por el paquete; no garantiza borrar los datos personales creados en tu hogar. autoremove propone dependencias automáticas que ya no se necesitan según APT: revisa esa lista.',
        'dpkg -l consulta paquetes DEB conocidos por la base local. Snap y Flatpak mantienen inventarios distintos. Desinstalar un formato no elimina necesariamente otra instalación de la misma aplicación. Antes de actuar, identifica el origen y conserva tus documentos.'
      ], 'dpkg -l\napt-get -s autoremove', 'Consulta el inventario DEB y simula la retirada de dependencias automáticas sin aplicar cambios.', 'Si una aplicación aparece en APT y Flatpak, explica por qué quitar una copia podría dejar la otra disponible.', [
        Q('¿Qué diferencia habitual hay entre remove y purge?', 'purge retira también configuración gestionada del paquete', 'remove siempre borra todos los documentos personales', 'purge instala una versión anterior', 'No existe ninguna diferencia', 'purge añade la retirada de archivos de configuración del paquete.'),
        Q('¿Qué propone autoremove?', 'Dependencias automáticas que ya no se necesitan', 'Todos los archivos grandes del hogar', 'Todos los navegadores', 'Cualquier programa sin icono', 'APT utiliza el marcado automático y las dependencias para proponer candidatos.'),
        Q('¿Qué inventario consulta dpkg -l?', 'Paquetes DEB de la base local', 'Solo Flatpaks remotos', 'Procesos activos', 'Redes Wi-Fi', 'dpkg administra la base de paquetes Debian.'),
        Q('¿Quitar una aplicación DEB elimina necesariamente su copia Flatpak?', 'No, son instalaciones gestionadas por separado', 'Sí, siempre', 'Solo por tener el mismo icono', 'Solo al usar un escritorio claro', 'Cada gestor mantiene su instalación.'),
        Q('¿apt purge garantiza borrar las preferencias personales del hogar?', 'No', 'Sí, elimina todo /home', 'Sí, si el nombre es corto', 'Solo si el archivo es oculto', 'Los datos personales no son necesariamente configuración gestionada por el paquete.')
      ]),
      L('Identidades, grupos y cuentas', [
        'El sistema usa identificadores numéricos: UID para usuarios y GID para grupos. id muestra la identidad y grupos de un usuario. root normalmente tiene UID 0. El nombre visible es una representación legible; los permisos se aplican según identidades y reglas del sistema.',
        '/etc/passwd describe cuentas locales y no suele contener las contraseñas actuales en texto. Los hashes locales suelen estar protegidos en /etc/shadow. Los grupos permiten compartir acceso sin convertir a todos en administradores. Tras un cambio de grupos puede ser necesario iniciar una nueva sesión.'
      ], 'id\ngetent passwd "$USER"', 'Consulta tu identidad y la entrada de tu cuenta mediante la base de nombres configurada.', 'Identifica UID, GID y grupos secundarios en id. Explica por qué compartir un grupo no requiere compartir contraseña.', [
        Q('¿Qué identifica un UID?', 'Un usuario mediante un número', 'Un disco externo', 'Un puerto de red', 'Una ventana', 'UID es el identificador numérico de usuario.'),
        Q('¿Qué UID corresponde normalmente a root?', '0', '1000 siempre', '22', '65535 siempre', 'La cuenta privilegiada tradicional usa UID 0.'),
        Q('¿Para qué ayudan los grupos?', 'Compartir permisos entre cuentas', 'Compartir obligatoriamente contraseñas', 'Reemplazar toda autenticación', 'Aumentar la memoria física', 'Los grupos facilitan conceder acceso colectivo.'),
        Q('¿Dónde suelen guardarse hashes de contraseñas de cuentas locales?', '/etc/shadow', '/tmp/passwords.txt', '/usr/bin/passwd.txt', '/home/public-passwords', 'shadow restringe el acceso a datos de autenticación locales.'),
        Q('Después de añadir un grupo a una cuenta, ¿qué puede ser necesario?', 'Iniciar una nueva sesión', 'Formatear el disco', 'Reinstalar el escritorio', 'Cambiar de monitor', 'Los grupos de los procesos existentes pueden conservar el estado de la sesión anterior.')
      ]),
      L('Permisos simbólicos y numéricos', [
        'chmod cambia bits de permisos cuando tienes autorización sobre el archivo. En forma simbólica, u es propietario, g grupo y o otros; + añade y - retira. chmod u+x archivo añade ejecución al propietario sin reemplazar todos los demás bits.',
        'En modo numérico, lectura vale 4, escritura 2 y ejecución 1. 640 concede rw- al propietario, r-- al grupo y --- a otros. Para directorios, lectura permite listar y ejecución permite atravesar. No uses 777 como reparación universal: concede acceso a todos y puede esconder el problema real.'
      ], 'ls -l archivo-de-practica.txt\nchmod u+rw archivo-de-practica.txt', 'Sobre un archivo tuyo de práctica, revisa y añade lectura y escritura al propietario.', 'Descompón 750 en tres bloques de permisos e indica qué acceso reciben otros usuarios.', [
        Q('¿Qué valor numérico tiene el permiso de lectura?', '4', '2', '1', '8', 'Los bits tradicionales son lectura 4, escritura 2 y ejecución 1.'),
        Q('¿Qué permisos da 640 al grupo?', 'Solo lectura', 'Lectura y escritura', 'Todos', 'Solo ejecución', 'El segundo dígito es 4, equivalente a r--.'),
        Q('¿Qué hace chmod u+x archivo?', 'Añade ejecución al propietario', 'Da escritura a todos', 'Elimina el propietario', 'Cambia el grupo a root', 'u selecciona usuario propietario y +x añade ejecución.'),
        Q('¿Qué concede el último 0 de 750 a otros?', 'Ningún permiso de esos bits', 'Lectura completa', 'Ejecución completa', 'Administración', 'El tercer dígito controla otros y 0 no concede bits.'),
        Q('¿Por qué 777 no es una solución general recomendable?', 'Abre permisos a todos sin resolver necesariamente la causa', 'Impide siempre leer archivos', 'Desactiva el disco', 'Solo funciona en imágenes', 'Los permisos deben limitarse al acceso necesario.')
      ]),
      L('Propiedad y permisos de creación', [
        'chown cambia propietario y, opcionalmente, grupo; cambiar propietario normalmente requiere privilegios. chgrp cambia el grupo cuando está permitido. La propiedad y los bits de modo son capas distintas: chmod no cambia quién es dueño del archivo.',
        'umask indica bits que se retiran de los permisos solicitados al crear archivos. Si una aplicación solicita 666 y la máscara es 022, el resultado habitual es 644. Para directorios solicitados con 777, es 755. La máscara no añade ejecución a archivos ni modifica archivos anteriores.'
      ], 'umask\nls -ld ~', 'Muestra la máscara de creación de esta shell y los metadatos del propio directorio personal.', 'Calcula los permisos resultantes para un archivo solicitado con 666 y umask 027.', [
        Q('¿Qué modifica chown?', 'El propietario y opcionalmente el grupo', 'Solo el texto del archivo', 'La extensión automáticamente', 'La memoria usada', 'chown administra propiedad, no contenido.'),
        Q('¿Cambia chmod al propietario?', 'No, modifica bits de permisos', 'Sí, siempre a root', 'Sí, al usuario conectado', 'Solo con -l', 'Cambiar modo y cambiar propiedad son operaciones diferentes.'),
        Q('Con solicitud 666 y umask 022, ¿qué modo habitual resulta?', '644', '777', '022', '000', 'La máscara retira escritura de grupo y otros.'),
        Q('¿umask modifica los archivos ya existentes?', 'No', 'Sí, todos recursivamente', 'Solo los ocultos siempre', 'Solo los de /tmp siempre', 'La máscara actúa al crear nuevas entradas.'),
        Q('Con solicitud 666 y umask 027, ¿qué modo resulta?', '640', '666', '750', '027', 'Se retiran escritura del grupo y todos los permisos de otros.')
      ]),
      L('Inspecciona y termina procesos', [
        'ps muestra procesos y top actualiza una vista en tiempo real. Puedes inspeccionar PID, usuario, tiempo y uso de recursos antes de intervenir. Un mismo nombre puede aparecer varias veces; identifica el proceso correcto, no solo una coincidencia textual.',
        'kill envía señales. Sin indicar otra, normalmente usa SIGTERM, que permite al programa intentar cerrar ordenadamente. SIGKILL no puede manejarse y evita esa limpieza, por lo que se reserva para casos necesarios. No puedes señalar cualquier proceso sin permisos; perder datos sin guardar es posible al terminar aplicaciones.'
      ], 'ps -eo pid,user,comm,%cpu,%mem --sort=-%cpu', 'En ps de procps, lista procesos ordenados por uso de CPU. La métrica de ps no es idéntica a una muestra instantánea de top.', 'Identifica qué columnas revisarías antes de cerrar un proceso bloqueado. Explica por qué intentarías un cierre normal primero.', [
        Q('¿Qué hace realmente kill?', 'Enviar una señal a un proceso', 'Borrar siempre el ejecutable del disco', 'Desinstalar paquetes', 'Formatear memoria', 'El efecto depende de la señal y del proceso.'),
        Q('¿Qué señal envía kill normalmente por defecto?', 'SIGTERM', 'SIGKILL siempre', 'SIGSTOP siempre', 'SIGCONT siempre', 'La señal predeterminada habitual es TERM.'),
        Q('¿Por qué intentar SIGTERM antes de SIGKILL?', 'Permite que el programa intente limpiar y cerrar', 'SIGTERM garantiza guardar cualquier archivo', 'SIGKILL solo sirve para directorios', 'SIGTERM cambia contraseñas', 'El programa puede manejar TERM; KILL no permite esa limpieza.'),
        Q('¿Qué dato conviene comprobar antes de enviar una señal?', 'PID e identidad del proceso correcto', 'Solo el color de su icono', 'La extensión de una foto', 'El número de carpetas del hogar', 'Evita terminar un proceso distinto al que investigas.'),
        Q('¿Puedes terminar cualquier proceso como usuario normal?', 'No, existen controles de permisos', 'Sí, siempre', 'Solo si el nombre es corto', 'Sí, con cualquier señal', 'El envío de señales está sujeto a permisos.')
      ]),
      L('Servicios y systemd', [
        'En sistemas con systemd, una unidad representa un recurso administrado. Una unidad .service describe un servicio. systemctl status consulta estado y mensajes recientes. active no equivale a enabled: uno describe actividad y el otro la configuración de arranque.',
        'start inicia ahora; stop detiene ahora. enable prepara la activación mediante sus relaciones de arranque, pero por sí solo no inicia inmediatamente. enable --now combina habilitar e iniciar. Un servicio puede estar activo sin estar habilitado y también habilitado pero fallando.'
      ], 'systemctl --failed\nsystemctl status cron.service --no-pager', 'Lista unidades fallidas y consulta cron si existe en tu sistema. El nombre de un servicio puede variar entre distribuciones.', 'Distingue activo, habilitado y fallido. Describe un servicio que deseas usar hoy pero no arrancar automáticamente.', [
        Q('¿Qué describe active en una unidad?', 'Su estado de actividad', 'Que está habilitada necesariamente', 'Que nunca fallará', 'Que no usa memoria', 'El estado activo indica actividad actual, no política de arranque.'),
        Q('¿Qué hace systemctl enable por sí solo normalmente?', 'Configura su habilitación sin iniciarlo inmediatamente', 'Lo inicia siempre y solo una vez', 'Borra sus registros', 'Lo desinstala', 'enable modifica relaciones de activación; start inicia.'),
        Q('¿Qué opción combina habilitar e iniciar?', 'enable --now', 'status --delete', 'stop --forever', 'list --install', '--now solicita además la acción inmediata.'),
        Q('¿Qué consulta systemctl --failed?', 'Unidades en estado fallido', 'Solo archivos corruptos del hogar', 'Contraseñas incorrectas del navegador', 'Todos los puertos UDP', '--failed filtra unidades por estado fallido.'),
        Q('¿Puede un servicio estar activo y no habilitado?', 'Sí', 'No, son sinónimos', 'Solo si está desinstalado', 'Solo antes de iniciar Linux', 'Actividad actual y habilitación son propiedades distintas.')
      ]),
      L('Registros útiles con journalctl', [
        'journalctl consulta el diario de systemd. -b limita al arranque actual, -u filtra una unidad y -n limita la cantidad de líneas. --since permite acotar el tiempo. Una ventana temporal pequeña cerca del fallo suele aportar más que miles de líneas sin contexto.',
        'No todos los usuarios pueden ver todo el diario. Un mensaje de acceso limitado no demuestra que no existan registros. Los diarios pueden contener nombres, rutas o secretos de aplicaciones: revisa antes de compartir. La persistencia entre reinicios depende de la configuración del sistema.'
      ], 'journalctl -b -n 30 --no-pager', 'Muestra las últimas 30 entradas visibles del arranque actual sin abrir un paginador.', 'Elige qué filtros aplicarías si un servicio falló hace diez minutos.', [
        Q('¿Qué limita journalctl -b sin número de arranque?', 'El arranque actual', 'Todos los meses del año', 'Solo registros del navegador', 'Solo paquetes borrados', '-b selecciona el arranque.'),
        Q('¿Para qué sirve -u en journalctl?', 'Filtrar una unidad', 'Cambiar el usuario propietario', 'Desinstalar el diario', 'Actualizar el kernel', '-u limita entradas relacionadas con una unidad.'),
        Q('¿Qué hace -n 30 al consultar el diario?', 'Limita a las últimas 30 entradas solicitadas', 'Borra 30 registros', 'Espera 30 minutos', 'Reinicia 30 servicios', '-n acota el número de líneas a mostrar.'),
        Q('¿Por qué filtrar por tiempo ayuda al diagnóstico?', 'Acerca los mensajes al momento del fallo', 'Garantiza reparar el problema', 'Cambia la hora del sistema', 'Oculta toda información relevante', 'Relacionar eventos en el tiempo reduce ruido.'),
        Q('Si tu usuario ve pocos registros, ¿qué debes considerar?', 'Que su acceso puede estar restringido', 'Que el sistema nunca registra nada', 'Que todos los discos fallaron', 'Que journalctl siempre elimina datos', 'La visibilidad depende de permisos y configuración.')
      ]),
      L('Espacio de disco: df y du', [
        'df informa del uso de sistemas de archivos montados. du estima el espacio ocupado por entradas recorridas. df -h y du -sh ofrecen unidades legibles; -s resume en du. Las cifras pueden diferir por archivos borrados aún abiertos, metadatos y distintos alcances.',
        'Un sistema puede agotar inodos antes que bytes: df -i consulta esa dimensión. Cuando falta espacio, identifica primero el sistema de archivos lleno y luego directorios relevantes. Borrar a ciegas carpetas del sistema puede dañar paquetes o datos.'
      ], 'df -h\ndf -i\ndu -sh ~/Descargas', 'Consulta capacidad, inodos y tamaño de Descargas si existe. Algunos archivos pueden no ser accesibles.', 'Si /home está lleno pero / tiene espacio, explica por qué importa saber dónde se guarda el archivo.', [
        Q('¿Qué mide df principalmente?', 'Uso de sistemas de archivos', 'Solo el tamaño de una carpeta seleccionada', 'Temperatura de CPU', 'Número de servicios', 'df informa capacidad de los sistemas de archivos.'),
        Q('¿Qué significa -s en du -sh?', 'Resumir el total del argumento', 'Eliminar archivos pequeños', 'Ordenar procesos', 'Usar sudo', '-s entrega un resumen por argumento.'),
        Q('¿Qué consulta df -i?', 'Uso de inodos', 'Interfaces inalámbricas', 'Versiones instaladas', 'Identidad del usuario', 'Los inodos representan otra dimensión de capacidad.'),
        Q('¿Puede agotarse capacidad de crear archivos aunque queden bytes?', 'Sí, si se agotan los inodos', 'No, nunca', 'Solo sin escritorio', 'Solo por falta de internet', 'Muchos archivos pequeños pueden agotar inodos.'),
        Q('¿Qué puede explicar diferencias entre df y du?', 'Archivos borrados aún abiertos y distinto alcance', 'Que ambos siempre mienten', 'El color de las carpetas', 'La distribución del teclado', 'No miden exactamente el mismo conjunto de recursos.')
      ]),
      L('Particiones y puntos de montaje', [
        'Un disco puede contener particiones y estas pueden alojar sistemas de archivos. Montar conecta un sistema de archivos a una carpeta del árbol. lsblk muestra dispositivos de bloque y sus relaciones; con -f añade información de sistemas de archivos y UUID.',
        'Un nombre como /dev/sdb puede variar al conectar dispositivos. Los UUID ayudan a referenciar sistemas de archivos de forma estable. /etc/fstab describe montajes configurados. Antes de desconectar un soporte, desmontarlo o expulsarlo permite completar escrituras pendientes.'
      ], 'lsblk -f\nfindmnt', 'Inspecciona dispositivos, identificadores y montajes actuales sin modificarlos.', 'Ubica conceptualmente el dispositivo, el sistema de archivos y su carpeta de montaje en una memoria USB.', [
        Q('¿Qué significa montar un sistema de archivos?', 'Conectarlo a una carpeta del árbol', 'Comprimir todo el disco', 'Cambiar su fabricante', 'Crear siempre una partición nueva', 'El punto de montaje integra el contenido en el árbol.'),
        Q('¿Qué consulta lsblk?', 'Dispositivos de bloque y su estructura', 'Contraseñas de red', 'Solo procesos de root', 'Paquetes pendientes', 'lsblk describe discos y dispositivos de bloque relacionados.'),
        Q('¿Por qué usar UUID en referencias de montaje?', 'Es más estable que nombres dependientes del orden de detección', 'Siempre indica velocidad del disco', 'Es una contraseña secreta', 'Evita necesitar sistema de archivos', 'Los nombres de dispositivos pueden variar entre arranques.'),
        Q('¿Qué archivo describe montajes configurados habitualmente?', '/etc/fstab', '/etc/hosts como única función', '/tmp/mount-password', '/usr/bin/particiones', 'fstab contiene configuraciones de montaje.'),
        Q('¿Por qué expulsar un soporte antes de retirarlo?', 'Para completar escrituras y desmontarlo ordenadamente', 'Para borrar sus documentos', 'Para cambiar su formato', 'Para instalar controladores nuevos siempre', 'Retirar con escrituras pendientes puede perder datos.')
      ]),
      L('Memoria, caché y swap', [
        'free presenta memoria y swap. available estima cuánto podría asignarse a aplicaciones sin empezar a intercambiar memoria, considerando cachés recuperables. free y available no son equivalentes: memoria usada para caché puede ser útil y recuperable.',
        'La swap ofrece espacio de intercambio, habitualmente en disco o mediante soluciones de memoria comprimida. Puede aliviar presión, pero no equivale a añadir RAM física. vmstat permite observar actividad con muestras; interpreta tendencias junto con síntomas. Una sola captura no demuestra una fuga de memoria.'
      ], 'free -h\nvmstat 1 3', 'Consulta memoria y tres muestras de actividad de vmstat. La primera línea de valores puede resumir desde el arranque.', 'Explica por qué mirar available resulta más útil que concluir que cualquier caché es memoria desperdiciada.', [
        Q('¿Qué estima available en free?', 'Memoria que puede usarse considerando caché recuperable', 'Solo bytes nunca tocados', 'El tamaño de la pantalla', 'La velocidad de descarga', 'available estima capacidad para nuevas asignaciones.'),
        Q('¿La caché de archivos es siempre un problema?', 'No, aprovecha RAM y puede ser recuperable', 'Sí, debe borrarse cada minuto', 'Sí, es siempre un virus', 'No utiliza RAM nunca', 'La caché mejora acceso a archivos y puede ceder memoria.'),
        Q('¿Qué es la swap en términos generales?', 'Un recurso de intercambio de memoria', 'Una carpeta de iconos', 'Un gestor de paquetes', 'Una cuenta administrativa', 'El intercambio ayuda al sistema a gestionar presión de memoria.'),
        Q('¿Añadir swap equivale a añadir RAM física?', 'No', 'Sí, siempre con igual velocidad', 'Solo por usar ext4', 'Solo con GNOME', 'El soporte y comportamiento del intercambio son diferentes.'),
        Q('¿Qué enfoque ayuda a investigar una supuesta fuga de memoria?', 'Observar crecimiento sostenido y contexto', 'Concluir con una única cifra aislada', 'Eliminar toda caché sin medir', 'Cambiar el teclado', 'Una tendencia ofrece más evidencia que una captura aislada.')
      ]),
      L('Tareas programadas', [
        'cron ejecuta tareas según un calendario. En un crontab de usuario, cinco campos definen minuto, hora, día del mes, mes y día de semana; después va la orden. 0 9 * * * significa a las 09:00 cada día según la zona del servicio.',
        'Las tareas programadas tienen un entorno distinto de tu terminal interactiva. Usa rutas claras y recoge salida y errores. systemd también ofrece timers, que puedes listar con systemctl list-timers. No todas las máquinas tienen cron instalado o activo.'
      ], 'crontab -l\nsystemctl list-timers --all', 'Consulta tareas del usuario y temporizadores de systemd. crontab puede indicar que aún no tienes entradas.', 'Interpreta 30 18 * * * y enumera qué ruta y registros necesitaría un script programado.', [
        Q('¿Qué expresa 0 9 * * * en un crontab de usuario?', 'Todos los días a las 09:00', 'Cada nueve minutos', 'Solo el día nueve del mes', 'Cada nueve meses', 'Los primeros campos son minuto y hora.'),
        Q('¿Cuántos campos temporales tiene una entrada cron tradicional de usuario?', 'Cinco', 'Uno', 'Tres', 'Diez', 'Minuto, hora, día del mes, mes y día de semana.'),
        Q('¿Por qué usar rutas explícitas en tareas programadas?', 'El entorno y PATH pueden diferir de tu sesión', 'Cron prohíbe todos los comandos', 'Para cifrar las rutas', 'Porque siempre se ejecutan desde tu escritorio', 'No debes asumir el entorno interactivo.'),
        Q('¿Qué consulta systemctl list-timers?', 'Temporizadores de systemd', 'Solo la hora del BIOS', 'Contraseñas caducadas', 'Archivos por tamaño', 'Los timers programan activaciones en systemd.'),
        Q('¿Qué conviene registrar de un script programado?', 'Salida y errores útiles para verificar su ejecución', 'Solo su color de fuente', 'La contraseña en texto', 'Nada, siempre funciona', 'Los registros permiten saber qué sucedió sin una terminal interactiva.')
      ]),
      L('Respaldo antes de cambiar', [
        'Un cambio recuperable incluye una copia del estado previo y pasos para volver. Antes de editar configuración, registra el valor original y comprueba cómo validarlo. Una instantánea puede facilitar recuperación del sistema, pero su alcance depende de la herramienta y no siempre incluye documentos personales.',
        'rsync permite sincronizar árboles; con --dry-run muestra acciones previstas. La barra final del origen importa: origen/ representa su contenido. --delete puede borrar elementos del destino y debe entenderse antes de usarse. Comprueba respaldos restaurando un archivo de prueba.'
      ], 'rsync -av --dry-run ~/Documentos/ /ruta/a/respaldo/', 'Ejemplo de simulación: sustituye el destino por una ruta real de respaldo. No aplica cambios por usar --dry-run.', 'Describe qué datos cubre tu copia y qué harías para recuperar un archivo concreto.', [
        Q('¿Qué añade un plan de recuperación a un cambio?', 'Una forma conocida de volver al estado anterior', 'Una garantía de que nada puede fallar', 'Permisos ilimitados', 'La eliminación de toda configuración', 'Preparar la vuelta reduce el impacto de un fallo.'),
        Q('¿Qué hace --dry-run en rsync?', 'Mostrar cambios previstos sin aplicarlos', 'Borrar siempre el destino', 'Cifrar el origen', 'Apagar tras copiar', 'La simulación sirve para revisar acciones.'),
        Q('En rsync, ¿qué indica la barra final en origen/?', 'Copiar el contenido del directorio', 'Borrar el directorio necesariamente', 'Montar un disco', 'Solicitar una contraseña nueva', 'La barra final cambia cómo se interpreta el directorio de origen.'),
        Q('¿Qué riesgo introduce --delete en rsync?', 'Eliminar elementos del destino que no están en el origen', 'Borrar siempre el programa rsync', 'Cambiar todos los usuarios', 'Ocultar todos los archivos de origen', '--delete hace que el destino refleje también ausencias del origen.'),
        Q('¿Una instantánea de sistema incluye siempre tus documentos personales?', 'No, depende de su alcance y configuración', 'Sí, cualquier archivo de cualquier disco', 'Solo si el nombre tiene espacios', 'Sí, incluso archivos nunca guardados', 'Hay que verificar qué rutas protege cada herramienta.')
      ]),
      L('Un diagnóstico ordenado', [
        'Relaciona el síntoma con recursos y servicios: falta de espacio, memoria presionada o una unidad fallida requieren consultas distintas. Empieza por herramientas de observación, registra la hora y compara con el comportamiento esperado. Evita atribuir un problema a la primera cifra llamativa.',
        'Después de una intervención, vuelve a ejecutar la comprobación original. Documenta el cambio y conserva mensajes relevantes sin credenciales. Un reinicio puede ser necesario en ciertos cambios, pero no sustituye a identificar la causa. Distingue recuperación temporal de solución verificada.'
      ], 'systemctl --failed\ndf -h\nfree -h', 'Tres consultas independientes sobre unidades, almacenamiento y memoria. Interpreta cada una según el síntoma.', 'Una app no puede guardar: plantea primero una comprobación de espacio y permisos antes de proponer reinstalarla.', [
        Q('Si una aplicación no puede guardar, ¿qué comprobarías pronto?', 'Espacio y permisos del destino', 'Solo la velocidad del ratón', 'La cantidad de temas visuales', 'El número de pestañas del manual', 'Ambas condiciones pueden impedir crear o modificar archivos.'),
        Q('¿Qué dato ayuda a correlacionar un fallo con registros?', 'La hora aproximada del fallo', 'El color del escritorio', 'El largo del cable del teclado', 'El fondo de pantalla anterior', 'El tiempo permite acotar eventos relevantes.'),
        Q('¿Qué distingue una solución verificada?', 'Se comprueba que la operación original vuelve a funcionar', 'Solo se cierra la ventana de error', 'Se cambian varias cosas sin medir', 'Se elimina el registro', 'La verificación reproduce el caso que fallaba.'),
        Q('¿Un reinicio que elimina el síntoma demuestra por sí solo la causa?', 'No', 'Sí, siempre', 'Solo en equipos portátiles', 'Sí, si tarda poco', 'Recuperación temporal no equivale a diagnóstico causal.'),
        Q('¿Qué conviene documentar tras una intervención?', 'Qué cambió y qué prueba confirmó el resultado', 'Contraseñas completas', 'Solo que «se arregló»', 'El número de clics sin contexto', 'Un registro claro permite repetir o revertir la intervención.')
      ])
    ]
  });
})(globalThis);
