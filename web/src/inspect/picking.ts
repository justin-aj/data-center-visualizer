import { Vector2, type Camera, type Object3D, type Raycaster } from 'three';

function featureIdForObject(object: Object3D): string | null {
  let current: Object3D | null = object;
  while (current) {
    const featureId = current.userData['featureId'];
    if (typeof featureId === 'string') return featureId;
    current = current.parent;
  }
  return null;
}

export function pickFeatureId(
  raycaster: Raycaster,
  camera: Camera,
  root: Object3D,
  normalizedPointer: { x: number; y: number },
): string | null {
  raycaster.setFromCamera(
    new Vector2(normalizedPointer.x, normalizedPointer.y),
    camera,
  );
  const intersections = raycaster.intersectObject(root, true);
  for (const intersection of intersections) {
    const featureId = featureIdForObject(intersection.object);
    if (featureId) return featureId;
  }
  return null;
}
