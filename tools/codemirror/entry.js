// Punto de entrada del bundle de CodeMirror 6 para el Módulo Dev.
// Se compila con `npm run build` y expone `window.CM`.
import { basicSetup } from 'codemirror';
import { EditorView, keymap } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { indentWithTab } from '@codemirror/commands';
import { HighlightStyle, StreamLanguage, syntaxHighlighting } from '@codemirror/language';
import { tags as t } from '@lezer/highlight';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { shell } from '@codemirror/legacy-modes/mode/shell';

// Colores alineados con el diseño del Módulo Dev (paleta tipo GitHub Dark).
const devTheme = EditorView.theme({
  '&': { color: '#e6edf3', backgroundColor: '#161b22', height: '100%' },
  '.cm-scroller': { fontFamily: "'Cascadia Code', 'JetBrains Mono', Consolas, monospace", lineHeight: '1.75' },
  '.cm-content': { caretColor: '#4f8cff', padding: '12px 0' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: '#4f8cff' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: 'rgba(79,140,255,.28)' },
  '.cm-gutters': { backgroundColor: '#161b22', color: '#4b5568', border: 'none' },
  '.cm-activeLine': { backgroundColor: 'rgba(79,140,255,.06)' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent', color: '#8b98a9' },
  '.cm-tooltip': { backgroundColor: '#1c2330', border: '1px solid #2d3748', color: '#e6edf3' },
  '.cm-tooltip-autocomplete ul li[aria-selected]': { backgroundColor: 'rgba(79,140,255,.3)', color: '#fff' },
  '.cm-panels': { backgroundColor: '#1c2330', color: '#e6edf3' },
  '.cm-searchMatch': { backgroundColor: 'rgba(210,153,34,.3)' },
  '.cm-matchingBracket': { backgroundColor: 'rgba(63,185,80,.25)', outline: 'none' },
}, { dark: true });

const devHighlight = HighlightStyle.define([
  { tag: [t.keyword, t.controlKeyword, t.operatorKeyword, t.definitionKeyword, t.moduleKeyword], color: '#ff7b72' },
  { tag: [t.string, t.special(t.string), t.regexp], color: '#a5d6ff' },
  { tag: [t.comment, t.lineComment, t.blockComment], color: '#7d8590', fontStyle: 'italic' },
  { tag: [t.function(t.variableName), t.function(t.propertyName), t.definition(t.function(t.variableName))], color: '#d2a8ff' },
  { tag: [t.number, t.bool, t.null, t.atom], color: '#79c0ff' },
  { tag: [t.className, t.typeName, t.definition(t.typeName)], color: '#ffa657' },
  { tag: [t.tagName], color: '#7ee787' },
  { tag: [t.attributeName, t.propertyName], color: '#79c0ff' },
  { tag: [t.heading], color: '#4f8cff', fontWeight: 'bold' },
  { tag: [t.link, t.url], color: '#39c5cf', textDecoration: 'underline' },
  { tag: [t.invalid], color: '#f85149' },
]);

function languageFor(path) {
  const name = (path || '').toLowerCase();
  if (name.endsWith('.py')) return python();
  if (name.endsWith('.js') || name.endsWith('.mjs') || name.endsWith('.cjs')) return javascript();
  if (name.endsWith('.ts')) return javascript({ typescript: true });
  if (name.endsWith('.html') || name.endsWith('.htm')) return html();
  if (name.endsWith('.css')) return css();
  if (name.endsWith('.json')) return json();
  if (name.endsWith('.md')) return markdown();
  if (name.endsWith('.sh') || name.endsWith('.bash')) return StreamLanguage.define(shell);
  return [];
}

export {
  EditorView,
  EditorState,
  Compartment,
  basicSetup,
  keymap,
  indentWithTab,
  devTheme,
  languageFor,
};
export const devHighlighting = syntaxHighlighting(devHighlight);
