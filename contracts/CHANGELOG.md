# Contract changelog

All notable changes to the Data Center Visualizer package contract are recorded here.

## 1.0.0 - 2026-10-24

- Define Draft 2020-12 schemas for `manifest.json`, `proposal.json`, and `context.json`.
- Require proposal identity, dates, source provenance, georeferencing details, viewpoints, review records, attribution, and deliberately excluded fields.
- Define physical proposal categories and current/proposed transition states.
- Enforce that unknown proposal heights use null values and that null height values are never presented as known.
- Define context layers for buildings, roads, railways, water, and open space without owner, assessor, address, or prohibited analytical fields.
