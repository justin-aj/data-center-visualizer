import { createNoneGeocoder, LOOKUP_UNAVAILABLE_MESSAGE } from './none';
import type { Geocoder, GeocodeResult, LookupState } from './types';

export class AddressLookupController {
  readonly provider: Geocoder;
  #state: LookupState;

  constructor(provider: Geocoder = createNoneGeocoder()) {
    this.provider = provider;
    this.#state = {
      providerId: provider.id,
      status: provider.available ? 'idle' : 'unavailable',
      selected: null,
      message: provider.available ? '' : LOOKUP_UNAVAILABLE_MESSAGE,
    };
  }

  getState(): Readonly<LookupState> {
    return structuredClone(this.#state);
  }

  async search(query: string, signal?: AbortSignal): Promise<GeocodeResult[]> {
    if (!this.provider.available) return [];
    const activeQuery = query.trim();
    if (!activeQuery) {
      this.#state = {
        ...this.#state,
        status: 'empty',
        message: 'Enter an address.',
      };
      return [];
    }

    this.#state = { ...this.#state, status: 'loading', message: 'Searching…' };
    try {
      const results = await this.provider.search(activeQuery, signal);
      this.#state = {
        ...this.#state,
        status: results.length > 0 ? 'ready' : 'empty',
        message: results.length > 0 ? 'Address found.' : 'No address found.',
      };
      return results;
    } catch (error) {
      if (signal?.aborted) throw error;
      this.#state = {
        ...this.#state,
        status: 'error',
        message: 'Address lookup failed. Curated viewpoints still work.',
      };
      return [];
    }
  }

  select(result: GeocodeResult): void {
    this.#state = {
      ...this.#state,
      status: 'ready',
      selected: structuredClone(result),
      message: 'Viewpoint placed near the address result.',
    };
  }
}

export function lookupExportMetadata(controller: AddressLookupController): {
  providerId: string;
  selectedLocation: { lon: number; lat: number } | null;
} {
  const state = controller.getState();
  return {
    providerId: state.providerId,
    selectedLocation: state.selected
      ? { lon: state.selected.lon, lat: state.selected.lat }
      : null,
  };
}
