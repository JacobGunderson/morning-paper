import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const games = JSON.parse(readFileSync(new URL('../generated/games/index.json', import.meta.url), 'utf8')) as {
  external: Array<{ id: string; provider: string }>;
};

describe('games edition', () => {
  it('embeds the daily mini crossword without retired publishers', () => {
    expect(games.external.map(game => game.id)).toContain('daily_mini_crossword');
    expect(games.external.map(game => game.provider)).not.toContain('latimes');
  });
});
