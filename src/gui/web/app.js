/* ==========================================================================
   LinuxMate AI — Liquid Glass Client Application Bridge
   Connects HTML/CSS/JS frontend to Python PyWebView Backend
   ========================================================================== */

// --- Global State ---
let isResizing = false;
let isChatExpanded = false;
let pointerFrame = null;
let pendingUninstall = null;
let catalogSearchTimer = null;
let catalogRequestId = 0;
let diagnosticLoaded = false;
let diagnosticLoading = false;
let explanationKind = null;
let guideExplanationKind = 'command';
let problemGuides = [];
let selectedProblemId = '';
let problemGuidesLoaded = false;
let problemCheckRunning = false;
let problemCheckResults = [];
let backupSources = [];
let customBackupSources = [];
let backupSelectedSources = new Set();
let backupDestination = '';
let backupTaskId = '';
let backupOverviewLoading = false;
let systemServices = [];
let systemServicesLoading = false;
let systemServiceActionRunning = false;
let systemServiceError = '';
let resourceMonitorLoading = false;
let resourceMonitorData = null;
let codeActiveProject = '';
let codeActiveFile = '';
let codeBaseContent = '';
let codePendingToken = '';

const appCatalogState = {
  source: 'all',
  category: 'all',
  query: '',
  offset: 0,
  limit: 36,
  total: 0,
  hasMore: false,
  loading: false,
  loaded: false
};

const catalogCategoryLabels = {
  all: 'Todas',
  internet: 'Internet',
  office: 'Oficina',
  multimedia: 'Multimedia',
  development: 'Desarrollo',
  design: 'Diseño',
  communication: 'Comunicación',
  games: 'Juegos',
  utilities: 'Utilidades',
  system: 'Sistema',
  other: 'Otros paquetes'
};

const catalogSourceLabels = {
  apt: 'APT', dnf: 'DNF', pacman: 'Pacman', zypper: 'Zypper', snap: 'Snap', flatpak: 'Flatpak'
};

const previewCatalog = [
  { source: 'apt', package: 'firefox', name: 'Firefox', description: 'Navegador web privado y extensible.', category: 'internet', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.mozilla.firefox.png' },
  { source: 'apt', package: 'libreoffice', name: 'LibreOffice', description: 'Suite completa de oficina.', category: 'office', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.libreoffice.LibreOffice.png' },
  { source: 'apt', package: 'vlc', name: 'VLC', description: 'Reproductor multimedia universal.', category: 'multimedia', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.videolan.VLC.png' },
  { source: 'apt', package: 'gimp', name: 'GIMP', description: 'Edición avanzada de imágenes.', category: 'design', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.gimp.GIMP.png' },
  { source: 'dnf', package: 'code', name: 'Visual Studio Code', description: 'Editor para programación.', category: 'development', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/com.visualstudio.code.png' },
  { source: 'pacman', package: 'firefox', name: 'Firefox', description: 'Navegador web privado y extensible.', category: 'internet', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.mozilla.firefox.png' },
  { source: 'zypper', package: 'gimp', name: 'GIMP', description: 'Edición avanzada de imágenes.', category: 'design', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.gimp.GIMP.png' },
  { source: 'snap', package: 'spotify', name: 'Spotify', description: 'Música y podcasts.', category: 'multimedia', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/com.spotify.Client.png' },
  { source: 'snap', package: 'discord', name: 'Discord', description: 'Comunidades, chat y llamadas.', category: 'communication', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/com.discordapp.Discord.png' },
  { source: 'flatpak', package: 'org.blender.Blender', name: 'Blender', description: 'Creación y animación 3D.', category: 'design', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/org.blender.Blender.png' },
  { source: 'flatpak', package: 'com.valvesoftware.Steam', name: 'Steam', description: 'Plataforma de videojuegos.', category: 'games', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/com.valvesoftware.Steam.png' },
  { source: 'flatpak', package: 'md.obsidian.Obsidian', name: 'Obsidian', description: 'Notas enlazadas en Markdown.', category: 'office', installed: false, icon: 'https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/md.obsidian.Obsidian.png' }
];

const toolWorkspaceActions = new Set([
  'code_workspace',
  'install_programs',
  'terminal_guide',
  'troubleshooter',
  'resource_monitor',
  'logs_analyzer',
  'service_manager',
  'backup_manager',
  'problem_solver',
  'setup_guide',
  'uninstall_manager'
]);

const toolTabCopy = {
  code_workspace: ['Proyectos de programación', 'Archivos locales con cambios revisables antes de aplicarlos.'],
  install_programs: ['Instalar aplicaciones', 'Catálogo de APT, DNF, Pacman, Zypper, Snap y Flatpak.'],
  terminal_guide: ['Comandos y errores', 'Explicaciones locales; no ejecutan comandos ni envían el texto a la IA.'],
  troubleshooter: ['Diagnóstico del sistema', 'Revisa problemas comunes sin modificar tu equipo.'],
  resource_monitor: ['Monitor de recursos', 'Consulta CPU, memoria, discos, red, temperatura y procesos.'],
  logs_analyzer: ['Analizador de registros', 'Filtra eventos locales y revisa patrones frecuentes con datos sensibles redactados.'],
  service_manager: ['Gestor de servicios', 'Consulta servicios systemd y controla su estado con confirmación.'],
  backup_manager: ['Respaldos y restauración', 'Guarda archivos personales y restaura una copia en una carpeta nueva.'],
  problem_solver: ['Soluciones guiadas', 'Investiga un síntoma con comprobaciones locales y pasos seguros.'],
  setup_guide: ['Configuración inicial', 'Prepara una ruta para tu distribución y el uso que le darás a Linux.'],
  uninstall_manager: ['Desinstalador seguro', 'Busca la aplicación y confirma antes de quitarla.']
};

const setupStorageKey = 'linuxmate_guided_setup_v1';
const setupProfiles = {
  daily: { title: 'uso diario', category: 'internet', steps: [
    { id: 'updates', icon: 'sync', title: 'Revisa las actualizaciones', detail: 'Abre el gestor de tu distribución. Lee la lista de cambios antes de aceptar y conecta el portátil a la corriente.', action: 'run:update_distro', actionLabel: 'Actualizar sistema', secondaryAction: 'update_system', secondaryLabel: 'Guía de actualización' },
    { id: 'apps', icon: 'network', title: 'Elige navegador y aplicaciones', detail: 'Busca las aplicaciones que ya conoces y revisa su origen. Instala solo las que vayas a usar.', action: 'apps', actionLabel: 'Explorar aplicaciones', category: 'internet' },
    { id: 'media', icon: 'game', title: 'Prepara video y música', detail: 'Explora reproductores y formatos multimedia compatibles con tu distribución; LinuxMate no añade repositorios automáticamente.', action: ' run:install_codecs'.trim(), actionLabel: 'Instalar codecs multimedia', secondaryAction: 'apps', secondaryCategory: 'multimedia', secondaryLabel: 'Ver multimedia' },
    { id: 'drivers', icon: 'settings', title: 'Comprueba los controladores', detail: 'Consulta qué recomienda tu distribución para gráficos y Wi-Fi. Instala un controlador solo si el sistema lo recomienda.', action: 'run:check_drivers', actionLabel: 'Comprobar controladores', secondaryAction: 'drivers_manager', secondaryLabel: 'Consultar al asistente' },
    { id: 'backup', icon: 'backup', title: 'Prepara una copia de seguridad', detail: 'Decide qué archivos guardar y en qué disco. Comprueba que puedas abrir una copia antes de depender de ella.', action: 'backup_manager', actionLabel: 'Crear un respaldo' }
  ] },
  study: { title: 'estudio', category: 'office', steps: [
    { id: 'updates', icon: 'sync', title: 'Revisa las actualizaciones', detail: 'Lee los cambios que proponga el gestor de tu distribución antes de aceptarlos.', action: 'run:update_distro', actionLabel: 'Actualizar sistema', secondaryAction: 'update_system', secondaryLabel: 'Guía de actualización' },
    { id: 'apps', icon: 'package', title: 'Instala tus herramientas de estudio', detail: 'Busca ofimática, lectores y aplicaciones para tus clases. Comprueba el formato y la fuente de cada app.', action: 'apps', actionLabel: 'Explorar oficina', category: 'office' },
    { id: 'drivers', icon: 'settings', title: 'Comprueba los controladores', detail: 'Verifica que el Wi-Fi, el sonido y los gráficos tengan su controlador activo.', action: 'run:check_drivers', actionLabel: 'Comprobar controladores', secondaryAction: 'drivers_manager', secondaryLabel: 'Consultar al asistente' },
    { id: 'academy', icon: 'doc', title: 'Aprende Linux a tu ritmo', detail: 'Abre LinuxMate Academy para seguir los cursos y practicar en su terminal de aprendizaje.', action: 'academy', actionLabel: 'Abrir LinuxMate Academy' },
    { id: 'backup', icon: 'backup', title: 'Guarda tus trabajos', detail: 'Mantén una copia en un soporte aparte y prueba que tus documentos se abran desde allí.', action: 'backup_manager', actionLabel: 'Crear un respaldo' }
  ] },
  development: { title: 'desarrollo', category: 'development', steps: [
    { id: 'updates', icon: 'sync', title: 'Revisa las actualizaciones', detail: 'Actualiza antes de instalar herramientas y revisa los cambios que proponga el gestor.', action: 'run:update_distro', actionLabel: 'Actualizar sistema', secondaryAction: 'update_system', secondaryLabel: 'Guía de actualización' },
    { id: 'apps', icon: 'code', title: 'Elige tus herramientas de desarrollo', detail: 'Explora editores, Git, Python, Node.js y otros paquetes disponibles para tu distribución.', action: 'apps', actionLabel: 'Explorar desarrollo', category: 'development' },
    { id: 'workspace', icon: 'code', title: 'Crea tu primer proyecto', detail: 'LinuxMate Dev Studio ofrece plantillas y ejecuta ejemplos dentro de un entorno aislado.', action: 'code_workspace', actionLabel: 'Abrir Dev Studio' },
    { id: 'drivers', icon: 'settings', title: 'Comprueba los controladores', detail: 'Revisa las recomendaciones de la distribución, sobre todo si usarás GPU para desarrollo o cómputo.', action: 'run:check_drivers', actionLabel: 'Comprobar controladores', secondaryAction: 'drivers_manager', secondaryLabel: 'Consultar al asistente' },
    { id: 'backup', icon: 'backup', title: 'Respalda tus proyectos', detail: 'Usa Git para el historial y conserva además una copia separada de tus archivos importantes.', action: 'backup_manager', actionLabel: 'Crear un respaldo' }
  ] },
  gaming: { title: 'juegos', category: 'games', steps: [
    { id: 'updates', icon: 'sync', title: 'Revisa las actualizaciones', detail: 'Usa el gestor de tu distribución y revisa la lista de cambios antes de aplicarlos.', action: 'run:update_distro', actionLabel: 'Actualizar sistema', secondaryAction: 'update_system', secondaryLabel: 'Guía de actualización' },
    { id: 'drivers', icon: 'settings', title: 'Comprueba los controladores gráficos', detail: 'Consulta las recomendaciones oficiales de tu distribución y confirma el modelo de GPU antes de cambiar drivers.', action: 'run:check_drivers', actionLabel: 'Comprobar controladores', secondaryAction: 'drivers_manager', secondaryLabel: 'Consultar al asistente' },
    { id: 'games', icon: 'game', title: 'Explora Steam y juegos', detail: 'Revisa disponibilidad, compatibilidad y espacio requerido. Proton puede variar por juego.', action: 'apps', actionLabel: 'Explorar juegos', category: 'games' },
    { id: 'multimedia', icon: 'package', title: 'Añade herramientas multimedia si las necesitas', detail: 'Busca grabación, chat de voz y reproductores. Evita instalar componentes que no vayas a utilizar.', action: 'run:install_codecs', actionLabel: 'Instalar codecs multimedia', secondaryAction: 'apps', secondaryCategory: 'multimedia', secondaryLabel: 'Explorar multimedia' },
    { id: 'backup', icon: 'backup', title: 'Protege partidas y archivos', detail: 'Comprueba dónde guarda cada juego las partidas y configura respaldo antes de cambiar de disco o reinstalar.', action: 'backup_manager', actionLabel: 'Crear un respaldo' }
  ] }
};
let setupProfile = 'daily';
let setupCompleted = {};
try {
  const savedSetup = JSON.parse(localStorage.getItem(setupStorageKey) || '{}');
  if (Object.prototype.hasOwnProperty.call(setupProfiles, savedSetup.profile)) setupProfile = savedSetup.profile;
  if (savedSetup.completed && typeof savedSetup.completed === 'object' && !Array.isArray(savedSetup.completed)) setupCompleted = savedSetup.completed;
} catch (_) { /* El configurador sigue funcionando si el almacenamiento local no está disponible. */ }

const themeLabels = {
  dracula: 'Carbón Dracula (Pastel)',
  violet: 'Violeta nocturno',
  cyberpunk: 'Aurora coral',
  matrix: 'Bosque menta',
  ocean: 'Océano boreal',
  amber: 'Ámbar cálido',
  pastel: 'Pastel nube'
};

// --- DOM Initializer ---
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSplitter();
  initNavigation();
  initInteractiveSurfaces();
  initSetupGuide();
  initProblemSolver();
  initLogAnalyzer();
  initResourceMonitor();
  initServiceManager();
  initBackupManager();
  renderCatalogCategories();
  initTelemetryLoop();
  initCyberGlobe();
  initEqualizerAnimation();
  document.getElementById('firstRunExplore')?.addEventListener('click', () => completeFirstRun(false));
  document.getElementById('firstRunConfigure')?.addEventListener('click', () => completeFirstRun(true));
  document.getElementById('codeProjectForm')?.addEventListener('submit', createCodeProject);
  document.getElementById('codeProjectSelect')?.addEventListener('change', event => selectCodeProject(event.target.value));
  document.getElementById('codePreviewButton')?.addEventListener('click', previewCodeChange);
  document.getElementById('codeAskAiButton')?.addEventListener('click', requestCodeChange);
  document.getElementById('codeInstruction')?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      requestCodeChange();
    }
  });
  document.getElementById('codeApplyButton')?.addEventListener('click', applyCodeChange);
  document.getElementById('codeRejectButton')?.addEventListener('click', rejectCodeChange);
  document.getElementById('devToggleDiffBtn')?.addEventListener('click', toggleDevDiffView);
  document.getElementById('devRunButton')?.addEventListener('click', runCodeInSandbox);
  document.getElementById('devSaveButton')?.addEventListener('click', saveActiveCodeFile);
  document.getElementById('devExportButton')?.addEventListener('click', exportActiveCodeProject);
  document.getElementById('devWhyFailedBtn')?.addEventListener('click', explainLastDevFailure);
  document.getElementById('devNewProjectTrigger')?.addEventListener('click', () => toggleCreateProjectBar('python'));
  document.getElementById('devTemplateTrigger')?.addEventListener('click', () => toggleCreateProjectBar('organizador_descargas'));
  document.getElementById('devTutorialTrigger')?.addEventListener('click', startGuidedDevTutorial);
  document.getElementById('devCancelCreateBtn')?.addEventListener('click', () => {
    const form = document.getElementById('codeProjectForm');
    if (form) form.hidden = true;
  });
  document.getElementById('devCloseTutorialBtn')?.addEventListener('click', () => {
    const banner = document.getElementById('devTutorialBanner');
    if (banner) banner.hidden = true;
  });
  document.getElementById('devCreateCheckpointBtn')?.addEventListener('click', createManualCheckpoint);
  document.getElementById('guideExplainInput')?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      runGuideExplanation();
    }
  });
  selectGuideExplanation('command');
  document.querySelectorAll('.dev-pill-prompt').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('codeInstruction');
      if (input) {
        input.value = btn.dataset.devPrompt || '';
        requestCodeChange();
      }
    });
  });

  window.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeToolWindow();
  });
  
  // Listen for pywebviewready event
  window.addEventListener('pywebviewready', () => {
    console.log("PyWebView Python API is ready!");
    updateTelemetry();
    loadInitialInfo();
  });
});

// ==========================================================================
// 1. THEME SWITCHER
// ==========================================================================
function initTheme() {
  if (!localStorage.getItem('linuxmate_carbon_default_v2')) {
    localStorage.setItem('linuxmate_theme', 'dracula');
    localStorage.setItem('linuxmate_carbon_default_v2', '1');
  }
  const savedTheme = localStorage.getItem('linuxmate_theme') || 'dracula';
  applyTheme(savedTheme);
  const select = document.getElementById('themeSelect');
  if (select) select.value = savedTheme;
}

function changeTheme(themeName) {
  applyTheme(themeName);
  localStorage.setItem('linuxmate_theme', themeName);
  showToast(`Tema aplicado: ${themeLabels[themeName] || themeName}`);
}

function applyTheme(themeName) {
  document.body.setAttribute('data-theme', themeName);
  document.body.classList.remove('theme-changing');
  void document.body.offsetWidth;
  document.body.classList.add('theme-changing');
  window.setTimeout(() => document.body.classList.remove('theme-changing'), 550);
}

function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      if (item.dataset.mainView === 'learning' || item.dataset.mainView === 'settings') return;
      navItems.forEach(navItem => navItem.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

function initInteractiveSurfaces() {
  const motionSelector = [
    '.action-card',
    '.status-card',
    '.progress-section',
    '.daily-tip',
    '.app-item',
    '.tool-app-row',
    '.command-row',
    '.uninstall-candidate'
  ].join(', ');
  const surfaces = document.querySelectorAll(`.glass-card, ${motionSelector}`);
  surfaces.forEach(surface => enhanceInteractiveSurface(surface, surface.matches(motionSelector)));

  window.addEventListener('pointermove', event => {
    if (pointerFrame) return;
    pointerFrame = window.requestAnimationFrame(() => {
      const x = ((event.clientX / window.innerWidth) - 0.5) * -14;
      const y = ((event.clientY / window.innerHeight) - 0.5) * -10;
      document.body.style.setProperty('--ambient-x', `${x}px`);
      document.body.style.setProperty('--ambient-y', `${y}px`);
      pointerFrame = null;
    });
  });
}

function enhanceInteractiveSurface(surface, allowMotion = true) {
  if (!surface || surface.dataset.interactiveBound === 'true') return;
  surface.dataset.interactiveBound = 'true';
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (allowMotion && !reduceMotion) surface.classList.add('motion-surface');

  surface.addEventListener('pointerenter', () => {
    if (allowMotion && !reduceMotion) surface.classList.add('is-pointed');
  });

  surface.addEventListener('pointermove', event => {
    const rect = surface.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    surface.style.setProperty('--shine-x', `${localX}px`);
    surface.style.setProperty('--shine-y', `${localY}px`);

    if (allowMotion && !reduceMotion) {
      const xRatio = localX / rect.width - 0.5;
      const yRatio = localY / rect.height - 0.5;
      surface.style.setProperty('--tilt-x', `${(-yRatio * 1.4).toFixed(2)}deg`);
      surface.style.setProperty('--tilt-y', `${(xRatio * 1.8).toFixed(2)}deg`);
    }
  });

  surface.addEventListener('pointerleave', () => {
    surface.classList.remove('is-pointed');
    surface.style.setProperty('--shine-x', '50%');
    surface.style.setProperty('--shine-y', '50%');
    surface.style.setProperty('--tilt-x', '0deg');
    surface.style.setProperty('--tilt-y', '0deg');
  });
}

function bindDynamic3DSurfaces(root = document) {
  const scope = root && typeof root.querySelectorAll === 'function' ? root : document;
  const selector = [
    '.learning-shortcut',
    '.cyber-widget-card',
    '.cyber-activity-card',
    '.cyber-stat-card',
    '.forecast-card',
    '.setup-hero',
    '.setup-system-card',
    '.setup-profile',
    '.setup-step',
    '.setup-driver-card',
    '.diagnostic-check',
    '.problem-guide-option',
    '.problem-guide-content',
    '.problem-repair-card',
    '.resource-metric-card',
    '.resource-detail-panel',
    '.service-card',
    '.backup-create-card',
    '.backup-timeshift-card',
    '.logs-insight-card',
    '.tool-app-row',
    '.command-row'
  ].join(', ');
  scope.querySelectorAll(selector).forEach(el => enhanceInteractiveSurface(el, true));
}

function showToast(message) {
  const region = document.getElementById('toastRegion');
  if (!region) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  region.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add('is-leaving');
    window.setTimeout(() => toast.remove(), 260);
  }, 2200);
}

// ==========================================================================
// 2. TOOL WORKSPACE
// ==========================================================================
function openToolWindow(actionId) {
  const overlay = document.getElementById('toolOverlay');
  if (!overlay) return;

  overlay.hidden = false;
  overlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('tool-window-open');
  openToolTab(actionId);
}

function closeToolWindow() {
  const overlay = document.getElementById('toolOverlay');
  if (!overlay || overlay.hidden) return;

  overlay.classList.add('is-closing');
  window.setTimeout(() => {
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden', 'true');
    overlay.classList.remove('is-closing');
    document.body.classList.remove('tool-window-open');
  }, 180);
}

function closeToolFromBackdrop(event) {
  if (event.target.id === 'toolOverlay') closeToolWindow();
}

function openToolTab(actionId) {
  if (!toolWorkspaceActions.has(actionId)) return;

  const copy = toolTabCopy[actionId];
  const title = document.getElementById('toolWindowTitle');
  const subtitle = document.getElementById('toolWindowSubtitle');
  if (title) title.textContent = copy[0];
  if (subtitle) subtitle.textContent = copy[1];

  document.querySelectorAll('.tool-tab').forEach(tab => {
    const selected = tab.dataset.toolTab === actionId;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-selected', selected ? 'true' : 'false');
  });

  document.querySelectorAll('.tool-view').forEach(view => {
    view.classList.toggle('active', view.dataset.toolView === actionId);
  });

  bindDynamic3DSurfaces(document.getElementById('toolOverlay') || document);

  if (actionId === 'install_programs' && !appCatalogState.loaded) {
    window.setTimeout(() => loadAppCatalog(true), 60);
  } else if (actionId === 'code_workspace') {
    window.setTimeout(() => loadCodeProjects(), 60);
  } else if (actionId === 'troubleshooter' && !diagnosticLoaded && !diagnosticLoading) {
    window.setTimeout(() => runTroubleshooter(), 60);
  } else if (actionId === 'resource_monitor') {
    window.setTimeout(() => loadResourceOverview(), 60);
  } else if (actionId === 'logs_analyzer') {
    window.setTimeout(() => loadSystemLogs(), 60);
  } else if (actionId === 'service_manager') {
    window.setTimeout(() => loadSystemServices(), 60);
  } else if (actionId === 'backup_manager') {
    window.setTimeout(() => loadBackupOverview(), 60);
  } else if (actionId === 'problem_solver') {
    window.setTimeout(() => loadProblemGuides(), 60);
  } else if (actionId === 'setup_guide') {
    renderSetupGuide();
    window.setTimeout(() => loadSetupOverview(), 60);
  } else if (actionId === 'uninstall_manager') {
    window.setTimeout(() => document.getElementById('uninstallQuery')?.focus(), 120);
  }
}

let setupDynamicPlan = null;
let setupStepResults = {};

function initSetupGuide() {
  document.querySelectorAll('[data-setup-profile]').forEach(button => {
    button.addEventListener('click', () => {
      setupProfile = button.dataset.setupProfile;
      persistSetupGuide();
      renderSetupGuide();
      loadSetupOverview();
    });
  });
  const list = document.getElementById('setupStepList');
  list?.addEventListener('click', event => {
    const button = event.target.closest('[data-setup-complete]');
    if (!button) return;
    const id = button.dataset.setupComplete;
    setupCompleted[id] = !setupCompleted[id];
    persistSetupGuide();
    renderSetupGuide();
  });
  bindDynamic3DSurfaces(document);
}

function persistSetupGuide() {
  try {
    localStorage.setItem(setupStorageKey, JSON.stringify({ profile: setupProfile, completed: setupCompleted }));
  } catch (_) {
    showToast('No se pudo guardar el avance de configuración en este equipo.');
  }
}

function renderSetupStepResult(stepId) {
  const result = setupStepResults[stepId];
  if (!result) return '';
  if (Array.isArray(result.driver_report) && result.driver_report.length) {
    const rows = result.driver_report.map(item => {
      const st = item.status === 'ok' ? 'ok' : 'warning';
      const kindRaw = String(item.kind || 'Dispositivo');
      const isGpu = /gpu|gr[aá]fic/i.test(kindRaw);
      const iconClass = isGpu ? 'icon-cpu' : 'icon-network';
      const statusText = st === 'ok' ? 'Controlador activo' : 'Revisión sugerida';
      return `<div class="setup-driver-card diagnostic-check diagnostic-${st}">
        <div class="setup-driver-head">
          <span class="setup-driver-cube" aria-hidden="true"><span class="ui-icon ${iconClass}"></span></span>
          <div class="setup-driver-meta">
            <span class="setup-driver-kind">${escapeHtml(kindRaw)}</span>
            <strong>${escapeHtml(String(item.device || ''))}</strong>
          </div>
          <span class="setup-driver-pill is-${st}">${statusText}</span>
        </div>
        <div class="setup-driver-foot">
          <span class="setup-driver-module-label">Módulo kernel</span>
          <code class="setup-driver-module">${escapeHtml(String(item.driver || ''))}</code>
        </div>
      </div>`;
    }).join('');
    const summaryMsg = result.message ? `<div class="setup-driver-banner"><span>✓</span><span>${escapeHtml(String(result.message))}</span></div>` : '';
    return `<div class="setup-step-inline-result setup-driver-showcase" role="status">${summaryMsg}<div class="setup-driver-grid">${rows}</div></div>`;
  }
  if (result.message) {
    return `<div class="setup-step-inline-result" role="status"><div class="setup-driver-banner"><span>✓</span><span>${escapeHtml(String(result.message))}</span></div></div>`;
  }
  return '';
}

function renderSetupGuide() {
  const fallbackProfile = setupProfiles[setupProfile] || setupProfiles.daily;
  const activeSteps = (setupDynamicPlan && setupDynamicPlan.profile === setupProfile && Array.isArray(setupDynamicPlan.steps))
    ? setupDynamicPlan.steps
    : fallbackProfile.steps;
  const profileTitle = (setupDynamicPlan && setupDynamicPlan.profile === setupProfile && setupDynamicPlan.profile_title)
    ? setupDynamicPlan.profile_title
    : fallbackProfile.title;
  const list = document.getElementById('setupStepList');
  if (!list) return;
  document.querySelectorAll('[data-setup-profile]').forEach(button => {
    const selected = button.dataset.setupProfile === setupProfile;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  const title = document.getElementById('setupPlanTitle');
  if (title) title.textContent = `Ruta para ${profileTitle}`;
  list.innerHTML = activeSteps.map((step, index) => {
    const done = setupCompleted[`${setupProfile}:${step.id}`] === true || step.status === 'ready_done';
    const attention = !done && step.status === 'attention';
    const key = `${setupProfile}:${step.id}`;
    const badgeHtml = step.badge ? `<span class="setup-done-label${attention ? ' is-attention' : ''}">${escapeHtml(String(step.badge))}</span>` : '';
    const cmdHtml = step.command ? `<div class="setup-step-cmd"><code>${escapeHtml(String(step.command))}</code></div>` : '';
    const inlineResultHtml = renderSetupStepResult(step.id);
    const secondaryHtml = step.secondaryAction
      ? `<button class="glass-btn glass-btn-secondary setup-open-action" type="button" onclick="openSetupTask('${escapeHtml(String(step.secondaryAction))}', '${escapeHtml(String(step.secondaryCategory || ''))}')">${escapeHtml(String(step.secondaryLabel || 'Ver herramienta'))}</button>`
      : '';
    return `<article class="setup-step${done ? ' is-complete' : ''}${attention ? ' is-attention' : ''}">
      <div class="setup-step-number" aria-hidden="true">${done ? '✓' : String(index + 1).padStart(2, '0')}</div>
      <div class="setup-step-copy"><div class="setup-step-title"><span class="setup-step-icon-cube"><span class="ui-icon icon-${escapeHtml(String(step.icon || 'settings'))}"></span></span><h5>${escapeHtml(String(step.title || 'Paso'))}</h5>${badgeHtml}${done ? '<span class="setup-done-label is-complete">Completado</span>' : ''}</div><p>${escapeHtml(String(step.detail || ''))}</p>${cmdHtml}${inlineResultHtml}</div>
      <div class="setup-step-actions"><button class="glass-btn glass-btn-secondary setup-open-action" type="button" onclick="openSetupTask('${escapeHtml(String(step.action || ''))}', '${escapeHtml(String(step.category || ''))}', '${escapeHtml(String(step.id || ''))}')">${escapeHtml(String(step.actionLabel || 'Continuar'))}<span aria-hidden="true"> →</span></button>${secondaryHtml}<button class="setup-check-button" type="button" data-setup-complete="${escapeHtml(key)}" aria-pressed="${done}" aria-label="${done ? 'Marcar como pendiente' : 'Marcar como completado'}: ${escapeHtml(String(step.title || ''))}">${done ? '✓ Listo' : 'Marcar listo'}</button></div>
    </article>`;
  }).join('');
  bindDynamic3DSurfaces(list);
  const completed = activeSteps.filter(step => setupCompleted[`${setupProfile}:${step.id}`] === true).length;
  const total = activeSteps.length;
  const percent = total ? Math.round(completed / total * 100) : 0;
  const progressLabel = document.getElementById('setupProgressLabel');
  const progressBar = document.getElementById('setupProgressBar');
  const progressFill = document.getElementById('setupProgressFill');
  if (progressLabel) progressLabel.textContent = `${completed} de ${total} pasos`;
  if (progressBar) progressBar.setAttribute('aria-valuenow', String(percent));
  if (progressFill) progressFill.style.width = `${percent}%`;
}

function resetSetupProgress() {
  const prefix = `${setupProfile}:`;
  Object.keys(setupCompleted).forEach(key => { if (key.startsWith(prefix)) delete setupCompleted[key]; });
  setupStepResults = {};
  persistSetupGuide();
  renderSetupGuide();
  showToast('Se reinició el avance de esta ruta.');
}

async function loadSetupOverview() {
  const name = document.getElementById('setupDistroName');
  const detail = document.getElementById('setupDistroDetail');
  if (!name || !detail) return;
  if (!window.pywebview?.api?.get_distro_info) {
    name.textContent = 'Vista de demostración';
    detail.textContent = 'La detección del equipo está disponible dentro de LinuxMate.';
    return;
  }
  name.textContent = 'Detectando distribución…';
  detail.textContent = 'Consultando gestor de paquetes, codecs, idioma y espacio libre';
  try {
    const [distro, stats, plan] = await Promise.all([
      window.pywebview.api.get_distro_info(),
      window.pywebview.api.get_system_stats(),
      window.pywebview.api.get_setup_plan ? window.pywebview.api.get_setup_plan(setupProfile) : Promise.resolve(null),
    ]);
    if (plan?.success) {
      setupDynamicPlan = plan;
      renderSetupGuide();
    }
    name.textContent = `${distro?.name || 'Distribución Linux'}${distro?.version ? ` ${distro.version}` : ''}`;
    const managers = Array.isArray(distro?.available_package_managers) ? distro.available_package_managers.join(', ') : '';
    const free = Number.isFinite(Number(stats?.disk_free_gb)) ? `${stats.disk_free_gb} GB libres` : 'espacio disponible no detectado';
    detail.textContent = `Gestor principal: ${distro?.package_manager || 'no detectado'}${managers ? ` · Disponibles: ${managers}` : ''} · ${free}`;
  } catch (_) {
    name.textContent = 'No se pudo detectar el equipo';
    detail.textContent = 'Puedes continuar con los pasos; la detección no modifica tu sistema.';
  }
}

async function openSetupTask(action, category, stepId) {
  let normalizedAction = typeof action === 'string' ? action.trim() : '';
  if (normalizedAction === 'drivers_manager' && stepId === 'drivers') {
    normalizedAction = 'run:check_drivers';
  } else if (normalizedAction === 'update_system' && stepId === 'updates') {
    normalizedAction = 'run:update_distro';
  }
  if (normalizedAction.startsWith('run:')) {
    const runId = normalizedAction.slice(4);
    if (window.pywebview?.api?.run_setup_action) {
      showToast(runId === 'check_drivers' ? 'Comprobando controladores gráficos y de red…' : 'Abriendo paso en terminal…');
      try {
        const res = await window.pywebview.api.run_setup_action(runId, setupProfile);
        showToast(res?.message || 'Paso ejecutado.');
        if (stepId && res) {
          setupStepResults[stepId] = res;
        }
        if (res?.success && stepId) {
          setupCompleted[`${setupProfile}:${stepId}`] = true;
          persistSetupGuide();
        }
        renderSetupGuide();
      } catch (err) {
        showToast(`No se pudo iniciar el paso: ${err}`);
      }
    } else {
      showToast('Esta acción requiere abrir LinuxMate en tu escritorio.');
    }
    return;
  }
  if (normalizedAction === 'apps') {
    appCatalogState.category = catalogCategoryLabels[category] ? category : 'all';
    appCatalogState.query = '';
    const catalogAlreadyLoaded = appCatalogState.loaded;
    const search = document.getElementById('catalogSearch');
    if (search) search.value = '';
    document.querySelectorAll('.catalog-category').forEach(button => {
      button.classList.toggle('active', button.dataset.catalogCategory === appCatalogState.category);
    });
    openTool('install_programs');
    if (catalogAlreadyLoaded) loadAppCatalog(true);
    return;
  }
  if (normalizedAction === 'academy') {
    openLearning();
    return;
  }
  openTool(normalizedAction);
}

function initProblemSolver() {
  const guideList = document.getElementById('problemGuideList');
  const content = document.getElementById('problemGuideContent');
  guideList?.addEventListener('click', event => {
    const button = event.target.closest('[data-problem-id]');
    if (button) selectProblemGuide(button.dataset.problemId);
  });
  content?.addEventListener('click', event => {
    if (event.target.closest('[data-problem-run]')) {
      runProblemChecks();
      return;
    }
    const repairButton = event.target.closest('[data-problem-repair]');
    if (repairButton) {
      executeProblemRepair(repairButton.dataset.problemRepair);
      return;
    }
    const actionButton = event.target.closest('[data-problem-action]');
    if (!actionButton) return;
    const action = actionButton.dataset.problemAction;
    if (action === 'install_programs' && actionButton.dataset.problemCategory) {
      openSetupTask('apps', actionButton.dataset.problemCategory);
    } else {
      openTool(action);
    }
  });
}

function initLogAnalyzer() {
  document.getElementById('logsQuery')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      loadSystemLogs();
    }
  });
}

let logsAnalyzerLoading = false;

async function loadSystemLogs() {
  if (logsAnalyzerLoading) return;
  const summary = document.getElementById('logsSummary');
  const insights = document.getElementById('logsInsights');
  const events = document.getElementById('logsEvents');
  const button = document.getElementById('loadSystemLogsButton');
  if (!summary || !insights || !events) return;

  const api = window.pywebview?.api;
  if (!api?.get_system_logs) {
    summary.textContent = 'Abre LinuxMate en Linux para consultar el journal local.';
    insights.replaceChildren();
    events.replaceChildren();
    return;
  }

  const priority = document.getElementById('logsPriority')?.value || 'err';
  const period = document.getElementById('logsPeriod')?.value || '24h';
  const source = document.getElementById('logsSource')?.value || 'system';
  const query = document.getElementById('logsQuery')?.value || '';
  logsAnalyzerLoading = true;
  if (button) {
    button.disabled = true;
    button.innerHTML = '<span class="loading-dots" aria-label="Analizando"><i></i><i></i><i></i></span> Analizando…';
  }
  summary.textContent = 'Consultando los registros locales…';
  insights.replaceChildren();
  events.replaceChildren();

  try {
    const response = await api.get_system_logs(priority, period, source, query);
    if (!response?.success) throw new Error(response?.message || 'No se pudieron consultar los registros.');
    renderSystemLogs(response);
  } catch (error) {
    summary.textContent = error?.message || 'No se pudieron consultar los registros. Vuelve a intentarlo.';
    insights.replaceChildren();
    events.replaceChildren();
  } finally {
    logsAnalyzerLoading = false;
    if (button) {
      button.disabled = false;
      button.innerHTML = '<span class="ui-icon icon-search"></span> Analizar registros';
    }
  }
}

function renderSystemLogs(response) {
  const summary = document.getElementById('logsSummary');
  const insights = document.getElementById('logsInsights');
  const events = document.getElementById('logsEvents');
  if (!summary || !insights || !events) return;

  const found = Array.isArray(response.events) ? response.events : [];
  const patterns = Array.isArray(response.insights) ? response.insights : [];
  const scanned = Number.isFinite(Number(response.scanned)) ? Number(response.scanned) : found.length;
  summary.textContent = found.length
    ? `${found.length} ${found.length === 1 ? 'registro coincide' : 'registros coinciden'}; se revisaron ${scanned} registros recientes.`
    : `No se encontraron coincidencias entre ${scanned} registros recientes. Prueba otro periodo, prioridad u origen.`;

  insights.innerHTML = patterns.map(pattern => `<article class="logs-insight-card">
    <span class="logs-insight-count">${escapeHtml(String(pattern.count || '0'))}</span>
    <div><h4>${escapeHtml(String(pattern.title || 'Patrón detectado'))}</h4><p>${escapeHtml(String(pattern.recommendation || ''))}</p></div>
  </article>`).join('');

  events.innerHTML = found.map(event => {
    const priority = String(event.priority || '7');
    const severityClass = ['0', '1', '2', '3'].includes(priority) ? 'error' : priority === '4' ? 'warning' : 'normal';
    const source = String(event.source || event.unit || 'Sistema');
    const unit = String(event.unit || '');
    return `<article class="logs-event logs-event-${severityClass}">
      <header class="logs-event-header"><span class="logs-severity-badge">${escapeHtml(String(event.severity || 'Registro'))}</span>
        <time>${escapeHtml(String(event.time || 'Hora desconocida'))}</time><span class="logs-event-source">${escapeHtml(source)}</span></header>
      ${unit && unit !== source ? `<div class="logs-event-unit">${escapeHtml(unit)}</div>` : ''}
      <p class="logs-event-message">${escapeHtml(String(event.message || '(sin mensaje)'))}</p>
    </article>`;
  }).join('');
}

function initResourceMonitor() {
  document.getElementById('resourceProcessSort')?.addEventListener('change', () => {
    if (resourceMonitorData) renderResourceOverview(resourceMonitorData);
  });
  document.getElementById('resourceProcessList')?.addEventListener('click', async event => {
    const button = event.target.closest('[data-stop-pid]');
    if (!button) return;
    const pid = Number(button.dataset.stopPid);
    const name = button.dataset.stopName || `PID ${pid}`;
    if (!pid || !window.confirm(`¿Deseas solicitar el cierre del proceso "${name}" (PID ${pid})?`)) return;
    button.disabled = true;
    try {
      const response = await window.pywebview?.api?.stop_user_process?.(pid);
      showToast(response?.message || 'Solicitud enviada al proceso.');
      if (response?.success) await loadResourceOverview();
    } catch (error) {
      showToast(`No se pudo finalizar el proceso: ${error}`);
    } finally {
      button.disabled = false;
    }
  });
  document.getElementById('resourceStartupList')?.addEventListener('click', async event => {
    const button = event.target.closest('[data-toggle-startup]');
    if (!button) return;
    const desktopId = button.dataset.toggleStartup;
    const nextEnabled = button.dataset.startupEnabled === 'true';
    button.disabled = true;
    try {
      const response = await window.pywebview?.api?.toggle_startup_app?.(desktopId, nextEnabled);
      showToast(response?.message || 'Preferencia de inicio actualizada.');
      if (response?.success && Array.isArray(response.startup_apps)) {
        if (resourceMonitorData) resourceMonitorData.startup_apps = response.startup_apps;
        renderResourceStartupApps(response.startup_apps);
      } else {
        await loadResourceOverview();
      }
    } catch (error) {
      showToast(`No se pudo cambiar el acceso de inicio: ${error}`);
    } finally {
      button.disabled = false;
    }
  });
  window.setInterval(() => {
    const overlay = document.getElementById('toolOverlay');
    const view = document.querySelector('[data-tool-view="resource_monitor"]');
    if (overlay && !overlay.hidden && view?.classList.contains('active')) loadResourceOverview();
  }, 5000);
}

async function loadResourceOverview() {
  if (resourceMonitorLoading) return;
  const api = window.pywebview?.api;
  const updated = document.getElementById('resourceUpdatedAt');
  const button = document.getElementById('refreshResourcesButton');
  if (!api?.get_resource_overview) {
    if (updated) updated.textContent = 'Abre LinuxMate en Linux para consultar métricas locales.';
    return;
  }
  resourceMonitorLoading = true;
  if (button) button.disabled = true;
  if (updated) updated.textContent = 'Actualizando lecturas…';
  try {
    const response = await api.get_resource_overview();
    if (!response?.success) throw new Error(response?.message || 'No se pudieron consultar los recursos.');
    resourceMonitorData = response;
    renderResourceOverview(response);
    const sampled = new Date(response.sampled_at);
    if (updated) updated.textContent = Number.isNaN(sampled.getTime())
      ? 'Lectura actualizada'
      : `Actualizado a las ${sampled.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} · se renueva cada 5 s`;
  } catch (error) {
    if (updated) updated.textContent = error?.message || 'No se pudieron consultar las métricas.';
    if (!resourceMonitorData) {
      ['resourceDiskList', 'resourceProcessList', 'resourceStartupList', 'resourceTemperatureList'].forEach(id => {
        const target = document.getElementById(id);
        if (target) target.innerHTML = `<div class="resource-panel-empty">${escapeHtml(error?.message || 'No se pudo obtener esta lectura.')}</div>`;
      });
    }
  } finally {
    resourceMonitorLoading = false;
    if (button) button.disabled = false;
  }
}

function renderResourceOverview(data) {
  const cpu = data.cpu || {};
  const memory = data.memory || {};
  const swap = data.swap || {};
  const battery = data.battery || {};
  const network = data.network || {};
  const cpuPercent = Number(cpu.percent);
  const memoryPercent = Number(memory.percent);
  const cpuValue = document.getElementById('resourceCpuValue');
  const cpuBar = document.getElementById('resourceCpuBar');
  if (cpuValue) cpuValue.innerHTML = `${Number.isFinite(cpuPercent) ? `${cpuPercent.toFixed(1)}<small>%</small>` : '—'}`;
  if (cpuBar) cpuBar.style.width = `${clampResourcePercent(cpuPercent)}%`;
  const cpuCores = document.getElementById('resourceCpuCores');
  if (cpuCores) cpuCores.textContent = `${Number(cpu.logical_cores) || 0} núcleos lógicos`;
  const cpuFrequency = document.getElementById('resourceCpuFrequency');
  if (cpuFrequency) cpuFrequency.textContent = cpu.frequency_mhz ? `${Math.round(Number(cpu.frequency_mhz))} MHz` : 'Frecuencia no disponible';
  const loads = Array.isArray(cpu.load_average) ? cpu.load_average.map(value => Number(value).toFixed(2)).join(' · ') : '';
  const cpuLoad = document.getElementById('resourceCpuLoad');
  if (cpuLoad) cpuLoad.textContent = loads ? `Carga 1 · 5 · 15 min: ${loads}` : 'Carga del sistema no disponible';

  const memoryValue = document.getElementById('resourceMemoryValue');
  const memoryBar = document.getElementById('resourceMemoryBar');
  if (memoryValue) memoryValue.innerHTML = `${Number.isFinite(memoryPercent) ? `${memoryPercent.toFixed(1)}<small>%</small>` : '—'}`;
  if (memoryBar) memoryBar.style.width = `${clampResourcePercent(memoryPercent)}%`;
  const memoryDetail = document.getElementById('resourceMemoryDetail');
  if (memoryDetail) memoryDetail.textContent = `${formatResourceBytes(memory.used_bytes)} de ${formatResourceBytes(memory.total_bytes)} usados`;
  const memoryFree = document.getElementById('resourceMemoryFree');
  if (memoryFree) memoryFree.textContent = `${formatResourceBytes(memory.available_bytes)} disponibles`;
  const swapDetail = document.getElementById('resourceSwapDetail');
  if (swapDetail) swapDetail.textContent = `Swap: ${formatResourceBytes(swap.used_bytes)} de ${formatResourceBytes(swap.total_bytes)} · ${Number(swap.percent || 0).toFixed(1)}%`;

  const download = document.getElementById('resourceDownloadRate');
  const upload = document.getElementById('resourceUploadRate');
  if (download) download.textContent = formatResourceRate(network.download_bytes_sec);
  if (upload) upload.textContent = formatResourceRate(network.upload_bytes_sec);
  const networkState = document.getElementById('resourceNetworkState');
  if (networkState) networkState.textContent = network.sampled ? 'Tráfico medido' : 'Midiendo primer intervalo…';
  const interfaces = document.getElementById('resourceInterfaceCount');
  if (interfaces) {
    const interfaceCount = Number(network.interfaces);
    interfaces.textContent = Number.isFinite(interfaceCount) ? `${interfaceCount} ${interfaceCount === 1 ? 'interfaz' : 'interfaces'}` : '— interfaces';
  }

  const batteryValue = document.getElementById('resourceBatteryValue');
  const batteryBar = document.getElementById('resourceBatteryBar');
  const batteryStatus = document.getElementById('resourceBatteryStatus');
  const batteryPlugged = document.getElementById('resourceBatteryPlugged');
  const batteryDetail = document.getElementById('resourceBatteryDetail');
  const batteryPercent = Number(battery.percent);
  if (battery.present && Number.isFinite(batteryPercent)) {
    if (batteryValue) batteryValue.innerHTML = `${batteryPercent.toFixed(0)}<small>%</small>`;
    if (batteryBar) batteryBar.style.width = `${clampResourcePercent(batteryPercent)}%`;
    if (batteryStatus) batteryStatus.textContent = String(battery.status || 'Detectada');
    if (batteryPlugged) batteryPlugged.textContent = battery.power_plugged ? 'En corriente' : 'En batería';
    if (batteryDetail) batteryDetail.textContent = String(battery.detail || 'Batería del sistema');
  } else {
    if (batteryValue) batteryValue.innerHTML = `<small>CA</small>`;
    if (batteryBar) batteryBar.style.width = '100%';
    if (batteryStatus) batteryStatus.textContent = String(battery.status || 'Corriente directa');
    if (batteryPlugged) batteryPlugged.textContent = 'Sin batería';
    if (batteryDetail) batteryDetail.textContent = String(battery.detail || 'Equipo de escritorio o sin batería detectada.');
  }

  renderResourceTemperatures(Array.isArray(data.temperatures) ? data.temperatures : []);
  renderResourceDisks(Array.isArray(data.disks) ? data.disks : []);
  renderResourceProcesses(data.processes || {});
  renderResourceStartupApps(Array.isArray(data.startup_apps) ? data.startup_apps : []);
  const processCount = document.getElementById('resourceProcessCount');
  if (processCount) processCount.textContent = `${Number(data.process_count) || 0} procesos activos. Puedes finalizar procesos iniciados por tu usuario.`;
}

function renderResourceTemperatures(readings) {
  const container = document.getElementById('resourceTemperatureList');
  if (!container) return;
  if (!readings.length) {
    container.innerHTML = '<div class="resource-temperature-empty"><span class="ui-icon icon-temperature"></span>Este equipo no expone sensores térmicos a LinuxMate.</div>';
    return;
  }
  container.innerHTML = readings.slice(0, 4).map(reading => {
    const value = Number(reading.celsius);
    const critical = Number(reading.critical);
    const high = Number(reading.high);
    const level = Number.isFinite(critical) && value >= critical ? 'critical' : Number.isFinite(high) && value >= high ? 'high' : 'normal';
    const label = String(reading.label || reading.sensor || 'Sensor');
    return `<div class="resource-temperature-row"><div><strong>${escapeHtml(label)}</strong><small>${escapeHtml(String(reading.sensor || 'Sensor térmico'))}</small></div><span class="resource-temp-value resource-temp-${level}">${Number.isFinite(value) ? `${value.toFixed(1)}°C` : '—'}</span></div>`;
  }).join('');
}

function renderResourceDisks(disks) {
  const list = document.getElementById('resourceDiskList');
  const count = document.getElementById('resourceDiskCount');
  if (!list || !count) return;
  count.textContent = `${disks.length} ${disks.length === 1 ? 'unidad' : 'unidades'}`;
  if (!disks.length) {
    list.innerHTML = '<div class="resource-panel-empty">No se encontraron unidades montadas que se puedan consultar.</div>';
    return;
  }
  list.innerHTML = disks.map(disk => {
    const percent = clampResourcePercent(Number(disk.percent));
    return `<article class="resource-disk-card"><div class="resource-disk-heading"><span class="resource-disk-icon"><span class="ui-icon icon-clean"></span></span><div><strong>${escapeHtml(String(disk.label || 'Unidad'))}</strong><small>${escapeHtml(String(disk.mountpoint || ''))} · ${escapeHtml(String(disk.filesystem || ''))}</small></div><span class="resource-disk-percent">${percent.toFixed(1)}%</span></div><div class="resource-meter resource-disk-meter"><span style="width:${percent}%"></span></div><div class="resource-disk-foot"><span>${formatResourceBytes(disk.used_bytes)} usados de ${formatResourceBytes(disk.total_bytes)}</span><strong>${formatResourceBytes(disk.free_bytes)} libres</strong></div></article>`;
  }).join('');
}

function renderResourceProcesses(processes) {
  const list = document.getElementById('resourceProcessList');
  if (!list) return;
  const sort = document.getElementById('resourceProcessSort')?.value === 'memory' ? 'top_memory' : 'top_cpu';
  const entries = Array.isArray(processes[sort]) ? processes[sort] : [];
  if (!entries.length) {
    list.innerHTML = '<div class="resource-panel-empty">No se pudieron leer procesos en esta sesión.</div>';
    return;
  }
  list.innerHTML = `<div class="resource-process-header"><span>Proceso</span><span>CPU</span><span>RAM</span><span>Control</span></div>${entries.map(process => {
    const name = String(process.name || 'Proceso sin nombre');
    const pid = Number(process.pid) || 0;
    const stopControl = process.can_stop && pid > 1
      ? `<button class="glass-btn glass-btn-secondary resource-control-btn" type="button" data-stop-pid="${pid}" data-stop-name="${escapeHtml(name)}">Finalizar</button>`
      : `<small class="resource-process-protected">Sistema</small>`;
    return `<div class="resource-process-row"><div class="resource-process-name"><strong>${escapeHtml(name)}</strong><small>PID ${pid || '—'}</small></div><span>${Number(process.cpu_percent || 0).toFixed(1)}%</span><span>${Number(process.memory_percent || 0).toFixed(1)}% <small>· ${formatResourceBytes(process.memory_bytes)}</small></span><span>${stopControl}</span></div>`;
  }).join('')}`;
}

function renderResourceStartupApps(apps) {
  const list = document.getElementById('resourceStartupList');
  const count = document.getElementById('resourceStartupCount');
  if (!list || !count) return;
  const enabled = apps.filter(app => app.enabled).length;
  count.textContent = `${enabled} activos · ${apps.length} detectados`;
  if (!apps.length) {
    list.innerHTML = '<div class="resource-panel-empty">No se encontraron accesos .desktop configurados para iniciar con la sesión.</div>';
    return;
  }
  list.innerHTML = apps.map(app => {
    const id = String(app.id || '');
    const toggleBtn = id
      ? `<button class="glass-btn glass-btn-secondary resource-control-btn" type="button" data-toggle-startup="${escapeHtml(id)}" data-startup-enabled="${!app.enabled}">${app.enabled ? 'Desactivar' : 'Activar'}</button>`
      : '';
    return `<div class="resource-startup-row"><span class="resource-startup-icon"><span class="ui-icon icon-package"></span></span><div><strong>${escapeHtml(String(app.name || 'Aplicación'))}</strong><small>${escapeHtml(String(app.scope || 'Sistema'))}</small></div><span class="resource-startup-state ${app.enabled ? 'is-enabled' : 'is-disabled'}">${app.enabled ? 'Se inicia' : 'Desactivada'}</span>${toggleBtn}</div>`;
  }).join('');
}

function clampResourcePercent(value) {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
}

function formatResourceBytes(value) {
  let bytes = Math.max(0, Number(value) || 0);
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let index = 0;
  while (bytes >= 1024 && index < units.length - 1) { bytes /= 1024; index += 1; }
  return `${bytes.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatResourceRate(value) {
  return value === null || value === undefined ? 'No disponible' : `${formatResourceBytes(value)}/s`;
}

function initServiceManager() {
  document.getElementById('serviceSearch')?.addEventListener('input', renderSystemServices);
  document.getElementById('serviceStateFilter')?.addEventListener('change', renderSystemServices);
  document.getElementById('serviceCardList')?.addEventListener('click', event => {
    const button = event.target.closest('[data-service-action]');
    if (button) manageSystemServiceFromView(button.dataset.serviceUnit, button.dataset.serviceAction);
  });
  document.getElementById('serviceSearch')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') loadSystemServices(true);
  });
}

async function loadSystemServices() {
  if (systemServicesLoading) return;
  const cards = document.getElementById('serviceCardList');
  const count = document.getElementById('serviceCount');
  const status = document.getElementById('serviceActionStatus');
  const button = document.getElementById('refreshServicesButton');
  const api = window.pywebview?.api;
  if (!cards || !count) return;
  if (!api?.get_service_overview) {
    count.textContent = 'Solo disponible en Linux';
    cards.innerHTML = '<div class="service-empty-state"><span class="ui-icon icon-settings"></span>Abre LinuxMate en Linux para consultar los servicios del sistema.</div>';
    return;
  }

  systemServicesLoading = true;
  if (button) button.disabled = true;
  count.textContent = 'Actualizando…';
  if (status) status.textContent = 'Consultando el estado actual de systemd…';
  if (!systemServices.length) cards.innerHTML = '<div class="service-empty-state"><span class="ui-icon icon-sync"></span>Consultando los servicios systemd…</div>';
  try {
    const response = await api.get_service_overview();
    if (!response?.success) throw new Error(response?.message || 'No se pudo consultar systemd.');
    systemServiceError = '';
    systemServices = Array.isArray(response.services) ? response.services : [];
    renderSystemServices();
    const serviceTotal = Number(response.total) || systemServices.length;
    if (status) status.textContent = response.limited
      ? `Se muestran ${systemServices.length} de ${serviceTotal} servicios. Usa la búsqueda para acotar la lista.`
      : `${serviceTotal} ${serviceTotal === 1 ? 'servicio disponible' : 'servicios disponibles'}. La consulta no hizo cambios.`;
  } catch (error) {
    systemServices = [];
    systemServiceError = error?.message || 'No se pudo consultar systemd. Comprueba que LinuxMate se esté ejecutando en Linux con systemd.';
    count.textContent = 'No disponible';
    cards.innerHTML = `<div class="service-empty-state service-empty-error"><span class="ui-icon icon-shield"></span>${escapeHtml(systemServiceError)}</div>`;
    if (status) status.textContent = 'No se pudo actualizar el estado de los servicios.';
  } finally {
    systemServicesLoading = false;
    if (button) button.disabled = false;
    renderSystemServices();
  }
}

function renderSystemServices() {
  const cards = document.getElementById('serviceCardList');
  const count = document.getElementById('serviceCount');
  if (!cards || !count) return;
  if (systemServiceError) {
    count.textContent = 'No disponible';
    cards.innerHTML = `<div class="service-empty-state service-empty-error"><span class="ui-icon icon-shield"></span>${escapeHtml(systemServiceError)}</div>`;
    return;
  }
  const query = String(document.getElementById('serviceSearch')?.value || '').trim().toLocaleLowerCase();
  const filter = document.getElementById('serviceStateFilter')?.value || 'all';
  const filtered = systemServices.filter(service => {
    const matchesQuery = !query || `${service.unit || ''} ${service.description || ''}`.toLocaleLowerCase().includes(query);
    const matchesState = filter === 'all'
      || filter === service.active
      || (filter === 'enabled' && String(service.startup || '').startsWith('enabled'))
      || (filter === 'disabled' && service.startup === 'disabled');
    return matchesQuery && matchesState;
  });
  count.textContent = `${filtered.length} de ${systemServices.length} ${systemServices.length === 1 ? 'servicio' : 'servicios'}`;
  if (!systemServices.length) {
    cards.innerHTML = '<div class="service-empty-state"><span class="ui-icon icon-settings"></span>No hay servicios para mostrar.</div>';
    return;
  }
  if (!filtered.length) {
    cards.innerHTML = '<div class="service-empty-state"><span class="ui-icon icon-search"></span>No encontré servicios con esos filtros. Prueba otro nombre o estado.</div>';
    return;
  }

  const stateLabels = { active: 'En ejecución', inactive: 'Detenido', failed: 'Fallido', activating: 'Iniciando', deactivating: 'Deteniéndose', reloading: 'Actualizando' };
  const startupLabels = { enabled: 'Inicio automático', 'enabled-runtime': 'Inicio automático (sesión actual)', disabled: 'Inicio manual', static: 'Gestionado por systemd', masked: 'Bloqueado', generated: 'Generado', indirect: 'Activado por dependencia', linked: 'Enlazado', alias: 'Alias de otro servicio' };
  const actionLabels = { start: 'Iniciar', stop: 'Detener', restart: 'Reiniciar', enable: 'Activar inicio', disable: 'Quitar inicio' };
  cards.innerHTML = filtered.map(service => {
    const unit = String(service.unit || '');
    const active = String(service.active || 'unknown');
    const startup = String(service.startup || 'unknown');
    const critical = Boolean(service.critical);
    const escapedUnitName = /\\x[0-9a-f]{2}/i.test(unit);
    const stateClass = ['active', 'inactive', 'failed'].includes(active) ? active : 'other';
    const actions = [];
    if (!escapedUnitName && startup !== 'masked' && startup !== 'alias') {
      if (active === 'active') {
        if (!critical) actions.push('stop', 'restart');
      } else if (active === 'inactive' || active === 'failed') {
        actions.push('start');
      }
      if (startup.startsWith('enabled') && !critical) actions.push('disable');
      else if (startup === 'disabled') actions.push('enable');
    }
    const buttons = actions.map(action => `<button class="service-action-button service-action-${action}" type="button" data-service-action="${action}" data-service-unit="${escapeHtml(unit)}"${systemServiceActionRunning || systemServicesLoading ? ' disabled' : ''}>${serviceActionIcon(action)}${actionLabels[action]}</button>`).join('');
    return `<article class="service-card">
      <div class="service-card-icon"><span class="ui-icon icon-settings"></span></div>
      <div class="service-card-main">
        <div class="service-card-heading"><h4>${escapeHtml(String(service.description || unit))}</h4><span class="service-state-badge service-state-${stateClass}">${escapeHtml(stateLabels[active] || active)}</span></div>
        <code class="service-unit-name">${escapeHtml(unit)}</code>
        <div class="service-card-meta"><span><i class="service-meta-dot service-meta-${stateClass}"></i>${escapeHtml(String(service.sub || 'estado desconocido'))}</span><span class="service-startup-badge">${escapeHtml(startupLabels[startup] || startup)}</span></div>
        ${critical ? '<p class="service-critical-hint"><span class="ui-icon icon-shield"></span>Protegido por LinuxMate para cuidar el inicio y la conectividad.</p>' : ''}
      </div>
      <div class="service-card-actions">${buttons || `<span class="service-no-actions">${escapedUnitName ? 'Nombre escapado · solo lectura' : 'Sin acciones disponibles'}</span>`}</div>
    </article>`;
  }).join('');
}

function serviceActionIcon(action) {
  const icons = { start: 'icon-pulse', stop: 'icon-close', restart: 'icon-sync', enable: 'icon-shield', disable: 'icon-close' };
  return `<span class="ui-icon ${icons[action] || 'icon-settings'}" aria-hidden="true"></span>`;
}

async function manageSystemServiceFromView(unit, action) {
  if (systemServiceActionRunning || !unit || !action) return;
  const actionLabels = { start: 'iniciar', stop: 'detener', restart: 'reiniciar', enable: 'activar el inicio automático de', disable: 'quitar el inicio automático de' };
  const context = {
    start: 'El servicio comenzará ahora y puede activar funciones relacionadas.',
    stop: 'El servicio dejará de funcionar hasta que vuelva a iniciarse.',
    restart: 'El servicio se detendrá brevemente y volverá a iniciarse.',
    enable: 'El servicio también intentará iniciarse automáticamente al arrancar el equipo.',
    disable: 'El servicio dejará de iniciarse automáticamente cuando enciendas el equipo.'
  };
  const label = actionLabels[action];
  if (!label || !window.confirm(`¿Quieres ${label} «${unit}»?\n\n${context[action]} LinuxMate solicitará autorización del sistema.`)) return;

  const status = document.getElementById('serviceActionStatus');
  systemServiceActionRunning = true;
  if (status) status.textContent = `Solicitando autorización para ${label} «${unit}»…`;
  renderSystemServices();
  try {
    const api = window.pywebview?.api;
    if (!api?.manage_system_service) throw new Error('El control de servicios no está disponible en esta sesión de LinuxMate.');
    const response = await api.manage_system_service(unit, action, true);
    if (!response?.success) {
      if (status) status.textContent = response?.message || 'No se aplicó ningún cambio.';
      return;
    }
    if (status) status.textContent = response.message || 'La operación terminó.';
    if (response.refresh !== false) {
      await loadSystemServices();
      if (status) status.textContent = response.message || 'La operación terminó y se actualizó la lista.';
    }
  } catch (error) {
    if (status) status.textContent = error?.message || 'No se pudo ejecutar la operación.';
  } finally {
    systemServiceActionRunning = false;
    renderSystemServices();
  }
}

function initBackupManager() {
  const sourceChoices = document.getElementById('backupSourceChoices');
  sourceChoices?.addEventListener('change', event => {
    const checkbox = event.target.closest('[data-backup-source]');
    if (!checkbox) return;
    if (checkbox.checked) backupSelectedSources.add(checkbox.dataset.backupSource);
    else backupSelectedSources.delete(checkbox.dataset.backupSource);
    updateBackupCreateButton();
  });
  sourceChoices?.addEventListener('click', async event => {
    const removeButton = event.target.closest('[data-remove-backup-source]');
    if (!removeButton) return;
    const sourceId = removeButton.dataset.removeBackupSource;
    try {
      const response = await window.pywebview.api.remove_custom_backup_source(sourceId);
      if (!response?.success) throw new Error(response?.message || 'No se quitó la carpeta.');
      customBackupSources = customBackupSources.filter(source => source.id !== sourceId);
      backupSelectedSources.delete(sourceId);
      renderBackupSourceChoices();
    } catch (error) {
      document.getElementById('backupTaskStatus').textContent = error.message || 'No se quitó la carpeta.';
    }
  });
  document.getElementById('chooseBackupDestinationButton')?.addEventListener('click', chooseBackupDestination);
  document.getElementById('addBackupFolderButton')?.addEventListener('click', addCustomBackupFolder);
  document.getElementById('createPersonalBackupButton')?.addEventListener('click', createPersonalBackup);
  document.getElementById('refreshBackupsButton')?.addEventListener('click', loadBackupOverview);
  document.getElementById('openTimeshiftButton')?.addEventListener('click', openTimeshiftManager);
  document.getElementById('timeshiftInstallButton')?.addEventListener('click', findTimeshiftInCatalog);
  document.getElementById('backupHistoryList')?.addEventListener('click', event => {
    const button = event.target.closest('[data-backup-preview]');
    if (button) previewPersonalBackup(button.dataset.backupPreview);
  });
  document.getElementById('backupRestorePreview')?.addEventListener('click', event => {
    if (event.target.closest('[data-backup-cancel-preview]')) {
      document.getElementById('backupRestorePreview').hidden = true;
      return;
    }
    const button = event.target.closest('[data-backup-confirm-restore]');
    if (button) restorePersonalBackup(button.dataset.backupConfirmRestore);
  });
}

async function loadBackupOverview() {
  if (backupOverviewLoading) return;
  const sourceList = document.getElementById('backupSourceChoices');
  const history = document.getElementById('backupHistoryList');
  if (!sourceList || !history) return;
  const api = window.pywebview?.api;
  if (!api?.get_backup_overview) {
    sourceList.innerHTML = '<div class="backup-empty-state">Abre LinuxMate en Linux para consultar las carpetas locales.</div>';
    history.innerHTML = '<div class="backup-empty-state">Los respaldos se administran desde la aplicación de LinuxMate.</div>';
    return;
  }
  backupOverviewLoading = true;
  try {
    const response = await api.get_backup_overview();
    if (!response?.success) throw new Error(response?.message || 'No se pudo cargar la información de respaldos.');
    backupSources = Array.isArray(response.sources) ? response.sources : [];
    renderBackupSourceChoices();
    renderBackupHistory(Array.isArray(response.backups) ? response.backups : []);
    const timeshiftStatus = document.getElementById('timeshiftStatus');
    const openButton = document.getElementById('openTimeshiftButton');
    const installButton = document.getElementById('timeshiftInstallButton');
    if (timeshiftStatus) timeshiftStatus.textContent = response.timeshift_available
      ? 'Timeshift está instalado. Puedes revisar snapshots y confirmar la creación o restauración desde su interfaz.'
      : response.timeshift_installed
        ? 'Timeshift está instalado, pero no encontramos su interfaz gráfica. Revisa el menú de aplicaciones.'
        : 'Timeshift no está instalado. Puedes buscarlo en el catálogo de aplicaciones.';
    if (openButton) openButton.hidden = !response.timeshift_available;
    if (installButton) installButton.hidden = Boolean(response.timeshift_available || response.timeshift_installed);
  } catch (error) {
    sourceList.innerHTML = `<div class="backup-empty-state">${escapeHtml(error.message || 'No se pudo cargar la información.')}</div>`;
    history.innerHTML = '<div class="backup-empty-state">Vuelve a cargar para consultar tus respaldos.</div>';
  } finally {
    backupOverviewLoading = false;
  }
}

function renderBackupSourceChoices() {
  const container = document.getElementById('backupSourceChoices');
  if (!container) return;
  const sources = [...backupSources, ...customBackupSources];
  if (!sources.length) {
    container.innerHTML = '<div class="backup-empty-state">No encontré carpetas comunes. Añade una carpeta dentro de tu carpeta personal.</div>';
    updateBackupCreateButton();
    return;
  }
  container.innerHTML = sources.map(source => {
    const id = String(source.id || '');
    const checked = backupSelectedSources.has(id);
    const isCustom = id.startsWith('custom:');
    return `<div class="backup-source-option">
      <input class="backup-source-checkbox" type="checkbox" id="backup-source-${escapeHtml(id)}" data-backup-source="${escapeHtml(id)}"${checked ? ' checked' : ''}>
      <span class="backup-source-icon"><span class="ui-icon icon-doc"></span></span>
      <label class="backup-source-text" for="backup-source-${escapeHtml(id)}"><strong>${escapeHtml(String(source.name || 'Carpeta personal'))}</strong><small>${escapeHtml(String(source.path || ''))}</small></label>
      ${isCustom ? `<button class="backup-source-remove" type="button" data-remove-backup-source="${escapeHtml(id)}" aria-label="Quitar ${escapeHtml(String(source.name || 'la carpeta'))}" title="Quitar carpeta">×</button>` : '<span class="backup-source-check" aria-hidden="true">✓</span>'}
    </div>`;
  }).join('');
  updateBackupCreateButton();
}

function renderBackupHistory(backups) {
  const list = document.getElementById('backupHistoryList');
  if (!list) return;
  if (!backups.length) {
    list.innerHTML = '<div class="backup-empty-state"><span class="ui-icon icon-backup"></span><strong>Aún no tienes respaldos de LinuxMate</strong><span>Elige tus carpetas y guarda la primera copia en otra ubicación.</span></div>';
    return;
  }
  list.innerHTML = backups.map(backup => {
    const id = String(backup.id || '');
    const folders = Array.isArray(backup.folders) ? backup.folders.map(String).join(' · ') : 'Carpetas personales';
    return `<article class="backup-history-card">
      <span class="backup-history-icon"><span class="ui-icon icon-backup"></span></span>
      <div class="backup-history-info"><strong>${escapeHtml(formatBackupDate(backup.created_at))}</strong><span>${escapeHtml(folders)}</span><small>${escapeHtml(String(backup.file_count || 0))} archivos · ZIP ${escapeHtml(formatBackupSize(backup.size))} · originales ${escapeHtml(formatBackupSize(backup.source_bytes))}</small><small class="backup-history-path">${escapeHtml(String(backup.path || ''))}</small></div>
      <button class="glass-btn glass-btn-secondary backup-preview-button" type="button" data-backup-preview="${escapeHtml(id)}"><span class="ui-icon icon-eye"></span> Revisar</button>
    </article>`;
  }).join('');
}

function formatBackupDate(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Fecha desconocida' : parsed.toLocaleString();
}

function formatBackupSize(value) {
  let size = Math.max(0, Number(value) || 0);
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function updateBackupCreateButton() {
  const button = document.getElementById('createPersonalBackupButton');
  if (!button) return;
  button.disabled = !backupDestination || backupSelectedSources.size === 0 || Boolean(backupTaskId);
}

async function chooseBackupDestination() {
  const status = document.getElementById('backupTaskStatus');
  try {
    const response = await window.pywebview.api.choose_backup_destination();
    if (!response?.success) {
      if (!response?.cancelled && status) status.textContent = response?.message || 'No se pudo elegir el destino.';
      return;
    }
    backupDestination = String(response.path || '');
    const label = document.getElementById('backupDestinationLabel');
    if (label) label.textContent = backupDestination;
    if (status) status.textContent = 'Destino listo. Selecciona las carpetas que quieres incluir.';
    updateBackupCreateButton();
  } catch (error) {
    if (status) status.textContent = error.message || 'No se pudo abrir el selector de carpetas.';
  }
}

async function addCustomBackupFolder() {
  try {
    const response = await window.pywebview.api.choose_custom_backup_source();
    if (!response?.success) {
      if (!response?.cancelled) document.getElementById('backupTaskStatus').textContent = response?.message || 'No se añadió la carpeta.';
      return;
    }
    const source = response.source;
    if (!source?.id || customBackupSources.some(item => item.id === source.id)) return;
    customBackupSources.push(source);
    backupSelectedSources.add(source.id);
    renderBackupSourceChoices();
    document.getElementById('backupTaskStatus').textContent = `Añadida: ${source.name}. Elige el destino cuando estés listo.`;
  } catch (error) {
    document.getElementById('backupTaskStatus').textContent = error.message || 'No se pudo añadir la carpeta.';
  }
}

async function createPersonalBackup() {
  const status = document.getElementById('backupTaskStatus');
  const selected = Array.from(document.querySelectorAll('[data-backup-source]:checked')).map(input => input.dataset.backupSource);
  if (!backupDestination || !selected.length) {
    if (status) status.textContent = 'Elige al menos una carpeta y un destino.';
    return;
  }
  try {
    const response = await window.pywebview.api.start_personal_backup(selected, backupDestination);
    if (!response?.success) throw new Error(response?.message || 'No se pudo iniciar el respaldo.');
    const selectedCustom = new Set(selected.filter(id => id.startsWith('custom:')));
    customBackupSources = customBackupSources.filter(source => !selectedCustom.has(source.id));
    selectedCustom.forEach(id => backupSelectedSources.delete(id));
    renderBackupSourceChoices();
    startBackupTaskPolling(response.task_id);
  } catch (error) {
    if (status) status.textContent = error.message || 'No se pudo iniciar el respaldo.';
  }
}

async function previewPersonalBackup(backupId) {
  const preview = document.getElementById('backupRestorePreview');
  if (!preview) return;
  preview.hidden = false;
  preview.textContent = 'Revisando el contenido…';
  try {
    const response = await window.pywebview.api.preview_backup_restore(backupId);
    if (!response?.success) throw new Error(response?.message || 'No se pudo leer el respaldo.');
    const sample = Array.isArray(response.sample) && response.sample.length
      ? `<ul>${response.sample.map(path => `<li><code>${escapeHtml(String(path))}</code></li>`).join('')}</ul>`
      : '<p>El respaldo no contiene archivos para restaurar.</p>';
    preview.innerHTML = `<div class="backup-preview-content"><div><span class="eyebrow">Revisión antes de restaurar</span><h4>${escapeHtml(formatBackupDate(response.created_at))}</h4><p>${escapeHtml(String(response.file_count || 0))} archivos · ${escapeHtml(formatBackupSize(response.source_bytes))} originales · ZIP ${escapeHtml(formatBackupSize(response.size))}. Se copiarán a una carpeta nueva dentro de <code>~/Restauraciones-LinuxMate</code>; no reemplazarán archivos actuales.</p>${sample}</div><div class="backup-preview-actions"><button class="glass-btn" type="button" data-backup-confirm-restore="${escapeHtml(String(response.id))}"><span class="ui-icon icon-backup"></span> Restaurar en carpeta nueva</button><button class="glass-btn glass-btn-secondary" type="button" data-backup-cancel-preview>Cerrar</button></div></div>`;
  } catch (error) {
    preview.textContent = error.message || 'No se pudo revisar este respaldo.';
  }
}

async function restorePersonalBackup(backupId) {
  const target = '~/Restauraciones-LinuxMate/ (se creará una carpeta nueva)';
  if (!window.confirm(`Se extraerá esta copia en ${target}. Tus archivos actuales no se reemplazarán. ¿Continuar?`)) return;
  try {
    const response = await window.pywebview.api.start_backup_restore(backupId);
    if (!response?.success) throw new Error(response?.message || 'No se pudo iniciar la restauración.');
    startBackupTaskPolling(response.task_id);
  } catch (error) {
    document.getElementById('backupTaskStatus').textContent = error.message || 'No se pudo iniciar la restauración.';
  }
}

async function startBackupTaskPolling(taskId) {
  backupTaskId = taskId;
  const status = document.getElementById('backupTaskStatus');
  const progress = document.getElementById('backupProgressTrack');
  const fill = document.getElementById('backupProgressFill');
  if (progress) progress.hidden = false;
  updateBackupCreateButton();
  while (backupTaskId === taskId) {
    try {
      const response = await window.pywebview.api.get_backup_task(taskId);
      if (!response?.success) throw new Error(response?.message || 'Se perdió el estado de la operación.');
      const task = response.task;
      if (status) status.textContent = task.message || 'Procesando respaldo…';
      if (fill) fill.style.width = `${Math.max(0, Math.min(100, Number(task.progress) || 0))}%`;
      if (task.status === 'complete') {
        const resultPath = task.result?.path || '';
        if (status) status.textContent = task.kind === 'restore'
          ? `Restauración lista en ${resultPath || '~/Restauraciones-LinuxMate'}. No se sobrescribió ningún archivo.`
          : `Respaldo creado en ${resultPath || backupDestination}.`;
        backupTaskId = '';
        updateBackupCreateButton();
        if (progress) progress.hidden = true;
        await loadBackupOverview();
        return;
      }
      if (task.status === 'failed') {
        if (status) status.textContent = task.error || task.message || 'La operación no se pudo completar.';
        backupTaskId = '';
        updateBackupCreateButton();
        if (progress) progress.hidden = true;
        return;
      }
    } catch (error) {
      if (status) status.textContent = error.message || 'No se pudo consultar el progreso.';
      backupTaskId = '';
      updateBackupCreateButton();
      if (progress) progress.hidden = true;
      return;
    }
    await new Promise(resolve => window.setTimeout(resolve, 700));
  }
}

async function openTimeshiftManager() {
  const status = document.getElementById('timeshiftStatus');
  try {
    const response = await window.pywebview.api.open_timeshift();
    if (status) status.textContent = response?.message || 'No se pudo abrir Timeshift.';
  } catch (error) {
    if (status) status.textContent = error.message || 'No se pudo abrir Timeshift.';
  }
}

function findTimeshiftInCatalog() {
  appCatalogState.source = 'all';
  appCatalogState.category = 'system';
  appCatalogState.query = 'timeshift';
  const search = document.getElementById('catalogSearch');
  if (search) search.value = 'timeshift';
  document.querySelectorAll('.catalog-source').forEach(button => button.classList.toggle('active', button.dataset.catalogSource === 'all'));
  document.querySelectorAll('.catalog-category').forEach(button => button.classList.toggle('active', button.dataset.catalogCategory === 'system'));
  openTool('install_programs');
  window.setTimeout(() => loadAppCatalog(true), 80);
}

async function loadProblemGuides() {
  if (problemGuidesLoaded) {
    if (!selectedProblemId && problemGuides.length) selectProblemGuide(problemGuides[0].id);
    return;
  }
  const list = document.getElementById('problemGuideList');
  if (!list) return;
  if (!window.pywebview?.api?.get_problem_guides) {
    list.innerHTML = '<div class="problem-guide-unavailable">Abre LinuxMate en Linux para cargar las guías y comprobar el equipo.</div>';
    return;
  }
  try {
    const response = await window.pywebview.api.get_problem_guides();
    if (!response?.success || !Array.isArray(response.guides)) throw new Error(response?.message || 'No se pudo cargar el catálogo.');
    problemGuides = response.guides;
    problemGuidesLoaded = true;
    list.innerHTML = problemGuides.map(guide => `<button class="problem-guide-option" type="button" data-problem-id="${escapeHtml(guide.id)}" aria-pressed="false"><span class="ui-icon icon-${escapeHtml(guide.icon)}"></span><span><strong>${escapeHtml(guide.title)}</strong><small>${escapeHtml(guide.summary)}</small></span><span class="problem-guide-chevron" aria-hidden="true">›</span></button>`).join('');
    if (problemGuides.length) selectProblemGuide(problemGuides[0].id);
  } catch (error) {
    list.innerHTML = `<div class="problem-guide-unavailable">${escapeHtml(error.message || 'No se pudieron cargar las soluciones.')}</div>`;
  }
}

function selectProblemGuide(issueId) {
  const guide = problemGuides.find(item => item.id === issueId);
  if (!guide) return;
  selectedProblemId = guide.id;
  problemCheckResults = [];
  document.querySelectorAll('[data-problem-id]').forEach(button => {
    const selected = button.dataset.problemId === selectedProblemId;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  renderProblemGuide(guide);
}

function renderProblemGuide(guide) {
  const content = document.getElementById('problemGuideContent');
  if (!content) return;
  const steps = Array.isArray(guide.steps) ? guide.steps : [];
  const input = guide.input ? `<div class="problem-input-wrap"><label for="${escapeHtml(guide.input.id)}">${escapeHtml(guide.input.label)}</label><input class="glass-input" id="${escapeHtml(guide.input.id)}" type="text" maxlength="240" placeholder="${escapeHtml(guide.input.placeholder || '')}" autocomplete="off"><small>El dato se usa solo para esta comprobación local.</small></div>` : '';
  const allActions = Array.isArray(guide.actions) ? guide.actions : [];
  const repairActions = allActions
    .filter(action => action.kind === 'repair')
    .map(action => `<div class="problem-repair-card"><div><strong>${escapeHtml(action.label)}</strong>${action.description ? `<small>${escapeHtml(action.description)}</small>` : ''}</div><button class="glass-btn" type="button" data-problem-repair="${escapeHtml(action.id)}">${escapeHtml(action.label)}</button></div>`)
    .join('');
  const toolActions = allActions
    .filter(action => action.kind !== 'repair')
    .map(action => `<button class="glass-btn glass-btn-secondary" type="button" data-problem-action="${escapeHtml(action.id)}"${action.category ? ` data-problem-category="${escapeHtml(action.category)}"` : ''}>${escapeHtml(action.label)} <span aria-hidden="true">→</span></button>`)
    .join('');
  content.innerHTML = `<header class="problem-detail-heading"><span class="problem-detail-icon"><span class="ui-icon icon-${escapeHtml(guide.icon)}"></span></span><div><span class="eyebrow">Problema seleccionado</span><h4>${escapeHtml(guide.title)}</h4><p>${escapeHtml(guide.summary)}</p></div></header>
    <div class="problem-instructions"><h5>Prueba estos pasos</h5><ol>${steps.map(step => `<li>${escapeHtml(step)}</li>`).join('')}</ol></div>
    ${input}
    <div class="problem-check-actions"><div><strong>Comprobaciones del equipo</strong><small>Lecturas locales; no se cambiará ninguna configuración.</small></div><button class="glass-btn" type="button" data-problem-run ${problemCheckRunning ? 'disabled' : ''}><span class="ui-icon icon-pulse"></span> ${problemCheckRunning ? 'Analizando…' : 'Analizar este problema'}</button></div>
    <div class="problem-check-status" id="problemCheckStatus" role="status">${problemCheckResults.length ? 'Último análisis de este problema:' : 'Elige cuándo ejecutar las comprobaciones.'}</div>
    <div class="diagnostic-list problem-check-results" id="problemCheckResults">${renderProblemCheckResults(problemCheckResults)}</div>
    ${repairActions ? `<div class="problem-next-actions"><h5>Acciones guiadas de reparación</h5><div class="problem-repair-list">${repairActions}</div></div>` : ''}
    ${toolActions ? `<div class="problem-next-actions"><h5>Herramientas relacionadas</h5><div>${toolActions}</div></div>` : ''}`;
}

async function executeProblemRepair(actionId) {
  if (!actionId) return;
  const guide = problemGuides.find(item => item.id === selectedProblemId);
  const action = (guide?.actions || []).find(item => item.id === actionId);
  const promptText = action?.description
    ? `${action.label}\n\n${action.description}\n\n¿Deseas continuar?`
    : `¿Deseas ejecutar "${action?.label || actionId}"?`;
  if (!window.confirm(promptText)) return;
  const status = document.getElementById('problemCheckStatus');
  if (status) status.textContent = 'Ejecutando acción guiada…';
  try {
    const response = await window.pywebview?.api?.run_problem_action?.(actionId);
    const message = response?.message || 'Acción ejecutada.';
    if (status) status.textContent = message;
    showToast(message);
  } catch (error) {
    const errMsg = error?.message || String(error);
    if (status) status.textContent = `No se pudo ejecutar la acción: ${errMsg}`;
    showToast(`Error: ${errMsg}`);
  }
}

function renderProblemCheckResults(results) {
  return results.map(result => {
    const status = ['ok', 'warning', 'unknown'].includes(result.status) ? result.status : 'unknown';
    const label = {ok: 'Correcto', warning: 'Revisar', unknown: 'Sin dato'}[status];
    const symbol = {ok: '✓', warning: '!', unknown: '?'}[status];
    return `<article class="diagnostic-check diagnostic-${status}"><div class="diagnostic-check-heading"><div class="diagnostic-title-wrap"><span class="diagnostic-icon">${symbol}</span><strong>${escapeHtml(result.title || 'Comprobación')}</strong></div><span class="diagnostic-badge">${label}</span></div><p>${escapeHtml(result.detail || '')}</p></article>`;
  }).join('');
}

async function runProblemChecks() {
  if (problemCheckRunning || !selectedProblemId) return;
  const issueId = selectedProblemId;
  const status = document.getElementById('problemCheckStatus');
  const button = document.querySelector('[data-problem-run]');
  const results = document.getElementById('problemCheckResults');
  const application = document.getElementById('problemApplication')?.value.trim() || '';
  const targetPath = document.getElementById('problemPath')?.value.trim() || '';
  problemCheckRunning = true;
  if (button) { button.disabled = true; button.innerHTML = '<span class="loading-dots" aria-label="Analizando"><i></i><i></i><i></i></span> Analizando…'; }
  if (status) status.textContent = 'Ejecutando consultas locales. Esto puede tardar unos segundos…';
  if (results) results.replaceChildren();
  try {
    const response = await window.pywebview.api.run_problem_checks(issueId, application, targetPath);
    if (!response?.success) throw new Error(response?.message || 'No se completó el análisis.');
    if (selectedProblemId === issueId) {
      problemCheckResults = Array.isArray(response.results) ? response.results : [];
      if (status) status.textContent = response.message || 'Análisis local completado.';
    }
  } catch (error) {
    if (selectedProblemId === issueId) {
      problemCheckResults = [{title: 'No se pudo analizar', status: 'unknown', detail: error.message || 'Vuelve a intentarlo.'}];
      if (status) status.textContent = 'No se completó la comprobación.';
    }
  } finally {
    problemCheckRunning = false;
    const guide = problemGuides.find(item => item.id === selectedProblemId);
    if (guide) renderProblemGuide(guide);
  }
}

let devEditorView = null;
let devLanguageCompartment = null;
let devOpenTabs = [];
let devTutorialsCache = [];
let devTutorialIndex = 0;

function ensureCodeMirrorEditor() {
  if (devEditorView) return devEditorView;
  const host = document.getElementById('devCodeMirrorHost');
  const fallback = document.getElementById('codeEditor');
  if (!host || !window.CM) {
    if (fallback) fallback.hidden = false;
    return null;
  }
  const { EditorView, EditorState, Compartment, basicSetup, keymap, indentWithTab, devTheme, devHighlighting, languageFor } = window.CM;
  devLanguageCompartment = new Compartment();
  const updateListener = EditorView.updateListener.of(update => {
    if (update.docChanged && fallback) {
      fallback.value = update.state.doc.toString();
    }
  });
  const state = EditorState.create({
    doc: fallback ? fallback.value : '',
    extensions: [
      basicSetup,
      keymap.of([indentWithTab]),
      devTheme,
      devHighlighting,
      devLanguageCompartment.of(languageFor(codeActiveFile || 'main.py')),
      updateListener
    ]
  });
  devEditorView = new EditorView({ state, parent: host });
  return devEditorView;
}

function getEditorContent() {
  if (devEditorView) return devEditorView.state.doc.toString();
  const fallback = document.getElementById('codeEditor');
  return fallback ? fallback.value : '';
}

function setEditorContent(content, filename) {
  const fallback = document.getElementById('codeEditor');
  if (fallback) {
    fallback.value = content;
    fallback.disabled = false;
  }
  const view = ensureCodeMirrorEditor();
  if (view && window.CM) {
    const effects = devLanguageCompartment
      ? [devLanguageCompartment.reconfigure(window.CM.languageFor(filename || codeActiveFile || 'main.py'))]
      : [];
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: content },
      effects
    });
  }
}

function iconForDevFile(path) {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md')) return '📘';
  if (lower.endsWith('.json')) return '⚙️';
  if (lower.endsWith('.sh') || lower.endsWith('.bash')) return '🐚';
  if (lower.endsWith('.html') || lower.endsWith('.css')) return '🌐';
  return '📄';
}

async function loadCodeProjects() {
  const api = window.pywebview?.api;
  if (!api) return;
  const status = document.getElementById('codeWorkspaceStatus');
  const select = document.getElementById('codeProjectSelect');
  if (status) status.textContent = 'Cargando entorno del Módulo Dev…';
  try {
    let projects = [];
    let rootPath = '';
    if (api.get_dev_status) {
      const devInfo = await api.get_dev_status();
      if (devInfo.success) {
        projects = devInfo.projects || [];
        rootPath = devInfo.root || '';
        devTutorialsCache = devInfo.tutorials || [];
        updateSandboxChip(devInfo.sandbox);
      }
    }
    if (!projects.length && api.get_code_projects) {
      const result = await api.get_code_projects();
      if (!result.success) throw new Error(result.message || 'No se pudieron leer los proyectos.');
      projects = result.projects || [];
      rootPath = result.root || '';
    }
    const root = document.getElementById('codeWorkspaceRoot');
    if (root) root.textContent = rootPath;
    select.replaceChildren(new Option('Selecciona un proyecto', ''));
    projects.forEach(project => select.add(new Option(project.name, project.name)));
    const current = projects.some(project => project.name === codeActiveProject)
      ? codeActiveProject : (projects[0]?.name || '');
    select.value = current;
    if (current) await selectCodeProject(current);
    else {
      codeActiveProject = '';
      document.getElementById('codeFileList').textContent = 'Crea un proyecto para empezar.';
      if (status) status.textContent = 'Selecciona una plantilla y crea tu primer proyecto.';
    }
  } catch (error) {
    if (status) status.textContent = error.message || String(error);
  }
}

function updateSandboxChip(sandbox) {
  const dot = document.getElementById('devSandboxDot');
  const label = document.getElementById('devSandboxLabel');
  if (!sandbox || !label) return;
  const pyVer = sandbox.python_version ? `Python ${sandbox.python_version.split('.').slice(0, 2).join('.')}` : 'Python 3';
  if (sandbox.available) {
    if (dot) dot.classList.remove('offline');
    label.textContent = `sandbox activo · ${pyVer}`;
  } else {
    if (dot) dot.classList.add('offline');
    label.textContent = `sandbox limitado · ${pyVer}`;
  }
}

function toggleCreateProjectBar(defaultTemplate) {
  const form = document.getElementById('codeProjectForm');
  const tpl = document.getElementById('codeProjectTemplate');
  const nameInput = document.getElementById('codeProjectName');
  if (!form) return;
  form.hidden = !form.hidden;
  if (!form.hidden) {
    if (tpl && defaultTemplate) tpl.value = defaultTemplate;
    if (nameInput) {
      if (!nameInput.value && defaultTemplate === 'organizador_descargas') {
        nameInput.value = 'mi_organizador';
      }
      nameInput.focus();
    }
  }
}

async function createCodeProject(event) {
  event.preventDefault();
  const status = document.getElementById('codeWorkspaceStatus');
  const name = document.getElementById('codeProjectName').value.trim();
  const template = document.getElementById('codeProjectTemplate').value;
  const api = window.pywebview?.api;
  try {
    const isRecipe = template === 'organizador_descargas' || template === 'monitor_sistema_bash';
    const result = (isRecipe && api.create_dev_recipe_project)
      ? await api.create_dev_recipe_project(name, template)
      : await api.create_code_project(name, template);
    if (!result.success) throw new Error(result.message || 'No se pudo crear el proyecto.');
    document.getElementById('codeProjectName').value = '';
    const form = document.getElementById('codeProjectForm');
    if (form) form.hidden = true;
    codeActiveProject = result.project.name;
    if (status) status.textContent = `Proyecto ${result.project.name} creado.`;
    appendDevChatMessage('ai', `¡Listo! Creé el proyecto **${result.project.name}**. Selecciona un archivo o pulsa **▶ Ejecutar** para probarlo en el sandbox.`);
    await loadCodeProjects();
  } catch (error) {
    if (status) status.textContent = error.message || String(error);
  }
}

async function selectCodeProject(project) {
  if (!project) return;
  if (codeActiveFile && getEditorContent() !== codeBaseContent && !window.confirm('Hay cambios sin guardar. ¿Descartarlos?')) {
    document.getElementById('codeProjectSelect').value = codeActiveProject;
    return;
  }
  codeActiveProject = project;
  codeActiveFile = '';
  codeBaseContent = '';
  devOpenTabs = [];
  const projLabel = document.getElementById('devCurrentProjectLabel');
  if (projLabel) projLabel.textContent = project;
  document.getElementById('codeActiveFile').textContent = 'Sin archivo seleccionado';
  document.getElementById('codePreviewButton').disabled = true;
  document.getElementById('codeDiffPanel').hidden = true;
  codePendingToken = '';
  const list = document.getElementById('codeFileList');
  const status = document.getElementById('codeWorkspaceStatus');
  try {
    const result = await window.pywebview.api.list_code_files(project);
    if (!result.success) throw new Error(result.message || 'No se pudo listar el proyecto.');
    list.replaceChildren();
    result.files.forEach(relativePath => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'dev-fitem code-file-button';
      button.dataset.path = relativePath;
      button.innerHTML = `<span class="dev-ficon">${iconForDevFile(relativePath)}</span><span>${relativePath}</span>`;
      button.addEventListener('click', () => openCodeFile(relativePath));
      list.appendChild(button);
    });
    const preferred = result.files.includes('main.py')
      ? 'main.py'
      : (result.files.find(f => f.endsWith('.py') || f.endsWith('.sh') || f.endsWith('.js')) || result.files[0]);
    if (preferred) await openCodeFile(preferred);
    else list.textContent = 'Este proyecto todavía no tiene archivos.';
    if (status) status.textContent = `${result.files.length} archivo(s) en ${project}.`;
    await loadProjectCheckpoints();
  } catch (error) {
    list.textContent = error.message || String(error);
  }
}

function renderEditorTabs() {
  const container = document.getElementById('devEditorTabs');
  if (!container) return;
  const diffBtn = document.getElementById('codePreviewButton');
  container.replaceChildren();
  devOpenTabs.forEach(path => {
    const tab = document.createElement('button');
    tab.type = 'button';
    tab.className = `dev-etab${path === codeActiveFile ? ' on' : ''}`;
    if (path === codeActiveFile) {
      const span = document.createElement('span');
      span.id = 'codeActiveFile';
      span.textContent = path;
      tab.appendChild(span);
    } else {
      tab.textContent = path;
    }
    tab.addEventListener('click', () => openCodeFile(path));
    container.appendChild(tab);
  });
  if (!devOpenTabs.length) {
    const empty = document.createElement('div');
    empty.className = 'dev-etab on';
    empty.innerHTML = '<span id="codeActiveFile">Sin archivo seleccionado</span>';
    container.appendChild(empty);
  }
  if (diffBtn) container.appendChild(diffBtn);
}

async function openCodeFile(relativePath) {
  if (codeActiveFile && getEditorContent() !== codeBaseContent && !window.confirm('Hay cambios sin guardar. ¿Descartarlos?')) return;
  const result = await window.pywebview.api.read_code_file(codeActiveProject, relativePath);
  if (!result.success) {
    document.getElementById('codeWorkspaceStatus').textContent = result.message || 'No se pudo abrir el archivo.';
    return;
  }
  codeActiveFile = relativePath;
  codeBaseContent = result.content;
  if (!devOpenTabs.includes(relativePath)) {
    devOpenTabs.push(relativePath);
    if (devOpenTabs.length > 5) devOpenTabs.shift();
  }
  renderEditorTabs();
  setEditorContent(result.content, relativePath);
  document.getElementById('codeInstruction').disabled = false;
  document.getElementById('codeAskAiButton').disabled = false;
  document.getElementById('codePreviewButton').disabled = false;
  document.querySelectorAll('.code-file-button').forEach(button => {
    const isMatch = (button.dataset.path || button.textContent) === relativePath;
    button.classList.toggle('active', isMatch);
    button.classList.toggle('on', isMatch);
  });
  document.getElementById('codeDiffPanel').hidden = true;
  codePendingToken = '';
}

async function saveActiveCodeFile() {
  if (!codeActiveProject || !codeActiveFile) return;
  const status = document.getElementById('codeWorkspaceStatus');
  const api = window.pywebview?.api;
  const content = getEditorContent();
  try {
    if (api.save_code_file) {
      const res = await api.save_code_file(codeActiveProject, codeActiveFile, content);
      if (!res.success) throw new Error(res.message || 'No se pudo guardar.');
      codeBaseContent = content;
      if (status) status.textContent = `✔ Guardado: ${codeActiveFile}`;
    } else {
      await previewCodeChange();
    }
  } catch (error) {
    if (status) status.textContent = error.message || String(error);
  }
}

async function previewCodeChange() {
  const status = document.getElementById('codeWorkspaceStatus');
  try {
    const result = await window.pywebview.api.preview_code_change(
      codeActiveProject, codeActiveFile, getEditorContent()
    );
    if (!result.success) throw new Error(result.message || 'No se pudo preparar el diff.');
    showCodeDiffPreview(result);
    if (status) status.textContent = 'Revisa el diff; el archivo original todavía no se ha modificado.';
  } catch (error) {
    if (status) status.textContent = error.message || String(error);
  }
}

function appendDevChatMessage(role, text) {
  const container = document.getElementById('devChatMessages');
  if (!container) return;
  const div = document.createElement('div');
  div.className = `dev-msg ${role === 'user' ? 'user' : 'ai'}`;
  if (role === 'ai') {
    const bold = document.createElement('b');
    bold.textContent = '🤖 Agente: ';
    div.appendChild(bold);
    div.appendChild(document.createTextNode(text.replace(/\*\*/g, '')));
  } else {
    div.textContent = text;
  }
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendDevToolEvent(label, spinning = false) {
  const container = document.getElementById('devChatMessages');
  if (!container) return null;
  const pill = document.createElement('div');
  pill.className = 'dev-tool-pill';
  if (spinning) {
    const spin = document.createElement('span');
    spin.className = 'dev-spin';
    pill.appendChild(spin);
    pill.appendChild(document.createTextNode(` ${label}`));
  } else {
    pill.textContent = `✔ ${label}`;
  }
  container.appendChild(pill);
  container.scrollTop = container.scrollHeight;
  return pill;
}

async function requestCodeChange() {
  const input = document.getElementById('codeInstruction');
  const instruction = (input?.value || '').trim();
  if (!instruction || !codeActiveProject) return;
  const api = window.pywebview?.api;
  const status = document.getElementById('codeWorkspaceStatus');
  const button = document.getElementById('codeAskAiButton');
  const mode = document.getElementById('devAssistanceMode')?.value || 'guided';

  appendDevChatMessage('user', instruction);
  input.value = '';
  if (button) button.disabled = true;
  const readingPill = appendDevToolEvent(`Leyendo ${codeActiveFile || 'proyecto'}…`, true);
  if (status) status.textContent = 'El agente está analizando tu solicitud…';

  try {
    if (api.dev_agent_chat) {
      const res = await api.dev_agent_chat(codeActiveProject, codeActiveFile, instruction, mode);
      if (readingPill) readingPill.remove();
      if (!res.success) throw new Error(res.message || 'El agente no pudo procesar la solicitud.');
      (res.tool_events || []).forEach(ev => appendDevToolEvent(ev.label, false));
      if (res.reply) appendDevChatMessage('ai', res.reply);
      if (res.proposal && res.proposal.token) {
        showCodeDiffPreview(res.proposal);
        if (status) status.textContent = 'Propuesta recibida. Revisa y aprueba los cambios debajo del editor.';
      } else if (status) {
        status.textContent = 'Respuesta del agente lista.';
      }
      return;
    }

    // Fallback directo a request_code_change si se invoca desde un entorno antiguo
    const result = await api.request_code_change(codeActiveProject, codeActiveFile, instruction, true);
    if (readingPill) readingPill.remove();
    if (!result.success) throw new Error(result.message || 'El modelo no pudo proponer el cambio.');
    showCodeDiffPreview(result);
    if (status) status.textContent = 'Propuesta recibida. Revisa el diff antes de aplicarlo.';
  } catch (error) {
    if (readingPill) readingPill.remove();
    appendDevChatMessage('ai', `No pude completar ese paso: ${error.message || error}`);
    if (status) status.textContent = error.message || String(error);
  } finally {
    if (button) button.disabled = false;
  }
}

function showCodeDiffPreview(result) {
  codePendingToken = result.token;
  const pathEl = document.getElementById('codeDiffPath');
  if (pathEl) pathEl.textContent = `${result.project}/${result.path}`;
  const diffEl = document.getElementById('codeDiff');
  if (diffEl) {
    diffEl.textContent = result.diff;
    diffEl.hidden = false;
  }
  const statsEl = document.getElementById('devDiffStats');
  if (statsEl) {
    const added = result.added != null ? `+${result.added}` : '';
    const removed = result.removed != null ? ` / -${result.removed} líneas` : '';
    statsEl.textContent = added ? `${added}${removed}` : '';
  }
  const summaryEl = document.getElementById('devDiffSummary');
  if (summaryEl) {
    summaryEl.textContent = result.summary || 'Revisa el diff visual antes de aplicar los cambios al proyecto.';
  }
  document.getElementById('codeDiffPanel').hidden = false;
}

function toggleDevDiffView() {
  const pre = document.getElementById('codeDiff');
  if (pre) pre.hidden = !pre.hidden;
}

async function applyCodeChange() {
  if (!codePendingToken) return;
  const status = document.getElementById('codeWorkspaceStatus');
  const result = await window.pywebview.api.apply_code_change(codePendingToken, true);
  codePendingToken = '';
  document.getElementById('codeDiffPanel').hidden = true;
  if (!result.success) {
    if (status) status.textContent = result.message || 'No se pudieron aplicar los cambios.';
    return;
  }
  if (status) status.textContent = `✔ ${result.message} (${result.path})`;
  await openCodeFile(result.path);
  await loadProjectCheckpoints();
}

async function rejectCodeChange() {
  if (codePendingToken) await window.pywebview.api.apply_code_change(codePendingToken, false);
  codePendingToken = '';
  document.getElementById('codeDiffPanel').hidden = true;
  document.getElementById('codeWorkspaceStatus').textContent = 'Propuesta rechazada; no se modificó el archivo.';
}

async function runCodeInSandbox() {
  if (!codeActiveProject || !codeActiveFile) return;
  const api = window.pywebview?.api;
  if (!api?.run_code_in_sandbox) return;
  const status = document.getElementById('codeWorkspaceStatus');
  const runBtn = document.getElementById('devRunButton');
  if (getEditorContent() !== codeBaseContent && api.save_code_file) {
    await api.save_code_file(codeActiveProject, codeActiveFile, getEditorContent());
    codeBaseContent = getEditorContent();
  }
  if (runBtn) runBtn.disabled = true;
  if (status) status.textContent = `Ejecutando ${codeActiveFile} en el sandbox aislado…`;

  try {
    const res = await api.run_code_in_sandbox(codeActiveProject, codeActiveFile, '');
    renderConsoleOutput(res);
    if (status) status.textContent = res.message || 'Ejecución finalizada.';
    // Si el script creó archivos nuevos dentro del sandbox, refrescar lista
    const filesRes = await api.list_code_files(codeActiveProject);
    if (filesRes.success) {
      const list = document.getElementById('codeFileList');
      list.replaceChildren();
      filesRes.files.forEach(relativePath => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `dev-fitem code-file-button${relativePath === codeActiveFile ? ' on active' : ''}`;
        button.dataset.path = relativePath;
        button.innerHTML = `<span class="dev-ficon">${iconForDevFile(relativePath)}</span><span>${relativePath}</span>`;
        button.addEventListener('click', () => openCodeFile(relativePath));
        list.appendChild(button);
      });
    }
  } catch (error) {
    if (status) status.textContent = error.message || String(error);
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

function renderConsoleOutput(res) {
  const container = document.getElementById('devConsoleLines');
  const whyBtn = document.getElementById('devWhyFailedBtn');
  if (!container) return;
  container.replaceChildren();

  const translated = res.translated || {};
  const mainLine = document.createElement('div');
  if (res.success) {
    mainLine.innerHTML = `<span class="ok">✔</span> `;
    mainLine.appendChild(document.createTextNode(translated.headline || `${res.command} terminado.`));
    container.appendChild(mainLine);
    if (res.stdout && res.stdout.trim().includes('\n')) {
      const extra = document.createElement('div');
      extra.style.color = '#8b98a9';
      extra.textContent = res.stdout.trim();
      container.appendChild(extra);
    }
    const hint = document.createElement('div');
    hint.className = 'warn';
    hint.textContent = `⚠ ${translated.hint || 'Sugerencia del agente: puedes crear un checkpoint antes de probar cambios nuevos.'}`;
    container.appendChild(hint);
    if (whyBtn) whyBtn.hidden = true;
  } else {
    mainLine.innerHTML = `<span class="err">✖</span> `;
    mainLine.appendChild(document.createTextNode(translated.headline || res.message || 'El programa falló.'));
    container.appendChild(mainLine);
    if (res.stderr) {
      const rawLine = document.createElement('div');
      rawLine.style.color = '#8b98a9';
      rawLine.textContent = res.stderr.trim().split('\n').slice(-3).join(' | ');
      container.appendChild(rawLine);
    }
    if (whyBtn) {
      whyBtn.hidden = false;
      container.appendChild(whyBtn);
    }
  }
}

async function explainLastDevFailure() {
  const api = window.pywebview?.api;
  if (!api?.explain_dev_failure || !codeActiveProject) return;
  const pill = appendDevToolEvent('tool: explicar_error', false);
  const res = await api.explain_dev_failure(codeActiveProject, '');
  if (res.success && res.explanation) {
    const exp = res.explanation;
    appendDevChatMessage(
      'ai',
      `¿Por qué falló?: ${exp.cause}\n\nCómo corregirlo: ${exp.suggestion}`
    );
  } else if (pill) {
    pill.remove();
  }
}

async function loadProjectCheckpoints() {
  const api = window.pywebview?.api;
  const list = document.getElementById('devCheckpointList');
  if (!api?.list_code_checkpoints || !codeActiveProject || !list) return;
  const res = await api.list_code_checkpoints(codeActiveProject);
  list.replaceChildren();
  const items = res.checkpoints || [];
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'dev-fitem';
    empty.textContent = 'Sin checkpoints';
    list.appendChild(empty);
    return;
  }
  items.slice(0, 6).forEach(cp => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'dev-fitem';
    btn.title = 'Clic para restaurar el proyecto a este punto';
    btn.innerHTML = `<span class="dev-ficon">📸</span><span>${cp.label || cp.id}</span>`;
    btn.addEventListener('click', () => restoreProjectCheckpoint(cp.id, cp.label));
    list.appendChild(btn);
  });
}

async function createManualCheckpoint() {
  const api = window.pywebview?.api;
  if (!api?.create_code_checkpoint || !codeActiveProject) return;
  const status = document.getElementById('codeWorkspaceStatus');
  const res = await api.create_code_checkpoint(codeActiveProject, 'Snapshot manual');
  if (res.success) {
    if (status) status.textContent = '📸 Checkpoint guardado.';
    await loadProjectCheckpoints();
  }
}

async function restoreProjectCheckpoint(checkpointId, label) {
  if (!window.confirm(`¿Restaurar el proyecto al punto «${label || checkpointId}»? Se guardará una copia del estado actual por seguridad.`)) {
    return;
  }
  const api = window.pywebview?.api;
  const status = document.getElementById('codeWorkspaceStatus');
  const res = await api.restore_code_checkpoint(codeActiveProject, checkpointId);
  if (res.success) {
    if (status) status.textContent = res.message;
    appendDevToolEvent(`tool: checkpoint — restaurado (${label})`, false);
    if (codeActiveFile) await openCodeFile(codeActiveFile);
    await loadProjectCheckpoints();
  } else if (status) {
    status.textContent = res.message || 'No se pudo restaurar el checkpoint.';
  }
}

async function exportActiveCodeProject() {
  if (!codeActiveProject) return;
  if (!window.confirm(`¿Exportar una copia del proyecto «${codeActiveProject}» a tu carpeta ~/Documentos/${codeActiveProject}?`)) {
    return;
  }
  const api = window.pywebview?.api;
  const status = document.getElementById('codeWorkspaceStatus');
  const res = await api.export_code_project(codeActiveProject, 'Documentos');
  if (status) status.textContent = res.message || 'Exportación finalizada.';
  if (res.success) {
    appendDevToolEvent(`tool: exportar — ${res.destination}`, false);
    appendDevChatMessage('ai', `Exporté tu proyecto a **${res.destination}**. Ya puedes usarlo fuera del sandbox cuando quieras.`);
  }
}

function startGuidedDevTutorial() {
  const banner = document.getElementById('devTutorialBanner');
  const titleEl = document.getElementById('devTutorialTitle');
  const stepsEl = document.getElementById('devTutorialSteps');
  if (!banner || !stepsEl) return;
  const tutorials = devTutorialsCache.length ? devTutorialsCache : [
    {
      title: '📚 Tutorial guiado: Organizador de archivos en Python',
      steps: [
        'Pulsa ▶ Ejecutar para correr main.py dentro del sandbox aislado.',
        'Usa las píldoras del chat a la derecha para pedirle una mejora al agente y revisa el diff antes de aceptarlo.',
        'Haz clic en un Checkpoint de la izquierda para comprobar que puedes revertir cualquier cambio.'
      ]
    }
  ];
  const current = tutorials[devTutorialIndex % tutorials.length];
  devTutorialIndex += 1;
  if (titleEl) titleEl.textContent = `📚 ${current.title}`;
  stepsEl.replaceChildren();
  (current.steps || []).forEach(step => {
    const li = document.createElement('li');
    li.textContent = step.replace(/\*\*|`/g, '');
    stepsEl.appendChild(li);
  });
  banner.hidden = false;
}

function renderCatalogCategories() {
  const container = document.getElementById('catalogCategories');
  if (!container) return;
  container.replaceChildren();

  Object.entries(catalogCategoryLabels).forEach(([key, label]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `catalog-category${key === appCatalogState.category ? ' active' : ''}`;
    button.dataset.catalogCategory = key;
    button.textContent = label;
    button.addEventListener('click', () => setCatalogCategory(key));
    container.appendChild(button);
  });
}

function setCatalogSource(source) {
  appCatalogState.source = source;
  document.querySelectorAll('.catalog-source').forEach(button => {
    button.classList.toggle('active', button.dataset.catalogSource === source);
  });
  loadAppCatalog(true);
}

function setCatalogCategory(category) {
  appCatalogState.category = category;
  document.querySelectorAll('.catalog-category').forEach(button => {
    button.classList.toggle('active', button.dataset.catalogCategory === category);
  });
  loadAppCatalog(true);
}

function scheduleCatalogSearch() {
  window.clearTimeout(catalogSearchTimer);
  catalogSearchTimer = window.setTimeout(() => {
    const input = document.getElementById('catalogSearch');
    appCatalogState.query = input ? input.value.trim() : '';
    loadAppCatalog(true);
  }, 380);
}

function handleCatalogSearchKey(event) {
  if (event.key !== 'Enter') return;
  window.clearTimeout(catalogSearchTimer);
  appCatalogState.query = event.currentTarget.value.trim();
  loadAppCatalog(true);
}

function refreshAppCatalog() {
  loadAppCatalog(true, true);
}

async function chooseLocalPackage() {
  const button = document.getElementById('chooseLocalPackageButton');
  const status = document.getElementById('installToolStatus');
  if (!window.pywebview?.api?.choose_local_package) {
    if (status) status.textContent = 'Abre LinuxMate para elegir e instalar un archivo local.';
    return;
  }
  if (button) {
    button.disabled = true;
    button.textContent = 'Abriendo selector...';
  }
  try {
    let result = await window.pywebview.api.choose_local_package();
    if (result?.success && result.preview) result = await confirmPackagePreview(result.preview);
    if (status) status.textContent = result?.message || 'No se pudo preparar el archivo.';
    if (result?.success) {
      showToast('Instalación local preparada.');
      loadAppCatalog(true, true);
    }
  } catch (error) {
    if (status) status.textContent = `No se pudo preparar el archivo: ${error}`;
  } finally {
    if (button) {
      button.disabled = false;
      button.innerHTML = '<span class="ui-icon icon-package"></span> Elegir archivo .deb o AppImage';
    }
  }
}

function loadMoreCatalogApps() {
  if (!appCatalogState.loading && appCatalogState.hasMore) loadAppCatalog(false);
}

async function loadAppCatalog(reset = true, refreshInstalled = false) {
  const grid = document.getElementById('appCatalogGrid');
  const count = document.getElementById('catalogCount');
  const moreButton = document.getElementById('catalogLoadMore');
  if (!grid) return;

  if (reset) {
    appCatalogState.offset = 0;
    grid.innerHTML = '<div class="catalog-loading"><span class="loading-dots" aria-label="Cargando"><i></i><i></i><i></i></span><span>Consultando aplicaciones...</span></div>';
  }

  appCatalogState.loading = true;
  const requestId = ++catalogRequestId;
  if (count) count.textContent = appCatalogState.query ? 'Buscando en los gestores...' : 'Cargando catálogo...';
  if (moreButton) moreButton.hidden = true;

  try {
    let response;
    if (window.pywebview && window.pywebview.api) {
      response = await window.pywebview.api.get_app_catalog(
        appCatalogState.source,
        appCatalogState.category,
        appCatalogState.query,
        appCatalogState.offset,
        appCatalogState.limit,
        refreshInstalled
      );
    } else {
      await new Promise(resolve => window.setTimeout(resolve, 280));
      response = getPreviewCatalogPage();
    }

    if (requestId !== catalogRequestId) return;
    renderAppCatalog(response, !reset);
    updateCatalogSourceAvailability(response.sources_available || {});
    appCatalogState.loaded = true;
  } catch (err) {
    if (requestId !== catalogRequestId) return;
    grid.innerHTML = `<div class="catalog-empty">No se pudo cargar el catálogo.<span>${escapeHtml(String(err))}</span></div>`;
    if (count) count.textContent = 'Catálogo no disponible';
    const notice = document.getElementById('catalogNotice');
    if (notice) notice.hidden = true;
  } finally {
    if (requestId === catalogRequestId) appCatalogState.loading = false;
  }
}

function getPreviewCatalogPage() {
  const query = appCatalogState.query.toLowerCase();
  const filtered = previewCatalog.filter(app => {
    const sourceMatches = appCatalogState.source === 'all' || app.source === appCatalogState.source;
    const categoryMatches = appCatalogState.category === 'all' || app.category === appCatalogState.category;
    const text = `${app.name} ${app.package} ${app.description}`.toLowerCase();
    return sourceMatches && categoryMatches && (!query || text.includes(query));
  });
  const apps = filtered.slice(appCatalogState.offset, appCatalogState.offset + appCatalogState.limit);
  return {
    apps,
    total: filtered.length,
    offset: appCatalogState.offset,
    limit: appCatalogState.limit,
    has_more: appCatalogState.offset + apps.length < filtered.length,
    sources_available: { apt: true, dnf: true, pacman: true, zypper: true, snap: true, flatpak: true },
    recommended_source: 'apt',
    distribution: 'Linux'
  };
}

function renderAppCatalog(response, append = false) {
  const grid = document.getElementById('appCatalogGrid');
  const count = document.getElementById('catalogCount');
  const moreButton = document.getElementById('catalogLoadMore');
  const notice = document.getElementById('catalogNotice');
  const nativeInfo = document.getElementById('catalogNativeInfo');
  const apps = Array.isArray(response.apps) ? response.apps : [];
  const notices = Array.isArray(response.notices) ? response.notices : [];
  appCatalogState.recommendedSource = response.recommended_source || '';
  appCatalogState.distribution = response.distribution || '';
  if (nativeInfo) {
    const manager = catalogSourceLabels[appCatalogState.recommendedSource] || appCatalogState.recommendedSource.toUpperCase();
    nativeInfo.textContent = manager
      ? `Para ${appCatalogState.distribution || 'tu distribución'}, recomendamos ${manager}. El gestor pedirá confirmación antes de instalar.`
      : 'No se detectó un gestor compatible. Puedes elegir un archivo .deb o AppImage.';
  }
  if (notice) {
    notice.textContent = notices.join(' ');
    notice.hidden = notices.length === 0;
  }
  if (!append) grid.replaceChildren();

  if (!apps.length && !append) {
    const empty = document.createElement('div');
    empty.className = 'catalog-empty';
    empty.innerHTML = '<strong>No encontramos resultados</strong><span>Prueba otro nombre, origen o categoría.</span>';
    grid.appendChild(empty);
  } else {
    apps.forEach(app => grid.appendChild(createCatalogCard(app)));
  }

  appCatalogState.total = Number(response.total || 0);
  appCatalogState.offset = Number(response.offset || 0) + apps.length;
  appCatalogState.hasMore = Boolean(response.has_more);
  const shown = Math.min(appCatalogState.offset, appCatalogState.total);
  if (count) {
    const suffix = appCatalogState.query ? ` para “${appCatalogState.query}”` : '';
    count.textContent = `Mostrando ${shown.toLocaleString('es')} de ${appCatalogState.total.toLocaleString('es')} paquetes${suffix}`;
  }
  if (moreButton) moreButton.hidden = !appCatalogState.hasMore;
}

function createCatalogCard(app) {
  const card = document.createElement('article');
  card.className = 'tool-app-row catalog-app-card';

  const icon = document.createElement('div');
  icon.className = `app-icon-box catalog-app-icon source-${app.source}`;
  icon.setAttribute('aria-hidden', 'true');
  const showIconFallback = () => {
    icon.replaceChildren();
    icon.classList.remove('has-image');
    const fallback = document.createElement('span');
    fallback.className = 'ui-icon icon-package catalog-icon-fallback';
    icon.appendChild(fallback);
  };
  if (app.icon) {
    const image = document.createElement('img');
    image.className = 'catalog-app-logo';
    image.alt = '';
    image.loading = 'lazy';
    image.decoding = 'async';
    image.addEventListener('error', showIconFallback, { once: true });
    image.src = app.icon;
    icon.classList.add('has-image');
    icon.appendChild(image);
  } else {
    showIconFallback();
  }

  const copy = document.createElement('div');
  copy.className = 'tool-app-copy';
  const heading = document.createElement('div');
  heading.className = 'catalog-app-heading';
  const name = document.createElement('strong');
  name.textContent = app.name || app.package;
  const source = document.createElement('span');
  source.className = `package-source package-source-${app.source}`;
  source.textContent = app.source === 'apt' ? 'DEB / APT' : (catalogSourceLabels[app.source] || String(app.source).toUpperCase());
  heading.append(name, source);
  if (app.recommended) {
    const recommended = document.createElement('span');
    recommended.className = 'package-recommended';
    recommended.textContent = 'Recomendado';
    recommended.title = `Gestor nativo de ${appCatalogState.distribution || 'tu distribución'}`;
    heading.appendChild(recommended);
  }
  const description = document.createElement('span');
  description.textContent = app.description || 'Paquete disponible para Linux.';
  const packageName = document.createElement('code');
  packageName.className = 'catalog-package-name';
  packageName.textContent = app.origin ? `${app.package} · ${app.origin}` : app.package;
  copy.append(heading, description, packageName);

  const button = document.createElement('button');
  button.type = 'button';
  if (app.installed) {
    button.className = 'installed-badge';
    button.textContent = 'Instalado';
    button.disabled = true;
  } else {
    button.className = 'glass-btn btn-install';
    button.textContent = 'Instalar';
    button.addEventListener('click', () => installCatalogApp(button, app));
  }

  card.append(icon, copy, button);
  enhanceInteractiveSurface(card, true);
  return card;
}

function updateCatalogSourceAvailability(availability) {
  ['apt', 'dnf', 'pacman', 'zypper', 'snap', 'flatpak'].forEach(source => {
    const button = document.querySelector(`[data-catalog-source="${source}"]`);
    if (!button) return;
    const available = availability[source] !== false;
    button.classList.toggle('unavailable', !available);
    button.title = available ? '' : `${source} no está instalado en este equipo`;
  });
}

async function installCatalogApp(button, app) {
  const status = document.getElementById('installToolStatus');
  const previousText = button.textContent;
  button.disabled = true;
  button.textContent = 'Preparando...';
  if (status) status.textContent = `Preparando ${app.name} desde ${String(app.source).toUpperCase()}...`;

  try {
    let result;
    if (window.pywebview && window.pywebview.api) {
      result = await window.pywebview.api.install_catalog_app(app.package, app.source, app.name);
      if (result?.success && result.preview) {
        result = await confirmPackagePreview(result.preview);
      }
    } else {
      await new Promise(resolve => window.setTimeout(resolve, 500));
      result = { success: true, message: `Vista previa: instalación de ${app.name} preparada.` };
    }

    if (result && result.success) {
      button.textContent = 'En proceso';
      button.classList.add('processing');
      if (status) status.textContent = result.message;
      showToast(`Instalación preparada: ${app.name}`);
    } else {
      button.disabled = false;
      button.textContent = previousText;
      if (status) status.textContent = result?.message || 'No se pudo preparar la instalación.';
    }
  } catch (err) {
    button.disabled = false;
    button.textContent = previousText;
    if (status) status.textContent = `Error: ${err}`;
  }
}

async function copyCommand(command, button) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(command);
    } else {
      const helper = document.createElement('textarea');
      helper.value = command;
      helper.style.position = 'fixed';
      helper.style.opacity = '0';
      document.body.appendChild(helper);
      helper.select();
      document.execCommand('copy');
      helper.remove();
    }
    const previous = button.textContent;
    button.textContent = 'Copiado';
    showToast(`Comando copiado: ${command}`);
    window.setTimeout(() => { button.textContent = previous; }, 1400);
  } catch (err) {
    showToast('No se pudo copiar el comando');
  }
}

function selectGuideExplanation(kind) {
  if (!['command', 'error'].includes(kind)) return;
  const kindChanged = guideExplanationKind !== kind;
  guideExplanationKind = kind;
  const input = document.getElementById('guideExplainInput');
  const label = document.getElementById('guideExplainLabel');
  const submit = document.getElementById('guideExplainButton');
  const examples = document.getElementById('guideExplainExamples');
  const result = document.getElementById('guideExplainResult');
  const status = document.getElementById('guideExplainStatus');
  const isCommand = kind === 'command';

  document.querySelectorAll('[data-guide-kind]').forEach(button => {
    const selected = button.dataset.guideKind === kind;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', selected ? 'true' : 'false');
  });
  if (label) label.textContent = isCommand ? 'Pega un comando para entender sus partes y riesgos' : 'Pega el mensaje de error exacto';
  if (input) {
    if (kindChanged) input.value = '';
    input.placeholder = isCommand
      ? 'Ejemplo: sudo apt install vlc'
      : 'Ejemplo: E: Unable to locate package vlc';
  }
  if (result && kindChanged) {
    result.hidden = true;
    result.replaceChildren();
  }
  if (status && kindChanged) status.textContent = 'Pega un texto o elige un ejemplo.';
  if (submit) submit.innerHTML = `<span class="ui-icon ${isCommand ? 'icon-eye' : 'icon-tools'}"></span> ${isCommand ? 'Explicar comando' : 'Explicar error'}`;
  if (examples) {
    const items = isCommand
      ? [
          ['Instalar con APT', 'sudo apt install vlc'],
          ['Ver archivos ocultos', 'ls -la'],
          ['Revisar espacio', 'df -h'],
          ['Ver servicios fallidos', 'systemctl --failed']
        ]
      : [
          ['Paquete no encontrado', 'E: Unable to locate package vlc'],
          ['Permiso denegado', 'Permission denied'],
          ['Disco lleno', 'No space left on device'],
          ['Orden desconocida', 'bash: htop: command not found']
        ];
    examples.replaceChildren();
    items.forEach(([title, value]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'guide-example-chip';
      button.textContent = title;
      button.addEventListener('click', () => {
        if (input) {
          input.value = value;
          input.focus();
        }
      });
      examples.appendChild(button);
    });
  }
}

async function runGuideExplanation() {
  const input = document.getElementById('guideExplainInput');
  const button = document.getElementById('guideExplainButton');
  const result = document.getElementById('guideExplainResult');
  const status = document.getElementById('guideExplainStatus');
  const content = input?.value.trim() || '';
  if (!content || !result || button?.disabled) {
    input?.focus();
    if (status && !content) status.textContent = 'Pega el comando o error que quieras entender.';
    return;
  }

  if (button) button.disabled = true;
  if (status) status.textContent = 'Analizando localmente…';
  result.hidden = false;
  result.innerHTML = '<span class="loading-dots" aria-label="Analizando"><i></i><i></i><i></i></span> Preparando explicación…';
  try {
    const api = window.pywebview?.api;
    const reply = api?.explain_text
      ? await api.explain_text(guideExplanationKind, content)
      : 'Abre LinuxMate para analizar el texto. No se ejecutó ni envió nada.';
    result.innerHTML = formatAiResponse(String(reply || 'No se pudo generar una explicación.'));
    if (status) status.textContent = 'Listo. El comando no se ejecutó y el texto no se envió al agente.';
  } catch (error) {
    result.textContent = `No se pudo explicar el texto: ${error}`;
    if (status) status.textContent = 'Ocurrió un error al analizar el texto.';
  } finally {
    if (button) button.disabled = false;
  }
}

async function runTroubleshooter() {
  const resultBox = document.getElementById('diagnosticResult');
  const button = document.getElementById('runDiagnosticButton');
  if (!resultBox || diagnosticLoading) return;
  diagnosticLoading = true;
  if (button) button.disabled = true;
  resultBox.innerHTML = '<div class="empty-result"><span class="loading-dots" aria-label="Analizando"><i></i><i></i><i></i></span><strong>Analizando el sistema</strong></div>';

  try {
    let response;
    if (window.pywebview && window.pywebview.api) {
      response = await window.pywebview.api.get_system_diagnostic();
    } else {
      response = { checks: [], problems: 0, unknown: 0 };
    }
    renderDiagnostic(response);
    diagnosticLoaded = true;
  } catch (err) {
    resultBox.textContent = `No se pudo completar el diagnóstico: ${err}`;
  } finally {
    diagnosticLoading = false;
    if (button) button.disabled = false;
  }
}

function renderDiagnostic(report) {
  const resultBox = document.getElementById('diagnosticResult');
  if (!resultBox || !report || !Array.isArray(report.checks)) throw new Error('Respuesta de diagnóstico no válida');
  resultBox.replaceChildren();

  const summary = document.createElement('div');
  summary.className = 'diagnostic-summary';
  if (!report.checks.length) {
    summary.textContent = 'La vista previa no puede examinar este equipo. Abre LinuxMate para ejecutar el diagnóstico.';
    resultBox.appendChild(summary);
    return;
  }
  const problems = Number(report.problems || 0);
  const unknown = Number(report.unknown || 0);
  summary.textContent = problems
    ? `${problems} problema${problems === 1 ? '' : 's'} detectado${problems === 1 ? '' : 's'}`
    : (unknown ? 'No se detectaron problemas en las comprobaciones disponibles' : 'No se detectaron problemas');
  if (unknown) summary.textContent += ` · ${unknown} comprobación${unknown === 1 ? '' : 'es'} sin datos`;
  summary.classList.add(problems ? 'has-issues' : 'is-clear');
  resultBox.appendChild(summary);

  const list = document.createElement('div');
  list.className = 'diagnostic-list';
  const labels = { ok: 'Correcto', warning: 'Atención', unknown: 'No disponible' };
  const iconClasses = {
    storage: 'icon-clean', memory: 'icon-memory', cpu: 'icon-cpu', packages: 'icon-package',
    updates: 'icon-sync', services: 'icon-settings', network: 'icon-network',
    permissions: 'icon-shield', battery: 'icon-battery', temperature: 'icon-temperature',
    repositories: 'icon-package'
  };
  const allowedActions = new Set(['repair_packages', 'restart_network', 'inspect_services']);
  report.checks.forEach(check => {
    const status = Object.prototype.hasOwnProperty.call(labels, check.status) ? check.status : 'unknown';
    const card = document.createElement('article');
    card.className = `diagnostic-check diagnostic-${status}`;
    const heading = document.createElement('div');
    heading.className = 'diagnostic-check-heading';
    const titleWrap = document.createElement('div');
    titleWrap.className = 'diagnostic-title-wrap';
    const icon = document.createElement('span');
    icon.className = `ui-icon diagnostic-icon ${iconClasses[check.id] || 'icon-pulse'}`;
    icon.setAttribute('aria-hidden', 'true');
    const title = document.createElement('strong');
    title.textContent = check.title || 'Comprobación';
    titleWrap.append(icon, title);
    const badge = document.createElement('span');
    badge.className = 'diagnostic-badge';
    badge.textContent = labels[status];
    heading.append(titleWrap, badge);
    const detail = document.createElement('p');
    detail.textContent = check.detail || 'No hay detalles disponibles.';
    card.append(heading, detail);
    if (check.action && allowedActions.has(check.action.id)) {
      const actionButton = document.createElement('button');
      actionButton.className = 'glass-btn glass-btn-secondary diagnostic-action';
      actionButton.type = 'button';
      actionButton.textContent = check.action.label || 'Abrir herramienta';
      actionButton.addEventListener('click', () => prepareDiagnosticAction(check.action.id, card));
      card.appendChild(actionButton);
    }
    list.appendChild(card);
  });
  resultBox.appendChild(list);
}

function prepareDiagnosticAction(actionId, card) {
  document.querySelectorAll('.diagnostic-confirm').forEach(element => element.remove());
  if (actionId === 'inspect_services') {
    executeDiagnosticAction(actionId, card);
    return;
  }
  const explanations = {
    repair_packages: 'Se abrirá una terminal para terminar configuraciones pendientes y reparar dependencias. Revisa cualquier cambio que APT proponga.',
    restart_network: 'Se abrirá una terminal para reiniciar NetworkManager. Tu conexión podría cortarse durante unos segundos.'
  };
  const confirmation = document.createElement('div');
  confirmation.className = 'diagnostic-confirm';
  const description = document.createElement('p');
  description.textContent = explanations[actionId] || 'Confirma la acción antes de continuar.';
  const controls = document.createElement('div');
  controls.className = 'diagnostic-confirm-controls';
  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.className = 'glass-btn glass-btn-secondary';
  cancel.textContent = 'Cancelar';
  cancel.addEventListener('click', () => confirmation.remove());
  const proceed = document.createElement('button');
  proceed.type = 'button';
  proceed.className = 'glass-btn';
  proceed.textContent = 'Continuar';
  proceed.addEventListener('click', () => {
    confirmation.remove();
    executeDiagnosticAction(actionId, card);
  });
  controls.append(cancel, proceed);
  confirmation.append(description, controls);
  card.appendChild(confirmation);
}

async function executeDiagnosticAction(actionId, card) {
  const actionButton = card.querySelector('.diagnostic-action');
  if (actionButton) actionButton.disabled = true;
  let status = card.querySelector('.diagnostic-action-status');
  if (!status) {
    status = document.createElement('p');
    status.className = 'diagnostic-action-status';
    card.appendChild(status);
  }
  status.textContent = 'Preparando terminal...';
  try {
    const response = window.pywebview && window.pywebview.api
      ? await window.pywebview.api.run_diagnostic_fix(actionId)
      : { success: false, message: 'Esta acción solo está disponible en LinuxMate.' };
    status.textContent = response.message || 'No se obtuvo respuesta.';
    if (response.success) showToast('Herramienta abierta en la terminal');
  } catch (err) {
    status.textContent = `No se pudo abrir la herramienta: ${err}`;
  } finally {
    if (actionButton) actionButton.disabled = false;
  }
}

function handleUninstallKey(event) {
  if (event.key === 'Enter') searchInstalledApps();
}

async function searchInstalledApps() {
  const input = document.getElementById('uninstallQuery');
  const sourceSelect = document.getElementById('uninstallSource');
  const resultsBox = document.getElementById('uninstallResults');
  const confirmBox = document.getElementById('uninstallConfirm');
  const query = input ? input.value.trim() : '';
  const source = sourceSelect ? sourceSelect.value : 'auto';

  pendingUninstall = null;
  if (confirmBox) confirmBox.hidden = true;
  if (!query) {
    resultsBox.textContent = 'Escribe primero el nombre de una aplicación.';
    input?.focus();
    return;
  }

  resultsBox.innerHTML = '<span class="loading-inline"><span class="loading-dots" aria-label="Buscando"><i></i><i></i><i></i></span> Buscando instalaciones...</span>';

  try {
    let candidates = [];
    if (window.pywebview && window.pywebview.api) {
      candidates = await window.pywebview.api.search_installed_apps(query, source);
    } else {
      await new Promise(resolve => window.setTimeout(resolve, 450));
      candidates = [{ source: source === 'auto' ? 'apt' : source, package: query, name: query }];
    }
    renderUninstallCandidates(Array.isArray(candidates) ? candidates : []);
  } catch (err) {
    resultsBox.textContent = `No se pudo buscar la aplicación: ${err}`;
  }
}

function renderUninstallCandidates(candidates) {
  const resultsBox = document.getElementById('uninstallResults');
  if (!resultsBox) return;
  resultsBox.replaceChildren();

  if (!candidates.length) {
    const empty = document.createElement('div');
    empty.className = 'uninstall-empty';
    empty.textContent = 'No se encontró una aplicación instalada con ese nombre.';
    resultsBox.appendChild(empty);
    return;
  }

  candidates.slice(0, 8).forEach(candidate => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'uninstall-candidate';

    const copy = document.createElement('span');
    const name = document.createElement('strong');
    const detail = document.createElement('small');
    name.textContent = candidate.name || candidate.package;
    detail.textContent = `${candidate.package} · ${String(candidate.source).toUpperCase()}`;
    copy.append(name, detail);

    const action = document.createElement('span');
    action.className = 'candidate-action';
    action.textContent = 'Seleccionar';
    row.append(copy, action);
    row.addEventListener('click', () => prepareUninstall(candidate));
    enhanceInteractiveSurface(row, true);
    resultsBox.appendChild(row);
  });
}

function prepareUninstall(candidate) {
  pendingUninstall = {
    package: candidate.package,
    source: candidate.source || 'auto',
    name: candidate.name || candidate.package
  };

  const confirmBox = document.getElementById('uninstallConfirm');
  const title = document.getElementById('uninstallConfirmTitle');
  const text = document.getElementById('uninstallConfirmText');
  if (title) title.textContent = `Quitar ${pendingUninstall.name}`;
  if (text) text.textContent = `Se abrirá una terminal para desinstalar ${pendingUninstall.package} mediante ${pendingUninstall.source.toUpperCase()}. Revisa el comando antes de confirmar en la terminal.`;
  if (confirmBox) confirmBox.hidden = false;
}

async function confirmUninstall() {
  if (!pendingUninstall) return;
  const button = document.getElementById('confirmUninstallButton');
  const resultsBox = document.getElementById('uninstallResults');
  button.disabled = true;
  button.textContent = 'Preparando terminal...';

  try {
    let response;
    if (window.pywebview && window.pywebview.api) {
      response = await window.pywebview.api.uninstall_app(pendingUninstall.package, pendingUninstall.source);
    } else {
      await new Promise(resolve => window.setTimeout(resolve, 550));
      response = `Vista previa: se abriría la terminal para quitar ${pendingUninstall.package}.`;
    }
    resultsBox.textContent = response;
    showToast('Desinstalación preparada en la terminal');
    document.getElementById('uninstallConfirm').hidden = true;
    pendingUninstall = null;
  } catch (err) {
    resultsBox.textContent = `No se pudo preparar la desinstalación: ${err}`;
  } finally {
    button.disabled = false;
    button.textContent = 'Confirmar y abrir terminal';
  }
}

// ==========================================================================
// 3. WINDOW CONTROLS (Min, Max, Close)
// ==========================================================================
function windowControl(action) {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.window_control(action);
  } else {
    console.log("Window control:", action);
  }
}

// ==========================================================================
// 3. SPLITTER & DYNAMIC CHAT RESIZING
// ==========================================================================
function initSplitter() {
  const splitter = document.getElementById('splitter');
  const rightPanel = document.getElementById('rightPanel');

  if (!splitter || !rightPanel) return;

  splitter.addEventListener('mousedown', (e) => {
    isResizing = true;
    splitter.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  window.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const newWidth = window.innerWidth - e.clientX;
    if (newWidth >= 260 && newWidth <= 750) {
      rightPanel.style.width = `${newWidth}px`;
    }
  });

  window.addEventListener('mouseup', () => {
    if (isResizing) {
      isResizing = false;
      splitter.classList.remove('active');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });
}

function toggleChatSize() {
  const rightPanel = document.getElementById('rightPanel');
  if (!rightPanel) return;

  if (isChatExpanded) {
    rightPanel.style.width = '360px';
    isChatExpanded = false;
    showToast('Chat restaurado');
  } else {
    rightPanel.style.width = '580px';
    isChatExpanded = true;
    showToast('Chat ampliado');
  }
}

// ==========================================================================
// 4. CHAT SYSTEM WITH AI BACKEND
// ==========================================================================
function handleChatKey(event) {
  if (event.key === 'Enter') {
    sendChatMessage();
  }
}

function sendQuickTag(text) {
  switchRightTab('chat');
  closeExplainPanel();
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = text;
    sendChatMessage();
  }
}

function openExplainPanel(kind) {
  if (!['error', 'command'].includes(kind)) return;
  switchRightTab('chat');
  explanationKind = kind;
  const panel = document.getElementById('chatExplainPanel');
  const title = document.getElementById('chatExplainTitle');
  const label = document.getElementById('chatExplainLabel');
  const input = document.getElementById('chatExplainInput');
  if (!panel || !input) return;
  const isError = kind === 'error';
  if (title) title.textContent = isError ? 'Entender un error' : 'Entender un comando';
  if (label) label.textContent = isError ? 'Pega el mensaje de error' : 'Pega el comando completo';
  input.placeholder = isError ? 'Ejemplo: E: Unable to locate package...' : 'Ejemplo: sudo apt install vlc';
  input.value = '';
  panel.hidden = false;
  focusChat();
  input.focus();
}

function closeExplainPanel() {
  explanationKind = null;
  const panel = document.getElementById('chatExplainPanel');
  if (panel) panel.hidden = true;
}

async function submitExplanation() {
  const input = document.getElementById('chatExplainInput');
  const button = document.getElementById('chatExplainSubmit');
  const content = input?.value.trim() || '';
  const kind = explanationKind;
  if (!content || !kind || button?.disabled) {
    input?.focus();
    return;
  }
  if (button) button.disabled = true;
  const loadingId = `explanation-${Date.now()}`;
  appendMessage(`${kind === 'error' ? 'Error' : 'Comando'}: ${content}`, 'user');
  appendLoadingMessage(loadingId);
  try {
    const reply = window.pywebview && window.pywebview.api
      ? await window.pywebview.api.explain_text(kind, content)
      : 'La explicación local está disponible al abrir LinuxMate.';
    removeLoadingMessage(loadingId);
    appendMessage(reply, 'ai');
    if (input) input.value = '';
    closeExplainPanel();
  } catch (err) {
    removeLoadingMessage(loadingId);
    appendMessage(`No se pudo explicar el texto: ${err}`, 'ai');
  } finally {
    if (button) button.disabled = false;
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const query = input ? input.value.trim() : '';
  if (!query) return;

  input.value = '';
  await sendChatMessageCore(query);
}

async function sendChatMessageCore(query) {
  appendMessage(query, 'user');

  const loadingId = 'loading-' + Date.now();
  appendLoadingMessage(loadingId);

  try {
    let reply = "";
    if (window.pywebview && window.pywebview.api) {
      reply = await window.pywebview.api.chat(query);
    } else {
      await new Promise(r => setTimeout(r, 600));
      reply = `He recibido tu consulta: "${query}". Para tareas del sistema, utiliza los accesos rápidos o comandos validados.`;
    }
    removeLoadingMessage(loadingId);
    appendMessage(reply, 'ai');
  } catch (err) {
    console.error(err);
    removeLoadingMessage(loadingId);
    appendMessage("Error al conectar con el asistente: " + err, 'ai');
  }
}

function getChatContainers() {
  return document.querySelectorAll('#chatMessages, #chatSectionMessages');
}

function appendMessage(text, sender) {
  const containers = getChatContainers();
  if (!containers.length) return;

  containers.forEach(chatMessages => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${sender}`;

    if (sender === 'ai') {
      msgDiv.innerHTML = formatAiResponse(text);
    } else {
      msgDiv.textContent = text;
    }

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}

function appendLoadingMessage(id) {
  const containers = getChatContainers();
  if (!containers.length) return;

  containers.forEach((chatMessages, idx) => {
    const msgDiv = document.createElement('div');
    msgDiv.id = idx === 0 ? id : `${id}-section`;
    msgDiv.className = 'message message-ai';
    msgDiv.innerHTML = '<span class="loading-dots" aria-label="Pensando"><i></i><i></i><i></i></span>';
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}

function removeLoadingMessage(id) {
  const el1 = document.getElementById(id);
  if (el1) el1.remove();
  const el2 = document.getElementById(`${id}-section`);
  if (el2) el2.remove();
}

function clearMainChatHistory() {
  getChatContainers().forEach(chatMessages => {
    chatMessages.innerHTML = `
      <div class="message message-ai">
        ¡Conversación reiniciada! ¿En qué puedo ayudarte en tu sistema Linux?
      </div>
    `;
  });
  showToast('Historial de chat reiniciado');
}

function handleSectionChatKey(event) {
  if (event.key === 'Enter') {
    sendSectionChatMessage();
  }
}

async function sendSectionChatMessage() {
  const input = document.getElementById('chatSectionInput');
  if (!input) return;
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  await sendChatMessageCore(query);
}

function sendSectionQuickTag(text) {
  closeSectionExplainPanel();
  const input = document.getElementById('chatSectionInput');
  if (input) input.value = text;
  sendChatMessageCore(text);
}

function openSectionExplainPanel(kind) {
  if (!['error', 'command'].includes(kind)) return;
  explanationKind = kind;
  const panel = document.getElementById('chatSectionExplainPanel');
  const title = document.getElementById('chatSectionExplainTitle');
  const label = document.getElementById('chatSectionExplainLabel');
  const input = document.getElementById('chatSectionExplainInput');
  if (!panel || !input) return;
  const isError = kind === 'error';
  if (title) title.textContent = isError ? 'Entender un error' : 'Entender un comando';
  if (label) label.textContent = isError ? 'Pega el mensaje de error' : 'Pega el comando completo';
  input.placeholder = isError ? 'Ejemplo: E: Unable to locate package...' : 'Ejemplo: sudo apt install vlc';
  input.value = '';
  panel.hidden = false;
  input.focus();
}

function closeSectionExplainPanel() {
  explanationKind = null;
  const panel = document.getElementById('chatSectionExplainPanel');
  if (panel) panel.hidden = true;
}

async function submitSectionExplanation() {
  const input = document.getElementById('chatSectionExplainInput');
  const button = document.getElementById('chatSectionExplainSubmit');
  const content = input?.value.trim() || '';
  const kind = explanationKind;
  if (!content || !kind || button?.disabled) {
    input?.focus();
    return;
  }
  if (button) button.disabled = true;
  const loadingId = `explanation-${Date.now()}`;
  appendMessage(`${kind === 'error' ? 'Error' : 'Comando'}: ${content}`, 'user');
  appendLoadingMessage(loadingId);
  try {
    const reply = window.pywebview && window.pywebview.api
      ? await window.pywebview.api.explain_text(kind, content)
      : 'La explicación local está disponible al abrir LinuxMate.';
    removeLoadingMessage(loadingId);
    appendMessage(reply, 'ai');
    if (input) input.value = '';
    closeSectionExplainPanel();
  } catch (err) {
    removeLoadingMessage(loadingId);
    appendMessage(`No se pudo explicar el texto: ${err}`, 'ai');
  } finally {
    if (button) button.disabled = false;
  }
}

function formatAiResponse(text) {
  // Escape backend/LLM output first, then allow a small safe Markdown subset.
  let html = escapeHtml(String(text || ''));
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/gi, (match, lang, code) => {
    return `<div class="chat-code-block">${code.trim()}</div>`;
  });
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ==========================================================================
// 5. GLOBAL SEARCH BAR
// ==========================================================================
function handleSearchKey(event) {
  if (event.key === 'Enter') {
    executeSearch();
  }
}

function executeSearch() {
  const input = document.getElementById('globalSearch');
  const val = input.value.trim();
  if (!val) return;

  focusChat();
  const chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.value = val;
    sendChatMessage();
  }
}

function clearSearch() {
  const input = document.getElementById('globalSearch');
  if (input) {
    input.value = '';
    input.focus();
  }
}

// ==========================================================================
// 6. ACTION TOOLS & RUNNER
// ==========================================================================
async function openTool(actionId, event) {
  if (event) event.preventDefault();

  if (actionId === 'code_workspace' && window.pywebview?.api?.open_dev_window) {
    try {
      const res = await window.pywebview.api.open_dev_window();
      if (res && res.success) {
        showToast('Abriendo LinuxMate Dev Studio en ventana independiente…');
        return;
      }
    } catch (err) {
      console.warn('Fallback a vista integrada:', err);
    }
  }

  if (toolWorkspaceActions.has(actionId)) {
    openToolWindow(actionId);
    return;
  }

  const overlay = document.getElementById('toolOverlay');
  if (overlay && !overlay.hidden) {
    closeToolWindow();
  }

  appendMessage(`Ejecutando acción: ${actionId.replace(/_/g, ' ')}...`, 'user');
  focusChat();
  showToast('Consulta enviada al asistente en el panel de chat.');

  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.run_action(actionId);
      if (res) {
        appendMessage(res, 'ai');
      }
    } catch (err) {
      appendMessage("Error ejecutando acción: " + err, 'ai');
    }
  } else {
    appendMessage(`Simulación: Acción ${actionId} ejecutada con éxito.`, 'ai');
  }
}

function scrollToTop(event) {
  if (event) event.preventDefault();
  const main = document.getElementById('mainPanel');
  if (main) main.scrollTo({ top: 0, behavior: 'smooth' });
}

function focusChat(event) {
  if (event) event.preventDefault();
  if (typeof showChatSection === 'function') {
    showChatSection();
  }
  const input = document.getElementById('chatSectionInput') || document.getElementById('chatInput');
  if (input) input.focus();
}

// ==========================================================================
// 7. APP INSTALLER
// ==========================================================================
async function installApp(buttonElement, appId, appName) {
  const originalText = buttonElement.innerText;
  buttonElement.disabled = true;
  buttonElement.innerText = "Instalando...";
  buttonElement.style.opacity = "0.7";
  const toolStatus = document.getElementById('installToolStatus');
  if (toolStatus) toolStatus.textContent = `Abriendo la instalación de ${appName}...`;

  appendMessage(`Solicitada instalación de ${appName}...`, 'user');

  try {
    let result = null;
    if (window.pywebview && window.pywebview.api) {
      result = await window.pywebview.api.install_app(appId);
      if (result?.success && result.preview) {
        result = await confirmPackagePreview(result.preview);
      }
    } else {
      await new Promise(r => setTimeout(r, 1200));
      result = { success: true, message: `Simulación: ${appName} instalado exitosamente.` };
    }

    if (result && result.success) {
      buttonElement.innerText = "En proceso";
      buttonElement.disabled = true;
      appendMessage(`Se abrió el gestor para instalar ${appName}.\n${result.message || ''}`, 'ai');
      showToast(`Instalación iniciada: ${appName}`);
      if (toolStatus) toolStatus.textContent = result.message || `Se inició la instalación de ${appName}.`;
    } else {
      buttonElement.innerText = "Reintentar";
      buttonElement.disabled = false;
      buttonElement.style.opacity = "1";
      appendMessage(`No se pudo instalar ${appName}: ${result ? result.message : 'Error desconocido'}`, 'ai');
      if (toolStatus) toolStatus.textContent = result ? result.message : 'No se pudo iniciar la instalación.';
    }
  } catch (err) {
    buttonElement.innerText = "Error";
    buttonElement.disabled = false;
    buttonElement.style.opacity = "1";
    appendMessage(`Error durante la instalación: ${err}`, 'ai');
    if (toolStatus) toolStatus.textContent = `Error: ${err}`;
  }
}

async function confirmPackagePreview(preview) {
  const confirmed = window.confirm(
    `Confirma la instalación de ${preview.name}\n\n` +
    `Paquete: ${preview.package}\nOrigen: ${String(preview.source).toUpperCase()}\n\n` +
    `${preview.action_label || 'Comando exacto'}:\n${preview.command}\n\n` +
    `${preview.size_and_dependencies}\n\n¿Continuar?`
  );
  return window.pywebview.api.confirm_catalog_app_install(preview.token, confirmed);
}

// ==========================================================================
// 8. TELEMETRY SYSTEM STATUS LOOP
// ==========================================================================
function initTelemetryLoop() {
  setInterval(updateTelemetry, 2500);
}

async function updateTelemetry() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const stats = await window.pywebview.api.get_system_stats();
    if (!stats) return;

    // Update RAM
    const ramText = document.getElementById('ramText');
    const ramBar = document.getElementById('ramBar');
    if (ramText && stats.ram_percent !== undefined) {
      ramText.innerText = `${stats.ram_percent}%`;
    }
    if (ramBar && stats.ram_percent !== undefined) {
      ramBar.style.width = `${stats.ram_percent}%`;
    }

    // Update CPU
    const cpuText = document.getElementById('cpuText');
    const cpuBar = document.getElementById('cpuBar');
    if (cpuText && stats.cpu_percent !== undefined) {
      cpuText.innerText = `${stats.cpu_percent}%`;
    }
    if (cpuBar && stats.cpu_percent !== undefined) {
      cpuBar.style.width = `${stats.cpu_percent}%`;
    }

    // Update Updates status
    const updatesText = document.getElementById('updatesText');
    const updatesBar = document.getElementById('updatesBar');
    if (updatesText && stats.updates_pending !== undefined) {
      if (stats.updates_pending === 0) {
        updatesText.innerHTML = `Al día <span style="font-size: 0.8rem;">✓</span>`;
        if (updatesBar) updatesBar.style.width = '100%';
      } else {
        updatesText.innerHTML = `${stats.updates_pending} pendientes`;
        if (updatesBar) updatesBar.style.width = '60%';
      }
    }

    // --- Cyber Dashboard Real Metrics ---
    if (stats.packages_count) {
      const heroCounter = document.getElementById('cyberHeroCounter');
      if (heroCounter) heroCounter.innerText = stats.packages_count.toLocaleString('es');
      const rightPkgs = document.getElementById('rightStatPackages');
      if (rightPkgs) rightPkgs.innerText = stats.packages_count.toLocaleString('es');
      const actAptVal = document.getElementById('actAptVal');
      if (actAptVal) actAptVal.innerText = stats.packages_count.toLocaleString('es');
    }

    if (stats.ram_available_gb !== undefined) {
      const ramAvail = document.getElementById('cyberRamAvailable');
      if (ramAvail) ramAvail.innerText = `${stats.ram_available_gb} GB`;
      const ramUsed = document.getElementById('cyberRamUsed');
      if (ramUsed) ramUsed.innerText = `${stats.ram_used_gb} GB`;
      const ramTotal = document.getElementById('cyberRamTotal');
      if (ramTotal) ramTotal.innerText = `De ${stats.ram_total_gb} GB totales`;
    }

    if (stats.process_count !== undefined) {
      const procs = document.getElementById('cyberProcs');
      if (procs) procs.innerText = `${stats.process_count}`;
    }

    if (stats.load_avg !== undefined) {
      const loadAvg = document.getElementById('cyberLoadAvg');
      if (loadAvg) loadAvg.innerText = `${stats.load_avg}`;
    }

    // --- CPU Temperature Logic ---
    const hasCpuTemp = typeof stats.cpu_temp === 'number' && Number.isFinite(stats.cpu_temp);
    const temp = hasCpuTemp ? stats.cpu_temp : null;
    const cyberCpuTemp = document.getElementById('cyberCpuTemp');
    if (cyberCpuTemp) cyberCpuTemp.innerText = hasCpuTemp ? `${temp.toFixed(1)}°C` : '—';
    const cyberTempStatus = document.getElementById('cyberTempStatus');
    if (cyberTempStatus) {
      cyberTempStatus.textContent = hasCpuTemp ? 'Sensor activo' : 'No disponible';
      cyberTempStatus.style.color = hasCpuTemp ? 'var(--accent-green)' : 'var(--text-faint)';
      cyberTempStatus.style.background = hasCpuTemp ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.1)';
    }

    // No inventar lecturas por núcleo cuando el sistema no las expone.
    for (let i = 0; i < 4; i++) {
      const coreTemp = document.getElementById(`cyberCore${i}`);
      if (coreTemp) coreTemp.innerText = '—';
    }

    if (stats.disk_percent !== undefined) {
      const diskPct = document.getElementById('cyberDiskPercent');
      if (diskPct) diskPct.innerHTML = `${stats.disk_percent}<small>%</small>`;
      const diskUsed = document.getElementById('cyberDiskUsed');
      if (diskUsed) diskUsed.innerText = `${stats.disk_used_gb} GB`;
      const diskSub = document.getElementById('cyberDiskSub');
      if (diskSub) diskSub.innerText = `De ${stats.disk_total_gb} GB · ${stats.disk_free_gb} GB libres`;
      
      const donutArc = document.getElementById('cyberDonutArc');
      if (donutArc) {
        const offset = 251.2 - (251.2 * stats.disk_percent / 100);
        donutArc.style.strokeDashoffset = `${offset}`;
      }
    }

    if (stats.updates_pending !== undefined) {
      const rightUpdates = document.getElementById('rightStatUpdates');
      if (rightUpdates) {
        rightUpdates.innerText = stats.updates_pending === 0 ? 'Al día ✓' : `${stats.updates_pending} pendientes`;
      }
    }

    if (stats.academy_total !== undefined && stats.academy_total > 0) {
      const academyLessons = document.getElementById('rightStatAcademyLessons');
      if (academyLessons) academyLessons.innerText = `${stats.academy_completed} / ${stats.academy_total}`;
      const academySub = document.getElementById('rightStatAcademySub');
      if (academySub) {
        const pct = Math.round((stats.academy_completed / stats.academy_total) * 100);
        academySub.innerText = `Lecciones completadas (${pct}% del curso)`;
      }
    }
  } catch (err) {
    console.debug("Telemetry error:", err);
  }
}

async function loadInitialInfo() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const info = await window.pywebview.api.get_distro_info();
    if (info && info.name) {
      const distroLabel = document.getElementById('distroLabel');
      if (distroLabel) {
        distroLabel.innerText = `${info.name} ${info.version || ''}`;
      }
      const cyberDistro = document.getElementById('cyberHeroDistro');
      if (cyberDistro) {
        cyberDistro.innerText = `${info.name} ${info.version || ''} · ${info.arch || ''}`;
      }
      await showFirstRunGuide(info);
    }
  } catch (err) {
    console.debug("Error loading distro info:", err);
  }
}

async function showFirstRunGuide(info) {
  let completed = false;
  try { completed = localStorage.getItem('linuxmate_first_run_v1') === 'done'; } catch (_) {}
  const dialog = document.getElementById('firstRunDialog');
  if (completed || !dialog || typeof window.pywebview?.api?.get_settings !== 'function') return;
  const distro = document.getElementById('firstRunDistro');
  const mode = document.getElementById('firstRunMode');
  if (distro) distro.textContent = `${info.name || 'Linux'} ${info.version || ''} · gestor nativo: ${info.package_manager || 'no detectado'}`;
  try {
    const settings = await window.pywebview.api.get_settings();
    if (mode && ['safe', 'readonly'].includes(settings?.security?.security_mode)) {
      mode.value = settings.security.security_mode;
    }
  } catch (_) {}
  if (!dialog.open) dialog.showModal();
}

async function completeFirstRun(openSettings) {
  const api = window.pywebview?.api;
  const mode = document.getElementById('firstRunMode')?.value || 'safe';
  const error = document.getElementById('firstRunError');
  const buttons = [document.getElementById('firstRunExplore'), document.getElementById('firstRunConfigure')];
  buttons.forEach(button => { if (button) button.disabled = true; });
  if (error) error.hidden = true;
  try {
    const saved = await api.save_settings({ llm: {}, security: { security_mode: mode }, appearance: {} });
    if (!saved?.success) throw new Error(saved?.error || 'No se pudo guardar el modo de seguridad.');
    try { localStorage.setItem('linuxmate_first_run_v1', 'done'); } catch (_) {}
    document.getElementById('firstRunDialog')?.close();
    if (openSettings) await api.open_settings_window();
  } catch (err) {
    if (error) {
      error.textContent = err.message || 'No se pudo completar la configuración.';
      error.hidden = false;
    }
  } finally {
    buttons.forEach(button => { if (button) button.disabled = false; });
  }
}

// ==========================================================================
// 9. CYBER DASHBOARD & 3D HOLOGRAPHIC GLOBE
// ==========================================================================

function switchRightTab(tabName) {
  if (tabName === 'chat') {
    if (typeof showChatSection === 'function') {
      showChatSection();
    }
    return;
  }
  if (typeof showHome === 'function') {
    showHome();
  }
}

function initEqualizerAnimation() {
  const bars = document.querySelectorAll('#equalizerBars .eq-bar');
  if (!bars.length) return;

  const baseHeights = [45, 75, 90, 60, 80, 100, 55, 85, 70, 95, 65, 40];

  setInterval(() => {
    bars.forEach((bar, idx) => {
      const base = baseHeights[idx % baseHeights.length];
      const variance = (Math.random() - 0.5) * 35;
      const target = Math.max(15, Math.min(100, Math.round(base + variance)));
      bar.style.setProperty('--h', `${target}%`);
    });
  }, 400);
}

function initCyberGlobe() {
  const canvas = document.getElementById('cyberGlobeCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const width = canvas.width || 460;
  const height = canvas.height || 460;
  const dpr = window.devicePixelRatio || 1;
  
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);

  const centerX = width / 2;
  const centerY = height / 2;
  const globeRadius = Math.min(width, height) * 0.38;

  // Generate sphere points using Fibonacci lattice
  const pointCount = 380;
  const points = [];
  const phi = Math.PI * (Math.sqrt(5) - 1); // Golden ratio

  const draculaPalette = ['#bd93f9', '#ff79c6', '#8be9fd', '#50fa7b', '#ffb86c', '#f1fa8c', '#ff5555'];
  const particleRgba = [
    '189, 147, 249', // purple
    '255, 121, 198', // pink
    '139, 233, 253', // cyan
    '80, 250, 123',  // green
    '255, 184, 108', // orange
    '241, 250, 140'  // yellow
  ];

  for (let i = 0; i < pointCount; i++) {
    const y = 1 - (i / (pointCount - 1)) * 2; // from 1 to -1
    const radiusAtY = Math.sqrt(1 - y * y);
    const theta = phi * i;
    const x = Math.cos(theta) * radiusAtY;
    const z = Math.sin(theta) * radiusAtY;

    const isHub = (i % 18 === 0);
    const hubColor = draculaPalette[i % draculaPalette.length];
    const rgbStr = particleRgba[i % particleRgba.length];

    points.push({
      x: x * globeRadius,
      y: y * globeRadius,
      z: z * globeRadius,
      isHub,
      hubColor,
      rgbStr,
      pulsePhase: Math.random() * Math.PI * 2
    });
  }

  // Precompute nearest neighbor connections for wireframe look
  const connections = [];
  const maxConnDistSq = (globeRadius * 0.35) ** 2;
  for (let i = 0; i < pointCount; i++) {
    let connected = 0;
    for (let j = i + 1; j < pointCount; j++) {
      const dx = points[i].x - points[j].x;
      const dy = points[i].y - points[j].y;
      const dz = points[i].z - points[j].z;
      const distSq = dx * dx + dy * dy + dz * dz;
      if (distSq < maxConnDistSq && connected < 2) {
        connections.push([i, j]);
        connected++;
      }
    }
  }

  // Orbital particles around equator
  const orbitCount = 48;
  const orbitRadius = globeRadius * 1.32;
  const orbitTilt = 0.45; // radians

  let rotY = 0;
  const rotX = 0.25; // tilt forward

  function render() {
    ctx.clearRect(0, 0, width, height);

    rotY += 0.005;
    const cosY = Math.cos(rotY);
    const sinY = Math.sin(rotY);
    const cosX = Math.cos(rotX);
    const sinX = Math.sin(rotX);

    // Transform and project points
    const projected = [];
    for (let i = 0; i < pointCount; i++) {
      const p = points[i];

      // Rotate around Y axis
      const x1 = p.x * cosY + p.z * sinY;
      const z1 = -p.x * sinY + p.z * cosY;

      // Rotate around X axis (tilt)
      const y2 = p.y * cosX - z1 * sinX;
      const z2 = p.y * sinX + z1 * cosX;

      // Perspective projection
      const cameraDistance = globeRadius * 2.8;
      const scale = cameraDistance / (cameraDistance + z2);
      const projX = centerX + x1 * scale;
      const projY = centerY + y2 * scale;
      const depthAlpha = Math.max(0.12, Math.min(1, (z2 + globeRadius) / (globeRadius * 2)));

      projected.push({
        x: projX,
        y: projY,
        z: z2,
        scale,
        depthAlpha,
        isHub: p.isHub,
        hubColor: p.hubColor,
        rgbStr: p.rgbStr,
        pulsePhase: p.pulsePhase
      });
    }

    // 1. Draw multi-colored wireframe connections
    ctx.lineWidth = 0.85;
    for (let k = 0; k < connections.length; k++) {
      const [i, j] = connections[k];
      const p1 = projected[i];
      const p2 = projected[j];

      // Only draw if at least one point is somewhat towards front
      if (p1.z > -globeRadius * 0.4 || p2.z > -globeRadius * 0.4) {
        const avgAlpha = (p1.depthAlpha + p2.depthAlpha) * 0.24;
        ctx.strokeStyle = `rgba(${p1.rgbStr}, ${avgAlpha})`;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // 2. Draw points and beacon hubs
    const now = Date.now() * 0.003;
    for (let i = 0; i < pointCount; i++) {
      const p = projected[i];
      const isFront = p.z > 0;

      if (p.isHub) {
        // Beacon Hub
        const hubRadius = (isFront ? 3.6 : 2.1) * p.scale;
        ctx.beginPath();
        ctx.arc(p.x, p.y, hubRadius, 0, Math.PI * 2);
        ctx.fillStyle = p.hubColor;
        ctx.shadowColor = p.hubColor;
        ctx.shadowBlur = isFront ? 11 : 3;
        ctx.fill();
        ctx.shadowBlur = 0; // reset

        if (isFront) {
          // Pulsing halo ring around hub
          const pulse = (Math.sin(now + p.pulsePhase) + 1) * 0.5;
          const ringRadius = hubRadius + pulse * 7.5;
          ctx.beginPath();
          ctx.arc(p.x, p.y, ringRadius, 0, Math.PI * 2);
          ctx.strokeStyle = p.hubColor;
          ctx.lineWidth = 1.1;
          ctx.globalAlpha = (1 - pulse) * 0.75;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      } else {
        // Standard multi-color pastel particle
        const r = (isFront ? 1.65 : 1.0) * p.scale;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isFront
          ? `rgba(${p.rgbStr}, ${p.depthAlpha * 0.88})`
          : `rgba(${p.rgbStr}, ${p.depthAlpha * 0.38})`;
        ctx.fill();
      }
    }

    // 3. Draw tilted orbital ring particles
    const cosOrbit = Math.cos(orbitTilt);
    const sinOrbit = Math.sin(orbitTilt);

    for (let o = 0; o < orbitCount; o++) {
      const angle = (o / orbitCount) * Math.PI * 2 + rotY * 1.5;
      const ox = Math.cos(angle) * orbitRadius;
      const oz = Math.sin(angle) * orbitRadius;
      // Tilt orbit
      const oy = oz * sinOrbit;
      const ozTilted = oz * cosOrbit;

      const scale = (globeRadius * 2.8) / (globeRadius * 2.8 + ozTilted);
      const px = centerX + ox * scale;
      const py = centerY + (oy * cosX - ozTilted * sinX) * scale;
      const alpha = Math.max(0.18, Math.min(0.95, (ozTilted + orbitRadius) / (orbitRadius * 2)));
      const orbColor = draculaPalette[o % draculaPalette.length];

      ctx.beginPath();
      ctx.arc(px, py, 1.45 * scale, 0, Math.PI * 2);
      ctx.fillStyle = orbColor;
      ctx.globalAlpha = alpha * 0.85;
      ctx.shadowColor = orbColor;
      ctx.shadowBlur = 5;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}


// ==========================================================================
// 10. PANEL DE CONFIGURACIÓN & GESTIÓN DE MODELOS
// ==========================================================================




function openSettingsWindow(event) {
  if (event) event.preventDefault();
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_settings_window();
  } else {
    showToast("La API no está lista", true);
  }
}
