import type { StrandsData } from '../types';
import { button } from '../lib';
import { adjacent, cellsBetween, traceWord } from './logic';

const cellKey = ([row, column]: [number, number]) => `${row},${column}`;

export function createStrands(data: StrandsData | null): HTMLElement {
  const root = document.createElement('section'); root.className = 'local-game strands';
  if (!data?.grid || !data.answers || !data.theme || data.status !== 'ok') {
    root.innerHTML = '<p class="notice">TODAY\'S STRANDS DATA UNAVAILABLE</p><a class="source-link" href="https://www.nytimes.com/games/strands" target="_blank" rel="noopener noreferrer">OPEN OFFICIAL GAME ↗</a>';
    return root;
  }
  const gridData = data.grid;
  const answers = data.answers;
  const found = new Set<string>(); const hinted = new Set<string>(); let active: Array<[number, number]> = [];
  let pointerId: number | null = null; let pointerStart: [number, number] | null = null; let dragging = false; let suppressClick = false;
  const earned = { value: 0 };
  const theme = document.createElement('p'); theme.className = 'strands-theme'; theme.innerHTML = `TODAY'S THEME<br><strong>${data.theme}</strong>`;
  const board = document.createElement('div'); board.className = 'strands-board'; board.style.setProperty('--rows', String(gridData.length));
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('aria-hidden', 'true'); svg.setAttribute('viewBox', `0 0 600 ${gridData.length * 100}`); svg.setAttribute('preserveAspectRatio', 'none');
  const cells = new Map<string, HTMLButtonElement>();
  gridData.forEach((row, rowIndex) => [...row].forEach((letter, columnIndex) => {
    const cell = button(letter, 'strand-cell'); const coordinate: [number, number] = [rowIndex, columnIndex];
    cell.dataset.row = String(rowIndex); cell.dataset.column = String(columnIndex); cell.setAttribute('aria-label', `${letter}, row ${rowIndex + 1}, column ${columnIndex + 1}`);
    cells.set(cellKey(coordinate), cell); board.append(cell);
  }));
  board.prepend(svg);
  const wordView = document.createElement('p'); wordView.className = 'strand-word'; wordView.setAttribute('role', 'status');
  const message = document.createElement('p'); message.className = 'game-message';
  const progress = document.createElement('p'); progress.className = 'strands-progress';
  const hintStatus = document.createElement('p'); hintStatus.className = 'strands-hint-status';
  const hint = button('HINT', 'outline-button'); hint.disabled = true;
  const check = button('CHECK WORD', 'solid-button');
  const clear = button('CLEAR', 'outline-button');
  const controls = document.createElement('div'); controls.className = 'game-controls strands-controls'; controls.append(check, clear, hint);

  const refreshLines = () => {
    svg.replaceChildren();
    const draw = (path: Array<[number, number]>, className: string) => {
      if (path.length < 2) return;
      const points = path.map(([row, column]) => `${column * 100 + 50},${row * 100 + 50}`).join(' ');
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline'); line.setAttribute('points', points); line.setAttribute('class', className); svg.append(line);
    };
    answers.filter(answer => found.has(answer.word)).forEach(answer => draw(answer.cells, answer.spangram ? 'spangram-line' : 'found-line'));
    draw(active, 'active-line');
    cells.forEach(cell => { cell.classList.remove('selected', 'found', 'spangram', 'hinted'); });
    answers.filter(answer => found.has(answer.word)).forEach(answer => answer.cells.forEach(position => cells.get(cellKey(position))?.classList.add(answer.spangram ? 'spangram' : 'found')));
    active.forEach(position => cells.get(cellKey(position))?.classList.add('selected'));
    hinted.forEach(key => cells.get(key)?.classList.add('hinted'));
    wordView.textContent = traceWord(gridData, active);
    progress.textContent = `${found.size} OF ${answers.length} THEME WORDS FOUND`;
    hintStatus.textContent = hint.disabled ? `HINTS: ${earned.value} OF 3 NON-THEME WORDS` : 'HINT READY';
  };
  const coordinateFromEvent = (event: PointerEvent): [number, number] | null => {
    const directTarget = event.target instanceof Element ? event.target.closest<HTMLButtonElement>('.strand-cell') : null;
    const target = directTarget ?? document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLButtonElement>('.strand-cell');
    if (!target || !board.contains(target)) return null;
    return [Number(target.dataset.row), Number(target.dataset.column)];
  };
  const extendOne = (coordinate: [number, number]) => {
    const existing = active.findIndex(cell => cellKey(cell) === cellKey(coordinate));
    if (existing === active.length - 2) { active.pop(); refreshLines(); return; }
    if (existing >= 0 || (active.length && !adjacent(active.at(-1)!, coordinate))) return;
    active.push(coordinate); refreshLines();
  };
  const extend = (coordinate: [number, number]) => {
    const previous = active.at(-1);
    if (!previous || adjacent(previous, coordinate)) { extendOne(coordinate); return; }
    cellsBetween(previous, coordinate).forEach(extendOne);
  };
  const submit = () => {
    const word = traceWord(gridData, active).toUpperCase(); const answer = answers.find(candidate => candidate.word.toUpperCase() === word);
    if (answer && !found.has(answer.word)) {
      found.add(answer.word); message.textContent = answer.spangram ? 'SPANGRAM!' : 'THEME WORD';
      if (found.size === answers.length) message.textContent = 'PUZZLE COMPLETE';
    } else if (answer) {
      message.textContent = 'ALREADY FOUND';
    } else if (word.length >= 4 && (data.valid_words ?? []).includes(word)) {
      earned.value += 1; message.textContent = 'NON-THEME WORD';
      if (earned.value >= 3) hint.disabled = false;
    } else if (word.length >= 4) {
      message.textContent = 'NOT IN WORD LIST';
    } else if (word) {
      message.textContent = 'SELECT AT LEAST 4 LETTERS';
    }
    active = []; refreshLines();
  };
  const selectByClick = (coordinate: [number, number]) => {
    if (!active.length) { active = [coordinate]; message.textContent = 'SELECT CONNECTING LETTERS, THEN CHECK WORD'; refreshLines(); return; }
    const before = active.length; extend(coordinate);
    if (active.length === before && cellKey(active.at(-1)!) !== cellKey(coordinate)) message.textContent = 'NEXT LETTER MUST TOUCH THE SELECTION';
    const word = traceWord(gridData, active).toUpperCase();
    if (answers.some(answer => !found.has(answer.word) && answer.word.toUpperCase() === word) || (data.valid_words ?? []).includes(word)) submit();
  };
  const beginPointerPath = (event: PointerEvent, coordinate: [number, number]) => {
    pointerId = event.pointerId; pointerStart = coordinate; dragging = false;
    board.setPointerCapture(event.pointerId);
  };
  board.onpointermove = event => {
    if (pointerId !== event.pointerId || !pointerStart) return;
    const coordinate = coordinateFromEvent(event); if (!coordinate) return;
    if (!dragging && cellKey(coordinate) !== cellKey(pointerStart)) { dragging = true; active = [pointerStart]; board.setPointerCapture(event.pointerId); }
    if (dragging) { event.preventDefault(); extend(coordinate); }
  };
  const finish = (event: PointerEvent) => {
    if (pointerId !== event.pointerId) return;
    if (dragging) { suppressClick = true; submit(); }
    if (board.hasPointerCapture(event.pointerId)) board.releasePointerCapture(event.pointerId);
    pointerId = null; pointerStart = null; dragging = false;
  };
  board.onpointerup = finish; board.onpointercancel = event => { pointerId = null; pointerStart = null; dragging = false; event.preventDefault(); };
  // The individual cells own click handling. Pointer capture changes the event target
  // during a drag, so relying on one delegated board click made taps unreliable.
  cells.forEach((cell, key) => {
    const [row, column] = key.split(',').map(Number) as [number, number];
    cell.onpointerdown = event => beginPointerPath(event, [row, column]);
    cell.onclick = () => {
      if (suppressClick) { suppressClick = false; return; }
      selectByClick([row, column]);
    };
  });
  check.onclick = submit;
  clear.onclick = () => { active = []; message.textContent = ''; refreshLines(); };
  hint.onclick = () => {
    const target = answers.find(answer => !found.has(answer.word)); if (!target) return;
    const cell = target.cells.find(position => !hinted.has(cellKey(position)));
    if (!cell) { message.textContent = 'THIS WORD IS ALREADY FULLY HINTED'; return; }
    hinted.add(cellKey(cell));
    earned.value = 0; hint.disabled = true; message.textContent = 'A THEME-WORD LETTER IS HIGHLIGHTED';
    refreshLines();
  };
  root.append(theme, board, wordView, progress, hintStatus, message, controls); refreshLines();
  root.insertAdjacentHTML('beforeend', `<a class="source-link" href="${data.source_url}" target="_blank" rel="noopener noreferrer">OFFICIAL NYT VERSION ↗</a>`);
  return root;
}
