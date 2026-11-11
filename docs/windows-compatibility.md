# Compatibilidad en Desde Windows

La ventana de migración contiene una sección **Compatibilidad** con un orientador,
guías por herramienta, métodos de instalación y diagnóstico local bajo demanda.
No necesita un LLM ni consultas de red para generar las rutas. Los enlaces a la
documentación se abren cuando el usuario los selecciona.

## Responsabilidades

- `src/gui/compatibility_catalog.py`: catálogo versionado de Wine, Bottles, Lutris,
  Proton, Heroic, WinBoat y wineboot. Contiene requisitos, límites, pasos, métodos
  de instalación y fuentes oficiales. No contiene código ejecutable.
- `src/gui/compatibility.py`: reglas de orientación y detección de ejecutables,
  aplicaciones Flatpak, memoria, almacenamiento y acceso a KVM. La única consulta
  a un proceso es `flatpak list`, con argumentos fijos y timeout de cinco segundos.
- `src/gui/webview_app.py`: adaptadores `get_compatibility_catalog`,
  `get_compatibility_overview` y `recommend_windows_compatibility`.
- `src/gui/web/compatibility.js` y `.css`: presentación acotada a la ventana de
  migración. Carga diferida, reintento, resultados con texto literal y limpieza de
  estados anteriores al volver a comprobar. Reutiliza la navegación y la vista
  previa de instalación de `migration.js`.

## Contratos y límites

Una recomendación recibe `use_case`, `application` (opcional, hasta 160 caracteres)
y `special_requirements` (booleano). Devuelve una ruta inicial y alternativas;
siempre indica que la aplicación concreta está pendiente de verificar. El nombre
de la aplicación no se convierte en comandos ni en HTML.

El catálogo tiene `schema_version: 1`. Cada método tiene una sola acción: paquete
Flatpak, búsqueda en el catálogo, enlace de descarga o selector de archivo local.
Los identificadores son curados; los comandos se preparan en el instalador
existente y se ejecutan mediante su flujo de confirmación. RPM se enlaza a las
descargas del proyecto; el selector local existente admite DEB y AppImage.

La detección diferencia **Detectado**, **No detectado** y **Sin comprobar**. Si
Flatpak falla, no declara ausentes sus aplicaciones. No inspecciona AppImage,
prefijos ni runners internos; encontrar Steam no significa encontrar Proton.
Las métricas no certifican que WinBoat esté listo: faltan versiones, Compose,
servicio de contenedores, soporte gráfico y espacio del destino elegido.

Para añadir una herramienta: incorporar la ficha con fuentes oficiales, añadir
su detector fijo y, si corresponde, una regla de orientación. No añadir comandos
de mantenimiento a la detección: wineboot puede modificar un prefijo incluso
cuando se invoca para resolver un problema.

## Validación

```sh
venv/bin/python -m pytest tests/test_compatibility.py tests/test_migration.py tests/test_artcraft_catalog.py tests/test_windows_guide.py tests/test_webview_app.py -q
node --test tests/compatibility-ui.test.cjs tests/migration-ui.test.cjs
```

Las pruebas JavaScript usan un DOM simulado; no sustituyen una revisión visual de
la ventana PyWebView. Fuentes y requisitos deben revisarse al actualizar fichas,
especialmente los de WinBoat, que sigue marcado como beta en su documentación.
