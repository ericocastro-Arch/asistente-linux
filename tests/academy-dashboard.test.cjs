const test = require('node:test');
const assert = require('node:assert/strict');
require('../src/gui/web/academy-data.js');
require('../src/gui/web/academy-terminal.js');
require('../src/gui/web/academy-administration.js');
require('../src/gui/web/academy-network.js');
require('../src/gui/web/academy-extra-courses.js');
const courses = require('../src/gui/web/academy-catalog.js');
const core = require('../src/gui/web/academy-core.js');
const dashboard = require('../src/gui/web/academy-dashboard-model.js');

test('Dashboard migration retains lessons, notes, active exams and preferences', () => {
  const old = core.normalize({},courses), course = courses[0];
  const p = old.courses[course.id];
  p.enrolled = true; p.completed = [0,1]; p.notes[0] = 'Mi apunte';
  p.exam = core.startExam(); p.exam.answers[4] = 2; p.exam.flagged = [4];
  old.preferences.theme = 'coral'; old.preferences.effects = false;
  delete old.dashboard;
  const loaded = core.normalize(old,courses);
  assert.deepEqual(loaded.courses,old.courses);
  assert.deepEqual(loaded.preferences,old.preferences);
  assert.deepEqual(loaded.dashboard,{challenges:{},agenda:[]});
});

test('Daily challenge awards XP once per local day and survives reload', () => {
  const state = core.normalize({},courses), now = new Date(2026,9,9,23,58);
  const challenge = dashboard.daily(now);
  assert.deepEqual(dashboard.completeChallenge(state,'incorrecto',now),{correct:false,awarded:false});
  assert.deepEqual(dashboard.completeChallenge(state,challenge.solution,now),{correct:true,awarded:true});
  assert.deepEqual(dashboard.completeChallenge(state,challenge.solution,now),{correct:true,awarded:false});
  const loaded = core.normalize(JSON.parse(JSON.stringify(state)),courses);
  assert.equal(dashboard.summary(loaded,courses,now).xp,150);
  assert.equal(dashboard.summary(loaded,courses,now).streak,1);
  const tomorrow = new Date(2026,9,10,0,1);
  assert.notEqual(dashboard.daily(tomorrow).date,challenge.date);
  assert.equal(dashboard.completeChallenge(loaded,dashboard.daily(tomorrow).solution,tomorrow).awarded,true);
  assert.equal(dashboard.summary(loaded,courses,tomorrow).streak,2);
});

test('XP uses unique completed lessons and approved courses rather than retake count', () => {
  const state = core.normalize({},courses), course = courses[0], now = new Date(2026,9,9);
  core.recordCompletion(state,course,0,now);
  core.recordCompletion(state,course,0,now);
  const p = state.courses[course.id];
  for (let i=0;i<3;i++) { p.exam = core.startExam(); p.exam.answers = course.questions.map(q=>q.answer); core.finishExam(course,p); }
  assert.equal(dashboard.summary(state,courses,now).xp,300);
  assert.equal(dashboard.ranking(state,courses)[0].xp,300);
});

test('Heatmap reflects actual local dates and a streak remains active through yesterday', () => {
  const state = core.normalize({},courses), course = courses[0];
  core.recordCompletion(state,course,0,new Date(2026,9,7));
  core.recordCompletion(state,course,1,new Date(2026,9,8));
  const now = new Date(2026,9,9);
  assert.equal(dashboard.summary(state,courses,now).streak,2);
  assert.equal(dashboard.summary(state,courses,new Date(2026,9,10)).streak,0);
  const cells = dashboard.heatmap(state,courses,now);
  assert.equal(cells.length,112);
  assert.equal(cells.find(c=>c.date==='2026-10-08').count,1);
  assert.equal(cells.find(c=>c.date==='2026-10-09').count,0);
  assert.ok(cells.filter(c=>c.future).every(c=>c.count===0));
});

test('Weekly XP includes the first passing exam and does not count a later retake again', () => {
  const state = core.normalize({},courses), course = courses[0], p = state.courses[course.id];
  const passed = core.startExam(); passed.answers = course.questions.map(q=>q.answer); passed.finished = new Date(2026,9,8,12).toISOString();
  p.attempts = [passed]; p.bestAttempt = passed;
  assert.equal(dashboard.summary(state,courses,new Date(2026,9,9)).weekXP,250);
  p.attempts.push({...passed,finished:new Date(2026,9,14,12).toISOString()});
  assert.equal(dashboard.summary(state,courses,new Date(2026,9,15)).weekXP,0);
  assert.equal(dashboard.summary(state,courses,new Date(2026,9,15)).xp,250);
});

test('Agenda survives normalization, validates dates and preserves a bounded unique list', () => {
  const state = core.normalize({},courses);
  const item = {id:'session-1',courseId:'terminal',title:'Mi estudio',when:'2026-10-10T18:30',done:false};
  state.dashboard.agenda = [item,item,{...item,id:'bad-time',when:'2026-10-10T25:30'},{...item,id:'bad-date',when:'2026-02-30T10:00'},{...item,id:'bad-course',courseId:'missing'}];
  const loaded = core.normalize(state,courses);
  assert.deepEqual(loaded.dashboard.agenda,[item]);
  assert.deepEqual(core.normalize(loaded,courses),loaded);
});

test('Sandbox reads the existing progress and notes and never treats input as executable code', () => {
  const state = core.normalize({},courses), ctx = {state,courses};
  state.name = '<img src=x onerror=alert(1)>';
  state.courses.fundamentos.notes[0] = 'Mi nota literal';
  const before = JSON.stringify(state);
  assert.equal(dashboard.runCommand('whoami',ctx).output,state.name);
  assert.match(dashboard.runCommand('cat notas.md',ctx).output,/Mi nota literal/);
  assert.match(dashboard.runCommand('sudo rm -rf /',ctx).output,/no disponible/);
  assert.match(dashboard.runCommand('ls; touch archivo',ctx).output,/no disponible/);
  assert.equal(dashboard.runCommand('echo "<script>"',ctx).output,'<script>');
  assert.equal(dashboard.runCommand('cd /etc',ctx).cwd,'/etc');
  assert.equal(dashboard.runCommand('cd /root',ctx).cwd,undefined);
  assert.equal(dashboard.runCommand('clear',ctx).clear,true);
  assert.equal(JSON.stringify(state),before);
});
