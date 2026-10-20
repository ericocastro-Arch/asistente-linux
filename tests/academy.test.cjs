const test = require('node:test');
const assert = require('node:assert/strict');
require('../src/gui/web/academy-data.js');
require('../src/gui/web/academy-terminal.js');
require('../src/gui/web/academy-administration.js');
require('../src/gui/web/academy-network.js');
require('../src/gui/web/academy-extra-courses.js');
const courses = require('../src/gui/web/academy-catalog.js');
const core = require('../src/gui/web/academy-core.js');

test('Every course has 15 complete lessons and 75 distinct, explained questions', () => {
  assert.equal(courses.length, 6);
  for (const course of courses) {
    assert.equal(course.lessons.length, 15);
    assert.equal(course.questions.length, 75);
    assert.equal(new Set(course.questions.map(q => q.text)).size, 75);
    assert.equal(new Set(course.questions.map(q => q.id)).size, 75);
    for (const lesson of course.lessons) {
      assert.equal(lesson.questions.length, 5);
      assert.ok(lesson.paragraphs.join(' ').length > 300);
      assert.ok(lesson.command && lesson.detail && lesson.practice);
    }
    for (const question of course.questions) {
      assert.equal(new Set(question.choices).size, 4);
      assert.ok(question.answer >= 0 && question.answer < 4);
      assert.ok(question.explanation.length > 20);
      assert.ok(course.lessons[question.lesson]);
      const original = course.lessons[question.lesson].questions.find(q => q.text === question.text);
      assert.equal(question.choices[question.answer], original.choices[0]);
    }
    for (let i = 0; i < 5; i++) assert.equal(course.questions.filter(q => q.module === i).length, 15);
    for (let i = 0; i < 4; i++) assert.ok(course.questions.filter(q => q.answer === i).length >= 18);
  }
});

test('Unanswered questions cannot be submitted and do not receive credit', () => {
  const course = courses[0], p = core.emptyCourse();
  p.exam = core.startExam();
  assert.equal(core.grade(course, p.exam).correct, 0);
  assert.equal(core.finishExam(course, p), false);
  assert.equal(p.attempts.length, 0);
});

test('Passing threshold is 53 correct; 52 fails even after rounding', () => {
  for (const course of courses) {
    const exam = core.startExam();
    exam.answers = course.questions.map((q, i) => i < 52 ? q.answer : (q.answer + 1) % 4);
    assert.equal(core.grade(course, exam).passed, false);
    exam.answers[52] = course.questions[52].answer;
    assert.equal(core.grade(course, exam).passed, true);
    assert.equal(core.grade(course, exam).correct, 53);
  }
});

test('Exam resumes with selected answers, position, flags and notes', () => {
  const state = core.normalize({}, courses);
  const p = state.courses.terminal;
  p.enrolled = true; p.saved = true; p.current = 3; p.completed = [0, 1, 2];
  p.notes[3] = '<script>literal</script> ñ';
  p.exam = core.startExam(); p.exam.answers[33] = 2; p.exam.index = 33; p.exam.flagged = [4, 33];
  assert.deepEqual(core.normalize(JSON.parse(JSON.stringify(state)), courses), state);
});

test('Normalization removes invalid indices and malformed storage without false completion', () => {
  const state = core.normalize({ courses: { fundamentos: { completed: [0, 0, -1, 15, '2'], current: 90, exam: { answers: [] } } } }, courses);
  assert.deepEqual(state.courses.fundamentos.completed, [0]);
  assert.equal(state.courses.fundamentos.current, 0);
  assert.equal(state.courses.fundamentos.exam, null);
  assert.equal(core.certificateReady(courses[0], state.courses.fundamentos), false);
});

test('Submitting is idempotent; retakes retain history; certificate needs all lessons', () => {
  const course = courses[0], p = core.emptyCourse();
  p.exam = core.startExam(); p.exam.answers = course.questions.map(q => q.answer);
  assert.equal(core.finishExam(course, p).correct, 75);
  assert.equal(core.finishExam(course, p), false);
  assert.equal(p.attempts.length, 1);
  assert.equal(core.certificateReady(course, p), false);
  p.completed = course.lessons.map((_, i) => i);
  assert.equal(core.certificateReady(course, p), true);
  const previous = JSON.stringify(p.attempts[0]);
  p.exam = core.startExam(); p.exam.answers[0] = 0;
  assert.equal(JSON.stringify(p.attempts[0]), previous);
  assert.equal(core.bestResult(course, p).correct, 75);
});

test('A previously earned achievement survives more than ten failed retakes and reload', () => {
  const course = courses[0], state = core.normalize({}, courses), p = state.courses[course.id];
  p.completed = course.lessons.map((_, i) => i);
  p.exam = core.startExam(); p.exam.answers = course.questions.map(q => q.answer);
  core.finishExam(course, p);
  for (let attempt = 0; attempt < 12; attempt++) {
    p.exam = core.startExam(); p.exam.answers = course.questions.map(q => (q.answer + 1) % 4);
    core.finishExam(course, p);
  }
  assert.equal(p.attempts.length, 10);
  const loaded = core.normalize(JSON.parse(JSON.stringify(state)), courses).courses[course.id];
  assert.equal(core.bestResult(course, loaded).correct, 75);
  assert.equal(core.certificateReady(course, loaded), true);
});
