import type { Comic } from '../types';
import { escapeHtml } from '../lib';

function providerLabel(provider: string): string {
  return ({ gocomics_snapshot: 'GoComics', comics_kingdom: 'Comics Kingdom', farside: 'The Far Side', xkcd: 'xkcd' } as Record<string, string>)[provider] ?? provider;
}

export function renderFunnies(comics: Comic[] | null, editionDate: string): HTMLElement {
  const view = document.createElement('section');
  view.className = 'view funnies-view';
  view.innerHTML = '<div class="section-header"><span>03</span><h1>Funnies</h1></div>';
  const sheet = document.createElement('div');
  sheet.className = 'comic-sheet';
  const todaysComics = comics?.filter(comic => comic.images.length > 0 && comic.published_date === editionDate) ?? [];
  const notUpdated = comics?.filter(comic => !todaysComics.includes(comic)) ?? [];
  if (!comics?.length) sheet.innerHTML = '<p class="notice">TODAY\'S COMICS ARE UNAVAILABLE.</p>';
  if (comics?.length && !todaysComics.length) sheet.innerHTML = '<p class="notice">NO FRESH COMICS WERE AVAILABLE FOR THIS EDITION.</p>';
  todaysComics.forEach(comic => {
    const item = document.createElement('article');
    item.className = 'comic';
    item.innerHTML = `
      <header><h2><a href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(comic.name)}</a></h2>${comic.author ? `<p class="comic-byline">${escapeHtml(comic.author)}</p>` : ''}</header>
      <div class="comic-images">${comic.images.map((src, index) => `<img loading="lazy" src="${escapeHtml(src)}" alt="${escapeHtml(comic.name)}${comic.images.length > 1 ? `, panel ${index + 1}` : ''}">`).join('')}</div>`;
    sheet.append(item);
  });
  view.append(sheet);
  if (notUpdated.length) {
    const unavailable = document.createElement('section');
    unavailable.className = 'comic-updates-missing';
    const bySource = new Map<string, Comic[]>();
    notUpdated.forEach(comic => {
      const source = providerLabel(comic.provider);
      bySource.set(source, [...(bySource.get(source) ?? []), comic]);
    });
    const groups = [...bySource.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([source, sourceComics]) => `
      <section class="comic-missing-source"><h3>${escapeHtml(source)}</h3><ul>${sourceComics
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(comic => `<li><a href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(comic.name)}</a></li>`).join('')}</ul></section>`).join('');
    unavailable.innerHTML = `<h2>Comics that didn’t update today</h2><p>No fresh edition was available for these strips.</p><div class="comic-missing-sources">${groups}</div>`;
    view.append(unavailable);
  }
  return view;
}
