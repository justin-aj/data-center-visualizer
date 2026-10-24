import type { ContextScene } from '../data/types';

export interface SceneOverlayInfo {
  title: string;
  siteAddress: string;
  baselineDate: string;
  contextRadiusM: number;
  attributionCount: number;
  context: ContextScene;
  showMock: boolean;
}

export interface SceneOverlay {
  element: HTMLElement;
  setViewpoint: (label: string) => void;
}

function el(tag: string, className: string, text?: string): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function stat(value: string, label: string): HTMLElement {
  const item = el('div', 'ov-stat');
  item.append(el('strong', '', value), el('span', '', label));
  return item;
}

function swatch(color: string, label: string, detail: string): HTMLElement {
  const row = el('div', 'ov-legend-row');
  const chip = el('span', 'ov-chip');
  chip.style.background = color;
  const text = el('div', '');
  text.append(el('strong', '', label), el('span', '', detail));
  row.append(chip, text);
  return row;
}

export function createSceneOverlay(info: SceneOverlayInfo): SceneOverlay {
  const root = el('div', 'scene-overlay');
  root.setAttribute('aria-hidden', 'false');

  const card = el('section', 'ov-card ov-site');
  card.setAttribute('aria-label', 'Site summary');
  card.append(
    el('p', 'ov-kicker', 'Pilot site · Lowell, MA'),
    el('h2', 'ov-title', 'What would it look like here?'),
    el('p', 'ov-sub', info.title),
    el('p', 'ov-address', info.siteAddress),
  );
  const stats = el('div', 'ov-stats');
  const c = info.context;
  stats.append(
    stat(`${(info.contextRadiusM / 1000).toFixed(1)} km`, 'radius modeled'),
    stat(c.buildings.length.toLocaleString(), 'buildings'),
    stat(c.roads.length.toLocaleString(), 'road segments'),
    stat(String(c.water.length + c.openSpace.length), 'water & parks'),
  );
  card.append(
    stats,
    el(
      'p',
      'ov-foot',
      `Baseline ${info.baselineDate} · ${info.attributionCount} public data sources (MassGIS, MassDOT, USGS, OpenStreetMap)`,
    ),
  );

  const viewpoint = el('div', 'ov-pill ov-viewpoint', 'Neighborhood overview');

  const help = el('section', 'ov-card ov-help');
  help.setAttribute('aria-label', 'Controls');
  help.append(
    el('p', 'ov-kicker', 'Explore'),
    el('p', '', 'Drag to orbit · Scroll or + / − to zoom'),
    el('p', '', '[ and ] step through street-level public viewpoints'),
  );

  root.append(card, viewpoint, help);

  if (info.showMock) {
    const legend = el('section', 'ov-card ov-legend');
    legend.setAttribute('aria-label', 'Legend');
    legend.append(
      el('p', 'ov-kicker', 'What you are seeing'),
      swatch(
        '#f07a3f',
        'Proposed hall (illustrative)',
        '70 × 34 m, 24 m tall ≈ 8 stories, beside today’s Markley building',
      ),
      swatch(
        '#2f6fa3',
        'Backup generators (illustrative)',
        '6 units, 9 × 5 m each, facing the street',
      ),
      swatch(
        '#c9c6bf',
        'Existing buildings',
        'Heights estimated from footprint',
      ),
      el(
        'p',
        'ov-warn',
        'Mock-up for demonstration. Sizes and positions are not from proposal documents.',
      ),
    );
    root.append(legend);
  } else {
    root.append(
      el(
        'div',
        'ov-pill ov-note',
        'Context only · Proposal geometry not yet georeferenced',
      ),
    );
  }

  return {
    element: root,
    setViewpoint: (label) => {
      viewpoint.textContent = label;
    },
  };
}

export const OVERLAY_CSS = `
  .scene-overlay { position: absolute; inset: 0; pointer-events: none; font-size: .85rem; }
  .ov-card { position: absolute; animation: ov-in .5s ease-out both; pointer-events: auto; background: rgba(255,255,255,.88);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(30,42,49,.08); border-radius: 14px;
    box-shadow: 0 8px 28px rgba(16,32,48,.16); padding: .9rem 1rem; color: #1e2a31; }
  .ov-card p { margin: .15rem 0; }
  .ov-kicker { text-transform: uppercase; letter-spacing: .08em; font-size: .68rem;
    font-weight: 700; color: #b4532a; }
  .ov-site { top: 1rem; left: 1rem; width: min(340px, calc(100% - 2rem)); }
  .ov-title { margin: .25rem 0 .1rem; font-size: 1.35rem; line-height: 1.15; letter-spacing: -.01em;
    background: linear-gradient(90deg,#14232d,#b4532a); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .ov-sub { font-weight: 600; color: #1e2a31; }
  .ov-address { color: #4a5a64; }
  .ov-stats { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin: .7rem 0 .5rem; }
  .ov-stat { background: #f3efe6; border-radius: 10px; padding: .45rem .6rem; }
  .ov-stat strong { display: block; font-size: 1.25rem; color: #b4532a; }
  .ov-stat span { color: #5b6a73; font-size: .75rem; }
  .ov-foot { color: #5b6a73; font-size: .72rem; }
  .ov-pill { position: absolute; pointer-events: auto; background: #1e2a31; color: #fff;
    border-radius: 999px; padding: .4rem .9rem; font-weight: 600;
    box-shadow: 0 6px 18px rgba(16,32,48,.25); }
  .ov-viewpoint { top: 1rem; right: 1rem; }
  .ov-note { bottom: 1rem; left: 50%; transform: translateX(-50%); background: #f7f3ea; color: #1e2a31; }
  .ov-help { bottom: 1rem; right: 1rem; width: 250px; }
  .ov-legend { bottom: 1rem; left: 1rem; width: 300px; }
  .ov-legend-row { display: flex; gap: .6rem; align-items: flex-start; margin: .45rem 0; }
  .ov-legend-row strong { display: block; }
  .ov-legend-row span { color: #5b6a73; font-size: .75rem; }
  .ov-chip { flex: none; width: 16px; height: 16px; border-radius: 4px; margin-top: 2px; }
  .ov-warn { margin-top: .5rem !important; padding: .45rem .6rem; border-radius: 8px;
    background: #fff4e5; color: #8a4b12; font-size: .75rem; }
  @keyframes ov-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .ov-card { animation: none; } }
  .ov-legend-row:first-of-type .ov-chip { box-shadow: 0 0 0 3px rgba(240,122,63,.25); }
  @media (max-width: 900px) { .ov-help { display: none; } }
  @media (max-width: 600px) {
    .ov-site { width: auto; right: 1rem; } .ov-stats { display: none; }
    .ov-legend { width: auto; right: 1rem; } .ov-viewpoint { top: auto; bottom: 1rem; }
  }
`;
