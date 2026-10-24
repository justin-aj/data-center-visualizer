---
inclusion: always
---

# Hackachusetts Submission and Judging Rules

Apply these rules to all Data Center Visualizer planning, implementation, documentation, testing, and release work.

## Project Positioning

- Submit Data Center Visualizer under the civic track. The supplied rules use both **Civic Action** and **Civic Services**; verify the exact label shown on the official submission form before submitting.
- Explain the project as an accessible civic-visualization tool that converts public development plans into georeferenced, to-scale 3D scenes for Massachusetts residents.
- Keep the product neutral. It must not advocate for or against data centers, predict health effects, determine legal compliance, or assign good/bad project scores.
- Make the interactive current-versus-proposed scene the primary output. Keep explanatory text concise and subordinate to the visual.
- Start with one dependable Lowell pilot rather than claiming unsupported statewide coverage.

## Visual Accuracy and Civic Trust

- Identify every modeled position, dimension, height, state, and label as official, derived, estimated, or unknown.
- Connect consequential geometry and labels to a versioned source reference containing the document, issuer, date, sheet or page, retrieval date, and public URL when available.
- Never silently invent a realistic-looking height or feature. Use symbolic geometry, an explicit estimate, or omit the feature.
- Record georeferencing control points, transformation method, coordinate reference system, residual error, and human review.
- Distinguish applicant claims, resident allegations, government findings, court allegations, and model estimates.
- Do not combine geometry or facts from different proposal versions without documenting the relationship and review.
- The August 2024 Lowell civil plan set must not be represented as the 2025–2026 expansion until that relationship is verified.
- Do not expose assessor owner names, abutter names, personal contact details, user-entered addresses, or other unnecessary personal information.
- Do not expose restricted critical-infrastructure information. Public records are not automatically appropriate for republication at full detail.
- Do not display company logos, proposal-sheet artwork, third-party imagery, fonts, icons, or 3D assets without compatible rights and required attribution.

## Non-Negotiable Submission Requirements

Before declaring the submission ready, verify each item with repository or deployment evidence:

- The team has no more than four members, and all members are listed.
- One eligible team member is authorized as the team Representative.
- The submission identifies the selected challenge track using the official form's wording.
- The text description clearly explains the problem, intended users, visual output, functionality, accessibility, data sources, limitations, and realistic path to scale.
- The demonstration video is under three minutes, shows the working product on its intended device, and is publicly viewable on YouTube, Vimeo, Facebook Video, or Youku. Put its public URL on the submission form.
- The video contains no third-party trademarks, copyrighted music, proposal-sheet artwork, or other material unless the team has permission or a verified legal basis to use it.
- The public GitHub repository contains all source code, distributable assets, dependency declarations, setup instructions, testing instructions, and run instructions needed for judging. Put its public URL on the submission form.
- The repository root contains a tracked `.kiro/` directory. Never add `.kiro/` or its required contents to `.gitignore`.
- Judges can access a working deployment, functioning demo, or test build free of charge and without restrictions through the end of judging. Put its URL on the submission form.
- The description, images, and video communicate the project without assuming that judges will run it.
- Submission materials are in English or include complete English translations.
- The submission is original, team-owned work and does not violate copyright, trademark, patent, contract, privacy, publicity, or other rights.
- Dependencies, public datasets, imagery, maps, source plans, icons, fonts, and third-party assets have compatible licenses and required notices or attribution.
- Confirm that the project was not developed or derived from a project that received disqualifying financial or preferential support from the Sponsor or Administrator before the end of the Submission Period.
- Confirm that submitted content contains no malicious code.
- Do not modify the submitted project after the Submission Period ends unless the Sponsor or Administrator explicitly permits the specific correction.

The supplied information does not state the Submission Period or Judging Period dates. Treat both dates as unresolved until verified from the official Hackachusetts website. Unknown team, Representative, deployment, video, licensing, deadline, or submission-form details must be reported as unresolved. Never invent evidence or claim an unmet requirement is complete.

## Required Kiro Evidence

- Keep substantial feature Specs under `.kiro/specs/`. Requirements, design, and tasks must show how Kiro converted product intent into implementation.
- Use requirements-first review gates for the Data Center Visualizer: approve requirements before design, and approve design before implementation tasks.
- Distinguish Spec-driven work from exploratory Vibe work and explain why each mode was chosen.
- Keep useful project hooks under `.kiro/hooks/` and document the workflow and measurable benefit or risk reduction.
- Keep steering documents focused and version-controlled. Record how steering improved neutrality, accessibility, provenance, visual accuracy, privacy, or submission compliance.
- Document MCP servers and Kiro Powers only when they were actually used.
- Identify every Kiro surface actually used and explain how their roles differed.
- Never claim use of a Kiro feature, integration, test method, or tool without repository history or other verifiable evidence.

## Judging Priorities

### Potential Value

- Define the affected community and the decision the visual helps them make.
- Demonstrate how the product reduces the expertise required to interpret site plans.
- Make the primary workflow understandable on mobile and desktop.
- Address accessibility, equity, adoption barriers, data gaps, and who may be excluded by incomplete digital records.
- Explain expansion beyond Lowell without overstating accuracy, automation, legal authority, or operational readiness.

### Implementation and Use of Kiro

- Use Kiro across requirements, architecture, implementation, validation, and documentation.
- Prefer a small number of useful integrations and automations over decorative complexity.
- Preserve important experiments and rejected options when their trade-offs affect the final design.
- Keep geospatial transforms, source mappings, confidence rules, and current/proposed classification explicit in version-controlled source code.
- Require human review for source interpretation, public claims, model publication, destructive operations, releases, and submission actions.

### Quality and Design

- Build an intentional, accessible visual workflow with useful loading, unavailable-data, low-confidence, fallback, and error states.
- Use public datasets reproducibly and with clear attribution.
- Validate modeled geometry against the applicable source sheets.
- Cache or bundle critical pilot data where permitted so transient services do not break judging.
- Ensure exported visuals retain proposal version, confidence, and map attribution.

## Submission Rights and Administrative Awareness

Before submission, the team Representative must ensure every member understands and accepts the official rules, including ownership, judging licenses, promotional rights, releases, indemnities, limitations of liability, prize restrictions, and binding decisions. This steering file is an engineering checklist, not a substitute for reading the official rules.

Proof of sending is not proof of receipt. Confirm that the Hackathon website accepted the final submission and retain evidence of submitted URLs and the final commit.

## Validation Gates

For implementation work:

- Keep setup, build, test, and run instructions synchronized with the code.
- Validate behavior against the approved Spec and acceptance criteria.
- Check the primary workflow with keyboard-only navigation and reduced motion.
- Preserve source provenance, proposal versions, transformations, licenses, confidence, and limitations.
- Verify current/proposed classification and prevent cross-version merging.
- Do not commit secrets, private credentials, restricted data, unnecessary personal information, or unlicensed assets.

Before submission:

- Test from a clean checkout using only documented instructions.
- Confirm `.kiro/` is tracked and publicly visible.
- Confirm public repository and demo URLs work in a logged-out browser.
- Confirm the final video is public, under three minutes, and shows the working visual output.
- Confirm team, Representative, track, description, Kiro narrative, testing, rights, and licensing information is complete.
- Record the submitted commit hash, proposal package version, source manifest version, and deployment version.
- Freeze the submitted commit and deployment after the deadline unless an authorized correction is documented.

When a request conflicts with these rules, stop and explain the conflict before changing files, deployments, submission materials, or Git history.
