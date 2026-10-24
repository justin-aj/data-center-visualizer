export type DataState =
  'loading' | 'ready' | 'unavailable' | 'unknown' | 'estimated' | 'error';

export function showDataState(
  target: HTMLElement,
  state: DataState,
  message: string,
): void {
  target.dataset['state'] = state;
  target.textContent = message;
  target.setAttribute('role', state === 'error' ? 'alert' : 'status');
}
