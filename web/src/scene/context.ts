import {
  Group,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  type BufferGeometry,
  type Material,
} from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

import type { ContextScene } from '../data/types';
import {
  countDrawCalls,
  extrudedPolygonMesh,
  mergeContextBuildings,
  wideLineMeshes,
} from './builders';
import { sceneStyle } from './style';

export const FLAT_GROUND_NOTE = 'Ground shown flat; terrain not modeled';

export interface ContextLayerCounts {
  buildings: number;
  roads: number;
  railways: number;
  water: number;
  openSpace: number;
}

export interface BuiltContextScene {
  group: Group;
  layerCounts: ContextLayerCounts;
  drawCalls: number;
  legendNote: typeof FLAT_GROUND_NOTE;
}

function material(color: string): MeshStandardMaterial {
  return new MeshStandardMaterial({ color, roughness: 0.9, metalness: 0 });
}

function addFlatPolygon(
  group: Group,
  geometry: ContextScene['water'][number]['geometry'],
  color: string,
  elevationM: number,
  layerMaterial?: Material,
): void {
  const mesh = extrudedPolygonMesh(
    geometry,
    0.08,
    elevationM,
    layerMaterial ?? material(color),
  );
  mesh.castShadow = false;
  mesh.receiveShadow = true;
  group.add(mesh);
}

function mergeLineGroups(
  groups: Group[],
  layerMaterial: Material,
  name: string,
): Mesh | null {
  const geometries: BufferGeometry[] = [];
  for (const group of groups) {
    for (const child of group.children) {
      if (!(child instanceof Mesh)) continue;
      child.updateMatrix();
      const geometry = child.geometry.clone();
      geometry.applyMatrix4(child.matrix);
      geometries.push(geometry);
    }
  }
  if (geometries.length === 0) return null;
  const merged = mergeGeometries(geometries, false);
  for (const geometry of geometries) geometry.dispose();
  for (const group of groups) {
    group.traverse((object) => {
      if (object instanceof Mesh) object.geometry.dispose();
    });
  }
  if (!merged) throw new Error(`${name} geometry could not be merged.`);
  const mesh = new Mesh(merged, layerMaterial);
  mesh.name = name;
  mesh.receiveShadow = true;
  return mesh;
}
function groundPlane(radiusM: number): Mesh {
  const mesh = new Mesh(
    new PlaneGeometry(radiusM * 2, radiusM * 2),
    material(sceneStyle.ground),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  mesh.name = 'Flat context ground';
  return mesh;
}

export function buildContextLayers(
  context: ContextScene,
  radiusM: number,
): BuiltContextScene {
  if (!Number.isFinite(radiusM) || radiusM <= 0) {
    throw new Error('Context radius must be a positive finite number.');
  }

  const group = new Group();
  group.name = 'Neighborhood context';
  group.add(groundPlane(radiusM));

  if (context.buildings.length > 0) {
    const buildings = mergeContextBuildings(
      context.buildings,
      material(sceneStyle.contextBuilding),
    ).mesh;
    buildings.name = 'Context buildings';
    group.add(buildings);
  }

  const roadMaterial = material(sceneStyle.road);
  const roads = mergeLineGroups(
    context.roads.map((road) =>
      wideLineMeshes(road.geometry, road.widthM, 0.1, 0.02, roadMaterial),
    ),
    roadMaterial,
    'Context roads',
  );
  if (roads) group.add(roads);

  const railwayMaterial = material(sceneStyle.contextOutline);
  const railways = mergeLineGroups(
    context.railways.map((railway) =>
      wideLineMeshes(
        railway.geometry,
        railway.widthM,
        0.14,
        0.04,
        railwayMaterial,
      ),
    ),
    railwayMaterial,
    'Context railways',
  );
  if (railways) group.add(railways);

  const waterMaterial = material(sceneStyle.water);
  for (const water of context.water) {
    addFlatPolygon(
      group,
      water.geometry,
      sceneStyle.water,
      0.04,
      waterMaterial,
    );
  }

  const openSpaceMaterial = material(sceneStyle.openSpace);
  for (const openSpace of context.openSpace) {
    addFlatPolygon(
      group,
      openSpace.geometry,
      sceneStyle.openSpace,
      0.02,
      openSpaceMaterial,
    );
  }

  const layerCounts: ContextLayerCounts = {
    buildings: context.buildings.length,
    roads: context.roads.length,
    railways: context.railways.length,
    water: context.water.length,
    openSpace: context.openSpace.length,
  };

  return {
    group,
    layerCounts,
    drawCalls: countDrawCalls(group),
    legendNote: FLAT_GROUND_NOTE,
  };
}
