import type { WordleData } from '../types';
import { button } from '../lib';
import { scoreWordle, type TileState } from './logic';

const WORDS = new Set(['about','adieu','after','again','alert','alone','arise','audio','avoid','basic','beach','berry','black','brain','break','bring','brown','cause','chair','charm','chase','clean','clear','close','cloud','crane','cream','dance','dream','earth','field','first','flame','fresh','giant','grace','grand','great','green','heart','house','light','media','night','ocean','paper','place','plant','point','pride','quiet','raise','route','score','shine','slate','smile','sound','space','spare','steam','stone','story','stray','table','their','there','today','trace','train','water','whale','white','world','write']);

export function createWordle(data: WordleData | null): HTMLElement {
  const root = document.createElement('section');
  root.className = 'local-game wordle';
  if (!data?.solution || data.status !== 'ok') {
    root.innerHTML = '<p class="notice">TODAY\'S WORDLE DATA UNAVAILABLE</p><a class="source-link" href="https://www.nytimes.com/games/wordle/index.html" target="_blank" rel="noopener noreferrer">OPEN OFFICIAL GAME ↗</a>';
    return root;
  }
  const solution = data.solution.toLowerCase();
  WORDS.add(solution);
  let row = 0; let guess = ''; let finished = false;
  const grid = document.createElement('div'); grid.className = 'wordle-grid'; grid.setAttribute('aria-label', 'Wordle board');
  const cells: HTMLDivElement[][] = Array.from({ length: 6 }, () => Array.from({ length: 5 }, () => {
    const cell = document.createElement('div'); cell.className = 'wordle-cell'; cell.setAttribute('aria-hidden', 'true'); grid.append(cell); return cell;
  }));
  const message = document.createElement('p'); message.className = 'game-message'; message.setAttribute('role', 'status');
  const keys = new Map<string, HTMLButtonElement>();
  const keyboard = document.createElement('div'); keyboard.className = 'keyboard';
  const update = () => cells[row]?.forEach((cell, index) => cell.textContent = guess[index]?.toUpperCase() ?? '');
  const input = (key: string) => {
    if (finished) return;
    if (key === 'BACKSPACE') { guess = guess.slice(0, -1); update(); return; }
    if (key === 'ENTER') {
      if (guess.length !== 5) { message.textContent = 'NOT ENOUGH LETTERS'; return; }
      if (!WORDS.has(guess) && guess !== solution) { message.textContent = 'WORD NOT IN LIST'; return; }
      const states = scoreWordle(guess, solution);
      states.forEach((state: TileState, index) => {
        cells[row][index].dataset.state = state;
        const keyButton = keys.get(guess[index]);
        if (keyButton && (state === 'correct' || keyButton.dataset.state !== 'correct')) keyButton.dataset.state = state;
      });
      if (guess === solution) { message.textContent = 'SOLVED'; finished = true; return; }
      row += 1; guess = '';
      if (row === 6) { message.textContent = `THE WORD WAS ${solution.toUpperCase()}`; finished = true; }
      return;
    }
    if (/^[A-Z]$/.test(key) && guess.length < 5) { guess += key.toLowerCase(); update(); }
  };
  ['QWERTYUIOP','ASDFGHJKL','ZXCVBNM'].forEach((line, lineIndex) => {
    const rowElement = document.createElement('div');
    if (lineIndex === 2) { const enter = button('ENTER'); enter.className = 'wide-key'; enter.onclick = () => input('ENTER'); rowElement.append(enter); }
    [...line].forEach(letter => { const key = button(letter); key.onclick = () => input(letter); keys.set(letter.toLowerCase(), key); rowElement.append(key); });
    if (lineIndex === 2) { const backspace = button('⌫', 'wide-key'); backspace.setAttribute('aria-label', 'Backspace'); backspace.onclick = () => input('BACKSPACE'); rowElement.append(backspace); }
    keyboard.append(rowElement);
  });
  const keyHandler = (event: KeyboardEvent) => {
    if (!root.isConnected || !root.contains(document.activeElement)) return;
    if (event.key === 'Enter') input('ENTER'); else if (event.key === 'Backspace') input('BACKSPACE'); else input(event.key.toUpperCase());
  };
  window.addEventListener('keydown', keyHandler);
  root.append(grid, message, keyboard);
  root.insertAdjacentHTML('beforeend', `<a class="source-link" href="${data.source_url}" target="_blank" rel="noopener noreferrer">OFFICIAL NYT VERSION ↗</a>`);
  return root;
}
