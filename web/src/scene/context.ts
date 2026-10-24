import {
  Group,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  type Material,
} from 'three';

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
  for (const [index, road] of context.roads.entries()) {
    const roads = wideLineMeshes(
      road.geometry,
      road.widthM,
      0.1,
      0.02,
      roadMaterial,
    );
    roads.name = `Road ${index + 1}: ${road.class}`;
    group.add(roads);
  }

  const railwayMaterial = material(sceneStyle.contextOutline);
  for (const [index, railway] of context.railways.entries()) {
    const railways = wideLineMeshes(
      railway.geometry,
      railway.widthM,
      0.14,
      0.04,
      railwayMaterial,
    );
    railways.name = `Railway ${index + 1}`;
    group.add(railways);
  }

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
