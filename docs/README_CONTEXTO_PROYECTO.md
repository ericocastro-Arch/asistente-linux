# LinuxMate

## Contexto del proyecto para elaborar el informe de graduación

Este documento resume el propósito, el alcance técnico y el estado que puede comprobarse en el repositorio de LinuxMate. Está pensado como punto de partida para una persona asesora o una IA que apoyará la redacción del informe. No reemplaza la guía de graduación de la universidad ni los resultados que el equipo debe obtener mediante pruebas.

## Identificación

- **Nombre del proyecto:** LinuxMate (el repositorio también se identifica como Asistente Linux).
- **Tipo de proyecto:** desarrollo de software aplicado.
- **Propósito:** facilitar tareas de administración y aprendizaje de Linux mediante una interfaz gráfica y conversacional en español, con énfasis en personas principiantes.
- **Usuarios previstos:** personas que usan Linux y necesitan consultar el estado del equipo, comprender diagnósticos o realizar tareas habituales sin depender de recordar comandos.
- **Plataforma principal:** escritorio Linux. El código contempla adaptar algunas operaciones a diferentes familias y gestores de paquetes; esto no equivale a certificar compatibilidad con toda distribución.

## Problema que aborda

La administración de Linux puede exigir familiaridad con la terminal, los comandos, los gestores de paquetes, los permisos y los mensajes de error. Para una persona nueva, es difícil saber qué herramienta usar, qué significa el resultado y qué consecuencias tiene una acción. LinuxMate busca ofrecer un punto de entrada más accesible: recibir solicitudes en lenguaje natural, orientar a la persona mediante vistas gráficas y explicaciones, y controlar las operaciones que puedan modificar el sistema.

Esta formulación describe el propósito inferible del producto. Si el informe necesita cifras sobre usuarios afectados, una encuesta diagnóstica o datos de una institución, esos datos deben obtenerse de fuentes reales; no deben deducirse del código.

## Objetivo general sugerido

Desarrollar una aplicación de escritorio para Linux que facilite a usuarios principiantes la consulta, el diagnóstico y la administración guiada del sistema mediante interacción conversacional y visual, con controles de seguridad y registro de actividad.

Este objetivo es una propuesta redactada a partir del producto. Debe compararse con el objetivo aprobado por la universidad o el asesor antes de incorporarlo como objetivo oficial.

## Arquitectura y tecnologías visibles

La solución separa la interfaz de usuario, el procesamiento de solicitudes, las herramientas del sistema, la seguridad y el almacenamiento.

- **Interfaz:** HTML, CSS y JavaScript en `src/gui/web/`; la aplicación Python expone funciones a la interfaz mediante PyWebView.
- **Agente y proveedores:** `src/core/agent.py`, `src/core/llm.py` y `src/core/providers.py` coordinan respuestas de modelos y llamadas estructuradas a herramientas. La documentación enumera Groq, NVIDIA NIM, OpenAI, Anthropic, Gemini, xAI, Together AI, DeepSeek, Alibaba Cloud Qwen, Moonshot Kimi, Z.ai, Ollama y una API personalizada.
- **Enrutamiento:** `src/nlp/router.py` y `src/nlp/processor.py` priorizan rutas locales para intenciones conocidas y delegan al agente las solicitudes que requieren interpretación adicional.
- **Herramientas del sistema:** `src/core/tools.py` y módulos especializados consultan o administran funciones de Linux.
- **Seguridad y políticas:** `src/core/security.py` y `src/core/policy.py` clasifican operaciones, restringen comandos sensibles y gestionan modos de autorización.
- **Persistencia:** `src/core/storage.py` usa SQLite para sesiones, mensajes, ejecuciones y capturas del sistema. El progreso educativo se guarda de forma local por separado.
- **Distribuciones:** `src/core/distro.py` detecta información de distribución y adapta algunas operaciones de paquetes.

## Funciones documentadas

1. Chat conversacional en español, con un modo de conversación general separado de las acciones del sistema.
2. Diagnósticos locales para síntomas y consultas sobre recursos del equipo.
3. Vistas de recursos, procesos, red, servicios, instalación de programas y actualizaciones.
4. Búsqueda y gestión de programas mediante fuentes como apt, Snap, Flatpak y archivos `.deb`; el código contempla más gestores según la distribución.
5. Herramientas para archivos personales, copias de seguridad, recuperación de cambios y espacio de trabajo de código con revisión antes de aplicar propuestas.
6. Políticas para bloquear acciones peligrosas y pedir confirmación ante acciones sensibles.
7. Registro local de sesiones, mensajes, ejecuciones y datos seleccionados del sistema.
8. Configuración de proveedores de modelos; el uso de servicios remotos requiere credenciales y conexión.
9. Funciones opcionales de voz; el reconocimiento offline depende de un modelo de Vosk disponible.
10. Academia local Aprende Linux. El README describe seis cursos, cinco módulos y quince lecciones por curso, exámenes, notas y progreso. La terminal de práctica es simulada y no ejecuta comandos en el sistema.
11. Guías y panel de bienvenida para orientar a la persona usuaria.

La lista refleja módulos documentados y presentes en el repositorio; no significa que todas las funciones hayan sido aceptadas por usuarios o comprobadas en todas las distribuciones.

## Método de desarrollo que puede describirse

El historial y la estructura del código son compatibles con un desarrollo incremental de tipo aplicado: se construyen componentes, se integran en la aplicación y se agregan pruebas automatizadas para casos definidos. Es válido describir esta metodología como una reconstrucción técnica basada en la evidencia del repositorio.

No se encontró en el repositorio un protocolo aprobado, un registro de entrevistas, una encuesta, actas de aceptación, datos de sesiones con usuarios ni un informe actual de ejecución completa de pruebas. No se debe afirmar que esas actividades ocurrieron sin evidencia del equipo.

## Estado verificable del proyecto

La base funcional es amplia y cuenta con módulos y pruebas automatizadas para seguridad, configuración, diagnóstico, distribución, ejecución de herramientas, PyWebView, academia, respaldos, espacio de trabajo y otros componentes. El historial contiene commits de implementación.

Al revisar el árbol de trabajo se observaron cambios locales sin confirmar en varios módulos centrales y pruebas, además de archivos nuevos para la pantalla de bienvenida. Por ese motivo, el código revisado no debe presentarse como una versión congelada. La existencia de pruebas tampoco demuestra que hayan pasado: hace falta ejecutar la suite sobre la versión que se entregará y conservar el resultado.

No se encontraron mediciones verificables de rendimiento, resultados de pruebas con usuarios, encuesta de satisfacción ni acta de aceptación. Por tanto, el estado prudente es: **implementación avanzada; cierre y validación final pendientes de comprobar**.

## Evidencia que debe recolectarse antes de afirmar que está terminado

- Identificador del commit o versión final y lista de cambios incluidos.
- Entorno de ejecución: distribución, versión, entorno gráfico, versión de Python y dependencias.
- Salida de la suite de pruebas, con cantidad aprobada, fallida y omitida.
- Pruebas manuales de instalación, inicio, tareas críticas y recuperación ante errores.
- Matriz de compatibilidad limitada a las distribuciones y versiones realmente ensayadas.
- Mediciones de rendimiento si el informe va a afirmar que se alcanzó una meta de memoria o tiempo.
- Evaluación de usabilidad o aprendizaje, solo si se realiza con participantes e instrumentos documentados.
- Guía institucional, título oficial, objetivos aprobados y capítulos anteriores para alinear el informe.

## Estructura académica que se puede proponer

La estructura depende de la facultad. Una propuesta común, que debe validarse con el asesor, es:

- **Capítulo IV. Desarrollo e implementación:** método técnico, arquitectura, módulos, flujos, controles, persistencia y decisiones de implementación.
- **Capítulo V. Resultados y evaluación:** evidencia de pruebas, resultados observados, compatibilidad, rendimiento y evaluación de usuarios, distinguiendo con claridad lo medido de lo pendiente.
- **Capítulo VI. Conclusiones y recomendaciones:** conclusiones vinculadas a los objetivos, limitaciones y acciones futuras.

No se deben completar resultados con valores estimados o ejemplos ficticios. Los casos propuestos para evaluación deben identificarse como plan de trabajo, no como resultados ya obtenidos.

## Archivos útiles del repositorio

- `README.md`: instalación, funciones, arquitectura y comandos de verificación sugeridos.
- `docs/proveedores.md`: configuración y alcance de los proveedores de modelos.
- `tests/`: pruebas automatizadas que describen comportamientos esperados.
- `src/core/`: agente, seguridad, políticas, herramientas, almacenamiento y distribución.
- `src/nlp/`: procesamiento y enrutamiento de solicitudes.
- `src/gui/` y `src/gui/web/`: interfaz de escritorio y recursos web.
- `docs/capitulos_4_5_6_linuxmate.docx`: borrador de capítulos preparado a partir del estado observado; requiere alineación con la guía institucional y actualización con resultados reales.
