"""Catálogo editorial verificado en getartcraft.com/apps y /linux el 2026-11-10.

Las equivalencias describen tareas, no paridad de funciones ni afiliación.
Los enlaces llevan a la página oficial vigente para evitar fijar versiones.
"""
from copy import deepcopy

_APPS = (
    ('photocraft', 'PhotoCraft', 'Adobe Photoshop', 'Imagen y fotografía', 'Capas, retoque y composición.', 'Alpha temprana'),
    ('vectorcraft', 'VectorCraft', 'Adobe Illustrator', 'Diseño', 'Ilustración y edición vectorial.', 'En desarrollo'),
    ('filmcraft', 'FilmCraft', 'Adobe Premiere Pro', 'Video y animación', 'Edición y montaje de video.', 'En desarrollo'),
    ('lightcraft', 'LightCraft', 'Adobe Lightroom', 'Imagen y fotografía', 'Organización fotográfica y revelado RAW.', 'En desarrollo'),
    ('pdfcraft', 'PdfCraft', 'Adobe Acrobat', 'Documentos', 'Lectura, organización y combinación de PDF.', 'Alpha temprana'),
    ('effectcraft', 'EffectCraft', 'Adobe After Effects', 'Video y animación', 'Composición, efectos y gráficos en movimiento.', 'En desarrollo'),
    ('anicraft', 'AniCraft', 'Adobe Animate', 'Video y animación', 'Animación vectorial 2D.', 'Alpha temprana'),
    ('designcraft', 'DesignCraft', 'Adobe InDesign', 'Diseño', 'Maquetación y publicaciones.', 'En desarrollo'),
    ('figcraft', 'FigCraft', 'Figma', 'Diseño', 'Diseño y prototipos de interfaces.', 'Alpha temprana'),
    ('texturecraft', 'TextureCraft', 'Adobe Substance 3D Painter', 'Diseño', 'Pintura de texturas 3D.', 'En desarrollo'),
    ('materialcraft', 'MaterialCraft', 'Adobe Substance 3D Designer', 'Diseño', 'Materiales procedurales mediante nodos.', 'En desarrollo'),
    ('wordcraft', 'WordCraft', 'Microsoft Word', 'Documentos', 'Procesamiento de textos y documentos.', 'En desarrollo'),
    ('soundcraft', 'SoundCraft', 'Avid Pro Tools', 'Audio', 'Grabación, edición y mezcla de audio.', 'En desarrollo'),
    ('deckcraft', 'DeckCraft', 'Microsoft PowerPoint', 'Documentos', 'Presentaciones y diapositivas.', 'En desarrollo'),
    ('cadcraft', 'CADCraft', 'Autodesk AutoCAD', 'Diseño', 'Dibujo técnico y diseño CAD.', 'En desarrollo'),
    ('gridcraft', 'GridCraft', 'Microsoft Excel', 'Documentos', 'Hojas de cálculo y análisis de datos.', 'En desarrollo'),
    ('craft-anything', 'Craft Anything', 'Sin equivalente directo', 'Desarrollo', 'Exploración y creación de software.', 'Alpha temprana'),
)

METHODS = (
    {'id': 'flatpak', 'label': 'Flatpak', 'available': True,
     'detail': 'Paquete .flatpak oficial descargable. No se presupone que esté en Flathub.',
     'steps': 'Descarga el .flatpak para tu arquitectura desde la ficha oficial. Abre una terminal en Descargas y sustituye el nombre del archivo en el comando. Flatpak mostrará los componentes y pedirá confirmación.',
     'command': 'flatpak install --user "./ARCHIVO.flatpak"'},
    {'id': 'deb', 'label': 'DEB / Ubuntu', 'available': True,
     'detail': 'Para Debian, Ubuntu y derivadas con APT.',
     'steps': 'Descarga el .deb de tu arquitectura. Puedes elegirlo con el botón de archivo local de LinuxMate para revisar la instalación, o usar este comando desde Descargas.',
     'command': 'sudo apt install "./ARCHIVO.deb"'},
    {'id': 'rpm', 'label': 'RPM', 'available': True,
     'detail': 'Para distribuciones RPM; comprueba sus dependencias.',
     'steps': 'Descarga el .rpm correcto. Desde Descargas, usa DNF en Fedora o zypper en openSUSE. No uses ambos comandos.',
     'command': 'sudo dnf install "./ARCHIVO.rpm"\n# En openSUSE, en su lugar:\nsudo zypper install "./ARCHIVO.rpm"'},
    {'id': 'appimage', 'label': 'AppImage', 'available': True,
     'detail': 'Ejecutable portátil para x86_64 o ARM64.',
     'steps': 'Descarga el AppImage de tu arquitectura. LinuxMate puede guardarlo y crear un acceso mediante el selector de archivo local. Para abrirlo manualmente, concede permiso de ejecución en sus propiedades; se ejecuta con los permisos de tu usuario.',
     'command': 'chmod u+x "./ARCHIVO.AppImage"\n"./ARCHIVO.AppImage"'},
    {'id': 'snap', 'label': 'Snap', 'available': False,
     'detail': 'No verificado en las descargas oficiales consultadas. No se ofrece un comando Snap.'},
)


def artcraft_catalog():
    result = []
    for slug, name, windows, category, description, maturity in _APPS:
        result.append({
            'id': 'artcraft-' + slug, 'kind': 'app', 'windows': windows,
            'linux': name, 'route': 'alternative', 'family': 'artcraft',
            'category': category, 'description': description, 'maturity': maturity,
            'aliases': [name, slug, windows, windows.removeprefix('Adobe ').removeprefix('Microsoft ').removeprefix('Autodesk ').removeprefix('Avid ')],
            'note': description + ' Experimental: prueba tus archivos y funciones; no implica compatibilidad completa.',
            'searches': [], 'verified_on': '2026-11-10',
            'icon': f'https://getartcraft.com/images/apps/{slug}/icon.webp',
            'website': f'https://getartcraft.com/apps/{slug}',
            'repositories': 'https://getartcraft.com/linux',
            'methods': deepcopy(METHODS),
        })
    return result
