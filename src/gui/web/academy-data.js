/* Contenido original en español. Cada lección aporta cinco preguntas distintas.
 * Las opciones se rotan de forma estable para conservar respuestas al reabrir.
 * Los ejemplos son material de lectura: la academia no ejecuta comandos.
 */
(function (root) {
  'use strict';
  const Q = (text, correct, b, c, d, explanation) => ({ text, choices: [correct, b, c, d], answer: 0, explanation });
  const L = (title, paragraphs, command, detail, practice, questions) => ({ title, paragraphs, command, detail, practice, questions, minutes: 8 });
  const courses = [
    {
      id: 'fundamentos', title: 'Linux desde cero', subtitle: 'Tu primer paso hacia un sistema que entiendes.',
      category: 'Fundamentos', level: 'Principiante', color: 'violet', symbol: '>_', label: 'EMPIEZA AQUÍ',
      description: 'Conoce tu escritorio, organiza tus archivos y entiende cómo funciona Linux. Una base clara para empezar con confianza, incluso si vienes de Windows.',
      requirements: 'No necesitas experiencia. Solo un equipo con Linux o una máquina virtual para las prácticas opcionales.',
      outcomes: ['Entender el núcleo, la distribución y el escritorio.', 'Navegar por carpetas y reconocer rutas.', 'Interpretar permisos y elegir aplicaciones.', 'Consultar ayuda y trabajar con copias de seguridad.'],
      modules: ['Conoce tu sistema', 'Tu mapa de archivos', 'Trabaja con confianza', 'Aplicaciones y permisos', 'Autonomía digital'],
      resources: [['Manual de GNU Coreutils', 'https://www.gnu.org/software/coreutils/manual/coreutils.html'], ['Ayuda de Ubuntu', 'https://help.ubuntu.com/']],
      lessons: [
        L('Linux, el núcleo y tu distribución', [
          'Linux es el núcleo que coordina memoria, procesos y dispositivos. Una distribución añade herramientas, un gestor de paquetes y, normalmente, un escritorio. Ubuntu, Debian y Fedora son distribuciones: comparten Linux, pero sus versiones y herramientas pueden ser diferentes.',
          'El escritorio es la interfaz visual. GNOME y KDE Plasma son dos ejemplos; cambiar de escritorio no implica cambiar de núcleo. Para seguir una guía necesitas saber qué distribución y versión tienes. El archivo /etc/os-release contiene esa identificación; uname -r informa de la versión del núcleo.'
        ], 'cat /etc/os-release\nuname -r', 'El primer comando lee la identificación del sistema; el segundo muestra la versión del núcleo.', 'Anota el nombre de tu distribución y la versión del núcleo. Identifica cuál de los dos necesitarías para buscar instrucciones de instalación.', [
          Q('¿Cuál es la función principal del núcleo Linux?', 'Coordinar recursos y dispositivos', 'Dibujar únicamente los iconos', 'Almacenar solo documentos', 'Ser una tienda de aplicaciones', 'El núcleo conecta el software con los recursos de la máquina.'),
          Q('¿Qué es Ubuntu?', 'Una distribución de Linux', 'Un comando para listar archivos', 'Un tipo de memoria RAM', 'Un editor de texto', 'Una distribución integra el núcleo y un conjunto de herramientas.'),
          Q('¿Dónde consultarías la identificación de tu distribución?', '/etc/os-release', '/home/os-version', '/tmp/kernel.txt', '/usr/desktop-name', '/etc/os-release describe la distribución instalada.'),
          Q('¿Qué informa uname -r?', 'La versión del núcleo', 'La contraseña de root', 'Las aplicaciones disponibles', 'El espacio de la papelera', 'La opción -r de uname muestra el release del núcleo.'),
          Q('Instalas KDE en lugar de GNOME. ¿Qué componente cambias principalmente?', 'El entorno de escritorio', 'La arquitectura física del procesador', 'El formato de todos los documentos', 'La contraseña del firmware', 'GNOME y KDE son entornos de escritorio, no arquitecturas de hardware.')
        ]),
        L('Escritorio, sesión y espacios de trabajo', [
          'El escritorio reúne ventanas, un lanzador de aplicaciones y un panel de estado. Los espacios de trabajo permiten separar grupos de ventanas sin cerrarlas: por ejemplo, estudio en uno y correo en otro. Los atajos exactos dependen del escritorio y se consultan en su configuración.',
          'Bloquear conserva tu sesión y solicita autenticación al volver. Cerrar sesión finaliza tus aplicaciones de usuario; guarda antes los cambios. Apagar termina la sesión y detiene el equipo. En un equipo compartido conviene usar una cuenta personal y bloquearla cuando te alejas.'
        ], 'loginctl list-sessions', 'En sistemas con systemd, enumera las sesiones conocidas; no las cierra.', 'Busca las opciones Bloquear y Cerrar sesión en tu menú. Explica qué pasaría con un documento abierto en cada caso.', [
          Q('¿Para qué sirven los espacios de trabajo?', 'Agrupar ventanas en escritorios virtuales', 'Aumentar físicamente la RAM', 'Cambiar el sistema de archivos', 'Crear contraseñas automáticamente', 'Organizan las ventanas de una sesión.'),
          Q('Te alejas unos minutos. ¿Qué opción conserva la sesión y la protege?', 'Bloquear la pantalla', 'Cerrar sesión', 'Apagar el equipo', 'Eliminar la cuenta', 'El bloqueo mantiene tus aplicaciones abiertas y exige autenticación.'),
          Q('¿Qué debes hacer antes de cerrar sesión?', 'Guardar los documentos pendientes', 'Borrar tu carpeta personal', 'Cambiar el núcleo', 'Desinstalar el navegador', 'Cerrar sesión puede terminar las aplicaciones con trabajo sin guardar.'),
          Q('¿Dónde verificarías un atajo de teclado del escritorio?', 'En la configuración de teclado del entorno', 'En el nombre del procesador', 'En la etiqueta del monitor', 'En la papelera', 'Los atajos dependen del entorno y de su configuración.'),
          Q('¿Qué consulta loginctl list-sessions en systemd?', 'Las sesiones registradas', 'Los paquetes desinstalados', 'Las contraseñas en texto', 'Las particiones vacías', 'loginctl permite consultar sesiones; list-sessions las enumera.')
        ]),
        L('Terminal y shell: dos piezas diferentes', [
          'La terminal es la ventana donde escribes texto; la shell interpreta tus instrucciones. Bash es una shell común. Un comando suele tener nombre, opciones y argumentos: en ls -l Documentos, ls es el programa, -l es una opción y Documentos es el destino.',
          'El prompt indica que la shell está lista. En ejemplos escritos, el símbolo $ al inicio suele representar el prompt y no se copia. Linux distingue mayúsculas y minúsculas en muchos contextos: LS no suele ser el mismo comando que ls. Leer un comando antes de ejecutarlo evita sorpresas.'
        ], 'printf "Hola, Linux\\n"', 'printf escribe texto en la salida. Las comillas agrupan el mensaje y \\n produce un salto de línea.', 'Separa nombre, opción y argumento en ls -l Documentos. Luego explica qué parte de un ejemplo con prompt no se copia.', [
          Q('¿Qué componente interpreta las instrucciones escritas?', 'La shell', 'El monitor físico', 'El gestor de ventanas exclusivamente', 'La papelera', 'La shell analiza y ejecuta las instrucciones.'),
          Q('En ls -l Documentos, ¿qué es -l?', 'Una opción', 'El nombre del usuario', 'Una contraseña', 'Un espacio de trabajo', 'Las opciones ajustan el comportamiento del comando.'),
          Q('En un ejemplo que comienza con $ ls, ¿qué se escribe normalmente?', 'ls', '$ ls literalmente siempre', 'sudo $ ls', 'Solo $', 'El $ inicial suele representar el prompt, no el comando.'),
          Q('¿Por qué LS podría fallar aunque ls funcione?', 'Los nombres distinguen mayúsculas y minúsculas', 'La terminal no permite letras grandes', 'ls necesita conexión permanente', 'LS siempre requiere sudo', 'Los nombres de comandos suelen ser sensibles a mayúsculas.'),
          Q('¿Qué hace printf con una cadena de texto?', 'Escribe texto en la salida', 'Instala un controlador de impresora', 'Borra la pantalla permanentemente', 'Crea una cuenta', 'printf formatea y escribe datos en la salida estándar.')
        ]),
        L('Ubícate: rutas absolutas y relativas', [
          'Los archivos forman un árbol cuya raíz es /. Una ruta absoluta empieza con / y se interpreta desde esa raíz. Una ruta relativa se interpreta desde tu carpeta actual. pwd muestra esa carpeta, por eso es una buena primera comprobación antes de trabajar.',
          'El directorio personal suele ser /home/tu_usuario y la shell lo abrevia con ~. El punto representa la carpeta actual y los dos puntos representan la superior. /home/ana/Documentos es absoluta; Documentos/informe.txt es relativa. El nombre /root corresponde al directorio personal habitual del administrador, no a la raíz /.'
        ], 'pwd\nls ~', 'pwd muestra tu ubicación y ls ~ lista tu carpeta personal.', 'Si estás en /home/ana, escribe una ruta absoluta y una relativa para Documentos/nota.txt.', [
          Q('¿Qué comando muestra la carpeta de trabajo actual?', 'pwd', 'mkdir', 'passwd', 'reboot', 'pwd imprime el directorio de trabajo.'),
          Q('¿Cuál de estas rutas es absoluta?', '/home/ana/nota.txt', 'Documentos/nota.txt', './nota.txt', '../nota.txt', 'Las rutas absolutas comienzan con /.'),
          Q('¿Qué representa ~ sin comillas al inicio de una ruta de Bash?', 'La carpeta personal del usuario', 'La raíz siempre', 'El último archivo borrado', 'La unidad USB', 'Bash expande ~ al directorio personal.'),
          Q('Desde /home/ana, ¿a qué apunta Documentos/nota.txt?', '/home/ana/Documentos/nota.txt', '/Documentos/nota.txt', '/root/nota.txt', '/tmp/Documentos/nota.txt', 'La ruta relativa se añade a la carpeta actual.'),
          Q('¿Qué diferencia hay entre / y /root?', '/ es la raíz; /root suele ser el hogar de root', 'Son siempre la misma carpeta', '/root contiene solo archivos ocultos', '/ es la papelera del usuario', 'La raíz del árbol y el directorio personal de root son conceptos diferentes.')
        ]),
        L('Lista archivos y reconoce los ocultos', [
          'ls muestra entradas de una carpeta. Con -l añade detalles como permisos, propietario y tamaño. Con -a incluye las entradas que comienzan con punto, habitualmente ocultas en el explorador. Se pueden combinar opciones: ls -la.',
          'Oculto no significa cifrado ni protegido. .config suele contener ajustes de aplicaciones; no conviene borrarlo por parecer desconocido. Un nombre con punto inicial sigue siendo accesible con su ruta. La lista detallada empieza con un carácter de tipo: d señala un directorio y - suele indicar un archivo regular.'
        ], 'ls -la ~', 'Lista tu carpeta personal con detalles y entradas ocultas; no modifica archivos.', 'Localiza un nombre con punto inicial y una línea que comience con d. Distingue visibilidad de permisos.', [
          Q('¿Qué añade ls -a?', 'Entradas que comienzan con punto', 'Cifrado de todos los archivos', 'Instalación de aplicaciones', 'Un cambio de propietario', 'La opción -a incluye entradas ocultas.'),
          Q('¿Cuál de estos nombres suele estar oculto?', '.config', 'foto.png', 'Documentos', 'reporte.pdf', 'El punto inicial indica un nombre oculto por convención.'),
          Q('¿Qué aporta la opción -l de ls?', 'Un listado detallado', 'La eliminación de enlaces', 'Un bloqueo de pantalla', 'Un listado solo de vídeos', 'El formato largo incluye permisos, propietario y otros metadatos.'),
          Q('¿Un archivo oculto está necesariamente cifrado?', 'No; ocultar el nombre no cifra el contenido', 'Sí, siempre con la contraseña de root', 'Sí, si comienza con dos puntos', 'Solo cuando está en /home', 'La visibilidad y el cifrado son independientes.'),
          Q('En ls -l, ¿qué suele significar d al principio de una entrada?', 'Directorio', 'Documento dañado', 'Descarga pendiente', 'Dispositivo desconectado', 'El primer carácter describe el tipo de entrada.')
        ]),
        L('Cambia de carpeta sin perderte', [
          'cd cambia el directorio de trabajo de tu shell. cd .. sube al padre; cd sin argumentos vuelve a tu hogar. cd - vuelve al directorio de trabajo anterior, que no tiene por qué ser el padre. El cambio afecta a esa shell, no mueve archivos.',
          'Los espacios separan argumentos, así que una ruta como Mis notas debe ir entre comillas. cd "Mis notas" trata el nombre completo como un argumento. Después de cambiar de carpeta, usa pwd para confirmar el destino. Si aparece No such file or directory, revisa la ruta y sus mayúsculas.'
        ], 'cd ~\npwd\ncd ..\npwd', 'Primero vas al hogar; luego subes a su carpeta superior y verificas ambos destinos.', 'Si antes estabas en /tmp y ahora en /home/ana, distingue el destino de cd .. del de cd -.', [
          Q('¿Qué hace cd ..?', 'Cambia al directorio superior', 'Elimina dos archivos', 'Vuelve siempre al hogar', 'Cambia la contraseña', '.. designa la carpeta superior.'),
          Q('¿Qué hace cd sin argumentos en Bash?', 'Va al directorio personal', 'Lista dispositivos', 'Reinicia la terminal', 'Sube dos niveles', 'cd utiliza HOME cuando no recibe un destino.'),
          Q('¿Cómo entrarías a una carpeta llamada Mis notas?', 'cd "Mis notas"', 'cd Mis notas como dos argumentos', 'ls "Mis notas"', 'pwd "Mis notas"', 'Las comillas conservan el espacio dentro del nombre.'),
          Q('¿Qué representa el destino de cd -?', 'El directorio de trabajo anterior', 'Siempre la raíz', 'Siempre la carpeta superior', 'El primer archivo oculto', 'cd - utiliza el directorio anterior de la shell.'),
          Q('¿Qué efecto tiene cd sobre tus documentos?', 'Cambia tu ubicación sin mover los archivos', 'Los reordena en el disco', 'Los cifra', 'Los envía a la papelera', 'cd modifica el contexto de la shell, no el contenido de las carpetas.')
        ]),
        L('El árbol de Linux', [
          '/home suele reunir carpetas de usuarios. /etc contiene configuración del sistema. /var alberga datos variables, como registros y colas; muchos registros tradicionales se encuentran en /var/log. /tmp se usa para archivos temporales y puede limpiarse automáticamente.',
          '/usr contiene gran parte de los programas y recursos instalados. /dev representa dispositivos mediante archivos especiales. Este mapa ayuda a interpretar rutas; no hace falta modificar esas carpetas para aprender. Guarda documentos duraderos en tu hogar, no en /tmp.'
        ], 'ls /\nls /etc', 'Consulta nombres de carpetas y archivos, sin editar la configuración.', 'Asocia configuración, registros, dispositivos y documentos personales con sus directorios habituales.', [
          Q('¿Dónde suele estar la configuración general del sistema?', '/etc', '/tmp', '/dev', '/home/config-siempre', '/etc reúne archivos de configuración del sistema.'),
          Q('¿Dónde se encuentran muchos registros tradicionales?', '/var/log', '/usr/pictures', '/dev/logs-personales', '/home/kernel', '/var/log es una ubicación habitual para registros.'),
          Q('¿Por qué /tmp no es buena ubicación para una única copia importante?', 'Puede limpiarse automáticamente', 'Siempre está cifrado', 'No admite texto', 'Solo acepta archivos de root', 'El contenido temporal no debe considerarse almacenamiento duradero.'),
          Q('¿Qué representa normalmente /dev?', 'Dispositivos mediante archivos especiales', 'Documentos de desarrollo exclusivamente', 'Vídeos personales', 'Solo aplicaciones de escritorio', '/dev ofrece representaciones de dispositivos.'),
          Q('¿Dónde guardarías normalmente tus apuntes personales?', 'En una carpeta de tu hogar', 'En /dev', 'Dentro de /etc/kernel', 'En /usr/bin', 'Tu directorio personal es el lugar habitual para documentos de usuario.')
        ]),
        L('Crear, copiar y mover con cuidado', [
          'mkdir crea directorios. cp copia archivos y deja el original. mv mueve o renombra: en el caso simple, el origen deja de estar en su ruta anterior. Para practicar, usa una carpeta nueva dentro de tu hogar y nombres que no contengan trabajo real.',
          'Un destino existente puede sobrescribirse. La opción -i en cp y mv solicita confirmación antes de sobrescribir. Una copia en el mismo disco ayuda ante un cambio accidental, pero no protege de perder ese disco. Revisa primero origen y destino.'
        ], 'mkdir -p ~/practica-linux\ncd ~/practica-linux\nprintf "Mi primera nota\\n" > nota.txt\ncp -i nota.txt copia.txt', 'Crea una carpeta de práctica y una copia. La redirección > escribe nota.txt; usa un nombre nuevo para evitar sobrescribir algo anterior.', 'Dibuja el estado de nota.txt y copia.txt tras copiar. Luego predice qué cambiaría al renombrar copia.txt con mv.', [
          Q('¿Qué comando crea un directorio?', 'mkdir', 'pwd', 'uname', 'whoami', 'mkdir crea directorios.'),
          Q('Después de cp origen.txt copia.txt, si todo sale bien, ¿qué ocurre?', 'Existen origen y copia', 'Se borra siempre el origen', 'Se cifra el destino', 'Se cambia el usuario', 'cp conserva el archivo original y crea o reemplaza el destino.'),
          Q('¿Qué comando permite renombrar un archivo?', 'mv', 'cat', 'ls', 'man', 'mv mueve o renombra una entrada.'),
          Q('¿Para qué usar cp -i?', 'Pedir confirmación antes de sobrescribir', 'Ignorar todos los errores', 'Convertir imágenes', 'Instalar el archivo', '-i activa la confirmación interactiva para sobrescrituras.'),
          Q('¿Qué debes revisar antes de copiar un archivo importante?', 'El origen y si el destino ya existe', 'Solo el color de la terminal', 'La resolución del monitor', 'El número de espacios de trabajo', 'Comprobar las rutas evita sobrescribir el archivo equivocado.')
        ]),
        L('Lee archivos y usa la ayuda', [
          'cat vuelca el contenido de archivos en la terminal. less permite recorrer textos largos sin mostrarlos de golpe; q sale del visor. head enseña el inicio y tail el final. Leer un archivo no es editarlo.',
          'Muchos programas aceptan --help. man abre páginas de manual cuando están instaladas: man ls explica opciones y uso. Consulta el manual de tu sistema porque las opciones pueden variar entre implementaciones. Para un archivo binario, como una imagen, usa una aplicación apropiada en lugar de cat.'
        ], 'ls --help\nman ls', 'Muestra ayuda breve y, si está instalado el manual, una referencia más completa. Pulsa q para salir del visor del manual.', 'Elige entre cat, less y tail para una nota corta, un manual extenso y las últimas líneas de un registro.', [
          Q('¿Qué herramienta es cómoda para recorrer un archivo de texto largo?', 'less', 'mkdir', 'mv', 'passwd', 'less es un visor paginado.'),
          Q('¿Con qué tecla sales normalmente de less?', 'q', 'La letra z obligatoriamente', 'Solo apagando el equipo', 'La tecla de impresión', 'La tecla q cierra el visor less y devuelve el control a la shell.'),
          Q('¿Qué consulta man ls?', 'El manual de ls', 'Los usuarios conectados', 'El contenido del disco completo', 'El número de paquetes', 'man busca la página de manual del comando.'),
          Q('¿Qué comando muestra el final de un texto?', 'tail', 'head', 'mkdir', 'cd', 'tail muestra las últimas líneas.'),
          Q('¿Qué opción ofrece ayuda breve en muchos comandos?', '--help', '--erase', '--root-only', '--password', '--help es una convención ampliamente utilizada.')
        ]),
        L('Usuarios y permisos básicos', [
          'Cada archivo tiene propietario y grupo. En el modo tradicional hay permisos para propietario, grupo y otros. r permite leer; w permite escribir; x permite ejecutar un archivo. En directorios, x permite atravesar la ruta y acceder a entradas conocidas; r permite listar sus nombres.',
          'whoami muestra el usuario efectivo e id muestra identificadores y grupos. En ls -l, tras el carácter de tipo aparecen tres grupos de permisos. rw-r--r-- concede lectura y escritura al propietario, y solo lectura al grupo y a otros. Los permisos deben responder a una necesidad concreta.'
        ], 'whoami\nid\nls -l', 'Consulta tu identidad, tus grupos y los permisos de la carpeta actual.', 'Interpreta rw-r--r-- por bloques. Explica por qué no permite ejecutar el archivo como programa.', [
          Q('¿Qué significa w en permisos de un archivo?', 'Escritura', 'Wi-Fi', 'Archivo oculto', 'Propiedad de Windows', 'w corresponde a write: escribir o modificar.'),
          Q('¿Qué grupos describe el modo tradicional de permisos?', 'Propietario, grupo y otros', 'RAM, disco y pantalla', 'Inicio, pausa y fin', 'Local, nube y papelera', 'Los bits se organizan en esas tres clases.'),
          Q('Con rw-r--r--, ¿quién tiene permiso de escritura según esos bits?', 'Solo el propietario', 'Todos los usuarios', 'Solo otros', 'Nadie', 'Solo el primer bloque contiene w.'),
          Q('¿Qué consulta whoami?', 'El usuario efectivo', 'El fabricante del disco', 'Las contraseñas de otros', 'El nombre de la red', 'whoami imprime la identidad efectiva del proceso.'),
          Q('¿Qué permite x sobre un directorio?', 'Atravesarlo y acceder a entradas conocidas', 'Ejecutar todos sus archivos sin restricciones', 'Cifrar su contenido', 'Hacer copias automáticamente', 'La ejecución en directorios se interpreta como búsqueda o travesía.')
        ]),
        L('sudo y decisiones con privilegios', [
          'sudo solicita ejecutar una orden con otra identidad, normalmente root, según la política del sistema. No arregla errores por sí mismo. root dispone de privilegios amplios; un destino equivocado con esos permisos puede afectar a todo el sistema.',
          'Al escribir una contraseña en una terminal puede no aparecer ningún carácter: es normal. Una petición de privilegios debe corresponder a una acción que entiendas. Antes de aceptar, identifica el programa, las opciones y la ruta. Para leer tus propios documentos normalmente no necesitas sudo.'
        ], 'sudo -l', 'Lista los permisos que la política de sudo te concede; puede solicitar autenticación.', 'Compara consultar un archivo tuyo con instalar un paquete del sistema. Justifica cuál puede necesitar privilegios.', [
          Q('¿Qué pide sudo normalmente?', 'Ejecutar una orden con privilegios de otra identidad', 'Aumentar la velocidad de cualquier programa', 'Conectarse automáticamente a internet', 'Crear una copia de cada archivo', 'sudo controla la ejecución con otra identidad según una política.'),
          Q('No aparecen caracteres al escribir la contraseña en la terminal. ¿Qué puede significar?', 'Que la entrada está oculta deliberadamente', 'Que el teclado está siempre roto', 'Que la cuenta fue borrada', 'Que el disco está lleno necesariamente', 'Es normal que las contraseñas no se reflejen en pantalla.'),
          Q('¿Necesitas sudo para leer normalmente tus propios documentos?', 'No, si ya tienes permiso de lectura', 'Sí, para todo archivo de texto', 'Sí, siempre al usar cat', 'Solo por estar en Linux', 'Tus permisos de usuario suelen bastar para tus documentos.'),
          Q('¿Qué comprobarías antes de aceptar una orden con sudo?', 'Su propósito, opciones y destinos', 'Solo si incluye muchos caracteres', 'El color del prompt', 'La cantidad de iconos del escritorio', 'Los privilegios aumentan el impacto de una orden equivocada.'),
          Q('¿Qué muestra sudo -l?', 'Las operaciones permitidas por la política de sudo', 'El listado de películas', 'Una clave SSH nueva', 'La versión del navegador', '-l consulta los privilegios autorizados para el usuario.')
        ]),
        L('Aplicaciones, paquetes y repositorios', [
          'Un paquete agrupa archivos de un programa y metadatos, como versión y dependencias. Un repositorio publica paquetes para un gestor. En Debian y Ubuntu, APT consulta repositorios y gestiona instalaciones; no es el gestor universal de todas las distribuciones.',
          'apt search busca y apt show muestra información. Estas consultas no instalan. Snap y Flatpak son otros sistemas de distribución de aplicaciones, con sus propios orígenes y actualizaciones. Revisa nombre, procedencia y compatibilidad antes de instalar; una aplicación conocida puede existir en más de un formato.'
        ], 'apt search vlc\napt show vlc', 'En Debian o Ubuntu consulta paquetes de VLC y la ficha del paquete principal, sin instalarlo.', 'Distingue aplicación, paquete y repositorio con un ejemplo de un reproductor multimedia.', [
          Q('¿Qué hace apt search vlc?', 'Busca paquetes relacionados con VLC', 'Instala VLC inmediatamente', 'Elimina sus preferencias', 'Abre un vídeo', 'search consulta el catálogo sin instalar.'),
          Q('¿Qué es una dependencia de un paquete?', 'Otro componente que necesita para funcionar', 'La contraseña del usuario', 'Un archivo siempre innecesario', 'Una cuenta en la nube obligatoria', 'Las dependencias expresan requisitos de otros paquetes.'),
          Q('¿En qué familia se usa habitualmente APT?', 'Debian y Ubuntu', 'Todas sin excepción', 'Solo Android', 'Solo macOS', 'APT es habitual en distribuciones basadas en Debian.'),
          Q('¿Qué aporta apt show nombre?', 'Metadatos del paquete', 'Una instalación sin preguntar', 'La desactivación de la red', 'Un cambio del escritorio', 'show presenta información como descripción y dependencias.'),
          Q('¿Qué conviene revisar al elegir una fuente de software?', 'Su procedencia y compatibilidad', 'Solo el tamaño del icono', 'Solo si el nombre es corto', 'El número de ventanas abiertas', 'La procedencia y compatibilidad ayudan a elegir paquetes adecuados.')
        ]),
        L('Procesos y recursos', [
          'Un proceso es una instancia de un programa en ejecución. Su PID lo identifica durante su vida. Un programa puede crear varios procesos; el PID no es un identificador permanente de la aplicación. ps presenta una instantánea y top ofrece una vista que se actualiza.',
          'CPU, memoria y disco miden recursos diferentes. free -h resume memoria y df -h muestra uso de sistemas de archivos. Memoria usada como caché puede recuperarse; una cifra alta de uso no basta para diagnosticar un problema. Observa síntomas y varios indicadores antes de actuar.'
        ], 'ps -u "$USER"\nfree -h\ndf -h', 'Consulta procesos de tu usuario, memoria y espacio de los sistemas de archivos.', 'Decide qué consulta usar ante poco espacio para guardar un vídeo y cuál ante una aplicación que consume mucha memoria.', [
          Q('¿Qué es un proceso?', 'Una instancia de un programa en ejecución', 'Un paquete sin instalar', 'Una carpeta vacía', 'Un permiso de lectura', 'Un proceso representa ejecución activa.'),
          Q('¿Qué identifica un PID?', 'Un proceso durante su vida', 'Una aplicación para siempre', 'La contraseña de la cuenta', 'La versión del escritorio', 'Los PID pueden reutilizarse tras terminar procesos.'),
          Q('¿Qué muestra free -h?', 'Información de memoria en unidades legibles', 'Todos los archivos gratuitos', 'El estado de la impresora', 'El catálogo de APT', 'free resume memoria física y swap.'),
          Q('¿Qué consulta df -h?', 'Uso de espacio de sistemas de archivos', 'Temperatura de la pantalla', 'Usuarios de una web', 'Historial del navegador', 'df presenta espacio usado y disponible.'),
          Q('¿Por qué memoria usada alta no prueba por sí sola una avería?', 'Parte puede ser caché recuperable', 'Linux no utiliza memoria', 'La memoria siempre es infinita', 'El uso solo mide disco', 'La caché aprovecha RAM disponible y puede liberarse cuando haga falta.')
        ]),
        L('Copias de seguridad y recuperación', [
          'Una copia de seguridad es una copia que puedes recuperar. Debe existir fuera del único lugar que puede fallar: otro disco, una ubicación remota o ambos. Sincronizar no equivale siempre a respaldar: una eliminación puede propagarse.',
          'Una estrategia habitual mantiene tres copias, en dos tipos de soporte, con una fuera del sitio. Lo esencial es probar la restauración y proteger datos sensibles. La papelera del escritorio puede recuperar ciertas eliminaciones, pero rm normalmente no la utiliza. Antes de borrar, revisa la ruta y verifica que hay una copia útil.'
        ], 'ls -lh ~/Documentos', 'Ayuda a identificar documentos que incluirías en un respaldo. No crea una copia.', 'Elige un archivo de prueba, cópialo a un soporte aparte y comprueba que puedes abrir la copia. No uses tu única copia importante.', [
          Q('¿Qué confirma que un respaldo es útil?', 'Poder restaurar y abrir sus archivos', 'Que su carpeta tenga un buen nombre', 'Que esté siempre en el mismo directorio', 'Que nunca se revise', 'Una prueba de recuperación comprueba la utilidad del respaldo.'),
          Q('¿Qué riesgo comparte una copia en el mismo disco?', 'Perderse si falla ese disco', 'No poder contener texto', 'Estar siempre vacía', 'No tener permisos nunca', 'El fallo del soporte puede afectar al original y a la copia.'),
          Q('¿Por qué sincronización y respaldo no siempre son equivalentes?', 'Una eliminación puede sincronizarse también', 'La sincronización solo funciona en papel', 'Un respaldo no contiene archivos', 'Siempre tienen el mismo historial', 'Sin versiones o protección, el cambio destructivo puede propagarse.'),
          Q('¿rm envía normalmente los archivos a la papelera del escritorio?', 'No', 'Sí, siempre', 'Solo por usar Bash', 'Sí, si el nombre contiene espacios', 'rm elimina entradas sin usar normalmente la papelera gráfica.'),
          Q('En la estrategia 3-2-1, ¿qué significa el 1?', 'Una copia fuera del sitio', 'Un único archivo', 'Una contraseña de un carácter', 'Un solo disco para todo', 'La copia externa protege ante incidentes en una misma ubicación.')
        ]),
        L('Aprender a resolver un problema', [
          'Un diagnóstico empieza con un síntoma concreto: qué querías hacer, qué ocurrió y desde cuándo. Anota el mensaje exacto y reproduce el problema de forma controlada. Recoger datos suele ser menos arriesgado que cambiar opciones al azar.',
          'Consulta la ayuda correspondiente a tu distribución y versión. Aplica un cambio a la vez y verifica su efecto; conserva una forma de volver atrás. Si pides ayuda, comparte pasos y mensajes útiles, ocultando claves y datos personales. Una buena pregunta permite que otra persona entienda y reproduzca el fallo.'
        ], 'uname -r\ncat /etc/os-release', 'Recoge versiones útiles para explicar el entorno al pedir ayuda.', 'Redacta un reporte de tres líneas: objetivo, pasos y error exacto. Añade qué cambió antes del fallo.', [
          Q('¿Cuál es un buen primer paso de diagnóstico?', 'Definir el síntoma y registrar el error', 'Reinstalar todo inmediatamente', 'Borrar /etc', 'Cambiar muchas opciones a la vez', 'Una descripción precisa orienta la investigación.'),
          Q('¿Por qué conviene cambiar una cosa cada vez?', 'Para relacionar el cambio con su efecto', 'Para usar más espacio', 'Para ocultar el error', 'Porque Linux prohíbe varios ajustes', 'Aislar cambios facilita identificar causas.'),
          Q('¿Qué hace más útil una solicitud de ayuda?', 'Pasos reproducibles y mensaje exacto', 'Solo decir «no funciona»', 'Compartir contraseñas', 'Enviar únicamente el color de fondo', 'Los pasos y el error permiten reconstruir el problema.'),
          Q('¿Qué dato debes ocultar antes de compartir registros?', 'Claves y tokens privados', 'El nombre genérico del comando', 'El tipo de distribución', 'Una opción documentada', 'Los registros pueden contener secretos que no hacen falta para diagnosticar.'),
          Q('¿Cómo verificas que una solución funcionó?', 'Repitiendo la operación y comprobando el resultado', 'Cerrando el reporte sin probar', 'Cambiando el nombre del equipo', 'Ignorando nuevos errores', 'La verificación conecta la solución con el síntoma original.')
        ])
      ]
    }
  ];
  // Los siguientes cursos se incorporan antes de preparar índices y preguntas.
  root.AcademyCourses = courses;
  root.AcademyContent = { Q, L };
})(typeof globalThis !== 'undefined' ? globalThis : this);
