# Lowell context-building height sources

## Decision status

Task 3.2 implements and measures the height approach, but it is **not approved for
publication**. A person must confirm the approach and license obligations before task 3.6
publishes a Lowell package.

The reproducible 0.1.0 pipeline selects the cached OpenStreetMap (OSM) observations, then
uses explicit visual-massing defaults for unmatched MassGIS footprints. Overture was measured
separately but is not selected because the repository has no bounded Overture cache or source
manifest entry. The pipeline does not make a live DuckDB or S3 request.

## Inputs and reproducibility

### MassGIS target footprints

- Manifest source: `massgis-buildings-lowell-160`
- Cached file: `data/raw/massgis-buildings-lowell-160.zip`
- Retrieved: `2026-10-24T21:33:18.864858Z`
- SHA-256: `ce814b38e4c885e7b888f1c69d60a044c37b820013af2dd1db3a12f380ea5825`
- Task 3.1 output used for measurement: 3,319 Polygon rows in EPSG:26986, clipped to
  the 1.2 km circle, simplified at 0.3 m, and filtered to at least 8 m².

### Selected OSM/Overpass observations

- Manifest source: `osm-building-heights-pilot`
- Cached file: `data/raw/osm-building-heights-pilot.json`
- OSM base timestamp in the response: `2026-10-24T21:32:51Z`
- Retrieved: `2026-10-24T21:33:18.864858Z`
- SHA-256: `10cf6bbc5b5cbbd9f42315170a9b976dd62feeba72be7147f2bfde993160bae8`
- Raw response: 18 closed ways in the bounding box. Thirteen intersect the 1.2 km circle;
  all 13 contain a valid observation and match 11 unique MassGIS buildings.
- Explicit `height` tags: none in this cache. The 13 selected observations use strict
  `building:levels` values from the set 1, 2, 2.5, 4, and 5.

OSM data is available under the Open Data Commons Open Database License (ODbL). The
[OSM copyright and license page](https://www.openstreetmap.org/copyright) requires OpenStreetMap
contributor attribution and describes the ODbL share-alike obligation for adapted databases.
The public product and exports must carry the required attribution. Before publication, the
team must confirm whether the combined and distributed context database is an adapted database
and apply the corresponding ODbL notice and share-alike terms.

The parser retains only the OSM element ID, polygon geometry, `height`, and
`building:levels`. It never carries names, addresses, websites, contributor/user metadata,
source tags, or unrelated tags into the enriched building output.

### Measured but deferred Overture input

The separate measurement used Overture Maps release **2026-10-21.0**, the
[building schema](https://docs.overturemaps.org/schema/reference/buildings/building/), and the
[buildings guide](https://docs.overturemaps.org/guides/buildings/). The Overture buildings data
is distributed under ODbL; the [Overture attribution guidance](https://docs.overturemaps.org/attribution/)
describes attribution and license handling. Publication would need to preserve the applicable
ODbL attribution and share-alike obligations.

Measured Overture results:

| Stage | Count |
|---|---:|
| Buildings in the bounding box | 4,102 |
| Bounding-box buildings with vertical fields | 3,679 |
| Vertical records intersecting the 1.2 km circle | 3,023 |
| Circle records with a height | 3,023 |
| Accepted geometry-match pairs | 2,928 |
| Unique accepted Overture records | 2,927 |
| Unique MassGIS targets | 2,925 (88.129% potential coverage) |
| Ambiguous Overture records | 1 |
| MassGIS targets with multiple source records | 3 |
| Target conflicts greater than 0.5 m | 2 |

Height-property source records inside the circle were 1,885 Microsoft ML Buildings,
1,133 USGS Lidar, and 5 unspecified. These counts describe measured coverage; they are not
zero and they are not part of the selected 0.1.0 output.

Overture is deferred because no bounded, versioned Overture extract exists in `data/raw/` and
no corresponding entry exists in `data/sources.yaml`. Requiring live DuckDB/S3 access would add
a network and service dependency during judging, outside task 3.2's file scope. The code accepts
optional normalized Overture candidates without a new dependency: USGS Lidar heights are
`derived`, while Microsoft ML and unspecified heights are `estimated`. A later task must add a
bounded source entry, cache, hash, retrieval record, license review, and synthetic parser tests
before enabling Overture in the reproducible path.

## Parsing and spatial matching

1. The OSM loader accepts closed way polygons and explicitly rejects relations. Correctly
   reconstructing relation member roles is not attempted.
2. WGS84 coordinates are read in longitude/latitude order, transformed to EPSG:26986, and
   retained when the polygon intersects the 1.2 km circle.
3. Explicit heights accept positive finite metres (`12`, `12 m`) and feet (`40 ft`, `40'`).
   Ranges, lists, descriptive units, malformed text, zero, negative, and non-finite values are
   rejected. Feet use exactly 0.3048 metres per foot.
4. `building:levels` accepts only a positive finite decimal. The estimate is levels × 3.0 m.
5. Matching uses geometry only. A candidate must have overlap coefficient
   `intersection area / min(candidate area, target area) >= 0.75` and centroid distance
   `<= 10 m`.
6. The unique best eligible target is the greatest overlap, then the shortest centroid
   distance. An exact tie is ambiguous and is ignored.
7. Multiple records may map to one MassGIS target only when the selected-tier heights agree
   within 0.5 m. Agreeing values are averaged. A conflict is reported and falls through to the
   next priority tier rather than silently selecting one record.
8. Equal-tier OSM and Overture explicit heights combine only when their full range is no more
   than 0.5 m. The combined status is conservatively `estimated` if any contributing record is
   estimated. Otherwise it is `derived`.

## Priority, statuses, and exact `heightSource` values

The implemented priority is:

1. OSM or optional Overture explicit height.
2. OSM `building:levels × 3.0 m`.
3. A footprint-area visual-massing default.

Explicit OSM values remain `estimated` because the selected cache contains no
measurement-method evidence. The exact single-source labels are:

| Evidence | `heightStatus` | Exact `heightSource` |
|---|---|---|
| OSM explicit | `estimated` | `OpenStreetMap explicit height` |
| OSM levels | `estimated` | `OpenStreetMap building:levels × 3.0 m` |
| Overture USGS Lidar | `derived` | `Overture explicit height (USGS Lidar)` |
| Overture Microsoft ML | `estimated` | `Overture explicit height (Microsoft ML Buildings)` |
| Overture unspecified | `estimated` | `Overture explicit height (source unspecified)` |

When agreeing explicit records with different labels combine, `heightSource` is
`Agreeing explicit heights: ` followed by the sorted exact labels joined with ` + `.

The area defaults are explicit **visual-massing assumptions**, not measured, official, or
site-specific heights:

| Simplified footprint area | Height | `heightStatus` | Exact `heightSource` |
|---|---:|---|---|
| `< 200 m²` | 7 m | `estimated` | `Visual-massing area default (<200 m²): 7 m` |
| `200 to < 1000 m²` | 9 m | `estimated` | `Visual-massing area default (200–<1000 m²): 9 m` |
| `>= 1000 m²` | 12 m | `estimated` | `Visual-massing area default (≥1000 m²): 12 m` |

## Selected OSM-only output coverage

The denominator is all 3,319 task 3.1 MassGIS context buildings. Counts group the final output
by the exact `heightSource` value and sum to every building.

| Exact `heightSource` | Buildings | Coverage |
|---|---:|---:|
| `OpenStreetMap building:levels × 3.0 m` | 11 | 0.331% |
| `Visual-massing area default (<200 m²): 7 m` | 2,828 | 85.206% |
| `Visual-massing area default (200–<1000 m²): 9 m` | 421 | 12.685% |
| `Visual-massing area default (≥1000 m²): 12 m` | 59 | 1.778% |
| **Total** | **3,319** | **100.000%** |

The 13 valid OSM observations produce 11 buildings because two pairs of OSM polygons map to
two larger MassGIS footprints. Each pair has agreeing level values, so the many-to-one rule
accepts them. The run reports no ambiguous OSM candidate, unmatched candidate, or target
conflict.

## Limitations and privacy

- The selected output has no measured or official heights. Eleven heights derive from OSM
  level counts but are still labeled estimated; 3,308 are area-class assumptions.
- A 3.0 m floor height does not capture industrial clear heights, mechanical penthouses,
  roof form, grade changes, or partial floors.
- Area classes preserve broad neighborhood massing but can be wrong for individual buildings.
  They must receive the estimated visual treatment and must not be described as observed.
- Matching compares independently maintained geometries. Renovations, footprint splits,
  generalized outlines, and source age can create false matches or misses.
- The ground datum remains flat. Task 3.4 adds `baseElevationM`; task 3.2 does not infer terrain.
- The output contains exactly `id`, `heightM`, `heightStatus`, `heightSource`, and geometry.
  It excludes OSM names, addresses, websites, users, unrelated tags, and MassGIS assessor or
  ownership data.

## Human decision required before task 3.6

Please approve or revise all of the following before publication:

- selecting cached OSM-only evidence for 0.1.0 and deferring Overture;
- OSM ODbL attribution, adapted-database analysis, and share-alike obligations;
- the 0.75 overlap, 10 m centroid, unique-best, 0.5 m agreement, and conflict-fallback rules;
- the 7/9/12 m estimated visual-massing defaults and their area boundaries; and
- the plan to add a bounded, hashed, reviewed Overture source before enabling its measured
  88.129% potential coverage.
