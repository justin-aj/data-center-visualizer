import type { DetailLevel } from './scene/textures';

export type ComparisonMode = 'current' | 'proposed' | 'split';

export interface CameraState {
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
}

export interface AppState {
  mode: ComparisonMode;
  camera: CameraState;
  date: string;
  time: string;
  visibleCategories: string[];
  selectedFeature: string | null;
  detailLevel: DetailLevel;
  viewpointId: string | null;
}

export const defaultAppState: AppState = {
  mode: 'proposed',
  camera: {
    position: [115, 92, 125],
    target: [0, 4, 0],
    zoom: 1,
  },
  date: '2026-10-24',
  time: '12:00',
  visibleCategories: [
    'building',
    'generator',
    'cooling',
    'electrical',
    'retaining_wall',
    'fence',
    'paving',
    'vegetation_screen',
    'other',
  ],
  selectedFeature: null,
  detailLevel: 'full',
  viewpointId: 'aerial-overview',
};

export function changeMode(state: AppState, mode: ComparisonMode): AppState {
  return { ...state, mode };
}

function coordinates(values: [number, number, number]): string {
  return values.map((value) => String(value)).join(',');
}

function parseCoordinates(
  value: string | null,
): [number, number, number] | null {
  if (!value) return null;
  const values = value.split(',').map(Number);
  if (values.length !== 3 || values.some((item) => !Number.isFinite(item))) {
    return null;
  }
  return [values[0] ?? 0, values[1] ?? 0, values[2] ?? 0];
}

export function stateToHash(state: AppState): string {
  const values = new URLSearchParams();
  values.set('mode', state.mode);
  values.set('camera', coordinates(state.camera.position));
  values.set('target', coordinates(state.camera.target));
  values.set('zoom', String(state.camera.zoom));
  values.set('date', state.date);
  values.set('time', state.time);
  values.set('categories', state.visibleCategories.join(','));
  if (state.selectedFeature) values.set('selected', state.selectedFeature);
  values.set('detail', state.detailLevel);
  if (state.viewpointId) values.set('viewpoint', state.viewpointId);
  return `#${values.toString()}`;
}

function isMode(value: string | null): value is ComparisonMode {
  return value === 'current' || value === 'proposed' || value === 'split';
}

function isDetail(value: string | null): value is DetailLevel {
  return value === 'full' || value === 'reduced';
}

export function stateFromHash(
  hash: string,
  fallback: AppState = defaultAppState,
): AppState {
  const values = new URLSearchParams(hash.replace(/^#/, ''));
  const mode = values.get('mode');
  const detail = values.get('detail');
  const position = parseCoordinates(values.get('camera'));
  const target = parseCoordinates(values.get('target'));
  const zoom = Number(values.get('zoom'));
  const categories = values.get('categories');

  return {
    mode: isMode(mode) ? mode : fallback.mode,
    camera: {
      position: position ?? [...fallback.camera.position],
      target: target ?? [...fallback.camera.target],
      zoom: Number.isFinite(zoom) && zoom > 0 ? zoom : fallback.camera.zoom,
    },
    date: values.get('date') ?? fallback.date,
    time: values.get('time') ?? fallback.time,
    visibleCategories: categories
      ? categories.split(',').filter(Boolean)
      : [...fallback.visibleCategories],
    selectedFeature: values.get('selected') ?? fallback.selectedFeature,
    detailLevel: isDetail(detail) ? detail : fallback.detailLevel,
    viewpointId: values.get('viewpoint') ?? fallback.viewpointId,
  };
}
