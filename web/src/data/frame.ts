import proj4 from 'proj4';
import { Vector3 } from 'three';

import type { Origin, Position2, Position3 } from './types';

export interface LongitudeLatitude {
  lon: number;
  lat: number;
}

export interface StatePlanePoint {
  easting: number;
  northing: number;
}

function finite(value: number, name: string): number {
  if (!Number.isFinite(value)) throw new Error(`${name} must be finite.`);
  return value;
}

export function localToThree(
  local: readonly [x: number, y: number, z: number],
): Vector3 {
  const [x, y, z] = local;
  return new Vector3(
    finite(x, 'local x'),
    finite(z, 'local z'),
    -finite(y, 'local y'),
  );
}

export function threeToLocal(three: {
  x: number;
  y: number;
  z: number;
}): Position3 {
  return [
    finite(three.x, 'Three.js x'),
    -finite(three.z, 'Three.js z'),
    finite(three.y, 'Three.js y'),
  ];
}

export function localToStatePlane(
  local: readonly [x: number, y: number],
  origin: Origin,
): StatePlanePoint {
  return {
    easting: finite(origin.easting + finite(local[0], 'local x'), 'easting'),
    northing: finite(origin.northing + finite(local[1], 'local y'), 'northing'),
  };
}

export function statePlaneToLocal(
  point: StatePlanePoint,
  origin: Origin,
): Position2 {
  return [
    finite(point.easting, 'easting') - origin.easting,
    finite(point.northing, 'northing') - origin.northing,
  ];
}

export function localToLongitudeLatitude(
  local: readonly [x: number, y: number],
  origin: Origin,
): LongitudeLatitude {
  const statePlane = localToStatePlane(local, origin);
  const [lon, lat] = proj4(origin.proj4, 'EPSG:4326', [
    statePlane.easting,
    statePlane.northing,
  ]) as [number, number];
  return {
    lon: finite(lon, 'longitude'),
    lat: finite(lat, 'latitude'),
  };
}

export function longitudeLatitudeToLocal(
  point: LongitudeLatitude,
  origin: Origin,
): Position2 {
  const [easting, northing] = proj4('EPSG:4326', origin.proj4, [
    finite(point.lon, 'longitude'),
    finite(point.lat, 'latitude'),
  ]) as [number, number];
  return statePlaneToLocal(
    {
      easting: finite(easting, 'easting'),
      northing: finite(northing, 'northing'),
    },
    origin,
  );
}
