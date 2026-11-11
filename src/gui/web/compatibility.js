'use strict';
// Shares the migration window's installation preview and navigation adapters.
window.CompatibilityHub = (() => {
  let tools = [], selected = 'bottles', overview = null, loading = false;
  const message = text => { $('compatStatus').textContent = text; };
  const list = (items, ordered = false) => {
    const el = node(ordered ? 'ol' : 'ul');
    items.forEach(text => el.append(node('li', text)));
    return el;
  };

  async function load() {
    if (tools.length || loading) return;
    if (!api()) {
      message('Esperando la conexión con LinuxMate…');
      $('compatRetry').hidden = false;
      return;
    }
    loading = true;
    $('compatRetry').hidden = true;
    message('Cargando guías de compatibilidad…');
    try {
      const result = await api().get_compatibility_catalog();
      if (!Array.isArray(result.tools) || !result.tools.length) throw new Error('El catálogo está vacío.');
      tools = result.tools;
      renderTools(); renderDetail();
      message('Guías locales con enlaces a las fuentes oficiales. Selecciona una herramienta.');
    } catch (err) {
      message('No se pudieron cargar las guías: ' + err.message);
      $('compatRetry').hidden = false;
    } finally { loading = false; }
  }

  function renderTools() {
    $('compatTools').replaceChildren();
    tools.forEach(tool => {
      const el = button('', () => select(tool.id));
      el.className = 'compat-tool';
      el.setAttribute('aria-pressed', String(selected === tool.id));
      el.setAttribute('aria-controls', 'compatDetail');
      const identity = node('span');
      const detected = overview?.tools[tool.id];
      identity.append(node('strong', tool.name), node('small', tool.kind),
        node('small', detected ? detected.status + (detected.formats.length ? ' · ' + detected.formats.join(', ') : '') : 'Estado sin comprobar'));
      el.append(node('span', tool.mark, 'compat-mark'), identity);
      $('compatTools').append(el);
    });
  }

  function select(id) {
    if (!tools.some(tool => tool.id === id)) return;
    selected = id;
    renderTools(); renderDetail();
  }

  function renderDetail() {
    const tool = tools.find(item => item.id === selected);
    if (!tool) return;
    const detail = $('compatDetail');
    detail.hidden = false; detail.replaceChildren();
    const title = node('h3', tool.name); title.id = 'compatDetailTitle';
    detail.append(node('span', tool.kind, 'badge'), title, node('p', tool.summary),
      node('h4', 'Cuándo elegirlo'), node('p', tool.best_for), node('p', tool.limits, 'compat-limit'));
    const state = overview?.tools[tool.id];
    if (state) detail.append(node('p', state.status + '. ' + state.note));
    detail.append(node('h4', 'Antes de empezar'), list(tool.requirements),
      node('h4', 'Preparación paso a paso'), list(tool.steps, true));
    if (tool.methods.length) {
      detail.append(node('h4', 'Instalación'));
      const actions = node('div', undefined, 'actions');
      tool.methods.forEach(method => {
        if (method.url) actions.append(link(method.label + ' ↗', method.url));
        else if (method.local) actions.append(button(method.label, async () => {
          await confirmInstall(await api().choose_local_package('migration'));
        }));
        else if (method.package) actions.append(button(method.label, () => install({
          name: tool.id === 'proton' ? 'Steam' : tool.name, package: method.package, source: method.source,
        })));
        else if (method.query) actions.append(button(method.label, () => searchPackages(method.query)));
      });
      detail.append(actions, node('p', 'La disponibilidad depende del sistema y sus repositorios. Revisa el origen antes de instalar.', 'catalog-disclaimer'));
    }
    const troubleshooting = node('details');
    troubleshooting.append(node('summary', 'Si algo no funciona'), list(tool.troubleshooting));
    detail.append(troubleshooting, node('h4', 'Consultar las fuentes'));
    tool.sources.forEach(source => detail.append(link(source.label + ' ↗', source.url)));
  }

  async function recommend(event) {
    event.preventDefault();
    const submit = $('compatRecommend'); submit.disabled = true;
    try {
      await load();
      if (!tools.length) throw new Error('Carga las guías antes de continuar.');
      const response = await api().recommend_windows_compatibility({
        use_case: $('compatUse').value, application: $('compatApp').value,
        special_requirements: $('compatSpecial').checked,
      });
      if (!response.success) throw new Error(response.message);
      const tool = tools.find(item => item.id === response.tool);
      if (!tool) throw new Error('La ruta no está en el catálogo.');
      const result = $('compatResult'); result.hidden = false; result.replaceChildren();
      result.append(node('span', 'RUTA PARA EVALUAR', 'badge'),
        node('h3', tool.name + (response.application ? ' · ' + response.application : '')),
        node('p', response.reason), node('p', response.notice, 'compat-limit'), list(response.checks));
      result.append(button('Ver guía de ' + tool.name, () => select(tool.id)));
      const alternatives = node('div', undefined, 'actions');
      alternatives.append(node('span', 'Otras rutas para comparar:'));
      response.alternatives.forEach(id => {
        const alternative = tools.find(item => item.id === id);
        if (alternative) alternatives.append(button(alternative.name, () => select(id)));
      });
      result.append(alternatives);
      select(tool.id);
    } catch (err) { message('No se pudo preparar la ruta: ' + err.message); }
    finally { submit.disabled = false; }
  }

  async function refresh() {
    $('compatRefresh').disabled = true;
    $('compatEnvironmentStatus').textContent = 'Consultando herramientas y recursos…';
    // Discard the previous snapshot so a failure cannot look like a fresh check.
    overview = null; $('compatEnvironment').replaceChildren(); $('compatNotices').replaceChildren();
    renderTools(); renderDetail();
    try {
      if (!api()) throw new Error('LinuxMate todavía no está conectado.');
      overview = await api().get_compatibility_overview();
      const machine = overview.machine;
      const metrics = [
        ['Arquitectura', machine.architecture], ['Memoria total', machine.ram_gib == null ? 'Sin datos' : machine.ram_gib + ' GiB'],
        ['Hilos de CPU', machine.cpu_threads ?? 'Sin datos'], ['Libre en carpeta personal', machine.home_free_gib == null ? 'Sin datos' : machine.home_free_gib + ' GiB'],
        ['KVM', machine.kvm_access ? 'Accesible' : machine.kvm_present ? 'Sin permiso de acceso' : 'No detectado'],
        ['Docker / Podman', [machine.docker ? 'Docker' : '', machine.podman ? 'Podman' : ''].filter(Boolean).join(' / ') || 'No detectados'],
        ['FreeRDP', machine.freerdp ? 'Detectado · versión por verificar' : 'No detectado'],
      ];
      metrics.forEach(([label, value]) => {
        const metric = node('div', undefined, 'compat-metric');
        metric.append(node('span', label), node('strong', String(value))); $('compatEnvironment').append(metric);
      });
      overview.notices.forEach(text => $('compatNotices').append(node('p', text)));
      $('compatEnvironmentStatus').textContent = 'Comprobación terminada. Los estados de las herramientas están actualizados.';
      renderTools(); renderDetail();
    } catch (err) {
      overview = null;
      $('compatEnvironmentStatus').textContent = 'No se pudo comprobar el equipo: ' + err.message;
    } finally { $('compatRefresh').disabled = false; }
  }

  $('compatForm').addEventListener('submit', recommend);
  $('compatRefresh').addEventListener('click', refresh);
  $('compatRetry').addEventListener('click', load);
  window.addEventListener('pywebviewready', () => { if (!$('compatibility').hidden) load(); });
  return {load};
})();
