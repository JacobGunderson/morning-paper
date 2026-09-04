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
  try {
    const edition = new Date(`${editionDate}T12:00:00Z`);
    for (let offset = 0; offset < 8; offset += 1) {
      const candidate = new Date(edition);
      candidate.setUTCDate(candidate.getUTCDate() - offset);
      const pageUrl = datedUrl(source.slug, candidate);
      try {
        const response = await page.goto(pageUrl, { waitUntil: 'domcontentloaded', timeout: 30_000 });
        if (!response?.ok()) continue;
        const label = longDate(candidate);
        const image = page.locator(`main img[alt$="for ${label}"]`).first();
        await image.waitFor({ state: 'attached', timeout: 12_000 });
        const imageUrl = await image.evaluate(node => node.currentSrc || node.src);
        if (!imageUrl || !imageUrl.startsWith('https://')) continue;
        const asset = await context.request.get(imageUrl, { headers: { referer: pageUrl }, timeout: 30_000 });
        if (!asset.ok()) continue;
        const bytes = await asset.body();
        const kind = imageKind(bytes);
        if (!kind || bytes.length < 4_000) continue;
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
      } catch {
        // A missing edition is normal for archived and non-daily strips.
      }
    }
    return {
      id: source.id, name: source.title, provider: source.provider,
      published_date: null, source_url: source.base_url, images: [],
      status: 'unavailable', detail: 'No rendered strip found in the 8-day window',
    };
  } finally {
    await page.close();
  }
}

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const results = new Array(sources.length);
  let next = 0;
  async function worker() {
    while (next < sources.length) {
      const index = next++;
      results[index] = await collectOne(context, sources[index]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, sources.length) }, worker));
  process.stdout.write(JSON.stringify(results));
} finally {
  await browser.close();
}
