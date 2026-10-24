import type { Manifest, Proposal } from '../data/types';
import { createInventoryTable } from '../inventory/table';

export const SIMPLE_GEOMETRY_FALLBACK_NOTE =
  'Detailed GLB assets are not loaded. Future asset failures must use extruded geometry.';

export function webGlAvailable(): boolean {
  const canvas = document.createElement('canvas');
  return Boolean(
    canvas.getContext('webgl2') ||
    canvas.getContext('webgl') ||
    canvas.getContext('experimental-webgl'),
  );
}

export function createNoWebGlFallback(
  manifest: Manifest,
  proposal: Proposal,
): HTMLElement {
  const section = document.createElement('section');
  section.dataset['fallback'] = 'no-webgl';
  const heading = document.createElement('h2');
  heading.textContent = 'Static scene';
  const message = document.createElement('p');
  message.textContent =
    '3D graphics are unavailable. This image shows the bundled pilot view.';
  const image = document.createElement('img');
  image.src = '/fallback/synthetic-site.png';
  image.alt = `${manifest.title}, proposed aerial view. ${manifest.attribution.join(' ')}`;
  image.style.cssText = 'display:block;width:100%;height:auto';
  section.append(
    heading,
    message,
    image,
    createInventoryTable(proposal, manifest),
  );
  return section;
}

export function contextMissingMessage(): HTMLElement {
  const message = document.createElement('p');
  message.dataset['fallback'] = 'context-missing';
  message.textContent =
    'Neighborhood context is unavailable. Proposal geometry uses a labeled flat ground plane.';
  return message;
}
