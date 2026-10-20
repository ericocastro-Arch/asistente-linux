(function () {
  'use strict';
  const courses = window.AcademyCourses;
  const core = window.AcademyCore;
  const nativeMode = location.hash === '#desktop' || new URLSearchParams(location.search).has('desktop');
  const content = document.getElementById('content');
  const modal = document.getElementById('modal');
  let state = core.normalize({}, courses);
  let ready = false;
  let category = 'Todos', level = 'Todos', order = 'recommended', query = '';
  let reviewMode = 'all', toastTimer, pendingSave = null, saving = false, writeAllowed = true;
  let practiceSession = null;
  let browserVideos = [];
  let noteCourse = 'all';
  const icons = {
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    book: '<path d="M12 5v16M3 4c4-1 7-1 9 1 2-2 5-2 9-1v15c-4-1-7-1-9 2-2-3-5-3-9-2Z"/>',
    bookmark: '<path d="M6 3h12v18l-6-4-6 4Z"/>',
    award: '<circle cx="12" cy="8" r="5"/><path d="m8 12-2 9 6-3 6 3-2-9"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    play: '<path d="m8 4 12 8-12 8Z"/>',
    flag: '<path d="M5 21V3m0 1h14l-3 4 3 4H5"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    file: '<path d="M14 3H5v18h14V8Zm0 0v5h5M8 12h8M8 16h6"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 11 3 3 5-5"/>'
    ,code: '<path d="m8 9-4 3 4 3m8-6 4 3-4 3M14 5l-4 14"/>'
    ,video: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3Z"/>'
    ,upload: '<path d="M12 16V4m-5 5 5-5 5 5M5 20h14"/>'
    ,trash: '<path d="M4 7h16m-10 4v6m4-6v6M9 7l1-3h4l1 3m3 0-1 14H7L6 7"/>'
    ,...window.AcademyExtraIcons
  };
  const dashboardUI = window.AcademyDashboard.create({courses, core, icon, escape, bar, toast, persist, openModal,
    getState: () => state, isReady: () => ready, nextCourse, render, navigate});
  function icon(name) { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.book}</svg>`; }
  function escape(value) { return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]); }
  const progress = course => state.courses[course.id];
  const percent = course => Math.round(progress(course).completed.length / course.lessons.length * 100);
  const date = value => { const d = new Date(value); return Number.isNaN(d.getTime()) ? 'Fecha no disponible' : d.toLocaleDateString('es', { year: 'numeric', month: 'long', day: 'numeric' }); };
  function toast(message) { const el = document.getElementById('toast'); el.textContent = message; el.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 4200); }
  function saveStatus(message, error = false) {
    document.getElementById('saveStatus').textContent = message;
    document.getElementById('saveStatus').classList.toggle('error', error);
    document.getElementById('retrySave').hidden = !error || !writeAllowed;
  }
  async function persist() {
    if (!writeAllowed) return;
    pendingSave = JSON.stringify(state);
    saveStatus('Guardando tu progreso…');
    if (saving) return;
    saving = true;
    while (pendingSave) {
      const snapshot = pendingSave;
      pendingSave = null;
      try {
        if (nativeMode) {
          const result = await window.pywebview.api.save_learning(JSON.parse(snapshot));
          if (!result.success) throw new Error(result.message);
        } else {
          localStorage.setItem(core.STORAGE_KEY, snapshot);
        }
        if (!pendingSave) saveStatus('✓ Progreso guardado en este equipo');
      } catch (error) {
        saveStatus(error.message || 'No se pudo guardar tu progreso.', true);
        // El estado sigue en memoria; Reintentar vuelve a enviar la versión actual.
      }
    }
    saving = false;
  }
  async function init() {
    if (ready) return;
    try {
      let raw;
      if (nativeMode) {
        if (!window.pywebview?.api?.load_learning) return;
        const result = await window.pywebview.api.load_learning();
        if (!result.success) throw new Error(result.message);
        raw = result.state;
      } else {
        raw = JSON.parse(localStorage.getItem(core.STORAGE_KEY) || '{}');
      }
      state = core.normalize(raw, courses);
      saveStatus('✓ Progreso guardado en este equipo');
    } catch (error) {
      writeAllowed = false;
      saveStatus(error.message || 'No se pudo leer el progreso anterior.', true);
      content.innerHTML = `<section class="empty-state"><h1>No pudimos cargar tu progreso</h1><p>Vuelve a abrir la academia para reintentar sin reemplazar tus datos anteriores.</p><button class="btn primary" data-action="reload">Reintentar</button></section>`;
      return;
    }
    ready = true;
    if (nativeMode && location.hash === '#desktop') history.replaceState(null, '', '?desktop=1#catalog');
    render();
  }
  function navigate(hash) { if (location.hash === `#${hash}`) render(); else location.hash = hash; }
  function route() {
    const parts = location.hash.slice(1).split('/');
    return { page: parts[0] || 'catalog', course: courses.find(c => c.id === parts[1]), index: Number(parts[2] || 0) };
  }
  function render() {
    if (!ready) return;
    dashboardUI.dispose();
    const r = route();
    document.body.dataset.page = r.page;
    applyPreferences();
    document.getElementById('focusToggle').hidden = r.page !== 'lesson';
    document.querySelectorAll('[data-nav]').forEach(link => {
      const active = link.dataset.nav === r.page || (['course', 'lesson', 'exam', 'result', 'review'].includes(r.page) && link.dataset.nav === 'my');
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    document.getElementById('enrolledCount').textContent = courses.filter(c => progress(c).enrolled).length;
    document.querySelector('.avatar').textContent = state.name ? state.name.trim().slice(0, 2).toUpperCase() : 'TÚ';
    content.className = ['lesson', 'exam'].includes(r.page) ? 'study-content' : '';
    if (['catalog', 'my', 'saved'].includes(r.page)) renderCatalog(r.page);
    else if (r.page === 'achievements') renderAchievements();
    else if (r.page === 'examples') renderExamples(r.course);
    else if (r.page === 'practice') renderPractice(r.course);
    else if (r.page === 'videos') renderVideos();
    else if (r.page === 'path') renderPath();
    else if (r.page === 'notes') renderNotes();
    else if (['sandbox', 'cheatsheet', 'activity', 'agenda'].includes(r.page)) content.innerHTML = dashboardUI.page(r.page);
    else if (!r.course) content.innerHTML = `<div class="empty-state"><h1>Ese curso no está disponible</h1><a class="btn primary" href="#catalog">Explorar cursos</a></div>`;
    else if (r.page === 'course') renderCourse(r.course);
    else if (r.page === 'lesson') renderLesson(r.course, r.index);
    else if (r.page === 'exam') renderExam(r.course);
    else if (r.page === 'result') renderResult(r.course);
    else if (r.page === 'review') renderReview(r.course);
    else navigate('catalog');
    if (!['catalog', 'my', 'saved'].includes(r.page)) dashboardUI.mount();
  }
  function applyPreferences() {
    const prefs = state.preferences;
    document.body.dataset.theme = prefs.theme;
    document.body.dataset.view = prefs.view;
    document.body.classList.toggle('effects-off', !prefs.effects);
    document.body.classList.toggle('focus-mode', prefs.focus);
    document.body.style.setProperty('--reader-font-size', `${prefs.fontSize}px`);
    document.getElementById('focusToggle').setAttribute('aria-pressed', String(prefs.focus));
    dashboardUI.refreshMotion();
  }
  function appearance() {
    const prefs = state.preferences;
    openModal(`<span class="modal-emblem">${icon('palette')}</span><span class="eyebrow">A TU MANERA</span><h2 id="dialogTitle">Tu academia, tu estilo.</h2><fieldset class="preference-field"><legend>Color de acento</legend><div class="theme-swatches">${[['electric', 'Verde terminal'], ['coral', 'Coral neón'], ['lime', 'Lima digital']].map(([id, name]) => `<label title="${name}"><input type="radio" name="academyTheme" value="${id}" ${prefs.theme === id ? 'checked' : ''}><span class="theme-swatch ${id}" aria-hidden="true"></span><span>${name}</span></label>`).join('')}</div></fieldset><label class="preference-toggle"><span>${icon('sparkles')} Efectos de luz y movimiento</span><input type="checkbox" id="academyEffects" ${prefs.effects ? 'checked' : ''}></label><div class="preference-field"><label for="academyFont">Tamaño de lectura</label><select id="academyFont">${[16, 18, 20].map(size => `<option value="${size}" ${prefs.fontSize === size ? 'selected' : ''}>${{16:'Normal',18:'Grande',20:'Extra grande'}[size]}</option>`).join('')}</select></div><div class="preference-field"><label for="weeklyGoalModal">Meta semanal de lecciones</label><select id="weeklyGoalModal">${[3,5,10].map(goal => `<option value="${goal}" ${state.weeklyGoal === goal ? 'selected' : ''}>${goal} lecciones</option>`).join('')}</select></div><div class="modal-actions"><button class="btn primary" data-action="close-modal">${icon('check')} Listo</button></div>`);
  }
  function nextCourse() {
    return courses.find(c => c.id === state.lastCourse && progress(c).enrolled && percent(c) < 100)
      || courses.find(c => progress(c).enrolled && percent(c) < 100)
      || courses.find(c => percent(c) < 100) || courses[0];
  }
  function dashboard() {
    return dashboardUI.hero(nextCourse());
  }
  function renderPath() {
    content.innerHTML = `<header class="page-heading"><span class="eyebrow">DE CERO A TU PROPIO SISTEMA</span><h1>Tu ruta de estudio</h1><p>Seis etapas. Avanza a tu ritmo y vuelve cuando lo necesites.</p></header><div class="learning-path">${courses.map((course, index) => { const p = progress(course); return `<article class="path-stage ${course.color}"><span class="path-number">${percent(course) === 100 ? icon('check') : String(index + 1).padStart(2,'0')}</span><div><span class="eyebrow">${course.category} · ${course.level}</span><h2>${course.title}</h2><p>${course.subtitle}</p><div class="path-progress">${bar(percent(course))}<span>${p.completed.length} / ${course.lessons.length} lecciones</span></div></div><a class="btn secondary" href="#${p.enrolled ? `lesson/${course.id}/${p.current}` : `course/${course.id}`}">${percent(course) === 100 ? 'Repasar' : p.enrolled ? 'Continuar' : 'Ver curso'} ${icon('arrow')}</a></article>`; }).join('')}</div>`;
  }
  function renderNotes() {
    const notes = courses.flatMap(course => Object.entries(progress(course).notes).filter(([,text]) => text.trim()).map(([index,text]) => ({course, index:Number(index), text}))).filter(item => noteCourse === 'all' || item.course.id === noteCourse);
    content.innerHTML = `<header class="page-heading feature-heading"><div><span class="eyebrow">TUS IDEAS, EN UN SOLO LUGAR</span><h1>Mis apuntes</h1><p>${notes.length} ${notes.length === 1 ? 'apunte guardado' : 'apuntes guardados'}</p></div><select id="notesCourse" aria-label="Filtrar apuntes por curso"><option value="all">Todos los cursos</option>${courses.map(c => `<option value="${c.id}" ${noteCourse === c.id ? 'selected' : ''}>${c.title}</option>`).join('')}</select></header><div class="notes-grid">${notes.length ? notes.map(({course,index,text}) => `<article class="note-entry ${course.color}"><span class="eyebrow">${course.category} · Lección ${index + 1}</span><h2>${escape(course.lessons[index].title)}</h2><p>${escape(text)}</p><a class="course-link" href="#lesson/${course.id}/${index}">Volver a mi apunte ${icon('arrow')}</a></article>`).join('') : `<div class="empty-state">${icon('notes')}<h2>Tus próximas ideas van aquí</h2><p>Los apuntes que guardes en tus lecciones aparecerán en este espacio.</p><a class="btn primary" href="#catalog">Explorar cursos ${icon('arrow')}</a></div>`}</div>`;
  }
  function bar(value, label = 'Progreso del curso') { return `<div class="progress-track" role="progressbar" aria-label="${escape(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}"><span style="width:${value}%"></span></div>`; }
  function artwork(course, small = false) {
    const previews = {
      fundamentos: ['$ whoami', 'tu próximo comienzo', '$ pwd', '/home/tu'],
      terminal: ['$ ls -la', 'ideas convertidas en comandos', '$ echo "Hola, Linux"', 'Hola, Linux'],
      administracion: ['$ systemctl status', '● sistema en funcionamiento', '$ df -h', 'espacio para tus proyectos'],
      redes: ['$ ip route', 'default via 192.168.1.1', '$ ping localhost', 'conexión estable'],
      git: ['$ git status', 'working tree clean', '$ git log --oneline', 'a1b2c3 tu primer commit'],
      contenedores: ['$ docker ps', 'CONTAINER   STATUS', 'linuxmate   Up', '$ docker compose up']
    };
    return `<div class="course-art ${course.color} ${small ? 'small' : ''}" aria-hidden="true"><span class="art-label">${course.category}</span><span class="art-number">0${courses.indexOf(course) + 1}</span><div class="course-terminal"><div class="terminal-caption"><span>${icon('code')} linuxmate ~</span><span>bash</span></div><code>${(previews[course.id] || []).map(line => `<span class="${line.startsWith('$') ? 'command' : 'output'}">${escape(line)}</span>`).join('')}</code></div>${course.id === 'fundamentos' ? '<img class="course-linux-mark" src="assets/linux-logo.png" alt="">' : ''}</div>`;
  }
  function card(course) {
    const p = progress(course), best = core.bestResult(course, p);
    return `<article class="course-card ${course.color}"><a class="course-cover" href="#course/${course.id}" aria-label="Ver curso ${escape(course.title)}">${artwork(course)}</a><div class="course-card-body"><div class="card-kicker"><span class="level-tag">${course.level}</span><button class="icon-button ${p.saved ? 'selected' : ''}" data-action="save" data-course="${course.id}" title="${p.saved ? 'Quitar de guardados' : 'Guardar curso'}" aria-label="${p.saved ? 'Quitar de guardados' : 'Guardar curso'}: ${escape(course.title)}" aria-pressed="${p.saved}">${icon('bookmark')}</button></div><h3><a href="#course/${course.id}">${course.title}</a></h3><p>${course.subtitle}</p><div class="course-meta"><span>${icon('book')} 15 lecciones</span><span>${icon('clock')} ~2 h de estudio</span></div><div class="card-bottom"><span>${icon('file')} Examen de 75 preguntas</span><strong>Gratis</strong></div>${p.enrolled ? `<div class="card-progress"><div><span>${p.completed.length} de 15 completadas</span><strong>${percent(course)}%</strong></div>${bar(percent(course))}</div>` : ''}<a class="course-link" href="#${p.enrolled ? `lesson/${course.id}/${p.current}` : `course/${course.id}`}">${p.enrolled ? 'Continuar curso' : 'Explorar curso'} ${icon('arrow')}</a>${best?.passed ? '<span class="passed-label">✓ Examen aprobado</span>' : ''}</div></article>`;
  }
  function renderCatalog(page) {
    dashboardUI.dispose();
    const enrolled = courses.filter(c => progress(c).enrolled);
    const totalDone = courses.reduce((n, c) => n + progress(c).completed.length, 0);
    let hero = '';
    if (page === 'catalog') hero = dashboard();
    if (page === 'my') hero = `<header class="page-heading"><span class="eyebrow">SIGUE CONSTRUYENDO</span><h1>Mi aprendizaje</h1><p>${state.name ? `${escape(state.name)}, c` : 'C'}ada lección cuenta. Continúa donde lo dejaste.</p></header><div class="stats-grid"><div><strong>${enrolled.length}</strong><span>cursos iniciados</span></div><div><strong>${totalDone}</strong><span>lecciones completadas</span></div><div><strong>${courses.filter(c => core.bestResult(c, progress(c))?.passed).length}</strong><span>exámenes aprobados</span></div></div>`;
    if (page === 'saved') hero = `<header class="page-heading"><span class="eyebrow">PARA TU PRÓXIMO PASO</span><h1>Cursos guardados</h1><p>Tu lista personal de cosas que quieres aprender.</p></header>`;
    const title = page === 'catalog' ? 'Elige tu siguiente nivel.' : page === 'my' ? 'Tus cursos' : 'Tu lista';
    const categories = ['Todos', ...new Set(courses.map(item => item.category))];
    content.innerHTML = `${hero}<section class="catalog-section"><div class="section-heading"><div><h2>${page === 'catalog' ? '<span class="dash-green">$</span> cursos <span class="dash-cyan">--explorar</span>' : title}</h2><p>Contenido práctico, paso a paso, desde la primera lección.</p></div><label class="sort-label">Ordenar <select id="sortSelect" aria-label="Ordenar cursos"><option value="recommended" ${order === 'recommended' ? 'selected' : ''}>Ruta recomendada</option><option value="title" ${order === 'title' ? 'selected' : ''}>Nombre del curso</option><option value="progress" ${order === 'progress' ? 'selected' : ''}>Mayor progreso</option></select></label></div><div class="catalog-controls"><div class="filter-pills" role="group" aria-label="Categorías">${categories.map(item => `<button class="pill ${category === item ? 'active' : ''}" data-action="filter" data-value="${item}" aria-pressed="${category === item}">${item}</button>`).join('')}</div><select id="levelSelect" aria-label="Nivel del curso">${['Todos', 'Principiante', 'Intermedio'].map(item => `<option value="${item}" ${level === item ? 'selected' : ''}>${item === 'Todos' ? 'Todos los niveles' : item}</option>`).join('')}</select></div><div class="result-count" id="resultCount" role="status"></div><div class="course-grid" id="courseGrid"></div></section>${page === 'catalog' ? dashboardUI.extras() : ''}<footer class="page-footer"><span class="brand-mini">linuxmate academy</span><span>Aprende hoy. Hazlo tuyo mañana.</span></footer>`;
    renderCards(page);
    const toolbar = document.createElement('div');
    toolbar.className = 'catalog-toolstrip';
    toolbar.innerHTML = `<div class="catalog-shortcuts"><a href="#practice">${icon('zap')} Prueba rápida</a><a href="#notes">${icon('notes')} Mis apuntes</a><button class="text-button" data-action="appearance">${icon('sliders')} Personalizar</button></div><div class="view-switch" role="group" aria-label="Vista del catálogo"><button class="icon-button" data-action="catalog-view" data-value="grid" aria-label="Vista de tarjetas" title="Vista de tarjetas" aria-pressed="${state.preferences.view === 'grid'}">${icon('grid')}</button><button class="icon-button" data-action="catalog-view" data-value="list" aria-label="Vista de lista" title="Vista de lista" aria-pressed="${state.preferences.view === 'list'}">${icon('list')}</button></div>`;
    document.getElementById('courseGrid').before(toolbar);
    dashboardUI.mount();
  }
  function renderCards(page = route().page) {
    const normalized = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    let list = courses.filter(c => (page !== 'my' || progress(c).enrolled) && (page !== 'saved' || progress(c).saved));
    list = list.filter(c => (category === 'Todos' || c.category === category) && (level === 'Todos' || c.level === level) && normalized([c.title, c.description, ...c.lessons.map(l => l.title)].join(' ')).includes(normalized(query)));
    if (order === 'title') list.sort((a, b) => a.title.localeCompare(b.title, 'es'));
    if (order === 'progress') list.sort((a, b) => percent(b) - percent(a));
    document.getElementById('resultCount').textContent = `${list.length} ${list.length === 1 ? 'curso disponible' : 'cursos disponibles'}${query ? ` para «${query}»` : ''}`;
    document.getElementById('courseGrid').innerHTML = list.length ? list.map(card).join('') : `<div class="empty-state">${icon(page === 'saved' ? 'bookmark' : 'search')}<h3>${page === 'my' && !courses.some(c => progress(c).enrolled) ? 'Tu primer curso te está esperando' : 'No hay cursos en esta selección'}</h3><p>${page === 'saved' ? 'Guarda cursos con el marcador de cada tarjeta o ajusta tus filtros.' : 'Explora el catálogo o prueba otra búsqueda.'}</p><button class="btn secondary" data-action="reset-filters">Ver todos los cursos</button></div>`;
  }
  function breadcrumbs(course, tail = '') { return `<nav class="breadcrumbs" aria-label="Ubicación"><a href="#catalog">Cursos</a>${icon('chevron')}<a href="#course/${course.id}">${course.title}</a>${tail ? `${icon('chevron')}<span>${escape(tail)}</span>` : ''}</nav>`; }
  function renderCourse(course) {
    const p = progress(course);
    content.innerHTML = `${breadcrumbs(course)}<section class="course-overview"><div><span class="eyebrow">${course.category.toUpperCase()} · ${course.level.toUpperCase()}</span><h1>${course.title}</h1><p class="lead">${course.description}</p><div class="overview-meta"><span>${icon('book')} 5 módulos · 15 lecciones</span><span>${icon('clock')} ~2 h + examen a tu ritmo</span><span>Español</span></div><p class="author-line"><span class="author-avatar">LM</span> Contenido de LinuxMate Academy <span>· Curso de lectura y práctica</span></p></div>${artwork(course)}</section><div class="detail-layout"><div><section class="white-panel"><h2>Lo que vas a aprender</h2><ul class="outcomes">${course.outcomes.map(item => `<li>${icon('check')}${item}</li>`).join('')}</ul></section><section class="curriculum"><div class="section-heading"><h2>Contenido del curso</h2><span>15 lecciones · 75 preguntas</span></div>${course.modules.map((title, mi) => `<details ${mi === 0 ? 'open' : ''}><summary><span><b>0${mi + 1}</b> ${title}</span><small>3 lecciones · 24 min</small></summary><div>${course.lessons.map((lesson, li) => lesson.module === mi ? `<a class="curriculum-lesson" href="#lesson/${course.id}/${li}"><span>${icon(p.completed.includes(li) ? 'check' : 'file')}${lesson.title}</span><small>${lesson.minutes} min ${icon('chevron')}</small></a>` : '').join('')}</div></details>`).join('')}<button class="exam-curriculum" data-action="exam-intro" data-course="${course.id}">${icon('award')}<span><strong>Examen final del curso</strong><small>75 preguntas · Aprobación: 53 aciertos · Reintentos disponibles</small></span>${icon('arrow')}</button></section><section class="white-panel"><h2>Antes de empezar</h2><p>${course.requirements}</p><h3>Material de consulta</h3><p class="muted">El curso funciona sin conexión. Estos manuales externos requieren internet.</p><div class="resource-links">${course.resources.map(([label, url]) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`).join('')}</div></section></div><aside class="enroll-panel white-panel"><span class="eyebrow">APRENDE SIN LÍMITES</span><h2>Acceso gratuito</h2><p>Todo el contenido, desde el primer día.</p><button class="btn primary full" data-action="enroll" data-course="${course.id}">${p.enrolled ? 'Continuar aprendiendo' : 'Empezar este curso'} ${icon('arrow')}</button><button class="btn secondary full" data-action="save" data-course="${course.id}" aria-pressed="${p.saved}">${icon('bookmark')} ${p.saved ? 'Guardado en tu lista' : 'Guardar para después'}</button>${p.enrolled ? `<div class="enroll-progress"><strong>${percent(course)}% completado</strong>${bar(percent(course))}<small>${p.completed.length} de 15 lecciones</small></div>` : ''}<ul class="includes"><li>${icon('file')} Lecciones con ejemplos explicados</li><li>${icon('book')} Prácticas y apuntes personales</li><li>${icon('award')} Examen de 75 preguntas</li><li>${icon('check')} Corrección y repaso por módulo</li><li>${icon('shield')} Progreso guardado en tu equipo</li></ul><p class="tiny">Al completar las lecciones y aprobar, obtienes una constancia personal de autoestudio de LinuxMate.</p></aside></div>`;
  }
  function renderLesson(course, requestedIndex) {
    const li = Number.isInteger(requestedIndex) && requestedIndex >= 0 && requestedIndex < course.lessons.length ? requestedIndex : 0;
    const p = progress(course), lesson = course.lessons[li];
    if (state.lastCourse !== course.id) { state.lastCourse = course.id; persist(); }
    if (!p.enrolled || p.current !== li) { p.enrolled = true; p.current = li; persist(); document.getElementById('enrolledCount').textContent = courses.filter(c => progress(c).enrolled).length; }
    const done = p.completed.includes(li);
    content.innerHTML = `${breadcrumbs(course, `Lección ${li + 1}`)}<div class="study-layout"><aside class="lesson-outline"><a class="back-link" href="#course/${course.id}">← Volver al curso</a><h2>${course.title}</h2><div class="outline-progress"><strong>${percent(course)}%</strong><span>${p.completed.length} de 15 lecciones</span></div>${bar(percent(course))}<nav aria-label="Lecciones del curso">${course.modules.map((title, mi) => `<details ${lesson.module === mi ? 'open' : ''}><summary><b>0${mi + 1}</b> ${title}</summary>${course.lessons.map((l, index) => l.module === mi ? `<a class="outline-lesson ${index === li ? 'active' : ''}" href="#lesson/${course.id}/${index}" ${index === li ? 'aria-current="step"' : ''}><span class="lesson-check ${p.completed.includes(index) ? 'done' : ''}">${p.completed.includes(index) ? '✓' : String(index + 1).padStart(2, '0')}</span><span>${l.title}</span></a>` : '').join('')}</details>`).join('')}</nav><button class="btn secondary full" data-action="exam-intro" data-course="${course.id}">${icon('award')} Examen final</button></aside><article class="lesson-reader"><div class="reader-topline"><span class="eyebrow">MÓDULO ${lesson.module + 1} · LECCIÓN ${li + 1} DE 15</span><span>${icon('clock')} ${lesson.minutes} min</span></div><h1>${lesson.title}</h1><span class="lesson-state ${done ? 'complete' : ''}">${done ? '✓ Lección completada' : 'Lectura y práctica'}</span><div class="lesson-prose">${lesson.paragraphs.map(paragraph => `<p>${escape(paragraph)}</p>`).join('')}</div><section class="code-example"><header><span>${icon('file')} Ejemplo explicado · Bash</span><button class="copy-button" data-action="copy" data-course="${course.id}" data-index="${li}">Copiar</button></header><pre><code>${escape(lesson.command)}</code></pre><p>${escape(lesson.detail)}</p></section><section class="practice-box"><span class="eyebrow">AHORA TE TOCA A TI</span><h2>Una pequeña práctica</h2><p>${escape(lesson.practice)}</p><small>Los ejemplos se copian como texto. Practica en tu propia carpeta de pruebas.</small></section><section class="notes-section"><label for="lessonNotes">${icon('file')} Tus apuntes de esta lección</label><textarea id="lessonNotes" data-course="${course.id}" data-index="${li}" maxlength="4000" rows="4" placeholder="Escribe lo que quieras recordar, tus dudas o el resultado de la práctica…">${escape(p.notes[li] || '')}</textarea><small>Se guardan automáticamente en este equipo. Evita incluir contraseñas.</small></section><div class="reader-actions"><a class="btn secondary ${li === 0 ? 'disabled-link' : ''}" ${li === 0 ? 'aria-disabled="true" tabindex="-1"' : `href="#lesson/${course.id}/${li - 1}"`}>← Anterior</a><button class="btn primary" data-action="complete" data-course="${course.id}" data-index="${li}">${done ? (li === 14 ? 'Ir al examen' : 'Siguiente lección') : (li === 14 ? 'Completar e ir al examen' : 'Completar y continuar')} ${icon('arrow')}</button></div></article></div>`;
  }
  function openModal(html) {
    document.getElementById('modalBody').innerHTML = `<button class="modal-close icon-button" data-action="close-modal" aria-label="Cerrar diálogo">${icon('close')}</button>${html}`;
    modal.showModal();
    modal.setAttribute('aria-labelledby', 'dialogTitle');
  }
  function examIntro(course) {
    const p = progress(course), active = p.exam && !p.exam.finished;
    openModal(`<span class="modal-emblem">${icon('award')}</span><span class="eyebrow">PON A PRUEBA LO APRENDIDO</span><h2 id="dialogTitle">${active ? 'Continúa tu examen' : 'Tu examen de ' + course.category.toLowerCase()}</h2><p>${course.title}</p><div class="exam-facts"><div><strong>75</strong><span>preguntas</span></div><div><strong>53</strong><span>aciertos para aprobar</span></div><div><strong>A tu ritmo</strong><span>sin límite de tiempo</span></div></div><ul class="modal-list"><li>Una respuesta correcta por pregunta. Cada acierto vale un punto.</li><li>Puedes marcar preguntas y cambiar respuestas antes de entregar.</li><li>Las respuestas se guardan para continuar después.</li><li>Al entregar verás tu resultado, las respuestas y sus explicaciones.</li></ul>${active ? `<p class="info-box">Tienes ${p.exam.answers.filter(a => a !== null).length} respuestas guardadas.</p>` : '<p class="muted">Puedes intentarlo varias veces. Recomendamos terminar las lecciones primero.</p>'}<button class="btn primary full" data-action="start-exam" data-course="${course.id}">${active ? 'Retomar examen' : 'Comenzar examen'} ${icon('arrow')}</button>${p.exam?.finished ? `<a class="result-shortcut" href="#result/${course.id}" data-action="close-link">Ver el último resultado</a>` : ''}`);
  }
  function renderExam(course) {
    const p = progress(course), exam = p.exam;
    if (!exam) { renderCourse(course); examIntro(course); return; }
    if (exam.finished) { navigate(`result/${course.id}`); return; }
    const index = exam.index, question = course.questions[index];
    const answered = exam.answers.filter(a => a !== null).length;
    content.innerHTML = `${breadcrumbs(course, 'Examen final')}<div class="exam-header"><div><span class="eyebrow">EXAMEN FINAL · ${course.title.toUpperCase()}</span><h1>Demuestra lo que sabes.</h1></div><a href="#course/${course.id}" class="btn secondary">Guardar y salir</a></div><div class="exam-layout"><section class="question-panel white-panel"><div class="question-top"><span>Pregunta <b>${index + 1}</b> de 75</span><button class="flag-button ${exam.flagged.includes(index) ? 'flagged' : ''}" data-action="flag" data-course="${course.id}" aria-pressed="${exam.flagged.includes(index)}">${icon('flag')} ${exam.flagged.includes(index) ? 'Marcada para revisar' : 'Marcar para revisar'}</button></div>${bar(Math.round(answered / 75 * 100), 'Preguntas respondidas')}<span class="question-module">${course.modules[question.module]}</span><fieldset class="question-fieldset"><legend>${escape(question.text)}</legend>${question.choices.map((choice, i) => `<label class="answer-option ${exam.answers[index] === i ? 'chosen' : ''}"><input type="radio" name="examAnswer" value="${i}" data-course="${course.id}" ${exam.answers[index] === i ? 'checked' : ''}><span class="answer-letter">${String.fromCharCode(65 + i)}</span><span>${escape(choice)}</span></label>`).join('')}</fieldset><div class="question-actions"><button class="btn secondary" data-action="question" data-course="${course.id}" data-index="${index - 1}" ${index === 0 ? 'disabled' : ''}>← Anterior</button><span>${exam.answers[index] === null ? 'Sin responder' : 'Respuesta seleccionada'}</span><button class="btn primary" data-action="${index === 74 ? 'finish-intro' : 'question'}" data-course="${course.id}" data-index="${index + 1}">${index === 74 ? 'Revisar entrega' : 'Siguiente →'}</button></div></section><aside class="question-map white-panel"><h2>Tu recorrido</h2><p id="answeredCount">${answered} de 75 respondidas</p><div class="question-numbers" aria-label="Navegador de preguntas">${course.questions.map((q, i) => `<button class="question-number ${exam.answers[i] !== null ? 'answered' : ''} ${exam.flagged.includes(i) ? 'marked' : ''} ${i === index ? 'current' : ''}" data-action="question" data-course="${course.id}" data-index="${i}" aria-label="Pregunta ${i + 1}${exam.answers[i] !== null ? ', respondida' : ', sin responder'}${exam.flagged.includes(i) ? ', marcada' : ''}" ${i === index ? 'aria-current="step"' : ''}>${i + 1}</button>`).join('')}</div><div class="map-legend"><span><i class="legend-answered"></i>Respondida</span><span><i class="legend-marked"></i>Por revisar</span></div><button class="btn primary full" data-action="finish-intro" data-course="${course.id}">Entregar examen</button><p class="tiny">Puedes cerrar y retomar. El resultado aparecerá al entregar las 75 respuestas.</p></aside></div>`;
  }
  function finishIntro(course) {
    const exam = progress(course).exam;
    if (!exam || exam.finished) return;
    const remaining = exam.answers.filter(a => a === null).length;
    openModal(`<span class="modal-emblem">${icon('file')}</span><h2 id="dialogTitle">${remaining ? 'Todavía quedan preguntas' : 'Todo listo para entregar'}</h2><p>${remaining ? `Te faltan ${remaining} de las 75 respuestas. Completa todas para recibir tu resultado.` : 'Has respondido las 75 preguntas. Después de entregar podrás revisar la corrección y comenzar otro intento.'}</p>${exam.flagged.length ? `<p class="info-box">Marcaste ${exam.flagged.length} preguntas para revisar.</p>` : ''}<div class="modal-actions"><button class="btn secondary" data-action="close-modal">Seguir revisando</button><button class="btn primary" data-action="${remaining ? 'first-unanswered' : 'submit-exam'}" data-course="${course.id}">${remaining ? 'Ir a la primera pendiente' : 'Confirmar entrega'}</button></div>`);
  }
  function renderResult(course) {
    const p = progress(course), exam = p.exam;
    if (!exam?.finished) { navigate(`exam/${course.id}`); return; }
    const result = core.grade(course, exam), best = core.bestResult(course, p);
    content.innerHTML = `${breadcrumbs(course, 'Resultado')}<section class="result-hero ${result.passed ? 'success' : ''}"><div class="score-circle" style="--score:${result.percent}%"><span><strong>${result.percent}%</strong><small>${result.correct} de 75</small></span></div><div><span class="eyebrow">${result.passed ? 'EXAMEN APROBADO' : 'UN PASO MÁS EN TU APRENDIZAJE'}</span><h1>${result.passed ? 'Lo aprendiste. Lo demostraste.' : 'Cada intento te enseña algo.'}</h1><p>${result.passed ? 'Has superado el examen de ' + course.title + '.' : 'Necesitas 53 aciertos para aprobar. Repasa tus respuestas y vuelve cuando quieras.'}</p><span class="muted">${date(exam.finished)} · Mejor resultado: ${best.correct}/75</span><div class="result-actions"><a class="btn primary" href="#review/${course.id}">Revisar mis respuestas ${icon('arrow')}</a><button class="btn secondary" data-action="exam-intro" data-course="${course.id}">Volver a intentar</button></div></div></section><section class="white-panel"><h2>Así te fue en cada módulo</h2><div class="module-results">${result.modules.map((item, i) => `<div><a href="#lesson/${course.id}/${i * 3}"><b>0${i + 1}</b> ${item.title}</a>${bar(Math.round(item.correct / item.total * 100), item.title)}<strong>${item.correct}/${item.total}</strong></div>`).join('')}</div></section><section class="completion-banner">${icon('award')}<div><h2>${core.certificateReady(course, p) ? 'Tu constancia está lista' : 'Completa tu recorrido'}</h2><p>${core.certificateReady(course, p) ? 'Un recuerdo de las habilidades que estás construyendo.' : `${p.completed.length}/15 lecciones completadas. La constancia requiere todas las lecciones y un examen aprobado.`}</p></div>${core.certificateReady(course, p) ? `<button class="btn secondary" data-action="certificate" data-course="${course.id}">Ver constancia</button>` : `<a class="btn secondary" href="#lesson/${course.id}/${p.current}">Volver a las lecciones</a>`}</section><section class="white-panel"><h2>Tus últimos intentos</h2><div class="attempt-list">${p.attempts.slice().reverse().map((attempt, i) => { const result = core.grade(course, attempt); return `<div><span>Intento ${p.attempts.length - i} · ${date(attempt.finished)}</span><strong>${result.correct}/75 · ${result.passed ? 'Aprobado' : 'Para repasar'}</strong></div>`; }).join('')}</div><p class="tiny">Se conservan los últimos diez intentos de este curso.</p></section>`;
  }
  function renderReview(course) {
    const exam = progress(course).exam;
    if (!exam?.finished) { navigate(`exam/${course.id}`); return; }
    const list = course.questions.map((question, index) => ({ question, index })).filter(({ question, index }) => reviewMode !== 'incorrect' || exam.answers[index] !== question.answer);
    content.innerHTML = `${breadcrumbs(course, 'Repaso')}<header class="page-heading"><span class="eyebrow">APRENDE DE CADA RESPUESTA</span><h1>Repaso del examen</h1><p>${course.title} · <a href="#result/${course.id}">Volver a mi resultado</a></p></header><div class="filter-pills review-filters"><button class="pill ${reviewMode === 'all' ? 'active' : ''}" data-action="review-filter" data-value="all" aria-pressed="${reviewMode === 'all'}">Todas las respuestas</button><button class="pill ${reviewMode === 'incorrect' ? 'active' : ''}" data-action="review-filter" data-value="incorrect" aria-pressed="${reviewMode === 'incorrect'}">Solo incorrectas</button><span>${list.length} preguntas</span></div><div class="review-list">${list.length ? list.map(({ question: q, index }) => `<article class="white-panel review-item"><span class="review-status ${exam.answers[index] === q.answer ? 'correct' : 'incorrect'}">${exam.answers[index] === q.answer ? '✓ Correcta' : '× Para repasar'} · Pregunta ${index + 1}</span><h2>${escape(q.text)}</h2><p><strong>Tu respuesta:</strong> ${escape(q.choices[exam.answers[index]] ?? 'Sin responder')}</p>${exam.answers[index] !== q.answer ? `<p class="correct-answer"><strong>Respuesta correcta:</strong> ${escape(q.choices[q.answer])}</p>` : ''}<p class="explanation">${escape(q.explanation)}</p><a href="#lesson/${course.id}/${q.lesson}">Repasar: ${course.lessons[q.lesson].title} →</a></article>`).join('') : '<div class="empty-state"><h2>¡Todas correctas!</h2><p>No hay respuestas incorrectas para repasar.</p></div>'}</div>`;
  }
  function renderExamples(selectedCourse) {
    const course = selectedCourse || courses[0];
    content.innerHTML = `<header class="page-heading feature-heading"><div><span class="eyebrow">APRENDE VIENDO CÓMO SE HACE</span><h1>Biblioteca de ejemplos</h1><p>Comandos explicados, resultado esperado y una práctica segura para cada lección.</p></div><span class="feature-icon">${icon('code')}</span></header><div class="course-tabs" role="navigation" aria-label="Curso de los ejemplos">${courses.map(item => `<a class="pill ${item.id === course.id ? 'active' : ''}" href="#examples/${item.id}" ${item.id === course.id ? 'aria-current="page"' : ''}>${item.title}</a>`).join('')}</div><div class="examples-grid">${course.lessons.map((lesson, index) => `<article class="example-card"><div class="example-card-top"><span>Ejemplo ${String(index + 1).padStart(2, '0')}</span><a href="#lesson/${course.id}/${index}">Ver lección →</a></div><h2>${escape(lesson.title)}</h2><pre><code>${escape(lesson.command)}</code></pre><p>${escape(lesson.detail)}</p><div class="example-practice"><strong>Prueba tú:</strong> ${escape(lesson.practice)}</div><button class="btn secondary" data-action="copy-example" data-course="${course.id}" data-index="${index}">${icon('code')} Copiar ejemplo</button></article>`).join('')}</div>`;
  }
  function newPractice(course) {
    const indexes = course.questions.map((_, index) => index);
    for (let i = indexes.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indexes[i], indexes[j]] = [indexes[j], indexes[i]];
    }
    practiceSession = { courseId: course.id, indexes: indexes.slice(0, 10), answers: Array(10).fill(null), index: 0, finished: false };
  }
  function renderPractice(course) {
    if (!course) {
      practiceSession = null;
      content.innerHTML = `<header class="page-heading feature-heading"><div><span class="eyebrow">PRÁCTICAS RÁPIDAS</span><h1>Ponte a prueba</h1><p>Cuestionarios de 10 preguntas con corrección inmediata al finalizar. No afectan tu examen final.</p></div><span class="feature-icon">${icon('check')}</span></header><div class="practice-course-grid">${courses.map(item => `<article class="practice-course-card ${item.color}"><span>${item.category}</span><h2>${item.title}</h2><p>10 preguntas aleatorias · Sin límite de tiempo</p><button class="btn primary" data-action="start-practice" data-course="${item.id}">Empezar prueba ${icon('arrow')}</button></article>`).join('')}</div>`;
      return;
    }
    if (!practiceSession || practiceSession.courseId !== course.id) newPractice(course);
    const session = practiceSession;
    if (session.finished) {
      const correct = session.indexes.reduce((total, questionIndex, index) => total + (session.answers[index] === course.questions[questionIndex].answer ? 1 : 0), 0);
      content.innerHTML = `${breadcrumbs(course, 'Prueba rápida')}<section class="quick-result white-panel"><span class="feature-icon">${icon(correct >= 7 ? 'award' : 'book')}</span><span class="eyebrow">RESULTADO DE LA PRUEBA</span><h1>${correct >= 7 ? 'Buen trabajo.' : 'Ya sabes qué repasar.'}</h1><strong>${correct}/10</strong><p>${correct >= 7 ? 'Tienes una base sólida en este conjunto de preguntas.' : 'Revisa las explicaciones y vuelve a intentarlo cuando quieras.'}</p><div class="quick-review">${session.indexes.map((questionIndex, index) => { const q = course.questions[questionIndex], ok = session.answers[index] === q.answer; return `<div class="${ok ? 'ok' : 'bad'}"><b>${index + 1}. ${escape(q.text)}</b><span>${ok ? '✓ Correcta' : `Correcta: ${escape(q.choices[q.answer])}`}</span><p>${escape(q.explanation)}</p></div>`; }).join('')}</div><div class="modal-actions"><a class="btn secondary" href="#practice">Elegir otro curso</a><button class="btn primary" data-action="restart-practice" data-course="${course.id}">Nueva prueba</button></div></section>`;
      return;
    }
    const question = course.questions[session.indexes[session.index]], selected = session.answers[session.index];
    content.innerHTML = `${breadcrumbs(course, 'Prueba rápida')}<div class="quick-test-layout"><section class="white-panel quick-question"><div class="question-top"><span>Pregunta <b>${session.index + 1}</b> de 10</span><span>${course.modules[question.module]}</span></div>${bar(Math.round(session.answers.filter(item => item !== null).length * 10), 'Preguntas respondidas')}<fieldset class="question-fieldset"><legend>${escape(question.text)}</legend>${question.choices.map((choice, index) => `<label class="answer-option ${selected === index ? 'chosen' : ''}"><input type="radio" name="practiceAnswer" value="${index}" ${selected === index ? 'checked' : ''}><span class="answer-letter">${String.fromCharCode(65 + index)}</span><span>${escape(choice)}</span></label>`).join('')}</fieldset><div class="question-actions"><button class="btn secondary" data-action="practice-move" data-index="${session.index - 1}" ${session.index === 0 ? 'disabled' : ''}>← Anterior</button><span>${session.answers.filter(item => item !== null).length}/10 respondidas</span><button class="btn primary" data-action="${session.index === 9 ? 'finish-practice' : 'practice-move'}" data-index="${session.index + 1}">${session.index === 9 ? 'Finalizar prueba' : 'Siguiente →'}</button></div></section><aside class="white-panel quick-map"><h2>${course.title}</h2><p>Selecciona una respuesta en cada pregunta.</p><div class="question-numbers">${session.answers.map((answer, index) => `<button class="question-number ${answer !== null ? 'answered' : ''} ${index === session.index ? 'current' : ''}" data-action="practice-move" data-index="${index}">${index + 1}</button>`).join('')}</div><a class="btn secondary full" href="#practice">Salir de la prueba</a></aside></div>`;
  }
  function videoCards(videos) {
    if (!videos.length) return `<div class="empty-state video-empty">${icon('video')}<h2>Tu biblioteca está lista</h2><p>Agrega clases, tutoriales o grabaciones propias. Los videos se guardan localmente en tu equipo.</p><button class="btn primary" data-action="upload-video">${icon('upload')} Agregar primer video</button></div>`;
    return `<div class="video-grid">${videos.map(item => `<article class="video-card"><video controls preload="metadata" src="${escape(item.url)}"></video><div><span class="eyebrow">VIDEO LOCAL</span><h2>${escape(item.title)}</h2><p>${(item.size / 1024 / 1024).toFixed(1)} MB · Solo en este equipo</p><button class="text-button danger" data-action="remove-video" data-video="${escape(item.id)}" data-title="${escape(item.title)}">${icon('trash')} Quitar de la biblioteca</button></div></article>`).join('')}</div>`;
  }
  async function renderVideos() {
    content.innerHTML = `<header class="page-heading feature-heading"><div><span class="eyebrow">TU BIBLIOTECA MULTIMEDIA</span><h1>Videos de aprendizaje</h1><p>Reúne tus clases y tutoriales en un espacio privado dentro de la academia.</p></div><button class="btn primary" data-action="upload-video">${icon('upload')} Agregar video</button></header><div class="video-notice">${icon('shield')} Los archivos se copian a la biblioteca local de LinuxMate. No se suben a internet.</div><div id="videoLibrary" class="loading-state">Buscando videos…</div><input id="browserVideoInput" type="file" accept="video/mp4,video/webm,video/ogg,video/quicktime,video/x-matroska" hidden>`;
    let videos = browserVideos;
    if (nativeMode) {
      try {
        const result = await window.pywebview.api.list_learning_videos();
        if (!result.success) throw new Error(result.message);
        videos = result.videos;
      } catch (error) {
        document.getElementById('videoLibrary').innerHTML = `<div class="empty-state"><h2>No se pudo abrir la biblioteca</h2><p>${escape(error.message || 'Inténtalo de nuevo.')}</p></div>`;
        return;
      }
    }
    document.getElementById('videoLibrary').className = '';
    document.getElementById('videoLibrary').innerHTML = videoCards(videos);
    document.querySelectorAll('#videoLibrary video').forEach((player, index) => {
      player.addEventListener('error', () => {
        const details = player.nextElementSibling;
        if (details.querySelector('[data-action="prepare-video"]')) return;
        const notice = document.createElement('p');
        notice.textContent = 'No se pudo reproducir este archivo. Puede necesitar un formato compatible.';
        details.appendChild(notice);
        if (!nativeMode) return;
        const button = document.createElement('button');
        button.className = 'btn secondary';
        button.dataset.action = 'prepare-video';
        button.dataset.video = videos[index].id;
        button.textContent = 'Preparar para reproducir';
        details.appendChild(button);
      });
      if (player.error) player.dispatchEvent(new Event('error'));
    });
  }
  function renderAchievements() {
    content.innerHTML = `<header class="page-heading"><span class="eyebrow">EL CAMINO QUE YA RECORRISTE</span><h1>Mis logros</h1><p>Tus avances, tus habilidades y tus próximos objetivos.</p></header><div class="achievement-grid">${courses.map(course => { const p = progress(course), unlocked = core.certificateReady(course, p), best = core.bestResult(course, p); return `<article class="white-panel achievement ${unlocked ? 'unlocked' : ''}"><span class="achievement-icon">${icon('award')}</span><span class="eyebrow">${unlocked ? 'OBJETIVO CONSEGUIDO' : 'EN TU HORIZONTE'}</span><h2>${course.title}</h2><p>${p.completed.length}/15 lecciones · ${best ? `Mejor examen: ${best.correct}/75` : 'Examen pendiente'}</p>${bar(percent(course))}<p class="tiny">Completa las 15 lecciones y alcanza 53 aciertos en el examen.</p>${unlocked ? `<button class="btn primary" data-action="certificate" data-course="${course.id}">Ver constancia</button>` : `<a class="btn secondary" href="#course/${course.id}">Seguir aprendiendo ${icon('arrow')}</a>`}</article>`; }).join('')}</div>`;
  }
  function certificate(course) {
    const p = progress(course);
    if (!core.certificateReady(course, p)) return;
    const result = core.bestResult(course, p);
    openModal(`<div class="certificate"><span class="brand-mini">LINUXMATE ACADEMY</span><span class="certificate-award">${icon('award')}</span><span class="eyebrow">CONSTANCIA DE AUTOESTUDIO</span><h2 id="dialogTitle">Un nuevo paso,<br>una nueva habilidad.</h2><p>Reconocemos el recorrido de</p><strong class="certificate-name">${escape(state.name || 'Estudiante de LinuxMate')}</strong><p>por completar las 15 lecciones y aprobar el examen de</p><h3>${course.title}</h3><div class="certificate-details"><span>Resultado: ${result.correct}/75</span><span>${date(result.date)}</span></div><p class="tiny">Constancia personal de aprendizaje emitida localmente por LinuxMate Academy. No es una acreditación oficial.</p></div><div class="modal-actions"><button class="btn secondary" data-action="profile">Cambiar mi nombre</button><button class="btn primary" data-action="download-certificate" data-course="${course.id}">Descargar constancia</button></div>`);
  }
  function profile() {
    if (modal.open) modal.close();
    openModal(`<span class="eyebrow">TU ESPACIO DE APRENDIZAJE</span><h2 id="dialogTitle">¿Cómo te llamas?</h2><p>Usaremos este nombre en tu espacio y en tus constancias.</p><form id="profileForm"><label for="studentName">Nombre</label><input id="studentName" maxlength="80" value="${escape(state.name)}" placeholder="Tu nombre" autocomplete="name"><button class="btn primary full" type="submit">Guardar nombre</button></form>`);
  }
  async function downloadCertificate(course) {
    if (!core.certificateReady(course, progress(course))) return;
    const result = core.bestResult(course, progress(course));
    const text = `LINUXMATE ACADEMY\nCONSTANCIA PERSONAL DE AUTOESTUDIO\n\nEstudiante: ${state.name || 'Estudiante de LinuxMate'}\nCurso: ${course.title}\nLecciones completadas: 15 de 15\nExamen: ${result.correct} de 75 respuestas correctas\nFecha del examen: ${date(result.date)}\n\nConstancia local de autoestudio. No es una acreditación oficial.\n`;
    if (nativeMode) {
      try {
        const response = await window.pywebview.api.export_learning_certificate(course.id, text);
        if (response.success) toast('Constancia guardada.');
        else if (!response.cancelled) toast(response.message || 'No se pudo guardar la constancia.');
      } catch (_) { toast('No se pudo exportar la constancia.'); }
    } else {
      const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
      const a = document.createElement('a'); a.href = url; a.download = `constancia-linuxmate-${course.id}.txt`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action, course = courses.find(c => c.id === button.dataset.course);
    if (action === 'reload') { ready = false; writeAllowed = true; init(); return; }
    if (!ready) return;
    if (action === 'close-modal' || action === 'close-link') { modal.close(); return; }
    if (action === 'profile') { profile(); return; }
    if (action === 'appearance') { appearance(); return; }
    if (action === 'focus-mode') { state.preferences.focus = !state.preferences.focus; applyPreferences(); persist(); return; }
    if (action === 'catalog-view') {
      state.preferences.view = button.dataset.value === 'list' ? 'list' : 'grid';
      applyPreferences(); persist();
      document.querySelectorAll('[data-action="catalog-view"]').forEach(control => control.setAttribute('aria-pressed', String(control.dataset.value === state.preferences.view)));
      return;
    }
    if (action === 'filter') { category = button.dataset.value; render(); return; }
    if (action === 'reset-filters') { category = level = 'Todos'; query = ''; document.getElementById('searchInput').value = ''; navigate('catalog'); return; }
    if (action === 'review-filter') { reviewMode = button.dataset.value; render(); return; }
    if (action === 'practice-move') {
      const index = Number(button.dataset.index);
      if (practiceSession && index >= 0 && index < 10) { practiceSession.index = index; render(); }
      return;
    }
    if (action === 'finish-practice') {
      if (!practiceSession) return;
      const missing = practiceSession.answers.filter(item => item === null).length;
      if (missing) { toast(`Responde las ${missing} preguntas pendientes.`); practiceSession.index = practiceSession.answers.indexOf(null); render(); }
      else { practiceSession.finished = true; render(); }
      return;
    }
    if (action === 'prepare-video') {
      if (typeof window.pywebview?.api?.prepare_learning_video !== 'function') {
        toast('Cierra todas las ventanas de LinuxMate y vuelve a abrir la aplicación para activar la conversión de videos.');
        return;
      }
      button.disabled = true;
      button.textContent = 'Preparando video…';
      try {
        const result = await window.pywebview.api.prepare_learning_video(button.dataset.video);
        if (!result.success) throw new Error(result.message);
        if (route().page === 'videos') await renderVideos();
        toast('Copia compatible lista.');
      } catch (error) {
        toast(error.message || 'No se pudo preparar el video.');
      } finally {
        button.disabled = false;
        button.textContent = 'Preparar para reproducir';
      }
      return;
    }
    if (action === 'upload-video') {
      if (!nativeMode) { document.getElementById('browserVideoInput')?.click(); return; }
      button.disabled = true;
      try {
        const result = await window.pywebview.api.add_learning_video();
        if (result.success) { toast('Video agregado a tu biblioteca.'); await renderVideos(); }
        else if (!result.cancelled) toast(result.message || 'No se pudo agregar el video.');
      } catch (_) { toast('No se pudo abrir el selector de videos.'); }
      finally { if (button.isConnected) button.disabled = false; }
      return;
    }
    if (action === 'remove-video') {
      openModal(`<span class="modal-emblem">${icon('trash')}</span><h2 id="dialogTitle">Quitar video</h2><p>Se eliminará la copia local de «${escape(button.dataset.title)}» guardada por LinuxMate.</p><div class="modal-actions"><button class="btn secondary" data-action="close-modal">Cancelar</button><button class="btn primary" data-action="confirm-remove-video" data-video="${escape(button.dataset.video)}">Quitar video</button></div>`);
      return;
    }
    if (action === 'confirm-remove-video') {
      const videoId = button.dataset.video;
      try {
        if (nativeMode) {
          const result = await window.pywebview.api.remove_learning_video(videoId);
          if (!result.success) throw new Error(result.message);
        } else {
          const item = browserVideos.find(video => video.id === videoId);
          if (item) URL.revokeObjectURL(item.url);
          browserVideos = browserVideos.filter(video => video.id !== videoId);
        }
        modal.close(); toast('Video quitado de la biblioteca.'); await renderVideos();
      } catch (error) { toast(error.message || 'No se pudo quitar el video.'); }
      return;
    }
    if (!course) return;
    const p = progress(course);
    if (action === 'save') { p.saved = !p.saved; persist(); render(); toast(p.saved ? 'Curso añadido a tus guardados.' : 'Curso retirado de guardados.'); }
    if (action === 'enroll') { p.enrolled = true; persist(); navigate(`lesson/${course.id}/${p.current}`); }
    if (action === 'copy') {
      try { await navigator.clipboard.writeText(course.lessons[Number(button.dataset.index)].command); toast('Ejemplo copiado.'); }
      catch (_) { toast('Selecciona el ejemplo y cópialo con Ctrl+C.'); }
    }
    if (action === 'copy-example') {
      try { await navigator.clipboard.writeText(course.lessons[Number(button.dataset.index)].command); toast('Ejemplo copiado.'); }
      catch (_) { toast('No se pudo copiar el ejemplo.'); }
    }
    if (action === 'start-practice' || action === 'restart-practice') {
      newPractice(course);
      navigate(`practice/${course.id}`);
    }
    if (action === 'complete') {
      const index = Number(button.dataset.index);
      core.recordCompletion(state, course, index);
      p.current = Math.min(index + 1, 14); persist();
      if (index === 14) { render(); examIntro(course); } else navigate(`lesson/${course.id}/${index + 1}`);
    }
    if (action === 'exam-intro') examIntro(course);
    if (action === 'start-exam') {
      p.enrolled = true;
      if (!p.exam || p.exam.finished) p.exam = core.startExam();
      persist(); modal.close(); navigate(`exam/${course.id}`);
    }
    if (action === 'question') {
      const index = Number(button.dataset.index);
      if (p.exam && !p.exam.finished && index >= 0 && index < 75) { p.exam.index = index; persist(); render(); content.querySelector('.question-fieldset')?.scrollIntoView({ block: 'nearest' }); }
    }
    if (action === 'flag' && p.exam && !p.exam.finished) {
      const i = p.exam.index;
      p.exam.flagged = p.exam.flagged.includes(i) ? p.exam.flagged.filter(n => n !== i) : [...p.exam.flagged, i]; persist(); render();
    }
    if (action === 'finish-intro') finishIntro(course);
    if (action === 'first-unanswered') { p.exam.index = p.exam.answers.indexOf(null); persist(); modal.close(); render(); }
    if (action === 'submit-exam') {
      if (core.finishExam(course, p)) { persist(); modal.close(); navigate(`result/${course.id}`); }
    }
    if (action === 'certificate') certificate(course);
    if (action === 'download-certificate') downloadCertificate(course);
  });
  document.addEventListener('change', event => {
    if (!ready) return;
    if (event.target.name === 'academyTheme') { state.preferences.theme = event.target.value; applyPreferences(); persist(); }
    if (event.target.id === 'academyEffects') { state.preferences.effects = event.target.checked; applyPreferences(); persist(); }
    if (event.target.id === 'academyFont') { state.preferences.fontSize = Number(event.target.value); applyPreferences(); persist(); }
    if (['weeklyGoal', 'weeklyGoalModal'].includes(event.target.id)) {
      state.weeklyGoal = Number(event.target.value); persist();
      if (['catalog', 'my', 'saved'].includes(route().page)) renderCatalog(route().page);
    }
    if (event.target.id === 'notesCourse') { noteCourse = event.target.value; renderNotes(); }
    if (event.target.id === 'sortSelect') { order = event.target.value; renderCards(); }
    if (event.target.id === 'levelSelect') { level = event.target.value; renderCards(); }
    if (event.target.name === 'examAnswer') {
      const course = courses.find(c => c.id === event.target.dataset.course), p = progress(course);
      if (p.exam.finished) return;
      const selected = Number(event.target.value);
      p.exam.answers[p.exam.index] = selected; persist();
      // Actualiza el mapa sin reemplazar el radio que conserva el foco del teclado.
      content.querySelectorAll('.answer-option').forEach((el, i) => el.classList.toggle('chosen', i === selected));
      const answered = p.exam.answers.filter(a => a !== null).length;
      document.getElementById('answeredCount').textContent = `${answered} de 75 respondidas`;
      const current = content.querySelector('.question-number.current');
      current.classList.add('answered');
      current.setAttribute('aria-label', `Pregunta ${p.exam.index + 1}, respondida${p.exam.flagged.includes(p.exam.index) ? ', marcada' : ''}`);
      const meter = content.querySelector('.progress-track'); meter.setAttribute('aria-valuenow', Math.round(answered / 75 * 100)); meter.firstElementChild.style.width = `${answered / 75 * 100}%`;
      content.querySelector('.question-actions > span').textContent = 'Respuesta seleccionada';
    }
    if (event.target.name === 'practiceAnswer' && practiceSession) {
      practiceSession.answers[practiceSession.index] = Number(event.target.value);
      render();
    }
    if (event.target.id === 'browserVideoInput') {
      const file = event.target.files?.[0];
      if (!file) return;
      browserVideos.push({ id: `preview-${Date.now()}`, title: file.name.replace(/\.[^.]+$/, ''), size: file.size, url: URL.createObjectURL(file) });
      toast('Video agregado para esta vista previa.');
      renderVideos();
    }
  });
  document.addEventListener('input', event => {
    if (!ready) return;
    if (event.target.id === 'lessonNotes') { const course = courses.find(c => c.id === event.target.dataset.course); progress(course).notes[event.target.dataset.index] = event.target.value; persist(); }
    if (event.target.id === 'searchInput') { query = event.target.value.trim(); if (['catalog', 'my', 'saved'].includes(route().page)) renderCards(); }
  });
  document.addEventListener('submit', event => {
    if (!ready) { event.preventDefault(); return; }
    if (event.target.id === 'searchForm') { event.preventDefault(); category = level = 'Todos'; navigate('catalog'); }
    if (event.target.id === 'profileForm') { event.preventDefault(); state.name = document.getElementById('studentName').value.trim().slice(0, 80); persist(); modal.close(); render(); toast('Nombre guardado.'); }
  });
  document.getElementById('retrySave').addEventListener('click', persist);
  document.getElementById('skipContent').addEventListener('click', event => { event.preventDefault(); content.focus(); });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !modal.open && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) { event.preventDefault(); document.getElementById('searchInput').focus(); }
  });
  document.addEventListener('pointerdown', event => {
    if (!state.preferences.effects || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const control = event.target.closest('button, .btn, .course-link, .pill');
    if (!control || control.disabled || control.getAttribute('aria-disabled') === 'true') return;
    control.classList.remove('press-flash');
    void control.offsetWidth;
    control.classList.add('press-flash');
    control.addEventListener('animationend', () => control.classList.remove('press-flash'), {once:true});
  });
  window.addEventListener('hashchange', () => { if (modal.open) modal.close(); render(); window.scrollTo(0, 0); content.focus({ preventScroll: true }); });
  window.addEventListener('pywebviewready', init);
  document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
  document.querySelectorAll('[data-nav]').forEach(link => { link.title = link.textContent.trim(); });
  init();
})();
