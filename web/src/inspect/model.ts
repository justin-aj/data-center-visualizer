import type {
  Claim,
  ConfidenceStatus,
  Manifest,
  Proposal,
  ProposalFeature,
  SourceReference,
} from '../data/types';

export interface InspectionConfidence {
  status: ConfidenceStatus;
  method: string;
}

export interface InspectionSource {
  id: string;
  citation: string;
  publicUrl: string | null;
}

export interface FeatureInspection {
  id: string;
  label: string;
  state: ProposalFeature['state'];
  category: ProposalFeature['category'];
  position: InspectionConfidence;
  footprint: InspectionConfidence;
  height: InspectionConfidence & { valueM: number | null };
  sources: InspectionSource[];
  claimKinds: Claim['kind'][];
}

function publicUrl(source: SourceReference): string | null {
  try {
    const url = new URL(source.url);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    if (url.hostname.endsWith('.invalid')) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function citation(source: SourceReference): string {
  return [
    source.title,
    source.issuer,
    source.date,
    source.sheetOrPage,
    `retrieved ${source.retrievedAt}`,
  ].join(' — ');
}

function sourceIds(feature: ProposalFeature): string[] {
  return [
    ...feature.confidence.position.sourceRefs,
    ...feature.confidence.footprint.sourceRefs,
    ...feature.height.sourceRefs,
  ].filter((id, index, ids) => ids.indexOf(id) === index);
}

function relatedClaimKinds(
  feature: ProposalFeature,
  claims: Claim[],
): Claim['kind'][] {
  const sources = new Set(sourceIds(feature));
  return claims
    .filter((claim) => claim.sourceRefs.some((source) => sources.has(source)))
    .map((claim) => claim.kind)
    .filter((kind, index, kinds) => kinds.indexOf(kind) === index);
}

export function inspectFeature(
  featureId: string,
  proposal: Proposal,
  manifest: Manifest,
): FeatureInspection {
  const feature = proposal.features.find(
    (candidate) => candidate.id === featureId,
  );
  if (!feature) throw new Error(`Unknown feature: ${featureId}`);
  const sourcesById = new Map(
    manifest.sources.map((source) => [source.id, source] as const),
  );
  const sources = sourceIds(feature).map((id) => {
    const source = sourcesById.get(id);
    if (!source) {
      return {
        id,
        citation: `Missing source record: ${id}`,
        publicUrl: null,
      };
    }
    return { id, citation: citation(source), publicUrl: publicUrl(source) };
  });

  return {
    id: feature.id,
    label: feature.label,
    state: feature.state,
    category: feature.category,
    position: {
      status: feature.confidence.position.status,
      method: feature.confidence.position.note || 'No method recorded',
    },
    footprint: {
      status: feature.confidence.footprint.status,
      method: feature.confidence.footprint.note || 'No method recorded',
    },
    height: {
      status: feature.height.status,
      valueM: feature.height.valueM,
      method: feature.height.method ?? 'No height method recorded',
    },
    sources,
    claimKinds: relatedClaimKinds(feature, manifest.claims),
  };
}
