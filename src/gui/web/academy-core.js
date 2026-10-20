/* Lógica compartida por la interfaz y las pruebas, sin acceso al DOM. */
(function (root) {
  'use strict';
  const EXAM_SIZE = 75;
  const PASS_COUNT = 53;
  const STORAGE_KEY = 'linuxmate_academy_v1';
  const emptyCourse = () => ({ enrolled: false, saved: false, completed: [], current: 0, notes: {}, exam: null, attempts: [], bestAttempt: null });
  const bounded = (value, max) => Number.isInteger(value) && value >= 0 && value < max;
  function normalizeExam(exam, course) {
    if (!exam || !Array.isArray(exam.answers) || exam.answers.length !== EXAM_SIZE) return null;
    const answers = exam.answers.map((answer, i) => bounded(answer, course.questions[i].choices.length) ? answer : null);
    return { answers, index: bounded(exam.index, EXAM_SIZE) ? exam.index : 0,
      flagged: [...new Set((Array.isArray(exam.flagged) ? exam.flagged : []).filter(i => bounded(i, EXAM_SIZE)))],
      started: typeof exam.started === 'string' ? exam.started : new Date().toISOString(),
      finished: typeof exam.finished === 'string' ? exam.finished : null };
  }
  function normalize(raw, courses) {
    const preferences = raw?.preferences || {};
    const result = { version: 1, name: typeof raw?.name === 'string' ? raw.name.slice(0, 80) : '', courses: {},
      preferences: {
        theme: ['electric', 'coral', 'lime'].includes(preferences.theme) ? preferences.theme : 'electric',
        view: preferences.view === 'list' ? 'list' : 'grid',
        effects: preferences.effects !== false,
        focus: preferences.focus === true,
        fontSize: [16, 18, 20].includes(preferences.fontSize) ? preferences.fontSize : 16,
      },
      weeklyGoal: [3, 5, 10].includes(raw?.weeklyGoal) ? raw.weeklyGoal : 3,
      lastCourse: courses.some(c => c.id === raw?.lastCourse) ? raw.lastCourse : '',
      activity: [],
      dashboard: { challenges: {}, agenda: [] },
    };
    for (const course of courses) {
      const saved = raw?.courses?.[course.id] || {};
      const item = emptyCourse();
      item.enrolled = saved.enrolled === true;
      item.saved = saved.saved === true;
      item.completed = [...new Set((Array.isArray(saved.completed) ? saved.completed : []).filter(i => bounded(i, course.lessons.length)))];
      item.current = bounded(saved.current, course.lessons.length) ? saved.current : 0;
      for (let i = 0; i < course.lessons.length; i++) {
        if (typeof saved.notes?.[i] === 'string') item.notes[i] = saved.notes[i].slice(0, 4000);
      }
      item.exam = normalizeExam(saved.exam, course);
      item.attempts = (Array.isArray(saved.attempts) ? saved.attempts : []).slice(-10)
        .map(exam => normalizeExam(exam, course)).filter(exam => exam?.finished);
      const best = normalizeExam(saved.bestAttempt, course);
      item.bestAttempt = best?.finished ? best : null;
      result.courses[course.id] = item;
    }
    const seen = new Set();
    for (const entry of (Array.isArray(raw?.activity) ? raw.activity : []).slice(-1000)) {
      const course = courses.find(c => c.id === entry?.courseId);
      if (!course || !result.courses[course.id].completed.includes(entry.index) || !validDate(entry.date)) continue;
      const key = `${course.id}:${entry.index}`;
      if (!seen.has(key)) { result.activity.push({courseId: course.id, index: entry.index, date: entry.date}); seen.add(key); }
    }
    for (const [date, id] of Object.entries(raw?.dashboard?.challenges || {})) {
      if (validDate(date) && bounded(id, 4)) result.dashboard.challenges[date] = id;
    }
    const agendaIds = new Set();
    for (const entry of (Array.isArray(raw?.dashboard?.agenda) ? raw.dashboard.agenda : []).slice(-100)) {
      if (typeof entry?.id !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(entry.id) || agendaIds.has(entry.id)) continue;
      if (!courses.some(course => course.id === entry.courseId) || typeof entry.title !== 'string' || !entry.title.trim()) continue;
      if (typeof entry.when !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(entry.when) || !validDate(entry.when.slice(0,10))) continue;
      if (Number(entry.when.slice(11,13)) > 23 || Number(entry.when.slice(14)) > 59) continue;
      result.dashboard.agenda.push({id: entry.id, courseId: entry.courseId, title: entry.title.trim().slice(0,120), when: entry.when, done: entry.done === true});
      agendaIds.add(entry.id);
    }
    return result;
  }
  function localDate(value = new Date()) {
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  }
  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const parsed = new Date(`${value}T12:00:00`);
    return !Number.isNaN(parsed.getTime()) && localDate(parsed) === value;
  }
  function recordCompletion(state, course, index, now = new Date()) {
    if (!bounded(index, course.lessons.length) || state.courses[course.id].completed.includes(index)) return false;
    state.courses[course.id].completed.push(index);
    state.activity.push({courseId: course.id, index, date: localDate(now)});
    return true;
  }
  function weeklyProgress(state, now = new Date()) {
    const monday = new Date(now);
    monday.setDate(now.getDate() - (now.getDay() + 6) % 7);
    const start = localDate(monday), today = localDate(now);
    const count = state.activity.filter(entry => entry.date >= start && entry.date <= today).length;
    return {count, goal: state.weeklyGoal, percent: Math.min(100, Math.round(count / state.weeklyGoal * 100))};
  }
  function startExam() {
    return { answers: Array(EXAM_SIZE).fill(null), index: 0, flagged: [], started: new Date().toISOString(), finished: null };
  }
  function grade(course, exam) {
    let correct = 0;
    const modules = course.modules.map(title => ({ title, correct: 0, total: 0 }));
    course.questions.forEach((question, i) => {
      const match = exam.answers[i] === question.answer;
      if (match) correct++;
      modules[question.module].total++;
      if (match) modules[question.module].correct++;
    });
    return { correct, total: EXAM_SIZE, percent: Math.round(correct / EXAM_SIZE * 100), passed: correct >= PASS_COUNT, modules };
  }
  function finishExam(course, progress) {
    if (!progress.exam || progress.exam.finished) return false;
    if (progress.exam.answers.some(answer => answer === null)) return false;
    progress.exam.finished = new Date().toISOString();
    const previousBest = bestResult(course, progress);
    if (!previousBest || grade(course, progress.exam).correct > previousBest.correct) {
      progress.bestAttempt = JSON.parse(JSON.stringify(progress.exam));
    } else if (!progress.bestAttempt) {
      // Conserva el mejor intento de los estados guardados antes de este campo.
      progress.bestAttempt = progress.attempts.reduce((best, exam) => !best || grade(course, exam).correct > grade(course, best).correct ? exam : best, null);
    }
    progress.attempts = [...progress.attempts, JSON.parse(JSON.stringify(progress.exam))].slice(-10);
    return grade(course, progress.exam);
  }
  function bestResult(course, progress) {
    return [...progress.attempts, ...(progress.bestAttempt ? [progress.bestAttempt] : [])].reduce((best, exam) => {
      const result = grade(course, exam);
      return !best || result.correct > best.correct ? { ...result, date: exam.finished } : best;
    }, null);
  }
  function certificateReady(course, progress) {
    return progress.completed.length === course.lessons.length && !!bestResult(course, progress)?.passed;
  }
  const api = { EXAM_SIZE, PASS_COUNT, STORAGE_KEY, emptyCourse, normalize, startExam, grade, finishExam, bestResult, certificateReady, recordCompletion, weeklyProgress, localDate };
  root.AcademyCore = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
