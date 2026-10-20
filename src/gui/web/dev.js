(() => {
  'use strict';

  const state = {
    projects: [],
    currentProject: '',
    files: [],
    openTabs: [],
    activeFile: '',
    originalContent: '',
    pendingProposal: null,
    lastRunResult: null,
    providers: [],
    activeProvider: 'groq',
    activeModel: '',
    selectedModalProvider: 'groq',
    tutorials: [],
    tutorialIndex: 0,
    cmView: null,
    cmLangCompartment: null,
  };

  const $ = (id) => document.getElementById(id);

  function hasBridge() {
    return Boolean(window.pywebview && window.pywebview.api);
  }

  function isOk(res) {
    return Boolean(res && (res.success === true || res.ok === true));
  }

  async function callApi(method, ...args) {
    if (!hasBridge() || typeof window.pywebview.api[method] !== 'function') {
      return { success: false, message: `API ${method} no disponible fuera de PyWebView.` };
    }
    try {
      return await window.pywebview.api[method](...args);
    } catch (err) {
      return { success: false, message: String(err) };
    }
  }

  // ==================== INICIALIZACIÓN DE CODEMIRROR 6 ====================
  function initEditor() {
    const host = $('cmHost');
    const fallback = $('fallbackEditor');
    if (window.CM && host) {
      const {
        EditorView,
        EditorState,
        Compartment,
        basicSetup,
        keymap,
        indentWithTab,
        devTheme,
        devHighlighting,
        languageFor,
      } = window.CM;

      state.cmLangCompartment = new Compartment();

      const shortcuts = keymap.of([
        indentWithTab,
        {
          key: 'Mod-s',
          preventDefault: true,
          run: () => {
            saveActiveFileDirect();
            return true;
          },
        },
        {
          key: 'Mod-Enter',
          preventDefault: true,
          run: () => {
            runInSandbox();
            return true;
          },
        },
      ]);

      const startState = EditorState.create({
        doc: '# Cargando proyecto en LinuxMate Dev Studio…\n',
        extensions: [
          basicSetup,
          shortcuts,
          devTheme,
          devHighlighting,
          state.cmLangCompartment.of(languageFor('main.py')),
        ],
      });

      state.cmView = new EditorView({
        state: startState,
        parent: host,
      });
    } else if (fallback) {
      if (host) host.hidden = true;
      fallback.hidden = false;
    }
  }

  function getEditorCode() {
    if (state.cmView) {
      return state.cmView.state.doc.toString();
    }
    const fb = $('fallbackEditor');
    return fb ? fb.value : '';
  }

  function setEditorCode(content, filePath = state.activeFile) {
    const text = typeof content === 'string' ? content : '';
    if (state.cmView && window.CM) {
      const effects = [];
      if (state.cmLangCompartment) {
        effects.push(state.cmLangCompartment.reconfigure(window.CM.languageFor(filePath || 'main.py')));
      }
      state.cmView.dispatch({
        changes: { from: 0, to: state.cmView.state.doc.length, insert: text },
        effects,
      });
    } else {
      const fb = $('fallbackEditor');
      if (fb) fb.value = text;
    }
  }

  // ==================== ICONOS Y UTILIDADES ====================
  function iconForFile(path) {
    const lower = (path || '').toLowerCase();
    if (lower.endsWith('.py')) return '🐍';
    if (lower.endsWith('.sh') || lower.endsWith('.bash')) return '🐚';
    if (lower.endsWith('.js') || lower.endsWith('.mjs')) return '🟨';
    if (lower.endsWith('.html')) return '🌐';
    if (lower.endsWith('.css')) return '🎨';
    if (lower.endsWith('.md')) return '📄';
    if (lower.endsWith('.json')) return '⚙️';
    return '📃';
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function formatDiffHtml(diffText) {
    const lines = String(diffText || '').split('\n');
    return lines
      .map((line) => {
        const safe = escapeHtml(line);
        if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
          return `<span class="diff-line-hdr">${safe}</span>`;
        }
        if (line.startsWith('+')) {
          return `<span class="diff-line-add">${safe}</span>`;
        }
        if (line.startsWith('-')) {
          return `<span class="diff-line-del">${safe}</span>`;
        }
        return `${safe}\n`;
      })
      .join('');
  }

  function appendConsoleLine(text, cls = '') {
    const out = $('consoleOutput');
    if (!out) return;
    const div = document.createElement('div');
    if (cls) div.className = cls;
    div.textContent = text;
    out.appendChild(div);
    out.scrollTop = out.scrollHeight;
  }

  function setStatus(message) {
    const banner = $('statusBanner');
    if (banner) banner.textContent = message;
  }

  // ==================== CARGA DE ESTADO Y PROYECTOS ====================
  async function loadInitialStatus() {
    const res = await callApi('get_dev_status');
    if (!isOk(res)) {
      setStatus(res?.message || 'Modo vista previa (sin bridge activo).');
      return;
    }

    const rootLbl = $('workspaceRootLabel');
    if (rootLbl && res.root) {
      rootLbl.textContent = `Ruta segura: ${res.root}`;
    }

    // Estado del Sandbox Bubblewrap
    const sDot = $('sandboxDot');
    const sTxt = $('sandboxText');
    if (res.sandbox) {
      const pyVer = res.sandbox.python_version
        ? `Python ${res.sandbox.python_version.split('.').slice(0, 2).join('.')}`
        : 'Python 3';
      if (res.sandbox.available) {
        if (sDot) sDot.classList.remove('warn');
        if (sTxt) sTxt.textContent = `sandbox activo · ${pyVer}`;
      } else {
        if (sDot) sDot.classList.add('warn');
        if (sTxt) sTxt.textContent = `sandbox limitado · ${pyVer}`;
      }
    }

    state.tutorials = Array.isArray(res.tutorials) ? res.tutorials : [];
    state.providers = Array.isArray(res.providers) ? res.providers : [];
    state.activeProvider = res.active_provider || 'groq';
    state.activeModel = res.active_model || '';
    renderProviderSelectors();

    state.projects = Array.isArray(res.projects) ? res.projects : [];
    renderProjectDropdown();

    if (state.projects.length > 0) {
      const preferred =
        state.projects.find((p) => p.name === state.currentProject)?.name || state.projects[0].name;
      await selectProject(preferred);
    }
  }

  function renderProjectDropdown() {
    const sel = $('projectSelect');
    if (!sel) return;
    sel.innerHTML = '';
    for (const p of state.projects) {
      const opt = document.createElement('option');
      opt.value = p.name;
      opt.textContent = p.name;
      if (p.name === state.currentProject) opt.selected = true;
      sel.appendChild(opt);
    }
  }

  async function selectProject(projectName) {
    if (!projectName) return;
    state.currentProject = projectName;
    state.openTabs = [];
    state.activeFile = '';
    hideProposalPanel();

    const titleEl = $('currentProjectTitle');
    if (titleEl) titleEl.textContent = projectName;
    const sel = $('projectSelect');
    if (sel) sel.value = projectName;

    await refreshProjectFiles();
    await refreshCheckpoints();
  }

  async function refreshProjectFiles() {
    if (!state.currentProject) return;
    const res = await callApi('list_code_files', state.currentProject);
    if (!isOk(res)) return;
    state.files = Array.isArray(res.files) ? res.files : [];
    renderFileExplorer();

    if (!state.activeFile && state.files.length > 0) {
      const preferred =
        state.files.find((f) => f === 'main.py' || f === 'script.sh' || f === 'index.js' || f === 'index.html') ||
        state.files[0];
      await openFile(preferred);
    } else if (state.activeFile && state.files.includes(state.activeFile)) {
      await openFile(state.activeFile);
    }
  }

  function renderFileExplorer() {
    const list = $('fileList');
    if (!list) return;
    list.innerHTML = '';
    for (const file of state.files) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `fitem${file === state.activeFile ? ' on' : ''}`;
      btn.innerHTML = `<span class="ficon">${iconForFile(file)}</span><span>${escapeHtml(file)}</span>`;
      btn.addEventListener('click', () => openFile(file));
      list.appendChild(btn);
    }
  }

  function renderTabs() {
    const bar = $('editorTabs');
    if (!bar) return;
    bar.innerHTML = '';
    for (const tabPath of state.openTabs) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `etab${tabPath === state.activeFile ? ' on' : ''}`;
      btn.textContent = tabPath;
      btn.addEventListener('click', () => openFile(tabPath));
      bar.appendChild(btn);
    }
  }

  async function openFile(relPath) {
    if (!state.currentProject || !relPath) return;
    const res = await callApi('read_code_file', state.currentProject, relPath);
    if (!isOk(res)) {
      setStatus(res?.message || `No se pudo abrir ${relPath}`);
      return;
    }
    state.activeFile = relPath;
    state.originalContent = res.content || '';
    if (!state.openTabs.includes(relPath)) {
      state.openTabs.push(relPath);
    }
    const badge = $('activeFileBadge');
    if (badge) badge.textContent = relPath;

    setEditorCode(state.originalContent, relPath);
    renderFileExplorer();
    renderTabs();
    setStatus(`Editando ${state.currentProject}/${relPath}`);
  }

  // ==================== GUARDADO Y DIFF VISUAL ("NADA SIN PERMISO") ====================
  async function saveActiveFileDirect() {
    if (!state.currentProject || !state.activeFile) return;
    const content = getEditorCode();
    await callApi('create_code_checkpoint', state.currentProject, `Guardado de ${state.activeFile}`);
    const res = await callApi('save_code_file', state.currentProject, state.activeFile, content);
    if (isOk(res)) {
      state.originalContent = content;
      setStatus(`✔ Guardado ${state.activeFile} (+ snapshot automático)`);
      await refreshProjectFiles();
      await refreshCheckpoints();
    } else {
      setStatus(res?.message || 'No se pudo guardar el archivo.');
    }
  }

  async function previewManualDiff() {
    if (!state.currentProject || !state.activeFile) return;
    const content = getEditorCode();
    const res = await callApi('preview_code_change', state.currentProject, state.activeFile, content);
    if (!isOk(res)) {
      setStatus(res?.message || 'No se pudo generar el diff.');
      return;
    }
    showProposalPanel(res);
  }

  function showProposalPanel(proposal) {
    if (!proposal || !proposal.token) return;
    state.pendingProposal = proposal;
    const panel = $('diffPanel');
    const pathEl = $('diffFilePath');
    const statsEl = $('diffStatsBadge');
    const summaryEl = $('diffSummaryText');
    const diffView = $('diffCodeView');

    const targetPath = proposal.path || proposal.rel_path || state.activeFile;
    if (pathEl) pathEl.textContent = targetPath;
    if (statsEl) {
      const add = proposal.added ?? 0;
      const rem = proposal.removed ?? 0;
      statsEl.textContent = `(+${add} / -${rem} líneas)`;
    }
    if (summaryEl) {
      summaryEl.textContent =
        proposal.summary ||
        'Revisa el diff propuesto por el agente. Si aceptas, se guardará un checkpoint automático antes de escribir.';
    }
    if (diffView) {
      diffView.innerHTML = formatDiffHtml(proposal.diff || '');
      diffView.hidden = false;
    }
    if (panel) panel.hidden = false;
  }

  function hideProposalPanel() {
    state.pendingProposal = null;
    const panel = $('diffPanel');
    if (panel) panel.hidden = true;
  }

  async function acceptPendingProposal() {
    const prop = state.pendingProposal;
    if (!prop || !prop.token) return;
    const res = await callApi('apply_code_change', prop.token, true);
    if (isOk(res)) {
      const targetPath = res.path || prop.path || state.activeFile;
      appendConsoleLine(
        `✔ Cambios aplicados en ${targetPath} (checkpoint automático creado).`,
        'ok'
      );
      hideProposalPanel();
      await refreshProjectFiles();
      await openFile(targetPath);
      await refreshCheckpoints();
    } else {
      setStatus(res?.message || 'Error aplicando cambios propuestos.');
    }
  }

  async function rejectPendingProposal() {
    const prop = state.pendingProposal;
    if (prop && prop.token) {
      await callApi('apply_code_change', prop.token, false);
    }
    hideProposalPanel();
    setStatus('Propuesta rechazada. Tu archivo original no fue modificado.');
  }

  // ==================== EJECUCIÓN EN SANDBOX BUBBLEWRAP ====================
  async function runInSandbox() {
    if (!state.currentProject || !state.activeFile) return;
    const currentCode = getEditorCode();
    if (currentCode !== state.originalContent) {
      await callApi('save_code_file', state.currentProject, state.activeFile, currentCode);
      state.originalContent = currentCode;
    }

    const stdinVal = $('stdinInput')?.value || '';
    const whyBtn = $('whyFailedBtn');
    if (whyBtn) whyBtn.hidden = true;

    setStatus('▶ Ejecutando en sandbox aislado (bwrap)…');
    const out = $('consoleOutput');
    if (out) out.innerHTML = '';
    appendConsoleLine(`▶ Ejecutando ${state.activeFile} en el sandbox aislado…`, '');

    const res = await callApi('run_code_in_sandbox', state.currentProject, state.activeFile, stdinVal);
    state.lastRunResult = res;

    if (out) out.innerHTML = '';

    if (!res) {
      appendConsoleLine('✖ Sin respuesta del sandbox.', 'err');
      return;
    }

    const translated = res.translated || {};
    if (res.success) {
      appendConsoleLine(`✔ ${translated.headline || `${state.activeFile} terminado.`}`, 'ok');
      if (res.stdout && res.stdout.trim()) {
        appendConsoleLine(res.stdout.trimEnd(), '');
      }
      if (translated.hint) {
        appendConsoleLine(`⚠ ${translated.hint}`, 'warn');
      } else {
        appendConsoleLine(
          '⚠ Sugerencia del agente: puedes crear un snapshot antes de probar un cambio grande.',
          'warn'
        );
      }
      setStatus(`✔ Ejecución exitosa (${res.duration_ms || 0} ms)`);
    } else {
      appendConsoleLine(`✖ ${translated.headline || res.message || 'El programa falló.'}`, 'err');
      if (res.stderr && res.stderr.trim()) {
        appendConsoleLine(res.stderr.trimEnd(), 'err');
      }
      if (whyBtn) whyBtn.hidden = false;
      setStatus('✖ Ejecución finalizó con errores. Pulsa "¿Por qué falló?" para analizarlo.');
    }

    await refreshProjectFiles();
  }

  async function explainLastFailure() {
    if (!state.currentProject) return;
    const rawErr = state.lastRunResult?.stderr || state.lastRunResult?.message || '';
    addChatMessage('user', '¿Por qué falló mi ejecución y cómo lo solucionamos?');
    setStatus('🤖 El agente está analizando el error…');

    const res = await callApi('explain_dev_failure', state.currentProject, rawErr);
    if (isOk(res) && res.explanation) {
      const exp = res.explanation;
      addChatMessage(
        'ai',
        `¿Por qué falló?:\n${exp.cause}\n\nCómo corregirlo:\n${exp.suggestion}`,
        [{ label: 'tool: explicar_error' }]
      );
      setStatus('✔ Diagnóstico del error listo.');
    } else {
      addChatMessage('ai', res?.message || 'No pude analizar el fallo.');
    }
  }

  // ==================== CHECKPOINTS Y EXPORTACIÓN ====================
  async function refreshCheckpoints() {
    if (!state.currentProject) return;
    const res = await callApi('list_code_checkpoints', state.currentProject);
    const container = $('checkpointList');
    if (!container) return;
    container.innerHTML = '';

    const items = res?.checkpoints || [];
    if (items.length === 0) {
      container.innerHTML = '<small style="color:var(--mut);font-size:11px;">Sin snapshots aún.</small>';
      return;
    }
    for (const cp of items.slice(0, 8)) {
      const row = document.createElement('div');
      row.className = 'checkpoint-item';
      row.innerHTML = `
        <div class="checkpoint-info">
          <b>${escapeHtml(cp.label || cp.id)}</b>
          <small>${escapeHtml(cp.id)}</small>
        </div>
      `;
      const restoreBtn = document.createElement('button');
      restoreBtn.type = 'button';
      restoreBtn.className = 'mini-btn';
      restoreBtn.textContent = 'Restaurar';
      restoreBtn.addEventListener('click', async () => {
        const r = await callApi('restore_code_checkpoint', state.currentProject, cp.id);
        if (isOk(r)) {
          appendConsoleLine(`↺ Proyecto restaurado al checkpoint ${cp.label || cp.id}.`, 'ok');
          await refreshProjectFiles();
        }
      });
      row.appendChild(restoreBtn);
      container.appendChild(row);
    }
  }

  // ==================== CHAT AGÉNTICO CON TOOLS Y MULTI-PROVEEDOR ====================
  function addChatMessage(role, text, toolEvents = []) {
    const stream = $('chatStream');
    if (!stream) return;

    if (role === 'ai' && Array.isArray(toolEvents) && toolEvents.length > 0) {
      const toolsRow = document.createElement('div');
      toolsRow.className = 'tools-log';
      for (const ev of toolEvents) {
        const pill = document.createElement('span');
        pill.className = 'tool-pill';
        pill.textContent = `✔ ${ev.label || ev.tool || 'tool'}`;
        toolsRow.appendChild(pill);
      }
      stream.appendChild(toolsRow);
    }

    const msg = document.createElement('div');
    msg.className = `msg ${role === 'user' ? 'u' : 'ai'}`;
    if (role === 'user') {
      msg.textContent = text;
    } else {
      let formatted = escapeHtml(text).replace(
        /```(?:[a-zA-Z0-9_+-]+)?\n?([\s\S]*?)```/g,
        (_, code) => `<pre><code>${code.trim()}</code></pre>`
      );
      formatted = formatted.replace(/^#{1,4}\s+(.+)$/gm, '<strong>$1</strong>');
      formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      formatted = formatted.replace(/`([^`\n]+)`/g, '<code>$1</code>');
      msg.innerHTML = `<b>🤖 Agente (${escapeHtml(state.activeProvider)}):</b>${formatted.replace(/\n/g, '<br>')}`;
    }
    stream.appendChild(msg);
    stream.scrollTop = stream.scrollHeight;
  }

  function isGreetingOrIdentityQuery(rawText) {
    const norm = String(rawText || '')
      .toLowerCase()
      .replace(/[¿?¡!.,;:]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    const greetings = new Set([
      'hola', 'buenas', 'buenos dias', 'buenos días', 'buenas tardes',
      'buenas noches', 'hey', 'ey', 'que tal', 'qué tal', 'saludos',
    ]);
    if (greetings.has(norm)) return 'greeting';
    const identityPatterns = [
      'que ia eres', 'qué ia eres', 'quien eres', 'quién eres',
      'que modelo eres', 'qué modelo eres', 'cual es tu nombre', 'cuál es tu nombre',
      'como te llamas', 'cómo te llamas', 'que eres', 'qué eres',
      'que proveedor usas', 'qué proveedor usas', 'que llm eres', 'qué llm eres',
    ];
    if (identityPatterns.some((p) => norm.includes(p))) return 'identity';
    return null;
  }

  async function sendAgentPrompt(promptText) {
    const clean = String(promptText || '').trim();
    if (!clean || !state.currentProject) return;

    const currentCode = getEditorCode();
    if (state.activeFile && currentCode !== state.originalContent) {
      await callApi('save_code_file', state.currentProject, state.activeFile, currentCode);
      state.originalContent = currentCode;
    }

    addChatMessage('user', clean);
    const input = $('chatInput');
    if (input) input.value = '';

    const mode = $('agentModeSelect')?.value || 'autonomous';
    const provider = $('providerQuickSelect')?.value || state.activeProvider || '';
    const model = $('modelQuickInput')?.value?.trim() || state.activeModel || '';
    const activeObj = state.providers.find((p) => p.id === provider);
    const providerDisplayName = activeObj?.name || provider || 'IA';
    const modelDisplayName = model || activeObj?.current_model || activeObj?.model || 'modelo predeterminado';

    const quickKind = isGreetingOrIdentityQuery(clean);
    if (quickKind === 'identity') {
      addChatMessage(
        'ai',
        `Soy el **Agente de Programación de LinuxMate Dev Studio**, conectado actualmente a **${providerDisplayName}** (\`${modelDisplayName}\`). Puedo ayudarte a crear código, explicar funciones, ejecutar en el sandbox aislado o proponerte cambios con diff.`
      );
      setStatus(`✔ Conectado a ${providerDisplayName} (${modelDisplayName}).`);
      return;
    }
    if (quickKind === 'greeting') {
      addChatMessage(
        'ai',
        `¡Hola! 👋 Estoy conectado a **${providerDisplayName}** (\`${modelDisplayName}\`). ¿Qué quieres programar, modificar o preguntar?`
      );
      setStatus('✔ Agente listo.');
      return;
    }

    setStatus(`🤖 Agente pensando con ${providerDisplayName}…`);
    const sendBtn = $('sendChatBtn');
    if (sendBtn) sendBtn.disabled = true;

    const res = await callApi(
      'dev_agent_chat',
      state.currentProject,
      state.activeFile,
      clean,
      mode,
      provider,
      model
    );

    if (sendBtn) sendBtn.disabled = false;

    if (!isOk(res)) {
      addChatMessage('ai', res?.message || 'No se pudo completar la consulta al agente.');
      setStatus('✖ Error al consultar al agente.');
      return;
    }

    addChatMessage('ai', res.reply || 'Listo.', res.tool_events || []);

    if (res.proposal && res.proposal.token) {
      showProposalPanel(res.proposal);
      setStatus(`🤖 El agente propone cambios en ${res.proposal.path}. Revísalos debajo del editor.`);
    } else {
      setStatus('✔ Respuesta del agente lista.');
    }

    await refreshProjectFiles();
    await refreshCheckpoints();
  }

  // ==================== GESTOR MULTI-PROVEEDOR DE APIs IA ====================
  function renderProviderSelectors() {
    const quickSel = $('providerQuickSelect');
    const modelInput = $('modelQuickInput');
    const badge = $('activeProviderBadge');

    if (quickSel && state.providers.length > 0) {
      quickSel.innerHTML = '';
      for (const p of state.providers) {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.configured ? '● ' : '○ '}${p.name}`;
        if (p.id === state.activeProvider) opt.selected = true;
        quickSel.appendChild(opt);
      }
    }

    const activeObj = state.providers.find((p) => p.id === state.activeProvider);
    if (modelInput) {
      modelInput.value = activeObj?.current_model || activeObj?.model || state.activeModel || '';
    }
    if (badge) {
      badge.textContent = activeObj ? activeObj.name : state.activeProvider;
    }
  }

  function openProviderModal(providerId = state.activeProvider) {
    const modal = $('providerModal');
    if (!modal) return;
    modal.hidden = false;
    selectModalProvider(providerId || state.activeProvider || 'groq');
  }

  function selectModalProvider(providerId) {
    state.selectedModalProvider = providerId;
    const listEl = $('providerList');
    if (listEl) {
      listEl.innerHTML = '';
      for (const p of state.providers) {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = `provider-item${p.id === providerId ? ' active' : ''}`;
        const ready = Boolean(p.configured);
        item.innerHTML = `
          <div>
            <span class="provider-item-name">${escapeHtml(p.name)}</span>
            <span class="provider-item-model">${escapeHtml(p.current_model || p.model || '')}</span>
          </div>
          <span class="provider-status-pill${ready ? ' ready' : ''}">
            ${ready ? '✔ Configurado' : 'Sin clave'}
          </span>
        `;
        item.addEventListener('click', () => selectModalProvider(p.id));
        listEl.appendChild(item);
      }
    }

    const p = state.providers.find((x) => x.id === providerId);
    if (!p) return;

    if ($('selectedProviderName')) $('selectedProviderName').textContent = p.name;
    const noteEl = $('selectedProviderNote');
    if (noteEl) {
      noteEl.textContent = p.note || '';
      noteEl.hidden = !p.note;
    }
    const docsEl = $('selectedProviderDocs');
    const docsUrl = p.docs_url || p.docs || '';
    if (docsEl) {
      if (docsUrl) {
        docsEl.href = docsUrl;
        docsEl.hidden = false;
      } else {
        docsEl.hidden = true;
      }
    }
    if ($('providerApiKeyInput')) $('providerApiKeyInput').value = '';
    if ($('providerCurrentKeyHint')) {
      $('providerCurrentKeyHint').textContent = p.configured
        ? `Estado actual: ${p.masked_key || 'Listo'}`
        : 'Aún no hay API Key guardada para este proveedor.';
    }
    if ($('providerModelInput')) $('providerModelInput').value = p.current_model || p.model || '';
    if ($('providerBaseUrlInput')) $('providerBaseUrlInput').value = p.current_base_url || p.base_url || '';
    if ($('discoveredModelsSelect')) $('discoveredModelsSelect').hidden = true;
    if ($('providerStatusMsg')) $('providerStatusMsg').textContent = '';
  }

  // ==================== BÚSQUEDA Y TUTORIALES ====================
  async function runProjectSearch() {
    const query = $('projectSearchInput')?.value?.trim() || '';
    const strip = $('projectSearchResults');
    if (!query || !state.currentProject || !strip) return;
    const res = await callApi('search_dev_project', state.currentProject, query);
    strip.innerHTML = '';
    const matches = res?.matches || [];
    if (matches.length === 0) {
      strip.innerHTML = '<small style="color:var(--mut);">Sin coincidencias.</small>';
      return;
    }
    for (const hit of matches) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'search-hit-pill';
      btn.innerHTML = `<code>${escapeHtml(hit.file)}:${hit.line}</code> ${escapeHtml(hit.snippet)}`;
      btn.addEventListener('click', () => openFile(hit.file));
      strip.appendChild(btn);
    }
  }

  function renderCurrentTutorial() {
    const banner = $('tutorialBanner');
    if (!banner || state.tutorials.length === 0) return;
    const tut = state.tutorials[state.tutorialIndex % state.tutorials.length];
    if ($('tutorialTitle')) $('tutorialTitle').textContent = `📚 ${tut.title}`;
    const stepsEl = $('tutorialSteps');
    if (stepsEl) {
      stepsEl.innerHTML = '';
      for (const s of tut.steps || []) {
        const li = document.createElement('li');
        li.textContent = s.replace(/\*\*/g, '').replace(/\*/g, '');
        stepsEl.appendChild(li);
      }
    }
    banner.hidden = false;
  }

  // ==================== ENLACE DE EVENTOS DOM ====================
  function bindEvents() {
    $('winCloseDot')?.addEventListener('click', () => window.close());

    $('projectSelect')?.addEventListener('change', (e) => {
      selectProject(e.target.value);
    });

    $('runBtn')?.addEventListener('click', runInSandbox);
    $('saveBtn')?.addEventListener('click', saveActiveFileDirect);
    $('localDiffBtn')?.addEventListener('click', previewManualDiff);

    $('acceptDiffBtn')?.addEventListener('click', acceptPendingProposal);
    $('rejectDiffBtn')?.addEventListener('click', rejectPendingProposal);
    $('toggleDiffCodeBtn')?.addEventListener('click', () => {
      const view = $('diffCodeView');
      if (view) view.hidden = !view.hidden;
    });

    $('clearConsoleBtn')?.addEventListener('click', () => {
      const out = $('consoleOutput');
      if (out) out.innerHTML = '';
    });
    $('whyFailedBtn')?.addEventListener('click', explainLastFailure);

    // Nuevo archivo rápido en el proyecto actual
    $('newFileBtn')?.addEventListener('click', async () => {
      if (!state.currentProject) return;
      const name = window.prompt('Nombre del nuevo archivo (ej. utils.py o script.sh):', 'nuevo.py');
      if (!name) return;
      const res = await callApi('save_code_file', state.currentProject, name.trim(), '# Nuevo archivo\n');
      if (isOk(res)) {
        await refreshProjectFiles();
        await openFile(name.trim());
      } else {
        setStatus(res?.message || 'Nombre de archivo inválido.');
      }
    });

    // Barra de nuevo proyecto / plantilla
    const toggleNewProjectBar = (defaultTpl = 'organizador_descargas') => {
      const bar = $('newProjectBar');
      if (!bar) return;
      bar.hidden = false;
      if ($('newProjectTemplate')) $('newProjectTemplate').value = defaultTpl;
      $('newProjectName')?.focus();
    };
    $('triggerNewProject')?.addEventListener('click', () => toggleNewProjectBar('python'));
    $('triggerFromTemplate')?.addEventListener('click', () => toggleNewProjectBar('organizador_descargas'));
    $('cancelNewProjectBtn')?.addEventListener('click', () => {
      if ($('newProjectBar')) $('newProjectBar').hidden = true;
    });

    $('newProjectBar')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = $('newProjectName')?.value?.trim() || '';
      const tpl = $('newProjectTemplate')?.value || 'python';
      if (!name) return;
      const res = await callApi('create_dev_recipe_project', name, tpl);
      if (isOk(res)) {
        if ($('newProjectBar')) $('newProjectBar').hidden = true;
        if ($('newProjectName')) $('newProjectName').value = '';
        const statusRes = await callApi('get_dev_status');
        state.projects = statusRes?.projects || state.projects;
        renderProjectDropdown();
        await selectProject(name);
      } else {
        setStatus(res?.message || 'No se pudo crear el proyecto.');
      }
    });

    // Búsqueda
    $('searchModalBtn')?.addEventListener('click', () => {
      const bar = $('searchBar');
      if (bar) {
        bar.hidden = !bar.hidden;
        if (!bar.hidden) $('projectSearchInput')?.focus();
      }
    });
    $('projectSearchRunBtn')?.addEventListener('click', runProjectSearch);
    $('projectSearchInput')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runProjectSearch();
      }
    });
    $('projectSearchCloseBtn')?.addEventListener('click', () => {
      if ($('searchBar')) $('searchBar').hidden = true;
    });

    // Tutorial interactivo
    $('triggerTutorial')?.addEventListener('click', renderCurrentTutorial);
    $('nextTutorialBtn')?.addEventListener('click', () => {
      state.tutorialIndex += 1;
      renderCurrentTutorial();
    });
    $('closeTutorialBtn')?.addEventListener('click', () => {
      if ($('tutorialBanner')) $('tutorialBanner').hidden = true;
    });

    // Checkpoints y Exportación
    $('createCheckpointBtn')?.addEventListener('click', async () => {
      if (!state.currentProject) return;
      const res = await callApi('create_code_checkpoint', state.currentProject, 'Snapshot manual');
      if (isOk(res)) {
        appendConsoleLine(`📸 Snapshot guardado (${res.checkpoint?.id || 'ok'}).`, 'ok');
        await refreshCheckpoints();
      }
    });

    $('exportBtn')?.addEventListener('click', async () => {
      if (!state.currentProject) return;
      const res = await callApi('export_code_project', state.currentProject, 'Documentos');
      if (isOk(res)) {
        const dest = res.destination || '~/Documentos';
        appendConsoleLine(`📤 Proyecto exportado en: ${dest}`, 'ok');
        setStatus(`✔ Exportado a ${dest}`);
      } else {
        setStatus(res?.message || 'No se pudo exportar.');
      }
    });

    // Selector rápido de proveedor en barra superior
    $('providerQuickSelect')?.addEventListener('change', (e) => {
      state.activeProvider = e.target.value;
      const p = state.providers.find((x) => x.id === state.activeProvider);
      if (p) {
        state.activeModel = p.current_model || p.model || '';
        if ($('modelQuickInput')) $('modelQuickInput').value = state.activeModel;
        if ($('activeProviderBadge')) $('activeProviderBadge').textContent = p.name;
      }
    });
    $('modelQuickInput')?.addEventListener('change', (e) => {
      state.activeModel = e.target.value.trim();
    });

    // Modal Multi-Proveedor
    $('openProviderDrawerBtn')?.addEventListener('click', () => openProviderModal(state.activeProvider));
    $('closeProviderModalBtn')?.addEventListener('click', () => {
      if ($('providerModal')) $('providerModal').hidden = true;
    });
    $('toggleKeyVisibilityBtn')?.addEventListener('click', () => {
      const inp = $('providerApiKeyInput');
      if (inp) inp.type = inp.type === 'password' ? 'text' : 'password';
    });

    $('fetchModelsBtn')?.addEventListener('click', async () => {
      const pid = state.selectedModalProvider;
      const apiKey = $('providerApiKeyInput')?.value || '';
      const baseUrl = $('providerBaseUrlInput')?.value || '';
      const statusEl = $('providerStatusMsg');
      if (statusEl) statusEl.textContent = 'Consultando modelos del proveedor…';
      const res = await callApi('fetch_dev_provider_models', pid, apiKey, baseUrl);
      if (isOk(res) && Array.isArray(res.models) && res.models.length > 0) {
        const sel = $('discoveredModelsSelect');
        if (sel) {
          sel.innerHTML = '';
          for (const m of res.models) {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            sel.appendChild(opt);
          }
          sel.hidden = false;
          sel.onchange = () => {
            if ($('providerModelInput')) $('providerModelInput').value = sel.value;
          };
        }
        if (statusEl) statusEl.textContent = `✔ ${res.models.length} modelos disponibles.`;
      } else if (statusEl) {
        statusEl.textContent = res?.error || res?.message || 'No se pudieron listar los modelos.';
      }
    });

    $('testProviderBtn')?.addEventListener('click', async () => {
      const pid = state.selectedModalProvider;
      const apiKey = $('providerApiKeyInput')?.value || '';
      const model = $('providerModelInput')?.value || '';
      const baseUrl = $('providerBaseUrlInput')?.value || '';
      const statusEl = $('providerStatusMsg');
      if (statusEl) statusEl.textContent = '⚡ Probando conexión con el proveedor…';
      const res = await callApi('test_dev_provider', pid, apiKey, model, baseUrl);
      const effectiveModel = res?.recommended_model || model;
      if (res?.recommended_model && $('providerModelInput')) {
        $('providerModelInput').value = res.recommended_model;
      }
      if (isOk(res)) {
        await callApi('save_dev_provider', pid, apiKey, effectiveModel, baseUrl, true);
        const statusRes = await callApi('get_dev_status');
        if (isOk(statusRes)) {
          state.providers = statusRes.providers || state.providers;
          state.activeProvider = statusRes.active_provider || pid;
          state.activeModel = statusRes.active_model || effectiveModel;
        }
        renderProviderSelectors();
        selectModalProvider(pid);
      }
      if (statusEl) {
        statusEl.textContent = isOk(res)
          ? `✔ ${res.message || 'Conexión exitosa.'} (Guardado y activo)`
          : `✖ ${res?.error || res?.message || 'Falló la prueba.'}`;
        statusEl.style.color = isOk(res) ? 'var(--ok)' : 'var(--err)';
      }
    });

    $('providerForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pid = state.selectedModalProvider;
      const apiKey = $('providerApiKeyInput')?.value || '';
      const model = $('providerModelInput')?.value || '';
      const baseUrl = $('providerBaseUrlInput')?.value || '';
      const statusEl = $('providerStatusMsg');
      if (statusEl) statusEl.textContent = 'Guardando configuración…';
      const res = await callApi('save_dev_provider', pid, apiKey, model, baseUrl, true);
      if (isOk(res)) {
        const statusRes = await callApi('get_dev_status');
        if (isOk(statusRes)) {
          state.providers = statusRes.providers || state.providers;
          state.activeProvider = statusRes.active_provider || pid;
          state.activeModel = statusRes.active_model || model;
        }
        renderProviderSelectors();
        selectModalProvider(pid);
        if (statusEl) {
          statusEl.textContent = '✔ Proveedor guardado y activado para el Agente de Código.';
          statusEl.style.color = 'var(--ok)';
        }
      } else if (statusEl) {
        statusEl.textContent = `✖ ${res?.error || res?.message || 'No se pudo guardar.'}`;
        statusEl.style.color = 'var(--err)';
      }
    });

    // Modal Arquitectura
    $('archModalBtn')?.addEventListener('click', () => {
      if ($('archModal')) $('archModal').hidden = false;
    });
    $('closeArchModalBtn')?.addEventListener('click', () => {
      if ($('archModal')) $('archModal').hidden = true;
    });

    // Chat Agéntico
    $('chatForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      sendAgentPrompt($('chatInput')?.value || '');
    });
    $('chatInput')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentPrompt($('chatInput')?.value || '');
      }
    });
    $('clearChatBtn')?.addEventListener('click', async () => {
      if (state.currentProject) {
        await callApi('clear_dev_chat', state.currentProject);
      }
      const stream = $('chatStream');
      if (stream) {
        stream.innerHTML =
          '<div class="msg ai"><b>🤖 Agente:</b> Historial reiniciado para este proyecto. ¿Qué construimos ahora?</div>';
      }
    });

    document.querySelectorAll('.qprompt').forEach((btn) => {
      btn.addEventListener('click', () => {
        const p = btn.getAttribute('data-prompt') || '';
        sendAgentPrompt(p);
      });
    });
  }

  // ==================== ARRANQUE ====================
  document.addEventListener('DOMContentLoaded', () => {
    initEditor();
    bindEvents();
    if (hasBridge()) {
      loadInitialStatus();
    } else {
      window.addEventListener('pywebviewready', () => {
        loadInitialStatus();
      });
    }
  });
})();
