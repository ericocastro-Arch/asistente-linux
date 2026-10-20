(function (root) {
  'use strict';
  root.AcademyCourses.forEach((course, ci) => {
    course.minutes = course.lessons.reduce((sum, lesson) => sum + lesson.minutes, 0);
    course.questions = [];
    course.lessons.forEach((lesson, li) => {
      lesson.module = Math.floor(li / 3);
      lesson.questions.forEach((question, qi) => {
        const offset = (li * 7 + qi * 3 + ci) % 4;
        const choices = question.choices.slice(offset).concat(question.choices.slice(0, offset));
        course.questions.push({ ...question, choices, answer: (4 - offset) % 4, lesson: li, module: lesson.module, id: `${course.id}-${li}-${qi}` });
      });
    });
  });
  if (typeof module !== 'undefined') module.exports = root.AcademyCourses;
})(globalThis);
