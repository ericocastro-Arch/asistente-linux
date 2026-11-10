/**
 * LinuxMate · Módulo de Bienvenida (Ventana Independiente)
 *
 * Se ejecuta en welcome.html. Muestra telemetría, permite elegir perfil,
 * seguridad y tema, y sincroniza las acciones con el Centro de Control principal.
 */
(function (global) {
  'use strict';

  const FIRST_RUN_KEY = 'linuxmate_first_run_v1';
  const THEME_KEY = 'linuxmate_theme';
  const SETUP_KEY = 'linuxmate_setup_state_v1';
  const SECURITY_MODES = ['safe', 'readonly'];

  const PROFILE_LABELS = {
    daily: 'Uso diario y migración',
    study: 'Estudio y ofimática',
    development: 'Desarrollo y DevOps',
    gaming: 'Gaming y multimedia'
  };

  const SECURITY_LABELS = {
    safe: 'Modo Seguro (Confirmación)',
    readonly: 'Solo lectura (Auditoría)'
  };

  let currentProfile = 'daily';
  let currentTheme = 'dracula';
  let currentSecurity = 'safe';
  let cachedDistroInfo = null;

  const $ = id => document.getElementById(id);
  const setText = (id, value) => {
    const el = $(id);
    if (el) el.textContent = value;
  };

  const api = () => global.pywebview?.api;

  function storageGet(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (_) {}
  }

  // ------------------------------------------------------------- UI SYNC
  function syncProfileUI(profile) {
    currentProfile = profile;
    document.querySelectorAll('[data-welcome-profile]').forEach(btn => {
      const active = btn.dataset.welcomeProfile === profile;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    setText('welcomeActiveProfileBadge', `Perfil: ${PROFILE_LABELS[profile] || 'Uso diario'}`);
  }

  function syncSecurityUI(mode) {
    const normalized = mode === 'readonly' ? 'readonly' : 'safe';
    currentSecurity = normalized;
    const select = $('firstRunMode');
    if (select && select.value !== normalized) select.value = normalized;
    document.querySelectorAll('[data-welcome-security]').forEach(btn => {
      const active = btn.dataset.welcomeSecurity === normalized;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    setText('welcomeBadgeSecurity', SECURITY_LABELS[normalized]);
  }

  function syncThemeUI(themeName) {
    currentTheme = themeName;
    document.body.setAttribute('data-theme', themeName);
    document.querySelectorAll('[data-welcome-theme]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.welcomeTheme === themeName);
    });
  }

  function selectTheme(themeName) {
    syncThemeUI(themeName);
    storageSet(THEME_KEY, themeName);
    const pyApi = api();
    if (pyApi?.welcome_navigate) {
      pyApi.welcome_navigate('', currentProfile, themeName);
    }
  }

  function selectProfile(profile) {
    if (!PROFILE_LABELS[profile]) return;
    syncProfileUI(profile);
    try {
      const existing = JSON.parse(storageGet(SETUP_KEY) || '{}');
      existing.profile = profile;
      storageSet(SETUP_KEY, JSON.stringify(existing));
    } catch (_) {}
    const pyApi = api();
    if (pyApi?.welcome_navigate) {
      pyApi.welcome_navigate('', profile, currentTheme);
    }
  }

  // ----------------------------------------------------------- TELEMETRY
  async function loadTelemetry() {
    const pyApi = api();
    let info = cachedDistroInfo;

    if (!info && pyApi?.get_distro_info) {
      try {
        info = await pyApi.get_distro_info();
        cachedDistroInfo = info;
      } catch (_) {}
    }

    const data = info || {};
    const distroFull = `${data.name || 'Linux'} ${data.version || ''}`.trim();
    const kernelArch = [data.kernel, data.arch].filter(Boolean).join(' · ') || 'Kernel Linux x86_64';
    const nativePkg = (data.package_manager || 'apt').toUpperCase();
    const managers = Array.isArray(data.available_package_managers) && data.available_package_managers.length
      ? data.available_package_managers.map(m => String(m).toUpperCase()).join(' · ')
      : `${nativePkg} · SNAP · FLATPAK`;

    setText('firstRunDistro', `${distroFull} · gestor nativo: ${data.package_manager || 'no detectado'}`);
    setText('welcomeEnvDistro', distroFull);
    setText('welcomeEnvKernel', kernelArch);
    setText('welcomeEnvManagers', managers);
    setText('welcomeBadgeDistro', distroFull);
    setText('welcomeBadgeKernel', `${data.kernel || 'Kernel Linux'} · ${nativePkg}`);

    if (pyApi?.get_settings) {
      try {
        const settings = await pyApi.get_settings();
        const mode = settings?.security?.security_mode;
        if (SECURITY_MODES.includes(mode)) syncSecurityUI(mode);
        const provider = String(settings?.llm?.provider || 'groq').toUpperCase();
        setText('welcomeEnvAi', `${provider} · Agente Activo`);
        setText('welcomeBadgeAi', `Motor ${provider} · Diagnóstico en vivo`);
      } catch (_) {}
    }
  }

  // ------------------------------------------------------- WINDOW CONTROL
  async function closeWelcomeWindow() {
    const pyApi = api();
    if (pyApi?.close_welcome_window) {
      await pyApi.close_welcome_window();
    } else {
      global.close();
    }
  }

  async function navigateTo(target) {
    const pyApi = api();
    if (pyApi?.welcome_navigate) {
      await pyApi.welcome_navigate(target, currentProfile, currentTheme);
    }
    await closeWelcomeWindow();
  }

  async function completeFirstRun({ openSettings = false, openGuidedSetup = false } = {}) {
    const pyApi = api();
    const mode = $('firstRunMode')?.value || currentSecurity || 'safe';
    const error = $('firstRunError');
    const buttons = ['firstRunExplore', 'firstRunConfigure', 'firstRunGuidedSetup'].map($);
    buttons.forEach(button => { if (button) button.disabled = true; });
    if (error) error.hidden = true;

    try {
      if (pyApi?.save_settings) {
        const saved = await pyApi.save_settings({ llm: {}, security: { security_mode: mode }, appearance: {} });
        if (!saved?.success) throw new Error(saved?.error || 'No se pudo guardar el modo de seguridad.');
      }
      storageSet(FIRST_RUN_KEY, 'done');

      if (openSettings) {
        if (pyApi?.welcome_navigate) {
          await pyApi.welcome_navigate('settings', currentProfile, currentTheme);
        } else if (pyApi?.open_settings_window) {
          await pyApi.open_settings_window();
        }
      } else if (openGuidedSetup) {
        if (pyApi?.welcome_navigate) {
          await pyApi.welcome_navigate('setup_guide', currentProfile, currentTheme);
        }
      } else {
        if (pyApi?.welcome_navigate) {
          await pyApi.welcome_navigate('dashboard', currentProfile, currentTheme);
        }
      }
      await closeWelcomeWindow();
    } catch (err) {
      if (error) {
        error.textContent = err.message || 'No se pudo completar la configuración.';
        error.hidden = false;
      }
    } finally {
      buttons.forEach(button => { if (button) button.disabled = false; });
    }
  }

  // --------------------------------------------------------------- EVENTS
  function bindEvents() {
    document.addEventListener('click', event => {
      const actionEl = event.target.closest('[data-welcome-action]');
      if (actionEl) {
        const action = actionEl.dataset.welcomeAction;
        if (action === 'close') {
          closeWelcomeWindow();
        } else if (action === 'theme') {
          selectTheme(actionEl.dataset.welcomeTheme);
        } else if (action === 'navigate') {
          navigateTo(actionEl.dataset.welcomeTarget);
        }
        return;
      }

      const profileBtn = event.target.closest('[data-welcome-profile]');
      if (profileBtn) {
        selectProfile(profileBtn.dataset.welcomeProfile);
        return;
      }

      const securityBtn = event.target.closest('[data-welcome-security]');
      if (securityBtn && SECURITY_MODES.includes(securityBtn.dataset.welcomeSecurity)) {
        syncSecurityUI(securityBtn.dataset.welcomeSecurity);
      }
    });

    $('firstRunMode')?.addEventListener('change', event => syncSecurityUI(event.target.value));
    $('firstRunExplore')?.addEventListener('click', () => completeFirstRun());
    $('firstRunConfigure')?.addEventListener('click', () => completeFirstRun({ openSettings: true }));
    $('firstRunGuidedSetup')?.addEventListener('click', () => completeFirstRun({ openGuidedSetup: true }));

    global.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeWelcomeWindow();
    });
  }

  function init() {
    try {
      const savedSetup = JSON.parse(storageGet(SETUP_KEY) || '{}');
      if (savedSetup.profile && PROFILE_LABELS[savedSetup.profile]) {
        currentProfile = savedSetup.profile;
      }
    } catch (_) {}

    const savedTheme = storageGet(THEME_KEY) || 'dracula';
    syncProfileUI(currentProfile);
    syncThemeUI(savedTheme);
    syncSecurityUI('safe');
    loadTelemetry();
  }

  bindEvents();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  global.addEventListener('pywebviewready', () => {
    loadTelemetry();
  });
})(window);
