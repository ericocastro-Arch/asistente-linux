(function (root) {
  'use strict';
  root.AcademyDashboard = {
    create(ctx) {
      const {courses, core, icon, escape: esc, bar, toast, persist, openModal} = ctx;
      const model = root.AcademyDashboardModel;
      const state = () => ctx.getState();
      let observer, animationTimers = [], countFrames = [], barAnimations = [], clockTimer, heroRun = 0;
      let shellCwd = '/home/estudiante', shellHistory = [], shellPosition = 0, shellLines = [];
      const reduced = () => !state().preferences.effects || matchMedia('(prefers-reduced-motion: reduce)').matches;
      const heading = (command, flag, tail = '') => `<header class="dash-heading"><h2><span>$</span> ${command} <em>${flag}</em></h2>${tail}</header>`;
      const meter = value => `<span class="dash-count" data-target="${value}">${value.toLocaleString('es')}</span>`;
      function hero(next) {
        const s = state(), p = s.courses[next.id], stats = model.summary(s,courses);
        const week = core.weeklyProgress(s), total = courses.reduce((n,c) => n + c.lessons.length,0);
        return `<section class="dash-hero dash-reveal"><div class="dash-welcome"><span class="eyebrow">${icon('terminal')} ~/aprendizaje</span><h1>Hola, ${esc(s.name || 'estudiante')}.<br>Tu <em>shell</em> te espera.</h1><p>Tu siguiente paso: <strong>${esc(next.lessons[p.current].title)}</strong>, en ${esc(next.title)}.</p><div class="dash-hero-actions"><button class="btn primary" data-action="enroll" data-course="${next.id}">${icon('play')} ${p.enrolled ? `Continuar lección ${p.current + 1}` : 'Comenzar mi recorrido'}</button><a class="btn secondary" href="#path">Mi ruta ${icon('arrow')}</a></div><div class="dash-quick"><span><b>${Math.round(p.completed.length / next.lessons.length * 100)}%</b>Curso actual</span><span><b>${p.completed.length}/${next.lessons.length}</b>Lecciones</span><span><b class="dash-cyan">+${stats.weekXP} XP</b>Esta semana</span></div></div><section class="dash-terminal dash-hero-terminal" aria-label="Resumen animado de aprendizaje"><header class="dash-term-bar"><span class="dash-term-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>estudiante@linuxmate: ~/aprendizaje</span><button class="icon-button" data-action="dashboard-replay" title="Repetir animación" aria-label="Repetir animación">${icon('refresh')}</button></header><div class="dash-hero-output" id="heroTerminal" aria-label="Resumen de tu progreso"></div><footer class="dash-term-status"><span>LinuxMate · aprendizaje local</span><span class="dash-green">${stats.streak} días de racha</span></footer></section></section><section class="dash-stats dash-reveal" aria-label="Tu progreso"><div><span class="dash-stat-label">${icon('flame')} Racha activa</span><strong>${meter(stats.streak)} <small>días</small></strong><p>Récord: ${stats.bestStreak} días</p></div><div><span class="dash-stat-label">${icon('zap')} XP total</span><strong>${meter(stats.xp)}</strong><p>Nivel ${stats.level} · ${stats.nextXP} XP para el siguiente</p>${bar(stats.levelPercent,'Progreso de nivel')}</div><div><span class="dash-stat-label">${icon('book')} Lecciones</span><strong>${meter(stats.completed)} <small>/ ${total}</small></strong><p>${courses.filter(c => s.courses[c.id].enrolled).length} cursos iniciados · ${stats.approved} exámenes aprobados</p></div><div class="dash-weekly"><span class="dash-stat-label">${icon('target')} Meta semanal</span><div class="dash-goal-value"><strong>${meter(week.count)} <small>/ ${week.goal}</small></strong><select id="weeklyGoal" aria-label="Meta semanal">${[3,5,10].map(n => `<option value="${n}" ${s.weeklyGoal === n ? 'selected' : ''}>${n} lecciones</option>`).join('')}</select></div>${bar(week.percent,'Meta semanal')}<p>${week.count >= week.goal ? 'Meta cumplida' : 'Lecciones nuevas esta semana'}</p></div></section>`;
      }
      function challenge() {
        const item = model.daily(), done = state().dashboard.challenges[item.date] === item.id;
        return `<section class="dash-challenge dash-reveal">${heading('reto', '--diario', '<span class="dash-reward">+150 XP</span>')}<h3>${esc(item.title)}</h3><p>${done ? 'Reto completado. Tu XP ya está guardado.' : 'Resuelve el comando de hoy.'}</p><div class="dash-challenge-help"><details><summary>Pista</summary><p>${esc(item.hint)}</p></details><details><summary>Solución</summary><code>${esc(item.solution)}</code></details></div><form id="dailyChallengeForm"><label class="sr-only" for="challengeAnswer">Comando del reto diario</label><input id="challengeAnswer" maxlength="200" autocomplete="off" spellcheck="false" placeholder="$ escribe tu comando" ${done ? 'disabled' : ''}><button class="btn secondary" type="submit" ${done ? 'disabled' : ''}>${icon(done ? 'check' : 'arrow')} ${done ? 'Completado' : 'Comprobar'}</button></form><p id="challengeFeedback" role="status"></p><div class="dash-challenge-footer"><a href="#sandbox">${icon('terminal')} Practicar</a><span>Siguiente reto en <b id="challengeCountdown"></b></span></div></section>`;
      }
      function roadmap() {
        return `<section class="dash-section dash-reveal">${heading('ruta', '--tu-recorrido', '<a href="#path">Ver ruta completa →</a>')}<div class="dash-road">${courses.map((c,i) => {
          const p = state().courses[c.id], done = p.completed.length === c.lessons.length;
          return `<a class="dash-road-node ${c.color} ${done ? 'done' : p.enrolled ? 'current' : ''}" href="#${p.enrolled ? `lesson/${c.id}/${p.current}` : `course/${c.id}`}"><span class="dash-road-dot">${done ? icon('check') : String(i+1).padStart(2,'0')}</span><span><b>${esc(c.title)}</b><small>${p.completed.length}/${c.lessons.length} lecciones</small></span><span class="dash-road-state">${done ? 'Completado' : p.enrolled ? 'En curso' : 'Disponible'}</span></a>`;
        }).join('')}</div></section>`;
      }
      const cheats = {
        archivos: [['ls -lah', 'Incluye archivos ocultos'], ['pwd', 'Carpeta actual'], ['find . -name "*.txt"', 'Busca archivos de texto'], ['du -sh .', 'Tamaño de la carpeta']],
        permisos: [['ls -l', 'Consulta permisos'], ['chmod +x script.sh', 'Hace ejecutable un script'], ['chmod 644 archivo.txt', 'Lectura para todos; escritura del dueño'], ['id', 'Usuario y grupos']],
        red: [['ip a', 'Interfaces y direcciones'], ['ip route', 'Rutas de red'], ['ss -tuln', 'Puertos en escucha'], ['ping -c 4 localhost', 'Comprueba la red local']],
        procesos: [['ps aux', 'Procesos activos'], ['top', 'Monitor de procesos'], ['systemctl status ssh', 'Estado del servicio SSH'], ['df -h', 'Espacio disponible']],
      };
      function cheatsheet() {
        return `<section class="dash-section dash-reveal">${heading('man', 'cheatsheet')}<div class="dash-tabs" role="tablist" aria-label="Categorías de comandos">${Object.keys(cheats).map((name,i) => `<button id="cheatTab-${name}" role="tab" aria-selected="${i===0}" aria-controls="cheatPanel-${name}" tabindex="${i===0 ? 0 : -1}" data-action="dashboard-cheat-tab" data-tab="${name}">${name}</button>`).join('')}</div>${Object.entries(cheats).map(([name,rows],i) => `<div id="cheatPanel-${name}" class="dash-cheat-panel" role="tabpanel" aria-labelledby="cheatTab-${name}" ${i ? 'hidden' : ''}>${rows.map(([cmd,description]) => `<div class="dash-command"><code>${esc(cmd)}</code><span>${description}</span><button class="icon-button" data-action="dashboard-copy" data-command="${esc(cmd)}" title="Copiar ${esc(cmd)}" aria-label="Copiar ${esc(cmd)}">${icon('copy')}</button></div>`).join('')}</div>`).join('')}</section>`;
      }
      function sandbox() {
        return `<section class="dash-section dash-reveal">${heading('terminal', '--práctica')}<div class="dash-terminal"><header class="dash-term-bar"><span class="dash-term-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>estudiante@linuxmate · práctica</span><button class="icon-button" data-action="dashboard-shell-clear" title="Limpiar terminal" aria-label="Limpiar terminal">${icon('trash')}</button></header><div class="dash-shell-body" id="sandboxScroll"><div id="sandboxOutput" role="log" aria-live="polite" aria-relevant="additions"></div><form id="sandboxForm"><label for="sandboxInput" id="sandboxPrompt">~ $</label><input id="sandboxInput" autocomplete="off" spellcheck="false" maxlength="500" aria-label="Comando de práctica"></form></div><footer class="dash-term-status"><span>Sandbox · simulación local</span><span class="dash-green">Sin acceso al sistema</span></footer></div></section>`;
      }
      function ranking() {
        const list = model.ranking(state(),courses), max = Math.max(1,list[0].xp);
        return `<section class="dash-section dash-reveal">${heading('ranking', '--mis-cursos')}<div class="dash-ranking">${list.map(({course,xp},i) => `<a class="dash-rank-row ${course.color}" href="#course/${course.id}"><span class="dash-rank-number">${i+1}</span><span><b>${esc(course.title)}</b>${bar(Math.round(xp/max*100),'XP del curso')}</span><strong>${xp}<small>XP</small></strong></a>`).join('')}</div><p class="dash-footnote">50 XP por lección · 250 XP por examen aprobado</p></section>`;
      }
      function activity() {
        const stats = model.summary(state(),courses), cells = model.heatmap(state(),courses), active = cells.filter(c => c.count).length;
        return `<section class="dash-section dash-reveal">${heading('git log', '--tu-actividad')}<div class="dash-activity-stats"><span><b>${active}</b>días activos / 112</span><span><b>${stats.streak}</b>días de racha</span><span><b>${stats.weekMinutes} min</b>lecturas de esta semana</span></div><div class="dash-heatmap-scroll"><div class="dash-heatmap" aria-label="Actividad de las últimas 16 semanas">${cells.map(cell => `<span class="dash-heat-cell heat-${cell.level} ${cell.future ? 'future' : ''}" tabindex="${cell.future ? -1 : 0}" title="${cell.date}: ${cell.count} actividades${cell.minutes ? ` · ${cell.minutes} min de lectura estimada` : ''}" aria-label="${cell.date}: ${cell.count} actividades"></span>`).join('')}</div></div><div class="dash-heat-legend"><span>Menos</span>${[0,1,2,3,4].map(n=>`<i class="dash-heat-cell heat-${n}"></i>`).join('')}<span>Más</span><small>16 semanas</small></div></section>`;
      }
      function achievements() {
        const stats = model.summary(state(),courses);
        const items = [['Primer arranque', stats.completed > 0, 'rocket', 'Completa tu primera lección'], ['Racha de 7 días', stats.bestStreak >= 7, 'flame', 'Aprende durante 7 días seguidos'], ['Primer reto', Object.keys(state().dashboard.challenges).length > 0, 'flag', 'Resuelve un reto diario'], ['Examen aprobado', stats.approved > 0, 'award', 'Aprueba un examen de curso'], ['Ruta completa', courses.every(c => core.certificateReady(c,state().courses[c.id])), 'route', 'Completa todos los cursos y exámenes'], ['Mi primer apunte', courses.some(c => Object.values(state().courses[c.id].notes).some(text => text.trim())), 'notes', 'Guarda un apunte en una lección']];
        return `<section class="dash-section dash-reveal">${heading('ls', '/logros', '<a href="#achievements">Constancias →</a>')}<div class="dash-badges">${items.map(([title,done,name,detail]) => `<div class="dash-badge ${done ? 'earned' : ''}" title="${detail}"><span>${icon(name)}</span><b>${title}</b><small>${done ? 'Conseguido' : detail}</small></div>`).join('')}</div></section>`;
      }
      function agenda() {
        const list = state().dashboard.agenda.slice().sort((a,b) => a.when.localeCompare(b.when));
        return `<section class="dash-section dash-reveal">${heading('cal', '--mi-agenda', `<button class="icon-button" data-action="dashboard-add-session" title="Añadir sesión" aria-label="Añadir sesión">${icon('plus')}</button>`)}<div class="dash-agenda">${list.length ? list.map(item => {
          const when = new Date(item.when), course = courses.find(c => c.id === item.courseId);
          return `<article class="dash-agenda-row ${item.done ? 'done' : ''}"><time class="dash-agenda-date" datetime="${item.when}"><b>${when.getDate()}</b><span>${when.toLocaleDateString('es',{month:'short'})}</span></time><div><h3>${esc(item.title)}</h3><p>${esc(course.title)} · ${when.toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'})}${item.done ? ' · Completada' : when < new Date() ? ' · Pendiente' : ''}</p><a href="#course/${course.id}">Abrir curso →</a></div><div class="dash-agenda-actions"><button class="icon-button" data-action="dashboard-session-done" data-session="${item.id}" aria-label="${item.done ? 'Marcar pendiente' : 'Completar sesión'}" title="${item.done ? 'Marcar pendiente' : 'Completar sesión'}" aria-pressed="${item.done}">${icon('check')}</button><button class="icon-button" data-action="dashboard-remove-session" data-session="${item.id}" title="Quitar sesión" aria-label="Quitar sesión">${icon('trash')}</button></div></article>`;
        }).join('') : '<div class="dash-agenda-empty"><span>Tu próxima sesión</span><p>Reserva un momento para seguir aprendiendo.</p><button class="btn secondary" data-action="dashboard-add-session">'+icon('plus')+' Añadir sesión</button></div>'}</div></section>`;
      }
      function recommendations() {
        const list = courses.filter(c => !core.certificateReady(c,state().courses[c.id])).slice(0,3);
        return `<section class="dash-section dash-reveal">${heading('apt install', 'conocimiento')}<div class="dash-recommendations">${(list.length ? list : courses.slice(0,3)).map(c => `<div class="dash-recommend-row ${c.color}"><span class="dash-recommend-icon">${icon('book')}</span><div><a href="#course/${c.id}"><b>${esc(c.title)}</b></a><p>${esc(c.category)} · ${c.lessons.length} lecciones</p></div><button class="icon-button" data-action="save" data-course="${c.id}" aria-pressed="${state().courses[c.id].saved}" title="${state().courses[c.id].saved ? 'Quitar de guardados' : 'Guardar curso'}" aria-label="Guardar ${esc(c.title)}">${icon(state().courses[c.id].saved ? 'check' : 'plus')}</button></div>`).join('')}</div><a class="dash-text-link" href="#saved">Ver mis guardados →</a></section>`;
      }
      function extras() {
        return `<div class="dashboard-extras"><div class="dash-row">${roadmap()}${challenge()}</div><div class="dash-row">${cheatsheet()}${sandbox()}</div><div class="dash-row">${activity()}${ranking()}</div><div class="dash-row">${achievements()}${agenda()}</div>${recommendations()}</div>`;
      }
      function page(name) {
        const pages = {sandbox: ['Terminal de práctica', sandbox], cheatsheet: ['Hoja de comandos', cheatsheet], activity: ['Tu actividad', () => `<div class="dash-row">${activity()}${ranking()}</div>${achievements()}`], agenda: ['Mi agenda', agenda]};
        const [title, render] = pages[name];
        return `<header class="page-heading"><span class="eyebrow">LINUXMATE ACADEMY</span><h1>${title}</h1></header>${render()}`;
      }
      function stopHero() { heroRun++; animationTimers.forEach(clearTimeout); animationTimers = []; }
      function runHero() {
        stopHero();
        const body = document.getElementById('heroTerminal');
        if (!body) return;
        const stats = model.summary(state(),courses), next = ctx.nextCourse(), p = state().courses[next.id];
        const lines = [ ['$ whoami', state().name || 'estudiante'], ['$ cat progreso.json', `${stats.completed} lecciones completadas · ${stats.approved} exámenes aprobados`], ['$ learn --continuar', `${next.title} · lección ${p.current+1}/${next.lessons.length}`] ];
        body.replaceChildren();
        const generation = heroRun;
        let lineIndex = 0, charIndex = 0, command;
        const tick = () => {
          if (generation !== heroRun || !body.isConnected) return;
          if (lineIndex >= lines.length) { const cursor = document.createElement('span'); cursor.className = 'dash-cursor'; cursor.setAttribute('aria-hidden','true'); body.append(cursor); return; }
          if (!charIndex) { command = document.createElement('div'); command.className = 'dash-term-command'; body.append(command); }
          const [input, output] = lines[lineIndex];
          charIndex = reduced() ? input.length : charIndex + 1;
          command.textContent = input.slice(0,charIndex);
          if (charIndex >= input.length) {
            const result = document.createElement('div'); result.className = 'dash-term-output'; result.textContent = output; body.append(result); lineIndex++; charIndex = 0;
          }
          if (reduced()) tick(); else animationTimers.push(setTimeout(tick,charIndex ? 28 : 220));
        };
        tick();
      }
      function shellPaint() {
        const output = document.getElementById('sandboxOutput');
        if (!output) return;
        output.replaceChildren();
        if (!shellLines.length) shellLines.push({text:'LinuxMate Shell · entorno de práctica\nhelp para consultar los comandos',command:false});
        shellLines.forEach(line => { const div = document.createElement('div'); div.className = line.command ? 'dash-term-command' : 'dash-term-output'; div.textContent = line.text; output.append(div); });
        document.getElementById('sandboxPrompt').textContent = `${shellCwd.replace('/home/estudiante','~')} $`;
        const scroll = document.getElementById('sandboxScroll'); scroll.scrollTop = scroll.scrollHeight;
      }
      function tickClock() {
        const now = new Date(), clock = document.getElementById('academyClock');
        if (clock) { clock.dateTime = now.toISOString(); clock.textContent = now.toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'}); }
        const countdown = document.getElementById('challengeCountdown');
        if (countdown) { const tomorrow = new Date(now); tomorrow.setHours(24,0,0,0); const seconds = Math.ceil((tomorrow-now)/1000); countdown.textContent = [Math.floor(seconds/3600),Math.floor(seconds%3600/60),seconds%60].map(n => String(n).padStart(2,'0')).join(':'); }
      }
      function updateStatus() {
        const stats = model.summary(state(),courses);
        document.getElementById('streakChip').innerHTML = `${icon('flame')} ${stats.streak} días`;
        document.getElementById('xpChip').innerHTML = `${icon('zap')} ${stats.xp.toLocaleString('es')} XP`;
        document.getElementById('agendaDot').hidden = !state().dashboard.agenda.some(item => !item.done);
      }
      function animateCount(el) {
        if (reduced()) return;
        const target = Number(el.dataset.target), start = performance.now();
        function frame(time) {
          if (!el.isConnected) return;
          const fraction = reduced() ? 1 : Math.min(1,(time-start)/1000);
          el.textContent = Math.round(target * (1 - (1-fraction)**3)).toLocaleString('es');
          if (fraction < 1) countFrames.push(requestAnimationFrame(frame));
        }
        countFrames.push(requestAnimationFrame(frame));
      }
      function mount() {
        updateStatus(); tickClock(); runHero(); shellPaint();
        let mountedDate = core.localDate(new Date());
        clearInterval(clockTimer);
        clockTimer = setInterval(() => {
          tickClock();
          if (mountedDate !== core.localDate(new Date()) && !document.getElementById('modal').open) { mountedDate = core.localDate(new Date()); ctx.render(); }
        },1000);
        const reveal = el => {
          el.classList.add('dash-in'); el.querySelectorAll('.dash-count').forEach(animateCount);
          if (!reduced()) el.querySelectorAll('.progress-track > span').forEach(fill => {
            if (fill.animate) barAnimations.push(fill.animate([{width:'0%'},{width:fill.style.width}],{duration:1000,easing:'cubic-bezier(.22,1,.3,1)'}));
          });
        };
        const elements = document.querySelectorAll('.dash-reveal, .course-card');
        if (reduced() || !root.IntersectionObserver) { elements.forEach(reveal); return; }
        observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { reveal(entry.target); observer.unobserve(entry.target); } }),{threshold:.08});
        elements.forEach(el => { el.classList.add('dash-reveal'); observer.observe(el); });
      }
      function dispose() { stopHero(); observer?.disconnect(); countFrames.forEach(cancelAnimationFrame); countFrames = []; barAnimations.forEach(animation=>animation.cancel()); barAnimations = []; clearInterval(clockTimer); }
      function addSession() {
        if (state().dashboard.agenda.length >= 100) { toast('Tu agenda tiene 100 sesiones. Quita una antes de añadir otra.'); return; }
        const when = new Date(); when.setHours(when.getHours()+1,0,0,0);
        const value = `${core.localDate(when)}T${String(when.getHours()).padStart(2,'0')}:00`;
        openModal(`<span class="eyebrow">TU TIEMPO DE APRENDIZAJE</span><h2 id="dialogTitle">Nueva sesión de estudio</h2><form id="studySessionForm" class="dash-session-form"><label for="sessionTitle">Título</label><input id="sessionTitle" maxlength="120" required value="Mi sesión de Linux"><label for="sessionCourse">Curso</label><select id="sessionCourse">${courses.map(c=>`<option value="${c.id}" ${ctx.nextCourse().id === c.id ? 'selected' : ''}>${esc(c.title)}</option>`).join('')}</select><label for="sessionWhen">Fecha y hora local</label><input type="datetime-local" id="sessionWhen" value="${value}" required><button class="btn primary" type="submit">${icon('calendar')} Guardar sesión</button></form>`);
      }
      document.addEventListener('click', async event => {
        const button = event.target.closest('[data-action^="dashboard-"]');
        if (!button || !ctx.isReady()) return;
        const action = button.dataset.action;
        if (action === 'dashboard-replay') runHero();
        if (action === 'dashboard-shell-clear') { shellLines = []; shellPaint(); document.getElementById('sandboxInput')?.focus(); }
        if (action === 'dashboard-cheat-tab') {
          document.querySelectorAll('[data-action="dashboard-cheat-tab"]').forEach(tab => { const selected = tab === button; tab.setAttribute('aria-selected',String(selected)); tab.tabIndex = selected ? 0 : -1; document.getElementById(tab.getAttribute('aria-controls')).hidden = !selected; });
        }
        if (action === 'dashboard-copy') { try { await navigator.clipboard.writeText(button.dataset.command); toast('Comando copiado.'); } catch (_) { toast(`Comando: ${button.dataset.command}`); } }
        if (action === 'dashboard-add-session') addSession();
        if (action === 'dashboard-session-done' || action === 'dashboard-remove-session') {
          const item = state().dashboard.agenda.find(item => item.id === button.dataset.session);
          if (!item) return;
          if (action === 'dashboard-session-done') item.done = !item.done;
          else state().dashboard.agenda = state().dashboard.agenda.filter(entry => entry !== item);
          persist(); ctx.render();
        }
        if (action === 'dashboard-notifications') {
          const pending = state().dashboard.agenda.filter(item => !item.done).length;
          openModal(`<span class="eyebrow">TU ESPACIO</span><h2 id="dialogTitle">Actividad y agenda</h2><p>${pending} sesiones de estudio pendientes.</p><p>${state().dashboard.challenges[model.daily().date] === model.daily().id ? 'Ya completaste el reto de hoy.' : 'Tu reto diario está disponible.'}</p><div class="modal-actions"><a class="btn primary" href="#agenda">${icon('calendar')} Mi agenda</a><a class="btn secondary" href="#activity">${icon('chart')} Mi actividad</a></div>`);
        }
      });
      document.addEventListener('submit', event => {
        if (!ctx.isReady()) return;
        if (event.target.id === 'dailyChallengeForm') {
          event.preventDefault();
          const result = model.completeChallenge(state(),document.getElementById('challengeAnswer').value);
          if (!result.correct) { document.getElementById('challengeFeedback').textContent = 'Revisa el comando y consulta la pista para volver a intentarlo.'; return; }
          if (result.awarded) persist();
          ctx.render(); toast(result.awarded ? 'Reto completado. +150 XP guardados.' : 'Ya completaste el reto de hoy.');
        }
        if (event.target.id === 'sandboxForm') {
          event.preventDefault();
          const input = document.getElementById('sandboxInput'), raw = input.value.trim();
          if (!raw) return;
          const result = model.runCommand(raw,{state:state(),courses,cwd:shellCwd});
          shellHistory = [...shellHistory,raw].slice(-100); shellPosition = shellHistory.length;
          if (result.clear) shellLines = [];
          else { shellLines.push({text:`${shellCwd.replace('/home/estudiante','~')} $ ${raw}`,command:true}); if (result.output) shellLines.push({text:result.output,command:false}); shellLines = shellLines.slice(-160); }
          if (result.cwd) shellCwd = result.cwd;
          input.value = ''; shellPaint();
        }
        if (event.target.id === 'studySessionForm') {
          event.preventDefault();
          const title = document.getElementById('sessionTitle').value.trim(), when = document.getElementById('sessionWhen').value;
          if (!title || !Number.isFinite(new Date(when).getTime())) return;
          state().dashboard.agenda.push({id:`session-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,title,when,courseId:document.getElementById('sessionCourse').value,done:false});
          persist(); document.getElementById('modal').close(); ctx.render(); toast('Sesión guardada en tu agenda.');
        }
      });
      document.addEventListener('keydown', event => {
        if (event.target.id === 'sandboxInput' && ['ArrowUp','ArrowDown'].includes(event.key)) { event.preventDefault(); shellPosition = Math.max(0,Math.min(shellHistory.length,shellPosition+(event.key === 'ArrowUp' ? -1 : 1))); event.target.value = shellHistory[shellPosition] || ''; }
        if (event.target.matches('[role="tab"]') && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
          const tabs = [...event.target.parentElement.querySelectorAll('[role="tab"]')], index = tabs.indexOf(event.target);
          event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length-1 : (index+(event.key === 'ArrowRight' ? 1 : -1)+tabs.length)%tabs.length; tabs[next].click(); tabs[next].focus();
        }
      });
      return {hero, extras, page, mount, dispose, refreshMotion: () => { if (reduced()) { runHero(); barAnimations.forEach(animation=>animation.cancel()); barAnimations = []; document.querySelectorAll('.dash-reveal').forEach(el=>el.classList.add('dash-in')); } }};
    }
  };
})(window);
