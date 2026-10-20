/* Dashboard calculations and the bounded practice environment have no DOM access. */
(function (root) {
  'use strict';
  const challenges = [
    {title: 'Lista los archivos .conf de /etc por tamaño', hint: 'Combina el formato largo (-l), tamaños legibles (-h) y orden por tamaño (-S).', solution: 'ls -lhS /etc/*.conf', answers: ['ls -lhS /etc/*.conf', 'ls -lSh /etc/*.conf', 'ls -hlS /etc/*.conf', 'ls -hSl /etc/*.conf', 'ls -Slh /etc/*.conf', 'ls -Shl /etc/*.conf']},
    {title: 'Muestra tu carpeta actual', hint: 'El nombre del comando significa print working directory.', solution: 'pwd', answers: ['pwd']},
    {title: 'Lista todos los archivos, incluidos los ocultos', hint: 'La opción -a incluye los nombres que comienzan con un punto.', solution: 'ls -la', answers: ['ls -la', 'ls -al', 'ls -lah', 'ls -lha']},
    {title: 'Imprime Hola, Linux en la terminal', hint: 'Usa echo y coloca el mensaje entre comillas.', solution: 'echo "Hola, Linux"', answers: ['echo "Hola, Linux"', "echo 'Hola, Linux'", 'echo Hola, Linux']},
  ];
  const dateKey = value => root.AcademyCore.localDate(value);
  function daily(now = new Date()) {
    const key = dateKey(now), id = Math.floor(Date.parse(`${key}T00:00:00Z`) / 86400000) % challenges.length;
    return { ...challenges[id], id, date: key };
  }
  function completeChallenge(state, answer, now = new Date()) {
    const challenge = daily(now);
    if (!challenge.answers.includes(answer.trim().replace(/\s+/g, ' '))) return {correct: false, awarded: false};
    const awarded = state.dashboard.challenges[challenge.date] !== challenge.id;
    if (awarded) state.dashboard.challenges[challenge.date] = challenge.id;
    return {correct: true, awarded};
  }
  function activity(state, courses, now = new Date()) {
    const days = new Map(), today = dateKey(now);
    const add = (date, minutes = 0) => {
      if (date > today) return;
      const item = days.get(date) || {count: 0, minutes: 0};
      item.count++; item.minutes += minutes; days.set(date, item);
    };
    state.activity.forEach(entry => add(entry.date, courses.find(c => c.id === entry.courseId)?.lessons[entry.index]?.minutes || 0));
    Object.keys(state.dashboard.challenges).forEach(date => add(date));
    return days;
  }
  function summary(state, courses, now = new Date()) {
    const core = root.AcademyCore, today = dateKey(now), days = activity(state, courses, now);
    const completed = courses.reduce((sum, c) => sum + state.courses[c.id].completed.length, 0);
    const approved = courses.filter(c => core.bestResult(c, state.courses[c.id])?.passed).length;
    const challengeCount = Object.keys(state.dashboard.challenges).filter(date => date <= today).length;
    const xp = completed * 50 + approved * 250 + challengeCount * 150;
    const monday = new Date(now); monday.setDate(now.getDate() - (now.getDay() + 6) % 7);
    const weekStart = dateKey(monday);
    const weekEntries = state.activity.filter(item => item.date >= weekStart && item.date <= today);
    const weekExamXP = courses.reduce((sum, course) => {
      const progress = state.courses[course.id];
      const passedDates = [...progress.attempts, ...(progress.bestAttempt ? [progress.bestAttempt] : [])]
        .filter(exam => core.grade(course,exam).passed && Number.isFinite(new Date(exam.finished).getTime()))
        .map(exam => dateKey(new Date(exam.finished))).sort();
      const firstPass = passedDates[0];
      return sum + (firstPass >= weekStart && firstPass <= today ? 250 : 0);
    },0);
    const weekXP = weekEntries.length * 50 + Object.keys(state.dashboard.challenges).filter(date => date >= weekStart && date <= today).length * 150 + weekExamXP;
    const weekMinutes = weekEntries.reduce((sum, entry) => sum + (courses.find(c => c.id === entry.courseId)?.lessons[entry.index]?.minutes || 0), 0);
    const cursor = new Date(now);
    if (!days.has(today)) cursor.setDate(cursor.getDate() - 1);
    let streak = 0;
    while (days.has(dateKey(cursor))) { streak++; cursor.setDate(cursor.getDate() - 1); }
    let bestStreak = 0, run = 0, previous;
    [...days.keys()].sort().forEach(date => {
      const serial = Date.parse(`${date}T00:00:00Z`) / 86400000;
      run = serial === previous + 1 ? run + 1 : 1; previous = serial; bestStreak = Math.max(bestStreak, run);
    });
    return {completed, approved, xp, weekXP, weekMinutes, streak, bestStreak, activeDays: days.size, level: Math.floor(xp / 500) + 1, levelPercent: xp % 500 / 5, nextXP: 500 - xp % 500};
  }
  function heatmap(state, courses, now = new Date()) {
    const days = activity(state, courses, now), end = new Date(now);
    end.setDate(end.getDate() + (7 - end.getDay()) % 7);
    return Array.from({length: 112}, (_, i) => {
      const value = new Date(end); value.setDate(end.getDate() - 111 + i);
      const date = dateKey(value), item = days.get(date) || {count: 0, minutes: 0};
      return {date, ...item, level: Math.min(4, item.count), future: date > dateKey(now)};
    });
  }
  function ranking(state, courses) {
    return courses.map(course => ({course, xp: state.courses[course.id].completed.length * 50 + (root.AcademyCore.bestResult(course, state.courses[course.id])?.passed ? 250 : 0)})).sort((a,b) => b.xp - a.xp);
  }
  function runCommand(raw, context, now = new Date()) {
    const input = raw.trim(), {state, courses} = context;
    if (!input) return {output: ''};
    if (input === 'clear') return {clear: true, output: ''};
    const cwd = context.cwd || '/home/estudiante';
    const outputs = {
      help: 'help · whoami · date · pwd · ls · cd · cat notas.md · cursos · neofetch · echo · clear\nEntorno de práctica simulado.',
      whoami: state.name || 'estudiante',
      date: now.toLocaleString('es'),
      pwd: cwd,
      cursos: courses.map(c => `${c.id.padEnd(16)} ${state.courses[c.id].completed.length}/${c.lessons.length} lecciones`).join('\n'),
      neofetch: `LinuxMate Academy\nEntorno: simulación local\nUsuario: ${state.name || 'estudiante'}\nCursos: ${courses.length}\nXP: ${summary(state, courses, now).xp}`,
      'ls -lhS /etc/*.conf': '-rw-r--r--  2.9K sysctl.conf\n-rw-r--r--  1.8K resolv.conf\n-rw-r--r--  1.2K hosts.conf',
    };
    if (Object.prototype.hasOwnProperty.call(outputs, input)) return {output: outputs[input]};
    if (/^ls(?: -(?:la|al|lah|lha))?$/.test(input)) return {output: cwd === '/etc' ? 'sysctl.conf  resolv.conf  hosts.conf' : `${input.includes('a') ? '.bashrc  ' : ''}cursos/  proyectos/  labs/  notas.md`};
    if (input === 'cat notas.md') return {output: courses.flatMap(c => Object.entries(state.courses[c.id].notes).filter(([,text]) => text.trim()).map(([i,text]) => `${c.title} · ${c.lessons[i].title}\n${text}`)).join('\n\n') || 'Aún no tienes apuntes guardados.'};
    if (input === 'cd' || input.startsWith('cd ')) {
      const target = input.slice(3).trim();
      const home = '/home/estudiante';
      const next = !target || target === '~' ? home : target.startsWith('/') ? target : target === '..' ? cwd.slice(0,cwd.lastIndexOf('/')) || '/' : `${cwd}/${target}`;
      return ['/', '/home', home, '/etc', `${home}/cursos`, `${home}/proyectos`, `${home}/labs`].includes(next) ? {output: '', cwd: next} : {output: `cd: ${target}: carpeta no disponible en la práctica`};
    }
    if (input === 'echo' || input.startsWith('echo ')) {
      let value = input.slice(5);
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1,-1);
      return {output: value};
    }
    return {output: `${input.split(/\s+/)[0]}: comando no disponible en este entorno. Consulta help.`};
  }
  const api = {daily, completeChallenge, summary, heatmap, ranking, runCommand};
  root.AcademyDashboardModel = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
