import {
  ACESFilmicToneMapping,
  BoxGeometry,
  Color,
  DirectionalLight,
  EdgesGeometry,
  Group,
  HemisphereLight,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshStandardMaterial,
  PCFSoftShadowMap,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  WebGLRenderer,
} from 'three';

import { createOrbitRig, type OrbitRig } from '../camera/orbit';
import { sceneStyle } from './style';

export interface RenderCore {
  scene: Scene;
  renderer: WebGLRenderer;
  camera: OrbitRig['camera'];
  controls: OrbitRig['controls'];
  render: () => void;
  dispose: () => void;
}

interface DemoBuilding {
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
}

const demoBuildings: readonly DemoBuilding[] = [
  { x: -72, z: -62, width: 30, depth: 20, height: 13 },
  { x: -32, z: -64, width: 24, depth: 18, height: 18 },
  { x: 12, z: -62, width: 38, depth: 22, height: 12 },
  { x: 62, z: -60, width: 25, depth: 21, height: 16 },
  { x: -68, z: -18, width: 25, depth: 26, height: 11 },
  { x: -27, z: -17, width: 28, depth: 25, height: 15 },
  { x: 52, z: -16, width: 46, depth: 25, height: 12 },
  { x: -67, z: 34, width: 28, depth: 23, height: 17 },
  { x: -25, z: 36, width: 26, depth: 25, height: 10 },
  { x: 20, z: 38, width: 37, depth: 20, height: 14 },
  { x: 68, z: 38, width: 24, depth: 25, height: 19 },
  { x: -58, z: 77, width: 38, depth: 18, height: 12 },
  { x: -8, z: 77, width: 30, depth: 19, height: 15 },
  { x: 48, z: 75, width: 48, depth: 22, height: 11 },
];

function createBuilding(building: DemoBuilding): Group {
  const geometry = new BoxGeometry(
    building.width,
    building.height,
    building.depth,
  );
  const mesh = new Mesh(
    geometry,
    new MeshStandardMaterial({
      color: sceneStyle.contextBuilding,
      roughness: 0.88,
      metalness: 0,
    }),
  );
  mesh.position.y = building.height / 2;
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  const outline = new LineSegments(
    new EdgesGeometry(geometry, 24),
    new LineBasicMaterial({ color: sceneStyle.contextOutline }),
  );
  outline.position.copy(mesh.position);

  const group = new Group();
  group.position.set(building.x, 0, building.z);
  group.add(mesh, outline);
  return group;
}

function createFlatArea(
  width: number,
  depth: number,
  color: string,
  x: number,
  z: number,
  y = 0.03,
): Mesh {
  const area = new Mesh(
    new PlaneGeometry(width, depth),
    new MeshStandardMaterial({ color, roughness: 1, metalness: 0 }),
  );
  area.rotation.x = -Math.PI / 2;
  area.position.set(x, y, z);
  area.receiveShadow = true;
  return area;
}

export function addProceduralDemo(scene: Scene): Group {
  const model = new Group();
  model.name = 'Procedural scale demo';

  model.add(
    createFlatArea(210, 16, sceneStyle.road, 0, 8),
    createFlatArea(14, 210, sceneStyle.road, -48, 0, 0.04),
    createFlatArea(38, 42, sceneStyle.openSpace, 48, -14, 0.05),
    createFlatArea(9, 210, sceneStyle.water, 100, 0, 0.06),
  );

  for (const building of demoBuildings) {
    model.add(createBuilding(building));
  }

  const proposalMaterial = new MeshStandardMaterial({
    color: sceneStyle.proposal,
    roughness: 0.74,
    metalness: 0,
  });
  const proposalGeometry = new BoxGeometry(42, 9, 24);
  const proposal = new Mesh(proposalGeometry, proposalMaterial);
  proposal.position.set(18, 4.5, -18);
  proposal.castShadow = true;
  proposal.receiveShadow = true;
  const proposalOutline = new LineSegments(
    new EdgesGeometry(proposalGeometry, 24),
    new LineBasicMaterial({ color: sceneStyle.proposalOutline }),
  );
  proposalOutline.position.copy(proposal.position);
  model.add(proposal, proposalOutline);

  scene.add(model);
  return model;
}

export function createRenderCore(host: HTMLElement): RenderCore {
  const width = Math.max(1, host.clientWidth);
  const height = Math.max(1, host.clientHeight);
  const renderer = new WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  renderer.domElement.style.display = 'block';
  renderer.domElement.style.width = '100%';
  renderer.domElement.style.height = '100%';
  renderer.domElement.setAttribute(
    'aria-label',
    'Interactive 3D planning scene',
  );
  host.append(renderer.domElement);

  const scene = new Scene();
  scene.background = new Color(sceneStyle.sky);
  scene.fog = null;

  const orbit = createOrbitRig(renderer.domElement, width / height);
  const hemisphere = new HemisphereLight(
    sceneStyle.sky,
    sceneStyle.shadow,
    2.1,
  );
  const sun = new DirectionalLight('#fff7df', 3.2);
  sun.position.set(-90, 145, 85);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2_048, 2_048);
  sun.shadow.camera.left = -150;
  sun.shadow.camera.right = 150;
  sun.shadow.camera.top = 150;
  sun.shadow.camera.bottom = -150;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 450;
  scene.add(hemisphere, sun);

  const ground = createFlatArea(260, 240, sceneStyle.ground, 0, 0, 0);
  ground.name = 'Flat demonstration ground';
  scene.add(ground);

  const render = (): void => {
    renderer.render(scene, orbit.camera);
  };
  orbit.controls.addEventListener('change', render);

  const resizeObserver = new ResizeObserver(() => {
    const nextWidth = Math.max(1, host.clientWidth);
    const nextHeight = Math.max(1, host.clientHeight);
    orbit.camera.aspect = nextWidth / nextHeight;
    orbit.camera.updateProjectionMatrix();
    renderer.setSize(nextWidth, nextHeight, false);
    render();
  });
  resizeObserver.observe(host);
  render();

  return {
    scene,
    renderer,
    camera: orbit.camera,
    controls: orbit.controls,
    render,
    dispose: () => {
      resizeObserver.disconnect();
      orbit.controls.removeEventListener('change', render);
      orbit.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
