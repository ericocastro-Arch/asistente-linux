(function (root) {
  'use strict';
  const { Q, L } = root.AcademyContent;

  function makeLesson(courseName, item) {
    const paragraphs = [
      `${item.explain} En ${courseName} conviene observar primero el estado actual, aplicar un cambio pequeño y comprobar el resultado. Esta forma de trabajo deja evidencia clara, evita mezclar causas y permite volver atrás cuando algo no sale como esperabas.`,
      `${item.context} El ejemplo está pensado para una carpeta o entorno de práctica. Lee cada opción, confirma la ruta y conserva una copia cuando trabajes con información importante. La meta es comprender el flujo completo y saber explicar el resultado, en lugar de memorizar una orden aislada.`
    ];
    const first = item.command.split('\n')[0];
    const questions = [
      Q(`En «${item.title}», ¿cuál es la idea central?`, item.concept, `Publicar ${item.title} automáticamente`, `Convertir ${item.title} en una contraseña`, `Borrar el proyecto para empezar`, `${item.concept} es el principio que organiza esta lección.`),
      Q(`¿Qué comando inicia el ejemplo de «${item.title}»?`, first, `sudo ${item.title}`, `apt install ${item.title}`, `rm ${item.title}`, `El ejemplo comienza con «${first}» porque consulta o realiza la operación estudiada.`),
      Q(`¿Qué resultado indica que la práctica de «${item.title}» avanzó?`, item.result, 'Todos los archivos desaparecen', 'El sistema reinicia sin explicación', 'No hay salida ni cambio comprobable', `${item.result} es la señal concreta que permite verificar el ejercicio.`),
      Q(`¿Qué precaución corresponde a «${item.title}»?`, item.caution, 'Ejecutar todo con privilegios sin leer', 'Trabajar sobre la única copia disponible', 'Omitir cualquier comprobación', `${item.caution} reduce el riesgo y facilita corregir un error.`),
      Q(`Si «${item.title}» falla, ¿qué paso ayuda más?`, item.recovery, 'Cambiar muchas opciones a la vez', 'Ocultar el mensaje de error', 'Repetir sin leer la salida', `${item.recovery} permite localizar la causa con información reproducible.`)
    ];
    return L(item.title, paragraphs, item.command, item.detail, item.practice, questions);
  }

  const gitRaw = [
    ['Git, repositorio y área de trabajo','Git registra versiones y distingue el directorio de trabajo, el área de preparación y el historial.','Un repositorio conserva instantáneas verificables.','git status','El estado muestra archivos nuevos o modificados.'],
    ['Configura tu identidad','Los commits guardan nombre y correo de autor; la configuración puede ser global o local.','La identidad describe la autoría del cambio.','git config --local user.name "Tu nombre"','La configuración queda limitada al repositorio.'],
    ['Crea tu primer repositorio','git init prepara los metadatos sin confirmar automáticamente los archivos existentes.','Inicializar crea la estructura de control de versiones.','git init','git status reconoce el repositorio nuevo.'],
    ['Prepara cambios con add','git add copia el contenido elegido al índice que formará el próximo commit.','El índice permite elegir exactamente qué se guarda.','git add README.md','README.md aparece como cambio preparado.'],
    ['Guarda una versión con commit','Un commit registra una instantánea preparada con autor, fecha, mensaje e historia.','Un commit debe representar un cambio coherente.','git commit -m "Documenta instalación"','El historial incorpora un commit explicable.'],
    ['Lee diferencias e historial','git diff compara contenido y git log recorre commits guardados.','Las diferencias muestran qué cambió y el historial cuándo.','git log --oneline --decorate -5','Se muestran cinco commits resumidos.'],
    ['Ignora archivos generados','.gitignore describe patrones que Git no debe empezar a seguir, como cachés o secretos locales.','Ignorar evita agregar archivos derivados por accidente.','printf ".env\\n__pycache__/\\n" >> .gitignore','git status deja fuera archivos no seguidos coincidentes.'],
    ['Trabaja con ramas','Una rama es un nombre móvil para una línea de commits y separa una idea en desarrollo.','Las ramas aíslan líneas de trabajo.','git switch -c mejora-documentacion','La rama nueva queda creada y activa.'],
    ['Fusiona cambios','git merge integra la historia indicada en la rama que está activa.','Fusionar incorpora una línea de trabajo.','git merge mejora-documentacion','La rama actual contiene los commits integrados.'],
    ['Resuelve conflictos','Un conflicto aparece cuando Git no puede decidir cómo combinar dos cambios.','Resolver significa elegir el contenido final y prepararlo.','git diff --name-only --diff-filter=U','Se listan archivos que siguen sin resolver.'],
    ['Conecta un remoto','Un remoto es un nombre para otra ubicación del repositorio; origin es una convención.','El remoto registra una URL de sincronización.','git remote -v','Se muestran nombres y URL configurados.'],
    ['Descarga y publica','fetch actualiza referencias; pull obtiene e integra; push envía commits.','Sincronizar exige entender la dirección y la rama.','git fetch origin','Las referencias origin se actualizan sin fusionar.'],
    ['Deshaz sin perder contexto','restore recupera contenido y revert crea un commit inverso sin ocultar la historia.','Revertir conserva una historia compartida comprensible.','git revert <commit>','Se crea un commit que invierte el cambio elegido.'],
    ['Etiquetas y versiones','Una etiqueta asigna un nombre estable a un commit y marca hitos publicados.','Las etiquetas identifican versiones concretas.','git tag -a v1.0 -m "Primera versión"','v1.0 aparece asociada al commit actual.'],
    ['Flujo completo de Git','Un buen flujo revisa estado, crea rama, prepara, prueba, confirma y sincroniza con intención.','Los commits pequeños facilitan revisión y recuperación.','git status\ngit diff\ngit log --oneline -5','Las consultas explican estado, cambios e historia.']
  ];
  const containerRaw = [
    ['Qué resuelve un contenedor','Un contenedor ejecuta procesos aislados y comparte el núcleo del anfitrión.','Una imagen es plantilla y un contenedor su instancia.','docker version','Cliente y motor muestran versiones compatibles.'],
    ['Imágenes, capas y registros','Las imágenes se construyen en capas y se descargan desde registros identificables.','Un digest identifica contenido mejor que una etiqueta mutable.','docker image ls','Aparece el inventario local de imágenes.'],
    ['Ejecuta tu primer contenedor','docker run crea y arranca un contenedor desde una imagen.','run combina creación e inicio con opciones explícitas.','docker run --rm hello-world','El ejemplo muestra un mensaje y se elimina.'],
    ['Lista e inspecciona','docker ps muestra contenedores y inspect expone configuración detallada.','Observar estado e identidad precede a cualquier cambio.','docker ps -a','Aparecen contenedores activos y detenidos.'],
    ['Registros y procesos','docker logs lee la salida capturada y top muestra procesos del contenedor.','Los registros conectan síntomas con la aplicación.','docker logs --tail 50 mi-app','Se muestran cincuenta líneas recientes.'],
    ['Detener y eliminar','stop solicita cierre ordenado; rm elimina un contenedor detenido.','Proceso, contenedor, imagen y datos tienen ciclos distintos.','docker stop mi-app','El contenedor cambia a estado detenido.'],
    ['Publica puertos','-p conecta un puerto del anfitrión con uno del contenedor.','Publicar amplía el alcance de un servicio.','docker run --rm -p 127.0.0.1:8080:80 nginx','El servicio queda disponible por loopback.'],
    ['Variables y secretos','-e define variables, pero estas pueden quedar visibles en inspecciones.','Los secretos requieren un mecanismo diseñado para protegerlos.','docker run --rm -e MODO=prueba alpine env','La salida incluye MODO=prueba.'],
    ['Volúmenes persistentes','Los volúmenes mantienen datos fuera de la capa escribible del contenedor.','Persistencia y proceso se diseñan por separado.','docker volume ls','Aparece el inventario de volúmenes.'],
    ['Montajes de carpeta','Un bind mount presenta una ruta real del anfitrión dentro del contenedor.','Los montajes enlazan explícitamente rutas.','docker run --rm -v "$PWD":/work:ro alpine ls /work','Se lista la carpeta actual en modo lectura.'],
    ['Redes de contenedores','Una red de usuario permite descubrimiento por nombre y separa grupos de servicios.','No todos los servicios internos necesitan puertos públicos.','docker network ls','Se muestran redes y sus controladores.'],
    ['Escribe un Dockerfile','Un Dockerfile describe pasos reproducibles para construir una imagen.','Un archivo declarativo permite revisar la construcción.','docker build -t mi-app:prueba .','Se crea una imagen etiquetada.'],
    ['Caché y builds pequeños','Docker reutiliza capas cuando instrucciones y entradas no cambian.','Ordenar capas estables mejora la caché.','docker history mi-app:prueba','Se muestran capas y tamaños de imagen.'],
    ['Compose para varios servicios','Compose describe servicios, redes y volúmenes en YAML.','La configuración declarativa coordina varios contenedores.','docker compose config','Se muestra la configuración combinada y validada.'],
    ['Operación y seguridad','Actualizar imágenes, limitar privilegios y observar recursos reduce impacto.','Cada contenedor debe recibir solo lo necesario.','docker stats --no-stream','Se obtiene una muestra de CPU y memoria.']
  ];
  function expand(raw, courseName) {
    return raw.map(([title, explain, concept, command, result]) => makeLesson(courseName, {
      title, explain, concept, command, result,
      context: courseName === 'Git' ? 'Git trabaja con contenido y referencias; sus consultas ayudan a mantener orientación.' : 'Los ejemplos requieren un entorno Docker local autorizado y datos de práctica.',
      caution: courseName === 'Git' ? 'Revisar estado y diferencias antes de guardar o compartir' : 'Revisar imagen, rutas, puertos y permisos antes de ejecutar',
      recovery: courseName === 'Git' ? 'Consultar git status, git diff y el mensaje exacto' : 'Consultar estado, logs e inspect del contenedor correcto',
      detail: `Ejemplo guiado de ${title.toLowerCase()}; revisa su salida antes de continuar.`,
      practice: `En un entorno de práctica, demuestra que: ${result.toLowerCase()}`
    }));
  }
  root.AcademyCourses.push({id:'git',title:'Git desde Linux',subtitle:'Versiona tus ideas y trabaja sin miedo a perder cambios.',category:'Git',level:'Intermedio',color:'rose',symbol:'⑂',label:'HISTORIAL CON SENTIDO',description:'Aprende el flujo local de Git, ramas, fusiones y remotos con prácticas recuperables.',requirements:'Manejo básico de archivos y terminal. Git debe estar instalado para las prácticas.',outcomes:['Crear repositorios y commits coherentes.','Trabajar con ramas y resolver conflictos.','Sincronizar remotos con intención.','Recuperar cambios sin destruir el historial.'],modules:['Tu historial local','Cambios comprensibles','Ramas sin miedo','Comparte y sincroniza','Recupera y publica'],resources:[['Manual oficial de Git','https://git-scm.com/docs'],['Libro Pro Git','https://git-scm.com/book/es/v2']],lessons:expand(gitRaw,'Git')});
  root.AcademyCourses.push({id:'contenedores',title:'Docker y contenedores',subtitle:'Empaqueta servicios y comprende cada capa.',category:'Contenedores',level:'Intermedio',color:'cyan',symbol:'▣',label:'ENTORNOS REPRODUCIBLES',description:'Comprende imágenes, contenedores, redes, volúmenes y Compose con fundamentos seguros.',requirements:'Terminal básica y conceptos de procesos, puertos y permisos. Docker es opcional para leer.',outcomes:['Distinguir imágenes, contenedores y volúmenes.','Publicar servicios y conectar redes.','Construir imágenes con Dockerfile.','Operar varios servicios con controles básicos.'],modules:['Primeros contenedores','Observa y controla','Datos y conectividad','Construye imágenes','Opera con criterio'],resources:[['Documentación de Docker','https://docs.docker.com/'],['Referencia de Dockerfile','https://docs.docker.com/reference/dockerfile/']],lessons:expand(containerRaw,'Docker')});
})(globalThis);
