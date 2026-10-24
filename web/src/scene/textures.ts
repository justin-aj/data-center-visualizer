import {
  CanvasTexture,
  LineBasicMaterial,
  LineDashedMaterial,
  RepeatWrapping,
  Sprite,
  SpriteMaterial,
  SRGBColorSpace,
  type Texture,
} from 'three';

import { sceneStyle } from './style';

export type DetailLevel = 'full' | 'reduced';

export function createHatchTexture(): Texture {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas textures are unavailable.');

  context.fillStyle = '#d8d2ca';
  context.fillRect(0, 0, 32, 32);
  context.strokeStyle = sceneStyle.proposalOutline;
  context.lineWidth = 4;
  context.beginPath();
  context.moveTo(-8, 32);
  context.lineTo(32, -8);
  context.moveTo(8, 40);
  context.lineTo(40, 8);
  context.stroke();

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  texture.repeat.set(2, 2);
  return texture;
}

export function outlineMaterial(
  estimated: boolean,
): LineBasicMaterial | LineDashedMaterial {
  if (estimated) {
    return new LineDashedMaterial({
      color: sceneStyle.proposalOutline,
      dashSize: 1.3,
      gapSize: 0.9,
    });
  }
  return new LineBasicMaterial({ color: sceneStyle.proposalOutline });
}

export function createStatusSprite(text: string): Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 768;
  canvas.height = 112;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas labels are unavailable.');

  context.fillStyle = sceneStyle.uiSurface;
  context.strokeStyle = sceneStyle.uiText;
  context.lineWidth = 6;
  context.fillRect(3, 3, 762, 106);
  context.strokeRect(3, 3, 762, 106);
  context.fillStyle = sceneStyle.uiText;
  context.font = '700 36px system-ui, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text.toUpperCase(), 384, 58, 730);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  const sprite = new Sprite(
    new SpriteMaterial({ map: texture, depthTest: false, depthWrite: false }),
  );
  sprite.scale.set(46, 6.7, 1);
  sprite.renderOrder = 10;
  sprite.userData['statusText'] = text;
  return sprite;
}
