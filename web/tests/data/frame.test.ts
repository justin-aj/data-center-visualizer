import fc from 'fast-check';
import { describe, expect, it } from 'vitest';

import manifestFixture from '../../../contracts/fixtures/synthetic-site/manifest.json';
import {
  localToLongitudeLatitude,
  localToStatePlane,
  localToThree,
  longitudeLatitudeToLocal,
  statePlaneToLocal,
  threeToLocal,
} from '../../src/data/frame';
import { validateManifest } from '../../src/data/loader';

const origin = validateManifest(manifestFixture).origin;
const localOrdinate = fc.double({
  min: -1_200,
  max: 1_200,
  noNaN: true,
});
const height = fc.double({ min: -100, max: 500, noNaN: true });

describe('local frame', () => {
  it('maps local east, north, and up to Three.js axes', () => {
    const three = localToThree([12, 34, 5]);

    expect(three.toArray()).toEqual([12, 5, -34]);
    expect(threeToLocal(three)).toEqual([12, 34, 5]);
  });

  it('round-trips local and Three.js points exactly', () => {
    fc.assert(
      fc.property(localOrdinate, localOrdinate, height, (x, y, z) => {
        expect(threeToLocal(localToThree([x, y, z]))).toEqual([x, y, z]);
      }),
    );
  });

  it('uses the manifest State Plane origin', () => {
    const statePlane = localToStatePlane([0, 0], origin);

    expect(statePlane).toEqual({
      easting: origin.easting,
      northing: origin.northing,
    });
    expect(statePlaneToLocal(statePlane, origin)).toEqual([0, 0]);
  });

  it('round-trips latitude and longitude within one centimeter', () => {
    fc.assert(
      fc.property(localOrdinate, localOrdinate, (x, y) => {
        const longitudeLatitude = localToLongitudeLatitude([x, y], origin);
        const recovered = longitudeLatitudeToLocal(longitudeLatitude, origin);
        const errorM = Math.hypot(recovered[0] - x, recovered[1] - y);

        expect(errorM).toBeLessThanOrEqual(0.01);
      }),
      { numRuns: 500 },
    );
  });

  it('rejects non-finite coordinates', () => {
    expect(() => localToThree([Number.NaN, 0, 0])).toThrow('must be finite');
    expect(() =>
      longitudeLatitudeToLocal(
        { lon: Number.POSITIVE_INFINITY, lat: 0 },
        origin,
      ),
    ).toThrow('must be finite');
  });
});
