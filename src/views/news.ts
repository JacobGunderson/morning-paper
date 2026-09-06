import type { NewsData } from '../types';
import { escapeHtml } from '../lib';

function sourceLink(publisher: string, url: string, prefix = 'OPEN'): string {
  return `<a class="source-link compact" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(prefix)} ${escapeHtml(publisher)} ↗</a>`;
}

export function renderNews(data: NewsData | null): HTMLElement {
  const view = document.createElement('section');
  view.className = 'view news-view';
  view.setAttribute('aria-labelledby', 'news-title');
  if (!data?.sections?.length) {
    view.innerHTML = '<h1 id="news-title" class="view-title">News</h1><p class="notice">TODAY\'S NEWS DATA IS UNAVAILABLE.</p>';
    return view;
  }
  const contents = data.sections.map(section => `
    <div class="news-toc-row">
      <button class="news-toc-major" type="button" data-news-target="section-${escapeHtml(section.id)}">${escapeHtml(section.title)}</button>
      <div class="news-toc-topics" aria-label="${escapeHtml(section.title)} topics">
        ${section.subsections.map(subsection => `<button type="button" data-news-target="topic-${escapeHtml(section.id)}-${escapeHtml(subsection.id)}">${escapeHtml(subsection.title)}</button>`).join('')}
      </div>
    </div>`).join('');
  view.innerHTML = `<header class="section-header"><span>01</span><h1 id="news-title">News</h1></header><nav class="news-toc" aria-label="News contents">${contents}</nav>` + data.sections.map((section, sectionIndex) => `
    <section class="news-section" aria-labelledby="section-${escapeHtml(section.id)}">
      <header class="section-header"><span>${String(sectionIndex + 1).padStart(2, '0')}</span><h1 id="section-${escapeHtml(section.id)}">${escapeHtml(section.title)}</h1></header>
      <div class="news-grid">
        ${section.subsections.map(subsection => `
          <article class="news-column" id="topic-${escapeHtml(section.id)}-${escapeHtml(subsection.id)}">
            <h2>${escapeHtml(subsection.title)}</h2>
            ${subsection.status === 'fallback' && subsection.source && subsection.active_source ? `
              <p class="source-note">${escapeHtml(subsection.source.publisher)} is unavailable. Showing ${escapeHtml(subsection.active_source.publisher)}.</p>
              ${sourceLink(subsection.source.publisher, subsection.source.url)}
            ` : ''}
            ${subsection.items.length ? `<ol>${subsection.items.map(item => `
              <li><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.headline)}</a><span>${escapeHtml(item.publisher)}</span></li>
            `).join('')}</ol>` : `<p class="notice">SOURCE CURRENTLY UNAVAILABLE</p>${subsection.source ? sourceLink(subsection.source.publisher, subsection.source.url) : ''}`}
          </article>`).join('')}
      </div>
    </section>`).join('');
  view.querySelectorAll<HTMLButtonElement>('[data-news-target]').forEach(button => {
    button.addEventListener('click', () => {
      document.getElementById(button.dataset.newsTarget ?? '')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  return view;
}
