import { DirectionalLight } from 'three';
import { describe, expect, it } from 'vitest';

import {
  sunPositionForWallClock,
  wallClockToInstant,
} from '../../src/sun/position';
import {
  applySunPosition,
  NEARBY_CONTEXT_SHADOW_RADIUS_M,
  shadowDecision,
} from '../../src/sun/shadows';

const LOWELL_LATITUDE = 42.6305082;
const LOWELL_LONGITUDE = -71.304229;

describe('Lowell wall-clock time', () => {
  it.each([
    ['2026-03-08', '01:30', '2026-03-08T06:30:00.000Z'],
    ['2026-03-08', '03:30', '2026-03-08T07:30:00.000Z'],
    ['2026-11-01', '12:00', '2026-11-01T17:00:00.000Z'],
  ])('uses New York rules for %s %s', (date, time, expected) => {
    expect(wallClockToInstant({ date, time }).toISOString()).toBe(expected);
  });

  it('rejects the missing spring-forward hour', () => {
    expect(() =>
      wallClockToInstant({ date: '2026-03-08', time: '02:30' }),
    ).toThrow('does not exist');
  });
});

describe('Lowell sun position', () => {
  it.each([
    ['2026-03-08', '01:30', -46.38, 35.51],
    ['2026-03-08', '03:30', -38.64, 53.08],
    ['2026-11-01', '12:00', 32.36, 188.94],
  ])(
    'matches the fixed reference for %s %s',
    (date, time, altitudeDeg, azimuthDeg) => {
      const position = sunPositionForWallClock(
        { date, time },
        LOWELL_LATITUDE,
        LOWELL_LONGITUDE,
      );

      expect(position.altitudeDeg).toBeCloseTo(altitudeDeg, 1);
      expect(position.azimuthDeg).toBeCloseTo(azimuthDeg, 1);
    },
  );

  it('disables shadows below the horizon', () => {
    const light = new DirectionalLight();
    const result = applySunPosition(light, {
      instant: new Date('2026-03-08T06:30:00Z'),
      altitudeDeg: -46.38,
      azimuthDeg: 35.51,
    });

    expect(result.enabled).toBe(false);
    expect(result.explanation).toContain('below the horizon');
    expect(light.visible).toBe(false);
  });
});

describe('shadow confidence', () => {
  it('labels estimated shadows', () => {
    expect(shadowDecision('estimated', 0, true)).toMatchObject({
      enabled: true,
      label: 'Estimated shadow',
    });
  });

  it('omits unknown-height shadows', () => {
    expect(shadowDecision('unknown', 0, true)).toMatchObject({
      enabled: false,
      label: 'No shadow',
    });
  });

  it('keeps only nearby context shadows', () => {
    expect(
      shadowDecision('derived', NEARBY_CONTEXT_SHADOW_RADIUS_M, false).enabled,
    ).toBe(true);
    expect(
      shadowDecision('derived', NEARBY_CONTEXT_SHADOW_RADIUS_M + 1, false)
        .enabled,
    ).toBe(false);
  });
});
