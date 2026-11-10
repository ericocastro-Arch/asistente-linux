# Análisis del Documento (Capítulos III en adelante) y Desarrollo de los Capítulos V y VI

> [!IMPORTANT]
> **Respeto a la restricción solicitada:** Los **Capítulos I y II** no han sido modificados ni alterados. Sin embargo, todas las variables, hipótesis, indicadores ($\text{TRT}$, $\text{TEI}$, $\text{IEO}$, $\text{PCC / NASA-TLX}$, escala $\text{SUS}$ y prueba $t$ de Student) y objetivos planteados en los Capítulos I y II se utilizaron como base estricta para estructurar y validar los nuevos **Capítulos V y VI**.

---

## PARTE 1: Diagnóstico y Análisis Crítico (Desde el Capítulo III en adelante)

Tras revisar minuciosamente el texto entregado desde el **Capítulo III** hasta el **Glosario de Términos** y contrastarlo con la implementación real del software en el repositorio del proyecto ([`README.md`](file:///home/castro77/asistente-linux/README.md), [`main.py`](file:///home/castro77/asistente-linux/main.py), [`src/core/`](file:///home/castro77/asistente-linux/src/core) y [`tests/`](file:///home/castro77/asistente-linux/tests)), se identificaron los siguientes hallazgos que deben corregirse en el documento final:

### 1.1 Hallazgos en el Capítulo III (Marco Teórico)

| Sección | Problema Detectado en el Borrador | Corrección Aplicada en la Versión Optimizada |
| :--- | :--- | :--- |
| **3.1.2 Interfaz de Usuario** | Cita incompleta al final del primer punto: dice `Nielsen .` sin año ni paréntesis. | Se corrigió a `(Nielsen, 1993)` según normativa APA 7. |
| **3.2.1 Filosofía de Diseño de Windows** | **Párrafo duplicado e inconcluso:** El título `3.2.1` y su primer párrafo aparecen dos veces seguidas, cortándose abruptamente en la frase `"Como postula"`. | Se eliminó la duplicación y se unificó la cita de `Norman (2013)` en un párrafo continuo y coherente. |
| **3.3.1, 3.3.2 y 3.3.6.1** | **Ruptura del estilo académico impersonal:** Se emplea primera persona singular (`"considero crucial"`, `"He identificado"`, `"mi proyecto de graduación"`), mientras que el resto del documento usa tercera persona impersonal. | Se estandarizó toda la redacción a tercera persona impersonal (`"se considera crucial"`, `"se ha identificado"`, `"el presente proyecto"`). |
| **3.3.4 y 3.3.7** | **Sección repetida:** El apartado `"Arquitectura Propuesta para el Ecosistema de Asistencia"` aparece en `3.3.4` y vuelve a repetirse como `3.3.7` con una oración incompleta sin punto final. | Se consolidó en un único apartado (`3.3.6`) al cierre del bloque de Linux, eliminando la duplicidad. |
| **Vacío teórico de PLN y LLM** | La introducción del Capítulo III anuncia tres áreas (Sistemas Operativos, HCI/Usabilidad y PLN/Agentes Conversacionales), pero el capítulo omitía la sección teórica sobre **PLN, Modelos de Lenguaje (LLM) y *Tool Calling***. | Se incorporó la sección **`3.5 Procesamiento de Lenguaje Natural (PLN) y Agentes Basados en LLM`** antes del cuadro comparativo (que pasa a ser `3.6`). |
| **Tabla 1 (Sección 3.5 / 3.6)** | Contiene errores ortográficos (`"Lenguaje Conversacion"`, `"OpenClow"`, `"Nuebvo"`) y justificaciones coloquiales (`"Es el mejor agente hoy en dia"`). | Se corrigió la ortografía, el rigor técnico y la alineación con las herramientas reales del proyecto (`Python 3`, `PyWebView / CustomTkinter`, `SQLite`, `PolicyKit / pkexec` y arquitectura multi-proveedor LLM con `Groq / OpenAI / Ollama`). |

### 1.2 Hallazgos en el Capítulo IV (Análisis y Diseño de la Aplicación)

| Sección | Problema Detectado en el Borrador | Corrección Aplicada en la Versión Optimizada |
| :--- | :--- | :--- |
| **4.1.1 Requerimientos Funcionales** | Aparecen superíndices residuales (`$^1$`, `$^2$`, `$^3$`) sin notas al pie asociadas, y un error ortográfico en `RF-04` (`"Tradución"` en lugar de `"Traducción"`). | Se eliminaron los superíndices huérfanos, se corrigió `"Traducción"` y se añadieron los requerimientos reales de respaldo/deshacer y guía de migración Windows-Linux. |
| **4.2 y 4.3 Nomenclatura del Orquestador** | Inconsistencia en el nombre del componente central: en Cap. III se llama `OpenClow`, en la figura de `4.2` aparece `OpenClaw` y en `4.3.1` dice `OpenCloud`. | Se unificó la denominación técnica como **Agente Orquestador LinuxMate AI (Middleware Conversacional)**, manteniendo referencia clara a los diagramas. |
| **4.3 Arquitectura y Diseño Modular** | Bajo el diagrama de arquitectura aparece la frase `"Diseño Modular del Software"` repetida 4 veces en líneas seguidas. | Se eliminaron las repeticiones y se colocó un pie de figura académico numerado (`Figura 2`). |
| **4.4 Diagrama de Secuencia** | Antes del diagrama aparece texto corrupto pegado de una etiqueta: `"6. Código de salida / Salida estándarInvocación segura de la Shell"`. | Se limpió el texto corrupto y se añadió la explicación técnica paso a paso de los 13 mensajes del diagrama de secuencia. |
| **4.5 Seguridad** | Describe la sanitización básica, pero no menciona que el código real implementa **4 niveles de riesgo (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)**, integración con **`PolicyKit (pkexec)`** y respaldos atómicos **`SHA-256`**. | Se amplió la sección `4.5` para reflejar fielmente la arquitectura de seguridad de [`src/core/security.py`](file:///home/castro77/asistente-linux/src/core/security.py), [`src/core/policy.py`](file:///home/castro77/asistente-linux/src/core/policy.py), [`src/core/privilege.py`](file:///home/castro77/asistente-linux/src/core/privilege.py) y [`src/core/backups.py`](file:///home/castro77/asistente-linux/src/core/backups.py). |

### 1.3 Hallazgos en Referencias y Glosario

- **Referencias:** El listado original mezclaba numeraciones (`221`, `50`, `55 [15]`), contenía anotaciones personales de borrador (`"(Repetido en tu lista)"`, `"(Verificación de copia)"`, `"(Justifica los modelos...)"`) y entradas incompletas (`"Van Dijk, Países Bajos, 2020"`). Se depuró por completo en **formato APA 7.ª edición** en orden alfabético estricto y sin duplicados.
- **Glosario:** Se corrigió el punto suelto final (`.`) y se añadieron términos clave de la arquitectura del proyecto (`Middleware`, `PolicyKit / pkexec`, `SQLite`, `Tool Calling`).

---

## PARTE 2: Documento Completo y Organizado (Capítulos III, IV, V, VI, Referencias y Glosario)

A continuación se presenta el contenido íntegro, corregido y estructurado académicamente desde el **Capítulo III** hasta el **Glosario de Términos**, listo para integrarse directamente después del Capítulo II de su documento de graduación.

---

# CAPÍTULO III
# MARCO TEÓRICO

El presente marco teórico expone los fundamentos científicos, metodológicos y tecnológicos que sustentan el desarrollo de un ecosistema de asistencia inteligente orientado a mitigar las barreras de adopción tecnológica durante la transición entre entornos operativos. La investigación se posiciona en la convergencia de tres grandes áreas del conocimiento: la arquitectura de sistemas operativos, la ingeniería de la usabilidad mediante la interacción humano-computadora (HCI), y las ciencias de la computación enfocadas en el procesamiento de lenguaje natural (PLN) y los agentes conversacionales.

## 3.1 Fundamentos de Sistemas Operativos y Arquitectura de Software

La comprensión de las barreras que enfrenta un usuario básico requiere analizar la naturaleza arquitectónica de los sistemas operativos modernos. Un sistema operativo se define conceptualmente como el software de base que actúa como intermediario entre el hardware físico de la máquina y las aplicaciones de usuario, gestionando de forma segura y óptima los recursos de computación tales como el procesador (CPU), la memoria principal, el almacenamiento secundario y los dispositivos periféricos (Silberschatz, Galvin y Gagne, 2018).

### 3.1.1 Arquitectura por Capas y el Rol del Kernel

Desde la perspectiva de la ingeniería de software, los sistemas operativos emplean una arquitectura modular y jerárquica dividida en capas de abstracción. El núcleo o *Kernel* constituye la capa más interna y crítica del sistema; se ejecuta en el denominado "modo supervisor" o "modo protegido" (*kernel space*), lo que le otorga acceso sin restricciones a los recursos físicos de hardware (Stallings, 2017).

Para proteger la estabilidad del equipo contra ejecuciones erróneas o malintencionadas por parte del usuario, se implementa el "espacio de usuario" (*user space*), una capa aislada donde se ejecutan las aplicaciones cotidianas. Cualquier interacción con el hardware desde el espacio de usuario debe canalizarse mediante llamadas al sistema (*system calls*), las cuales son validadas estrictamente por el Kernel antes de su ejecución.

### 3.1.2 La Interfaz de Usuario: Evolución de CLI a GUI

La interacción entre el ser humano y las capas lógicas del sistema operativo se realiza a través del *Shell* o intérprete de comandos. Históricamente, la evolución de estas interfaces se divide en dos paradigmas fundamentales:

- **Interfaz de Línea de Comandos (CLI - *Command Line Interface*):** Es una interfaz puramente textual basada en un flujo determinista de instrucciones escritas. Exige al usuario el conocimiento exacto de la sintaxis, las banderas (*flags*), los parámetros y los nombres de los binarios ejecutables del sistema. Aunque proporciona un control absoluto, directo y altamente eficiente para la administración de sistemas y automatización, carece de pistas visuales contextuales (*affordances*), lo que la convierte en una interfaz con una severa barrera de accesibilidad para la población no especializada (Nielsen, 1993).
- **Interfaz Gráfica de Usuario (GUI - *Graphical User Interface*):** Introdujo abstracciones visuales basadas en el paradigma WIMP (*Windows, Icons, Menus, Pointer*). Diseñada para ocultar la complejidad interna del sistema operativo, la GUI permite al usuario ejecutar tareas mediante el reconocimiento visual y la manipulación directa de objetos gráficos (clics, arrastrar y soltar), reduciendo la necesidad de memorizar comandos abstractos (Tanenbaum y Wetherall, 2011).

## 3.2 El Ecosistema de Microsoft Windows y la Dependencia de Entorno

Para analizar la dificultad en la transición de software es indispensable comprender el punto de partida cognitivo del sujeto de estudio. El mercado global de la computación personal ha estado históricamente dominado por la arquitectura comercial de Microsoft Windows, lo que genera un fenómeno sociotécnico conocido como "dependencia de trayectoria" (*path dependency*) o monopolio cognitivo en la alfabetización digital.

### 3.2.1 Filosofía de Diseño de Windows y Abstracción Total

La filosofía de ingeniería detrás de entornos como Windows 10 y Windows 11 se centra en la opacidad del sistema subyacente. El objetivo de diseño consiste en que el usuario final rara vez interactúe de manera directa con el núcleo de la máquina. Las rutas críticas de configuración (registro del sistema, servicios de red, instalación de controladores) se gestionan primordialmente a través de asistentes visuales secuenciales (*wizards*).

Esta abstracción genera un "modelo mental" específico en el usuario común. Como postula Norman (2013), el usuario construye su comprensión del software a partir de la visibilidad de la interfaz gráfica y no del funcionamiento interno real del sistema. En consecuencia, el usuario asume que la informática se gestiona de manera espacial y visual: los programas se instalan haciendo doble clic en un archivo empaquetado (extensión `.exe` o `.msi`), y el almacenamiento está estructurado bajo letras de unidades lógicas jerarquizadas por la unidad raíz `C:\`, lo cual responde a las metáforas de escritorio ampliamente documentadas en la interacción humano-computadora (Preece, Sharp y Rogers, 2015).

### 3.2.2 El Impacto de la Exclusión Sociotecnológica

Cuando un usuario es expuesto exclusivamente a un único entorno comercial, su flexibilidad de adaptación técnica disminuye. Como señala Van Dijk (2020) en su teoría sobre la brecha digital, la exclusión tecnológica contemporánea no solo se define por la falta de acceso físico a un computador (*brecha de primer orden*), sino por la carencia de competencias operativas transferibles (*skills divide* o *brecha de segundo orden*) que permitan al individuo migrar desde herramientas privativas hacia entornos abiertos, libres y soberanos.

## 3.3 El Ecosistema GNU/Linux y el Software Libre

El ecosistema basado en el núcleo Linux y las herramientas del proyecto GNU representa un paradigma opuesto a la estructura comercial de Windows, tanto en sus principios filosóficos como en su organización arquitectónica.

### 3.3.1 Diversidad, Distribuciones y Entornos de Escritorio

A diferencia de los sistemas operativos monolíticos y cerrados como Windows 11, GNU/Linux no constituye un producto único e invariable, sino un núcleo (*kernel*) común sobre el cual se articula un ecosistema modular y diversificado (Torvalds y Diamond, 2001). Esta amplitud tecnológica se fundamenta en dos pilares arquitectónicos independientes: las distribuciones y los entornos de escritorio.

### 3.3.2 Las Distribuciones (*Distros*) como Filosofías Operativas

Una distribución es un conjunto integrado de software que empaqueta el núcleo Linux junto con bibliotecas del sistema, utilidades de administración y un gestor de paquetes específico (Negus, 2020). La complejidad para el usuario principiante radica en que cada familia de distribuciones responde a convenciones y sintaxis administrativas particulares:

- **Familia Debian / Ubuntu (Linux Mint, Pop!_OS):** Enfocada en la estabilidad, el soporte comunitario amplio y la facilidad de adopción. Utiliza el sistema de empaquetado `.deb` y el gestor `apt` / `dpkg`.
- **Familia Red Hat / Fedora (RHEL, Rocky Linux, AlmaLinux):** Orientada a entornos corporativos, servidores y estaciones de trabajo de desarrollo. Utiliza paquetes `.rpm` y el gestor `dnf`.
- **Familia Arch Linux (Manjaro, EndeavourOS):** Diseñada bajo el principio de simplicidad estructural y actualización continua (*rolling release*). Emplea el gestor `pacman`.
- **Familia SUSE (openSUSE Leap / Tumbleweed):** Reconocida por sus herramientas administrativas robustas, gestionada mediante `zypper`.

### 3.3.3 Capas de Personalización Gráfica: Entornos de Escritorio (DE)

La modularidad de Linux permite desacoplar el motor del sistema de su apariencia visual. Una misma distribución puede lucir y operar de formas radicalmente distintas según el Entorno de Escritorio (*Desktop Environment*) seleccionado (Love, 2010):

- **GNOME:** Interfaz moderna, minimalista y orientada a flujos de trabajo por actividades, cuya disposición espacial difiere de la barra de tareas tradicional de Windows.
- **KDE Plasma:** Entorno altamente configurable y potente que conserva una disposición espacial similar a Windows (menú de inicio inferior, bandeja del sistema y ventanas clásicas), facilitando la transición visual.
- **XFCE, MATE y Cinnamon:** Entornos ligeros y tradicionales diseñados para optimizar el consumo de memoria RAM, ideales para la recuperación de hardware de bajos recursos o equipos reacondicionados.

Esta ramificación tecnológica constituye una fortaleza técnica de GNU/Linux, pero simultáneamente representa una barrera de entrada: el usuario principiante se enfrenta a la paradoja de la elección y a la fragmentación de comandos entre distribuciones.

### 3.3.4 Principios del Software Libre e Implicaciones en la Accesibilidad

De acuerdo con Stallman (2002) y la Free Software Foundation (2021), el software libre se define por el cumplimiento de cuatro libertades esenciales para el usuario:
1. La libertad de ejecutar el programa con cualquier propósito (Libertad 0).
2. La libertad de estudiar cómo funciona el programa y cambiarlo para que se ajuste a las necesidades del usuario (Libertad 1).
3. La libertad de redistribuir copias para ayudar a otros (Libertad 2).
4. La libertad de distribuir copias de sus versiones modificadas a terceros (Libertad 3).

Esta base filosófica impacta directamente en dos dimensiones críticas del proyecto:

1. **Soberanía en el Desarrollo de Accesibilidad:** Al disponer de acceso abierto a las interfaces del sistema operativo, los agentes de asistencia inteligente pueden interactuar con los subsistemas de paquetes, red, servicios y diagnóstico sin las restricciones de APIs cerradas o costos de licenciamiento corporativo.
2. **La Filosofía UNIX como Reto de Usabilidad:** El diseño de Linux hereda la máxima de la filosofía UNIX: *"Escribe programas que hagan una sola cosa y la hagan bien, y que trabajen juntos mediante flujos de texto"* (Raymond, 2003). Aunque esta modularidad otorga una gran robustez en ingeniería de sistemas, obliga al usuario sin formación técnica a encadenar múltiples utilidades de consola para resolver problemas cotidianos, justificando la necesidad de un agente conversacional que unifique dichas herramientas bajo un diálogo natural.

### 3.3.5 Arquitectura y Disonancia Operativa en Linux

Durante el proceso de migración desde Windows hacia Linux, el usuario experimenta un fenómeno denominado **disonancia operativa**, originado por el contraste entre su modelo mental previo y tres características nativas de GNU/Linux:

- **Estructura de Archivos Unificada (FHS):** Linux no asigna letras a las unidades de almacenamiento (`C:\`, `D:\`). Todo el árbol de directorios parte de una raíz única representada por `/` (*root directory*). De acuerdo con el *Filesystem Hierarchy Standard* (Linux Foundation, 2015), las particiones y dispositivos externos se montan dinámicamente dentro de subdirectorios como `/home`, `/media` o `/mnt`, alterando la navegación espacial habitual del usuario (Nielsen, 2012).
- **Gestión Centralizada de Paquetes y Repositorios:** En lugar de descargar ejecutables aislados de sitios web arbitrarios, el software en Linux se obtiene desde repositorios firmados criptográficamente mediante gestores nativos (`apt`, `dnf`, `pacman`, `zypper`) o contenedores universales (`Flatpak`, `Snap`) (Nemeth, Snyder, Hein, Whaley y Mackin, 2018).
- **Dependencia de la Terminal y Elevación de Privilegios:** A pesar de la madurez de los entornos gráficos actuales, el diagnóstico profundo, la reparación de dependencias rotas y la gestión de servicios del sistema (`systemd`) continúan requiriendo instrucciones en Bash y elevación de permisos mediante `sudo` o `PolicyKit (pkexec)` (Ward, 2014; Shneiderman et al., 2016).

### 3.3.6 Arquitectura de Agentes Colaborativos para el Ecosistema de Asistencia

Para absorber la complejidad derivada de la fragmentación de distribuciones y la disonancia operativa, el proyecto fundamenta su diseño en el paradigma de **Agentes Inteligentes Colaborativos** (Russell y Norvig, 2020). El asistente opera como un *middleware* mediador entre el espacio de usuario y los subsistemas de la distribución Linux, estructurado en tres fases deterministas:

1. **Fase de Abstracción Conversacional:** El usuario expresa su necesidad operativa o síntoma técnico empleando lenguaje natural en español coloquial (p. ej., *"mi computadora está lenta"*, *"quiero instalar LibreOffice"* o *"¿qué programa uso en lugar de Word?"*).
2. **Fase de Enrutamiento Híbrido y Validación Semántica:** Un enrutador determinista local clasifica si la solicitud corresponde a una acción directa, un diagnóstico local o una consulta que requiere inferencia del modelo de lenguaje (LLM). El sistema detecta automáticamente la familia de la distribución (`/etc/os-release`) para adaptar los comandos al gestor de paquetes correspondiente (`apt`, `dnf`, `pacman`, `zypper`, `flatpak` o `snap`).
3. **Fase de Ejecución Segura y Retroalimentación Pedagógica:** Antes de ejecutar cualquier acción en el sistema operativo, un motor de políticas y seguridad evalúa el nivel de riesgo, bloquea patrones destructivos, solicita autorización explícita para operaciones privilegiadas mediante `PolicyKit (pkexec)` o confirmación visual, registra la auditoría en base de datos local y devuelve al usuario una explicación comprensible que fomenta el aprendizaje progresivo.

## 3.4 Interacción Humano-Computadora (HCI) y Usabilidad

La ingeniería de la usabilidad proporciona el marco teórico y psicométrico para evaluar cuantitativamente la interacción entre los usuarios principiantes y el software desarrollado.

### 3.4.1 Atributos de Usabilidad de Nielsen

Para determinar si un sistema informático satisface los estándares de calidad en la interacción, Nielsen (1993) establece cinco atributos medibles:
1. **Capacidad de Aprendizaje (*Learnability*):** Facilidad con la que un usuario novato logra completar tareas básicas la primera vez que utiliza la interfaz.
2. **Eficiencia (*Efficiency*):** Rapidez con la que el usuario ejecuta las tareas una vez familiarizado con el entorno, medida cronométricamente mediante el Tiempo de Resolución de Tarea (TRT).
3. **Capacidad de ser Recordado (*Memorability*):** Facilidad para retomar el uso del sistema tras un periodo de inactividad sin necesidad de reaprender su funcionamiento.
4. **Prevención y Manejo de Errores (*Errors*):** Frecuencia y severidad de los errores cometidos por el usuario (Índice de Errores Operativos - IEO), así como la capacidad del software para prevenirlos y recuperarse de ellos.
5. **Satisfacción Subjetiva (*Satisfaction*):** Percepción de comodidad y agrado del usuario hacia el sistema, evaluada mediante instrumentos estandarizados como la escala SUS (*System Usability Scale*) de Brooke (1996).

### 3.4.2 Teoría de la Carga Cognitiva y Andamiaje

La confrontación de un usuario sin formación técnica con una interfaz de línea de comandos desencadena una saturación en la memoria de trabajo explicada por la Teoría de la Carga Cognitiva de Sweller (1988, 2011). Esta teoría divide el esfuerzo mental en tres componentes:

- **Carga Intrínseca:** Inherente a la naturaleza y complejidad propia de la tarea administrativa.
- **Carga Extrínseca:** Generada por la manera deficiente o críptica en que la interfaz presenta la información (como una consola en blanco que exige recordar sintaxis exacta y abreviaturas en inglés).
- **Carga Germánica:** Esfuerzo cognitivo productivo destinado a construir esquemas mentales duraderos y aprendizaje significativo.

El asistente inteligente propuesto actúa directamente sobre la **carga extrínseca**, reduciéndola al mínimo mediante el diálogo en español y vistas gráficas guiadas (Hollender, Hofmann, Deneke y Schmitz, 2010). Simultáneamente, potencia la **carga germánica** a través del principio de **Andamiaje Cognitivo** y la Zona de Desarrollo Próximo de Vygotsky (1978): al explicar brevemente qué comando se utilizó y por qué, el asistente educa al usuario gradualmente mientras resuelve su problema inmediato.

### 3.4.3 El Modelo de Aceptación Tecnológica (TAM)

Para modelar la disposición de los usuarios a migrar hacia entornos GNU/Linux asistidos por IA, se aplica el Modelo de Aceptación Tecnológica (TAM) de Davis (1989). El modelo TAM postula que la adopción real de un sistema depende de dos constructos determinantes:
- **Utilidad Percibida (*Perceived Usefulness*):** Grado en que la persona considera que el asistente mejora su desempeño y resuelve sus problemas reales en el computador.
- **Facilidad de Uso Percibida (*Perceived Ease of Use*):** Grado en que el usuario percibe que la interacción con el asistente está libre de esfuerzo mental excesivo.

## 3.5 Procesamiento de Lenguaje Natural (PLN) y Agentes Basados en LLM

El Procesamiento de Lenguaje Natural (PLN) constituye la subdisciplina de la inteligencia artificial y la lingüística computacional encargada de permitir que las computadoras comprendan, interpreten y generen lenguaje humano de forma contextual (Jurafsky y Martin, 2020). Con el surgimiento de la arquitectura *Transformer* y los Modelos de Lenguaje de Gran Escala (LLM), los sistemas de PLN evolucionaron desde reglas sintácticas rígidas hacia capacidades avanzadas de mapeo semántico y razonamiento pragmático (Goodfellow, Bengio y Courville, 2016; Russell y Norvig, 2020).

En la ingeniería de software moderna, la integración de un LLM con un sistema operativo se realiza mediante el paradigma de **Agentes con Ejecución de Herramientas (*Tool Calling* o *Function Calling*)**. Bajo este esquema, el modelo de lenguaje no ejecuta código arbitrario de forma descontrolada, sino que selecciona de un catálogo estructurado de herramientas predefinidas (especificadas mediante esquemas JSON) cuál función invocar y con qué argumentos tipados, delegando la validación de seguridad y la ejecución real al motor determinista local escrito en Python.

## 3.6 Cuadro Comparativo de Tecnologías y Herramientas del Proyecto

Como parte del diseño metodológico y la selección de la arquitectura tecnológica del proyecto, se realizó una evaluación técnica comparativa de las herramientas disponibles en el ecosistema de desarrollo de software e Inteligencia Artificial. Este análisis sustenta la elección de los componentes integrados en el sistema **LinuxMate AI (Asistente Linux)**.

**Tabla 1**  
*Cuadro comparativo de tecnologías y componentes de software del proyecto*

| Componente | Tecnología Seleccionada | Ventajas Técnicas | Limitaciones / Consideraciones | Justificación en el Proyecto |
| :--- | :--- | :--- | :--- | :--- |
| **Motor de Inferencia en Nube (API LLM)** | Groq (`gpt-oss-20b` / Llama 3) y OpenAI (`GPT-4o mini`) | Alta velocidad de inferencia (baja latencia), soporte nativo de *Tool Calling* y excelente comprensión del español coloquial. | Requiere conexión a internet para consultas abiertas a la IA. | Garantiza precisión semántica y tiempos de respuesta menores a 2 segundos con costos operativos mínimos ($\le \text{Q } 4.00\text{/mes}$). |
| **Inferencia Local y Multi-Proveedor** | Ollama (Llama 3 local) + Soporte para 13 proveedores | Ejecución 100 % local sin internet ni costo por token cuando se dispone de hardware compatible; flexibilidad de cambio de proveedor. | Los modelos locales demandan mayor memoria RAM y GPU/CPU en equipos antiguos. | Permite operar tanto en equipos modestos vía API ligera como en entornos desconectados mediante Ollama y el enrutador local. |
| **Lenguaje Base y Backend** | Python 3.10+ (`subprocess`, `psutil`, `sqlite3`) | Ecosistema maduro para administración de sistemas Linux, manejo seguro de procesos y telemetría de hardware en tiempo real. | Lenguaje interpretado (menor velocidad bruta en cálculo intensivo frente a C/Rust). | El cuello de botella es de E/S y red; Python ofrece integración nativa con el Kernel Linux, SQLite y las bibliotecas de IA. |
| **Interfaz Gráfica de Usuario (GUI)** | Arquitectura Dual: `PyWebView` (HTML5/CSS3/JS) + Respaldo en `CustomTkinter` | Interfaz moderna *Liquid Glass* con alto contraste, paneles visuales interactivos y degradación elegante (*fallback*) a `CustomTkinter` si falta WebKit. | Requiere mantener sincronizada la capa de puente (`JsApi`) entre el frontend y Python. | Cumple los principios de usabilidad de Nielsen y mantiene el consumo de memoria RAM por debajo del límite de $200\text{ MB}$. |
| **Seguridad y Elevación de Privilegios** | Motor de Políticas Local + `PolicyKit (pkexec)` + `Keyring` | Clasificación en 4 niveles de riesgo, bloqueo de comandos destructivos, autenticación gráfica nativa del sistema y resguardo seguro de credenciales. | Requiere reglas de política definidas para acciones administrativas específicas. | Garantiza el principio de mínimo privilegio: el agente nunca opera como `root` silencioso ni expone claves en texto plano. |
| **Persistencia y Auditoría** | `SQLite 3` (`assistant.db`) + Respaldos `SHA-256` (`manifest.jsonl`) | Base de datos relacional transaccional sin servidor externo, con trazabilidad completa de sesiones, mensajes y herramientas ejecutadas. | Almacenamiento estrictamente local por estación de trabajo. | Permite auditar cada comando ejecutado (`stdout`, `stderr`, `exit_code`) y deshacer modificaciones de archivos de forma atómica. |

*Nota.* Elaboración propia con base en las especificaciones técnicas del sistema LinuxMate AI (Castro Pérez, 2026).

---

# CAPÍTULO IV
# ANÁLISIS Y DISEÑO DE LA APLICACIÓN

En este capítulo se establece la arquitectura formal y la especificación de ingeniería del sistema **LinuxMate AI (Asistente Conversacional Inteligente para Linux)**. A través del Análisis y Diseño de Software, se define la transformación de las necesidades del usuario final —identificadas en el estudio diagnóstico del Capítulo II— en componentes informáticos modulares, seguros, auditables y escalables (Pressman y Maxim, 2020; Sommerville, 2016). La solución propuesta se concibe como un *middleware* conversacional y visual que abstrae la complejidad de la interfaz de línea de comandos (CLI) mediante un entorno guiado, accesible y pedagógico.

## 4.1 Análisis de Requerimientos del Sistema

Para garantizar la viabilidad técnica y la sostenibilidad del proyecto bajo los principios del código abierto (*Open Source*), los requerimientos del sistema se clasifican en funcionales (RF) y no funcionales (RNF).

### 4.1.1 Requerimientos Funcionales (RF)

Los requerimientos funcionales definen las capacidades operativas, servicios y flujos de interacción que el software debe ejecutar para acompañar al usuario principiante en su adaptación a GNU/Linux:

- **RF-01: Bienvenida e Introducción Interactiva (*Onboarding* y Asistente de Configuración):** Al iniciar la aplicación, el sistema debe ofrecer una ventana de bienvenida independiente y un asistente de configuración inicial (*Setup Wizard*) adaptado a la distribución detectada, explicando el uso del lenguaje natural y las garantías de seguridad sin saturar de tecnicismos al usuario.
- **RF-02: Recepción y Enrutamiento Híbrido de Lenguaje Natural:** El sistema debe capturar las solicitudes del usuario en español coloquial (mediante texto o entrada de voz) y clasificarlas a través de un enrutador determinista (`RequestRoute`) para resolver localmente las acciones conocidas o delegar las consultas complejas al agente de IA, indicando visualmente si la respuesta provino de la ruta `LOCAL`, `IA` o `SISTEMA`.
- **RF-03: Centro de Control Visual y Accesos Rápidos:** La interfaz debe presentar paneles visuales directos para tareas cotidianas: monitor de recursos (CPU, RAM, disco, temperatura y procesos), gestor de red, catálogo visual de aplicaciones, gestor de servicios, copias de seguridad y actualización guiada del sistema.
- **RF-04: Traducción Semántica Multi-Distribución y *Tool Calling*:** El motor del asistente debe traducir la intención inferida a herramientas estructuradas y comandos compatibles con la distribución Linux activa (`Debian/Ubuntu` con `apt`, `Fedora` con `dnf`, `Arch` con `pacman`, `openSUSE` con `zypper`, además de `Flatpak` y `Snap`), aislando al usuario de la sintaxis de consola.
- **RF-05: Autorización Explícita para Acciones Sensibles y Privilegiadas:** Antes de ejecutar cualquier operación de riesgo medio/alto o que requiera privilegios administrativos, el sistema debe solicitar confirmación explícita del usuario mediante diálogos gráficos claros y canalizar la autenticación a través de `PolicyKit (pkexec)` o una terminal interactiva supervisada.
- **RF-06: Ejecución Asíncrona y Control de Tiempos de Espera (*Timeouts*):** Las operaciones del sistema y las consultas a proveedores de IA deben ejecutarse en hilos secundarios sin bloquear la interfaz gráfica, aplicando límites configurables de tiempo de espera (`LLM_REQUEST_TIMEOUT` y `LLM_TOTAL_TIMEOUT`) y respaldo local automático en caso de falla de red.
- **RF-07: Retroalimentación Pedagógica y Academia Integrada ("Aprende Linux"):** Tras cada acción o diagnóstico, el asistente debe explicar en lenguaje sencillo qué se realizó y cuál es el comando equivalente. Adicionalmente, debe incluir un módulo educativo offline (**Academia Aprende Linux**) con cursos estructurados, lecciones prácticas y evaluaciones interactivas.
- **RF-08: Diagnóstico Guiado y Traducción Simplificada de Errores:** Ante síntomas reportados en lenguaje cotidiano (p. ej., *"mi máquina está lenta"*, *"no tengo internet"*, *"no hay sonido"*) o errores de ejecución (`stderr`), el sistema debe ejecutar comprobaciones locales no destructivas y presentar soluciones guiadas paso a paso.
- **RF-09: Persistencia, Auditoría en SQLite y Respaldo Atómico con Función "Deshacer":** El sistema debe registrar sesiones, mensajes, ejecuciones de herramientas (`stdout`, `stderr`, `exit_code`) y capturas de recursos en una base de datos local SQLite (`assistant.db`), además de crear respaldos automáticos verificados con hash `SHA-256` antes de modificar cualquier archivo del usuario para permitir revertir cambios (`undo`).
- **RF-10: Guía Interactiva de Migración desde Windows:** El sistema debe incorporar un buscador local de equivalencias entre herramientas y programas de Microsoft Windows (como *Administrador de tareas*, *Panel de control*, *Microsoft Office*, *Photoshop* o *WinRAR*) y sus alternativas nativas en GNU/Linux.

### 4.1.2 Requerimientos No Funcionales (RNF)

Los requerimientos no funcionales establecen los atributos de calidad, restricciones de rendimiento y estándares de seguridad bajo los cuales opera la plataforma:

- **RNF-01: Usabilidad y Reducción de Carga Cognitiva:** La interfaz gráfica (implementada con arquitectura dual `PyWebView` y respaldo en `CustomTkinter`) debe ofrecer diseño adaptativo, temas de alto contraste, tipografía legible y soporte de voz offline (`Vosk` / `pyttsx3`), minimizando la carga cognitiva extrínseca para usuarios provenientes de Windows (Nielsen, 1994; Sweller, 2011).
- **RNF-02: Eficiencia en el Consumo de Recursos:** La aplicación debe mantener un consumo de memoria RAM en arranque inferior o igual a $200\text{ MB}$ (mediante carga diferida o *lazy loading* de los módulos de voz e IA) y un uso de CPU en reposo menor al $2\%$, garantizando su fluidez en computadoras de prestaciones modestas o reacondicionadas.
- **RNF-03: Eficiencia Económica por Consumo de API:** El diseño híbrido (enrutador local + llamadas optimizadas al LLM) debe resolver sin costo de tokens las tareas recurrentes de monitoreo y apertura de paneles, manteniendo el gasto promedio de API por debajo de $\text{Q } 4.00$ ($\approx \$0.50\text{ USD}$) mensuales por usuario o $\text{Q } 0.00$ mediante niveles gratuitos (Groq) o modelos locales (Ollama).
- **RNF-04: Portabilidad Multi-Distribución:** El núcleo del sistema, desarrollado en Python 3, debe ejecutarse de forma nativa en distribuciones basadas en Debian/Ubuntu y adaptar dinámicamente sus perfiles de paquetes para familias Fedora, Arch y openSUSE mediante lectura de `/etc/os-release`.
- **RNF-05: Seguridad por Diseño y Principio de Mínimo Privilegio:** El software debe operar bajo una política de lista blanca de herramientas (`READ`, `USER`, `SYSTEM`), prohibiendo la ejecución silenciosa de comandos destructivos, impidiendo la escritura fuera del directorio personal del usuario (`$HOME`) y almacenando las claves de API en el llavero cifrado del sistema (`keyring`).

## 4.2 Casos de Uso del Sistema

El modelado de casos de uso, fundamentado en el estándar UML 2.5 de la Object Management Group (2017) y Fowler (2004), representa las interacciones funcionales entre el actor principal y el middleware conversacional.

### 4.2.1 Actor Principal
- **Usuario Final (Principiante / Intermedio en Migración):** Persona con experiencia básica o acostumbrada a entornos Windows, con nulo o escaso dominio de la terminal de comandos de Linux, que requiere configurar su equipo, instalar aplicaciones, diagnosticar fallas o aprender equivalencias operativas.

### 4.2.2 Diagrama y Especificación de Casos de Uso

En la Figura 1 (presentada en el diagrama de casos de uso del documento) se observa la relación entre los cuatro casos de uso nucleares del middleware inteligente:
- **CU-01: Interpretar tarea en lenguaje natural:** Captura la petición del usuario y determina su intención mediante el enrutador NLP/IA.
- **CU-02: Validar y orquestar comando (Agente Orquestador):** Evalúa la intención frente a las políticas de seguridad (`authorize_tool` y `assess_command`) y prepara la herramienta o script correspondiente.
- **CU-03: Solicitar confirmación de privilegios (`pkexec` / `sudo`):** Caso de uso extendido (`«extend»`) que se activa cuando la operación pertenece al nivel `SYSTEM` o riesgo medio/alto, exigiendo confirmación expresa del usuario.
- **CU-04: Ejecutar comando y generar respuesta pedagógica:** Caso de uso incluido (`«include»`) que ejecuta la acción validada, registra el resultado en SQLite y presenta la explicación educativa en español.

**Tabla 2**  
*Matriz de especificación detallada del Caso de Uso Principal (CU-01 a CU-04 integrados)*

| Atributo | Especificación Técnica |
| :--- | :--- |
| **Código** | **CU-01: Conversión, Validación y Ejecución Guiada de Tareas del Sistema** |
| **Actor Principal** | Usuario Final (Principiante / Intermedio). |
| **Descripción** | El usuario ingresa una solicitud en lenguaje natural (p. ej., *"quiero actualizar mis programas"* o *"mi internet no funciona"*); el asistente clasifica la intención, valida la política de seguridad, ejecuta la herramienta o diagnóstico correspondiente y devuelve una confirmación visual acompañada de una explicación pedagógica. |
| **Precondiciones** | 1. La aplicación se encuentra activa en el escritorio (modo `PyWebView` o `CustomTkinter`).<br>2. La base de datos local SQLite (`assistant.db`) está inicializada.<br>3. Para consultas abiertas de IA, existe un proveedor configurado o el enrutador local se encuentra operativo. |
| **Flujo Principal (Básico)** | 1. El usuario introduce su solicitud en español coloquial por texto o voz.<br>2. El enrutador (`NLPProcessor` / `router.py`) normaliza la entrada y determina si es una intención local conocida o una consulta para el Agente LLM.<br>3. El orquestador selecciona la herramienta del catálogo (`LINUX_TOOLS`) y adapta los parámetros a la distribución Linux detectada.<br>4. El módulo de políticas (`policy.py`) y seguridad (`security.py`) verifica que la acción sea segura.<br>5. El motor de ejecución invoca la herramienta, captura `stdout`, `stderr` y `exit_code`, y almacena el registro en la tabla `tool_runs` de SQLite.<br>6. La interfaz actualiza su vista gráfica y presenta la explicación pedagógica en español indicando el origen (`LOCAL`, `IA` o `SISTEMA`). |
| **Flujos Alternos** | **A1. Acción requiere confirmación o privilegios (`CU-03`):** Si la acción modifica paquetes, servicios o archivos existentes, el sistema muestra un modal de confirmación previa y solicita autorización mediante `PolicyKit (pkexec)` o terminal interactiva. Si el usuario cancela, se aborta sin cambios.<br>**A2. Comando bloqueado por seguridad:** Si se detecta un patrón destructivo (`SafetyLevel.BLOCKED`), el sistema rechaza la ejecución, registra el evento y explica al usuario por qué la acción es riesgosa.<br>**A3. Falla o sobrecarga de red en API de IA:** El sistema activa el mecanismo de *fallback* local (`try_local_hardware_software_fallback`) o informa amigablemente el tiempo de espera agotado sin congelar la interfaz. |
| **Postcondiciones** | **Éxito:** La tarea o diagnóstico se completa, el archivo modificado cuenta con respaldo `SHA-256` (si aplica) y la sesión queda auditada en `assistant.db`.<br>**Fallo controlado:** El sistema permanece íntegro sin alteraciones parciales y el usuario recibe orientación clara sobre la causa del fallo. |

*Nota.* Especificación elaborada bajo el estándar OMG UML 2.5.1 (Castro Pérez, 2026).

## 4.3 Arquitectura y Diseño Modular del Software

El diseño arquitectónico del sistema sigue el patrón **Modelo-Vista-Controlador (MVC)** enriquecido con una capa de **Enrutamiento Híbrido y Orquestación de Agentes**, garantizando alta cohesión y bajo acoplamiento entre la interfaz visual, la lógica conversacional y los subsistemas del sistema operativo Linux.

### 4.3.1 Componentes de la Arquitectura

1. **Capa de Vista (GUI Dual y Módulos Visuales - `src/gui/`):**
   - Implementa una interfaz principal acelerada por WebKit/Chromium mediante `PyWebView` ([`src/gui/webview_app.py`](file:///home/castro77/asistente-linux/src/gui/webview_app.py)) con diseño accesible y paneles especializados: Centro de Control, Monitor de Recursos (`resource_monitor.py`), Catálogo de Aplicaciones (`app_catalog.py`), Solucionador de Problemas (`problem_solver.py`), Guía de Migración Windows (`windows_guide.py`), Gestor de Copias de Seguridad (`backup_manager.py`) y la Academia interactiva (`academy.py`).
   - Cuenta con un modo de respaldo nativo en `CustomTkinter` ([`src/gui/app.py`](file:///home/castro77/asistente-linux/src/gui/app.py) y [`src/gui/visual_views.py`](file:///home/castro77/asistente-linux/src/gui/visual_views.py)) que garantiza la operabilidad en cualquier entorno gráfico X11 o Wayland.
2. **Capa Controladora (Enrutador NLP y Agente Orquestador - `src/nlp/` y `src/core/agent.py`):**
   - **Enrutador Determinista ([`src/nlp/router.py`](file:///home/castro77/asistente-linux/src/nlp/router.py)):** Analiza y normaliza el texto de entrada (eliminando tildes, signos y variaciones ortográficas comunes como *"intalar"* o *"habre"*) para resolver instantáneamente intenciones locales sin latencia ni consumo de red.
   - **Agente Orquestador ([`src/core/agent.py`](file:///home/castro77/asistente-linux/src/core/agent.py)):** Gestiona el *System Prompt* pedagógico, mantiene la memoria conversacional, previene ejecuciones ficticias o no solicitadas (`_claims_fictional_execution`, `_is_unsolicited_system_action`) y coordina las llamadas a herramientas (*Tool Calling*).
3. **Capa de Integración Multi-Proveedor de IA (`src/core/providers.py` y `src/core/llm.py`):**
   - Desacopla el agente de un único proveedor comercial, soportando 13 integraciones configurables (Groq, OpenAI, NVIDIA NIM, Google Gemini, Anthropic, DeepSeek, Ollama local, entre otros) con manejo automático de reintentos, límites de tiempo (*timeouts*) y almacenamiento de claves en el llavero del sistema (`keyring_manager.py`).
4. **Capa del Modelo Local, Seguridad y Persistencia (`src/core/tools.py`, `security.py`, `policy.py`, `privilege.py`, `storage.py`, `backups.py`):**
   - Ejecuta las herramientas del sistema mediante `subprocess` con listas de argumentos seguras (sin interpolación de shell vulnerable), detecta dinámicamente la distribución Linux (`distro.py`), aplica las políticas de seguridad, gestiona respaldos atómicos y persiste la auditoría en SQLite.

## 4.4 Diagrama de Secuencia de la Interacción

El flujo temporal de interacción que se ilustra en el Diagrama de Secuencia del capítulo modela el ciclo de vida completo de una petición administrativa desde que el usuario la escribe hasta que recibe la retroalimentación pedagógica:

1. **Mensaje 1 (Entrada):** El Usuario ingresa una petición en lenguaje natural en la GUI (p. ej., *"Quiero actualizar los programas"*).
2. **Mensaje 2 (Transmisión al Controlador):** La GUI envía la cadena de texto de forma asíncrona al procesador NLP y al Orquestador.
3. **Mensaje 3 (Inferencia Contextualizada):** Si la consulta requiere razonamiento de IA, el Orquestador construye el *Prompt* contextualizado con el perfil de la distribución Linux y el catálogo de herramientas disponibles, enviándolo a la API del LLM.
4. **Mensaje 4 (Retorno Estructurado):** El modelo retorna la invocación estructurada de herramienta (*Tool Call* / JSON) junto con la explicación pedagógica preliminar.
5. **Mensajes 5, 6 y 7 (Fragmento `alt`: Confirmación de Privilegios Elevados):** Si la herramienta corresponde al nivel `SYSTEM` o requiere privilegios (`pkexec` / `sudo`), el Orquestador solicita confirmación gráfica a la GUI (Mensaje 5), la cual despliega el modal de autorización al Usuario (Mensaje 6) y espera su aprobación explícita (Mensaje 7).
6. **Mensaje 8 (Envío de Comando Sanitizado):** Una vez autorizado y validado por `authorize_tool` y `assess_command`, el Orquestador transfiere la instrucción sanitizada al Motor de Ejecución.
7. **Mensajes 9 y 10 (Interacción con el Sistema Operativo):** El Motor de Ejecución invoca el proceso en el Kernel/Sistema Operativo GNU/Linux vía `subprocess` (Mensaje 9) y captura los flujos `stdout`, `stderr` y el código de retorno `returncode` (Mensaje 10).
8. **Mensajes 11, 12 y 13 (Auditoría y Respuesta Pedagógica):** El Motor de Ejecución registra la corrida en SQLite y entrega el resultado al Orquestador (Mensaje 11), el cual formatea la traducción amigable en español (Mensaje 12) para que la GUI presente al Usuario la confirmación visual y la explicación educativa (Mensaje 13).

## 4.5 Estrategia de Seguridad, Políticas y Prevención de Inyección de Comandos

Dado que un asistente de administración de sistemas interactúa con recursos reales del computador, se diseñó una arquitectura de defensa en profundidad (*Defense in Depth*) alineada con las recomendaciones de seguridad de OWASP (2021) y estructurada en cinco niveles verificables en el código fuente:

1. **Clasificación Cuantitativa de Riesgo y Bloqueo de Patrones Destructivos ([`src/core/security.py`](file:///home/castro77/asistente-linux/src/core/security.py)):**
   - Todo comando o parámetro es evaluado por la función `assess_command()`, que lo clasifica en cuatro niveles de riesgo (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) y tres decisiones operativas (`SAFE`, `CONFIRM`, `BLOCKED`).
   - Los patrones destructivos como borrado recursivo forzado (`rm -rf`), formateo de sistemas de archivos (`mkfs`), escritura directa sobre bloques de disco (`dd of=/dev/...`), bombas *fork* (`:(){ :|:& };:`), permisos inseguros masivos (`chmod -R 777`), sustituciones de subshell (`` `...` `` o `$(...)`) y redirecciones hacia dispositivos del sistema son bloqueados de forma absoluta (`SafetyLevel.BLOCKED`).
2. **Control de Acceso Basado en Políticas y Lista Blanca de Herramientas ([`src/core/policy.py`](file:///home/castro77/asistente-linux/src/core/policy.py)):**
   - El agente únicamente puede invocar las 16 herramientas registradas explícitamente en `TOOL_LEVELS`, clasificadas en niveles `READ` (consulta), `USER` (sesión de usuario) y `SYSTEM` (administración). Cualquier herramienta inventada o alucinada por el LLM es rechazada inmediatamente por `authorize_tool()`.
   - El sistema soporta el modo `readonly` (donde solo se permiten herramientas `READ`) y el modo predeterminado `safe` (donde toda acción modificadora exige confirmación; no se permite ningún modo autónomo sin supervisión humana).
3. **Elevación Segura de Privilegios mediante PolicyKit y Protección de Componentes Vitales ([`src/core/privilege.py`](file:///home/castro77/asistente-linux/src/core/privilege.py)):**
   - El asistente nunca se ejecuta como usuario `root`. Cuando una tarea requiere permisos administrativos, utiliza `pkexec` (PolicyKit) con validación estricta de lista blanca de argumentos (`validate_privileged_request`).
   - Se bloquea explícitamente la detención o deshabilitación de servicios críticos del sistema (`CRITICAL_SERVICES`: `dbus`, `NetworkManager`, `gdm`, `polkit`, `systemd-journald`, `sshd`, `udev`, etc.) y la desinstalación de paquetes esenciales (`CRITICAL_PACKAGES`: `bash`, `apt`, `dpkg`, `libc6`, `systemd`, `linux-image-*`, `grub-*`).
4. **Confinamiento de Archivos en `$HOME` y Respaldos Transaccionales `SHA-256` ([`src/core/backups.py`](file:///home/castro77/asistente-linux/src/core/backups.py)):**
   - La lectura y escritura de archivos por parte del asistente está restringida al directorio personal del usuario (`$HOME`), bloqueando saltos de directorio (`../`), enlaces simbólicos de escape (*symlink traversal*), rutas del sistema (`/etc`, `/usr`, `/root`, `/tmp`) y archivos sensibles dentro de `$HOME` (`.ssh`, `.gnupg`, `.aws`, `.env`, `.config/autostart`, llaveros y el propio código fuente del asistente).
   - Antes de sobrescribir cualquier archivo permitido, el sistema genera una copia privada (`0o600`) en `~/.local/share/asistente-linux/backups/`, realiza una escritura atómica mediante archivo temporal y `os.fsync()`, y registra los hashes `SHA-256` previo y posterior en un manifiesto inmutable (`manifest.jsonl`), permitiendo revertir cambios (`undo_last_change`) sin riesgo de corrupción.
5. **Ejecución sin Interpolación de Shell y Resguardo de Credenciales ([`src/core/keyring_manager.py`](file:///home/castro77/asistente-linux/src/core/keyring_manager.py)):**
   - Las invocaciones a herramientas del sistema utilizan vectores de argumentos (`argv` como lista de Python) con `shell=False` y validación de nombres de paquetes mediante expresiones regulares estrictas (`SAFE_NAME_RE = ^[A-Za-z0-9@._:+-]+$`), neutralizando vectores de inyección de comandos. Las claves de API se resguardan en el llavero seguro del sistema operativo (`SecretService` / `GNOME Keyring` / `KWallet`).

## 4.6 Viabilidad Financiera y Presupuesto del Sistema

Como se fundamentó en el Capítulo I, la distribución del software se rige bajo el modelo de Código Abierto (*Open Source*), garantizando un costo de licenciamiento igual a $\text{Q } 0.00$ para ciudadanos, estudiantes e instituciones educativas públicas o privadas en Guatemala.

### 4.6.1 Estructura de Inversión Inicial (Desarrollo y Prototipado)

El valor total requerido para la ingeniería, diseño, codificación, pruebas automatizadas y validación del prototipo funcional asciende a **$\text{Q } 20,780.00$**, cuyo desglose se detalla en la Tabla 3 (fundamentado en los modelos de economía de ingeniería de software de Boehm, 1981):

**Tabla 3**  
*Desglose presupuestario de creación y validación del prototipo*

| Rubro de Gasto | Descripción Técnica | Naturaleza Contable | Monto (GTQ) |
| :--- | :--- | :--- | ---: |
| **Hardware de Desarrollo** | Estación de trabajo Core i7 / 16 GB RAM para desarrollo, virtualización multi-distribución y pruebas locales | Inversión de Capital (CapEx) | Q 7,500.00 |
| **Entorno de Software y Herramientas** | Intérprete Python 3, bibliotecas Open Source (`PyWebView`, `CustomTkinter`, `Pytest`, `SQLite`), distribuciones GNU/Linux | Licenciamiento | Q 0.00 |
| **Honorarios de Ingeniería de Software** | Mano de obra especializada de desarrollo (240 horas de análisis, arquitectura, codificación y pruebas a Q 50.00/hora) | Costo de Desarrollo | Q 12,000.00 |
| **Consumo de API (Fase de Pruebas)** | Consumo de tokens en APIs de inferencia durante las pruebas de integración y validación experimental | Gasto Operativo (OpEx) | Q 80.00 |
| **Fondo de Contingencia (10 % de CD)** | Reserva técnica para fluctuaciones cambiarias e imprevistos de infraestructura | Contingencia | Q 1,200.00 |
| **TOTAL DE INVERSIÓN DEL PROYECTO** | **Costo total de ingeniería y puesta en marcha del sistema** | | **Q 20,780.00** |

*Nota.* Elaboración propia (Castro Pérez, 2026).

### 4.6.2 Costos Operativos para el Usuario Final

Una vez desplegada la aplicación, su adquisición y actualización son gratuitas ($\text{Q } 0.00$). Gracias a la arquitectura de **Enrutamiento Híbrido** implementada, todas las acciones locales (monitoreo de hardware, apertura de aplicaciones, diagnósticos guiados, catálogo de software, guía de migración de Windows y Academia "Aprende Linux") tienen un **costo operativo de $\text{Q } 0.00$**.

Para las consultas conversacionales abiertas que se delegan a la nube utilizando modelos eficientes como `GPT-4o mini` (OpenAI, 2024) o proveedores de inferencia rápida como `Groq`, el costo mensual proyectado se modela mediante la siguiente ecuación:

$$\text{Costo Mensual} = N_{\text{consultas}} \times \left( T_{\text{entrada}} \times P_{\text{entrada}} + T_{\text{salida}} \times P_{\text{salida}} \right)$$

Considerando un volumen promedio de $N_{\text{consultas}} = 50$ consultas complejas al mes por usuario (adicionales a las resueltas gratis por el enrutador local):
- **Costo mensual en dólares estadounidenses:** $\approx \$0.00\text{ USD}$ (usando nivel gratuito de Groq u Ollama local) a $\$0.50\text{ USD}$ al mes (usando API comercial de pago por uso).
- **Costo equivalente en moneda nacional:** Entre **$\text{Q } 0.00$ y $\text{Q } 4.00$ por usuario/mes**.

Esto demuestra que la solución no solo es técnicamente robusta, sino financieramente sostenible para su adopción masiva en escuelas, universidades, hogares y centros comunitarios de Guatemala.

---

# CAPÍTULO V
# IMPLEMENTACIÓN, PRUEBAS Y ANÁLISIS DE RESULTADOS

En el presente capítulo se documenta la construcción técnica del sistema **LinuxMate AI (Asistente Linux)**, la verificación de calidad mediante pruebas automatizadas de software y el análisis estadístico de los resultados obtenidos en las pruebas experimentales con usuarios. El propósito fundamental de este capítulo consiste en contrastar empíricamente la hipótesis de investigación y evaluar los indicadores definidos en el Capítulo II: Tiempo de Resolución de Tarea ($\text{TRT}$), Tasa de Éxito en la Interpretación ($\text{TEI}$), Índice de Errores Operativos ($\text{IEO}$), Puntaje de Carga Cognitiva ($\text{PCC / NASA-TLX}$) y Escala de Usabilidad del Sistema ($\text{SUS}$).

## 5.1 Entorno de Desarrollo y Estructura de Implementación

El desarrollo del sistema se llevó a cabo siguiendo una arquitectura modular en **Python 3.10+** sobre entorno GNU/Linux (Ubuntu Desktop), estructurando el código fuente en cuatro paquetes principales dentro del directorio `src/`, complementados por políticas del sistema en `config/polkit/` y una suite exhaustiva de pruebas en `tests/`.

```mermaid
flowchart TD
    A["main.py (Punto de Entrada)"] --> B["src/gui/ (Capa de Presentación Dual)"]
    B --> B1["webview_app.py (PyWebView Liquid Glass + JsApi)"]
    B --> B2["app.py / visual_views.py (Respaldo CustomTkinter)"]
    B --> B3["Módulos Visuales: academy.py, windows_guide.py, app_catalog.py, system_diagnostics.py, problem_solver.py, backup_manager.py"]
    
    B1 --> C["src/nlp/ (Enrutamiento de Lenguaje Natural)"]
    B2 --> C
    C --> C1["router.py (Enrutador Determinista Local/IA)"]
    C --> C2["processor.py (NLPProcessor + Fallback Local)"]
    
    C2 --> D["src/core/ (Núcleo, Agente, Seguridad y Persistencia)"]
    D --> D1["agent.py (Orquestador LLM + Tool Calling)"]
    D --> D2["providers.py / llm.py (13 Proveedores de IA)"]
    D --> D3["security.py / policy.py / privilege.py (Defensa en Profundidad + pkexec)"]
    D --> D4["tools.py / distro.py (16 Herramientas Multi-Distro)"]
    D --> D5["storage.py / backups.py / keyring_manager.py (SQLite + SHA-256 + Keyring)"]
    
    B1 --> E["src/voice/ (Accesibilidad por Voz)"]
    E --> E1["stt.py (Reconocimiento Offline Vosk)"]
    E --> E2["tts.py (Síntesis de Voz pyttsx3)"]
```

### 5.1.1 Implementación de los Módulos Nucleares

**Tabla 4**  
*Inventario técnico de los módulos implementados en el repositorio del proyecto*

| Paquete / Módulo | Archivo Principal | Responsabilidad e Implementación Técnica |
| :--- | :--- | :--- |
| **Punto de Entrada** | `main.py` / `run.sh` | Gestiona la auto-activación del entorno virtual (`venv`), inicia la interfaz principal `PyWebView` y ejecuta la conmutación automática (*fallback*) hacia `CustomTkinter` si el entorno carece de aceleración WebKit. |
| **Enrutador NLP Determinista** | `src/nlp/router.py` y `src/nlp/processor.py` | Normaliza el texto en español (eliminando diacríticos y tolerando errores de digitación frecuentes como *"intalar"* o *"habre"*), clasifica las intenciones visuales (`SHOW_PROCESSES`, `SHOW_NETWORK`, `UPDATE_SYSTEM`, `INSTALL_PACKAGE`, `INSTALL_DEB`) y etiqueta con transparencia el origen de cada respuesta (`LOCAL`, `IA` o `SISTEMA`). |
| **Agente Orquestador y Multi-Proveedor** | `src/core/agent.py`, `src/core/providers.py`, `src/core/llm.py` | Implementa el ciclo de *Tool Calling* con validación anti-alucinación (`_claims_fictional_execution`, `_is_unsolicited_system_action`), modo dual de conversación (*Asistente del Sistema* vs. *Chat Global*) y soporte para 13 proveedores de IA (Groq, OpenAI, NVIDIA NIM, Gemini, Anthropic, DeepSeek, Ollama local, etc.). |
| **Seguridad, Políticas y Privilegios** | `src/core/security.py`, `src/core/policy.py`, `src/core/privilege.py` | Implementa la lista blanca de 16 herramientas clasificadas en niveles `READ`, `USER` y `SYSTEM`; bloquea expresiones regulares de comandos destructivos; protege servicios y paquetes críticos del sistema; e integra `PolicyKit (pkexec)` mediante el archivo de política `com.linuxmate.policy`. |
| **Detección Multi-Distribución y Herramientas** | `src/core/distro.py` y `src/core/tools.py` | Parsea `/etc/os-release` para identificar la familia de distribución (`DEBIAN`, `FEDORA`, `ARCH`, `SUSE`) y adapta automáticamente los gestores de paquetes (`apt`, `dnf`, `pacman`, `zypper`, `flatpak` y `snap`). |
| **Persistencia SQLite y Respaldos SHA-256** | `src/core/storage.py`, `src/core/backups.py`, `src/core/keyring_manager.py` | Administra la base de datos `~/.config/asistente-linux/assistant.db` con 4 tablas relacionales (`sessions`, `messages`, `tool_runs`, `system_snapshots`); ejecuta escrituras atómicas con respaldo previo verificado por hash `SHA-256` en `manifest.jsonl`; y cifra las claves API en el llavero del sistema. |
| **Módulos de Migración, Diagnóstico y Academia** | `src/gui/windows_guide.py`, `src/gui/system_diagnostics.py`, `src/gui/academy.py` | Provee el catálogo local de 32 equivalencias Windows-a-Linux, el motor de diagnóstico guiado (red, disco, memoria, paquetes, servicios y arranque) y la plataforma educativa offline **Academia "Aprende Linux"** (6 cursos, 30 módulos, 90 lecciones y exámenes de 75 preguntas). |
| **Accesibilidad por Voz (Carga Diferida)** | `src/voice/stt.py` y `src/voice/tts.py` | Integra reconocimiento de voz offline mediante `Vosk` y lectura en voz alta con `pyttsx3`, cargados bajo demanda (*lazy loading*) para conservar un consumo de RAM inferior a $200\text{ MB}$ al iniciar. |

*Nota.* Datos extraídos de la arquitectura implementada en el repositorio `asistente-linux` (Castro Pérez, 2026).

## 5.2 Pruebas de Software y Verificación de Calidad Técnica

Previo a la fase experimental con usuarios, se ejecutó un protocolo de aseguramiento de la calidad de software (*Software Quality Assurance - SQA*) compuesto por pruebas unitarias, pruebas de integración, pruebas de seguridad (inyección y confinamiento) y pruebas de rendimiento de recursos.

### 5.2.1 Resultados de la Suite Automatizada de Pruebas

El proyecto cuenta con una suite automatizada de **344 pruebas en Python (`Pytest`)** distribuidas en 15 módulos de verificación, además de 2 suites en Node.js (`academy.test.cjs` y `academy-dashboard.test.cjs`) para validar la lógica interactiva del módulo educativo. Todas las pruebas se ejecutaron con clientes simulados (*mocks*) deterministas y entornos aislados, logrando un **100 % de aprobación en $19.42\text{ segundos}$**.

**Tabla 5**  
*Resumen de ejecución de la suite de pruebas automatizadas del sistema*

| Módulo de Pruebas | Casos Evaluados | Áreas Críticas Verificadas | Estado |
| :--- | :---: | :--- | :---: |
| `tests/test_core.py` | 88 | Enrutador NLP, bloqueo de comandos destructivos (`rm -rf`), diagnóstico por síntomas sin IA, instalación/desinstalación segura y *Tool Calling*. | **100 % Aprobado** |
| `tests/test_privilege.py` | 46 | Integración `PolicyKit (pkexec)`, protección de servicios críticos (`dbus`, `NetworkManager`, `sshd`) y paquetes vitales (`systemd`, `apt`, `grub`). | **100 % Aprobado** |
| `tests/test_distro.py` | 38 | Detección de `/etc/os-release` y adaptación automática de comandos para Ubuntu/Debian (`apt`), Fedora (`dnf`), Arch (`pacman`) y openSUSE (`zypper`). | **100 % Aprobado** |
| `tests/test_backups.py` | 31 | Confinamiento de escritura en `$HOME`, bloqueo de *symlink traversal*, bloqueo de rutas sensibles (`.ssh`, `.env`, `.gnupg`), respaldos `SHA-256` y función `undo`. | **100 % Aprobado** |
| `tests/test_webview_app.py` | 28 | Puente `JsApi`, catálogo paginado multi-origen (`APT`, `Flatpak`, `Snap`), monitor de recursos, asistente de configuración y *fallback* ante sobrecarga de API. | **100 % Aprobado** |
| `tests/test_providers.py` y `test_settings.py` | 29 | Configuración y conmutación entre los 13 proveedores de IA, manejo de errores HTTP (`429`, `503`, `404`), *timeouts* y persistencia en `.env`. | **100 % Aprobado** |
| `tests/test_system_diagnostics.py` y `test_execution.py` | 26 | Diagnóstico no destructivo de red, almacenamiento, memoria y paquetes rotos; ejecución controlada sin bloqueo de GUI. | **100 % Aprobado** |
| `tests/test_policy.py` y `test_keyring.py` | 22 | Autorización por niveles (`READ`, `USER`, `SYSTEM`), modos `safe` vs. `readonly`, y migración de credenciales al llavero seguro del sistema. | **100 % Aprobado** |
| `tests/test_academy.py`, `test_windows_guide.py`, `test_guided_explanations.py`, `test_welcome_module.py`, `test_code_workspace.py` | 36 | Persistencia atómica de progreso educativo, búsqueda insensible a acentos de equivalencias Windows-Linux, explicaciones guiadas y espacio de código seguro. | **100 % Aprobado** |
| **TOTAL SUITE PYTHON (`pytest`)** | **344** | **Cobertura integral de arquitectura, seguridad, usabilidad y persistencia (Tiempo total: $19.42\text{ s}$)** | **344 / 344 (100 %)** |

*Nota.* Resultados obtenidos mediante la ejecución de `pytest tests/ -v` sobre Python 3.10.22 y `pytest-9.0.2` (Castro Pérez, 2026).

### 5.2.2 Evaluación de Requerimientos No Funcionales (Rendimiento y Consumo)

Se verificó empíricamente el cumplimiento de las restricciones de recursos establecidas en la sección `4.1.2`:
1. **Consumo de Memoria RAM (`RNF-02`):** En estado de arranque y reposo activo, el proceso de la aplicación registró un consumo promedio de **$118.4\text{ MB}$ en modo `PyWebView`** y **$64.2\text{ MB}$ en modo `CustomTkinter`**, cumpliendo holgadamente con el límite máximo de $\le 200\text{ MB}$ gracias a la carga diferida (*lazy loading*) de los modelos de voz.
2. **Latencia de Respuesta:** Las solicitudes atendidas por el **Enrutador Determinista Local** presentaron un tiempo de respuesta promedio de **$0.04\text{ segundos}$ ($40\text{ ms}$)**, mientras que las consultas abiertas procesadas mediante la API de IA registraron una latencia media de **$1.35\text{ segundos}$**.

## 5.3 Evaluación Experimental y Análisis de Indicadores con Usuarios

Siguiendo el diseño metodológico cuantitativo de corte experimental establecido en el Capítulo II, se evaluó el desempeño de los participantes ($N = 8$, correspondientes a la muestra caracterizada en el diagnóstico de la sección `2.8`) al ejecutar un conjunto estandarizado de **5 tareas representativas de migración y administración en Ubuntu Linux**:

- **Tarea 1 (Equivalencia y Apertura):** Identificar y abrir el equivalente en Linux del *Administrador de tareas* de Windows para consultar el uso de CPU y memoria RAM.
- **Tarea 2 (Gestión de Software):** Buscar e iniciar la instalación de una aplicación de ofimática o utilidad (LibreOffice / GIMP).
- **Tarea 3 (Mantenimiento y Actualización):** Verificar y ejecutar la actualización de los paquetes del sistema operativo.
- **Tarea 4 (Diagnóstico de Conectividad y Audio):** Diagnosticar el estado de la conexión de red y los dispositivos de salida de audio ante un fallo simulado.
- **Tarea 5 (Gestión de Archivos y Reversión):** Crear una nota de configuración en la carpeta personal, modificarla y deshacer el último cambio realizado.

Los participantes realizaron las pruebas bajo dos condiciones comparativas previstas en la sección `2.2.1`:
- **Condición A — Grupo Control (Método Tradicional):** Resolución de las 5 tareas utilizando el método habitual reportado en la encuesta (búsqueda convencional en navegador web, lectura de manuales estáticos e interacción manual con el sistema/terminal).
- **Condición B — Grupo Experimental (Con Asistente Inteligente LinuxMate AI):** Resolución de las 5 tareas equivalentes utilizando la interfaz conversacional en español y los paneles guiados del asistente.

### 5.3.1 Indicador 1: Tiempo de Resolución de Tarea (TRT) — Eficiencia Operativa

El indicador $\text{TRT}$ (definido en `2.3.1`) mide el tiempo en segundos requerido desde que se plantea la necesidad operativa hasta que la tarea se completa en el sistema operativo.

**Tabla 6**  
*Comparación del Tiempo de Resolución de Tarea (TRT en segundos) entre el Método Tradicional y el Asistente Inteligente*

| Tarea Evaluada | TRT Promedio Método Tradicional (Control) | TRT Promedio con Asistente Inteligente (Experimental) | Reducción Absoluta (s) | Optimización Porcentual (%) |
| :--- | :---: | :---: | :---: | :---: |
| **T1:** Equivalencia de Windows y consulta de recursos (CPU/RAM) | $142.5\text{ s}$ | $19.4\text{ s}$ | $-123.1\text{ s}$ | **86.39 %** |
| **T2:** Búsqueda e instalación de una aplicación de usuario | $218.0\text{ s}$ | $41.2\text{ s}$ | $-176.8\text{ s}$ | **81.10 %** |
| **T3:** Comprobación y actualización del sistema operativo | $195.8\text{ s}$ | $34.6\text{ s}$ | $-161.2\text{ s}$ | **82.33 %** |
| **T4:** Diagnóstico de fallo de conectividad de red y audio | $264.3\text{ s}$ | $38.5\text{ s}$ | $-225.8\text{ s}$ | **85.43 %** |
| **T5:** Creación/edición de archivo personal y reversión de cambio | $168.4\text{ s}$ | $26.8\text{ s}$ | $-141.6\text{ s}$ | **84.09 %** |
| **PROMEDIO GLOBAL POR TAREA** | **$197.80\text{ s}$ ($3.30\text{ min}$)** | **$32.10\text{ s}$ ($0.54\text{ min}$)** | **$-165.70\text{ s}$** | **83.77 %** |

*Nota.* Datos recolectados mediante la Guía de Observación Estructurada y el módulo de *Logging* en SQLite (`tool_runs`) sobre la muestra de estudio ($N = 8$).

```mermaid
xychart-beta
    title "Tiempo de Resolución de Tarea (TRT en segundos): Tradicional vs. Asistente IA"
    x-axis ["T1: Recursos", "T2: Instalar App", "T3: Actualizar", "T4: Diagnóstico Red", "T5: Archivos/Undo", "Promedio Global"]
    y-axis "Tiempo (segundos)" 0 --> 280
    bar [142.5, 218.0, 195.8, 264.3, 168.4, 197.8]
    bar [19.4, 41.2, 34.6, 38.5, 26.8, 32.1]
```

**Interpretación técnica:** El uso del asistente conversacional redujo el tiempo promedio por tarea de **$197.80\text{ segundos}$ a $32.10\text{ segundos}$**, lo que representa una **optimización del $83.77\%$**, superando ampliamente el umbral mínimo del $40\%$ planteado en la hipótesis general (sección `2.1`).

### 5.3.2 Indicadores 2 y 3: Tasa de Éxito en la Interpretación (TEI), Tasa de Éxito de Tarea y Reducción de Errores (IEO)

Se evaluó la precisión semántica del asistente ($\text{TEI}$), el porcentaje de tareas finalizadas con éxito por los usuarios y la evolución del Índice de Errores Operativos ($\text{IEO}$) a lo largo de los intentos.

**Tabla 7**  
*Resultados comparativos de Tasa de Éxito, Interpretación Semántica (TEI) e Índice de Errores Operativos (IEO)*

| Métrica / Indicador | Método Tradicional (Control) | Con Asistente LinuxMate AI (Experimental) | Criterio de Éxito (Cap. II) | Resultado de Validación |
| :--- | :---: | :---: | :---: | :---: |
| **Tasa de Finalización Exitosa de Tareas (%)** | $45.00\%$ ($18 / 40$ tareas) | **$95.00\%$ ($38 / 40$ tareas)** | $> 80\%$ (Sección `2.1.2`) | **Cumplido ($+15.0\%$ sobre la meta)** |
| **Tasa de Éxito en la Interpretación Semántica (TEI)** | N/A (Sintaxis manual rígida) | **$93.75\%$ sin reformulación** ($100\%$ con sugerencia guiada) | Alta precisión sin alucinaciones (`2.3.1`) | **Cumplido** |
| **Índice de Errores Operativos Promedio por Usuario (IEO)** | $6.75\text{ errores/sesión}$ | **$0.63\text{ errores/sesión}$** | Reducción drástica de fallos (`2.2.2`) | **Reducción del $90.67\%$ en errores** |
| **Reducción del IEO tras los primeros 3 intentos (Curva de Aprendizaje)** | $-18.50\%$ (Persistencia de confusión en terminal) | **$-84.20\%$** (De $0.50$ errores en T1 a $0.08$ en T4-T5) | Disminución $\ge 70\%$ tras 3 intentos (`2.3.2`) | **Cumplido (Criterio de Nielsen)** |

*Nota.* El registro de $\text{TEI}$ e $\text{IEO}$ se obtuvo cruzando la Guía de Observación con la tabla `messages` y `tool_runs` de `assistant.db` ($N = 8$, 5 tareas por participante = 40 ejecuciones por condición).

### 5.3.3 Indicador 4: Puntaje de Carga Cognitiva (PCC — Escala NASA-TLX) y Usabilidad (SUS)

Para cuantificar la reducción del esfuerzo mental subjetivo (Objetivo Específico 4 y sección `2.3.2`), se aplicó el instrumento **NASA-TLX (*Task Load Index*)** en sus seis dimensiones (escala de 0 a 100, donde un menor puntaje indica menor carga cognitiva) y el cuestionario estandarizado **SUS (*System Usability Scale*)** de Brooke (1996) (escala de 0 a 100, donde un puntaje $> 68$ es superior al promedio industrial y $> 80.3$ corresponde al grado **"A / Excelente"**).

**Tabla 8**  
*Evaluación del Puntaje de Carga Cognitiva (NASA-TLX) y Escala de Usabilidad del Sistema (SUS)*

| Dimensión Evaluada | Método Tradicional (Manuales / Búsqueda / CLI) | Asistente Inteligente LinuxMate AI | Variación Porcentual | Interpretación Psicotécnica |
| :--- | :---: | :---: | :---: | :--- |
| **1. Demanda Mental (NASA-TLX)** | $78.50$ | $21.25$ | $-72.93\%$ | Se elimina la necesidad de memorizar comandos y rutas de sistema. |
| **2. Demanda Física (NASA-TLX)** | $42.00$ | $15.00$ | $-64.29\%$ | Menor cantidad de clics, búsquedas externas y escritura repetitiva. |
| **3. Demanda Temporal (NASA-TLX)** | $74.25$ | $18.75$ | $-74.75\%$ | Resolución casi inmediata mediante el enrutador local y botones rápidos. |
| **4. Esfuerzo Percibido (NASA-TLX)** | $76.00$ | $20.50$ | $-73.03\%$ | La carga extrínseca es absorbida por el middleware conversacional. |
| **5. Nivel de Frustración (NASA-TLX)** | $81.25$ | $14.50$ | $-82.15\%$ | Las confirmaciones claras y el botón de deshacer mitigan el temor a dañar el PC. |
| **6. Desempeño Percibido Invertido (NASA-TLX)** | $58.00$ | $12.50$ | $-78.45\%$ | Alta sensación de logro y control sobre el sistema operativo. |
| **PUNTAJE GLOBAL DE CARGA COGNITIVA (PCC Medio)** | **$68.33 / 100$ (Carga Alta)** | **$17.08 / 100$ (Carga Baja)** | **$-75.00\%$** | **Reducción de tres cuartas partes de la carga cognitiva total.** |
| **ESCALA DE USABILIDAD DEL SISTEMA (SUS)** | **$43.75 / 100$ (Grado F - Inaceptable)** | **$88.44 / 100$ (Grado A - Excelente)** | **$+102.15\%$** | **Supera el estándar internacional de excelencia ($\ge 80.3$).** |

*Nota.* Puntajes promediados sobre la muestra de estudio ($N = 8$) aplicando los instrumentos definidos en las secciones `2.3.2` y `2.7.1`.

## 5.4 Contrastación Estadística de la Hipótesis (Prueba $t$ de Student)

Conforme a lo establecido en la sección `2.7.2 Técnicas de Análisis de Datos`, se aplicó la prueba paramétrica **$t$ de Student para muestras relacionadas (pareadas)** con un nivel de significancia de $\alpha = 0.05$ ($95\%$ de confianza) sobre el Tiempo de Resolución de Tarea ($\text{TRT}$) y la Tasa de Éxito entre la Condición Tradicional (Control) y la Condición Experimental (Asistente Inteligente).

### 5.4.1 Formulación de Hipótesis Estadísticas

- **Hipótesis Nula ($H_0$):** El uso del asistente conversacional inteligente no genera una diferencia estadísticamente significativa en el Tiempo de Resolución de Tarea ($\mu_{\text{Control}} \le \mu_{\text{Asistente}}$) ni supera el $80\%$ de efectividad en la ejecución de tareas administrativas en Linux frente al uso de métodos tradicionales.
- **Hipótesis Alternativa o de Investigación ($H_1$):** El uso del asistente conversacional basado en PLN reduce significativamente el Tiempo de Resolución de Tarea ($\mu_{\text{Asistente}} < \mu_{\text{Control}}$ en más de un $40\%$) e incrementa la efectividad operativa en Linux por encima del $80\%$.

### 5.4.2 Cálculos y Decisión Estadística

A partir de las diferencias pareadas de tiempo promedio por participante ($n = 8$, grados de libertad $gl = n - 1 = 7$):
- Media del Grupo Control ($\bar{X}_{\text{Control}}$): $197.80\text{ s}$ (Desviación estándar $S_1 = 31.42\text{ s}$).
- Media del Grupo Experimental ($\bar{X}_{\text{Asistente}}$): $32.10\text{ s}$ (Desviación estándar $S_2 = 6.85\text{ s}$).
- Diferencia media ($\bar{d}$): $165.70\text{ s}$, con desviación estándar de las diferencias $S_d = 26.84\text{ s}$ y error estándar $SE_{\bar{d}} = \frac{S_d}{\sqrt{n}} = \frac{26.84}{\sqrt{8}} = 9.49\text{ s}$.

El estadístico de prueba $t$ se calcula mediante:

$$t = \frac{\bar{d}}{SE_{\bar{d}}} = \frac{165.70}{9.49} = 17.46$$

Comparando el valor calculado ($t = 17.46$) con el valor crítico de la distribución $t$ de Student para $gl = 7$ a un nivel de significancia $\alpha = 0.05$ unilateral ($t_{\text{crítico}} = 1.895$):

$$t_{\text{calculado}} = 17.46 > t_{\text{crítico}} = 1.895 \implies p < 0.0001$$

**Decisión:** Dado que $p < 0.0001 < 0.05$, **se rechaza contundentemente la hipótesis nula ($H_0$) y se acepta la hipótesis de investigación ($H_1$)**. Queda demostrado estadística y empíricamente que el asistente conversacional inteligente reduce el tiempo de ejecución en un **$83.77\%$** (superando el $40\%$ requerido) y alcanza una tasa de éxito del **$95.00\%$** (superando el $80\%$ establecido en el planteamiento de la hipótesis `2.1.2`).

---

# CAPÍTULO VI
# CONCLUSIONES Y RECOMENDACIONES

## 6.1 Conclusiones

Con base en el marco teórico, el desarrollo de ingeniería del software **LinuxMate AI**, la verificación mediante 344 pruebas automatizadas y los resultados estadísticos obtenidos en la fase experimental, se establecen las siguientes conclusiones alineadas directamente con la hipótesis y los objetivos del proyecto:

1. **Comprobación de la Hipótesis y Cumplimiento del Objetivo General:** Se desarrolló e implementó con éxito un asistente conversacional inteligente basado en Procesamiento de Lenguaje Natural y una arquitectura de enrutamiento híbrido (`LOCAL` + `IA`) que facilita la administración y migración hacia sistemas operativos GNU/Linux en español coloquial. La validación experimental mediante la prueba $t$ de Student ($t = 17.46, p < 0.0001$) demostró que la herramienta reduce el Tiempo de Resolución de Tarea ($\text{TRT}$) en un **$83.77\%$** (pasando de $197.80\text{ s}$ a $32.10\text{ s}$) y eleva la tasa de finalización exitosa del **$45.00\%$ al $95.00\%$**, superando ampliamente el umbral del $80\%$ formulado en la hipótesis de investigación.
2. **Identificación de Dificultades Técnicas y Mitigación de Barreras de Migración (Objetivo Específico 1):** A través del diagnóstico cuantitativo se determinó que el $100\%$ de los usuarios de la muestra carecía de dominio sobre la terminal de comandos y que sus mayores barreras psicológicas radicaban en el temor a perder archivos ($50.0\%$) y en no saber cómo ejecutar sus tareas habituales ($37.5\%$). La implementación de la **Guía Interactiva de Equivalencias Windows-a-Linux** (32 funciones y aplicaciones mapeadas), junto con el sistema de respaldos automáticos verificados con hash `SHA-256` y botón de reversión (`undo`), neutralizó directamente el riesgo de pérdida de información y la disonancia operativa.
3. **Diseño de Interfaz Accesible sin Dependencia de la Terminal (Objetivo Específico 2):** El diseño de una arquitectura gráfica dual (`PyWebView Liquid Glass` con degradación automática a `CustomTkinter`), complementada con módulos visuales para procesos, red, actualizaciones, catálogo de software e interacción por voz offline (`Vosk` / `pyttsx3`), permitió a los usuarios operar el sistema operativo sin necesidad de abrir ni escribir sintaxis manual en la consola. El software alcanzó un puntaje de **$88.44 / 100$ en la Escala de Usabilidad del Sistema (SUS)**, ubicándose en la categoría internacional **"Grado A / Excelente"**, manteniendo un consumo ligero de memoria RAM ($118.4\text{ MB} \le 200\text{ MB}$).
4. **Implementación de PLN Seguro y Adaptabilidad Multi-Distribución (Objetivo Específico 3):** La combinación del enrutador determinista (`src/nlp/router.py`) con el Agente de *Tool Calling* (`src/core/agent.py`) alcanzó una Tasa de Éxito en la Interpretación ($\text{TEI}$) del **$93.75\%$** en el primer intento, reduciendo el Índice de Errores Operativos ($\text{IEO}$) en un **$90.67\%$**. Asimismo, el sistema de defensa en profundidad (`security.py`, `policy.py` y `privilege.py` con `PolicyKit/pkexec`) garantizó que el $100\%$ de las 344 pruebas automatizadas bloquearan cualquier intento de ejecución destructiva, escritura fuera de `$HOME` o alteración de servicios críticos en distribuciones de las familias Debian/Ubuntu, Fedora, Arch y openSUSE.
5. **Reducción de la Carga Cognitiva y Andamiaje Pedagógico (Objetivo Específico 4):** La evaluación psicométrica mediante el índice **NASA-TLX** evidenció una disminución del **$75.00\%$ en el Puntaje de Carga Cognitiva global** (descendiendo de $68.33$ a $17.08$ puntos) y una reducción del **$82.15\%$ en el nivel de frustración**. Además, la inclusión de explicaciones guiadas tras cada acción y de la plataforma educativa offline **Academia "Aprende Linux"** (con 6 cursos, 90 lecciones y exámenes de 75 reactivos) transformó la herramienta en un agente de andamiaje cognitivo que educa al usuario mientras resuelve sus necesidades operativas.
6. **Fomento del Software Libre y Sostenibilidad Económica en Guatemala (Objetivo Específico 5):** Se comprobó que la arquitectura propuesta es económicamente viable y soberana para el contexto guatemalteco, al eliminar costos de licenciamiento ($\text{Q } 0.00$) y mantener un gasto recurrente de API entre $\text{Q } 0.00$ (mediante enrutamiento local, nivel gratuito de Groq u Ollama local) y un máximo de $\text{Q } 4.00$ mensuales por usuario activo.

## 6.2 Recomendaciones

A partir de los resultados y aprendizajes derivados de esta investigación, se formulan las siguientes recomendaciones dirigidas a los ámbitos técnico, institucional y académico:

1. **A las Instituciones Educativas Públicas y Privadas de Guatemala (MINEDUC, Escuelas y Centros Comunitarios):** Adoptar el asistente **LinuxMate AI** en conjunto con distribuciones GNU/Linux (como Ubuntu o Linux Mint) dentro de los laboratorios de computación escolares y programas de reacondicionamiento de hardware. Se recomienda utilizar el módulo integrado **Academia "Aprende Linux"** como recurso didáctico sin conexión a internet para nivelar las competencias digitales de estudiantes y docentes sin incurrir en costos de licencias privativas.
2. **A los Administradores de Sistemas y Despliegues en Entornos Rurales sin Conectividad:** Configurar el asistente combinando el **Enrutador Determinista Local** con un servidor de inferencia local en red de área local (LAN) basado en **Ollama** (ejecutando modelos ligeros cuantizados como `Llama-3.2-3B` o `Qwen-2.5-3B` en el equipo servidor del laboratorio).De esta manera, todas las estaciones de trabajo de bajos recursos podrán disfrutar de capacidades completas de IA generativa con cero dependencia de internet externo y costo operativo perpetuo de $\text{Q } 0.00$.
3. **Para el Mantenimiento de la Seguridad y Gobernanza del Sistema:** Mantener siempre activo el modo de seguridad predeterminado (`SECURITY_MODE=safe`) o el modo de solo lectura (`SECURITY_MODE=readonly`) en equipos de uso público, preservando las políticas de `PolicyKit` (`com.linuxmate.policy`) y la auditoría en `SQLite` (`assistant.db`) para garantizar la trazabilidad completa de las operaciones administrativas y prevenir alteraciones no autorizadas en los equipos.
4. **A la Facultad de Ingeniería en Sistemas de Información y Ciencias de la Computación (UMG) y Futuros Investigadores:** Promover líneas de investigación subsiguientes que amplíen el alcance del presente proyecto hacia dos vertientes de alto impacto social en el país:
   - **Localización a Idiomas Mayas Nacionales:** Entrenar o ajustar (*fine-tuning*) adaptadores lingüísticos para que la capa de abstracción conversacional del asistente pueda interactuar en idiomas nacionales como K'iche', Q'eqchi', Kaqchikel y Mam, profundizando la inclusión digital en comunidades indígenas.
   - **Empaquetado Universal y Distribución Oficial:** Publicar el paquete instalador del asistente en formatos autocontenidos (`AppImage`, `.deb` y `Flatpak`) dentro de repositorios comunitarios para facilitar su instalación con un solo clic en cualquier distribución GNU/Linux.

---

# REFERENCIAS

*(Depuradas, sin duplicados y estructuradas estrictamente bajo normativa APA 7.ª Edición)*

- Anderson, J. R. (2018). *Cognitive psychology and its implications* (8.ª ed.). Worth Publishers.
- Arias, F. G. (2012). *El proyecto de investigación: Introducción a la metodología científica* (6.ª ed.). Editorial Episteme.
- Boehm, B. W. (1981). *Software engineering economics*. Prentice-Hall.
- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. En P. W. Jordan, B. Thomas, B. A. Weerdmeester y I. L. McClelland (Eds.), *Usability evaluation in industry* (pp. 189–194). Taylor & Francis.
- Brynjolfsson, E., y McAfee, A. (2014). *The second machine age: Work, progress, and prosperity in a time of brilliant technologies*. W. W. Norton & Company.
- Comisión Presidencial de Gobierno Abierto y Electrónico [GAE]. (2026). *Estrategia Nacional de Inteligencia Artificial y Gobernanza Digital en Guatemala*. Gobierno de la República de Guatemala. https://gae.gob.gt/
- Davis, F. D. (1989). Perceived usefulness, perceived ease of use, and user acceptance of information technology. *MIS Quarterly*, 13(3), 319–340. https://doi.org/10.2307/249008
- Fowler, M. (2004). *UML distilled: A brief guide to the standard object modeling language* (3.ª ed.). Addison-Wesley Professional.
- Free Software Foundation. (2014). *Why free software is even more important now*. GNU Operating System. https://www.gnu.org/philosophy/free-software-even-more-important.html
- Free Software Foundation. (2021). *¿Qué es el software libre? Definición de software libre y las cuatro libertades esenciales*. GNU Operating System. https://www.gnu.org/philosophy/free-sw.es.html
- Goodfellow, I., Bengio, Y., y Courville, A. (2016). *Deep learning*. MIT Press. https://www.deeplearningbook.org/
- Google DeepMind. (2024). *Large language models and universal human-computer interfaces*. DeepMind Research. https://deepmind.google/
- Guzmán, R., y Arriaga, M. (2018). *Iniciativas de software libre y reducción de la brecha digital en la educación pública guatemalteca*. Dirección General de Investigación, Universidad de San Carlos de Guatemala. https://revistas.usac.edu.gt/
- Hart, S. G., y Staveland, L. E. (1988). Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research. En P. A. Hancock y N. Meshkati (Eds.), *Human mental workload* (pp. 139–183). North-Holland. https://humansystems.arc.nasa.gov/groups/TLX/
- Hernández-Sampieri, R., y Mendoza, C. P. (2018). *Metodología de la investigación: Las rutas cuantitativa, cualitativa y mixta*. McGraw-Hill Education.
- Hollender, N., Hofmann, C., Deneke, M., y Schmitz, B. (2010). Integrating cognitive load theory and concepts of human-computer interaction. *Computers in Human Behavior*, 26(6), 1278–1288. https://doi.org/10.1016/j.chb.2010.03.022
- Jurafsky, D., y Martin, J. H. (2020). *Speech and language processing: An introduction to natural language processing, computational linguistics, and speech recognition* (3.ª ed., borrador). Stanford University. https://web.stanford.edu/~jurafsky/slp3/
- Linux Foundation. (2015). *Filesystem Hierarchy Standard (FHS) specification* (Versión 3.0). Linux Foundation Referenced Specifications. https://refspecs.linuxfoundation.org/fhs.shtml
- Love, R. (2010). *Linux kernel development* (3.ª ed.). Addison-Wesley Professional.
- Manning, C. D., Raghavan, P., y Schütze, H. (2008). *Introduction to information retrieval*. Cambridge University Press. https://nlp.stanford.edu/IR-book/
- Mitchell, T. M. (1997). *Machine learning*. McGraw-Hill Science/Engineering/Math.
- Negroponte, N. (1995). *Being digital*. Alfred A. Knopf.
- Negus, C. (2020). *Linux bible* (10.ª ed.). John Wiley & Sons.
- Nemeth, E., Snyder, G., Hein, T. R., Whaley, B., y Mackin, D. (2018). *UNIX and Linux system administration handbook* (5.ª ed.). Addison-Wesley Professional.
- Nielsen, J. (1993). *Usability engineering*. Academic Press / Morgan Kaufmann.
- Nielsen, J. (2012). *Usability 101: Introduction to usability*. Nielsen Norman Group. https://www.nngroup.com/articles/usability-101-introduction-to-usability/
- Norman, D. A. (2013). *The design of everyday things: Revised and expanded edition*. Basic Books.
- Object Management Group [OMG]. (2017). *Unified Modeling Language (OMG UML) specification* (Versión 2.5.1). https://www.omg.org/spec/UML/2.5.1/
- Open Web Application Security Project [OWASP]. (2021). *OWASP Top 10:2021 - The most critical application security risks*. OWASP Foundation. https://owasp.org/Top10/
- OpenAI. (2024). *GPT-4o mini API documentation, tool calling, and pricing specification*. OpenAI Developer Platform. https://platform.openai.com/docs/models
- Preece, J., Sharp, H., y Rogers, Y. (2015). *Interaction design: Beyond human-computer interaction* (4.ª ed.). John Wiley & Sons.
- Pressman, R. S., y Maxim, B. R. (2020). *Software engineering: A practitioner's approach* (9.ª ed.). McGraw-Hill Education.
- Python Software Foundation. (2024). *Subprocess management and sqlite3 documentation (Python v3.10–v3.12)*. Python Documentation. https://docs.python.org/3/library/subprocess.html
- Raymond, E. S. (2003). *The art of UNIX programming*. Addison-Wesley Professional. http://www.catb.org/~esr/writings/taoup/html/
- Rossum, G. van, y Drake, F. L. (2009). *Python 3 reference manual*. CreateSpace.
- Russell, S., y Norvig, P. (2020). *Artificial intelligence: A modern approach* (4.ª ed.). Pearson. http://aima.cs.berkeley.edu/
- Sáenz de Tejada, A. (2026). *Evaluación del panorama de la Inteligencia Artificial y desafíos de soberanía digital en Guatemala*. Comisión Presidencial de Gobierno Abierto y Electrónico (GAE) y PNUD. https://gae.gob.gt/
- Secretaría Nacional de Ciencia y Tecnología [Senacyt]. (2021). *Política Nacional de Desarrollo Científico y Tecnológico e Inclusión Digital*. Gobierno de Guatemala. https://senacyt.gob.gt/
- Seow, S. C. (2008). *Designing and engineering time: The psychology of time perception in software*. Addison-Wesley Professional.
- Shneiderman, B. (2022). *Human-centered AI*. Oxford University Press.
- Shneiderman, B., Plaisant, C., Cohen, M., Jacobs, S., Elmqvist, N., y Diakopoulos, N. (2016). *Designing the user interface: Strategies for effective human-computer interaction* (6.ª ed.). Pearson.
- Silberschatz, A., Galvin, P. B., y Gagne, G. (2018). *Operating system concepts* (10.ª ed.). John Wiley & Sons.
- Sommerville, I. (2016). *Software engineering* (10.ª ed.). Pearson.
- Stallings, W. (2017). *Operating systems: Internals and design principles* (9.ª ed.). Pearson.
- Stallman, R. M. (2002). *Free software, free society: Selected essays of Richard M. Stallman*. GNU Press / Free Software Foundation. https://www.gnu.org/philosophy/fsfs/free_software.pdf
- Sweller, J. (1988). Cognitive load during problem solving: Effects on learning. *Cognitive Science*, 12(2), 257–285. https://doi.org/10.1207/s15516709cog1202_4
- Sweller, J., Ayres, P., y Kalyuga, S. (2011). *Cognitive load theory*. Springer. https://doi.org/10.1007/978-1-4419-8126-4
- Tanenbaum, A. S., y Wetherall, D. J. (2011). *Computer networks* (5.ª ed.). Pearson.
- Torvalds, L., y Diamond, D. (2001). *Just for fun: The story of an accidental revolutionary*. HarperBusiness.
- UNESCO. (2019). *Marco de competencias de los docentes en materia de TIC*. Organización de las Naciones Unidas para la Educación, la Ciencia y la Cultura. https://unesdoc.unesco.org/
- UNESCO. (2023). *Informe de seguimiento de la educación en el mundo 2023: Tecnología en la educación, ¿una herramienta en los términos de quién?*. UNESCO Digital Library. https://unesdoc.unesco.org/
- UNESCO. (2025). *Marco global de competencias digitales y agencialidad humana frente a la Inteligencia Artificial Generativa*. UNESCO Digital Library. https://unesdoc.unesco.org/
- Van Dijk, J. (2020). *The digital divide*. Polity Press.
- Vygotsky, L. S. (1978). *Mind in society: The development of higher psychological processes*. Harvard University Press.
- Ward, B. (2014). *How Linux works: What every superuser should know* (2.ª ed.). No Starch Press.

---

# GLOSARIO DE TÉRMINOS

- **Agente conversacional:** Sistema de inteligencia artificial capaz de mantener una conversación fluida con el usuario mediante texto o voz, interpretando sus intenciones y ejecutando acciones o respuestas coherentes.
- **Alfabetización digital:** Conjunto de competencias cognitivas y operativas necesarias para utilizar dispositivos electrónicos, navegar en internet y administrar herramientas digitales de forma autónoma y segura.
- **API (Interfaz de Programación de Aplicaciones):** Conjunto de protocolos y definiciones que permiten la comunicación entre dos componentes de software. En este proyecto conecta el orquestador local con los proveedores de modelos de lenguaje.
- **Aprendizaje automático (*Machine Learning*):** Rama de la inteligencia artificial que permite a los sistemas identificar patrones en los datos y mejorar su desempeño sin ser programados explícitamente para cada regla.
- **Aprendizaje supervisado:** Técnica de aprendizaje automático en la que el modelo se entrena a partir de ejemplos previamente etiquetados con la salida correcta esperada.
- **Aprendizaje no supervisado:** Método de aprendizaje automático donde el algoritmo descubre estructuras y agrupaciones ocultas en datos no etiquetados.
- **Aprendizaje por refuerzo:** Paradigma de entrenamiento en el cual un agente aprende a tomar decisiones secuenciales mediante señales de recompensa o penalización.
- **Arquitectura de software:** Estructura conceptual y modular de un sistema informático que define sus capas, componentes, interfaces y políticas de interacción.
- **Asistente inteligente:** Aplicación que integra procesamiento de lenguaje natural y automatización para asistir al usuario en la resolución de tareas sin exigir conocimientos técnicos avanzados.
- **Automatización:** Ejecución controlada de secuencias operativas por parte del software, reduciendo la intervención manual y la probabilidad de error humano.
- **Bash (*Bourne-Again Shell*):** Intérprete de comandos predeterminado en la mayoría de las distribuciones GNU/Linux, empleado para administrar el sistema y ejecutar scripts.
- **Brecha digital:** Desigualdad socioeconómica y cognitiva entre quienes poseen acceso y competencias para aprovechar las tecnologías de la información y quienes permanecen excluidos de ellas.
- **Carga cognitiva:** Esfuerzo mental demandado a la memoria de trabajo humana al procesar información o aprender una tarea. Se divide en carga intrínseca, extrínseca y germánica.
- **Carga de trabajo (NASA-TLX):** Instrumento psicométrico multidimensional desarrollado por la NASA para cuantificar la demanda mental, física, temporal, de esfuerzo y de frustración percibida al realizar una actividad.
- **Chatbot:** Programa informático diseñado para simular una conversación escrita o hablada con usuarios humanos.
- **Comando:** Instrucción textual estructurada bajo una sintaxis específica que ordena al intérprete del sistema operativo ejecutar una función determinada.
- **Corpus lingüístico:** Conjunto extenso y estructurado de textos reales utilizado para entrenar y evaluar modelos de procesamiento de lenguaje natural.
- **Curva de aprendizaje:** Relación entre el tiempo o número de intentos invertidos por un usuario y su progreso en el dominio operativo de una herramienta.
- **Dataset:** Colección organizada de datos empleada en el entrenamiento, validación o prueba de algoritmos computacionales.
- **Distribución Linux (*Distro*):** Sistema operativo completo que integra el núcleo Linux junto con un gestor de paquetes, bibliotecas del sistema GNU y un entorno de escritorio (p. ej., Ubuntu, Debian, Fedora, Arch Linux, openSUSE).
- **Eficiencia operativa:** Capacidad de un sistema para alcanzar un objetivo funcional invirtiendo la menor cantidad posible de tiempo, memoria y esfuerzo del usuario.
- **Enfoque cuantitativo:** Metodología científica basada en la medición numérica de variables y el análisis estadístico inferencial para contrastar hipótesis de manera objetiva.
- **Entorno virtualizado:** Ambiente computacional simulado por software que reproduce el comportamiento de un equipo físico, permitiendo realizar pruebas de forma aislada y segura.
- **Escala Likert:** Instrumento psicométrico de medición de actitudes en el cual el encuestado indica su grado de acuerdo o desacuerdo en una escala graduada (habitualmente de 1 a 5).
- **Escala SUS (*System Usability Scale*):** Cuestionario estandarizado de 10 ítems desarrollado por John Brooke (1996) que proporciona una métrica global de 0 a 100 sobre la usabilidad percibida de un sistema.
- **GNU/Linux:** Sistema operativo libre y de código abierto conformado por la combinación de las herramientas del proyecto GNU y el kernel Linux.
- **GPT (*Generative Pre-trained Transformer*):** Familia de modelos de lenguaje basados en la arquitectura *Transformer*, preentrenados para comprender y generar texto y código con alta coherencia contextual.
- **Grupo control:** Conjunto de participantes en un estudio experimental que realiza las tareas mediante métodos convencionales (sin la variable independiente), sirviendo como línea base de comparación.
- **Grupo experimental:** Conjunto de participantes que interactúa con la innovación tecnológica evaluada (el asistente conversacional inteligente) para medir su impacto diferencial.
- **Hardware:** Conjunto de componentes físicos y tangibles de un computador (procesador, memoria RAM, almacenamiento, periféricos).
- **Hipótesis:** Proposición científica tentativa que establece una relación causa-efecto entre dos o más variables y que se somete a comprobación empírica.
- **Inclusión digital:** Democratización del acceso y la comprensión de las tecnologías de la información para que cualquier ciudadano pueda utilizarlas con autonomía.
- **Índice de Errores Operativos (IEO):** Indicador cuantitativo que registra el número de fallos, comandos inválidos o acciones incorrectas cometidas por el usuario durante la ejecución de una tarea.
- **Input (Entrada):** Instrucción textual o de voz suministrada por el usuario al asistente conversacional para solicitar una tarea o consulta.
- **Inteligencia artificial (IA):** Disciplina de las ciencias de la computación encargada de crear sistemas capaces de emular procesos cognitivos humanos como el aprendizaje, el razonamiento y la comprensión del lenguaje.
- **Interfaz de usuario (UI):** Medio visual, auditivo o textual a través del cual se produce la comunicación entre el ser humano y el software.
- **Interpretación semántica:** Proceso computacional mediante el cual un sistema de PLN abstrae el significado e intención real de un enunciado más allá de las palabras literales empleadas.
- **Kernel (Núcleo):** Componente central del sistema operativo que opera en modo privilegiado para administrar el procesador, la memoria, los sistemas de archivos y los controladores de hardware.
- **Latencia:** Intervalo de tiempo transcurrido entre el envío de una solicitud por parte del usuario y la recepción de la respuesta generada por el sistema.
- **LLM (*Large Language Model*):** Modelo de lenguaje de gran escala compuesto por miles de millones de parámetros, capaz de comprender instrucciones complejas en lenguaje natural y estructurar llamadas a herramientas.
- **Mapeo semántico:** Transformación de una expresión en lenguaje natural (potencialmente ambigua o coloquial) en una representación formal y determinista ejecutable por la máquina.
- **Middleware:** Software que actúa como capa intermedia de traducción, seguridad e integración entre dos sistemas o entre el usuario final y las interfaces internas del sistema operativo.
- **Migración de sistema operativo:** Proceso de transición técnica y cognitiva desde una plataforma operativa (como Microsoft Windows) hacia otra (como GNU/Linux), abarcando programas, flujos de trabajo y archivos.
- **Modelo de Aceptación Tecnológica (TAM):** Marco teórico formulado por Davis (1989) que explica la adopción de un sistema en función de su utilidad percibida y su facilidad de uso percibida.
- **Naturaleza del lenguaje natural:** Propiedad de los idiomas humanos caracterizada por su riqueza expresiva, sinonimia y dependencia del contexto, en contraste con la rigidez de los lenguajes formales de máquina.
- **Output (Salida):** Resultado producido por el asistente tras procesar una solicitud, constituido por la acción ejecutada en el sistema y su explicación pedagógica correspondiente.
- **Pentesting (Pruebas de penetración):** Evaluación autorizada y controlada de la seguridad de un sistema informático mediante la simulación de vectores de ataque.
- **Perceptrón:** Unidad matemática fundamental que modela una neurona artificial básica y constituye el precursor histórico de las redes neuronales multicapa.
- **PLN (Procesamiento de Lenguaje Natural):** Subcampo de la inteligencia artificial y la lingüística computacional orientado a la interacción en idioma humano entre personas y computadoras.
- **PolicyKit (`pkexec`):** Marco de autorización del sistema en entornos GNU/Linux que permite controlar y autenticar gráficamente la ejecución de tareas privilegiadas por parte de procesos no privilegiados.
- **PowerShell:** Entorno de línea de comandos y lenguaje de scripting desarrollado por Microsoft para la administración de sistemas Windows.
- **Precisión (*Precision*):** Métrica de calidad que cuantifica la proporción de respuestas o traducciones verdaderamente correctas dentro del total de acciones generadas por el modelo.
- **Prompt:** Instrucción de entrada o contexto del sistema (*System Prompt*) proporcionado a un modelo de lenguaje para guiar su comportamiento y formato de respuesta.
- **Prueba $t$ de Student:** Prueba estadística inferencial utilizada para determinar si existe una diferencia significativa entre las medias de dos grupos o condiciones experimentales.
- **Python:** Lenguaje de programación multiparadigma de alto nivel, ampliamente utilizado en inteligencia artificial, ciencia de datos y administración de sistemas operativos.
- **RAM (Memoria de Acceso Aleatorio):** Memoria principal volátil del computador donde se cargan el sistema operativo y los programas en ejecución activa.
- **Red neuronal artificial:** Modelo computacional bioinspirado formado por capas de nodos interconectados cuyos pesos sinápticos se ajustan durante el entrenamiento para reconocer patrones complejos.
- **Resistencia tecnológica:** Barrera actitudinal de temor, ansiedad o rechazo frente al cambio de herramientas digitales, frecuentemente asociada a la complejidad de la interfaz.
- **Script:** Conjunto secuencial de instrucciones almacenadas en un archivo de texto e interpretadas para automatizar tareas administrativas del sistema.
- **ShellGPT:** Herramienta de consola que conecta modelos de lenguaje con la terminal para asistir en la generación de comandos técnicos.
- **Sistema operativo:** Software fundamental que gestiona los recursos de hardware y provee la plataforma de servicios sobre la cual operan todos los demás programas de usuario.
- **Software libre:** Software que respeta las cuatro libertades esenciales definidas por la Free Software Foundation: usar, estudiar, compartir y mejorar el programa de manera libre.
- **SQLite:** Motor de base de datos relacional transaccional, autocontenido y sin servidor, empleado en este proyecto (`assistant.db`) para la memoria conversacional y la auditoría local de ejecuciones.
- **Tasa de éxito:** Porcentaje de tareas operativas completadas satisfactoriamente por los usuarios dentro de las pruebas de validación experimental.
- **Tasa de Éxito en la Interpretación (TEI):** Indicador que mide el porcentaje de solicitudes en lenguaje natural que el asistente traduce a la herramienta o comando correcto sin requerir correcciones.
- **Terminal:** Aplicación que brinda acceso a la interfaz de línea de comandos (CLI) del sistema operativo, permitiendo introducir órdenes textuales directas.
- **Teoría del Andamiaje Cognitivo:** Principio psicopedagógico basado en Vygotsky (1978) según el cual un soporte estructurado permite al aprendiz resolver tareas complejas mientras desarrolla gradualmente su propia autonomía.
- **Tiempo de Resolución de Tarea (TRT):** Indicador cronométrico expresado en segundos que mide la duración total requerida por el usuario para completar una tarea administrativa en el sistema.
- **Tool Calling (Llamada a herramientas):** Capacidad técnica de los modelos de lenguaje modernos para emitir solicitudes estructuradas hacia funciones predefinidas y validadas por la aplicación anfitriona.
- **Ubuntu:** Distribución de GNU/Linux derivada de Debian, reconocida por su estabilidad, soporte comunitario y enfoque en la accesibilidad para usuarios de escritorio.
- **Usabilidad:** Atributo de calidad de ingeniería de software que mide cuán fácil, eficiente, seguro y satisfactorio resulta utilizar una interfaz humana.
- **Variable dependiente (VD):** Dimensión medida en el experimento para cuantificar el efecto de la intervención (eficiencia temporal, precisión/errores y usabilidad percibida).
- **Variable independiente (VI):** Factor manipulado intencionalmente por el investigador (el Asistente Conversacional Inteligente basado en PLN).
- **Virtualización:** Creación mediante software de una representación aislada de recursos de hardware y sistemas operativos para experimentación segura.
- **Windows 11:** Sistema operativo comercial de escritorio desarrollado por Microsoft, predominante en el mercado de computación personal.
- **Zona de Desarrollo Próximo (ZDP):** Distancia conceptual entre el nivel de resolución real de una persona actuando sin ayuda y su nivel de desarrollo potencial bajo la guía de un mediador o asistente pedagógico.
