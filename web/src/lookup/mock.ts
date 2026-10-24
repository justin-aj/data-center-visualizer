import type { Geocoder, GeocodeResult } from './types';

export class MockGeocoder implements Geocoder {
  readonly id = 'mock';
  readonly available = true;
  readonly results: GeocodeResult[];
  lastQuery: string | null = null;

  constructor(results: GeocodeResult[]) {
    this.results = structuredClone(results);
  }

  async search(query: string): Promise<GeocodeResult[]> {
    this.lastQuery = query;
    return structuredClone(this.results);
  }
}
