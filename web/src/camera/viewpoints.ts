import { Vector3, type PerspectiveCamera } from 'three';

import { localToThree } from '../data/frame';
import type {
  Manifest,
  PolygonGeometry,
  Position2,
  Position3,
  Viewpoint,
} from '../data/types';

export const GROUND_EYE_HEIGHT_M = 1.6;

export interface CameraObstacle {
  geometry: PolygonGeometry;
  baseElevationM: number;
  heightM: number;
}

export interface ViewpointTransitionOptions {
  reducedMotion?: boolean;
  durationMs?: number;
  requestFrame?: (callback: FrameRequestCallback) => number;
  now?: () => number;
}

function pointInRing(point: Position2, ring: Position2[]): boolean {
  let inside = false;
  for (
    let current = 0, previous = ring.length - 1;
    current < ring.length;
    previous = current, current += 1
  ) {
    const currentPoint = ring[current];
    const previousPoint = ring[previous];
    if (!currentPoint || !previousPoint) continue;
    const crosses =
      currentPoint[1] > point[1] !== previousPoint[1] > point[1] &&
      point[0] <
        ((previousPoint[0] - currentPoint[0]) * (point[1] - currentPoint[1])) /
          (previousPoint[1] - currentPoint[1]) +
          currentPoint[0];
    if (crosses) inside = !inside;
  }
  return inside;
}

export function pointInPolygon(
  point: Position2,
  polygon: PolygonGeometry,
): boolean {
  const outer = polygon.coordinates[0];
  if (!outer || !pointInRing(point, outer)) return false;
  return !polygon.coordinates.slice(1).some((hole) => pointInRing(point, hole));
}

export function viewpointPosition(viewpoint: Viewpoint): Position3 {
  if (viewpoint.kind === 'ground') {
    return [viewpoint.position[0], viewpoint.position[1], GROUND_EYE_HEIGHT_M];
  }
  return [...viewpoint.position];
}

export function validateCameraPosition(
  position: Position3,
  obstacles: CameraObstacle[],
): void {
  if (position[2] < 0) throw new Error('Camera cannot be below ground.');
  for (const obstacle of obstacles) {
    const insideHeight =
      position[2] >= obstacle.baseElevationM &&
      position[2] <= obstacle.baseElevationM + obstacle.heightM;
    if (
      insideHeight &&
      pointInPolygon([position[0], position[1]], obstacle.geometry)
    ) {
      throw new Error('Camera cannot be inside a footprint.');
    }
  }
}

export function aerialOverview(manifest: Manifest): Viewpoint {
  const radius = manifest.contextRadiusM;
  return {
    id: 'aerial-overview',
    label: 'Aerial overview',
    kind: 'aerial',
    position: [radius * 0.48, -radius * 0.58, radius * 0.42],
    target: [0, 0, 0],
    publicAccess: false,
  };
}

export function availableViewpoints(manifest: Manifest): Viewpoint[] {
  return [
    aerialOverview(manifest),
    ...manifest.viewpoints.filter(
      (viewpoint) => viewpoint.id !== 'aerial-overview',
    ),
  ];
}

function setCameraPose(
  camera: PerspectiveCamera,
  position: Position3,
  target: Position3,
): void {
  camera.position.copy(localToThree(position));
  camera.lookAt(localToThree(target));
  camera.updateMatrixWorld();
}

export function prefersReducedMotion(): boolean {
  return (
    globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  );
}

export async function moveToViewpoint(
  camera: PerspectiveCamera,
  viewpoint: Viewpoint,
  obstacles: CameraObstacle[] = [],
  options: ViewpointTransitionOptions = {},
): Promise<void> {
  const localPosition = viewpointPosition(viewpoint);
  validateCameraPosition(localPosition, obstacles);
  const reducedMotion = options.reducedMotion ?? prefersReducedMotion();
  const durationMs = reducedMotion ? 0 : (options.durationMs ?? 650);
  if (durationMs <= 0) {
    setCameraPose(camera, localPosition, viewpoint.target);
    return;
  }

  const startPosition = camera.position.clone();
  const endPosition = localToThree(localPosition);
  const endTarget = localToThree(viewpoint.target);
  const startDirection = camera.getWorldDirection(new Vector3());
  const startTarget = startPosition.clone().add(startDirection);
  const requestFrame = options.requestFrame ?? globalThis.requestAnimationFrame;
  const now = options.now ?? performance.now.bind(performance);
  if (!requestFrame) {
    setCameraPose(camera, localPosition, viewpoint.target);
    return;
  }

  const startedAt = now();
  await new Promise<void>((resolve) => {
    const step = (): void => {
      const progress = Math.min(1, (now() - startedAt) / durationMs);
      const eased = 1 - (1 - progress) ** 3;
      camera.position.lerpVectors(startPosition, endPosition, eased);
      camera.lookAt(new Vector3().lerpVectors(startTarget, endTarget, eased));
      camera.updateMatrixWorld();
      if (progress < 1) requestFrame(step);
      else resolve();
    };
    requestFrame(step);
  });
}

export function lookAroundGround(
  camera: PerspectiveCamera,
  yawRadians: number,
  pitchRadians: number,
): void {
  const fixedPosition = camera.position.clone();
  const pitch = Math.max(
    -Math.PI / 2 + 0.05,
    Math.min(Math.PI / 2 - 0.05, pitchRadians),
  );
  const direction = new Vector3(
    Math.sin(yawRadians) * Math.cos(pitch),
    Math.sin(pitch),
    -Math.cos(yawRadians) * Math.cos(pitch),
  );
  camera.lookAt(fixedPosition.clone().add(direction));
  camera.position.copy(fixedPosition);
  camera.updateMatrixWorld();
}
