import {
  WebGLRenderTarget,
  type Camera,
  type Scene,
  type WebGLRenderer,
} from 'three';

import { renderComparison } from '../compare/renderer';
import type { ComparisonMode } from '../state';

export interface ExportOverlay {
  title: string;
  version: string;
  date: string;
  mode: ComparisonMode;
  viewpoint: string;
  legend: string;
  attribution: string[];
  confidence: string;
  url: string;
}

export interface PngExportOptions {
  width: number;
  height: number;
  overlay: ExportOverlay;
}

export function overlayLines(overlay: ExportOverlay): string[] {
  return [
    `${overlay.title} — ${overlay.version}`,
    `${overlay.date} — ${overlay.mode} — ${overlay.viewpoint}`,
    overlay.legend,
    `Confidence: ${overlay.confidence}`,
    ...overlay.attribution,
    overlay.url,
  ];
}

function canvasBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('PNG export failed. Try a smaller image.'));
    }, 'image/png');
  });
}

export async function renderPng(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: Camera,
  options: PngExportOptions,
): Promise<Blob> {
  await document.fonts.ready;
  const width = Math.min(2_400, Math.max(1, Math.floor(options.width)));
  const height = Math.min(1_600, Math.max(1, Math.floor(options.height)));
  const target = new WebGLRenderTarget(width, height);
  const previousTarget = renderer.getRenderTarget();
  const pixels = new Uint8Array(width * height * 4);

  try {
    renderer.setRenderTarget(target);
    renderComparison(
      renderer,
      scene,
      camera,
      options.overlay.mode,
      width,
      height,
    );
    renderer.readRenderTargetPixels(target, 0, 0, width, height, pixels);
  } finally {
    renderer.setRenderTarget(previousTarget);
    target.dispose();
  }

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('PNG canvas is unavailable.');
  const image = context.createImageData(width, height);
  for (let row = 0; row < height; row += 1) {
    const source = (height - row - 1) * width * 4;
    image.data.set(
      pixels.subarray(source, source + width * 4),
      row * width * 4,
    );
  }
  context.putImageData(image, 0, 0);

  const lines = overlayLines(options.overlay);
  const fontSize = Math.max(15, Math.round(width / 90));
  const lineHeight = Math.round(fontSize * 1.35);
  const padding = lineHeight;
  const boxHeight = padding * 2 + lines.length * lineHeight;
  context.fillStyle = 'rgba(247,243,234,0.94)';
  context.fillRect(0, height - boxHeight, width, boxHeight);
  context.fillStyle = '#1e2a31';
  context.font = `${fontSize}px system-ui, sans-serif`;
  lines.forEach((line, index) => {
    context.fillText(
      line,
      padding,
      height - boxHeight + padding + lineHeight * (index + 1),
    );
  });
  canvas.dataset['overlay'] = lines.join(' | ');
  return canvasBlob(canvas);
}

export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
