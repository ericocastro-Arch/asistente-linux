# Presentación de Defensa de Tesis: LinuxMate AI
## Asistente Conversacional Inteligente para la Migración y Accesibilidad en Sistemas Operativos Linux
**Autor:** Erico Francisco Castro Pérez  
**Facultad de Ingeniería en Sistemas de Información y Ciencias de la Computación**  
**Universidad Mariano Gálvez de Guatemala**  
**Tiempo estimado total:** 20 a 25 minutos

---

## Estructura General de la Presentación (20 Diapositivas)

```
[01] Portada e Identificación Institucional
[02] Planteamiento del Problema: La Brecha Digital en Linux
[03] Justificación e Impacto Sociotécnico
[04] Pregunta General e Hipótesis de Investigación
[05] Objetivos: General y Específicos
[06] Marco Metodológico y Diagnóstico de Campo (N = 8)
[07] Fundamentos Teóricos: HCI, Carga Cognitiva y Ecosistema Linux
[08] Arquitectura del Sistema: Middleware MVC con IA
[09] Modelo de Datos Relacional (SQLite) y Topología de Red
[10] Estrategia de Seguridad en Profundidad y Políticas
[11] Módulos Clave: Migración Windows, Diagnóstico y Academia
[12] Aseguramiento de Calidad Técnica: 344 Pruebas Automatizadas
[13] Resultados: Eficiencia Operativa (TRT -83.77%)
[14] Resultados: Tasa de Éxito (95%) y Reducción de Errores (IEO -90.67%)
[15] Evaluación de Usabilidad: NASA-TLX (-75%) y Escala SUS (88.44/100)
[16] Contrastación Estadística de Hipótesis (Prueba t de Student, p < 0.0001)
[17] Viabilidad Financiera y Presupuesto Operativo
[18] Conclusiones Principales
[19] Recomendaciones Técnicas, Institucionales y Académicas
[20] Cierre, Agradecimientos y Demostración en Vivo
```

---

### DIAPOSITIVA 01: Portada e Identificación Institucional
- **Tiempo sugerido:** 1 minuto.
- **Elementos visuales en pantalla:**
  - Logotipo oficial de la Universidad Mariano Gálvez de Guatemala.
  - Título del Trabajo: *Asistente conversacional inteligente para la migración y accesibilidad en sistemas operativos Linux*.
  - Nombre del Sustentante: Erico Francisco Castro Pérez.
  - Título a optar: Ingeniero en Sistemas de Información y Ciencias de la Computación / Licenciado en Sistemas.
  - Autoridades de la Facultad: Decano Ing. Jorge Alberto Arias Tobar, Secretario Ing. Hugo Alberto Hernández Santizo, Asesor Ing. Ricardo Estrada.
  - Año: 2026.
- **Guion del Expositor (Qué decir):**
  > *"Muy buenos días / tardes, honorables miembros de la terna evaluadora, Decano Ing. Jorge Arias, Secretario Ing. Hugo Hernández, mi asesor Ing. Ricardo Estrada y docentes de la Facultad de Ingeniería. Es un honor para mí presentar el trabajo de graduación titulado: 'Asistente conversacional inteligente para la migración y accesibilidad en sistemas operativos Linux'. Esta investigación aborda la brecha técnica y cognitiva que sufren los usuarios al intentar adoptar software libre, presentando una solución de ingeniería que combina inteligencia artificial con administración segura del sistema operativo."*

---

### DIAPOSITIVA 02: Planteamiento del Problema
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - Diagrama comparativo: *"Monopolio Cognitivo de Windows"* vs. *"Disonancia Operativa en Linux"*.
  - Tarjetas de impacto:
    - Dependencia de la interfaz de línea de comandos (CLI/Terminal).
    - Miedo generalizado a *"dañar la computadora"* o borrar datos.
    - Fracaso de los manuales estáticos tradicionales por falta de interactividad contextual.
- **Guion del Expositor (Qué decir):**
  > *"A nivel mundial y nacional, el software libre representa soberanía tecnológica y ahorro económico masivo. Sin embargo, en Guatemala la mayoría de las iniciativas de migración a Linux fracasan o se abandonan. ¿Por qué ocurre esto? Porque el usuario promedio ha desarrollado un modelo mental condicionado exclusivamente por Windows. Al enfrentarse a Linux, experimenta una severa disonancia operativa: no existen letras de disco C o D, no hay instaladores .exe universales y la configuración crítica exige la terminal de comandos. Para un usuario principiante o un estudiante sin formación técnica, esta pantalla negra sin pistas visuales genera frustración, ansiedad y el abandono inmediato de la herramienta."*

---

### DIAPOSITIVA 03: Justificación e Impacto Sociotécnico
- **Tiempo sugerido:** 1:15 minutos.
- **Elementos visuales en pantalla:**
  - 3 Pilares de Justificación:
    1. **Inclusión y Soberanía Digital:** Reducir la brecha de segundo orden (*skills divide*) en escuelas y hogares de recursos limitados.
    2. **Ahorro Financiero:** Eliminar licencias privativas comerciales sin sacrificar la facilidad de uso.
    3. **Andamiaje Educativo:** Una IA que no solo ejecuta tareas, sino que explica el 'por qué' en español claro.
- **Guion del Expositor (Qué decir):**
  > *"Este proyecto se justifica plenamente en tres dimensiones: social, económica y pedagógica. Socialmente, el acceso a la tecnología no debe ser un privilegio condicionado a saber memorizar comandos técnicos en inglés. Económicamente, permite a escuelas y centros comunitarios reutilizar computadoras reacondicionadas sin incurrir en licencias costosas. Y pedagógicamente, transforma a la computadora en un tutor interactivo que acompaña al ciudadano en su propio idioma."*

---

### DIAPOSITIVA 04: Pregunta General e Hipótesis de Investigación
- **Tiempo sugerido:** 1:15 minutos.
- **Elementos visuales en pantalla:**
  - **Pregunta General:** ¿En qué medida un asistente conversacional basado en modelos de lenguaje optimiza la gestión administrativa de Linux y reduce la brecha de aprendizaje en usuarios guatemaltecos con alfabetización digital básica?
  - **Hipótesis ($H_1$):** El uso del asistente conversacional incrementa la efectividad administrativa en Linux en usuarios principiantes, alcanzando una tasa de éxito superior al $80\%$ y reduciendo el tiempo de ejecución en más de un $40\%$ frente a manuales convencionales.
- **Guion del Expositor (Qué decir):**
  > *"Para guiar la investigación se formuló una hipótesis clara y medible: postulamos que al interponer una capa conversacional inteligente entre el usuario y el kernel del sistema operativo, la tasa de éxito alcanzará más del 80% y los tiempos de resolución se reducirán en más de un 40% en comparación con la consulta de manuales estáticos o búsquedas en Google."*

---

### DIAPOSITIVA 05: Objetivos del Proyecto
- **Tiempo sugerido:** 1:15 minutos.
- **Elementos visuales en pantalla:**
  - **Objetivo General:** Desarrollar un asistente inteligente basado en modelos de lenguaje que facilite la administración de sistemas operativos Linux para usuarios principiantes, traduciendo comandos técnicos en conversación en español.
  - **5 Objetivos Específicos:**
    1. Identificar dificultades y barreras técnicas de migración.
    2. Diseñar una interfaz gráfica accesible sin dependencia de terminal.
    3. Implementar un modelo de PLN para traducción semántica y ejecución segura.
    4. Evaluar la reducción de carga cognitiva frente a métodos tradicionales.
    5. Fomentar la adopción sustentable de software libre en Guatemala.
- **Guion del Expositor (Qué decir):**
  > *"El objetivo general se articuló en cinco metas específicas: diagnosticar las barreras reales de los usuarios, diseñar una interfaz accesible con paneles visuales y voz, implementar un motor semántico seguro con control de privilegios, medir la carga mental mediante instrumentos psicométricos estandarizados y validar la viabilidad económica de la solución."*

---

### DIAPOSITIVA 06: Marco Metodológico y Diagnóstico de Campo
- **Tiempo sugerido:** 1:45 minutos.
- **Elementos visuales en pantalla:**
  - Enfoque cuantitativo, aplicado y experimental. Muestra: $N = 8$.
  - Gráficos circulares de diagnóstico clave:
    - **Nivel de Terminal:** $0\%$ de la muestra sabe usar la consola.
    - **Mayor Temor:** $50\%$ teme perder sus archivos y $37.5\%$ no saber hacer sus tareas habituales.
    - **Aceptación de IA:** $0\%$ de rechazo hacia asistentes virtuales ($37.5\%$ uso regular, $37.5\%$ deseo de aprender).
    - **Automatización de Accesibilidad:** $62.5\%$ aprueba delegar ajustes críticos al sistema.
- **Guion del Expositor (Qué decir):**
  > *"En el marco metodológico se aplicó un enfoque cuantitativo experimental. En la fase diagnóstica, la encuesta confirmó que ninguno de los participantes dominaba la terminal de comandos. Sin embargo, se identificó un terreno sumamente fértil: existe cero por ciento de rechazo a la inteligencia artificial y un 62.5% de aprobación para delegar configuraciones complejas al asistente. El temor principal no era el sistema en sí, sino el miedo a perder datos personales."*

---

### DIAPOSITIVA 07: Fundamentos Teóricos de la Solución
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - Esquema conceptual de 3 pilares teóricos:
    1. **Interacción Humano-Computadora (HCI):** Atributos de Usabilidad de Nielsen (Aprendizaje, Eficiencia, Errores, Satisfacción).
    2. **Teoría de la Carga Cognitiva (Sweller):** Absorción de la carga extrínseca (sintaxis críptica) y andamiaje cognitivo (Vygotsky).
    3. **Modelo de Aceptación Tecnológica (TAM de Davis):** Utilidad percibida y facilidad de uso percibida.
    4. **PLN y Tool Calling:** Transformación de intenciones libres en funciones estructuradas de sistema.
- **Guion del Expositor (Qué decir):**
  > *"La arquitectura del software se apoya en sólidos marcos teóricos: la Teoría de la Carga Cognitiva de Sweller explica cómo la terminal satura la memoria de trabajo del usuario con 'carga extrínseca'. El asistente absorbe esa carga innecesaria para que el sujeto se enfoque en su meta funcional. Asimismo, aplicando el principio de andamiaje de Vygotsky, cada acción va acompañada de una explicación pedagógica que permite aprender gradualmente."*

---

### DIAPOSITIVA 08: Arquitectura del Sistema (LinuxMate AI)
- **Tiempo sugerido:** 2:00 minutos.
- **Elementos visuales en pantalla:**
  - Diagrama de Arquitectura Modular MVC + Orquestador:
    - **Capa de Vista:** GUI Dual (`PyWebView Liquid Glass` + Respaldo seguro en `CustomTkinter`).
    - **Capa de Enrutamiento:** Enrutador Determinista Local (`router.py`) vs. Agente LLM (`agent.py`).
    - **Capa de Integración:** Multi-proveedor (Groq, OpenAI, NVIDIA, Gemini, Ollama local).
    - **Capa de Ejecución:** Subprocesos con validación de seguridad y detección de distribución (`distro.py`).
- **Guion del Expositor (Qué decir):**
  > *"En la arquitectura del software, adoptamos un patrón MVC desacoplado con una innovación crítica: el Enrutamiento Híbrido. Las peticiones cotidianas —como consultar recursos, abrir aplicaciones o diagnósticos de red— se resuelven en 40 milisegundos de forma 100% local sin consultar internet ni gastar cuota de API. Solo las consultas abiertas o explicativas complejas se envían al Agente LLM. Además, la interfaz cuenta con arquitectura dual: moderna acelerada por web y un respaldo nativo en CustomTkinter que garantiza que siempre abrirá en cualquier equipo."*

---

### DIAPOSITIVA 09: Modelo de Datos Relacional y Topología de Red
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - Diagrama E-R de SQLite (`assistant.db`): `SESSIONS` ($1:N$) $\rightarrow$ `MESSAGES`, `TOOL_RUNS`, `SYSTEM_SNAPSHOTS`.
  - Topología de Red: Aislamiento en Loopback Local (`127.0.0.1:11434` para Ollama y D-Bus interno) vs. Conexiones salientes cifradas HTTPS (`TLS 1.3 :443`) con límites de tiempo (*timeouts*).
- **Guion del Expositor (Qué decir):**
  > *"Para la persistencia y auditoría, el sistema integra una base de datos relacional local en SQLite con integridad referencial activa. Cada orden, comando ejecutado, salida estándar y código de retorno queda auditado de forma inmutable. A nivel de red, todo el tráfico sensible y el control del sistema ocurre dentro de la propia máquina; ninguna clave se transmite en texto plano gracias a su resguardo en el llavero del sistema operativo."*

---

### DIAPOSITIVA 10: Estrategia de Seguridad en Profundidad
- **Tiempo sugerido:** 1:45 minutos.
- **Elementos visuales en pantalla:**
  - Matriz de Seguridad de 4 Niveles:
    - **Nivel 1 - Sanitización y Bloqueo:** Filtro regex que bloquea comandos destructivos (`rm -rf`, `mkfs`, bombas fork, etc.).
    - **Nivel 2 - Lista Blanca de Herramientas:** Niveles `READ`, `USER` y `SYSTEM`. No hay modo autónomo descontrolado.
    - **Nivel 3 - Elevación Segura con PolicyKit:** Uso de `pkexec` con política dedicada (`com.linuxmate.policy`) y protección de paquetes vitales (`bash`, `apt`, `systemd`).
    - **Nivel 4 - Respaldos Atómicos SHA-256:** Confinamiento a `$HOME` y función 'Deshacer' (`undo`).
- **Guion del Expositor (Qué decir):**
  > *"Un asistente con acceso al sistema operativo debe ser seguro por diseño. Implementamos una estrategia de defensa en profundidad alineada con OWASP: el agente nunca opera como 'root' silencioso. Si un comando requiere privilegios, se invoca PolicyKit exigiendo la confirmación gráfica del usuario. Además, antes de que el asistente modifique un archivo, genera una copia privada y calcula su hash SHA-256, permitiendo revertir cualquier cambio al estado anterior con un solo clic."*

---

### DIAPOSITIVA 11: Módulos Clave de la Aplicación
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - 4 Capturas/Tarjetas de Funcionalidades:
    1. **Centro de Control:** Monitoreo visual de CPU, RAM, disco y procesos activos.
    2. **Guía de Migración Windows:** Buscador de 32 equivalencias (Photoshop $\rightarrow$ GIMP, Office $\rightarrow$ LibreOffice, etc.).
    3. **Solucionador de Problemas:** Diagnósticos guiados para "máquina lenta", problemas de audio o red.
    4. **Academia 'Aprende Linux':** 6 cursos interactivos offline, 90 lecciones y exámenes de 75 preguntas con evaluación inmediata.
- **Guion del Expositor (Qué decir):**
  > *"Para resolver los temores identificados en la encuesta, creamos módulos específicos: la Guía de Windows le indica al usuario exactamente cuál es el reemplazo de sus programas habituales. El Solucionador de Problemas diagnostica y repara fallas comunes en dos clics. Y para convertir la migración en un proceso formativo, se construyó la 'Academia Aprende Linux' con 6 cursos completos y 90 lecciones que funcionan completamente sin internet."*

---

### DIAPOSITIVA 12: Aseguramiento de Calidad Técnica (SQA)
- **Tiempo sugerido:** 1:15 minutos.
- **Elementos visuales en pantalla:**
  - Consola de Pruebas: **344 pruebas automatizadas en `Pytest` aprobadas al 100% en 19.42 segundos**.
  - Cobertura técnica:
    - 88 pruebas de núcleo, seguridad y enrutador NLP.
    - 46 pruebas de elevación PolicyKit y bloqueo de servicios vitales.
    - 38 pruebas de adaptación multi-distribución (Ubuntu, Fedora, Arch, openSUSE).
    - 31 pruebas de respaldos atómicos y reversión segura.
  - Consumo de RAM verificado: **$118.4\text{ MB}$** (muy por debajo del límite de $200\text{ MB}$).
- **Guion del Expositor (Qué decir):**
  > *"Antes de llevar el software a los usuarios, se ejecutó una suite exhaustiva de 344 pruebas unitarias y de integración automatizadas. El 100% de las pruebas pasaron satisfactoriamente en menos de 20 segundos. Se validó empíricamente que la aplicación consume apenas 118 MB de RAM, garantizando su funcionamiento fluido en computadoras reacondicionadas o de bajo costo."*

---

### DIAPOSITIVA 13: Resultados: Eficiencia Operativa (TRT)
- **Tiempo sugerido:** 1:45 minutos.
- **Elementos visuales en pantalla:**
  - Gráfico de barras comparativo: Tiempo de Resolución de Tarea ($\text{TRT}$ en segundos).
  - Tareas evaluadas ($T_1$ a $T_5$): Monitoreo de recursos, instalación de software, actualización, diagnóstico de red y gestión de archivos.
  - **Métricas:**
    - Método Tradicional (Manuales / Búsqueda web): **$197.80\text{ s}$ promedio ($3.3\text{ min}$)**.
    - Con LinuxMate AI: **$32.10\text{ s}$ promedio ($0.5\text{ min}$)**.
    - **Optimización lograda:** **$-83.77\%$ de reducción de tiempo** (superando con creces la meta del $40\%$).
- **Guion del Expositor (Qué decir):**
  > *"En la fase experimental con usuarios, medimos cronométricamente la eficiencia mediante el Tiempo de Resolución de Tarea. El resultado fue contundente: el tiempo promedio por tarea cayó de 197.8 segundos con manuales convencionales a solo 32.1 segundos con nuestro asistente inteligente. Esto representa una reducción de tiempo del 83.77%, duplicando con creces el umbral del 40% planteado en la hipótesis."*

---

### DIAPOSITIVA 14: Resultados: Tasa de Éxito y Curva de Errores
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - Tarjetas de impacto cuantitativo:
    - **Tasa de Finalización de Tareas:** Del **$45.0\%$** (método tradicional) al **$95.0\%$** (con el asistente). Meta superada ($> 80\%$).
    - **Interpretación Semántica (TEI):** **$93.75\%$** de precisión en primera orden ($100\%$ con sugerencia guiada).
    - **Índice de Errores Operativos (IEO):** Reducción de $6.75$ a $0.63$ errores por sesión (**$-90.67\%$**).
    - **Curva de Aprendizaje:** Reducción del **$84.20\%$** en errores tras 3 intentos (criterio de Nielsen cumplido $\ge 70\%$).
- **Guion del Expositor (Qué decir):**
  > *"La efectividad operativa pasó de un deficiente 45% a un sólido 95% de éxito. Además, los errores operativos se redujeron en más de un 90%. Al analizar la curva de aprendizaje de Nielsen, observamos que tras los primeros tres intentos los errores cayeron un 84.2%, demostrando que la interfaz es intuitiva y que el usuario adquiere confianza casi inmediata."*

---

### DIAPOSITIVA 15: Evaluación de Usabilidad y Carga Cognitiva
- **Tiempo sugerido:** 1:45 minutos.
- **Elementos visuales en pantalla:**
  - Comparativa de Carga Cognitiva (**NASA-TLX**):
    - Puntaje Global PCC: Reducción del **$75.00\%$** (de $68.33$ a $17.08$ puntos sobre 100).
    - Nivel de Frustración: Reducción del **$82.15\%$**.
  - **Escala de Usabilidad del Sistema (SUS):**
    - Método Tradicional: $43.75 / 100$ (Grado F - Inaceptable).
    - Asistente LinuxMate AI: **$88.44 / 100$ (Grado A - Nivel Excelente)**.
- **Guion del Expositor (Qué decir):**
  > *"Al evaluar la experiencia psicotécnica mediante la escala NASA-TLX, confirmamos que la carga cognitiva global disminuyó en tres cuartas partes (75%), y el nivel de frustración se desplomó un 82%. Finalmente, la Escala de Usabilidad del Sistema (SUS) otorgó una calificación de 88.44 sobre 100, posicionando a LinuxMate AI en el Grado A de Excelencia según los estándares internacionales de la industria del software."*

---

### DIAPOSITIVA 16: Contrastación Estadística de Hipótesis
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - Prueba paramétrica: **$t$ de Student para muestras pareadas** ($gl = 7, \alpha = 0.05$).
  - Ecuación del estadístico: $t = \frac{\bar{d}}{SE_{\bar{d}}} = \frac{165.70}{9.49} = 17.46$.
  - Comparación crítica:
    - $t_{\text{calculado}} = 17.46$ frente a $t_{\text{crítico}} = 1.895$.
    - Nivel de significancia alcanzado: **$p < 0.0001$**.
  - **Veredicto:** Rechazo contundente de la Hipótesis Nula ($H_0$) y Aceptación de la Hipótesis de Investigación ($H_1$).
- **Guion del Expositor (Qué decir):**
  > *"Para validar científicamente los resultados, aplicamos la prueba t de Student para muestras relacionadas. Con un valor crítico de 1.895 para un 95% de confianza, nuestro estadístico calculado alcanzó 17.46, arrojando un p-valor menor a 0.0001. Esto nos permite rechazar con total rigor estadístico la hipótesis nula y aceptar la hipótesis de investigación: la mediación del asistente conversacional optimiza el rendimiento y democratiza la administración del sistema operativo."*

---

### DIAPOSITIVA 17: Viabilidad Financiera y Presupuesto
- **Tiempo sugerido:** 1:00 minuto.
- **Elementos visuales en pantalla:**
  - **Inversión Inicial de Desarrollo:** $\text{Q } 20,780.00$ (Hardware, 240 horas de ingeniería de software y contingencia).
  - **Costo de Licenciamiento para Escuelas y Usuarios:** **$\text{Q } 0.00$ (100% Código Abierto)**.
  - **Costo Operativo Recurrente Mensual:**
    - Modo Local (Ollama) / Tareas Locales: **$\text{Q } 0.00$**.
    - Con API comercial (50 consultas al mes): Máximo $\text{Q } 4.00$ ($\approx \$0.50\text{ USD}$) al mes por usuario.
- **Guion del Expositor (Qué decir):**
  > *"En términos financieros, la solución es altamente sostenible. Su licenciamiento es libre y gratuito. Para las escuelas públicas de Guatemala, el costo operativo puede ser exactamente cero quetzales utilizando el motor de enrutamiento local o servidores Ollama en la red local. Si se utilizan modelos en la nube, el consumo promedio no supera los 4 quetzales mensuales por equipo."*

---

### DIAPOSITIVA 18: Conclusiones
- **Tiempo sugerido:** 1:30 minutos.
- **Elementos visuales en pantalla:**
  - 4 Conclusiones Cardinales:
    1. **Hipótesis Comprobada:** Se alcanzó $95\%$ de éxito y $-83.77\%$ en tiempos operativos ($p < 0.0001$).
    2. **Mitigación del Miedo Psicológico:** La guía de equivalencias y los respaldos atómicos SHA-256 eliminaron el temor a la pérdida de datos.
    3. **Autonomía sin Terminal:** Los paneles gráficos y la voz offline permitieron administrar el sistema con un índice SUS de 88.44/100 (Grado A).
    4. **Soberanía y Andamiaje:** La academia integrada educó a los usuarios mientras resolvían sus necesidades reales.
- **Guion del Expositor (Qué decir):**
  > *"Como conclusiones primordiales: primero, la hipótesis fue validada empírica y estadísticamente; segundo, demostramos que la principal barrera hacia Linux no era técnica sino cognitiva, y que fue superada mediante el andamiaje pedagógico y la protección de datos; tercero, logramos que usuarios sin conocimientos previos completaran tareas avanzadas con una usabilidad calificada de excelente; y cuarto, entregamos un producto de software robusto, auditado y listo para ser adoptado."*

---

### DIAPOSITIVA 19: Recomendaciones
- **Tiempo sugerido:** 1:15 minutos.
- **Elementos visuales en pantalla:**
  - 3 Ejes de Recomendaciones:
    1. **Sector Educativo (MINEDUC / Laboratorios):** Implementar LinuxMate AI como plataforma predeterminada en programas de computadoras reacondicionadas.
    2. **Entornos Rurales / Desconectados:** Desplegar servidores locales con Ollama (`Llama-3.2-3B`) en red LAN para operar con costo cero y sin depender de internet.
    3. **Futuras Investigaciones UMG:** Extender la capa de procesamiento de lenguaje natural hacia idiomas mayas nacionales (K'iche', Kaqchikel, Q'eqchi' y Mam).
- **Guion del Expositor (Qué decir):**
  > *"Recomendamos al Ministerio de Educación y a las instituciones comunitarias adoptar esta herramienta en sus programas de equipamiento escolar. Para zonas rurales sin acceso a internet, recomendamos el despliegue con Ollama en red de área local. Y como línea de investigación futura para nuestra facultad, proponemos entrenar modelos adaptadores en idiomas mayas nacionales como K'iche' o Kaqchikel, llevando la inclusión digital a las comunidades más vulnerables del país."*

---

### DIAPOSITIVA 20: Cierre y Espacio de Preguntas
- **Tiempo sugerido:** 1:00 minuto.
- **Elementos visuales en pantalla:**
  - Agradecimientos a la Universidad Mariano Gálvez de Guatemala, autoridades, asesor y familiares.
  - Repositorio del Proyecto y Demostración en Vivo disponible.
  - Frase de cierre: *"La tecnología no debe obligar al ser humano a hablar como máquina; la máquina debe aprender a comunicarse en el lenguaje del ser humano."*
  - Apertura al Tribunal para preguntas y respuestas.
- **Guion del Expositor (Qué decir):**
  > *"Agradezco a Dios, a mi familia, a mi asesor Ing. Ricardo Estrada y a las autoridades de la Universidad Mariano Gálvez por su orientación durante este proceso formativo. Quedo a la entera disposición de este honorable tribunal para responder a sus preguntas o realizar la demostración técnica en vivo del sistema. Muchas gracias."*
