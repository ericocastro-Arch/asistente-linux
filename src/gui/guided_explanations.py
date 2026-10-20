"""Explicaciones locales de comandos y errores sin ejecutar acciones."""

from __future__ import annotations

import re
import shlex

from src.core.security import RiskLevel, assess_command


COMMANDS = {
    "apt": "Gestiona paquetes de los repositorios Debian/Ubuntu.",
    "apt-get": "Gestiona paquetes de los repositorios Debian/Ubuntu.",
    "dnf": "Gestiona paquetes de Fedora y otras distribuciones compatibles con RPM.",
    "pacman": "Gestiona paquetes de Arch Linux y distribuciones derivadas.",
    "zypper": "Gestiona paquetes de openSUSE.",
    "dpkg": "Consulta o administra paquetes .deb instalados localmente.",
    "rpm": "Consulta paquetes RPM instalados o archivos RPM.",
    "snap": "Gestiona aplicaciones empaquetadas como Snap.",
    "flatpak": "Gestiona aplicaciones empaquetadas como Flatpak.",
    "systemctl": "Consulta o controla servicios del sistema.",
    "ls": "Muestra los archivos de una carpeta.",
    "cd": "Cambia de carpeta en esa terminal.",
    "pwd": "Muestra la carpeta actual.",
    "df": "Muestra el espacio usado y libre de los sistemas de archivos.",
    "du": "Calcula cuánto espacio ocupan archivos o carpetas.",
    "free": "Muestra el uso de memoria RAM.",
    "ps": "Muestra procesos en ejecución.",
    "grep": "Busca líneas que coincidan con un texto o patrón.",
    "find": "Busca archivos y carpetas.",
    "journalctl": "Consulta los registros del sistema.",
    "ip": "Consulta o modifica la configuración de red según sus argumentos.",
    "git": "Gestiona el historial y los cambios de un proyecto.",
    "mkdir": "Crea una carpeta.",
    "touch": "Crea un archivo vacío o actualiza su fecha de modificación.",
    "tar": "Agrupa o extrae archivos comprimidos.",
    "python": "Ejecuta el intérprete de Python; el resultado depende del archivo o argumentos.",
    "python3": "Ejecuta Python 3; el resultado depende del archivo o argumentos.",
    "pip": "Instala o administra paquetes de Python en un entorno.",
    "curl": "Realiza solicitudes a una dirección de red; el efecto depende de sus opciones.",
    "wget": "Descarga archivos desde una dirección de red.",
    "whoami": "Muestra el nombre del usuario actual.",
    "uname": "Muestra información del kernel y del sistema.",
    "cp": "Copia archivos o carpetas.",
    "mv": "Mueve o cambia el nombre de archivos o carpetas.",
    "rm": "Elimina archivos o carpetas; normalmente no van a la papelera.",
    "chmod": "Cambia permisos de archivos o carpetas.",
    "chown": "Cambia el propietario de archivos o carpetas.",
}

SUBCOMMANDS = {
    ("apt", "update"): "Actualiza la lista de paquetes disponibles; no instala las actualizaciones.",
    ("apt", "upgrade"): "Instala actualizaciones de los paquetes ya instalados.",
    ("apt", "install"): "Instala los paquetes indicados.",
    ("apt", "remove"): "Desinstala los paquetes indicados, conservando normalmente su configuración.",
    ("apt", "purge"): "Desinstala paquetes y también elimina su configuración gestionada por APT.",
    ("apt", "autoremove"): "Quita dependencias que APT considera innecesarias.",
    ("apt", "clean"): "Borra paquetes descargados de la caché de APT.",
    ("apt", "search"): "Busca paquetes en los índices locales de APT.",
    ("apt", "show"): "Muestra información de un paquete.",
    ("apt", "list"): "Lista paquetes; algunas opciones muestran actualizaciones disponibles.",
    ("snap", "install"): "Instala una aplicación Snap.",
    ("snap", "remove"): "Desinstala una aplicación Snap.",
    ("snap", "refresh"): "Actualiza Snap(s) instalados; con `--list` solo muestra actualizaciones disponibles.",
    ("flatpak", "install"): "Instala una aplicación Flatpak desde un repositorio configurado.",
    ("flatpak", "uninstall"): "Desinstala una aplicación Flatpak.",
    ("flatpak", "search"): "Busca aplicaciones en los repositorios Flatpak configurados.",
    ("flatpak", "list"): "Muestra aplicaciones y componentes Flatpak instalados.",
    ("systemctl", "status"): "Muestra el estado de un servicio sin cambiarlo.",
    ("systemctl", "restart"): "Detiene y vuelve a iniciar un servicio; puede interrumpirlo brevemente.",
    ("systemctl", "stop"): "Detiene un servicio en ejecución.",
    ("dnf", "search"): "Busca paquetes en los repositorios de DNF.",
    ("dnf", "install"): "Instala los paquetes indicados mediante DNF.",
    ("dnf", "upgrade"): "Actualiza paquetes ya instalados mediante DNF.",
    ("dnf", "check-update"): "Consulta si hay actualizaciones disponibles para paquetes instalados.",
    ("pacman", "-ss"): "Busca paquetes en los repositorios de Arch.",
    ("pacman", "-s"): "Instala paquetes desde los repositorios de Arch.",
    ("pacman", "-syu"): "Sincroniza las listas de paquetes y actualiza el sistema Arch completo.",
    ("pacman", "-qu"): "Muestra actualizaciones disponibles según la lista local de paquetes.",
    ("pacman", "-q"): "Consulta paquetes ya instalados; la información depende de las opciones usadas.",
    ("zypper", "search"): "Busca paquetes en los repositorios de openSUSE.",
    ("zypper", "install"): "Instala paquetes mediante Zypper.",
    ("zypper", "list-updates"): "Lista actualizaciones disponibles según los índices de repositorios locales.",
    ("git", "status"): "Resume los cambios de la carpeta de trabajo de Git.",
    ("git", "clone"): "Copia un repositorio remoto a una carpeta local.",
    ("git", "pull"): "Descarga cambios remotos y trata de integrarlos en la rama actual.",
}

OPTION_EXPLANATIONS = {
    "ls": {"-l": "muestra detalles como permisos y tamaño", "-a": "incluye archivos ocultos", "-h": "muestra tamaños en formato legible"},
    "df": {"-h": "muestra tamaños en formato legible"},
    "du": {"-h": "muestra tamaños en formato legible", "-s": "resume el total en vez de listar cada elemento"},
    "free": {"-h": "muestra cantidades en formato legible"},
    "grep": {"-i": "ignora mayúsculas y minúsculas", "-n": "muestra el número de línea", "-r": "busca también dentro de subcarpetas"},
    "find": {"-type": "limita la búsqueda a un tipo de elemento", "-name": "filtra por nombre"},
    "cp": {"-r": "copia también el contenido de carpetas"},
    "rm": {"-r": "elimina carpetas y su contenido", "-f": "fuerza la eliminación sin preguntar"},
    "apt": {"-y": "acepta automáticamente las preguntas de APT"},
    "apt-get": {"-y": "acepta automáticamente las preguntas de APT"},
    "dnf": {"-y": "acepta automáticamente las preguntas de DNF"},
    "pacman": {"-s": "selecciona la operación de sincronizar/instalar paquetes"},
    "zypper": {"-y": "acepta automáticamente las preguntas de Zypper"},
    "systemctl": {"--failed": "muestra solo las unidades que están en estado fallido", "--user": "consulta los servicios de la sesión actual"},
}

ERROR_PATTERNS = (
    (
        r"sudo:\s*command not found|sudo: no se encontr[oó] la orden|sudo: orden no encontrada",
        "El sistema no encuentra `sudo`; algunas distribuciones mínimas no lo incluyen o el usuario ya está en una sesión administrativa.",
        "Comprueba quién inició la sesión y sigue la guía de tu distribución para permisos de administrador. No instales `sudo` ni cambies permisos a ciegas.",
    ),
    (
        r"sudo:.*(?:a password is required|se requiere una contrase[nñ]a)|a terminal is required to read the password",
        "`sudo` no pudo solicitar la autenticación en esta sesión.",
        "Ejecuta la acción desde una terminal interactiva y revisa el comando completo antes de escribir tu contraseña.",
    ),
    (
        r"command not found|no se encontr[oó] la orden|orden no encontrada",
        "El sistema no encuentra ese programa o el nombre está mal escrito.",
        "Comprueba el nombre y si la aplicación está instalada. No pegues comandos de instalación que no reconozcas.",
    ),
    (
        r"permission denied|permiso denegado|acceso denegado",
        "Tu usuario no tiene permiso para esa operación o archivo.",
        "Revisa qué archivo o carpeta aparece en el error. No añadas sudo a ciegas.",
    ),
    (
        r"operation not permitted|operaci[oó]n no permitida",
        "El sistema bloqueó la operación por permisos, políticas de seguridad o porque el archivo está protegido.",
        "Comprueba el archivo y la acción solicitada. No uses `sudo` hasta confirmar por qué se requiere acceso administrativo.",
    ),
    (
        r"unable to locate package|no se ha podido localizar el paquete|no se pudo localizar el paquete",
        "APT no encuentra ese nombre en los repositorios configurados.",
        "Comprueba la escritura del paquete y búscalo en Instalar aplicaciones.",
    ),
    (
        r"could not get lock|unable to acquire.*lock|no se pudo obtener el bloqueo",
        "Otro gestor de paquetes podría estar trabajando en este momento.",
        "Espera a que termine y vuelve a intentarlo. No borres el archivo de bloqueo manualmente.",
    ),
    (
        r"no space left on device|no queda espacio en el dispositivo|espacio insuficiente",
        "El disco o la partición donde se escribe podría estar lleno.",
        "Abre Diagnóstico y revisa el almacenamiento antes de instalar o copiar más archivos.",
    ),
    (
        r"temporary failure (?:in name resolution|resolving)|fallo temporal en la resoluci[oó]n",
        "El equipo no pudo resolver un nombre de Internet.",
        "Comprueba la conexión y DNS en Diagnóstico. Reiniciar servicios sin comprobarlos puede cortar la red.",
    ),
    (
        r"could not resolve host|no se pudo resolver el host|name or service not known|no route to host|network is unreachable|connection timed out|conexi[oó]n agot[oó] el tiempo",
        "La conexión no llegó al servidor o no pudo resolver su nombre.",
        "Comprueba Wi-Fi/cable, red y DNS desde Diagnóstico. No cambies los DNS del sistema sin anotar la configuración actual.",
    ),
    (
        r"failed to fetch|some index files failed to download|no se pudieron descargar algunos archivos de [ií]ndice",
        "El gestor de paquetes no pudo descargar información de uno o más repositorios.",
        "Revisa la conexión y el estado de los repositorios. Si es un error temporal, espera y vuelve a intentarlo; no desactives la verificación de firmas.",
    ),
    (
        r"does not have a release file|no tiene un archivo de publicaci[oó]n|no tiene un fichero de publicaci[oó]n",
        "Una fuente configurada no ofrece una versión compatible con tu distribución o su dirección cambió.",
        "Comprueba que el repositorio corresponda a tu versión de Linux y consulta las instrucciones oficiales del proveedor antes de editar las fuentes.",
    ),
    (
        r"no_pubkey|gpg error|signature.*(?:invalid|failed)|firma.*(?:inv[aá]lida|no se pudo verificar)|not signed",
        "El gestor no pudo verificar la firma del repositorio o del paquete.",
        "No omitas la verificación ni aceptes claves desconocidas. Confirma el origen y sigue las instrucciones oficiales del repositorio.",
    ),
    (
        r"no such file or directory|no existe el archivo o el directorio|no existe el fichero o el directorio",
        "La ruta indicada no existe, está mal escrita o alguno de sus directorios falta.",
        "Copia la ruta exacta, comprueba mayúsculas y espacios con `ls`, y confirma desde qué carpeta ejecutaste la orden.",
    ),
    (
        r"read-only file system|sistema de archivos de solo lectura|sistema de ficheros de solo lectura",
        "La partición está montada como solo lectura o el sistema la protegió tras detectar un problema.",
        "Guarda tu trabajo y revisa el estado del disco. No fuerces el montaje de escritura sin entender la causa.",
    ),
    (
        r"unmet dependencies|dependencias incumplidas|dependencias no satisfechas|held broken packages|paquetes retenidos rotos",
        "Hay dependencias de paquetes que APT no puede resolver en este momento.",
        "Ejecuta Diagnóstico; si confirma un problema de paquetes, utiliza su reparación guiada.",
    ),
    (
        r"sub-process .*dpkg.*returned an error code|subproceso .*dpkg.*(?:devolvi[oó]|retorn[oó]) .*c[oó]digo de error",
        "Una operación anterior de DPKG terminó con error y pudo dejar paquetes a medio configurar.",
        "Lee las líneas anteriores para identificar el paquete que falló. Usa Diagnóstico antes de reparar; no borres archivos de bloqueo.",
    ),
    (
        r"segmentation fault|violaci[oó]n de segmento",
        "La aplicación se cerró por un fallo de memoria o de sus bibliotecas.",
        "Anota el nombre de la aplicación y revisa sus registros o actualizaciones antes de reinstalarla.",
    ),
    (
        r"address already in use|eaddrinuse|direcci[oó]n ya est[aá] en uso|puerto.*(?:ocupado|en uso)",
        "Otra aplicación ya está usando el puerto que intenta abrir el programa.",
        "Revisa qué proceso usa el puerto antes de cerrarlo o cambia el puerto de la aplicación.",
    ),
    (
        r"modulenotfounderror|no module named",
        "Python no encuentra un módulo requerido en el entorno que está ejecutando el programa.",
        "Confirma qué intérprete ejecutas y si el proyecto usa un entorno virtual. Instala dependencias dentro de ese entorno, no en el Python del sistema.",
    ),
    (
        r"externally-managed-environment|externally managed environment|entorno administrado externamente",
        "La distribución protege el Python del sistema para evitar conflictos con paquetes instalados por el gestor de Linux.",
        "Crea un entorno virtual para el proyecto o busca el paquete en el gestor de aplicaciones. No fuerces la instalación sobre el Python del sistema.",
    ),
    (
        r"broken pipe|tuber[ií]a rota",
        "Una orden terminó de leer antes de que la anterior acabara de escribir; suele pasar al usar tuberías con `head`.",
        "Si el resultado esperado está completo, normalmente puedes ignorarlo. Si no, revisa la orden que está antes de `|`.",
    ),
)


def explain_command(raw: str) -> str:
    command = (raw or "").strip()
    if not command:
        return "Pega un comando para explicarlo. No se ejecutará."
    if len(command) > 2000:
        return "El comando es demasiado largo para analizarlo de forma segura. Reduce el texto a la instrucción concreta."
    if "\n" in command:
        return "Hay varias líneas. Pega una sola orden cada vez para no pasar por alto una acción. No se ejecutó nada."
    if command.startswith("$ "):
        command = command[2:].strip()
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return "El comando parece tener comillas sin cerrar. Revísalo antes de usarlo. No se ejecutó nada."

    parts = [token for token in tokens if token not in {"|", "||", "&&", ";", ">", ">>", "<"}]
    if not parts:
        return "No encontré una orden reconocible. No se ejecutó nada."
    privileged = parts[0] in {"sudo", "pkexec"}
    if privileged:
        parts = parts[1:]
    if not parts:
        return "Esta instrucción solo solicita permisos elevados, pero no indica qué ejecutar. No se ejecutó nada."

    program = parts[0]
    normalized = "apt" if program == "apt-get" else program
    arguments = parts[1:]
    if program == "pacman":
        pacman_mode = next((part.lower() for part in arguments if part.lower().startswith(("-s", "-q"))), "")
        if pacman_mode.startswith("-sy"):
            subcommand = "-syu"
        elif pacman_mode.startswith("-ss"):
            subcommand = "-ss"
        elif pacman_mode.startswith("-s"):
            subcommand = "-s"
        elif pacman_mode.startswith("-qu"):
            subcommand = "-qu"
        elif pacman_mode.startswith("-q"):
            subcommand = "-q"
        else:
            subcommand = ""
    else:
        subcommand = next((part for part in arguments if not part.startswith("-") and part not in {"=", "("}), "")
    description = SUBCOMMANDS.get((normalized, subcommand)) or COMMANDS.get(program)
    lines = [f"**Comando principal:** `{program}`. {description or 'No tengo una explicación específica para esta orden.'}"]
    if privileged:
        lines.append("**Permisos:** `sudo` o `pkexec` solicita privilegios de administrador; revisa el resto antes de aceptarlos.")
    if "-y" in tokens or "--yes" in tokens:
        lines.append("**Confirmaciones:** `-y` acepta automáticamente algunas preguntas del gestor.")
    option_notes = []
    option_map = OPTION_EXPLANATIONS.get(program, {})
    for token in arguments:
        option = option_map.get(token.lower())
        if option and option not in option_notes:
            option_notes.append(option)
    if option_notes:
        lines.append("**Opciones:** " + "; ".join(option_notes) + ".")
    if program == "rm" and any(flag.startswith("-") and "r" in flag for flag in arguments):
        lines.append("**Alcance:** la opción recursiva también elimina el contenido de carpetas.")
    if program in {"pip", "python", "python3"} and any(part in {"install", "-m"} for part in arguments):
        lines.append("**Entorno:** instalar paquetes de Python puede modificar el entorno activo; para proyectos suele ser mejor un entorno virtual.")
    operators = {
        "|": "`|` pasa la salida de una orden a la siguiente.",
        "&&": "`&&` ejecuta la siguiente orden solo si la anterior funcionó.",
        "||": "`||` ejecuta la siguiente orden si la anterior falló.",
        ";": "`;` ejecuta otra orden aunque la anterior falle.",
        ">": "`>` sobrescribe un archivo con la salida.",
        ">>": "`>>` agrega la salida al final de un archivo.",
    }
    for token in operators:
        if token in tokens:
            lines.append("**Conexión entre órdenes:** " + operators[token])
    if any(token in tokens for token in ("|", "&&", "||", ";")):
        lines.append("Esta explicación describe la primera orden; revisa cada orden adicional por separado.")

    decision = assess_command(command, allow_confirmation=True)
    safe_query = not any(token in tokens for token in ("|", "&&", "||", ";", ">", ">>", "<")) and (
        (program in {"apt", "apt-get"} and subcommand in {"search", "show", "list", "policy"})
        or (program == "dnf" and (subcommand in {"search", "info", "list", "repoquery"} or (subcommand == "check-update" and "--cacheonly" in arguments)))
        or (program == "pacman" and subcommand in {"-ss", "-qu", "-q"})
        or (program == "zypper" and subcommand in {"search", "info", "list-updates", "repos"})
        or (program == "flatpak" and subcommand in {"list", "info", "search", "remote-ls", "remotes", "history"})
        or (program == "snap" and subcommand in {"list", "info", "find", "services", "changes"})
        or (program == "snap" and subcommand == "refresh" and "--list" in arguments)
        or (program == "systemctl" and (subcommand in {"status", "is-active", "is-enabled", "is-failed", "show", "cat"} or "--failed" in arguments))
        or (program == "git" and subcommand in {"status", "log", "diff", "show"})
    )
    if decision.risk == RiskLevel.CRITICAL:
        lines.append("**Riesgo:** esta instrucción puede dañar o borrar datos. No la ejecutes sin revisar cada parte.")
    elif not description:
        lines.append("**Precaución:** no he verificado qué hace esta orden; consulta su documentación antes de usarla.")
    elif not safe_query and decision.risk in {RiskLevel.MEDIUM, RiskLevel.HIGH}:
        lines.append("**Riesgo:** puede modificar el sistema o archivos; requiere revisión y confirmación antes de ejecutarla.")
    lines.append("No se ejecutó ningún comando.")
    return "\n".join(lines)


def explain_error(raw: str) -> str:
    error = (raw or "").strip()
    if not error:
        return "Pega el mensaje de error para explicarlo. No se modificará el sistema."
    if len(error) > 4000:
        return "El mensaje es demasiado largo. Pega solo las líneas del error, sin contraseñas ni datos personales."
    for pattern, cause, next_step in ERROR_PATTERNS:
        if re.search(pattern, error, flags=re.IGNORECASE):
            return f"**Posible causa:** {cause}\n**Qué revisar:** {next_step}\nNo se ejecutó ninguna reparación."
    return (
        "No reconozco este error con suficiente certeza para proponer una reparación automática.\n"
        "Indica qué aplicación estabas usando y qué hiciste justo antes; conserva el texto exacto del error. "
        "No compartas contraseñas, claves ni datos personales.\n"
        "No se modificó el sistema."
    )
