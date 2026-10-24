import { PerspectiveCamera, Vector3 } from 'three';
import { describe, expect, it, vi } from 'vitest';

import manifestFixture from '../../../contracts/fixtures/synthetic-site/manifest.json';
import { threeToLocal } from '../../src/data/frame';
import { validateManifest } from '../../src/data/loader';
import type { PolygonGeometry } from '../../src/data/types';
import {
  aerialOverview,
  availableViewpoints,
  GROUND_EYE_HEIGHT_M,
  lookAroundGround,
  moveToViewpoint,
  pointInPolygon,
  validateCameraPosition,
} from '../../src/camera/viewpoints';

const manifest = validateManifest(manifestFixture);
const firstViewpoint = manifest.viewpoints[0];
if (!firstViewpoint) throw new Error('Fixture needs one viewpoint.');
const footprint: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [
    [
      [-5, -5],
      [5, -5],
      [5, 5],
      [-5, 5],
      [-5, -5],
    ],
  ],
};
const obstacle = { geometry: footprint, baseElevationM: 0, heightM: 8 };

describe('viewpoints', () => {
  it('adds one aerial overview before manifest viewpoints', () => {
    const viewpoints = availableViewpoints(manifest);

    expect(viewpoints[0]).toEqual(aerialOverview(manifest));
    expect(viewpoints.slice(1)).toEqual(manifest.viewpoints);
  });

  it('loads every viewpoint at its safe position and target', async () => {
    for (const viewpoint of availableViewpoints(manifest)) {
      const camera = new PerspectiveCamera();

      await moveToViewpoint(camera, viewpoint, [], { reducedMotion: true });

      const localPosition = threeToLocal(camera.position);
      expect(localPosition[0]).toBeCloseTo(viewpoint.position[0]);
      expect(localPosition[1]).toBeCloseTo(viewpoint.position[1]);
      expect(localPosition[2]).toBeCloseTo(
        viewpoint.kind === 'ground'
          ? GROUND_EYE_HEIGHT_M
          : viewpoint.position[2],
      );
      const expectedDirection = new Vector3()
        .subVectors(
          new Vector3(
            viewpoint.target[0],
            viewpoint.target[2],
            -viewpoint.target[1],
          ),
          camera.position,
        )
        .normalize();
      expect(
        camera.getWorldDirection(new Vector3()).angleTo(expectedDirection),
      ).toBeLessThan(1e-6);
    }
  });

  it('cuts instantly when reduced motion is active', async () => {
    const requestFrame = vi.fn<(callback: FrameRequestCallback) => number>();
    const camera = new PerspectiveCamera();

    await moveToViewpoint(camera, firstViewpoint, [], {
      reducedMotion: true,
      requestFrame,
    });

    expect(requestFrame).not.toHaveBeenCalled();
  });

  it('keeps ground look-around at one eye position', () => {
    const camera = new PerspectiveCamera();
    camera.position.set(10, GROUND_EYE_HEIGHT_M, 20);
    const before = camera.position.clone();

    lookAroundGround(camera, 1.2, 0.4);

    expect(camera.position).toEqual(before);
  });

  it('rejects below-ground and inside-footprint cameras', () => {
    expect(() => validateCameraPosition([10, 10, -0.1], [])).toThrow(
      'below ground',
    );
    expect(() => validateCameraPosition([0, 0, 1.6], [obstacle])).toThrow(
      'inside a footprint',
    );
    expect(() => validateCameraPosition([0, 0, 12], [obstacle])).not.toThrow();
    expect(() =>
      validateCameraPosition([12, 0, 1.6], [obstacle]),
    ).not.toThrow();
  });

  it('handles polygon holes as open space', () => {
    const outer = footprint.coordinates[0];
    if (!outer) throw new Error('Fixture needs an outer ring.');
    const polygonWithHole: PolygonGeometry = {
      type: 'Polygon',
      coordinates: [
        outer,
        [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
          [-1, -1],
        ],
      ],
    };

    expect(pointInPolygon([3, 0], polygonWithHole)).toBe(true);
    expect(pointInPolygon([0, 0], polygonWithHole)).toBe(false);
  });
});
