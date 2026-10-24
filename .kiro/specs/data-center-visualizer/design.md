# Data Center Visualizer Design

**Status:** Approved by Ajin Frank Justin on 2026-10-24, after advisor review by GPT-5.6 Sol (section 12).  
**Implements:** [requirements.md](requirements.md)  
**Team model:** Two people, each running Kiro agents in parallel lanes (section 10 and `.kiro/steering/parallel-development.md`).

## 1. Overview

The system has two independent halves joined by one versioned file contract:

```text
 Lane A: pipeline (Python)                    Lane B: web (TypeScript)
 ─────────────────────────                    ────────────────────────
 public sources ──► fetch ──► context ─┐
 curation files (human-reviewed) ──────┼──► package ──► data/published/<project>/<version>/
 control points ──► georef ────────────┘                         │
                                                                 ▼
                                         contracts/*.schema.json ◄── validated by both
                                                                 │
                                       web/scripts/sync-data ────┤ copies into web/public/data
                                                                 ▼
                                    loader ──► scene builders ──► Three.js renderer
                                                                 ├─ comparison modes
                                                                 ├─ viewpoints + sun/shadows
                                                                 ├─ inspect + inventory
                                                                 └─ PNG export
```

- **Lane A** turns public records into a validated **proposal package**: neighborhood context, georeferenced proposal features, and provenance.
- **Lane B** renders any valid proposal package as an interactive, stylized 3D scene. Until Lane A publishes real Lowell data, Lane B develops against a hand-made synthetic fixture.
- **`contracts/`** holds JSON Schemas and fixtures. Both lanes validate against the same files, so neither lane needs the other's code to make progress.

The web app is fully static: no backend, database, login, or live permit API (Requirements 10 and 11.5).

## 2. Repository layout and ownership

| Path | Owner | Contents |
|---|---|---|
| `contracts/` | Lane A writes 1.0.0; later changes shared | JSON Schemas, `CHANGELOG.md`, synthetic fixture |
| `pipeline/` | Lane A | Python package, curation inputs, tests. `pipeline/build/` and `pipeline/curation/*/extracted/` are ignored. |
| `data/sources.yaml` | Lane A | Source manifest: URL, issuer, license, distributable flag, verification status |
| `data/raw/` | Lane A (ignored) | Downloaded sources, recreated by `fetch` |
| `data/published/` | Lane A | Tracked, versioned packages consumed by the web app |
| `web/` | Lane B | Vite app, rendering, UI, unit and e2e tests. `web/public/data/` and `web/public/fixtures/` are generated and ignored. |
| `scripts/check-all.sh` | Shared | Contract validation plus both lanes' checks |
| `.kiro/specs/…/tasks.md` | Shared | Each lane edits only its own checkboxes (exempt from `Files:` lists) |
| `README.md` | Shared | Setup, run, and test instructions |

## 3. Coordinate system and datum

- Source CRS: **EPSG:26986** (NAD83 / Massachusetts Mainland, meters).
- Origin `(E0, N0)`: the parcel-based site anchor in `manifest.origin`. The initial pilot anchor is the mapped building center (42.6305082, −71.3042290), converted to EPSG:26986, then replaced by the parcel centroid once parcels load.
- Local coordinates: `x = E − E0` (east) and `y = N − N0` (north), in meters, rounded to 0.1 m.
- **Flat-datum MVP.** All features stand on one ground plane. `baseElevationM` is height above that plane: 0 for the MVP unless a source gives a pad or wall elevation relative to site grade. Terrain is not modeled, and the UI states this in the legend. `context.ground.elevationM` records the site grade in NAVD88 for reference only. A terrain mesh can be added later without breaking the contract because `baseElevationM` already exists.
- Three.js mapping: local `(x, y, z)` becomes `(x, z, −y)`, with Y up.
- Lat/lon conversion is used only for point and address lookup. Lane B uses `proj4` with `manifest.origin.proj4`.

Within 1.2 km of the origin, State Plane distortion is far below the 2 m limit in Requirement 2.4.

## 4. Data contract (`contracts/`)

### 4.1 Package files

```text
data/published/<projectId>/<packageVersion>/
├── manifest.json     project metadata, origin, georeference, sources, viewpoints, attribution
├── proposal.json     proposal features with state and per-attribute confidence
└── context.json      neighborhood context layers
```

`packageVersion` uses semver. Any change to a published value creates a new version directory (Requirement 1.3). Published directories are never edited in place.

### 4.2 `manifest.json`

| Field | Type | Notes |
|---|---|---|
| `schemaVersion` | string | Contract version, for example `"1.0.0"` |
| `projectId`, `packageVersion`, `title`, `siteAddress` | string | Req 1.1 |
| `baselineDate`, `proposalDate`, `verifiedAt` | ISO date | Req 1.1, 4.6 |
| `proposalVersionLabel` | string | For example `"Lowell SPR plan set, 2024-08-09"`. Req 12.4 |
| `origin` | object | `lon`, `lat`, `epsg` (26986), `easting`, `northing`, `proj4` |
| `datum` | object | `kind: "flat"`, `siteGradeNavd88M` (number or null), `note` |
| `contextRadiusM` | number | At least 1000 for the pilot. Req 3.7 |
| `georeference` | object | See below. Req 2.2–2.4 |
| `sources[]` | object | `id`, `title`, `issuer`, `date`, `sheetOrPage`, `url`, `retrievedAt`, `license`, `distributable`. Req 8.2, 8.3 |
| `claims[]` | object | `id`, `kind` (`applicant` \| `government_finding` \| `allegation` \| `estimate`), `text`, `sourceRefs[]`. Req 8.5 |
| `viewpoints[]` | object | `id`, `label`, `kind` (`aerial` \| `ground`), `position[3]`, `target[3]`, `publicAccess` (bool). Req 5.1 |
| `publicViewingAreas` | string | Name of the context layers that count as public ground (for example `["roads", "openSpace"]`). Req 5.2 |
| `reviewIssues[]` | object | `id`, `severity`, `description`, `featureIds[]`. Req 2.6 |
| `review` | object | `reviewer`, `date`, `result`, `checklistRef`. Req 12.5 |
| `attribution[]` | string | Required credits. Req 7.2 |
| `excludedFields[]` | string | PII fields deliberately removed. Req 1.6 |

`georeference`:

| Field | Notes |
|---|---|
| `sourceSheet` | Source id plus sheet, for example `src-spr-2024:C-100` |
| `planUnits`, `planScale` | For example `"ft"`, `"1 in = 20 ft"` |
| `method` | Always `"similarity-least-squares"`. Affine fits are not allowed (section 5.3). |
| `parameters` | `scale`, `rotationDeg`, `translateE`, `translateN` |
| `controlPoints[]` | `id`, `role` (`control` \| `check`), `planX`, `planY`, `easting`, `northing`, `description`, `residualM` |
| `rmseM`, `checkPointCount` | RMSE on check points only |
| `approximate` | `true` when `rmseM > 2` or `checkPointCount < 2` |
| `verticalDatum` | `"NAVD88"` or `null` |
| `reviewedBy`, `reviewedAt` | Person who approved the control points |

### 4.3 `proposal.json` features

```json
{
  "id": "gen-yard-n-03",
  "category": "generator",
  "state": "proposed",
  "replaces": [],
  "label": "Proposed generator on pad",
  "geometry": { "type": "Polygon", "coordinates": [[[12.4, 88.1], "…"]] },
  "widthM": null,
  "baseElevationM": 0,
  "height": { "valueM": null, "status": "unknown", "method": null, "sourceRefs": [] },
  "confidence": {
    "position":  { "status": "derived",  "sourceRefs": ["src-spr-2024"], "note": "Georeferenced from C-100" },
    "footprint": { "status": "official", "sourceRefs": ["src-spr-2024"], "note": "13'-8\" x 55'-4 1/2\" typ." }
  },
  "notes": ""
}
```

- `category`: `building`, `generator`, `cooling`, `electrical`, `retaining_wall`, `fence`, `paving`, `vegetation_screen`, `other` (Req 3.2).
- `state`: `existing` (present at baseline and kept), `proposed` (new), `removed` (present at baseline, gone in the proposal), or `modified` (present in both but changed; `replaces` lists the superseded `existing` feature).
- Status values: `official`, `derived`, `estimated`, `unknown` (Req 8.1).
- Line features (walls and fences) use `LineString` with `widthM`.

**Invariants** (enforced by the schema where possible, otherwise by the validators in tasks 5.2 and 7.6):

1. `height.status == "unknown"` if and only if `height.valueM == null`.
2. Every `sourceRefs` entry resolves to a `manifest.sources[].id`.
3. Every `replaces` id exists and points to a feature in state `existing` or `removed`.
4. Current scene = `existing` + `removed` + features that `modified` replaces. Proposed scene = `existing` (minus anything replaced) + `proposed` + `modified`. No id appears in a scene twice (Req 4.4).
5. Polygons are valid, closed, non-self-intersecting, and have area greater than 0.
6. All coordinates lie within `contextRadiusM + 100` m of the origin.
7. No property key matches the PII blocklist (`owner`, `own_`, `abutter`, `phone`, `email`, and similar).

### 4.4 `context.json` layers

| Layer | Geometry | Required properties |
|---|---|---|
| `buildings` | Polygon | `id`, `baseElevationM` (0 in MVP), `heightM`, `heightStatus` (`derived` \| `estimated`), `heightSource` |
| `roads` | LineString | `class`, `widthM` |
| `railways` | LineString | `widthM` |
| `water` | Polygon | `name` (optional) |
| `openSpace` | Polygon | `kind` (`park`, `field`, `wooded`, `other`), `publicAccess` (bool) |

Context buildings carry no owner, assessor, or address attributes.

### 4.5 Contract change protocol

1. Changes within a major version are additive (new optional fields only).
2. Every change bumps `schemaVersion`, updates the synthetic fixture, and adds a dated entry to `contracts/CHANGELOG.md`.
3. Commit messages start with `contract:`. Each lane's agent stores the last version it saw in `.kiro/settings/contract-seen` and reads newer CHANGELOG entries at every "start development".
4. Breaking changes need agreement from both people and must not happen while either lane has work in progress against the old version.

### 4.6 Synthetic fixture

`contracts/fixtures/synthetic-site/` is a small hand-made package with about 20 context buildings, roads, a public park, water, and one feature of each proposal category, covering each state and status. It deliberately includes an unknown height, an estimated height, a `removed` → `proposed` replacement, a `modified` feature, a line wall, an `approximate` georeference variant (`manifest.approximate.json`), and a `reviewIssue`.

## 5. Lane A: pipeline design

**Stack:** Python 3.12 managed by `uv`. The machine's system Python 3.15 is too new for current geospatial wheels, so `uv` installs 3.12 automatically. Libraries: `geopandas`, `shapely`, `pyproj`, `jsonschema`, `pyyaml`, `requests`, `numpy`, plus `pdfplumber` for the optional extraction helper. Development tools: `pytest`, `hypothesis`, `ruff`. All versions are locked in `pipeline/uv.lock`.

**CLI** (`uv run --project pipeline dcviz <command>`):

| Command | Purpose |
|---|---|
| `contract-check` | Validate fixtures and every published package against the schemas |
| `fetch` | Download sources in `data/sources.yaml` into `data/raw/`, recording sha256 and retrieval time |
| `context` | Build `pipeline/build/context.json` |
| `extract-plan` (optional) | Export plan vector linework as GeoJSON in plan units |
| `georef` | Fit the similarity transform from `control-points.yaml` and report residuals |
| `package` | Write `data/published/<project>/<version>/` |
| `validate` | Check invariants 1–7 and the publication rules |

### 5.1 Sources (`data/sources.yaml`)

Each entry has `id`, `title`, `issuer`, `url`, `license`, `distributable`, `status` (`verified` \| `unverified`), `expectedSha256` (optional), and `usedFor`. Pilot candidates (Task 2.2 verifies each one):

- City of Lowell SPR plan set, Aug 2024 (DocumentCenter/View/27449). Cited and linked, never republished until rights are verified.
- From the same Lowell folder: Generator Yard Sketch, Previous Plans for Reference, Main Application, and the MassDEP air-quality application files, which may contain stack or equipment heights.
- MassGIS Building Structures (2-D) for Lowell (footprints).
- MassGIS Level 3 parcels for Lowell (anchor and control points only; owner fields dropped at load).
- Building heights: OSM `height` and `building:levels`, or Overture building heights. ODbL attribution applies. LiDAR is an optional follow-up (Task 3.7).
- Roads, rail, water, and open space: MassGIS layers, or OSM where MassGIS lacks coverage.

Google Maps, Google Earth, and Street View material in `captures/` is for human visual review only. It is never traced, sampled, committed, or published.

### 5.2 Context build

1. Clip each layer to a circle of radius 1200 m around the origin.
2. Building height priority: OSM or Overture explicit height (`estimated` unless the source documents a measurement method, in which case `derived`), then levels × 3.0 m (`estimated`), then a footprint-area class default (`estimated`, for example 7 m for footprints under 200 m²). Each building records `heightSource`.
3. Simplify footprints with a 0.3 m tolerance, preserving topology. Drop footprints smaller than 8 m².
4. Road width comes from a road-class lookup table.
5. Write `context.json`, then run `contract-check`.

### 5.3 Proposal georeferencing and curation

1. **Version first.** Task 4.1 establishes which records describe the August 2024 proposal before any feature is curated, so nothing from a different version is merged into the package (Req 12.4).
2. **Control points.** A person records at least 6 control points and at least 2 check points in `control-points.yaml`. Plan coordinates are measured on the sheet using its printed scale, or taken from the optional extraction output. State Plane coordinates come from MassGIS parcel corners or road intersections.
3. **Fit.** A similarity transform (scale, rotation, translation) is fit by least squares. Affine and higher-order fits are not used, because shear would distort official dimensions. If check-point RMSE exceeds 2 m, the person looks for bad control points. If it still exceeds 2 m, the package is published with `approximate: true` (Req 2.4).
4. **Curate.** `features.yaml` lists each proposal feature with its category, state, vertices in plan coordinates, dimension annotations from the plan (for example `13'-8" TYP`), height evidence, and source refs.
5. **Dimensions.** Official plan dimensions are checked against the transformed geometry within 0.5 m (Req 2.5).
6. **Heights.** Heights come only from sources such as DEP stack heights or equipment specifications. Otherwise they are `estimated` with a stated method, or `unknown` (Req 3.5).
7. **Discrepancies.** Conflicts with parcel geometry produce a `reviewIssue`. The feature stays where the plan puts it (Req 2.6).

## 6. Lane B: web design

**Stack:** Vite, strict TypeScript, Three.js, plain DOM with native form controls, `ajv`, `proj4`, `suncalc`, `vitest`, `fast-check`, `@playwright/test`, `@axe-core/playwright`. All versions are locked in `web/package-lock.json`.

### 6.1 Data delivery

`web/scripts/sync-data.mjs` runs before `dev`, `build`, and `test:e2e`. It copies `../data/published/**` to `web/public/data/` and `../contracts/fixtures/**` to `web/public/fixtures/`. Both destinations are ignored by Git. The production `dist/` therefore contains every published package. The active package comes from `?package=<projectId>/<version>`, falling back to the default in `web/src/config.ts`. The e2e suite runs against `vite preview` of the production build, not only the development server.

### 6.2 Modules

| Module | Responsibility | Requirements |
|---|---|---|
| `data/loader` | Fetch, validate with ajv against `contracts/*.schema.json`, and resolve sources | 1.4, 10.1 |
| `scene/renderer` | WebGLRenderer, tone mapping, anti-aliasing, hemisphere and directional lights, ground plane | 3.8 |
| `scene/style` | Palette and material tokens: warm-gray massing, cool shadows, green open space, tan roads, blue water | 3.8, 9.7 |
| `scene/builders` | Extrude polygons and widened lines. Merge context buildings into a few meshes without altering any vertex height, and keep a per-vertex `featureId` attribute for picking. Instance repeated equipment. | 3.1, 3.10, 11.4 |
| `scene/proposal` | Proposal state and confidence treatments | 3.3–3.6, 8.4 |
| `camera/` | Aerial orbit with a minimum height and distance; ground viewpoints as fixed eye positions (1.6 m) with look-around only, so the camera can never enter a structure or go underground | 3.9, 5.1, 5.6, 9.4 |
| `compare/` | One set of geometry and materials. Three.js layers mark current and proposed membership. Split mode renders the same scene twice with scissor rectangles and different layer masks. | 4.1–4.4 |
| `sun/` | Convert the selected Lowell wall-clock time to an instant with `America/New_York` rules (including DST), then run suncalc. The shadow light covers about 400 m around the site. | 6.1–6.5 |
| `inspect/` | Raycast picking by `featureId`, and a provenance panel | 8.1–8.3, 8.5 |
| `inventory/` | Accessible feature table | 9.3 |
| `export/` | See section 6.6 | 7.1–7.5 |
| `lookup/` | Geocoder adapter. Default `none`; a real provider is an open decision. | 5.3–5.5 |
| `ui/` | Controls, live region, errors, responsive layout | 9, 10 |

### 6.3 Visual treatments (never color alone)

| Meaning | Treatment, full detail | Treatment, reduced detail |
|---|---|---|
| Context building | Solid warm-gray massing, soft shadows | Same, no shadows |
| Proposal feature | Accent material, thin dark outline, focusable label | Same |
| Height `official` or `derived` | Solid fill, solid outline | Same |
| Height `estimated` | Diagonal-hatch texture, dashed outline, "Estimated" badge; shadow labeled estimated | Dashed outline and badge (no texture) |
| Height `unknown` | Flat footprint with a "?" marker, never a realistic height; no shadow | Same |
| Removed (current mode) | Normal; hidden in proposed mode | Same |
| Approximate georeference | Persistent "Approximate placement" banner | Same |
| Terrain | Legend note: "Ground shown flat; terrain not modeled" | Same |

### 6.4 Comparison and state

One state object holds `{mode, camera, date, time, visibleCategories, selectedFeature, detailLevel, viewpointId}`. A mode change touches only layer masks, never the camera, date, or time (Req 4.3). The URL hash serializes everything except lookup queries (Req 5.5, 7.3).

### 6.5 Performance

- Context buildings use fewer than 50 draw calls in total.
- Shadows are cast only by site features and nearby context.
- Reduced-detail mode disables shadows, lowers the pixel ratio, and drops textures but keeps outlines and markers (Req 11.6, 8.4).
- A performance trace reports load time and median FPS over 30 s (Req 11.2, 11.3).

### 6.6 Export

PNG export renders to an offscreen target of up to 2400 × 1600 px. It waits for `document.fonts.ready`, composites a 2-D canvas overlay (title, version and date, mode, viewpoint type, legend, wrapped attribution, confidence indicator, URL), and calls `toBlob`. WebGL context loss or a size failure keeps the live scene and shows a retry message (Req 7.5). The user's address is never drawn unless the user opts in.

### 6.7 Resilience

- Load order: manifest, proposal, context, each with visible progress (Req 10.1).
- Context fails: render the proposal on a labeled plain ground plane (Req 10.2).
- No WebGL: show the static image `web/public/fallback/<project>.png` plus the inventory (Req 10.5). Task 9.3 creates a fixture image; Task 10.4 replaces it with Lowell.
- Lookup unavailable: curated viewpoints keep working (Req 5.4, 10.3).
- The MVP has no detailed `.glb` assets, so Requirement 10.4 has no trigger yet. If assets are added later, extruded geometry is the fallback.

## 7. Accessibility

- Native, labeled controls: radio group for mode, checkboxes for categories, native date and time inputs (Req 9.2).
- Keyboard: arrows orbit, `+`/`−` zoom, `[`/`]` cycle viewpoints, and Tab moves through the controls and the inventory (Req 9.1).
- An `aria-live` region announces mode changes, loading, and errors.
- `prefers-reduced-motion` makes viewpoint changes instant cuts (Req 9.4).
- Layout works from 320 px. On narrow screens the controls become a bottom sheet (Req 9.6).
- axe-core in e2e tests must report zero serious or critical violations (Req 9.7).

## 8. Privacy and rights

- The pipeline drops owner, abutter, and contact fields at load, and `validate` enforces the blocklist (Req 1.6, 12.6).
- Address queries go only to the configured provider and never into state, the URL, or exports unless the user opts in (Req 5.5, 7.4).
- Sources with `distributable: false` are cited and linked, never copied into `data/published/` or `web/public/` (Req 8.3).
- No company logos or plan-sheet artwork appear in the app (Req 8.7).

## 9. Testing strategy

| Level | Lane A | Lane B |
|---|---|---|
| Unit | pytest per pipeline stage | vitest per module |
| Property (required) | Similarity fit recovers known transforms within 1 mm; dimensions survive transform within 0.5 m; State Plane ↔ local round trip; any single-invariant violation is rejected by `validate` | Extruded volume = footprint area × height within 0.1 %; current/proposed membership satisfies invariant 4; a mode change leaves camera and time unchanged; lat/lon round trip within 1 cm |
| Property (optional) | Context clipping and simplification stay valid (3.5) | — |
| Contract | `dcviz contract-check` on fixtures and every published package | ajv tests over the same files |
| End to end | — | Playwright on the production build: load, modes, keyboard-only path, export, failure fallbacks, axe |

`scripts/check-all.sh` runs every check whose toolchain is installed and exits non-zero if neither lane's validator could run. It never reports success without running a contract validation.

## 10. Parallel development model

### 10.1 Lanes

| Lane | Person | Tasks |
|---|---|---|
| A: data pipeline | Ajin Frank Justin | 1–5 |
| B: web app | Sushma (`sushmar`) | 6–9, then leads 10 |
| Release | Both, human-gated | 11 |

The protocol in `.kiro/steering/parallel-development.md` defines lane detection, setup, task selection, commits, and handoffs.

### 10.2 Handoffs

| Handoff | Produced by | Unblocks |
|---|---|---|
| H1: contracts, fixture, and contract check (Task 1.3) | Lane A | Lane B 6.3 and everything after it |
| H2: Lowell context package `0.1.0` (Task 3.6) | Lane A | Integration 10.1 |
| H3: Lowell proposal package `0.2.0` (Task 5.3) | Lane A | Integration 10.2 |

Lane B's 6.1 and 6.2 depend on nothing. Lane A should finish 1.1, 2.1, 1.2, and 1.3 first, because H1 unblocks Lane B.

### 10.3 Within-lane parallelism

Each task lists `Depends on:` and `Files:`. When several of a lane's tasks are ready and their `Files:` lists don't overlap, the agent may run them concurrently in sub-agents. Kiro's "run all tasks" must not be used, because it would also run the other lane's tasks.

### 10.4 Git workflow

Both lanes commit to `main`, one commit per task, with the prefix `lane-a(3.1): …` or `lane-b(7.2): …`. Before each push the agent runs `git pull --rebase origin main` and re-runs checks if anything came in. Force pushes are never used. Lane A's checkboxes and Lane B's checkboxes sit in different parts of `tasks.md`, so rebases on that file merge cleanly. A conflict in a file the lane does not own stops the agent.

## 11. Decisions and rejected options

| Decision | Chosen | Rejected and why |
|---|---|---|
| Renderer | Three.js in a local metric frame | MapLibre `fill-extrusion`: limited lighting and shadows, cannot reach the reference look. CesiumJS: heavier than a 1.2 km pilot needs. |
| Basemap imagery | None in the primary view | Aerial imagery adds licensing and availability risk and clashes with the stylized look. Possible later as an option. |
| 3D authoring | Procedural extrusion from data | Blender-first is slower and harder to tie to sources. `.glb` support is deferred. |
| Terrain | Flat datum for the MVP | Per-building DEM elevations without a terrain mesh would float or sink buildings. A terrain mesh is a later, contract-compatible addition. |
| Building heights | OSM or Overture heights plus labeled defaults | LiDAR nDSM: more accurate but heavy processing for a hackathon. Kept as optional Task 3.7. |
| Georeferencing | Similarity transform only | Affine fallback: shear can hide bad control points and distort official dimensions. |
| Plan geometry | Manual curation from measured plan coordinates; `pdfplumber` extraction optional | Fully automatic CAD-to-3D: unreliable. PyMuPDF: AGPL license. |
| Ground camera | Fixed eye positions with look-around | Free walking with collision: complex, and a risk to accessibility and the 30 FPS target. |
| Point placement | Allowed only on public roads and open space from the package | Any point: the requirement limits viewpoints to publicly accessible or valid areas. |
| UI framework | Plain TypeScript and DOM | React or Vue: unnecessary for about 10 controls. |
| Task status | One `tasks.md` with lane sections, checkbox edits exempt from `Files:` | Per-lane task files: would break Kiro's task view for the Spec. |
| Branching | Trunk-based on `main` | Long-lived lane branches: late, large merges. |
| Geocoding | Adapter, default `none` | Choosing a provider now: privacy, cost, and terms unresolved. |

## 12. Advisor review (GPT-5.6 Sol, 2026-10-24)

GPT-5.6 Sol reviewed the first draft of the requirements, design, tasks, and protocol without tool access. Its findings and the decisions taken:

| # | Finding | Decision |
|---|---|---|
| 1 | Production build would not include published packages | **Accepted.** Added `sync-data` (6.1) and e2e against `vite preview`. |
| 2 | `tasks.md` edits conflicted with the `Files:` rule | **Accepted in part.** Checkbox edits are exempt. Per-lane task files rejected (section 11). |
| 3 | Exact `user.name` lane detection is brittle | **Accepted.** Case-insensitive name match plus a one-line override in the README. |
| 4 | No early bootstrap for `.gitignore` and README | **Accepted.** Both were written with this Spec, before development starts. |
| 5 | Contract check could pass without validating | **Accepted.** One locked validator per lane; the script fails if none ran. 1.3 now depends on 2.1. |
| 6 | Version research came after feature curation | **Accepted.** It is now Task 4.1, and curation depends on it. |
| 7 | 6.3 should depend on 1.3, not 1.2 | **Accepted.** |
| 8 | No-WebGL image created after the test that needs it | **Accepted.** 9.3 makes a fixture image; 10.4 replaces it. |
| 9 | `.glb` fallback with no `.glb` loader | **Accepted.** `.glb` deferred; Req 10.4 noted as having no trigger. |
| 10 | Point placement did not check public access | **Accepted.** Placement limited to public roads and open space. |
| 11 | 11.2 dependencies incomplete; 10.3 allowed missing targets | **Accepted.** 11.2 depends on 10.3, 10.4, and 11.1; 10.3 must meet the targets. |
| 12 | Parent task rows had no semantics | **Accepted.** The protocol skips parent rows and checks them when all sub-tasks are done. |
| 13 | Scope too large for a hackathon | **Accepted in part.** Deferred: LiDAR, plan extraction, free walking, `.glb`, terrain, context property tests. Kept required: the core property tests, which protect the parts most likely to break silently. |
| 14 | Affine fallback can distort dimensions | **Accepted.** Similarity only. |
| 15 | Georeference schema incomplete | **Accepted.** Expanded in section 4.2. |
| 16 | Terrain and elevations inconsistent | **Accepted.** Flat-datum MVP. |
| 17 | Height-band merging could quantize heights | **Accepted.** Merging never changes vertex heights. |
| 18 | Reduced detail could drop non-color cues | **Accepted.** Outlines and markers stay. |
| 19 | Split view could double memory | **Accepted.** One scene, layer masks, scissor rendering. |
| 20 | DST handling for shadows | **Accepted.** Explicit time-zone conversion and DST-boundary tests. |
| 21 | Export strategy unspecified | **Accepted.** Section 6.6. |
