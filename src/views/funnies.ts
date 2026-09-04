import type { Comic } from '../types';
import { escapeHtml } from '../lib';

function dateLabel(value?: string | null): string {
  if (!value) return 'DATE UNAVAILABLE';
  return new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`));
}

export function renderFunnies(comics: Comic[] | null): HTMLElement {
  const view = document.createElement('section');
  view.className = 'view funnies-view';
  view.innerHTML = '<div class="section-header"><span>03</span><h1>Funnies</h1></div>';
  const stream = document.createElement('div');
  stream.className = 'comic-stream';
  if (!comics?.length) stream.innerHTML = '<p class="notice">TODAY\'S COMICS ARE UNAVAILABLE.</p>';
  comics?.forEach(comic => {
    const item = document.createElement('article');
    item.className = 'comic';
    item.innerHTML = `
      <header><h2><a href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(comic.name)}</a></h2><time>${escapeHtml(dateLabel(comic.published_date))}</time></header>
      ${comic.images.length ? `<div class="comic-images">${comic.images.map((src, index) => `<img loading="lazy" src="${escapeHtml(src)}" alt="${escapeHtml(comic.name)} comic for ${escapeHtml(dateLabel(comic.published_date))}${comic.images.length > 1 ? `, panel ${index + 1}` : ''}">`).join('')}</div>` : '<p class="notice">COMIC UNAVAILABLE</p>'}
      <a class="source-link" href="${escapeHtml(comic.source_url)}" target="_blank" rel="noopener noreferrer">SOURCE ↗</a>`;
    stream.append(item);
  });
  view.append(stream);
  return view;
}
