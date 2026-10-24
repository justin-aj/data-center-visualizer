import type { Camera, Scene, WebGLRenderer } from 'three';

import type { ComparisonMode } from '../state';
import { CONTEXT_LAYER, CURRENT_LAYER, PROPOSED_LAYER } from './membership';

function setCameraLayers(camera: Camera, featureLayer: number): void {
  camera.layers.disableAll();
  camera.layers.enable(CONTEXT_LAYER);
  camera.layers.enable(featureLayer);
}

function renderSide(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: Camera,
  featureLayer: number,
  left: number,
  width: number,
  height: number,
): void {
  setCameraLayers(camera, featureLayer);
  renderer.setViewport(left, 0, width, height);
  renderer.setScissor(left, 0, width, height);
  renderer.render(scene, camera);
}

export function renderComparison(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: Camera,
  mode: ComparisonMode,
  width: number,
  height: number,
): void {
  const safeWidth = Math.max(1, Math.floor(width));
  const safeHeight = Math.max(1, Math.floor(height));
  renderer.setScissorTest(mode === 'split');

  if (mode === 'split') {
    const leftWidth = Math.floor(safeWidth / 2);
    const rightWidth = safeWidth - leftWidth;
    renderSide(
      renderer,
      scene,
      camera,
      CURRENT_LAYER,
      0,
      leftWidth,
      safeHeight,
    );
    renderSide(
      renderer,
      scene,
      camera,
      PROPOSED_LAYER,
      leftWidth,
      rightWidth,
      safeHeight,
    );
  } else {
    const layer = mode === 'current' ? CURRENT_LAYER : PROPOSED_LAYER;
    renderSide(renderer, scene, camera, layer, 0, safeWidth, safeHeight);
  }

  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, safeWidth, safeHeight);
}
