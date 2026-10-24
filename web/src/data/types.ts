export type Position2 = [number, number];
export type Position3 = [number, number, number];

export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: Position2[][];
}

export interface LineStringGeometry {
  type: 'LineString';
  coordinates: Position2[];
}

export type FeatureGeometry = PolygonGeometry | LineStringGeometry;
export type ConfidenceStatus = 'official' | 'derived' | 'estimated' | 'unknown';
export type FeatureState = 'existing' | 'proposed' | 'removed' | 'modified';
export type FeatureCategory =
  | 'building'
  | 'generator'
  | 'cooling'
  | 'electrical'
  | 'retaining_wall'
  | 'fence'
  | 'paving'
  | 'vegetation_screen'
  | 'other';

export interface Origin {
  lon: number;
  lat: number;
  epsg: 26986;
  easting: number;
  northing: number;
  proj4: string;
}

export interface FlatDatum {
  kind: 'flat';
  siteGradeNavd88M: number | null;
  note: string;
}

export interface ControlPoint {
  id: string;
  role: 'control' | 'check';
  planX: number;
  planY: number;
  easting: number;
  northing: number;
  description: string;
  residualM: number;
}

export interface Georeference {
  sourceSheet: string;
  planUnits: string;
  planScale: string;
  method: 'similarity-least-squares';
  parameters: {
    scale: number;
    rotationDeg: number;
    translateE: number;
    translateN: number;
  };
  controlPoints: ControlPoint[];
  rmseM: number;
  checkPointCount: number;
  approximate: boolean;
  verticalDatum: 'NAVD88' | null;
  reviewedBy: string;
  reviewedAt: string;
}

export interface SourceReference {
  id: string;
  title: string;
  issuer: string;
  date: string;
  sheetOrPage: string;
  url: string;
  retrievedAt: string;
  license: string;
  distributable: boolean;
}

export interface Claim {
  id: string;
  kind: 'applicant' | 'government_finding' | 'allegation' | 'estimate';
  text: string;
  sourceRefs: string[];
}

export interface Viewpoint {
  id: string;
  label: string;
  kind: 'aerial' | 'ground';
  position: Position3;
  target: Position3;
  publicAccess: boolean;
}

export interface ReviewIssue {
  id: string;
  severity: string;
  description: string;
  featureIds: string[];
}

export interface ReviewRecord {
  reviewer: string;
  date: string;
  result: string;
  checklistRef: string;
}

export interface ManifestBase {
  projectId: string;
  packageVersion: string;
  title: string;
  siteAddress: string;
  baselineDate: string;
  proposalDate: string;
  verifiedAt: string;
  proposalVersionLabel: string;
  origin: Origin;
  datum: FlatDatum;
  contextRadiusM: number;
  sources: SourceReference[];
  claims: Claim[];
  viewpoints: Viewpoint[];
  publicViewingAreas: ('roads' | 'openSpace')[];
  reviewIssues: ReviewIssue[];
  review: ReviewRecord;
  attribution: string[];
  excludedFields: string[];
}

export type ProposalManifest = ManifestBase &
  (
    | {
        schemaVersion: '1.0.0';
        packageKind?: never;
        georeference: Georeference;
      }
    | {
        schemaVersion: '1.1.0';
        packageKind?: 'proposal';
        georeference: Georeference;
      }
  );

export interface ContextOnlyManifest extends ManifestBase {
  schemaVersion: '1.1.0';
  packageKind: 'context-only';
  georeference?: never;
}

export type Manifest = ProposalManifest | ContextOnlyManifest;

export function isContextOnlyManifest(
  manifest: Manifest,
): manifest is ContextOnlyManifest {
  return manifest.packageKind === 'context-only';
}

export interface HeightValue {
  valueM: number | null;
  status: ConfidenceStatus;
  method: string | null;
  sourceRefs: string[];
}

export interface ConfidenceValue {
  status: ConfidenceStatus;
  sourceRefs: string[];
  note: string;
}

export interface ProposalFeature {
  id: string;
  category: FeatureCategory;
  state: FeatureState;
  replaces: string[];
  label: string;
  geometry: FeatureGeometry;
  widthM: number | null;
  baseElevationM: number;
  height: HeightValue;
  confidence: {
    position: ConfidenceValue;
    footprint: ConfidenceValue;
  };
  notes: string;
}

export interface Proposal {
  features: ProposalFeature[];
}

export interface ContextBuilding {
  id: string;
  geometry: PolygonGeometry;
  baseElevationM: number;
  heightM: number;
  heightStatus: 'derived' | 'estimated';
  heightSource: string;
}

export interface ContextRoad {
  geometry: LineStringGeometry;
  class: string;
  widthM: number;
}

export interface ContextRailway {
  geometry: LineStringGeometry;
  widthM: number;
}

export interface ContextWater {
  geometry: PolygonGeometry;
  name?: string;
}

export interface ContextOpenSpace {
  geometry: PolygonGeometry;
  kind: 'park' | 'field' | 'wooded' | 'other';
  publicAccess: boolean;
}

export interface ContextScene {
  ground: { elevationM: number | null };
  buildings: ContextBuilding[];
  roads: ContextRoad[];
  railways: ContextRailway[];
  water: ContextWater[];
  openSpace: ContextOpenSpace[];
}

export interface LoadedPackage {
  manifest: Manifest;
  proposal: Proposal;
  context: ContextScene;
}
