# Proveedores de LinuxMate

Configuración → Modelos y API ofrece 13 opciones: Groq, NVIDIA NIM,
OpenAI, Anthropic, Google Gemini, xAI, Together AI, DeepSeek,
Alibaba Cloud Qwen, Moonshot Kimi, Z.ai, Ollama y una API personalizada.

Cada proveedor conserva su clave, modelo y URL base. Los cambios de selección
conservan los borradores; Guardar cambios los escribe en `.env` y recarga el
agente. Las claves son locales y se envían al endpoint configurado al consultar
modelos, probar la conexión o usar el asistente.

El botón de actualización consulta los modelos con la clave y URL del formulario.
También se puede escribir un identificador manualmente. La prueba de conexión
envía una consulta breve, que puede consumir cuota. La ejecución de acciones del
asistente requiere un modelo con soporte de herramientas; una conexión válida
no garantiza esa capacidad en todos los modelos del catálogo.

Tiempo de espera, límite de salida y estilo se aplican al agente al guardar.
La temperatura se omite en proveedores con restricciones de muestreo.
Ollama admite tanto la URL raíz como una URL terminada en `/v1`.

## Referencias de integración

- [DeepSeek](https://api-docs.deepseek.com/): interfaz compatible y endpoint.
- [Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope): endpoints y claves por región. El preset usa Virginia; otras regiones requieren su URL de espacio de trabajo.
- [Moonshot](https://platform.moonshot.ai/docs/api/chat): chat, herramientas y campos de razonamiento.
- [Z.ai](https://docs.z.ai/guides/overview/quick-start): endpoint de API estándar; los planes de programación tienen otro endpoint.
- [Anthropic](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk): capa compatible, parámetros de muestreo y herramientas.
- [Google Gemini](https://ai.google.dev/gemini-api/docs/openai): compatibilidad y catálogo de modelos.
- [xAI](https://docs.x.ai/developers/model-capabilities/text/generate-text): endpoint y modelos.
- [Together AI](https://docs.together.ai/docs/inference/openai-compatibility): configuración compatible.

Los identificadores iniciales son editables y pueden cambiar con el catálogo o
la cuenta. Las pruebas automatizadas usan clientes simulados, sin claves reales
ni consumo de APIs externas.
