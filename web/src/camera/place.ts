import type {
  ContextScene,
  Manifest,
  PolygonGeometry,
  Position2,
  Position3,
  Proposal,
} from '../data/types';
import { GROUND_EYE_HEIGHT_M, pointInPolygon } from './viewpoints';

export type PlacementReason =
  | 'valid'
  | 'out-of-radius'
  | 'inside-footprint'
  | 'private-ground'
  | 'not-public-ground';

export interface ViewpointPlacement {
  valid: boolean;
  reason: PlacementReason;
  explanation: string;
  position: Position3 | null;
}

function distanceToSegment(
  point: Position2,
  start: Position2,
  end: Position2,
): number {
  const deltaX = end[0] - start[0];
  const deltaY = end[1] - start[1];
  const lengthSquared = deltaX * deltaX + deltaY * deltaY;
  if (lengthSquared === 0)
    return Math.hypot(point[0] - start[0], point[1] - start[1]);
  const projection = Math.max(
    0,
    Math.min(
      1,
      ((point[0] - start[0]) * deltaX + (point[1] - start[1]) * deltaY) /
        lengthSquared,
    ),
  );
  return Math.hypot(
    point[0] - (start[0] + projection * deltaX),
    point[1] - (start[1] + projection * deltaY),
  );
}

function isInsideRoad(point: Position2, context: ContextScene): boolean {
  return context.roads.some((road) => {
    for (let index = 1; index < road.geometry.coordinates.length; index += 1) {
      const start = road.geometry.coordinates[index - 1];
      const end = road.geometry.coordinates[index];
      if (
        start &&
        end &&
        distanceToSegment(point, start, end) <= road.widthM / 2
      ) {
        return true;
      }
    }
    return false;
  });
}

function proposalFootprints(proposal: Proposal): PolygonGeometry[] {
  return proposal.features
    .filter((feature) => feature.geometry.type === 'Polygon')
    .map((feature) => feature.geometry as PolygonGeometry);
}

function isInsideFootprint(
  point: Position2,
  context: ContextScene,
  proposal: Proposal,
): boolean {
  return [
    ...context.buildings.map((building) => building.geometry),
    ...proposalFootprints(proposal),
  ].some((footprint) => pointInPolygon(point, footprint));
}

export function validateViewpointPlacement(
  point: Position2,
  manifest: Manifest,
  context: ContextScene,
  proposal: Proposal,
): ViewpointPlacement {
  if (Math.hypot(point[0], point[1]) > manifest.contextRadiusM) {
    return {
      valid: false,
      reason: 'out-of-radius',
      explanation: 'Choose a point inside the published scene area.',
      position: null,
    };
  }

  if (isInsideFootprint(point, context, proposal)) {
    return {
      valid: false,
      reason: 'inside-footprint',
      explanation: 'Choose a point outside every modeled footprint.',
      position: null,
    };
  }

  const publicOpenSpace = context.openSpace.some(
    (area) => area.publicAccess && pointInPolygon(point, area.geometry),
  );
  const privateOpenSpace = context.openSpace.some(
    (area) => !area.publicAccess && pointInPolygon(point, area.geometry),
  );
  const publicRoad = isInsideRoad(point, context);
  const roadsAllowed = manifest.publicViewingAreas.includes('roads');
  const openSpaceAllowed = manifest.publicViewingAreas.includes('openSpace');

  if ((roadsAllowed && publicRoad) || (openSpaceAllowed && publicOpenSpace)) {
    return {
      valid: true,
      reason: 'valid',
      explanation: 'Public ground viewpoint ready.',
      position: [point[0], point[1], GROUND_EYE_HEIGHT_M],
    };
  }

  if (privateOpenSpace) {
    return {
      valid: false,
      reason: 'private-ground',
      explanation: 'This open-space area is not marked for public access.',
      position: null,
    };
  }

  return {
    valid: false,
    reason: 'not-public-ground',
    explanation: 'Choose a published public road or open-space area.',
    position: null,
  };
}
