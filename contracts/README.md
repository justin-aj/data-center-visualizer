# Data Center Visualizer contracts

Contract versions `1.0.0` and `1.1.0` define the three JSON documents in each published package:

- `manifest.json` and `proposal.json` validate against `proposal-package.schema.json`. The schema root accepts either document; named definitions are available at `#/$defs/manifest` and `#/$defs/proposal`.
- `context.json` validates against `context-scene.schema.json`.

Both schemas use [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/schema).

## Package layout

```text
data/published/<projectId>/<packageVersion>/
├── manifest.json
├── proposal.json
└── context.json
```

Published package directories are immutable. Any change to a published value requires a new semantic package version.

## Package kinds

Version 1.1.0 adds the optional manifest field `packageKind`. Its accepted values are `proposal` and `context-only`. An omitted `packageKind` has proposal semantics, so both an explicit `proposal` package and a package with no kind must include `georeference`. A `context-only` package must omit `georeference`; it does not weaken or bypass the georeferencing requirement for proposal data.

Version 1.0.0 manifests remain fully compatible. They must include `georeference` and must not include `packageKind`. The package layout is unchanged for every version and kind: `manifest.json`, `proposal.json`, and `context.json` are all required. A context-only package uses a valid empty proposal document (`{"features": []}`) when it has no proposal features.

## Contract guarantees

The schemas require the metadata, provenance, applicable georeferencing, confidence, geometry, and review fields specified by the approved design. Proposal heights enforce this invariant: an unknown height has a null value, and only an unknown height may have a null value.

The proposal category enum is limited to physical site features. The context schema is limited to buildings, roads, railways, water, and open space. Neither schema defines noise, air-dispersion, emissions, health, legal-compliance, or utility-capacity layers.

Checks that require relationships between files or geometric computation remain the responsibility of `dcviz contract-check`, including source-reference resolution, replacement-reference resolution, polygon validity, coordinate bounds, and the PII blocklist.

## Changing the contract

Within a major version, changes must be additive and optional. Every contract change must:

1. bump `schemaVersion`,
2. update the synthetic fixture,
3. add a dated entry to `CHANGELOG.md`, and
4. use a commit whose subject starts with `contract:`.

Breaking changes require agreement from both development lanes and must not land while either lane is working against the previous version.
