# Data Center Visualizer

Data Center Visualizer is a civic web app that turns public development plans into a to-scale, stylized 3D model of the real neighborhood. Massachusetts residents can switch between current and proposed conditions and view a project from nearby public streets.

The output is the interactive 3D scene itself, not a report.

**Pilot:** the Markley data center at 2 Prince Avenue / 1 Markley Way, Lowell, MA, using the City of Lowell's August 2024 site-plan set.

## Status

Built with Kiro Spec-driven development (requirements first):

- [Requirements](.kiro/specs/data-center-visualizer/requirements.md): approved
- [Design](.kiro/specs/data-center-visualizer/design.md): approved, after review by GPT-5.6 Sol as advisor
- [Tasks](.kiro/specs/data-center-visualizer/tasks.md): approved for implementation, in two parallel lanes

No runnable app exists yet.

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
git clone https://github.com/justin-aj/lotlens.git
cd lotlens
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

### Running checks by hand

```bash
scripts/check-all.sh          # contracts plus whichever lanes are installed
```

Lane-specific commands appear here as their scaffolding tasks are completed (tasks 2.1 and 6.1).

## Accuracy and neutrality

Every modeled feature shows whether its position, footprint, and height are official, derived, estimated, or unknown. The app does not predict health effects, decide legal compliance, or score a project.

## Data and rights

- Source documents are downloaded into `data/raw/`, which Git ignores. The source list, licenses, and redistribution status are in `data/sources.yaml`.
- Reference screenshots of Google Maps and Google Earth in `captures/` are for human visual comparison only. They are ignored by Git and never used as data.
- Owner names and other personal information are removed from all published data.
