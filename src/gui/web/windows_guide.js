const windowsGuideState = { kind: 'all', loaded: false };
let windowsGuideTimer = null;
let windowsGuideRequestId = 0;

const WINDOWS_GUIDE_ICONS = {
  'task-manager': 'activity', 'file-explorer': 'folder', 'control-panel': 'sliders',
  'windows-update': 'refresh', 'disk-management': 'harddrive', 'event-viewer': 'scroll',
  notepad: 'file-text', 'snipping-tool': 'scan', 'system-restore': 'history',
  'device-manager': 'cpu', powershell: 'terminal', 'start-menu': 'grid',
  'uninstall-programs': 'trash', 'wifi-network': 'wifi', bluetooth: 'bluetooth',
  printers: 'printer', 'virtual-desktops': 'layout', 'default-apps': 'apps',
  photoshop: 'image', office: 'briefcase', word: 'file-text', excel: 'chart',
  powerpoint: 'presentation', illustrator: 'pen-tool', premiere: 'video',
  audition: 'audio', paint: 'palette', 'notepad-plus': 'code', winrar: 'archive',
  vscode: 'code', chrome: 'globe', steam: 'gamepad',
};

const WINDOWS_GUIDE_ART = {
  'task-manager': ['system', 'Monitor del sistema'], 'file-explorer': ['files', 'Archivos'],
  'control-panel': ['settings', 'Configuración'], 'windows-update': ['settings', 'Actualizaciones'],
  'disk-management': ['devices', 'Discos'], 'event-viewer': ['files', 'Registros del sistema'],
  notepad: ['productivity', 'Editor de texto'], 'snipping-tool': ['creative', 'Captura de pantalla'],
  'system-restore': ['settings', 'Restauración del sistema'], 'device-manager': ['devices', 'Hardware'],
  powershell: ['developer', 'Terminal'], 'start-menu': ['apps', 'Aplicaciones'],
  'uninstall-programs': ['apps', 'Centro de software'], 'wifi-network': ['connectivity', 'Red Wi-Fi'],
  bluetooth: ['connectivity', 'Bluetooth'], printers: ['devices', 'Impresoras'],
  'virtual-desktops': ['workspace', 'Escritorios virtuales'], 'default-apps': ['apps', 'Aplicaciones predeterminadas'],
  photoshop: ['creative', 'Edición de imágenes'], office: ['productivity', 'Ofimática'],
  word: ['productivity', 'Documentos'], excel: ['productivity', 'Hojas de cálculo'],
  powerpoint: ['productivity', 'Presentaciones'], illustrator: ['creative', 'Diseño vectorial'],
  premiere: ['media', 'Edición de video'], audition: ['media', 'Edición de audio'],
  paint: ['creative', 'Dibujo digital'], 'notepad-plus': ['developer', 'Editor de código'],
  winrar: ['files', 'Archivos comprimidos'], vscode: ['developer', 'Desarrollo de software'],
  chrome: ['connectivity', 'Navegador web'], steam: ['media', 'Juegos'],
};

const WINDOWS_GUIDE_ICON_PATHS = {
  activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/>',
  sliders: '<path d="M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3"/><path d="M2 14h4m4-6h4m4 8h4"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.6 9A7 7 0 0 1 17 6l3 6M4 12l3 6a7 7 0 0 0 11.4-3"/>',
  harddrive: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 14h18m-13 2h.01M16 16h.01"/>',
  scroll: '<path d="M8 21h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H8"/><path d="M4 3h4v18H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm7 5h7m-7 4h7m-7 4h5"/>',
  'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6m-12 4h8m-8 4h8m-8 4h5"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2m12 0h2a2 2 0 0 1 2 2v2M3 17v2a2 2 0 0 0 2 2h2m12 0h2a2 2 0 0 0 2-2v-2M3 12h18"/>',
  history: '<path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5m4-1v5l3 2"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 9h6v6H9zM9 1v5m6-5v5M9 18v5m6-5v5M1 9h5m-5 6h5m12-6h5m-5 6h5"/>',
  terminal: '<path d="m4 17 6-5-6-5m8 12h8"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  trash: '<path d="M3 6h18m-2 0-1 14H6L5 6m4 0V4h6v2m-5 4v6m4-6v6"/>',
  wifi: '<path d="M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 20h.01"/><path d="M2 9a15 15 0 0 1 20 0"/>',
  bluetooth: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/>',
  printer: '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6zm12-3h.01"/>',
  layout: '<rect x="3" y="4" width="8" height="7" rx="1"/><rect x="13" y="4" width="8" height="7" rx="1"/><rect x="3" y="13" width="8" height="7" rx="1"/><rect x="13" y="13" width="8" height="7" rx="1"/>',
  apps: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
  briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12h18m-11 0v2h4v-2"/>',
  chart: '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="13" y="8" width="3" height="10"/><rect x="19" y="5" width="2" height="13"/>',
  presentation: '<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M12 16v5m-4 0h8m-8-9 3-3 3 2 3-4"/>',
  'pen-tool': '<path d="m12 19 7-7 3 3-7 7-3-3zm0 0-7-7 7-9 7 9m-7-9v9m-7 0h14"/>',
  video: '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 10 4-3v10l-4-3z"/>',
  audio: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 1.5-3.3 2 2 0 0 1 1.5-3.3H19a2 2 0 0 0 2-2A9 9 0 0 0 12 3z"/><circle cx="7.5" cy="10" r=".8"/><circle cx="10" cy="7" r=".8"/><circle cx="15" cy="7.5" r=".8"/>',
  code: '<path d="m8 8-4 4 4 4m8-8 4 4-4 4m-2-10-4 12"/>',
  archive: '<path d="M3 4h18v5H3zM5 9v11h14V9m-7 3v5m-2-2 2 2 2-2"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20m-10-10a15 15 0 0 1 0 20m0-20a15 15 0 0 0 0 20"/>',
  gamepad: '<path d="M6 11h4m-2-2v4m8-1h.01M18 10h.01M7 7h10a4 4 0 0 1 3.9 3.2l1 5a2.4 2.4 0 0 1-4 2.2l-2-1.9H8l-2 1.9a2.4 2.4 0 0 1-4-2.2l1-5A4 4 0 0 1 7 7z"/>',
};

window.addEventListener('pywebviewready', () => {
  if (!document.getElementById('windowsGuideView')?.hidden) loadWindowsGuide();
});

function openWindowsGuide(event) {
  if (event) event.preventDefault();
  setMainView('windows');
  if (!windowsGuideState.loaded) loadWindowsGuide();
  document.getElementById('windowsGuideSearch')?.focus();
}

function setWindowsGuideKind(kind) {
  if (!['all', 'feature', 'app'].includes(kind)) return;
  windowsGuideState.kind = kind;
  document.querySelectorAll('[data-windows-kind]').forEach(button => {
    const active = button.dataset.windowsKind === kind;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  window.clearTimeout(windowsGuideTimer);
  loadWindowsGuide();
}

function scheduleWindowsGuideSearch() {
  window.clearTimeout(windowsGuideTimer);
  ++windowsGuideRequestId;
  windowsGuideTimer = window.setTimeout(loadWindowsGuide, 180);
}

function showWindowsGuideMessage(message) {
  const results = document.getElementById('windowsGuideResults');
  const status = document.createElement('p');
  status.className = 'windows-guide-message';
  status.textContent = message;
  results.replaceChildren(status);
}

async function loadWindowsGuide() {
  const requestId = ++windowsGuideRequestId;
  const count = document.getElementById('windowsGuideCount');
  const query = document.getElementById('windowsGuideSearch').value.trim();
  count.textContent = 'Buscando...';
  showWindowsGuideMessage('Consultando equivalencias...');

  if (!window.pywebview?.api?.get_windows_guide) {
    count.textContent = 'Guía no disponible';
    showWindowsGuideMessage('Abre LinuxMate para consultar las equivalencias.');
    return;
  }

  try {
    const items = await window.pywebview.api.get_windows_guide(query, windowsGuideState.kind);
    if (requestId !== windowsGuideRequestId) return;
    const packages = [...new Set(items.flatMap(item => (item.searches || []).map(search => search.query)))];
    if (packages.length && window.pywebview.api.get_windows_guide_icons) {
      const icons = await window.pywebview.api.get_windows_guide_icons(packages);
      if (requestId !== windowsGuideRequestId) return;
      items.forEach(item => item.searches?.forEach(search => { search.icon = icons[search.query] || ''; }));
    }
    windowsGuideState.loaded = true;
    count.textContent = `${items.length} ${items.length === 1 ? 'resultado' : 'resultados'}`;
    if (!items.length) {
      showWindowsGuideMessage('No hay coincidencias. Prueba con el nombre de una función o programa.');
      return;
    }
    const results = document.getElementById('windowsGuideResults');
    const fragment = document.createDocumentFragment();
    items.forEach(item => fragment.appendChild(createWindowsGuideRow(item)));
    results.replaceChildren(fragment);
  } catch (_) {
    if (requestId !== windowsGuideRequestId) return;
    count.textContent = 'Guía no disponible';
    showWindowsGuideMessage('No se pudo consultar la guía. Inténtalo de nuevo.');
  }
}

function createWindowsGuideRow(item) {
  const row = document.createElement('article');
  row.className = 'windows-guide-row';

  const icon = document.createElement('span');
  icon.className = 'windows-guide-icon';
  icon.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.7');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('focusable', 'false');
  svg.innerHTML = WINDOWS_GUIDE_ICON_PATHS[WINDOWS_GUIDE_ICONS[item.id]] || WINDOWS_GUIDE_ICON_PATHS.apps;
  icon.appendChild(svg);

  const origin = document.createElement('div');
  origin.className = 'windows-guide-origin';
  const kind = document.createElement('span');
  kind.className = 'windows-guide-kind';
  kind.textContent = item.kind === 'app' ? 'Programa' : 'Función';
  const windows = document.createElement('h3');
  windows.textContent = item.windows;
  const title = document.createElement('div');
  title.className = 'windows-guide-title';
  title.append(icon, windows);
  origin.append(kind, title);

  const alternative = document.createElement('div');
  alternative.className = 'windows-guide-alternative';
  const label = document.createElement('span');
  label.className = 'windows-guide-kind';
  label.textContent = 'En Linux';
  const linux = document.createElement('strong');
  linux.textContent = item.linux;
  const linuxTitle = document.createElement('div');
  linuxTitle.className = 'windows-guide-linux-title';
  const arrow = document.createElement('span');
  arrow.className = 'windows-guide-linux-icon';
  arrow.setAttribute('aria-hidden', 'true');
  const arrowSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  arrowSvg.setAttribute('viewBox', '0 0 24 24');
  arrowSvg.setAttribute('fill', 'none');
  arrowSvg.setAttribute('stroke', 'currentColor');
  arrowSvg.setAttribute('stroke-width', '1.8');
  arrowSvg.setAttribute('stroke-linecap', 'round');
  arrowSvg.setAttribute('stroke-linejoin', 'round');
  arrowSvg.innerHTML = WINDOWS_GUIDE_ICON_PATHS.refresh;
  arrow.appendChild(arrowSvg);
  linuxTitle.append(arrow, linux);
  const art = WINDOWS_GUIDE_ART[item.id] || ['apps', 'Alternativa en Linux'];
  const illustration = document.createElement('img');
  illustration.className = 'windows-guide-illustration windows-guide-illustration-fallback';
  illustration.src = `assets/windows-guide/${art[0]}.svg`;
  illustration.alt = `Ilustración: ${art[1]}`;
  illustration.loading = 'lazy';
  const visual = document.createElement('div');
  visual.className = 'windows-guide-visual';
  visual.appendChild(linuxTitle);
  const storeIcons = document.createElement('div');
  storeIcons.className = 'windows-guide-store-icons';
  (item.searches || []).filter(search => search.icon).forEach(search => {
    const app = document.createElement('div');
    app.className = 'windows-guide-store-app';
    app.title = `Icono de ${search.name} de la tienda`;
    const image = document.createElement('img');
    image.src = search.icon;
    image.alt = `Icono de ${search.name} de la tienda de aplicaciones`;
    image.loading = 'lazy';
    image.decoding = 'async';
    image.addEventListener('load', () => { illustration.hidden = true; }, { once: true });
    image.addEventListener('error', () => {
      app.remove();
      if (!storeIcons.childElementCount) illustration.hidden = false;
    }, { once: true });
    app.appendChild(image);
    const name = document.createElement('span');
    name.textContent = search.name;
    app.appendChild(name);
    storeIcons.appendChild(app);
  });
  visual.appendChild(storeIcons);
  visual.appendChild(illustration);
  const note = document.createElement('p');
  note.textContent = item.note;
  alternative.append(label, visual, note);

  if (Array.isArray(item.searches) && item.searches.length) {
    const actions = document.createElement('div');
    actions.className = 'windows-guide-actions';
    item.searches.forEach(search => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'glass-btn glass-btn-secondary windows-guide-action';
      const icon = document.createElement('span');
      icon.className = 'ui-icon icon-search';
      icon.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.textContent = `Buscar ${search.name}`;
      button.append(icon, text);
      button.addEventListener('click', () => openWindowsCatalogSearch(search.query));
      actions.appendChild(button);
    });
    alternative.appendChild(actions);
  }

  row.append(origin, alternative);
  return row;
}

function openWindowsCatalogSearch(query) {
  const input = document.getElementById('catalogSearch');
  appCatalogState.source = 'all';
  appCatalogState.category = 'all';
  appCatalogState.query = query;
  input.value = query;
  document.querySelectorAll('.catalog-source').forEach(button => {
    button.classList.toggle('active', button.dataset.catalogSource === 'all');
  });
  document.querySelectorAll('.catalog-category').forEach(button => {
    button.classList.toggle('active', button.dataset.catalogCategory === 'all');
  });
  openTool('install_programs');
  if (appCatalogState.loaded) loadAppCatalog(true);
  window.setTimeout(() => input.focus(), 100);
}
