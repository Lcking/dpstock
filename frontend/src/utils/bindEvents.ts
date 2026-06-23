/** Global event so all pages refresh assets after email bind (e.g. NavBar bind while on /watchlist). */
export const BIND_SUCCESS_EVENT = 'aguai:bind-success';

export function emitBindSuccess(detail?: unknown): void {
  window.dispatchEvent(new CustomEvent(BIND_SUCCESS_EVENT, { detail }));
}

export function onBindSuccess(handler: (event: Event) => void): () => void {
  window.addEventListener(BIND_SUCCESS_EVENT, handler);
  return () => window.removeEventListener(BIND_SUCCESS_EVENT, handler);
}
