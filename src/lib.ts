export const escapeHtml = (value: string) => value.replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[c]!);

export async function loadJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(String(response.status));
    return await response.json() as T;
  } catch {
    return null;
  }
}

export function formatEdition(date: string): string {
  const parsed = new Date(`${date}T12:00:00`);
  return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/Denver' })
    .format(parsed).replace(/, /g, ' / ').toUpperCase();
}

export function button(label: string, className = ''): HTMLButtonElement {
  const element = document.createElement('button');
  element.type = 'button';
  element.className = className;
  element.textContent = label;
  return element;
}
