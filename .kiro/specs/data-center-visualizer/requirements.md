# Data Center Visualizer Requirements

**Status:** Approved by Ajin Frank Justin on 2026-10-24 (the open items in section 7 are still unresolved)  
**Workflow:** Requirements-first Feature Spec  
**Pilot:** Markley data center, 2 Prince Avenue / 1 Markley Way, Lowell, Massachusetts

## 1. Purpose

Data Center Visualizer converts a curated public development proposal into a georeferenced, to-scale 3D scene. Its primary civic purpose is to help Massachusetts residents understand what proposed structures and equipment would look like in their actual surroundings before or during public review.

The product answers one direct question:

> What would this proposal look like here?

The product must remain neutral. It visualizes documented geometry and clearly identified estimates; it does not recommend approval or rejection, predict health outcomes, determine legal compliance, or assign a project score.

## 2. Users

- **Nearby resident:** wants to view a proposal from a familiar location without reading technical drawings.
- **Member of the public:** wants to compare current and proposed conditions before a hearing.
- **Journalist or civic organization:** wants an accurate, shareable visual tied to original sources.
- **Project data curator:** prepares and verifies a proposal package before publication.

## 3. Glossary

- **Proposal package:** Versioned, reviewable data containing project metadata, sources, georeferenced feature geometry, feature states, dimensions, confidence, and optional 3D assets.
- **Current state:** Features documented as existing at the proposal package's stated baseline date.
- **Proposed state:** Current features plus additions, removals, or modifications documented in a named proposal version.
- **Official value:** A value transcribed directly from an identified government record or applicant document.
- **Derived value:** A value calculated from official geometry or scale using a documented method.
- **Estimated value:** A value supplied because the source does not establish it; it must be visually distinguished.
- **Unknown value:** A value that cannot be supported and must not be silently invented.
- **Viewpoint:** A camera location and direction selected from the map, a curated location, or a geocoded address.
- **Source reference:** A stable identifier connecting a modeled claim to a document, sheet, page, date, and public URL when available.

## 4. Functional Requirements

### Requirement 1: Curated and versioned proposal packages

**User story:** As a project data curator, I want each published scene to use a versioned proposal package so users can tell exactly which proposal they are viewing.

#### Acceptance criteria

1. WHEN a proposal package is loaded, THE SYSTEM SHALL identify the project, site address, baseline date, proposal date, package version, and last verification date.
2. WHEN a modeled feature is published, THE SYSTEM SHALL record its category, current/proposed state, horizontal geometry, vertical dimension status, confidence level, and one or more source references.
3. WHEN a source value is revised, THE SYSTEM SHALL require a new proposal package version rather than silently replacing the published value.
4. IF a package fails schema validation, THEN THE SYSTEM SHALL reject it and identify each invalid or missing field.
5. THE SYSTEM SHALL support a preprocessed, preloaded Lowell pilot package without requiring a live permit system during the demonstration.
6. THE SYSTEM SHALL NOT publish assessor owner names, abutter names, personal contact details, or other unnecessary personal information.

### Requirement 2: Source-to-map georeferencing

**User story:** As a resident, I want proposal features placed on their actual parcel so the visualization communicates real proximity and scale.

#### Acceptance criteria

1. WHEN a proposal plan is curated, THE SYSTEM SHALL transform its geometry into a documented Massachusetts geospatial coordinate reference system before producing web-map coordinates.
2. THE SYSTEM SHALL record the control points, transformation method, residual error, plan scale, and source sheet used for georeferencing.
3. WHEN validation control points are available, THE SYSTEM SHALL calculate horizontal root-mean-square error and store it in the proposal package.
4. IF horizontal root-mean-square error exceeds 2 meters, THEN THE SYSTEM SHALL label the scene as approximate and SHALL NOT display it as survey-accurate.
5. WHEN a source contains explicit dimensions, THE SYSTEM SHALL preserve those dimensions independently of screen or map zoom.
6. IF the proposal drawing conflicts with parcel or aerial data, THEN THE SYSTEM SHALL preserve the discrepancy as a review issue rather than automatically moving the proposal feature.

### Requirement 3: To-scale 3D scene

**User story:** As a resident, I want structures and equipment shown at understandable real-world scale.

#### Acceptance criteria

1. WHEN a validated proposal package opens, THE SYSTEM SHALL place the modeled features at their recorded geographic positions and dimensions.
2. THE SYSTEM SHALL support, at minimum, buildings, generators, cooling equipment, transformer areas, retaining walls, fences, paved areas, and vegetation-screening areas.
3. WHEN an official height exists, THE SYSTEM SHALL use that height and label it as official.
4. WHEN only a derived or estimated height exists, THE SYSTEM SHALL render it with the corresponding confidence treatment and make the assumption available from the selected feature.
5. IF a feature height is unknown, THEN THE SYSTEM SHALL use a clearly symbolic representation or omit the vertical feature; it SHALL NOT silently assign a realistic-looking height.
6. THE SYSTEM SHALL render existing context separately from proposal geometry so users can distinguish the two without relying only on color.
7. THE LOWELL PILOT SHALL render a coherent surrounding neighborhood, rather than an isolated proposal model, including available buildings, streets, water, terrain or ground surface, and major open-space areas within at least 1 kilometer of the project centroid.
8. THE SYSTEM SHALL provide a stylized urban-massing view with solid building forms, simple materials, ambient and directional lighting, depth, and anti-aliased edges; a flat wireframe or proposal object floating over a conventional 2D map SHALL NOT satisfy the primary visual output.
9. THE SYSTEM SHALL provide an elevated oblique overview comparable to a physical city-planning model, with orbit, tilt, pan, and zoom controls.
10. THE SYSTEM SHALL use level of detail so nearby proposal features retain useful shape while distant context may use simplified extrusions.
11. THE SYSTEM SHALL preserve the real character and density of Lowell; it SHALL NOT add skyline buildings, landscape features, or visual detail merely to resemble a denser reference city.
12. THE SYSTEM SHALL make the proposal visually discoverable within the larger scene while avoiding company logos and avoiding a visual treatment that implies approval, danger, or advocacy.

### Requirement 4: Direct current-versus-proposed comparison

**User story:** As a member of the public, I want to compare current and proposed conditions without reading a report.

#### Acceptance criteria

1. WHEN a scene is ready, THE SYSTEM SHALL make the visual comparison the dominant interface.
2. THE SYSTEM SHALL provide current, proposed, and split-comparison modes.
3. WHEN the user changes comparison mode, THE SYSTEM SHALL preserve the camera location, direction, zoom, date, and time.
4. WHEN a proposed feature replaces or removes a current feature, THE SYSTEM SHALL represent the transition according to the proposal package rather than showing both as simultaneously present.
5. THE SYSTEM SHALL provide category visibility controls for buildings, generators, cooling equipment, electrical equipment, walls/fences, and landscaping.
6. THE SYSTEM SHALL identify the proposal date and version within the visual interface.

### Requirement 5: Aerial, street, and nearby-address viewpoints

**User story:** As a nearby resident, I want to see the proposal from a location that I recognize.

#### Acceptance criteria

1. THE SYSTEM SHALL provide an aerial orbit view and at least three curated ground-level viewpoints for the Lowell pilot.
2. WHEN the user selects a point on the map, THE SYSTEM SHALL allow a ground-level camera to be placed at that point when the point is in a publicly accessible or otherwise valid viewing area.
3. WHEN address search is available and returns a valid result, THE SYSTEM SHALL place the viewpoint near that result without revealing parcel ownership.
4. IF address search is unavailable, THEN THE SYSTEM SHALL keep all curated viewpoints functional and explain that free-form lookup is temporarily unavailable.
5. THE SYSTEM SHALL NOT retain or transmit a user-entered address beyond what is necessary for the active lookup, except where the chosen geocoding provider necessarily processes the query and that behavior is disclosed.
6. THE SYSTEM SHALL prevent the camera from entering modeled structures or inaccessible underground positions.

### Requirement 6: Time and shadow visualization

**User story:** As a resident, I want to understand how documented or estimated structure heights may affect visible shadows.

#### Acceptance criteria

1. WHEN sufficient height and location data exist, THE SYSTEM SHALL provide date-and-time controls for an estimated solar-shadow view.
2. THE SYSTEM SHALL calculate solar position using the site's coordinates, the selected date and time, and the applicable local time zone.
3. WHEN a shadow depends on an estimated height, THE SYSTEM SHALL visibly label the shadow as estimated.
4. IF material height data are unknown, THEN THE SYSTEM SHALL disable the shadow feature for those objects and explain why.
5. THE SYSTEM SHALL NOT characterize the shadow view as a certified shadow study.

### Requirement 7: Shareable visual output

**User story:** As a resident or journalist, I want to export the view I created so I can discuss the same proposal with others.

#### Acceptance criteria

1. WHEN the user requests an export, THE SYSTEM SHALL generate a PNG representing the active camera and comparison state.
2. THE EXPORTED IMAGE SHALL include the project name, proposal version/date, viewpoint type, current/proposed state, visual legend, required map attribution, and an official/estimated-data indicator.
3. THE EXPORTED IMAGE SHALL include a stable application URL or proposal package identifier when available.
4. THE SYSTEM SHALL NOT include the user's entered address in the exported image unless the user explicitly enables it.
5. IF an export cannot be generated, THEN THE SYSTEM SHALL preserve the active scene and provide a recoverable error.
6. Exported animation or video is OPTIONAL for the MVP and SHALL NOT block completion of the required PNG workflow.

### Requirement 8: Visible provenance, uncertainty, and neutrality

**User story:** As a member of the public, I want to distinguish documented facts from modeling assumptions.

#### Acceptance criteria

1. WHEN a user selects a modeled feature, THE SYSTEM SHALL show whether its position, footprint, and height are official, derived, estimated, or unknown.
2. WHEN a source reference is public, THE SYSTEM SHALL provide a link and identify the document title, issuer, date, and sheet or page.
3. WHEN a source is not distributable, THE SYSTEM SHALL provide a citation without embedding or republishing the restricted document.
4. THE SYSTEM SHALL use distinct shape, pattern, label, or line treatments so confidence is not communicated by color alone.
5. THE SYSTEM SHALL NOT present allegations, applicant claims, government findings, and modeled estimates as interchangeable evidence.
6. THE SYSTEM SHALL NOT visualize noise, air dispersion, emissions exposure, health effects, legal compliance, or utility capacity unless a later approved Spec defines defensible data, methods, validation, and limitations.
7. THE SYSTEM SHALL NOT display company logos or reproduce proposal-sheet artwork unless the team has documented permission or a verified legal basis.

### Requirement 9: Accessibility and responsive interaction

**User story:** As a user with a disability or a mobile device, I want access to the proposal's essential spatial information and controls.

#### Acceptance criteria

1. THE SYSTEM SHALL support the primary workflow with keyboard-only input.
2. THE SYSTEM SHALL expose labeled controls, current values, errors, and comparison state to assistive technology.
3. THE SYSTEM SHALL provide a compact nonvisual scene inventory listing visible feature categories, counts, dimensions, confidence, and source references.
4. THE SYSTEM SHALL honor reduced-motion preferences by disabling automatic camera flights and nonessential animation.
5. THE SYSTEM SHALL NOT use color as the only means of communicating current/proposed state, category, confidence, or selection.
6. THE SYSTEM SHALL maintain usable controls and readable text at widths from 320 CSS pixels through desktop layouts.
7. THE SYSTEM SHALL provide visible focus indicators and meet WCAG 2.2 AA contrast requirements for required controls and text.

### Requirement 10: Loading, unavailable-data, and error states

**User story:** As a user, I want failures to be understandable and recoverable without losing the scene.

#### Acceptance criteria

1. WHILE map or proposal assets are loading, THE SYSTEM SHALL show progress without presenting an empty interface as a completed result.
2. IF aerial imagery or an external map service is unavailable, THEN THE SYSTEM SHALL load a permitted fallback basemap or a clearly labeled context-free scene for the preloaded pilot.
3. IF geocoding fails, THEN THE SYSTEM SHALL preserve the scene and offer curated viewpoints.
4. IF an optional detailed 3D asset fails, THEN THE SYSTEM SHALL substitute its validated simple geometry instead of removing the feature.
5. IF WebGL is unavailable, THEN THE SYSTEM SHALL provide a static attributed pilot image and the accessible scene inventory.
6. THE SYSTEM SHALL distinguish unavailable, unknown, estimated, and loading states.

### Requirement 11: Performance and dependable demonstration

**User story:** As a judge or resident, I want the visualization to work without specialist hardware or fragile live dependencies.

#### Acceptance criteria

1. THE SYSTEM SHALL define and document representative desktop and mobile test devices before performance acceptance.
2. On those devices, the preloaded Lowell pilot SHALL display an interactive initial scene within 5 seconds after locally bundled application assets finish downloading.
3. On those devices, normal camera movement in the pilot SHALL maintain a median of at least 30 rendered frames per second during a documented 30-second interaction trace.
4. THE SYSTEM SHALL use level-of-detail or simple fallback geometry where detailed assets would prevent the performance target.
5. THE SYSTEM SHALL bundle the critical pilot proposal package and required simple geometry so a transient permit API cannot break judging.
6. THE SYSTEM SHALL provide a documented reduced-detail mode.

### Requirement 12: Lowell pilot fidelity

**User story:** As a Lowell resident, I want the demonstration to match the identified public proposal instead of combining unrelated project versions.

#### Acceptance criteria

1. THE PILOT SHALL identify the City of Lowell August 9, 2024 civil drawing set as its current working proposal source.
2. THE PILOT SHALL model only features supported by identified sheets, including current/proposed status where the sheets establish it.
3. BEFORE public release, THE PROJECT SHALL verify whether the August 2024 site-plan package corresponds to or differs from the April–July 2025 MassDEP application and plan approval.
4. IF later records differ, THEN THE SYSTEM SHALL publish them as a separate proposal version and SHALL NOT silently merge the geometry.
5. BEFORE public release, a human reviewer SHALL compare each pilot feature against the source sheet and record the review result.
6. THE PILOT SHALL exclude abutter-list personal information and unnecessary assessor ownership information.

## 5. Non-goals for the MVP

- Fully automatic conversion of arbitrary PDF plans into finished 3D scenes
- Statewide data-center coverage
- Photorealistic reconstruction
- Certified survey, architectural, engineering, shadow, noise, air-quality, or health analysis
- Prediction of project approval, construction, market behavior, or community response
- Legal conclusions or advocacy recommendations
- Live integration with permit systems as a critical dependency
- Virtual-reality or augmented-reality support
- Required Blender-authored models; simple verified geometry is sufficient

## 6. Success criteria

The MVP succeeds when a first-time user can open a polished, stylized 3D model of the Lowell neighborhood; orbit from an elevated overview into a ground-level viewpoint; switch between current and proposed conditions without losing camera position; identify which visible elements are official or estimated; and export an attributed PNG without reading the underlying engineering plan. The scene must include at least 1 kilometer of real surrounding context and must resemble Lowell rather than an invented generic city.

The team must validate the workflow on mobile and desktop, with keyboard-only navigation and the documented failure fallbacks.

## 7. Open decisions and unresolved evidence

These items remain unresolved and must not be presented as complete:

- Final product name
- Verified relationship between the August 2024 Lowell site-plan package and the 2025–2026 expansion and litigation records
- Official or defensible heights for generators, cooling equipment, walls, fences, and related structures
- Geocoding provider and its privacy, cost, availability, and license terms
- Aerial imagery, terrain, map style, icon, font, and 3D-asset licenses
- Permission or legal basis for redistributing source proposal documents or derived visual assets
- Representative performance test devices
- Team members and authorized team Representative
- Exact official Hackachusetts civic-track label
- Submission Period and Judging Period dates
- Public repository, deployment, and demonstration-video URLs
