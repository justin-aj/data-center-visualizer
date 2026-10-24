export interface SceneKeyboardActions {
  orbit: (horizontal: number, vertical: number) => void;
  zoom: (direction: number) => void;
  nextViewpoint: () => void;
  previousViewpoint: () => void;
}

export function bindSceneKeyboard(actions: SceneKeyboardActions): () => void {
  const onKeyDown = (event: KeyboardEvent): void => {
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLButtonElement
    )
      return;
    const action = new Map<string, () => void>([
      ['ArrowLeft', () => actions.orbit(-1, 0)],
      ['ArrowRight', () => actions.orbit(1, 0)],
      ['ArrowUp', () => actions.orbit(0, -1)],
      ['ArrowDown', () => actions.orbit(0, 1)],
      ['+', () => actions.zoom(-1)],
      ['=', () => actions.zoom(-1)],
      ['-', () => actions.zoom(1)],
      [']', actions.nextViewpoint],
      ['[', actions.previousViewpoint],
    ]).get(event.key);
    if (!action) return;
    event.preventDefault();
    action();
  };
  window.addEventListener('keydown', onKeyDown);
  return () => window.removeEventListener('keydown', onKeyDown);
}
