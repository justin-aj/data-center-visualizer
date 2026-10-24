import type { FeatureInspection } from './model';

function row(term: string, value: string): [HTMLElement, HTMLElement] {
  const name = document.createElement('dt');
  name.textContent = term;
  const description = document.createElement('dd');
  description.textContent = value;
  return [name, description];
}

function confidenceText(
  value: FeatureInspection['position'] | FeatureInspection['height'],
): string {
  const height = 'valueM' in value;
  const measured = height && value.valueM !== null ? `, ${value.valueM} m` : '';
  return `${value.status}${measured} — ${value.method}`;
}

export function createInspectPanel(inspection: FeatureInspection): HTMLElement {
  const panel = document.createElement('aside');
  panel.setAttribute('aria-labelledby', 'inspect-title');
  panel.dataset['featureId'] = inspection.id;

  const heading = document.createElement('h2');
  heading.id = 'inspect-title';
  heading.textContent = inspection.label;

  const details = document.createElement('dl');
  const rows = [
    row('State', inspection.state),
    row('Category', inspection.category.replace('_', ' ')),
    row('Position', confidenceText(inspection.position)),
    row('Footprint', confidenceText(inspection.footprint)),
    row('Height', confidenceText(inspection.height)),
    row(
      'Claim kind',
      inspection.claimKinds.length > 0
        ? inspection.claimKinds.join(', ').replaceAll('_', ' ')
        : 'No related claim',
    ),
  ];
  for (const [term, value] of rows) details.append(term, value);

  const sourcesHeading = document.createElement('h3');
  sourcesHeading.textContent = 'Sources';
  const sources = document.createElement('ul');
  if (inspection.sources.length === 0) {
    const item = document.createElement('li');
    item.textContent = 'No source listed for this unknown value.';
    sources.append(item);
  }
  for (const source of inspection.sources) {
    const item = document.createElement('li');
    if (source.publicUrl) {
      const link = document.createElement('a');
      link.href = source.publicUrl;
      link.textContent = source.citation;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      item.append(link);
    } else {
      item.textContent = source.citation;
    }
    sources.append(item);
  }

  panel.append(heading, details, sourcesHeading, sources);
  return panel;
}
