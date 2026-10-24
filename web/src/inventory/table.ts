import type { Manifest, Proposal, ProposalFeature } from '../data/types';

function dimensions(feature: ProposalFeature): string {
  const height =
    feature.height.valueM === null
      ? 'unknown height'
      : `${feature.height.valueM} m high`;
  if (feature.widthM !== null) return `${feature.widthM} m wide, ${height}`;
  const ring =
    feature.geometry.type === 'Polygon'
      ? feature.geometry.coordinates[0]
      : null;
  if (!ring) return height;
  const xs = ring.map((point) => point[0]);
  const ys = ring.map((point) => point[1]);
  return `${Math.max(...xs) - Math.min(...xs)} × ${Math.max(...ys) - Math.min(...ys)} m, ${height}`;
}

export function createInventoryTable(
  proposal: Proposal,
  manifest: Manifest,
): HTMLTableElement {
  const sources = new Map(
    manifest.sources.map((source) => [source.id, source.title]),
  );
  const table = document.createElement('table');
  table.createCaption().textContent = 'Visible scene features';
  const head = table.createTHead().insertRow();
  for (const label of [
    'Feature',
    'Category',
    'State',
    'Size',
    'Confidence',
    'Sources',
  ]) {
    const cell = document.createElement('th');
    cell.scope = 'col';
    cell.textContent = label;
    head.append(cell);
  }
  const body = table.createTBody();
  for (const feature of proposal.features) {
    const row = body.insertRow();
    row.dataset['category'] = feature.category;
    const sourceNames = [
      ...new Set([
        ...feature.confidence.position.sourceRefs,
        ...feature.confidence.footprint.sourceRefs,
        ...feature.height.sourceRefs,
      ]),
    ].map((id) => sources.get(id) ?? id);
    for (const value of [
      feature.label,
      feature.category.replaceAll('_', ' '),
      feature.state,
      dimensions(feature),
      `position ${feature.confidence.position.status}; footprint ${feature.confidence.footprint.status}; height ${feature.height.status}`,
      sourceNames.join(', ') || 'No source listed',
    ])
      row.insertCell().textContent = value;
  }
  return table;
}
