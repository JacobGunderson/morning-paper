import type { GamesData } from '../types';
import { button, escapeHtml } from '../lib';

export type GamePayloads = { games: GamesData | null };

export function renderGames(data: GamePayloads): HTMLElement {
  const view = document.createElement('section'); view.className = 'view games-view';
  view.innerHTML = '<div class="section-header"><span>04</span><h1>Games</h1></div>';
  const picker = document.createElement('nav'); picker.className = 'games-toc'; picker.setAttribute('aria-label', 'Games contents');
  const stage = document.createElement('div'); stage.className = 'game-stage';
  const games = [
    ...(data.games?.external ?? []).map(game => ({ id: game.id, title: game.title, create: () => {
      const panel = document.createElement('section'); panel.className = 'external-game';
      if (game.embed_url && game.status === 'ok') {
        const iframe = document.createElement('iframe'); iframe.src = game.embed_url; iframe.title = game.title; iframe.loading = 'lazy'; iframe.setAttribute('allow', 'fullscreen'); panel.append(iframe);
      } else panel.innerHTML = `<p class="notice">EMBED UNAVAILABLE — OPEN TODAY'S PUZZLE</p>`;
      panel.insertAdjacentHTML('beforeend', `<a class="source-link" href="${escapeHtml(game.url)}" target="_blank" rel="noopener noreferrer">OPEN ORIGINAL ↗</a>`);
      return panel;
    }}))
  ];
  games.forEach(game => {
    const contentsButton = button(game.title); contentsButton.className = 'games-toc-button'; contentsButton.dataset.gameTarget = `game-${game.id}`;
    contentsButton.onclick = () => document.getElementById(contentsButton.dataset.gameTarget ?? '')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    picker.append(contentsButton);
    const panel = document.createElement('section'); panel.className = 'game-panel'; panel.id = `game-${game.id}`;
    const heading = document.createElement('h2'); heading.className = 'game-panel-title'; heading.textContent = game.title;
    panel.append(heading, game.create()); stage.append(panel);
  });
  view.append(picker, stage);
  return view;
}
