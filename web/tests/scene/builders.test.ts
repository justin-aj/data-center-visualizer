import fc from 'fast-check';
import {
  Box3,
  Group,
  MeshBasicMaterial,
  type BufferAttribute,
  type Mesh,
} from 'three';
import { describe, expect, it } from 'vitest';

import contextFixture from '../../../contracts/fixtures/synthetic-site/context.json';
import proposalFixture from '../../../contracts/fixtures/synthetic-site/proposal.json';
import { validateContext, validateProposal } from '../../src/data/loader';
import {
  countDrawCalls,
  extrudePolygon,
  extrudedPolygonMesh,
  geometryVolume,
  instanceBoxes,
  mergeContextBuildings,
  wideLineMeshes,
} from '../../src/scene/builders';
import type {
  ContextBuilding,
  PolygonGeometry,
  Position2,
} from '../../src/data/types';

const context = validateContext(contextFixture);
const proposal = validateProposal(proposalFixture);
const positiveSize = fc.double({ min: 0.2, max: 200, noNaN: true });
const coordinate = fc.double({ min: -1_000, max: 1_000, noNaN: true });

function rectangle(
  x: number,
  y: number,
  width: number,
  depth: number,
): PolygonGeometry {
  const ring: Position2[] = [
    [x, y],
    [x + width, y],
    [x + width, y + depth],
    [x, y + depth],
    [x, y],
  ];
  return { type: 'Polygon', coordinates: [ring] };
}

function vertexHeightRange(mesh: Mesh, featureIndex: number): [number, number] {
  const positions = mesh.geometry.getAttribute('position') as BufferAttribute;
  const featureIds = mesh.geometry.getAttribute('featureId') as BufferAttribute;
  let minimum = Number.POSITIVE_INFINITY;
  let maximum = Number.NEGATIVE_INFINITY;
  for (let index = 0; index < positions.count; index += 1) {
    if (featureIds.getX(index) !== featureIndex) continue;
    minimum = Math.min(minimum, positions.getY(index));
    maximum = Math.max(maximum, positions.getY(index));
  }
  return [minimum, maximum];
}

describe('scene geometry builders', () => {
  it('extrudes volume within 0.1 percent', () => {
    fc.assert(
      fc.property(
        coordinate,
        coordinate,
        positiveSize,
        positiveSize,
        positiveSize,
        (x, y, width, depth, height) => {
          const geometry = extrudePolygon(
            rectangle(x, y, width, depth),
            height,
          );
          const expected = width * depth * height;
          const errorRatio =
            Math.abs(geometryVolume(geometry) - expected) / expected;

          expect(errorRatio).toBeLessThanOrEqual(0.001);
          geometry.dispose();
        },
      ),
      { numRuns: 300 },
    );
  });

  it('keeps every merged building height exact', () => {
    fc.assert(
      fc.property(
        fc.array(positiveSize, { minLength: 1, maxLength: 12 }),
        (heights) => {
          const buildings: ContextBuilding[] = heights.map((height, index) => ({
            id: `building-${index}`,
            geometry: rectangle(index * 20, 0, 10, 12),
            baseElevationM: index % 3,
            heightM: height,
            heightStatus: 'estimated',
            heightSource: 'Property test',
          }));
          const { mesh } = mergeContextBuildings(
            buildings,
            new MeshBasicMaterial(),
          );

          for (const [index, building] of buildings.entries()) {
            const [minimum, maximum] = vertexHeightRange(mesh, index);
            expect(minimum).toBeCloseTo(building.baseElevationM, 5);
            expect(maximum - minimum).toBeCloseTo(building.heightM, 4);
          }
          mesh.geometry.dispose();
        },
      ),
      { numRuns: 100 },
    );
  });

  it('builds wide line segments at their stated height', () => {
    const group = wideLineMeshes(
      {
        type: 'LineString',
        coordinates: [
          [0, 0],
          [10, 0],
          [10, 12],
        ],
      },
      2,
      4,
    );

    expect(group.children).toHaveLength(2);
    const bounds = new Box3().setFromObject(group);
    expect(bounds.max.y - bounds.min.y).toBeCloseTo(4);
  });

  it('instances repeated boxes in one draw call', () => {
    const mesh = instanceBoxes([
      {
        id: 'generator-a',
        center: [0, 0],
        widthM: 4,
        depthM: 9,
        baseElevationM: 0,
        heightM: 3,
      },
      {
        id: 'generator-b',
        center: [12, 0],
        widthM: 4,
        depthM: 9,
        baseElevationM: 0,
        heightM: 3,
      },
    ]);

    expect(mesh.count).toBe(2);
    expect(countDrawCalls(mesh)).toBe(1);
    expect(mesh.userData['featureIds']).toEqual(['generator-a', 'generator-b']);
  });

  it('renders the full fixture below fifty draw calls', () => {
    const scene = new Group();
    scene.add(mergeContextBuildings(context.buildings).mesh);
    for (const feature of proposal.features) {
      if (feature.height.valueM === null) continue;
      if (feature.geometry.type === 'Polygon') {
        scene.add(
          extrudedPolygonMesh(
            feature.geometry,
            feature.height.valueM,
            feature.baseElevationM,
          ),
        );
      } else if (feature.widthM !== null) {
        scene.add(
          wideLineMeshes(
            feature.geometry,
            feature.widthM,
            feature.height.valueM,
            feature.baseElevationM,
          ),
        );
      }
    }

    expect(countDrawCalls(scene)).toBeLessThan(50);
  });
});
