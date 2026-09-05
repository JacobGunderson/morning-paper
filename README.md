# Morning Paper

A static, responsive personal newspaper. A scheduled GitHub Action collects headlines, downloads the latest available comic images, resolves game embeds and normalizes daily puzzle data; Vite then publishes plain HTML, CSS, JavaScript, JSON, and images to GitHub Pages. Nothing runs on a server when a reader opens the edition.

## Local development

Python 3.12 and Node.js 22 are the versions used by CI.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run comics:browser
npm run refresh:local
npm run preview
```

Open the URL Vite prints (normally `http://127.0.0.1:4173`). Hash routes are `#news`, `#commentary`, `#funnies`, and `#games`. Use `npm run dev` instead of `npm run preview` when actively editing frontend code.

`npm run comics:browser` opens a separate Chrome profile stored in `work/gocomics-chrome`. Keep that window open while refreshing. If GoComics asks for a sign-in, sign in once in that dedicated window; do not use the profile for unrelated browsing. `npm run refresh:local` attaches to that ordinary browser session, visits the configured dated pages in two working tabs, caches the displayed strips into `generated/comics/`, and creates a fresh production build. Chrome's debugging connection is local to this machine. When the command finishes and Vite reports `built in`, reload the preview page. If the preview server is already running, do not start a second copy.

Run the full unit suite and make a production build with:

```bash
npm test
npm run build
```

The optional browser suite covers the required 390×844 and 1440×900 viewports. Install Chromium once, then run it:

```bash
npx playwright install chromium
npm run test:e2e
```

## How the edition is built

`scripts/refresh.py` is the orchestration entry point. It independently collects every configured source, records source status, validates the normalized data, and writes the static inputs in `generated/`. A failure from one publisher becomes an `unavailable` or `error` entry and does not stop unrelated sources. Validation runs before any Pages artifact is uploaded, so a bad new edition cannot replace the previous successful deployment.

The collectors use simple HTTP first, JSON-LD and semantic markup before fallback selectors, 20-second timeouts, three attempts, and exponential backoff. GoComics is the exception: its local collector attaches to a dedicated ordinary Chrome session, then caches the strip displayed on each dated page. A fresh Playwright browser remains the unattended-build fallback, but a publisher can decline that automated session. The collectors do not fetch article bodies or make readers' browsers contact news/comic publishers. The current comic build begins with an empty comic output directory, so it does not become a permanent archive.

Adapters are isolated by provider:

- `scripts/news/ap.py` and `scripts/news/politico.py`
- `scripts/comics/gocomics.py`, `comics_kingdom.py`, `farside.py`, and `xkcd.py`
- `scripts/games/nyt.py`, `latimes.py`, and `circle9.py`

If a publisher changes markup or an endpoint, adjust only that adapter and its fixture test where possible.

## Configuration

All editable source definitions live in `config/`.

### Rename the paper or change timezone

Edit `config/site.yaml`. The refresh step emits `generated/site.json`, which the frontend reads. Date and update-time formatting use `America/Denver` by default.

### Add a news source

Add an item beneath a section in `config/news.yaml`. Required fields are `id`, `publisher`, `adapter`, `subsection`, `title`, `url`, `limit`, and `specificity`. A high specificity value claims duplicate stories before a low-specificity catch-all. The collector scans up to 30 candidates and fills each subsection with as many unique results as possible, up to its configured limit.

News deduplication is global. Canonical URL equality wins first; a strongly normalized same-publisher headline match is the secondary rule. Different publishers covering the same event remain separate unless their canonical URL is literally identical.

A source may declare `fallback: another_source_id`; the fallback source should declare `fallback_for: primary_source_id`. The fallback is collected normally but rendered only when the primary has no usable items. The Technology column uses AP Technology when Politico declines the scheduled request and keeps a direct link to Politico.

### Add a comic

Add exactly one entry to `config/comics.yaml` with `id`, `title`, `provider`, `slug`, and `base_url`. GoComics and Comics Kingdom dated URLs are generated at collection time. Each adapter tries the edition date and up to seven prior days, records the strip's actual publication date, and supports multiple downloaded images. Display sorting ignores a leading “The.”

### Add an external game

Add an item to `config/games.yaml` with `id`, `title`, `provider`, and `url`. Circle9 items can include an `embed_url`; the collector checks current framing headers and removes the embed if framing is denied. L.A. Times pages are inspected daily for their current isolated Amuse Labs/PuzzleMe player. When no permitted player can be resolved, the site shows the original-page link.

NYT puzzle endpoint knowledge is confined to `scripts/games/nyt.py`. The frontend only consumes project-specific normalized JSON. Strands answer paths are derived at build time with DFS and a global non-overlapping assignment.

### Change the schedule

Edit the cron value in `.github/workflows/daily.yml`. GitHub schedules use UTC and do not observe daylight saving time. The default `12:34 UTC` corresponds to `05:34 MST` and `06:34 MDT`, close to the requested morning window and deliberately away from the top of the hour.

## GitHub Pages setup

1. Push this repository to GitHub.
2. In **Settings → Pages**, set **Source** to **GitHub Actions**.
3. In **Settings → Actions → General**, allow workflows to read repository contents and ensure Pages deployment is permitted. The workflow requests only `contents: read`, `pages: write`, and `id-token: write`.
4. Open **Actions → Build morning edition → Run workflow** for the first manual edition.

Collection, validation, tests, and the Vite build all finish before `actions/deploy-pages` runs. Failures and per-source diagnostics appear in that workflow's logs and in `generated/manifest.json`; raw exceptions are never shown on the public page.

For a custom domain, add it in **Settings → Pages → Custom domain** and follow GitHub's displayed DNS instructions. GitHub manages the domain verification and HTTPS certificate. The relative Vite asset base works for both project Pages and custom domains.

## Runtime behavior and limitations

- The three local NYT-style games use official daily data when its date-addressable endpoint is reachable. Answers are present in static JSON by design, but never revealed in normal play except Wordle after six misses.
- Browser progress is deliberately limited to the selected game. There is no login, analytics, advertising, or cross-device synchronization.
- Third-party publishers can change markup, endpoints, framing policy, or automated-access policy at any time. The corresponding adapter then records a failure and the public edition retains an original-source link.
- The L.A. Times recently serves a first-party game experience on its page. The resolver still looks for an isolated PuzzleMe/Amuse Labs iframe and will use a link fallback when none is publicly exposed or embeddable.
- Circle9 URLs do not need the example `v=414` query parameter; configuration uses their stable paths.

## Repository map

```text
config/       editable site and source definitions
scripts/      collectors, normalization, validation
generated/    the current static edition consumed by Vite
src/          vanilla TypeScript views and game interfaces
tests/        Python, TypeScript, and Playwright tests
.github/      scheduled/manual Pages workflow
```
