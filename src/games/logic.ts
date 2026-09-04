import type { ConnectionsGroup } from '../types';

export type TileState = 'correct' | 'present' | 'absent';

export function scoreWordle(guess: string, solution: string): TileState[] {
  const result: TileState[] = Array(5).fill('absent');
  const remaining = new Map<string, number>();
  for (let i = 0; i < 5; i += 1) {
    if (guess[i] === solution[i]) result[i] = 'correct';
    else remaining.set(solution[i], (remaining.get(solution[i]) ?? 0) + 1);
  }
  for (let i = 0; i < 5; i += 1) {
    if (result[i] === 'correct') continue;
    const count = remaining.get(guess[i]) ?? 0;
    if (count > 0) {
      result[i] = 'present';
      remaining.set(guess[i], count - 1);
    }
  }
  return result;
}

export function evaluateConnection(selected: string[], groups: ConnectionsGroup[]): { group?: ConnectionsGroup; oneAway: boolean } {
  const chosen = new Set(selected);
  const group = groups.find(candidate => candidate.members.every(member => chosen.has(member)));
  const oneAway = !group && groups.some(candidate => candidate.members.filter(member => chosen.has(member)).length === 3);
  return { group, oneAway };
}

export const adjacent = (a: [number, number], b: [number, number]) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])) === 1;

export function cellsBetween(a: [number, number], b: [number, number]): Array<[number, number]> {
  const rowDelta = b[0] - a[0]; const columnDelta = b[1] - a[1];
  const steps = Math.max(Math.abs(rowDelta), Math.abs(columnDelta));
  const straight = rowDelta === 0 || columnDelta === 0 || Math.abs(rowDelta) === Math.abs(columnDelta);
  if (!straight || steps === 0) return [];
  return Array.from({ length: steps }, (_, index) => [a[0] + Math.sign(rowDelta) * (index + 1), a[1] + Math.sign(columnDelta) * (index + 1)]);
}

export function validPath(path: Array<[number, number]>, rows = 8, columns = 6): boolean {
  const seen = new Set<string>();
  return path.every((cell, index) => {
    const key = cell.join(',');
    const valid = cell[0] >= 0 && cell[0] < rows && cell[1] >= 0 && cell[1] < columns && !seen.has(key) && (index === 0 || adjacent(path[index - 1], cell));
    seen.add(key);
    return valid;
  });
}

export function traceWord(grid: string[], path: Array<[number, number]>): string {
  return path.map(([row, column]) => grid[row]?.[column] ?? '').join('');
}
