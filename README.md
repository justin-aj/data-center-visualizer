# Data Center Visualizer

Data Center Visualizer is a civic web app that turns public development records into a to-scale, stylized 3D model of the surrounding neighborhood.

The current Lowell pilot is a **context-only scene** covering 1.2 km around 2 Prince Avenue / 1 Markley Way. It includes buildings, roads, rail, water, and public open space. It does not yet include proposal geometry or a current-versus-proposed Lowell comparison. Those features remain deferred rather than using unverified geometry.

The primary output is the interactive 3D scene.

## Status

Built with Kiro Spec-driven development (requirements first):

- [Requirements](.kiro/specs/data-center-visualizer/requirements.md): approved
- [Design](.kiro/specs/data-center-visualizer/design.md): approved, after review by GPT-5.6 Sol as advisor
- [Tasks](.kiro/specs/data-center-visualizer/tasks.md): approved for implementation, in two parallel lanes

A runnable Three.js app and the validated `lowell-markley/0.1.0` context package exist. The Lowell package is intentionally marked `context-only`; proposal georeferencing and feature curation are unfinished.

## Team and lanes

| Lane | Person | Builds |
|---|---|---|
| A: data pipeline | Ajin | Python pipeline that produces validated proposal packages (`pipeline/`, `data/`, `contracts/`) |
| B: web app | Sushma | Three.js app that renders any valid package (`web/`) |

The two lanes share one contract in `contracts/`, so each can work without waiting for the other's code.

## Getting started

### Prerequisites

- [Kiro CLI](https://kiro.dev)
- Git
- Lane A: [`uv`](https://docs.astral.sh/uv/) (installs Python 3.12 automatically)
- Lane B: Node.js 20 or newer

### Start developing

```bash
git clone https://github.com/justin-aj/data-center-visualizer.git
cd data-center-visualizer
kiro-cli
```

Trust the workspace when asked, then type:

```text
start development
```

Your agent picks your lane from `git config user.name`, installs dependencies, finds the next ready task in `tasks.md`, builds and tests it, then commits and pushes. The full procedure is in [`.kiro/steering/parallel-development.md`](.kiro/steering/parallel-development.md).

If your Git name contains neither "ajin" nor "sushma", the agent asks once which lane you are on. You can also set it yourself:

```bash
mkdir -p .kiro/settings && echo B > .kiro/settings/lane   # or A
```

Say **"continue development"** or **"next task"** to keep going in a later session.

### Run the web demo

```bash
npm ci --prefix web
npm --prefix web run dev -- --host 127.0.0.1
```

For a production build and local preview:

```bash
npm --prefix web run build
npm --prefix web run preview -- --host 127.0.0.1 --port 4175
```

Before the first end-to-end run, install the browsers:

```bash
npx --prefix web playwright install chromium webkit
npm --prefix web run test:e2e
```

### Run the data pipeline

```bash
uv sync --project pipeline
uv run --project pipeline dcviz contract-check
uv run --project pipeline dcviz context
```

`dcviz fetch` downloads source material into ignored `data/raw/`; it is not required to view the tracked H2 package.

### Run all installed checks

```bash
scripts/check-all.sh
```

The script runs contract validation and Lane A checks when `uv` is installed. It also runs Lane B lint and unit tests when `web/node_modules` exists.

## Accuracy and neutrality

Published values identify their source and whether they are derived or estimated. In H2, most context-building heights and all road/rail widths are explicit visualization estimates. Ground is shown flat. The package identifies mixed source vintages and states that proposal geometry and georeferencing are absent.

The app does not predict health effects, decide legal compliance, or score a project.

## Data and rights

- Source documents are downloaded into `data/raw/`, which Git ignores. The source list, licenses, and redistribution status are in `data/sources.yaml`.
- The tracked H2 package includes only sources marked distributable. Required MassGIS and OpenStreetMap attribution is stored in its `manifest.json`.
- Lowell proposal PDFs are citation-only and are not included in `data/published/` or the web build.
- Reference screenshots of Google Maps and Google Earth in `captures/` are for human visual comparison only. They are ignored by Git and never used as data.
- Owner names and other personal information are removed from all published data.

## Current limitations

- `lowell-markley/0.1.0` contains neighborhood context only.
- The August 9, 2024 proposal has not been georeferenced or modeled.
- Context layers have different source vintages.
- Terrain and site grade are unknown; the scene uses a flat ground plane.
- Most context-building heights use area-based visual-massing estimates.
- Deployment, final licensing documents, demonstration video, submission dates, and submission-form details remain unresolved.
