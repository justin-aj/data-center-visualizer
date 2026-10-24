export interface GeocodeResult {
  id: string;
  label: string;
  lon: number;
  lat: number;
}

export interface Geocoder {
  id: string;
  available: boolean;
  search: (query: string, signal?: AbortSignal) => Promise<GeocodeResult[]>;
}

export type LookupStatus =
  'unavailable' | 'idle' | 'loading' | 'ready' | 'empty' | 'error';

export interface LookupState {
  providerId: string;
  status: LookupStatus;
  selected: GeocodeResult | null;
  message: string;
}
