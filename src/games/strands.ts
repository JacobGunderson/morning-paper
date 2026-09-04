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
  const found = new Set<string>(); let active: Array<[number, number]> = []; let pointerId: number | null = null; let hintProgress = 0;
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
  const hint = button('HINT', 'outline-button'); hint.disabled = true;

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
    wordView.textContent = traceWord(gridData, active);
    progress.textContent = `${found.size} OF ${answers.length} THEME WORDS FOUND`;
  };
  const coordinateFromEvent = (event: PointerEvent): [number, number] | null => {
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLButtonElement>('.strand-cell');
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
  board.onpointerdown = event => {
    const coordinate = coordinateFromEvent(event); if (!coordinate) return;
    event.preventDefault(); pointerId = event.pointerId; board.setPointerCapture(pointerId); active = []; extend(coordinate);
  };
  board.onpointermove = event => { if (pointerId !== event.pointerId) return; event.preventDefault(); const coordinate = coordinateFromEvent(event); if (coordinate) extend(coordinate); };
  const finish = (event: PointerEvent) => {
    if (pointerId !== event.pointerId) return;
    const word = traceWord(gridData, active).toUpperCase(); const answer = answers.find(candidate => candidate.word.toUpperCase() === word);
    if (answer && !found.has(answer.word)) {
      found.add(answer.word); message.textContent = answer.spangram ? 'SPANGRAM!' : 'THEME WORD';
      if (found.size === answers.length) message.textContent = 'PUZZLE COMPLETE';
    } else if (word.length >= 4 && (data.valid_words ?? []).includes(word)) {
      earned.value += 1; message.textContent = 'NON-THEME WORD';
      if (earned.value >= 3) hint.disabled = false;
    } else if (word.length >= 4) message.textContent = 'NOT IN WORD LIST';
    active = []; pointerId = null; refreshLines();
  };
  board.onpointerup = finish; board.onpointercancel = event => { active = []; pointerId = null; refreshLines(); event.preventDefault(); };
  hint.onclick = () => {
    const target = answers.find(answer => !found.has(answer.word)); if (!target) return;
    const cell = target.cells[hintProgress % target.cells.length]; cells.get(cellKey(cell))?.classList.add('hinted'); hintProgress += 1;
    earned.value = 0; hint.disabled = true; message.textContent = 'A THEME-WORD LETTER IS HIGHLIGHTED';
  };
  root.append(theme, board, wordView, progress, message, hint); refreshLines();
  root.insertAdjacentHTML('beforeend', `<a class="source-link" href="${data.source_url}" target="_blank" rel="noopener noreferrer">OFFICIAL NYT VERSION ↗</a>`);
  return root;
}
