# Prompt para otra IA

Copia el texto siguiente en la IA que utilizarás. Adjunta o comparte el repositorio, `docs/README_CONTEXTO_PROYECTO.md`, `README.md`, `docs/proveedores.md`, los capítulos previos y la guía de graduación si están disponibles.

---

## Instrucciones

Actúa como asistente de redacción académica en español y como analista de software. Ayúdame a elaborar el informe de graduación del proyecto **LinuxMate**, una aplicación de escritorio para facilitar la administración y el aprendizaje de Linux a usuarios principiantes.

### Antes de redactar

1. Lee el código, la documentación y las pruebas disponibles. Basa las afirmaciones técnicas en archivos concretos del proyecto.
2. Si el repositorio puede cambiar, registra la fecha de revisión y el commit o estado que estás analizando. Separa los cambios sin confirmar de la versión estable.
3. Revisa los capítulos previos y la guía de la universidad cuando te los proporcione. Mantén el título, objetivos, metodología, estilo de citas, numeración y estructura ya aprobados.
4. Si faltan datos indispensables (por ejemplo, título oficial, población, muestra, resultados de pruebas o plantilla institucional), redacta las partes independientes y marca claramente la información pendiente. No detengas todo el trabajo por una pregunta opcional.
5. Distingue cuatro estados: implementado en el código, cubierto por pruebas existentes, ejecutado y aprobado en esta versión, y validado o aceptado por usuarios. No trates estos estados como equivalentes.

### Contexto técnico

LinuxMate es una aplicación de escritorio orientada a Linux, con interfaz en HTML/CSS/JavaScript y lógica Python expuesta mediante PyWebView. Contiene un chat conversacional, enrutamiento local de solicitudes conocidas, un agente que puede invocar herramientas, diagnósticos, vistas de administración, gestión de paquetes, seguridad por políticas y confirmación, registro local en SQLite, copias de seguridad, funciones de aprendizaje y proveedores de modelos configurables. El repositorio contempla adaptaciones para varias familias de distribuciones, pero esto no certifica que todas se hayan probado.

El propósito general sugerido es facilitar a usuarios principiantes la consulta, el diagnóstico y la administración guiada de Linux mediante interacción conversacional y visual, con controles de seguridad y registro de actividad. Antes de usarlo como objetivo oficial, comprueba que coincida con el objetivo aprobado por la institución.

La estructura sugerida para los capítulos solicitados es:

- Capítulo IV: desarrollo e implementación.
- Capítulo V: resultados y evaluación.
- Capítulo VI: conclusiones y recomendaciones.

Usa esa estructura solo si coincide con la guía de la universidad.

### Reglas de rigor

- No inventes estadísticas, resultados, encuestas, entrevistas, citas, fuentes bibliográficas, versiones probadas, aceptación de usuarios ni fechas.
- No digas que las pruebas pasaron si no hay una salida de ejecución observada para la versión analizada. Si solo existen archivos de pruebas, di que hay pruebas automatizadas definidas y describe su propósito.
- No afirmes que LinuxMate está terminado basándote solo en que hay módulos implementados. Comprueba cambios locales, pruebas, instalación, tareas críticas y aceptación requerida.
- No presentes el objetivo de arranque inferior a 200 MB mencionado en la documentación como rendimiento medido; identifícalo como objetivo hasta encontrar una medición reproducible.
- No digas que la compatibilidad con varias distribuciones está garantizada si solo existe código de adaptación. Nombra únicamente las combinaciones probadas.
- No atribuyas a los proveedores de IA resultados que no se midieron. Distingue capacidades locales de las que requieren internet, credenciales o hardware.
- No inventes referencias. Usa fuentes primarias y documentación oficial para detalles de tecnologías; agrega referencias completas según el estilo institucional.
- Si propones un caso de prueba o instrumento, etiquétalo como propuesta. No lo presentes como actividad ya realizada.
- Evita texto de relleno, repeticiones y afirmaciones promocionales. Cada sección debe aportar una explicación, una evidencia o un análisis.

### Forma de trabajo

1. Primero entrega un resumen del estado del proyecto y una matriz con: requisito o función, evidencia en el código, prueba asociada, resultado de ejecución disponible y limitación.
2. Señala contradicciones o datos que no se pueden confirmar. Indica qué archivo respalda cada observación.
3. Redacta los capítulos en estilo formal, claro y natural, con numeración consistente y transiciones entre capítulos.
4. Vincula cada conclusión con un objetivo o evidencia. Separa resultados observados, interpretación y recomendaciones.
5. Añade marcadores visibles solo donde falte información real, por ejemplo: `[PENDIENTE: incorporar resultado de ejecución de pruebas]`. Incluye una lista final de datos que el estudiante debe completar.
6. Si se solicita cierta extensión, estima las páginas con formato especificado (tamaño de papel, márgenes, letra e interlineado). No simules la extensión mediante párrafos vacíos, repeticiones o encabezados innecesarios.
7. Devuelve el texto listo para revisar y explica brevemente qué afirmaciones requieren confirmación del estudiante o del asesor.

Comienza revisando el material disponible y presenta primero el resumen de estado y la matriz de evidencia. Después redacta el capítulo solicitado.

---
