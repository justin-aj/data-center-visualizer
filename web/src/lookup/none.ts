import type { Geocoder } from './types';

export const LOOKUP_UNAVAILABLE_MESSAGE =
  'Address lookup is unavailable. Use a curated viewpoint.';

export function createNoneGeocoder(): Geocoder {
  return {
    id: 'none',
    available: false,
    search: async () => [],
  };
}
