import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

const [editionDate, outputDir] = process.argv.slice(2);
const input = await new Promise((resolve, reject) => {
  let value = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => { value += chunk; });
  process.stdin.on('end', () => resolve(value));
  process.stdin.on('error', reject);
});
const sources = JSON.parse(input);

function progress(message) {
  process.stderr.write(`[GoComics] ${message}\n`);
}

async function localChromeExecutable() {
  const configured = process.env.MORNING_PAPER_CHROME;
  const macosChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  for (const candidate of [configured, process.platform === 'darwin' ? macosChrome : undefined]) {
    if (!candidate) continue;
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // Keep Playwright's bundled Chromium as the cross-platform fallback.
    }
  }
  return undefined;
}

function datedUrl(slug, value) {
  const [year, month, day] = value.toISOString().slice(0, 10).split('-');
  return `https://www.gocomics.com/${slug}/${year}/${month}/${day}`;
}

function longDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  }).format(value);
}

function imageKind(bytes) {
  if (bytes.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff]))) return ['jpg', 'image/jpeg'];
  if (bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return ['png', 'image/png'];
  if (bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP') return ['webp', 'image/webp'];
  if (['GIF87a', 'GIF89a'].includes(bytes.subarray(0, 6).toString())) return ['gif', 'image/gif'];
  return null;
}

async function collectOne(context, source) {
  const page = await context.newPage();
  progress(`${source.title}: starting`);
  try {
    const edition = new Date(`${editionDate}T12:00:00Z`);
    let currentEditionDetail = '';
    for (let offset = 0; offset < 8; offset += 1) {
      const candidate = new Date(edition);
      candidate.setUTCDate(candidate.getUTCDate() - offset);
      const pageUrl = datedUrl(source.slug, candidate);
      try {
        const response = await page.goto(pageUrl, { waitUntil: 'domcontentloaded', timeout: 15_000 });
        if (!response?.ok()) {
          if (offset === 0) currentEditionDetail = `Current page returned HTTP ${response?.status() ?? 'unknown'}`;
          continue;
        }
        const label = longDate(candidate);
        const image = page.locator(`img[alt$="for ${label}"]`).first();
        await image.waitFor({ state: 'attached', timeout: 5_000 });
        const imageUrl = await image.evaluate(node => node.currentSrc || node.src);
        if (!imageUrl || !imageUrl.startsWith('https://')) {
          if (offset === 0) currentEditionDetail = 'Current page did not expose a strip image URL';
          continue;
        }
        // Fetch through the attached Chrome tab as well. This keeps both the page
        // request and the asset request in the ordinary browser network session.
        const asset = await page.goto(imageUrl, {
          waitUntil: 'commit', timeout: 15_000, referer: pageUrl,
        });
        if (!asset?.ok()) {
          if (offset === 0) currentEditionDetail = `Current strip image returned HTTP ${asset?.status() ?? 'unknown'}`;
          continue;
        }
        const bytes = await asset.body();
        const kind = imageKind(bytes);
        if (!kind || bytes.length < 4_000) {
          if (offset === 0) currentEditionDetail = 'Current strip response was not a valid image';
          continue;
        }
        const digest = crypto.createHash('sha256').update(bytes).digest('hex').slice(0, 10);
        const filename = `${source.id}-1-${digest}.${kind[0]}`;
        await fs.writeFile(path.join(outputDir, filename), bytes);
        return {
          id: source.id,
          name: source.title,
          provider: source.provider,
          published_date: candidate.toISOString().slice(0, 10),
          source_url: pageUrl,
          images: [`comics/${filename}`],
          status: offset === 0 ? 'ok' : 'stale',
          detail: '',
        };
      } catch (error) {
        if (offset === 0) {
          const message = error instanceof Error ? error.message.split('\n')[0] : String(error);
          currentEditionDetail = `Current page: ${message}`;
        }
        // A missing edition is normal for archived and non-daily strips.
      }
    }
    return {
      id: source.id, name: source.title, provider: source.provider,
      published_date: null, source_url: source.base_url, images: [],
      status: 'unavailable',
      detail: currentEditionDetail || 'No rendered strip found in the 8-day window',
    };
  } finally {
    await page.close();
  }
}

await fs.mkdir(outputDir, { recursive: true });
const cdpUrl = process.env.MORNING_PAPER_CDP_URL;
let browser;
let context;

if (cdpUrl) {
  progress(`Connecting to the dedicated Chrome session at ${cdpUrl}`);
  let lastConnectionError;
  for (let attempt = 0; attempt < 20 && !browser; attempt += 1) {
    try {
      browser = await chromium.connectOverCDP(cdpUrl, { timeout: 1_000 });
    } catch (error) {
      lastConnectionError = error;
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
  if (!browser) {
    const message = lastConnectionError instanceof Error
      ? lastConnectionError.message.split('\n')[0]
      : String(lastConnectionError);
    throw new Error(`Could not connect to the GoComics browser. Run "npm run comics:browser" first. ${message}`);
  }
  [context] = browser.contexts();
  if (!context) throw new Error('The connected GoComics browser has no usable browser context.');
} else {
  const executablePath = await localChromeExecutable();
  const headless = executablePath ? process.env.MORNING_PAPER_HEADLESS === '1' : true;
  progress(`Launching ${headless ? 'headless' : 'visible'} Chrome`);
  browser = await chromium.launch({ headless, ...(executablePath ? { executablePath } : {}) });
  context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
}

try {
  const results = new Array(sources.length);
  let next = 0;
  async function worker() {
    while (next < sources.length) {
      const index = next++;
      results[index] = await collectOne(context, sources[index]);
      const detail = results[index].detail ? ` (${results[index].detail})` : '';
      progress(`${sources[index].title}: ${results[index].status}${detail}`);
    }
  }
  const defaultWorkers = cdpUrl ? 2 : 4;
  const configuredWorkers = Number.parseInt(process.env.MORNING_PAPER_COMIC_WORKERS || '', 10);
  const workerCount = Number.isFinite(configuredWorkers) && configuredWorkers > 0
    ? configuredWorkers
    : defaultWorkers;
  await Promise.all(Array.from({ length: Math.min(workerCount, sources.length) }, worker));
  process.stdout.write(JSON.stringify(results));
} finally {
  // For a launched browser this closes Chrome; for a connected browser Playwright
  // only disconnects and leaves the dedicated Chrome window/profile running.
  await browser.close();
}
