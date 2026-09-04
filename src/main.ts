import './styles.css';
import type { Comic, ConnectionsData, GamesData, Manifest, NewsData, StrandsData, WordleData } from './types';
import { formatEdition, loadJson } from './lib';
import { renderNews } from './views/news';
import { renderFunnies } from './views/funnies';
import { renderGames } from './views/games';

type Route = 'news' | 'commentary' | 'funnies' | 'games';
const routes: Route[] = ['news', 'commentary', 'funnies', 'games'];
const routeNumber: Record<Route, string> = { news: '01', commentary: '02', funnies: '03', games: '04' };

async function boot() {
  const [site, manifest, news, comics, games, wordle, connections, strands] = await Promise.all([
    loadJson<{ site?: { title?: string; timezone?: string } }>('./site.json'), loadJson<Manifest>('./manifest.json'), loadJson<NewsData>('./news.json'), loadJson<Comic[]>('./comics.json'), loadJson<GamesData>('./games/index.json'),
    loadJson<WordleData>('./games/wordle.json'), loadJson<ConnectionsData>('./games/connections.json'), loadJson<StrandsData>('./games/strands.json')
  ]);
  const today = manifest?.edition_date ?? new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Denver' }).format(new Date());
  const updated = manifest?.build_time ? new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Denver' }).format(new Date(manifest.build_time)) : '—';
  const siteTitle = site?.site?.title ?? 'MORNING PAPER';
  document.title = siteTitle.replace(/\b\w/g, letter => letter.toUpperCase());
  document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
    <header class="masthead">
      <div class="masthead-kicker">PERSONAL DAILY / NO. ${today.replaceAll('-', '')}</div>
      <h1>${siteTitle}</h1>
      <div class="edition"><time datetime="${today}">${formatEdition(today)}</time><span>UPDATED ${updated} MT</span></div>
    </header>
    <nav class="primary-nav" aria-label="Primary">${routes.map(route => `<a href="#${route}" data-route="${route}"><span>${routeNumber[route]}</span>${route}</a>`).join('')}</nav>
    <main id="content" tabindex="-1"></main>
    <footer><span>STATIC EDITION / AMERICA—DENVER</span><span>${manifest ? `${manifest.news.success} NEWS SOURCES · ${manifest.comics.success} COMICS · ${manifest.games.success} GAMES` : 'BUILD STATUS UNAVAILABLE'}</span></footer>`;
  const content = document.querySelector<HTMLElement>('#content')!;
  const render = () => {
    const requested = location.hash.slice(1) as Route; const route: Route = routes.includes(requested) ? requested : 'news';
    if (location.hash !== `#${route}`) history.replaceState(null, '', `#${route}`);
    document.querySelectorAll('.primary-nav a').forEach(link => link.toggleAttribute('aria-current', (link as HTMLAnchorElement).dataset.route === route));
    if (route === 'news') content.replaceChildren(renderNews(news));
    else if (route === 'funnies') content.replaceChildren(renderFunnies(comics));
    else if (route === 'games') content.replaceChildren(renderGames({ games, wordle, connections, strands }));
    else { const view = document.createElement('section'); view.className = 'view empty-view'; view.innerHTML = '<div class="section-header"><span>02</span><h1>Commentary</h1></div><p class="notice">NO COMMENTARY SOURCES CONFIGURED</p>'; content.replaceChildren(view); }
    window.scrollTo({ top: 0 });
  };
  window.addEventListener('hashchange', render); render();
}

void boot();
