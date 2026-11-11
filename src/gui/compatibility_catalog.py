"""Curated compatibility guides. Data only: no commands or system access."""
from copy import deepcopy


TOOLS = [
    {
        "id": "bottles", "name": "Bottles", "kind": "Aplicaciones", "mark": "B",
        "summary": "Organiza programas de Windows en entornos Wine independientes, llamados botellas.",
        "best_for": "Probar una aplicación .exe o .msi con configuración propia.",
        "limits": "Separar botellas evita mezclar dependencias; no garantiza que el programa funcione ni sustituye una copia de tus archivos.",
        "requirements": ["Flatpak y Flathub configurados.", "Instalador legítimo y versión exacta de la aplicación."],
        "steps": ["Instala la edición Flatpak recomendada por Bottles.", "Crea una botella de tipo Aplicación y ponle el nombre del programa.", "Ejecuta el instalador dentro de esa botella. Añade dependencias solo si la aplicación las necesita.", "Prueba abrir, editar y exportar una copia de un proyecto real. Guarda la configuración que funcionó."],
        "methods": [{"label": "Flatpak · Flathub", "source": "flatpak", "package": "com.usebottles.bottles"}],
        "sources": [{"label": "Instalación oficial", "url": "https://docs.usebottles.com/getting-started/installation"}, {"label": "Guías de Bottles", "url": "https://docs.usebottles.com/"}],
        "troubleshooting": ["Si no ve una carpeta, revisa los permisos de archivos de Flatpak y concede acceso solo a la ubicación necesaria.", "Si una actualización falla, prueba otra botella antes de modificar la que ya funciona."],
    },
    {
        "id": "wine", "name": "Wine", "kind": "Capa de compatibilidad", "mark": "W",
        "summary": "Implementa interfaces de Windows para ejecutar aplicaciones en Linux sin instalar un Windows completo.",
        "best_for": "Configuración manual y aplicaciones con instrucciones de compatibilidad conocidas.",
        "limits": "La compatibilidad depende de la versión del programa, Wine y sus componentes; los controladores de Windows no se convierten en controladores Linux.",
        "requirements": ["Paquetes adecuados para tu distribución y arquitectura.", "Componentes de 32 bits si el programa los requiere."],
        "steps": ["Consulta AppDB para la versión concreta del programa.", "Instala Wine siguiendo el procedimiento de tu distribución o WineHQ.", "Prepara un prefijo separado para cada aplicación; Bottles facilita este paso.", "Prueba el instalador y tus archivos. Anota la versión de Wine y las dependencias que funcionaron."],
        "methods": [{"label": "Paquete de tu distribución", "query": "wine"}],
        "sources": [{"label": "WineHQ", "url": "https://www.winehq.org/"}, {"label": "Wine AppDB", "url": "https://appdb.winehq.org/"}],
        "troubleshooting": ["Un error de DLL requiere identificar la dependencia concreta; evita descargar DLL sueltas de sitios desconocidos.", "No ejecutes Wine con sudo: el programa debe usar tu entorno de usuario."],
    },
    {
        "id": "lutris", "name": "Lutris", "kind": "Juegos", "mark": "L",
        "summary": "Reúne juegos y administra los motores o runners necesarios para iniciarlos.",
        "best_for": "Juegos fuera de Steam, instaladores y varias bibliotecas.",
        "limits": "Los scripts y runners no aseguran compatibilidad. Comprueba el juego, su launcher y su anti-cheat.",
        "requirements": ["Controlador gráfico y soporte Vulkan apropiados.", "Bibliotecas gráficas de 32 bits cuando el juego las necesite."],
        "steps": ["Instala Lutris y revisa los requisitos de tu distribución.", "Busca el juego y lee las notas del instalador antes de usarlo.", "Selecciona el runner y una carpeta propia para ese juego.", "Prueba vídeo, audio, mando y guardado. Conserva los registros si falla."],
        "methods": [{"label": "Paquete de tu distribución", "query": "lutris"}, {"label": "Flatpak · Flathub", "source": "flatpak", "package": "net.lutris.Lutris"}],
        "sources": [{"label": "Preparación e instalación", "url": "https://lutris.net/about"}, {"label": "Descargas", "url": "https://lutris.net/downloads/"}],
        "troubleshooting": ["Revisa el registro del juego y cambia una opción cada vez.", "Si falta Vulkan, revisa los controladores y las bibliotecas de tu arquitectura desde el centro Gaming."],
    },
    {
        "id": "proton", "name": "Steam · Proton", "kind": "Juegos", "mark": "P",
        "summary": "La integración de Steam con Wine y otros componentes para juegos de Windows.",
        "best_for": "Juegos de tu biblioteca de Steam.",
        "limits": "Anti-cheat, DRM y actualizaciones pueden impedir jugar. Los informes de ProtonDB son comunitarios y dependen del equipo.",
        "requirements": ["Steam instalado y una cuenta con el juego.", "Controlador gráfico compatible con los requisitos del juego."],
        "steps": ["Consulta informes recientes del título y su anti-cheat.", "Instala Steam. Revisa Compatibilidad en sus ajustes y en las propiedades del juego.", "Prueba la versión de Proton ofrecida por Steam; cambia solo si hay una razón documentada.", "Comprueba rendimiento, partidas guardadas y funciones en línea."],
        "methods": [{"label": "Buscar Steam", "query": "steam"}, {"label": "Steam en Flatpak", "source": "flatpak", "package": "com.valvesoftware.Steam"}],
        "sources": [{"label": "Proton · Valve", "url": "https://github.com/ValveSoftware/Proton"}, {"label": "ProtonDB · comunidad", "url": "https://www.protondb.com/"}],
        "troubleshooting": ["Tener Steam instalado no significa que Proton esté descargado o que un juego sea compatible.", "Si falla un juego, verifica sus archivos y consulta problemas conocidos de esa versión."],
    },
    {
        "id": "heroic", "name": "Heroic", "kind": "Juegos", "mark": "H",
        "summary": "Lanzador para tus bibliotecas de Epic, GOG y Amazon Games.",
        "best_for": "Gestionar esas tiendas desde una interfaz Linux.",
        "limits": "Disponer del juego en la tienda no confirma su compatibilidad con Linux.",
        "requirements": ["Cuenta de la tienda correspondiente.", "Runner Wine/Proton y controladores adecuados al juego."],
        "steps": ["Instala Heroic y conecta la tienda desde el propio lanzador.", "Selecciona el juego y revisa su compatibilidad.", "Configura el runner desde Heroic y descarga el juego.", "Prueba guardados, audio y mando antes de trasladar tu biblioteca."],
        "methods": [{"label": "Flatpak · Flathub", "source": "flatpak", "package": "com.heroicgameslauncher.hgl"}],
        "sources": [{"label": "Descargas y documentación", "url": "https://heroicgameslauncher.com/"}],
        "troubleshooting": ["Comprueba el runner seleccionado y consulta el registro del juego.", "Si falla una sesión, vuelve a conectar la tienda desde Heroic; nunca pegues sus credenciales en el chat."],
    },
    {
        "id": "winboat", "name": "WinBoat", "kind": "Windows virtualizado", "mark": "WB",
        "summary": "Ejecuta Windows en una máquina virtual gestionada con Docker o Podman e integra sus ventanas mediante FreeRDP.",
        "best_for": "Evaluar aplicaciones que necesitan un Windows completo.",
        "limits": "Proyecto beta. Comprueba licencia de Windows, periféricos y requisitos gráficos de tu aplicación. No se asume compatibilidad universal.",
        "requirements": ["Al menos 4 GB de RAM, 2 hilos de CPU y 32 GB libres en el destino.", "Virtualización habilitada y acceso a KVM.", "Docker Engine con Compose v2, o Podman con Compose; Docker Desktop no está soportado.", "FreeRDP 3 con audio; comprueba versiones y permisos en la guía oficial."],
        "steps": ["Revisa los requisitos y la comprobación local de este apartado.", "Descarga DEB, RPM o AppImage desde las versiones oficiales.", "Sigue el asistente de WinBoat para preparar Windows y sus recursos.", "Revisa las carpetas compartidas y prueba tu aplicación antes de migrar datos."],
        "methods": [{"label": "Descargas oficiales · DEB / RPM / AppImage", "url": "https://github.com/winboat-org/winboat/releases"}, {"label": "Elegir DEB o AppImage descargado", "local": True}],
        "sources": [{"label": "Requisitos y documentación", "url": "https://github.com/winboat-org/winboat"}],
        "troubleshooting": ["Si KVM no está disponible, revisa virtualización y permisos siguiendo la documentación.", "Si no aparecen ventanas o audio, comprueba FreeRDP y la conexión con Windows."],
    },
    {
        "id": "wineboot", "name": "wineboot", "kind": "Mantenimiento de Wine", "mark": "↻",
        "summary": "Utilidad de Wine para inicializar o simular el arranque y apagado de un entorno Windows.",
        "best_for": "Mantenimiento de un prefijo Wine concreto siguiendo un diagnóstico.",
        "limits": "No es WinBoat, no instala Windows y no es un lanzador de aplicaciones. Sus operaciones pueden modificar el prefijo.",
        "requirements": ["Wine y un prefijo identificado.", "Copia de la configuración y aplicaciones cerradas antes de intervenir."],
        "steps": ["Identifica el prefijo y el gestor que lo administra.", "Si usas Bottles o Lutris, utiliza primero las opciones de ese gestor.", "Consulta la ayuda de wineboot y el diagnóstico antes de inicializar, actualizar o reiniciar un prefijo."],
        "methods": [],
        "sources": [{"label": "Manual de wineboot · código Wine", "url": "https://gitlab.winehq.org/wine/wine/-/blob/master/programs/wineboot/wineboot.man.in"}],
        "troubleshooting": ["Reiniciar un prefijo no soluciona automáticamente dependencias faltantes ni aplicaciones incompatibles."],
    },
]


def compatibility_catalog():
    return {"schema_version": 1, "tools": deepcopy(TOOLS)}
