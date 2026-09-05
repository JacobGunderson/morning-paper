import type { Comic } from '../types';
import { escapeHtml } from '../lib';

function dateLabel(value?: string | null): string {
  if (!value) return 'DATE UNAVAILABLE';
  return new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`));
}

function providerLabel(provider: string): string {
  return ({ gocomics: 'GoComics', comics_kingdom: 'Comics Kingdom', farside: 'The Far Side', xkcd: 'xkcd' } as Record<string, string>)[provider] ?? provider;
}

export function renderFunnies(comics: Comic[] | null): HTMLElement {
  const view = document.createElement('section');
  view.className = 'view funnies-view';
  view.innerHTML = '<div class="section-header"><span>03</span><h1>Funnies</h1></div>';
  const sheet = document.createElement('div');
  sheet.className = 'comic-sheet';
  if (!comics?.length) sheet.innerHTML = '<p class="notice">TODAY\'S COMICS ARE UNAVAILABLE.</p>';
  const notUpdated = comics?.filter(comic => comic.status !== 'ok') ?? [];
  let availableIndex = 0;
  comics?.forEach(comic => {
    const item = document.createElement('article');
    const isWide = comic.images.length > 0 && availableIndex++ % 5 === 0;
    item.className = `comic ${comic.images.length ? 'comic--available' : 'comic--source'}${isWide ? ' comic--wide' : ''}`;
    item.innerHTML = `
      <header><h2><a href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(comic.name)}</a></h2><time>${escapeHtml(dateLabel(comic.published_date))}</time></header>
      ${comic.images.length ? `<div class="comic-images">${comic.images.map((src, index) => `<img loading="lazy" src="${escapeHtml(src)}" alt="${escapeHtml(comic.name)} comic for ${escapeHtml(dateLabel(comic.published_date))}${comic.images.length > 1 ? `, panel ${index + 1}` : ''}">`).join('')}</div>` : `<div class="comic-fallback"><p class="notice">NOT AVAILABLE IN THIS EDITION</p><p>Read today’s strip on ${escapeHtml(providerLabel(comic.provider))}.</p></div>`}
      <a class="source-link" href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">OPEN ON ${escapeHtml(providerLabel(comic.provider).toUpperCase())} ↗</a>`;
    sheet.append(item);
  });
  view.append(sheet);
  if (notUpdated.length) {
    const unavailable = document.createElement('section');
    unavailable.className = 'comic-updates-missing';
    unavailable.innerHTML = `<h2>Comics that didn’t update today</h2><p>These strips did not publish a fresh edition or could not be collected. Their source pages are linked below.</p><ul>${notUpdated.map(comic => `<li><a href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(comic.name)}</a>${comic.status === 'stale' ? ' <span>LAST AVAILABLE EDITION SHOWN</span>' : ''}</li>`).join('')}</ul>`;
    view.append(unavailable);
  }
  return view;
}
