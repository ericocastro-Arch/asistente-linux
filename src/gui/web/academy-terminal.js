(function (root) {
  'use strict';
  const { Q, L } = root.AcademyContent;
  root.AcademyCourses.push({
    id: 'terminal', title: 'Domina la terminal', subtitle: 'De tu primer comando a tus propios scripts.',
    category: 'Terminal', level: 'Principiante', color: 'mint', symbol: '$_', label: 'APRENDE HACIENDO',
    description: 'Navega, encuentra archivos y transforma texto con Bash. Aprende a conectar comandos y escribe pequeños scripts que puedas entender y mantener.',
    requirements: 'Conocer carpetas y rutas. Recomendamos completar Linux desde cero. Los ejemplos usan Bash y herramientas GNU.',
    outcomes: ['Manejar comillas, variables y expansiones.', 'Buscar y transformar archivos de texto.', 'Combinar tuberías y redirecciones.', 'Crear scripts con condiciones y bucles.'],
    modules: ['Habla con la shell', 'Encuentra y organiza', 'Procesa información', 'Conecta comandos', 'Tus primeros scripts'],
    resources: [['Manual de Bash', 'https://www.gnu.org/software/bash/manual/bash.html'], ['Manual de GNU Grep', 'https://www.gnu.org/software/grep/manual/grep.html']],
    lessons: [
      L('Argumentos, comillas y espacios', [
        'Bash separa palabras por espacios sin comillas. Un nombre como informe final.txt necesita agruparse para representar un solo argumento. Las comillas simples conservan literalmente su contenido; las dobles conservan el grupo, pero permiten expansiones como $HOME.',
        'La barra inversa puede escapar un carácter. Al construir comandos con nombres de archivos, las comillas dobles alrededor de variables suelen evitar divisiones inesperadas. Las comillas son sintaxis de la shell: normalmente no forman parte del nombre que recibe el programa.'
      ], 'printf "%s\\n" "informe final.txt"\nprintf \'%s\\n\' \'$HOME\'', 'La primera orden trata el nombre con espacio como un argumento. La segunda muestra $HOME literalmente.', 'Predice la diferencia entre printf "%s\\n" "$HOME" y la misma orden con comillas simples alrededor de $HOME.', [
        Q('¿Cómo agruparías un nombre que contiene espacios?', 'Con comillas alrededor del nombre', 'Añadiendo sudo', 'Borrando la extensión siempre', 'Escribiendo el nombre dos veces', 'Las comillas impiden separar ese espacio en argumentos.'),
        Q('¿Qué hacen las comillas simples de Bash con $HOME?', 'Lo conservan como texto literal', 'Lo expanden siempre', 'Borran la variable', 'Cambian de directorio', 'Dentro de comillas simples no hay expansión de variables.'),
        Q('¿Qué permiten las comillas dobles alrededor de $HOME?', 'Expandir la variable manteniéndola como un argumento', 'Ejecutar su contenido como root', 'Eliminar espacios del nombre', 'Convertirlo en comentario', 'Las comillas dobles permiten expansión y conservan la agrupación.'),
        Q('¿Quién interpreta normalmente las comillas de una línea de comandos?', 'La shell', 'El disco duro', 'El servidor DNS', 'La impresora', 'La shell procesa la sintaxis antes de invocar el programa.'),
        Q('¿Para qué sirve escapar un espacio con barra inversa?', 'Tratarlo como parte de una palabra', 'Ir al directorio raíz', 'Invocar una segunda shell', 'Activar el historial', 'El escape evita el significado separador del espacio.')
      ]),
      L('Variables y entorno', [
        'Una variable se asigna con nombre=valor, sin espacios junto al signo igual. Se consulta con $nombre o ${nombre}. Los nombres distinguen mayúsculas. Una variable de shell no se convierte automáticamente en parte del entorno de los procesos hijos.',
        'export marca una variable para transmitirla a los procesos que se inicien desde esa shell. HOME suele identificar el hogar; PATH es la lista de carpetas donde se buscan comandos sin ruta. Modificar PATH afecta cómo se encuentran ejecutables; evita reemplazarlo sin entenderlo.'
      ], 'saludo="Hola Linux"\nprintf "%s\\n" "$saludo"\nexport CURSO_LINUX="terminal"', 'Define una variable local, la muestra y exporta una variable de práctica para futuros procesos hijos.', 'Explica por qué saludo = hola no equivale a saludo=hola y qué añade export.', [
        Q('¿Cuál es una asignación válida en Bash?', 'nombre=Ana', 'nombre = Ana', '$nombre=Ana', 'set nombre : Ana', 'La asignación no admite espacios alrededor de =.'),
        Q('¿Cómo consultas la variable saludo?', '"$saludo"', 'saludo$()', 'get.saludo', 'sudo saludo', 'El signo $ solicita la expansión de la variable.'),
        Q('¿Qué hace export con una variable?', 'La incluye en el entorno de procesos hijos', 'La guarda siempre en un archivo', 'La envía a internet', 'La cifra automáticamente', 'export transmite la variable al entorno de nuevos procesos.'),
        Q('¿Qué describe PATH?', 'Directorios donde buscar ejecutables', 'El espacio libre del disco', 'El historial de red', 'La carpeta de la papelera únicamente', 'PATH es una lista de rutas de búsqueda de comandos.'),
        Q('¿Son nombre y NOMBRE la misma variable en Bash?', 'No, son nombres distintos', 'Sí, siempre', 'Solo después de export', 'Solo dentro de comillas', 'Bash distingue mayúsculas en nombres de variables.')
      ]),
      L('Comodines y expansión de nombres', [
        'Bash puede expandir patrones de nombres antes de ejecutar un programa. * coincide con una secuencia de caracteres y ? con un carácter. [ab] coincide con a o b. No son las mismas reglas que las expresiones regulares usadas por grep.',
        'En el comportamiento habitual, * no incluye nombres con punto inicial. Un patrón entre comillas se pasa literalmente, lo que resulta útil cuando otra herramienta debe interpretarlo. Si no hay coincidencias, Bash normalmente deja el patrón sin expandir, salvo opciones como nullglob o failglob.'
      ], 'printf "%s\\n" *.txt', 'Muestra los nombres coincidentes en la carpeta actual. Sin coincidencias, la configuración habitual puede mostrar literalmente *.txt.', 'Con nota.txt, foto.png y .secreto.txt, predice qué nombres alcanza *.txt en Bash con su configuración habitual.', [
        Q('En un patrón de Bash, ¿con qué coincide *?', 'Una secuencia de caracteres', 'Solo un dígito', 'Solo un punto', 'Una ruta remota siempre', '* representa una secuencia, incluida la vacía.'),
        Q('¿Qué representa ? en un patrón de nombres?', 'Un carácter', 'Un comentario', 'Cualquier número de carpetas siempre', 'El código de salida', '? coincide con un único carácter.'),
        Q('¿Qué ocurre normalmente con los nombres que empiezan con punto al usar *?', 'No se incluyen', 'Se borran', 'Se cifran', 'Son los únicos incluidos', 'Los nombres ocultos necesitan un patrón apropiado o cambiar opciones.'),
        Q('¿Por qué escribir "*.txt" como argumento para find?', 'Para que find reciba el patrón sin expansión previa', 'Para ejecutar find como administrador', 'Para convertir archivos a texto', 'Para crear una carpeta', 'Las comillas dejan la interpretación del patrón a find.'),
        Q('En Bash habitual sin coincidencias, ¿qué puede recibir printf con *.txt?', 'El texto literal *.txt', 'Siempre cero argumentos', 'Todos los archivos del sistema', 'Una contraseña', 'Sin nullglob o failglob, un patrón sin coincidencias queda literal.')
      ]),
      L('Busca archivos con find', [
        'find recorre un árbol desde una ruta de inicio y evalúa condiciones. -type f selecciona archivos regulares, -type d directorios, -name patrones de nombre y -iname ignora diferencias de mayúsculas. Limitar la ruta hace la búsqueda más clara y rápida.',
        'Comienza con una búsqueda que solo liste. Las condiciones combinadas consecutivamente funcionan como una conjunción habitual: -type f -name "*.txt" exige ambas. Algunas acciones, como -delete, modifican archivos; no hacen falta para encontrar. Una ruta inaccesible puede producir Permission denied sin invalidar las coincidencias accesibles.'
      ], 'find ~/Documentos -type f -name "*.txt"', 'Busca archivos regulares con extensión .txt dentro de Documentos. Ajusta la carpeta si no existe.', 'Describe cómo cambiarías la búsqueda para localizar directorios llamados proyecto, sin borrarlos.', [
        Q('¿Qué selecciona find -type f?', 'Archivos regulares', 'Solo directorios', 'Procesos en primer plano', 'Paquetes Flatpak', '-type f filtra archivos regulares.'),
        Q('¿Qué condición de find ignora mayúsculas en el nombre?', '-iname', '-root', '-case-sensitive', '-exec-only', '-iname compara nombres sin distinguir mayúsculas.'),
        Q('¿Qué indica la primera ruta después de find?', 'El punto inicial del recorrido', 'Un archivo que siempre se borra', 'La contraseña de búsqueda', 'El destino de una copia', 'find recorre desde las rutas que recibe.'),
        Q('¿Qué significa combinar -type f y -name "*.txt" sin otro operador?', 'Exigir que se cumplan ambas condiciones', 'Elegir una al azar', 'Buscar solo carpetas ocultas', 'Desactivar los filtros', 'Las condiciones consecutivas se combinan normalmente con AND.'),
        Q('¿Qué acción evitarías en una búsqueda destinada solo a observar?', '-delete', '-name', '-type', '-print', '-delete elimina coincidencias; no es necesaria para listarlas.')
      ]),
      L('Busca contenido con grep', [
        'grep selecciona líneas que coinciden con un patrón. -n añade números de línea; -i ignora mayúsculas y -v invierte la selección. Si buscas texto literal con símbolos especiales, -F evita interpretarlos como una expresión regular.',
        'Buscar contenido no es buscar nombres: find trabaja principalmente con entradas y sus atributos; grep con líneas de texto. Con grep -n "error" app.log obtienes coincidencias y ubicación dentro del archivo. Un resultado vacío puede significar que no hubo coincidencias, no que el archivo esté dañado.'
      ], 'printf "Inicio\\nError de prueba\\nFinal\\n" | grep -ni "error"', 'Crea tres líneas en memoria y filtra la que contiene error, sin distinguir mayúsculas y con número de línea.', 'Predice qué líneas devolvería grep -v "Inicio" para el texto del ejemplo.', [
        Q('¿Qué busca grep principalmente?', 'Líneas que coinciden con un patrón', 'Solo nombres de carpetas', 'Discos vacíos', 'Aplicaciones instalables', 'grep filtra contenido textual por líneas.'),
        Q('¿Qué añade grep -n?', 'Números de línea', 'Privilegios de administrador', 'Un archivo nuevo obligatorio', 'Cifrado', '-n muestra la posición de cada línea coincidente.'),
        Q('¿Qué permite grep -i?', 'Ignorar mayúsculas y minúsculas', 'Invertir todos los bytes', 'Instalar un patrón', 'Ignorar el archivo entero', '-i realiza comparaciones sin distinguir el caso.'),
        Q('¿Qué selecciona grep -v?', 'Líneas que no coinciden', 'Solo la primera línea', 'Solo archivos de vídeo', 'Líneas vacías siempre', '-v invierte la selección del patrón.'),
        Q('¿Qué opción usarías para buscar a.b literalmente?', '-F', '-r como única solución', '-delete', '-sudo', '-F interpreta patrones como cadenas fijas.')
      ]),
      L('Archivos comprimidos y tar', [
        'tar agrupa archivos en un archivo contenedor; comprimir es un paso distinto. En tar -czf, c crea, z usa gzip y f indica el nombre del archivo contenedor. Un archivo .tar puede estar sin compresión; .tar.gz suele combinar ambas operaciones.',
        't lista el contenido y x lo extrae. Antes de extraer un archivo ajeno, consulta su contenido y usa un directorio de destino separado. Eso facilita revisar rutas y evita mezclar archivos con tu trabajo. La compresión por sí sola no cifra ni crea una copia fuera del disco.'
      ], 'tar -czf practica.tar.gz practica-linux/\ntar -tzf practica.tar.gz', 'Si existe practica-linux, crea un archivo comprimido y luego lista su contenido. Usa un nombre de salida nuevo.', 'Explica por qué listar el contenido antes de extraer puede evitar sorpresas en la carpeta de destino.', [
        Q('¿Cuál es la función básica de tar?', 'Agrupar archivos en un contenedor', 'Cifrar siempre con contraseña', 'Actualizar el núcleo', 'Medir tráfico de red', 'tar empaqueta; la compresión puede añadirse.'),
        Q('¿Qué significa c en tar -czf?', 'Crear un archivo contenedor', 'Cerrar sesión', 'Copiar al portapapeles', 'Consultar CPU', 'c selecciona la operación de creación.'),
        Q('¿Qué hace tar -tzf archivo.tar.gz?', 'Lista el contenido', 'Lo elimina', 'Lo instala como paquete', 'Lo extrae siempre en /', 't lista; z indica gzip; f señala el archivo.'),
        Q('¿Qué operación de tar extrae archivos?', 'x', 't', 'c', 'v por sí sola', 'x selecciona extracción.'),
        Q('¿Qué protección proporciona la compresión por sí sola?', 'Reduce tamaño cuando es posible, pero no cifra', 'Impide leer sin contraseña siempre', 'Evita cualquier fallo del disco', 'Bloquea todos los virus', 'Comprimir y cifrar son operaciones distintas.')
      ]),
      L('Ordena y cuenta líneas', [
        'sort ordena líneas; -n compara valores numéricos y -r invierte el orden. Sin -n, una comparación textual puede situar 10 antes de 2. El idioma y la configuración regional también pueden afectar al orden.',
        'uniq elimina repeticiones consecutivas, no todas las repetidas dispersas. Combinar sort con uniq agrupa primero los duplicados. uniq -c cuenta cada grupo. wc -l cuenta saltos de línea: un archivo cuya última línea no termina en salto puede dar una cuenta menor que la esperada visualmente.'
      ], 'printf "pera\\nmanzana\\npera\\n" | sort | uniq -c', 'Ordena tres líneas y cuenta dos peras y una manzana.', 'Predice la salida de ordenar 2, 10 y 1 como texto y como números.', [
        Q('¿Qué opción de sort compara valores numéricos?', '-n', '-i como única función', '-x', '-sudo', '-n habilita comparación numérica.'),
        Q('¿Qué duplicados elimina uniq de forma directa?', 'Los consecutivos', 'Todos aunque estén separados siempre', 'Solo archivos duplicados del disco', 'Solo palabras dentro de una línea', 'uniq compara líneas adyacentes.'),
        Q('¿Por qué usar sort antes de uniq?', 'Para juntar líneas iguales', 'Para cifrar el texto', 'Para cambiar permisos', 'Para instalar uniq', 'Agrupar duplicados permite que uniq los detecte consecutivamente.'),
        Q('¿Qué añade uniq -c?', 'El conteo de cada grupo', 'El color del escritorio', 'Un código QR', 'Un archivo comprimido', '-c muestra cuántas líneas hay en cada grupo.'),
        Q('¿Qué cuenta exactamente wc -l?', 'Caracteres de salto de línea', 'Solo palabras largas', 'Directorios ocultos', 'Procesos activos', 'Una última línea sin salto final no suma un salto a wc -l.')
      ]),
      L('Columnas y transformaciones simples', [
        'cut extrae campos o posiciones. Con -d eliges un delimitador y con -f los campos, numerados desde uno. Es útil para formatos simples separados por un carácter. Un CSV con comillas y separadores dentro de campos necesita una herramienta que entienda CSV.',
        'tr transforma o elimina caracteres que recibe por la entrada estándar. tr "a-z" "A-Z" convierte letras ASCII minúsculas en mayúsculas; para texto internacional hay que considerar el idioma y la herramienta. Ninguna de estas operaciones cambia el archivo original salvo que redirijas la salida sobre él.'
      ], 'printf "ana:estudiante\\nluis:docente\\n" | cut -d ":" -f 1', 'Extrae el primer campo de cada línea delimitada por dos puntos.', 'Cambia mentalmente -f 1 por -f 2 y predice la salida.', [
        Q('¿Qué especifica cut -d ":"?', 'El delimitador de campos', 'La carpeta de destino', 'La contraseña', 'El número de líneas', '-d elige el separador de campos.'),
        Q('¿Desde qué número se cuentan los campos de cut?', 'Uno', 'Cero siempre', 'Menos uno', 'Diez', 'Los campos de cut se numeran desde 1.'),
        Q('¿Qué devolvería el campo 2 de ana:estudiante usando :?', 'estudiante', 'ana', 'ana:estudiante completo', 'Una línea vacía siempre', 'El segundo campo está después del delimitador.'),
        Q('¿Qué tipo de operación realiza tr?', 'Transformar o eliminar caracteres', 'Mover carpetas', 'Cambiar propietario', 'Reiniciar procesos', 'tr opera sobre caracteres de la entrada estándar.'),
        Q('¿Por qué cut no basta para cualquier CSV?', 'No interpreta todas las reglas de campos entre comillas', 'No puede leer texto', 'Siempre necesita root', 'Solo acepta números', 'CSV admite separadores dentro de campos citados, lo que requiere un parser apropiado.')
      ]),
      L('Expresiones regulares esenciales', [
        'Una expresión regular describe un patrón de texto. En grep -E, ^ ancla al inicio, $ al final y . coincide con un carácter. [0-9] selecciona un dígito; + repite una o más veces el elemento anterior. En ese lenguaje, .* representa cualquier secuencia de caracteres de la línea.',
        'Los patrones de la shell y las expresiones regulares son distintos: *.txt es un patrón de nombres, no una expresión regular equivalente lista para grep. Pon el patrón entre comillas para que Bash no lo transforme. Para un punto literal en una expresión regular, escápalo como \\.'
      ], 'printf "error: uno\\ninfo: dos\\n" | grep -E "^error:"', 'Selecciona líneas que empiezan exactamente con error:.', 'Diseña verbalmente un patrón que encuentre líneas compuestas por uno o más dígitos, usando anclas.', [
        Q('¿Qué representa ^ al inicio de un patrón de grep -E?', 'El inicio de línea', 'El directorio personal', 'Un espacio obligatorio', 'Una negación universal', '^ ancla el patrón al comienzo.'),
        Q('¿Qué representa $ al final de la expresión regular?', 'El final de línea', 'El usuario root', 'Una variable siempre', 'La raíz del disco', '$ ancla el final del patrón a la línea.'),
        Q('En una expresión regular, ¿qué coincide con un carácter cualquiera?', '.', '* por sí solo', '~', '/', 'El punto representa un carácter; * es un cuantificador.'),
        Q('En grep -E, ¿qué describe [0-9]+?', 'Uno o más dígitos', 'Exactamente un guion', 'Solo el número 9', 'Cualquier carpeta', '+ repite una o más veces la clase de dígitos.'),
        Q('¿Qué patrón reconoce una línea completa de dígitos con grep -E?', '^[0-9]+$', '*.txt', '^texto', 'numero?', 'Las dos anclas limitan la coincidencia a toda la línea.')
      ]),
      L('Entrada, salida y redirecciones', [
        'Los procesos reciben una entrada estándar y producen una salida estándar y una salida de errores. Sus descriptores habituales son 0, 1 y 2. > redirige la salida estándar y reemplaza el archivo destino; >> añade al final. < toma la entrada de un archivo.',
        '2> redirige los errores. Separarlos permite guardar resultados por un lado y diagnósticos por otro. Evita leer y escribir el mismo archivo con > en una sola tubería: la shell puede vaciarlo antes de que el programa lo lea. Usa un archivo distinto y revisa el resultado.'
      ], 'printf "Primera línea\\n" > practica-salida.txt\nprintf "Otra línea\\n" >> practica-salida.txt\ncat < practica-salida.txt', 'Crea o reemplaza un archivo de práctica, añade otra línea y lo lee. Elige un nombre nuevo si ya existe.', 'Explica cómo cambiaría la segunda orden si usaras > en lugar de >>.', [
        Q('¿Qué hace > con un destino existente?', 'Lo trunca antes de escribir la salida', 'Siempre añade sin borrar', 'Lo cifra', 'No hace nada', '> abre el destino para reemplazar su contenido.'),
        Q('¿Qué operador añade al final de un archivo?', '>>', '>', '<', '|', '>> abre la salida en modo de anexado.'),
        Q('¿Qué descriptor corresponde habitualmente a errores estándar?', '2', '0', '1', '9 siempre', 'stdin es 0, stdout es 1 y stderr es 2.'),
        Q('¿Qué hace < archivo como redirección?', 'Usar archivo como entrada estándar', 'Borrar archivo', 'Ejecutar archivo con root', 'Comprimir archivo', '< conecta el archivo a stdin.'),
        Q('¿Qué riesgo hay en cat datos.txt > datos.txt?', 'Vaciar el archivo antes de leerlo', 'Duplicar siempre todos los datos', 'Cambiar la contraseña', 'Hacer el archivo oculto', 'La shell configura la redirección antes de ejecutar cat.')
      ]),
      L('Tuberías y códigos de salida', [
        'La tubería | conecta la salida estándar de un comando con la entrada del siguiente. No conecta por defecto los errores. El código de salida se consulta con $? inmediatamente después de la orden: cero suele indicar éxito y un valor distinto de cero otro resultado o un error.',
        'cmd1 && cmd2 ejecuta cmd2 si cmd1 termina con cero. cmd1 || cmd2 lo ejecuta si cmd1 termina con un valor distinto de cero. En Bash, el estado de una tubería es normalmente el del último comando; pipefail permite detectar fallos anteriores. El significado exacto de cada código depende del programa.'
      ], 'printf "rojo\\nazul\\n" | grep "azul"\nprintf "Estado: %s\\n" "$?"', 'Filtra azul y luego consulta el estado de grep, antes de que otro comando lo reemplace.', 'Predice cuándo se ejecutaría una segunda orden conectada con && y cuándo con ||.', [
        Q('¿Qué conecta | por defecto?', 'Salida estándar con entrada estándar', 'El teclado con la red siempre', 'Todos los errores con un archivo', 'Dos carpetas mediante un enlace', 'La tubería conecta stdout del primer proceso a stdin del siguiente.'),
        Q('¿Qué valor suele indicar éxito?', '0', 'Siempre 1', 'Siempre 127', 'Cualquier número negativo', 'La convención usual usa cero para éxito.'),
        Q('¿Cuándo se ejecuta la segunda orden en a && b?', 'Cuando a termina con estado cero', 'Siempre antes de a', 'Solo al apagar', 'Cuando a falla exclusivamente', '&& depende del éxito de la orden anterior.'),
        Q('¿Qué consulta $? en Bash?', 'El estado de la orden anterior', 'La cantidad de archivos ocultos', 'La contraseña de sudo', 'El nombre de la shell', '$? contiene el estado de salida reciente.'),
        Q('Sin pipefail, ¿qué estado suele devolver una tubería de Bash?', 'El del último comando', 'La suma de todos los estados', 'Siempre cero', 'El del primer comando únicamente', 'El comportamiento predeterminado toma el estado del último elemento.')
      ]),
      L('Procesos en primer y segundo plano', [
        'Un comando en primer plano ocupa la interacción de la terminal. & lo inicia en segundo plano. jobs lista trabajos de la shell actual y fg devuelve un trabajo al primer plano. No todos los procesos del sistema son trabajos conocidos por tu shell.',
        'Ctrl+C envía normalmente una señal de interrupción al grupo de procesos en primer plano. Ctrl+Z lo suspende; bg puede reanudarlo en segundo plano. Suspender no es terminar. Cerrar la terminal puede afectar a sus trabajos: & por sí solo no garantiza que sobrevivan.'
      ], 'sleep 30 &\njobs', 'Inicia una espera breve en segundo plano y consulta los trabajos de esta shell.', 'Explica la diferencia entre un trabajo suspendido y uno terminado. No practiques señales sobre documentos sin guardar.', [
        Q('¿Qué efecto tiene & al final de una orden?', 'Iniciarla en segundo plano', 'Ejecutarla con root', 'Comprimir la salida', 'Esperar a que cierre la sesión', '& permite que la shell continúe sin esperar al trabajo.'),
        Q('¿Qué muestra jobs?', 'Trabajos de la shell actual', 'Todos los empleos de internet', 'Paquetes disponibles', 'Todos los procesos del kernel necesariamente', 'El control de trabajos pertenece a la shell.'),
        Q('¿Qué suele hacer Ctrl+C en la terminal?', 'Interrumpir el grupo en primer plano', 'Copiar siempre como un editor gráfico', 'Suspender sin señal', 'Cerrar todas las sesiones', 'Habitualmente envía SIGINT al grupo en primer plano.'),
        Q('¿Qué suele hacer Ctrl+Z?', 'Suspender el trabajo en primer plano', 'Terminarlo siempre', 'Deshacer una instalación', 'Cambiar de usuario', 'Normalmente envía una señal de suspensión.'),
        Q('¿Qué comando devuelve un trabajo al primer plano?', 'fg', 'pwd', 'cut', 'export', 'fg reanuda o lleva un trabajo al primer plano.')
      ]),
      L('Tu primer script de Bash', [
        'Un script guarda instrucciones en un archivo de texto. La primera línea #!/usr/bin/env bash indica un intérprete al ejecutarlo directamente. También puedes invocarlo con bash archivo.sh: en ese caso Bash lee el archivo y no necesita el bit de ejecución, aunque sí poder leerlo.',
        'Para ejecutarlo como ./archivo.sh necesitas permiso de ejecución y una cabecera apropiada. chmod u+x añade ese permiso al propietario. ./ señala la carpeta actual; por seguridad y previsibilidad, esta no suele estar en PATH. Los comentarios comienzan con # fuera de comillas.'
      ], '#!/usr/bin/env bash\n# Mi primer script\nprintf "Hola desde mi script\\n"', 'Guarda estas líneas en saludo.sh dentro de tu carpeta de práctica y ejecútalo con bash saludo.sh.', 'Identifica cabecera, comentario y comando. Explica la diferencia entre bash saludo.sh y ./saludo.sh.', [
        Q('¿Para qué sirve la línea #! inicial?', 'Indicar el intérprete al ejecutar directamente', 'Cifrar el script', 'Convertirlo en paquete DEB', 'Ocultar la salida', 'El shebang especifica cómo interpretar el archivo.'),
        Q('¿Qué permiso añade chmod u+x saludo.sh?', 'Ejecución para el propietario', 'Escritura para todos', 'Lectura solo para otros', 'Administración permanente', 'u designa al propietario y +x añade ejecución.'),
        Q('¿Qué significa ./saludo.sh?', 'Ejecutar el archivo de la carpeta actual', 'Buscarlo en toda la red', 'Abrir el hogar de root', 'Ejecutar todos los scripts', './ es una ruta explícita relativa al directorio actual.'),
        Q('¿Necesita el archivo bit de ejecución al usar bash saludo.sh?', 'No, Bash lo lee como entrada de script', 'Sí, siempre para cualquier lectura', 'Solo si tiene comentarios', 'Solo si se usa printf', 'Invocar el intérprete explícitamente necesita lectura, no ejecución directa del archivo.'),
        Q('¿Cómo comienza un comentario habitual en Bash fuera de comillas?', '#', '// siempre', '<!--', 'REM obligatorio', '# introduce comentarios de shell en la posición correspondiente.')
      ]),
      L('Condiciones y argumentos', [
        'Un script puede recibir argumentos: $1 es el primero y $# cuenta los recibidos. "$@" conserva cada argumento como una palabra independiente. Validar argumentos ayuda a emitir un mensaje claro antes de operar sobre una ruta equivocada.',
        'if ejecuta una rama según el estado de una prueba. En [ -f "$1" ], -f comprueba si la ruta corresponde a un archivo regular. Los espacios alrededor de [ y ] son necesarios porque [ es un comando. fi cierra el bloque; else ofrece una alternativa.'
      ], 'if [ -f "$1" ]; then\n  printf "Es un archivo regular\\n"\nelse\n  printf "Indica un archivo válido\\n"\nfi', 'Dentro de un script, comprueba el primer argumento y muestra una respuesta sin modificarlo.', 'Describe qué ocurriría al pasar una carpeta en lugar de un archivo regular.', [
        Q('¿Qué representa $1 dentro de un script?', 'El primer argumento', 'El PID del sistema siempre', 'La primera línea del disco', 'El código de salida', 'Los parámetros posicionales guardan los argumentos.'),
        Q('¿Qué contiene $#?', 'El número de argumentos', 'El texto del último error', 'La contraseña', 'La cantidad de comentarios', '$# cuenta parámetros posicionales.'),
        Q('¿Qué comprueba [ -f "$1" ]?', 'Si la ruta es un archivo regular', 'Si es cualquier usuario', 'Si la red está conectada', 'Si es siempre un directorio', '-f es una prueba de archivo regular.'),
        Q('¿Qué cierra un bloque if de Bash?', 'fi', 'end-if obligatorio', '}', '</if>', 'La sintaxis if se termina con fi.'),
        Q('¿Por qué usar "$@" para transmitir argumentos?', 'Conserva cada argumento y sus espacios', 'Los convierte todos en una sola cadena', 'Elimina todos los argumentos', 'Ejecuta cada palabra como root', 'La expansión citada de "$@" mantiene los límites entre argumentos.')
      ]),
      L('Bucles y scripts comprensibles', [
        'for recorre una lista de elementos. do inicia el cuerpo y done lo cierra. Una variable representa cada elemento por turno. Al usar esa variable como nombre de archivo, conserva las comillas para admitir espacios. Empieza imprimiendo lo que harías antes de automatizar cambios.',
        'Un script mantenible tiene nombres claros, comentarios que explican decisiones y mensajes de error útiles. bash -n revisa sintaxis sin ejecutar las instrucciones. Esa comprobación no detecta todos los errores lógicos: también debes probar con datos de práctica y casos vacíos.'
      ], 'for tema in rutas permisos procesos; do\n  printf "Voy a repasar: %s\\n" "$tema"\ndone', 'Recorre tres elementos y muestra una línea por cada uno.', 'Añade un cuarto tema. Explica qué validaría bash -n y qué requeriría una prueba real.', [
        Q('¿Qué hace un bucle for?', 'Recorrer elementos y repetir un cuerpo', 'Comprimir una carpeta automáticamente', 'Cambiar el kernel', 'Salir siempre del script', 'for asigna cada elemento a una variable y ejecuta el cuerpo.'),
        Q('¿Qué palabra cierra el bucle del ejemplo?', 'done', 'fi', 'return siempre', 'endfor obligatorio', 'do y done delimitan el cuerpo del bucle.'),
        Q('¿Qué comprueba bash -n archivo.sh?', 'La sintaxis sin ejecutar las instrucciones', 'Todos los resultados lógicos', 'La velocidad de internet', 'El espacio de cada disco', '-n analiza la sintaxis sin ejecutar el script.'),
        Q('¿Qué práctica ayuda antes de automatizar cambios sobre archivos?', 'Mostrar primero las acciones previstas', 'Ejecutar siempre con sudo', 'Ocultar los errores', 'Probar sobre la única copia real', 'Una vista previa permite revisar destinos y comportamiento.'),
        Q('¿Qué caso conviene probar además del caso normal?', 'Una entrada vacía o sin coincidencias', 'Solo nombres sin espacios siempre', 'Únicamente el color del texto', 'Solo la fecha del escritorio', 'Los casos límite revelan supuestos frágiles del script.')
      ])
    ]
  });
})(globalThis);
