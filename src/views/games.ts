import type { ConnectionsData, GamesData, StrandsData, WordleData } from '../types';
import { button, escapeHtml } from '../lib';
import { createWordle } from '../games/wordle';
import { createConnections } from '../games/connections';
import { createStrands } from '../games/strands';

export type GamePayloads = { games: GamesData | null; wordle: WordleData | null; connections: ConnectionsData | null; strands: StrandsData | null };

export function renderGames(data: GamePayloads): HTMLElement {
  const view = document.createElement('section'); view.className = 'view games-view';
  view.innerHTML = '<div class="section-header"><span>04</span><h1>Games</h1></div>';
  const picker = document.createElement('div'); picker.className = 'game-picker'; picker.setAttribute('role', 'tablist'); picker.setAttribute('aria-label', 'Choose a game');
  const stage = document.createElement('div'); stage.className = 'game-stage';
  const games = [
    { id: 'wordle', title: 'Wordle', create: () => createWordle(data.wordle) },
    { id: 'connections', title: 'Connections', create: () => createConnections(data.connections) },
    { id: 'strands', title: 'Strands', create: () => createStrands(data.strands) },
    ...(data.games?.external ?? []).map(game => ({ id: game.id, title: game.title, create: () => {
      const panel = document.createElement('section'); panel.className = 'external-game';
      if (game.embed_url && game.status === 'ok') {
        const iframe = document.createElement('iframe'); iframe.src = game.embed_url; iframe.title = game.title; iframe.loading = 'lazy'; iframe.setAttribute('allow', 'fullscreen'); panel.append(iframe);
      } else panel.innerHTML = `<p class="notice">EMBED UNAVAILABLE — OPEN TODAY'S PUZZLE</p>`;
      panel.insertAdjacentHTML('beforeend', `<a class="source-link" href="${escapeHtml(game.url)}" target="_blank" rel="noopener noreferrer">OPEN ORIGINAL ↗</a>`);
      return panel;
    }}))
  ];
  const panels = new Map<string, HTMLElement>();
  const select = (id: string) => {
    let panel = panels.get(id);
    if (!panel) {
      const game = games.find(candidate => candidate.id === id)!; panel = game.create(); panel.classList.add('game-panel'); panel.id = `game-${id}`; panel.setAttribute('role', 'tabpanel'); panels.set(id, panel); stage.append(panel);
    }
    panels.forEach((element, key) => element.hidden = key !== id);
    picker.querySelectorAll('button').forEach(tab => { const selected = tab.dataset.game === id; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; });
    localStorage.setItem('morning-paper-game', id);
  };
  games.forEach(game => {
    const tab = button(game.title); tab.dataset.game = game.id; tab.setAttribute('role', 'tab'); tab.setAttribute('aria-controls', `game-${game.id}`); tab.onclick = () => select(game.id); picker.append(tab);
  });
  view.append(picker, stage);
  const saved = localStorage.getItem('morning-paper-game'); select(games.some(game => game.id === saved) ? saved! : 'wordle');
  return view;
}
