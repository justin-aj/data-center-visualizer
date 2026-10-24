export const CONTEXT_LOSS_MESSAGE =
  'The 3D view paused. Reload the scene, then retry the PNG export.';

export function watchContextLoss(
  canvas: HTMLCanvasElement,
  showMessage: (message: string) => void,
): () => void {
  const onLost = (event: Event): void => {
    event.preventDefault();
    showMessage(CONTEXT_LOSS_MESSAGE);
  };
  canvas.addEventListener('webglcontextlost', onLost);
  return () => canvas.removeEventListener('webglcontextlost', onLost);
}
