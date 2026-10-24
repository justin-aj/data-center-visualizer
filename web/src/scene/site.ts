import {
  EdgesGeometry,
  Group,
  LineSegments,
  MeshStandardMaterial,
  type Mesh,
} from 'three';

import type { ContextBuilding, ContextScene } from '../data/types';
import { pointInPolygon } from '../camera/viewpoints';
import { extrudedPolygonMesh } from './builders';
import { createStatusSprite, outlineMaterial } from './textures';

export const SITE_HIGHLIGHT_COLOR = '#2f6f9f';

export interface SiteHighlight {
  building: ContextBuilding;
  areaM2: number;
  group: Group;
  description: string;
}

function ringArea(ring: [number, number][]): number {
  let sum = 0;
  for (let index = 0; index < ring.length; index += 1) {
    const previous = ring[(index + ring.length - 1) % ring.length];
    const current = ring[index];
    if (!previous || !current) continue;
    sum += previous[0] * current[1] - current[0] * previous[1];
  }
  return Math.abs(sum) / 2;
}

/** The context building whose footprint contains the package origin. */
export function findSiteBuilding(
  context: ContextScene,
): ContextBuilding | null {
  return (
    context.buildings.find((building) =>
      pointInPolygon([0, 0], building.geometry),
    ) ?? null
  );
}

export function withoutBuilding(
  context: ContextScene,
  buildingId: string,
): ContextScene {
  return {
    ...context,
    buildings: context.buildings.filter(
      (building) => building.id !== buildingId,
    ),
  };
}

export function buildSiteHighlight(building: ContextBuilding): SiteHighlight {
  const outer = building.geometry.coordinates[0] ?? [];
  const areaM2 = Math.round(ringArea(outer));
  const estimated = building.heightStatus === 'estimated';
  const mesh: Mesh = extrudedPolygonMesh(
    building.geometry,
    building.heightM,
    building.baseElevationM,
    new MeshStandardMaterial({
      color: SITE_HIGHLIGHT_COLOR,
      roughness: 0.75,
      metalness: 0,
    }),
  );
  const outline = new LineSegments(
    new EdgesGeometry(mesh.geometry, 24),
    outlineMaterial(estimated),
  );
  if (estimated) outline.computeLineDistances();
  mesh.add(outline);

  const label = createStatusSprite(
    `Existing site building · height ${building.heightStatus}`,
  );
  label.scale.set(140, 20, 1);
  label.position.set(0, building.baseElevationM + building.heightM + 30, 0);

  const group = new Group();
  group.name = 'Existing Markley site building';
  group.add(mesh, label);

  const description =
    `Highlighted: existing building at the Markley site. ` +
    `MassGIS footprint ${areaM2.toLocaleString('en-US')} m²; ` +
    `height ${building.heightStatus} at ${building.heightM} m ` +
    `(${building.heightSource}). Proposed changes are not shown.`;

  return { building, areaM2, group, description };
}
