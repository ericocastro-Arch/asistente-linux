// Acceso a la academia desde la aplicación principal.
let academyOpening = false;
let academyPreview = null;

async function openLearning(event) {
  event?.preventDefault();
  if (academyOpening) return;
  academyOpening = true;
  try {
    if (window.pywebview?.api?.open_learning) {
      const result = await window.pywebview.api.open_learning();
      if (!result.success) throw new Error(result.message);
    } else {
      if (!academyPreview || academyPreview.closed) {
        academyPreview = window.open('academy.html', 'linuxmate-academy', 'width=1280,height=840');
      }
      if (!academyPreview) throw new Error('Permite abrir ventanas para entrar a la academia.');
      academyPreview.focus();
    }
  } catch (error) {
    showToast(error.message || 'No se pudo abrir la academia.');
  } finally {
    academyOpening = false;
  }
}

async function updateLearningProgress() {
  if (!window.pywebview?.api?.get_learning_summary) return;
  try {
    const result = await window.pywebview.api.get_learning_summary();
    if (!result.success) return;
    const percent = Math.round(result.completed / result.total * 100);
    document.getElementById('sidebarLearningPercent').textContent = `${percent}%`;
    document.getElementById('sidebarLearningCount').textContent = `${result.completed} de ${result.total} lecciones`;
    document.getElementById('sidebarLearningFill').style.width = `${percent}%`;
    document.getElementById('sidebarLearningProgress').setAttribute('aria-valuenow', percent);
    document.getElementById('heroLearningLabel').textContent = result.completed ? 'Continuar aprendiendo' : 'Explorar cursos';
  } catch (_) { /* La siguiente activación de la ventana reintenta la lectura. */ }
}

window.addEventListener('pywebviewready', updateLearningProgress);
window.addEventListener('focus', updateLearningProgress);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) updateLearningProgress();
});

let chatWindowOpening = false;

async function openChatStandaloneWindow(event) {
  event?.preventDefault();
  if (chatWindowOpening) return;
  chatWindowOpening = true;
  try {
    if (window.pywebview?.api?.open_chat_window) {
      const result = await window.pywebview.api.open_chat_window();
      if (!result.success) throw new Error(result.message);
    } else {
      window.open('chat.html', 'linuxmate-chat', 'width=540,height=760');
    }
  } catch (error) {
    showToast(error.message || 'No se pudo abrir la ventana del chat.');
  } finally {
    chatWindowOpening = false;
  }
}

function setMainView(view) {
  if (view === 'learning') { openLearning(); return; }
  const isWindows = view === 'windows';
  const isChat = view === 'chat';
  const isSettings = view === 'settings';
  const isHome = view === 'home' || (!isWindows && !isChat && !isSettings);

  const homeEl = document.getElementById('homeView');
  const windowsEl = document.getElementById('windowsGuideView');
  const chatEl = document.getElementById('chatSectionView');
  const settingsEl = document.getElementById('settingsSectionView');

  if (homeEl) homeEl.hidden = !isHome;
  if (windowsEl) windowsEl.hidden = !isWindows;
  if (chatEl) chatEl.hidden = !isChat;
  if (settingsEl) settingsEl.hidden = !isSettings;

  document.querySelectorAll('[data-main-view]').forEach(link => {
    link.classList.toggle('active', link.dataset.mainView === view);
  });
  const mainPanel = document.getElementById('mainPanel');
  if (mainPanel) mainPanel.scrollTop = 0;

  if (isChat) {
    const input = document.getElementById('chatSectionInput') || document.getElementById('chatInput');
    if (input) input.focus();
  }

  if (isSettings && typeof loadSettingsData === 'function') {
    loadSettingsData();
  }
}

function showHome(event) {
  event?.preventDefault();
  setMainView('home');
}

function showChatSection(event) {
  event?.preventDefault();
  setMainView('chat');
}

function openSettingsView(event) {
  event?.preventDefault();
  setMainView('settings');
}

