import { describe, expect, it } from 'vitest';
import { adjacent, cellsBetween, evaluateConnection, scoreWordle, traceWord, validPath } from '../src/games/logic';

describe('Wordle scoring', () => {
  it('does not credit a repeated letter more times than it appears', () => {
    expect(scoreWordle('allee', 'apple')).toEqual(['correct', 'present', 'absent', 'absent', 'correct']);
  });
  it('scores exact letters before present letters', () => {
    expect(scoreWordle('esses', 'seeds')).toEqual(['present', 'present', 'absent', 'present', 'correct']);
  });
});

describe('Connections', () => {
  const groups = [
    { level: 0, category: 'COLORS', members: ['RED', 'BLUE', 'GREEN', 'BLACK'] },
    { level: 1, category: 'BIRDS', members: ['TERN', 'CROW', 'WREN', 'DOVE'] },
  ];
  it('finds a correct group', () => expect(evaluateConnection(['RED', 'BLUE', 'GREEN', 'BLACK'], groups).group?.category).toBe('COLORS'));
  it('reports one away', () => expect(evaluateConnection(['RED', 'BLUE', 'GREEN', 'CROW'], groups).oneAway).toBe(true));
  it('rejects unrelated guesses', () => expect(evaluateConnection(['RED', 'BLUE', 'CROW', 'DOVE'], groups)).toEqual({ group: undefined, oneAway: false }));
});

describe('Strands paths', () => {
  it('accepts horizontal, vertical, and diagonal adjacency', () => {
    expect(adjacent([0, 0], [0, 1])).toBe(true);
    expect(adjacent([0, 0], [1, 0])).toBe(true);
    expect(adjacent([0, 0], [1, 1])).toBe(true);
  });
  it('rejects jumps and cell reuse', () => {
    expect(validPath([[0, 0], [0, 2]])).toBe(false);
    expect(validPath([[0, 0], [1, 1], [0, 0]])).toBe(false);
  });
  it('supports a valid backtracked path and word detection', () => {
    const grid = ['ABCDEF', 'GHIJKL', 'MNOPQR', 'STUVWX', 'YZABCD', 'EFGHIJ', 'KLMNOP', 'QRSTUV'];
    const path: Array<[number, number]> = [[0, 0], [0, 1], [1, 1], [1, 0]];
    expect(validPath(path)).toBe(true);
    expect(traceWord(grid, path)).toBe('ABHG');
  });
  it('fills cells crossed by a fast straight pointer movement', () => {
    expect(cellsBetween([3, 0], [3, 5])).toEqual([[3, 1], [3, 2], [3, 3], [3, 4], [3, 5]]);
    expect(cellsBetween([0, 0], [2, 1])).toEqual([]);
  });
});
