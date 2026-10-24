import {
  LineSegments,
  Mesh,
  Sprite,
  type Material,
  type Object3D,
  type Texture,
} from 'three';

import type { DetailLevel } from '../scene/textures';

interface SavedMaterialDetail {
  map: Texture | null;
}

function materials(mesh: Mesh): Material[] {
  return Array.isArray(mesh.material) ? mesh.material : [mesh.material];
}

export function applyDetailLevel(root: Object3D, level: DetailLevel): void {
  root.traverse((object) => {
    if (object instanceof Mesh) {
      object.castShadow =
        level === 'full' && object.userData['shadowConfidence'] !== 'none';
      for (const material of materials(object)) {
        if (!('map' in material)) continue;
        const mapped = material as Material & {
          map: Texture | null;
          needsUpdate: boolean;
        };
        const saved = material.userData['fullDetail'] as
          SavedMaterialDetail | undefined;
        if (!saved) material.userData['fullDetail'] = { map: mapped.map };
        mapped.map = level === 'full' ? (saved?.map ?? mapped.map) : null;
        mapped.needsUpdate = true;
      }
    }
    if (object instanceof LineSegments || object instanceof Sprite) {
      object.visible = true;
    }
  });
}

export function createDetailToggle(
  root: Object3D,
  initial: DetailLevel = 'full',
): HTMLLabelElement {
  const label = document.createElement('label');
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = initial === 'reduced';
  checkbox.addEventListener('change', () => {
    applyDetailLevel(root, checkbox.checked ? 'reduced' : 'full');
  });
  label.append(checkbox, ' Reduced detail');
  applyDetailLevel(root, initial);
  return label;
}
