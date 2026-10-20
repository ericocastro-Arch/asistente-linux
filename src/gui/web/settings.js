'use strict';
let settingsData = null;
let providers = [];
let selectedProvider = '';
let loadingSettings = false;
let dirty = false;
let busy = false;
let toastTimer;
const el = id => document.getElementById(id);
const api = () => window.pywebview?.api;

function showSettingsToast(message, error = false) {
  el('settingsToastMsg').textContent = message;
  el('settingsToastMsg').classList.toggle('error', error);
  el('settingsToastMsg').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el('settingsToastMsg').hidden = true; }, 6000);
}

function markDirty() {
  if (!settingsData) return;
  dirty = true;
  el('saveState').textContent = 'Cambios sin guardar';
}

function captureProvider() {
  if (!selectedProvider || !settingsData) return;
  for (const [field, id] of [['api_key', 'cfgApiKey'], ['model', 'cfgModel'], ['base_url', 'cfgBaseUrl']]) {
    settingsData.llm[`${selectedProvider}_${field}`] = el(id).value.trim();
  }
}

function selectProvider(id) {
  captureProvider();
  selectedProvider = id;
  const provider = providers.find(item => item.id === id);
  if (!provider) return;
  el('cfgProvider').value = id;
  el('providerName').textContent = provider.name;
  el('providerMonogram').textContent = provider.name.slice(0, 2).toUpperCase();
  el('providerRegion').textContent = provider.region;
  el('providerNote').textContent = provider.note || '';
  el('providerDocs').hidden = !provider.docs;
  el('providerDocs').href = provider.docs || '#';
  for (const [field, input] of [['api_key', 'cfgApiKey'], ['model', 'cfgModel'], ['base_url', 'cfgBaseUrl']]) {
    el(input).value = settingsData.llm[`${id}_${field}`] ?? provider[field] ?? '';
  }
  el('cfgApiKey').type = 'password';
  el('keyIcon').src = 'assets/lucide-eye.svg';
  el('toggleKey').setAttribute('aria-pressed', 'false');
  el('toggleKey').setAttribute('aria-label', 'Mostrar clave');
  el('toggleKey').title = 'Mostrar clave';
  el('apiKeyRow').hidden = id === 'ollama';
  el('providerModels').replaceChildren();
  if (provider.model) el('providerModels').append(new Option(provider.model, provider.model));
  el('modelStatus').textContent = '';
  el('testResultBadge').hidden = true;
}

function renderMaintenance(data) {
  const memory = data.memory || {};
  el('memTotalMessages').textContent = memory.total_messages || 0;
  el('memTotalSessions').textContent = memory.total_sessions || 0;
  el('memDbSize').textContent = `${memory.db_size_kb || 0} KB`;
  const diag = data.system_diagnostics || {};
  el('systemEnvGrid').replaceChildren();
  for (const [key, name] of [['apt', 'APT'], ['dnf', 'DNF'], ['pacman', 'Pacman'], ['zypper', 'Zypper'], ['snap', 'Snap'], ['flatpak', 'Flatpak'], ['gtk_launch', 'GTK Launcher']]) {
    const label = document.createElement('span');
    label.textContent = `${name}: ${diag[key] ? 'disponible' : 'no instalado'}`;
    label.classList.toggle('available', Boolean(diag[key]));
    el('systemEnvGrid').append(label);
  }
}

function renderKeyring(data) {
  const keyring = data.keyring || {};
  const isAvailable = Boolean(keyring.available);
  const dot = el('keyringStatusDot');
  const title = el('keyringStatusTitle');
  const desc = el('keyringStatusDesc');
  const btn = el('btnMigrateKeyring');
  const res = el('keyringMigrateResult');

  if (dot) dot.classList.toggle('active', isAvailable);
  if (title) {
    title.textContent = isAvailable
      ? `Activo: ${keyring.backend || 'Keyring del sistema'}`
      : 'Modo respaldo: Archivo .env privado (0600)';
  }
  if (desc) {
    if (isAvailable) {
      const count = (keyring.stored_providers || []).length;
      desc.textContent = count > 0
        ? `Hay ${count} clave(s) de API resguardadas en el almacén de contraseñas (${keyring.stored_providers.join(', ')}).`
        : 'El almacén está listo para guardar las claves de API de tus proveedores.';
    } else {
      desc.textContent = 'No se detectó un daemon de contraseñas de escritorio activo. Las claves se protegen con permisos estrictos (0600) en el archivo local.';
    }
  }
  if (btn) btn.disabled = !isAvailable;
  if (res) res.textContent = '';
}

async function loadSettingsData() {
  if (loadingSettings || settingsData || !api()?.get_settings) return;
  loadingSettings = true;
  try {
    const data = await api().get_settings();
    if (!Array.isArray(data.providers)) throw new Error('Reinicia LinuxMate para cargar los nuevos proveedores.');
    settingsData = data;
    providers = data.providers;
    const select = el('cfgProvider');
    select.replaceChildren();
    for (const region of [...new Set(providers.map(p => p.region))]) {
      const group = document.createElement('optgroup');
      group.label = region;
      providers.filter(p => p.region === region).forEach(p => group.append(new Option(p.name, p.id)));
      select.append(group);
    }
    select.disabled = false;
    selectProvider(data.llm.provider);
    el('providerCount').textContent = `${providers.length} opciones`;
    for (const [id, value] of [['cfgTemperature', data.llm.temperature], ['cfgSystemMode', data.llm.system_mode], ['cfgTimeout', data.llm.request_timeout], ['cfgMaxTokens', data.llm.max_tokens], ['cfgSecurityMode', data.security.security_mode], ['cfgPackagePreference', data.security.package_preference]]) el(id).value = value;
    el('lblTemperatureVal').textContent = Number(el('cfgTemperature').value).toFixed(2);
    for (const [id, field] of [['cfgChatDefaultFloat', 'chat_default_float'], ['cfgEnableBlur', 'enable_blur_effects'], ['cfgEnableNotifications', 'enable_notifications']]) el(id).checked = Boolean(data.appearance[field]);
    renderMaintenance(data);
    renderKeyring(data);
    el('saveButton').disabled = false;
    el('saveState').textContent = 'Configuración cargada';
  } catch (error) {
    settingsData = null;
    el('saveState').textContent = 'No se pudo cargar';
    showSettingsToast(error.message, true);
  } finally { loadingSettings = false; }
}

function setBusy(value) {
  busy = value;
  document.querySelectorAll('main input, main select, main button, #saveButton').forEach(input => { input.disabled = value; });
}

async function saveSettings() {
  if (!settingsData || busy) return;
  for (const id of ['cfgBaseUrl', 'cfgTimeout', 'cfgMaxTokens']) if (!el(id).reportValidity()) return;
  captureProvider();
  const payload = {
    llm: {...settingsData.llm, provider: selectedProvider, temperature: Number(el('cfgTemperature').value), system_mode: el('cfgSystemMode').value, request_timeout: Number(el('cfgTimeout').value), max_tokens: Number(el('cfgMaxTokens').value)},
    security: {security_mode: el('cfgSecurityMode').value, package_preference: el('cfgPackagePreference').value},
    appearance: {...settingsData.appearance, chat_default_float: el('cfgChatDefaultFloat').checked, enable_blur_effects: el('cfgEnableBlur').checked, enable_notifications: el('cfgEnableNotifications').checked}
  };
  setBusy(true);
  el('saveButton').textContent = 'Guardando…';
  try {
    const result = await api().save_settings(payload);
    if (!result.success) throw new Error(result.error || 'No se pudo guardar la configuración.');
    settingsData = {...settingsData, ...payload};
    dirty = false;
    el('saveState').textContent = 'Cambios guardados';
    showSettingsToast(result.message);
  } catch (error) { showSettingsToast(error.message, true); }
  finally { setBusy(false); el('saveButton').textContent = 'Guardar cambios'; }
}

async function runProviderAction(modelsOnly) {
  if (!settingsData || busy || !el('cfgBaseUrl').reportValidity()) return;
  const provider = selectedProvider;
  const key = el('cfgApiKey').value.trim();
  const model = el('cfgModel').value.trim();
  const url = el('cfgBaseUrl').value.trim();
  const badge = el('testResultBadge');
  badge.hidden = false;
  badge.classList.remove('error');
  badge.textContent = modelsOnly ? 'Consultando modelos…' : 'Probando conexión…';
  setBusy(true);
  try {
    const result = modelsOnly ? await api().list_llm_models(provider, key, url) : await api().test_llm_connection(provider, key, model, url);
    if (!result.success) throw new Error(result.error);
    if (modelsOnly) {
      el('providerModels').replaceChildren(...result.models.map(id => new Option(id, id)));
      el('modelStatus').textContent = `${result.models.length} modelos recibidos. Disponibilidad de herramientas según el modelo.`;
      badge.textContent = result.models.length ? 'Catálogo actualizado.' : 'El proveedor devolvió un catálogo vacío. Puedes escribir el modelo.';
    } else badge.textContent = result.message;
  } catch (error) { badge.textContent = error.message; badge.classList.add('error'); }
  finally { setBusy(false); }
}

function switchSettingsTab(key) {
  document.querySelectorAll('[data-tab]').forEach(button => {
    const active = button.dataset.tab === key;
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
    el(`pane-${button.dataset.tab}`).hidden = !active;
  });
}

document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => switchSettingsTab(button.dataset.tab));
  button.addEventListener('keydown', event => {
    const tabs = [...document.querySelectorAll('[data-tab]')];
    const index = tabs.indexOf(button);
    const target = {ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1}[event.key];
    if (target === undefined) return;
    event.preventDefault();
    switchSettingsTab(tabs[target].dataset.tab);
    tabs[target].focus();
  });
});
document.querySelector('main').addEventListener('input', markDirty);
el('cfgProvider').addEventListener('change', event => { selectProvider(event.target.value); markDirty(); });
el('cfgTemperature').addEventListener('input', event => { el('lblTemperatureVal').textContent = Number(event.target.value).toFixed(2); });
el('toggleKey').addEventListener('click', () => {
  const show = el('cfgApiKey').type === 'password';
  el('cfgApiKey').type = show ? 'text' : 'password';
  el('keyIcon').src = `assets/lucide-${show ? 'eye-off' : 'eye'}.svg`;
  el('toggleKey').setAttribute('aria-pressed', String(show));
  el('toggleKey').setAttribute('aria-label', show ? 'Ocultar clave' : 'Mostrar clave');
  el('toggleKey').title = show ? 'Ocultar clave' : 'Mostrar clave';
});
el('saveButton').addEventListener('click', saveSettings);
el('loadModels').addEventListener('click', () => runProviderAction(true));
el('testConnection').addEventListener('click', () => runProviderAction(false));
for (const [id, method] of [['clearMemory', 'clear_chat_memory'], ['cleanCache', 'run_system_cleanup']]) el(id).addEventListener('click', async () => {
  if (!api() || !settingsData) return;
  if (id === 'clearMemory' && !confirm('¿Vaciar las conversaciones guardadas? Esta acción no se puede deshacer.')) return;
  el(id).disabled = true;
  try {
    const result = await api()[method]();
    if (!result.success) throw new Error(result.error || 'No se pudo completar la operación.');
    showSettingsToast(result.message);
    renderMaintenance(await api().get_settings());
  } catch (error) { showSettingsToast(error.message, true); }
  finally { el(id).disabled = false; }
});
el('btnMigrateKeyring')?.addEventListener('click', async () => {
  if (!api()?.migrate_api_keys_to_keyring) return;
  const btn = el('btnMigrateKeyring');
  const res = el('keyringMigrateResult');
  btn.disabled = true;
  res.textContent = 'Migrando claves…';
  try {
    const result = await api().migrate_api_keys_to_keyring();
    if (!result.success) throw new Error(result.message || 'Error al migrar');
    res.textContent = result.message;
    showSettingsToast(result.message);
    const fresh = await api().get_settings();
    renderKeyring(fresh);
  } catch (err) {
    res.textContent = err.message;
    showSettingsToast(err.message, true);
  } finally {
    btn.disabled = false;
  }
});
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
window.addEventListener('pywebviewready', loadSettingsData);
loadSettingsData();
