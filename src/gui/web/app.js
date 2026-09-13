/* ==========================================================================
   LinuxMate AI — Liquid Glass Client Application Bridge
   Connects HTML/CSS/JS frontend to Python PyWebView Backend
   ========================================================================== */

// --- Global State ---
let isResizing = false;
let isChatExpanded = false;

// --- DOM Initializer ---
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSplitter();
  initTelemetryLoop();
  
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
  const savedTheme = localStorage.getItem('linuxmate_theme') || 'violet';
  applyTheme(savedTheme);
  const select = document.getElementById('themeSelect');
  if (select) select.value = savedTheme;
}

function changeTheme(themeName) {
  applyTheme(themeName);
  localStorage.setItem('linuxmate_theme', themeName);
}

function applyTheme(themeName) {
  document.body.setAttribute('data-theme', themeName);
}

// ==========================================================================
// 2. WINDOW CONTROLS (Min, Max, Close)
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
    rightPanel.style.width = '350px';
    isChatExpanded = false;
  } else {
    rightPanel.style.width = '580px';
    isChatExpanded = true;
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
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = text;
    sendChatMessage();
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  appendMessage(query, 'user');

  // Loading bubble
  const loadingId = 'loading-' + Date.now();
  appendLoadingMessage(loadingId);

  try {
    let reply = "";
    if (window.pywebview && window.pywebview.api) {
      reply = await window.pywebview.api.chat(query);
    } else {
      // Fallback preview mode
      await new Promise(r => setTimeout(r, 600));
      reply = `He recibido tu consulta: "${query}". Para tareas del sistema, utiliza los accesos rápidos o comandos validados.`;
    }
    removeLoadingMessage(loadingId);
    appendMessage(reply, 'ai');
  } catch (err) {
    console.error(err);
    removeLoadingMessage(loadingId);
    appendMessage("⚠️ Error al conectar con el asistente: " + err, 'ai');
  }
}

function appendMessage(text, sender) {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = `message message-${sender}`;

  // Simple formatting for code blocks or lines
  if (sender === 'ai') {
    msgDiv.innerHTML = formatAiResponse(text);
  } else {
    msgDiv.textContent = text;
  }

  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendLoadingMessage(id) {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;

  const msgDiv = document.createElement('div');
  msgDiv.id = id;
  msgDiv.className = 'message message-ai';
  msgDiv.innerHTML = '<span style="opacity: 0.7;">Pensando... 🤖💭</span>';
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoadingMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatAiResponse(text) {
  // Replace Markdown code blocks ```bash ... ```
  let html = text.replace(/```([a-z]*)\n([\s\S]*?)```/gi, (match, lang, code) => {
    return `<div class="chat-code-block">${escapeHtml(code.trim())}</div>`;
  });
  // Replace inline `code`
  html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:4px;color:#38bdf8;font-family:monospace;">$1</code>');
  // Replace newlines with <br>
  html = html.replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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
  if (input) input.value = '';
}

// ==========================================================================
// 6. ACTION TOOLS & RUNNER
// ==========================================================================
async function openTool(actionId, event) {
  if (event) event.preventDefault();
  
  appendMessage(`⚙️ Ejecutando acción: ${actionId.replace('_', ' ')}...`, 'user');
  
  if (window.pywebview && window.pywebview.api) {
    try {
      const res = await window.pywebview.api.run_action(actionId);
      if (res) {
        appendMessage(res, 'ai');
      }
    } catch (err) {
      appendMessage("⚠️ Error ejecutando acción: " + err, 'ai');
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
  const chatInput = document.getElementById('chatInput');
  if (chatInput) chatInput.focus();
}

// ==========================================================================
// 7. APP INSTALLER
// ==========================================================================
async function installApp(buttonElement, appId, appName) {
  const originalText = buttonElement.innerText;
  buttonElement.disabled = true;
  buttonElement.innerText = "⏳ Instalando...";
  buttonElement.style.opacity = "0.7";

  appendMessage(`📦 Solicitada instalación de ${appName}...`, 'user');

  try {
    let result = null;
    if (window.pywebview && window.pywebview.api) {
      result = await window.pywebview.api.install_app(appId);
    } else {
      await new Promise(r => setTimeout(r, 1200));
      result = { success: true, message: `Simulación: ${appName} instalado exitosamente.` };
    }

    if (result && result.success) {
      buttonElement.innerText = "✓ Listo";
      buttonElement.style.background = "linear-gradient(135deg, #10b981 0%, #059669 100%)";
      appendMessage(`✅ ${appName} se instaló correctamente.\n${result.message || ''}`, 'ai');
    } else {
      buttonElement.innerText = "Reintentar";
      buttonElement.disabled = false;
      buttonElement.style.opacity = "1";
      appendMessage(`❌ No se pudo instalar ${appName}: ${result ? result.message : 'Error desconocido'}`, 'ai');
    }
  } catch (err) {
    buttonElement.innerText = "Error";
    buttonElement.disabled = false;
    buttonElement.style.opacity = "1";
    appendMessage(`⚠️ Error durante la instalación: ${err}`, 'ai');
  }
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
    }
  } catch (err) {
    console.debug("Error loading distro info:", err);
  }
}
