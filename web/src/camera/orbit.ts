import { PerspectiveCamera, Vector3 } from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export const MIN_CAMERA_HEIGHT_M = 2;
export const MIN_ORBIT_DISTANCE_M = 18;

export interface OrbitRig {
  camera: PerspectiveCamera;
  controls: OrbitControls;
  dispose: () => void;
}

export function createOrbitRig(
  canvas: HTMLCanvasElement,
  aspect = 1,
): OrbitRig {
  const camera = new PerspectiveCamera(38, aspect, 0.5, 2_500);
  camera.position.set(115, 92, 125);

  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(new Vector3(0, 4, 0));
  controls.enableDamping = false;
  controls.enablePan = true;
  controls.enableRotate = true;
  controls.enableZoom = true;
  controls.minDistance = MIN_ORBIT_DISTANCE_M;
  controls.maxDistance = 650;
  controls.minPolarAngle = 0.08;
  controls.maxPolarAngle = Math.PI / 2 - 0.04;
  controls.screenSpacePanning = false;

  const keepCameraAboveGround = (): void => {
    controls.target.y = Math.max(0, controls.target.y);
    camera.position.y = Math.max(MIN_CAMERA_HEIGHT_M, camera.position.y);
  };

  controls.addEventListener('change', keepCameraAboveGround);
  controls.update();

  return {
    camera,
    controls,
    dispose: () => {
      controls.removeEventListener('change', keepCameraAboveGround);
      controls.dispose();
    },
  };
}
