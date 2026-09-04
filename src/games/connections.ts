import type { ConnectionsData, ConnectionsGroup } from '../types';
import { button } from '../lib';
import { evaluateConnection } from './logic';

const shuffle = <T>(items: T[]): T[] => items.map(value => ({ value, order: Math.random() })).sort((a, b) => a.order - b.order).map(item => item.value);

export function createConnections(data: ConnectionsData | null): HTMLElement {
  const root = document.createElement('section'); root.className = 'local-game connections';
  if (!data?.groups || data.status !== 'ok') {
    root.innerHTML = '<p class="notice">TODAY\'S CONNECTIONS DATA UNAVAILABLE</p><a class="source-link" href="https://www.nytimes.com/games/connections" target="_blank" rel="noopener noreferrer">OPEN OFFICIAL GAME ↗</a>';
    return root;
  }
  let remaining = shuffle(data.groups.flatMap(group => group.members));
  let unsolved = [...data.groups]; let selected = new Set<string>(); let mistakes = 4;
  const solved = document.createElement('div'); solved.className = 'solved-groups';
  const grid = document.createElement('div'); grid.className = 'connections-grid';
  const message = document.createElement('p'); message.className = 'game-message'; message.setAttribute('role', 'status');
  const mistakesView = document.createElement('p'); mistakesView.className = 'mistakes';
  const controls = document.createElement('div'); controls.className = 'game-controls';
  const deselect = button('DESELECT ALL', 'outline-button');
  const shuffleButton = button('SHUFFLE', 'outline-button');
  const submit = button('SUBMIT', 'solid-button');
  const render = () => {
    mistakesView.textContent = `MISTAKES REMAINING  ${'●'.repeat(mistakes)}${'○'.repeat(4 - mistakes)}`;
    grid.replaceChildren(...remaining.map(word => {
      const tile = button(word, 'connection-tile'); tile.setAttribute('aria-pressed', String(selected.has(word)));
      tile.onclick = () => { if (selected.has(word)) selected.delete(word); else if (selected.size < 4) selected.add(word); render(); };
      return tile;
    }));
  };
  deselect.onclick = () => { selected.clear(); render(); };
  shuffleButton.onclick = () => { remaining = shuffle(remaining); render(); };
  submit.onclick = () => {
    if (selected.size !== 4) { message.textContent = 'SELECT EXACTLY FOUR'; return; }
    const result = evaluateConnection([...selected], unsolved);
    if (result.group) {
      const group = result.group as ConnectionsGroup;
      const row = document.createElement('div'); row.className = 'solved-group'; row.dataset.level = String(group.level);
      row.innerHTML = `<strong>${group.category}</strong><span>${group.members.join(', ')}</span>`; solved.append(row);
      remaining = remaining.filter(word => !selected.has(word)); unsolved = unsolved.filter(candidate => candidate !== group); selected.clear();
      message.textContent = unsolved.length ? 'CORRECT' : 'PERFECT';
    } else {
      mistakes -= 1; message.textContent = result.oneAway ? 'ONE AWAY…' : 'NOT QUITE';
      if (mistakes === 0) { message.textContent = 'BETTER LUCK TOMORROW'; submit.disabled = true; }
    }
    render();
  };
  controls.append(shuffleButton, deselect, submit); root.append(solved, grid, mistakesView, message, controls); render();
  root.insertAdjacentHTML('beforeend', `<a class="source-link" href="${data.source_url}" target="_blank" rel="noopener noreferrer">OFFICIAL NYT VERSION ↗</a>`);
  return root;
}
