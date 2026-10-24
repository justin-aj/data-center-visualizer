# Lowell proposal-version research

**Status:** Prepared for human approval on 2026-10-24.  
**Decision proposed:** Treat the August 9, 2024 civil plan as a separate 19-generator proposal phase. Do not merge the April–July 2025 application and approval for a 27-generator phase into the 2024 package.

## Scope decision for `lowell-markley` 2024

### In scope

- **Horizontal geometry and feature state:** only the City-hosted August 9, 2024 Stantec civil drawing set, `lowell-spr-plan-2024-08-09`, specifically the identified sheets C-000, C-001, C-100, C-200, C-300, C-400, and L-100.
- **Administrative metadata:** the City-hosted 2024 Main Application may be cited for the local Site Plan Review filing, but not as geometry evidence.
- **Historical baseline checks:** older plans may be consulted only to identify a specifically dated prior condition. They must not supply undated geometry or be merged into the proposal.

### Out of scope unless a later human concordance explicitly approves a use

- The June–August 2024 VHB air-application sequence may be consulted for comparison, but it must not supply geometry, height, or feature state until each equipment ID is mapped to an August 9 civil-plan feature and the relationship is recorded.
- The Generator Yard Sketch remains out of scope because its `3 existing / 12 approved-under-construction / 4 new-request` partition does not directly match the status partition in the June–August air papers.
- The April 28, 2025 application, July 3, 2025 approval NE-25-002, March 27, 2026 MassDEP final decision, later amendments or enforcement records, and litigation records belong to a separate proposal version.

This scope deliberately favors omission over a realistic-looking but cross-version model. If the 2024 civil sheets do not establish a height, task 4.4 must mark it `estimated` with a method or `unknown`; it must not import a 2025 value.

## Finding

The 2024 and 2025 records describe different proposal stages.

- The reviewed 2024 air-application sequence describes **19 emergency generators** and **16 cooling towers**. Its sequence consists of June 2024 material, a June 27 submission described in the August response, an August 5 revision, and an August 8 response. The August 9 Stantec civil set is close in time and appears to depict the same general 19-generator site phase, but no reviewed document explicitly cross-references Stantec job `210400139` and VHB project `14497`.
- MassDEP's December 23, 2025 Recommended Final Decision identifies NE-25-002 as the July 3, 2025 approval of **eight additional generators**, bringing the facility total to **27**, with 16 cooling towers supporting the expanded infrastructure.
- The 2025 administrative record also identifies a separate March 25, 2025 approval, NE-24-014, that brought the approved generator total to 19 before the next eight-generator application. This supports treating the 19-generator and 27-generator stages as distinct versions.
- MassDEP's March 27, 2026 Final Decision affirmed NE-25-002. That decision concerns the later permit and does not retroactively make its geometry part of the August 2024 civil plan.

Matching facility name, location, or cooling-tower total does not make the records one version. The changed generator total and separate approval identifiers are consequential differences.

## 2024 source review

### August 9 civil set

The Stantec set is titled *Drawing Set for Site Plan Review: The Markley Group Data Center, 1 Markley Way, Lowell, MA*, job `210400139`. The cover is issued August 9, 2024. Sheet-level dates vary: C-001 references a July 17 Notice of Intent and L-100 references a July 22 Site Plan Review issue. C-000 and C-100 show the equipment arrangement, proposed pads, generators, cooling equipment, transformer yard, retaining walls, gates, fences, water-treatment building, paving, and existing Building #1. C-001 identifies removals and retained items.

The package must cite the individual sheet and its title-block date. It must not flatten every sheet date to August 9.

### City-folder air records

The City-hosted aggregate air record contains documents dated June–August 2024 even though some PDF container metadata and City posting activity occurred in October. Container timestamps are not treated as official issue dates.

The internally linked sequence describes 19 generators and 16 cooling towers. These documents are applicant or consultant submissions, not City or MassDEP findings merely because the City hosts them. They remain comparison evidence until a human maps their equipment IDs to the civil sheets.

### Generator Yard Sketch discrepancy

The sketch totals 19 generators but labels them as three existing, twelve approved and under construction, and four new requests. That status grouping differs from the reviewed 2024 air sequence. The sketch has no verified printed issue date in the current review. Its geometry and status labels must not be merged into the August 9 plan package without reconciliation.

## Required feature-level checks before using any supporting record

For every proposed feature, compare and record:

1. Equipment ID, count, make/model, capacity, and north/south or building-side location.
2. Existing, previously approved, under-construction, proposed, removed, or replacement state.
3. Pad, enclosure, spacing, stack, wall, fence, gate, paving, and building dimensions.
4. Printed issue/revision date and any supersession statement.
5. Stantec job, VHB project, MassDEP file, and approval identifiers.
6. Whether the statement is an applicant claim, consultant analysis, government finding or condition, allegation, or model estimate.

Third-party aerial figures in application records must not be traced, sampled, copied, or republished.

## Source register

All City PDFs below remain `distributable: false`. They are cited and reviewed locally but are not copied into published packages or the web application.

| Source ID | Document and role | Date / sheet or page | Public URL | Retrieved | SHA-256 |
|---|---|---|---|---|---|
| `lowell-spr-plan-2024-08-09` | Stantec civil drawing set; applicant plan and primary 2024 geometry source | Cover issued 2024-08-09; cite C-000 through L-100 individually | https://www.lowellma.gov/DocumentCenter/View/27449 | 2026-10-24 | `0de9b7065db73c1986bfb0f97185030a7620c871c2253eb06eea73e0cfdf5a58` |
| `lowell-previous-plans-2024` | City-hosted historical plans; baseline comparison only | Specific sheets span 2015–2023 | https://www.lowellma.gov/DocumentCenter/View/27447 | 2026-10-24 | `fbcf08751e74b8f23186db7cd7f6517050d0b5866f5ce9c9acc4ea7334ef3061` |
| `lowell-main-application-2024` | Applicant local land-use application; administrative metadata | PDF pp. 1–2; printed filing date unresolved | https://www.lowellma.gov/DocumentCenter/View/27450 | 2026-10-24 | `e51eaf740aeeb5428340c43dcd37812950bd694ef6c3a3c1d724d90a470288eb` |
| `lowell-generator-emissions-memo-2024` | VHB applicant-consultant memo; prior approval context | 2024-07-23, project 14497, PDF p. 1 | https://www.lowellma.gov/DocumentCenter/View/27451 | 2026-10-24 | `53c45fb29c9dfc4b9e8a33ade06be4fbcdb256307d687d4339f61b7eb78c42df` |
| `lowell-dep-air-application-files-2024` | VHB/Markley applicant package; comparison evidence | Fact sheet pp. 1–2; protocol pp. 8–11; equipment table pp. 59–60 | https://www.lowellma.gov/DocumentCenter/View/28306 | 2026-10-24 | `32e47a831827e0193dc1067e722f9bbeb487cd24d126692c6e217b7ca999f246` |
| `lowell-dep-potential-to-emit-revised-2024` | VHB applicant revision; comparison evidence only | 2024-08-05, project 14497.08 | https://www.lowellma.gov/DocumentCenter/View/28307 | 2026-10-24 | `ae62a1e3ac29cee584040a61fb4f6381fe0aa583eb14e9504b5b80d424765e68` |
| `lowell-dep-comments-response-2024` | VHB applicant response to MassDEP comments | 2024-08-08; submission chronology p. 1; equipment discussion pp. 7–9 and 18 | https://www.lowellma.gov/DocumentCenter/View/28308 | 2026-10-24 | `325c8d520f17fe51c37e775a6da2ad07bbd7280f45c5d2b96d4f49eb81acbde0` |
| `lowell-generator-yard-sketch-2024` | Applicant sketch with unresolved date/status relationship | Sheet 1; issue date unresolved | https://www.lowellma.gov/DocumentCenter/View/28351 | 2026-10-24 | `ac02566f9745c08e09c7eae1ae1fa1f3d15efe64cc729e4daa83a7c8506cbf94` |

### Later official and proceeding records

| Record | Role | Relevant finding | Public URL | Retrieved | SHA-256 |
|---|---|---|---|---|---|
| MassDEP Recommended Final Decision, OADR 2025-022 | Government administrative decision | Dated 2025-12-23; identifies NE-25-002, July 3 approval, eight additional generators, total 27, and 16 cooling towers | https://www.mass.gov/doc/markley-group-llc-recommended-final-decision-2025-022/download | 2026-10-24 | `e6cfd6a633fb84917bf6d60bfe3422a9440b3a43f538c9eaf5bb72d61bfd10b6` |
| MassDEP Final Decision, OADR 2025-022 | Government final administrative decision | Dated 2026-03-27; affirms NE-25-002 | https://www.mass.gov/doc/markley-group-llc-final-decision-2025-022/download | 2026-10-24 | `94a1edc183996bb5c1f3fb077200cb76a36594424853cd81d33bc706fbff365e` |
| Residents' Notice of Claim / Request for Adjudicatory Hearing | Petitioner allegations and attached records, not government findings | Filed 2025-07-24; identifies the April 28 application and July 3 approval as attachments | https://law.yale.edu/sites/default/files/documents/documents/pdf/Clinics/2025-07-24_filed_appeal_redacted.pdf | 2026-10-24 | `be0ecc43e43ed9a5ecf2f1a5bda4b48e60526e85cc747c75751be7abe6994fa9` |

## Remaining uncertainty

This review establishes that the 27-generator NE-25-002 phase is later and different from the 19-generator phase. It does **not** establish a one-to-one correspondence between every August 9 civil-plan feature and the June–August 2024 air documents. It also does not establish the official date or status mapping of the Generator Yard Sketch.

Until a human approves a feature concordance, the August 9 civil set remains the only geometry and state source for the 2024 proposal package. Later records must be published under a separate package version if modeled.

External-source descriptions in this document are paraphrased for licensing compliance.
