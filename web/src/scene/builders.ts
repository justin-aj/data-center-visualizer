import {
  BoxGeometry,
  ExtrudeGeometry,
  Float32BufferAttribute,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  Path,
  Shape,
  type BufferAttribute,
  type BufferGeometry,
  type Material,
  type Object3D,
} from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

import type {
  ContextBuilding,
  LineStringGeometry,
  PolygonGeometry,
  Position2,
} from '../data/types';

export interface MergedBuildings {
  mesh: Mesh;
  featureIds: ReadonlyMap<number, string>;
}

export interface BoxInstance {
  id: string;
  center: Position2;
  widthM: number;
  depthM: number;
  baseElevationM: number;
  heightM: number;
}

function positive(value: number, name: string): number {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`${name} must be a positive finite number.`);
  }
  return value;
}

function shapePath(ring: Position2[], path: Shape | Path): void {
  const first = ring[0];
  if (!first || ring.length < 4) {
    throw new Error('A polygon ring needs at least four points.');
  }
  path.moveTo(first[0], first[1]);
  for (const point of ring.slice(1)) path.lineTo(point[0], point[1]);
  path.closePath();
}

function polygonShape(polygon: PolygonGeometry): Shape {
  const [outer, ...holes] = polygon.coordinates;
  if (!outer) throw new Error('A polygon needs an outer ring.');

  const shape = new Shape();
  shapePath(outer, shape);
  for (const ring of holes) {
    const hole = new Path();
    shapePath(ring, hole);
    shape.holes.push(hole);
  }
  return shape;
}

export function extrudePolygon(
  polygon: PolygonGeometry,
  heightM: number,
  baseElevationM = 0,
): ExtrudeGeometry {
  const geometry = new ExtrudeGeometry(polygonShape(polygon), {
    depth: positive(heightM, 'heightM'),
    bevelEnabled: false,
    curveSegments: 1,
    steps: 1,
  });
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(0, baseElevationM, 0);
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

export function extrudedPolygonMesh(
  polygon: PolygonGeometry,
  heightM: number,
  baseElevationM = 0,
  material: Material = new MeshStandardMaterial(),
): Mesh {
  const mesh = new Mesh(
    extrudePolygon(polygon, heightM, baseElevationM),
    material,
  );
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

export function wideLineMeshes(
  line: LineStringGeometry,
  widthM: number,
  heightM: number,
  baseElevationM = 0,
  material: Material = new MeshStandardMaterial(),
): Group {
  const width = positive(widthM, 'widthM');
  const height = positive(heightM, 'heightM');
  const group = new Group();

  for (let index = 1; index < line.coordinates.length; index += 1) {
    const start = line.coordinates[index - 1];
    const end = line.coordinates[index];
    if (!start || !end) continue;
    const deltaX = end[0] - start[0];
    const deltaY = end[1] - start[1];
    const length = Math.hypot(deltaX, deltaY);
    if (length === 0) continue;

    const mesh = new Mesh(new BoxGeometry(length, height, width), material);
    mesh.position.set(
      (start[0] + end[0]) / 2,
      baseElevationM + height / 2,
      -(start[1] + end[1]) / 2,
    );
    mesh.rotation.y = Math.atan2(deltaY, deltaX);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }

  if (group.children.length === 0) {
    throw new Error('A line needs at least one non-zero segment.');
  }
  return group;
}

export function mergeContextBuildings(
  buildings: ContextBuilding[],
  material: Material = new MeshStandardMaterial(),
): MergedBuildings {
  if (buildings.length === 0) {
    throw new Error('At least one context building is required.');
  }

  const featureIds = new Map<number, string>();
  const geometries = buildings.map((building, featureIndex) => {
    const geometry = extrudePolygon(
      building.geometry,
      building.heightM,
      building.baseElevationM,
    );
    const vertexCount = geometry.getAttribute('position').count;
    geometry.setAttribute(
      'featureId',
      new Float32BufferAttribute(
        new Array<number>(vertexCount).fill(featureIndex),
        1,
      ),
    );
    featureIds.set(featureIndex, building.id);
    return geometry;
  });

  const merged = mergeGeometries(geometries, false);
  for (const geometry of geometries) geometry.dispose();
  if (!merged)
    throw new Error('Context building geometry could not be merged.');

  const mesh = new Mesh(merged, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData['featureIds'] = featureIds;
  return { mesh, featureIds };
}

export function instanceBoxes(
  instances: BoxInstance[],
  material: Material = new MeshStandardMaterial(),
): InstancedMesh {
  if (instances.length === 0) {
    throw new Error('At least one equipment instance is required.');
  }

  const mesh = new InstancedMesh(
    new BoxGeometry(1, 1, 1),
    material,
    instances.length,
  );
  const matrix = new Matrix4();
  for (const [index, instance] of instances.entries()) {
    const width = positive(instance.widthM, 'widthM');
    const depth = positive(instance.depthM, 'depthM');
    const height = positive(instance.heightM, 'heightM');
    matrix.makeScale(width, height, depth);
    matrix.setPosition(
      instance.center[0],
      instance.baseElevationM + height / 2,
      -instance.center[1],
    );
    mesh.setMatrixAt(index, matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData['featureIds'] = instances.map((instance) => instance.id);
  return mesh;
}

export function countDrawCalls(root: Object3D): number {
  let count = 0;
  root.traverse((object) => {
    if (object instanceof Mesh) count += 1;
  });
  return count;
}

export function geometryVolume(geometry: BufferGeometry): number {
  const readable = geometry.index ? geometry.toNonIndexed() : geometry;
  const positions = readable.getAttribute('position') as BufferAttribute;
  let signedVolume = 0;
  for (let index = 0; index < positions.count; index += 3) {
    const ax = positions.getX(index);
    const ay = positions.getY(index);
    const az = positions.getZ(index);
    const bx = positions.getX(index + 1);
    const by = positions.getY(index + 1);
    const bz = positions.getZ(index + 1);
    const cx = positions.getX(index + 2);
    const cy = positions.getY(index + 2);
    const cz = positions.getZ(index + 2);
    signedVolume +=
      (ax * (by * cz - bz * cy) -
        ay * (bx * cz - bz * cx) +
        az * (bx * cy - by * cx)) /
      6;
  }
  if (readable !== geometry) readable.dispose();
  return Math.abs(signedVolume);
}
