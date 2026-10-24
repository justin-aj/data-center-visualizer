# Contract changelog

All notable changes to the Data Center Visualizer package contract are recorded here.

## 1.1.0 - 2026-10-24

- Add the optional `packageKind` manifest field with `proposal` and `context-only` values.
- Treat an omitted `packageKind` as `proposal` and continue to require proposal georeferencing.
- Permit `context-only` packages to omit proposal georeferencing and require them to omit the `georeference` field.
- Preserve full compatibility for 1.0.0 manifests, which require `georeference` and forbid `packageKind`.
- Keep all three package files required for every package kind.

## 1.0.0 - 2026-10-24

- Define Draft 2020-12 schemas for `manifest.json`, `proposal.json`, and `context.json`.
- Require proposal identity, dates, source provenance, georeferencing details, viewpoints, review records, attribution, and deliberately excluded fields.
- Define physical proposal categories and current/proposed transition states.
- Enforce that unknown proposal heights use null values and that null height values are never presented as known.
- Define context layers for buildings, roads, railways, water, and open space without owner, assessor, address, or prohibited analytical fields.
