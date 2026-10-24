---
inclusion: always
---

# Hackachusetts Submission and Judging Rules

Apply these rules to all LotLens planning, implementation, documentation, testing, and release work.

## Project Positioning

- Submit LotLens under the civic track. The supplied rules use both **Civic Action** and **Civic Services**; verify the exact label shown on the official submission form before submitting.
- Explain LotLens as an accessible civic-information tool that helps Massachusetts residents understand parcel-level implications of Question 7.
- Keep public-facing analysis neutral, sourced, understandable, and explicit about estimates, confidence, and limitations.
- Prioritize a polished, dependable user journey over unsupported statewide coverage or speculative features.

## Non-Negotiable Submission Requirements

Before declaring the submission ready, verify each item with repository or deployment evidence:

- The team has no more than four members, and all members are listed.
- One eligible team member is authorized as the team Representative.
- The submission identifies the selected challenge track using the official form's wording.
- The text description clearly explains the project's problem, intended users, features, functionality, accessibility, and realistic path to scale.
- The demonstration video is under three minutes, shows the working product on its intended device, and is publicly viewable on YouTube, Vimeo, Facebook Video, or Youku. Put its public URL on the submission form.
- The video contains no third-party trademarks, copyrighted music, or other material unless the team has permission to use it.
- The public GitHub repository contains all source code, required assets, dependency declarations, setup instructions, testing instructions, and run instructions needed for judging. Put its public URL on the submission form.
- The repository root contains a tracked `.kiro/` directory. Never add `.kiro/` or its required contents to `.gitignore`.
- Judges can access a working deployment, functioning demo, or test build free of charge and without restrictions through the end of judging. Put its URL on the submission form. If authentication is unavoidable, include valid testing credentials through an appropriate secure submission channel, never as secrets committed to Git.
- The description, images, and video must communicate the project without assuming that judges will run it; judges may evaluate only those materials.
- Submission materials are in English, or include complete English translations, including translations of the video, description, testing instructions, and other submitted materials.
- The submission is original, team-owned work and does not violate copyright, trademark, patent, contract, privacy, publicity, or other rights.
- Open-source dependencies, public datasets, imagery, icons, fonts, and other third-party assets have compatible licenses and required notices or attribution. The team's software must add original functionality rather than merely repackaging an underlying open-source product.
- Confirm that the project was not developed or derived from a project that received disqualifying financial or preferential support from the Sponsor or Administrator before the end of the Submission Period, including prior funding, investment, contracted development, or a commercial license.
- Confirm that submitted content contains no viruses, Trojan horses, worms, spyware, disabling devices, or other malicious code.
- Do not modify the submitted project after the Submission Period ends unless the Sponsor or Administrator explicitly permits the specific change. Any permitted correction must remain substantively the same and be limited to the authorized removal or replacement of problematic material.

The supplied information does not state the Submission Period or Judging Period dates. Treat both dates as unresolved until verified from the official Hackachusetts website. Unknown team, representative, deployment, video, licensing, deadline, or submission-form details must be reported as unresolved. Never invent evidence or claim an unmet requirement is complete.

## Required Kiro Evidence

Kiro must materially contribute to the project. Preserve concrete, truthful evidence of how it helped rather than adding superficial artifacts near submission time.

- Keep Specs under `.kiro/specs/` for substantial features. Requirements, design, and tasks should show how Kiro converted product intent into implementation.
- Distinguish Spec-driven work from exploratory Vibe work and explain why each mode was chosen.
- Keep useful project hooks under `.kiro/hooks/` and document the workflow each hook automates and the measurable benefit or risk reduction it provides.
- Keep steering documents focused and version-controlled. Record how steering improved consistency, correctness, civic neutrality, accessibility, data provenance, or submission compliance.
- Document MCP servers only when they were actually used. Explain the capability or workflow each server enabled and why ordinary local tools were insufficient or less effective.
- Use property-based testing where invariant-heavy logic benefits from it, especially parcel eligibility, area/frontage bounds, geometry handling, and classification consistency. Record defects it catches that example tests miss.
- Document Kiro Powers only when actually used, including the bundled expertise and any third-party integration they supplied.
- Identify every Kiro surface actually used, such as CLI, IDE, Web, or Crew, and explain how their roles differed.
- Never claim use of a Kiro feature, integration, test method, or tool without repository history or other verifiable project evidence.

Maintain enough history and documentation to write the required Kiro-use narrative. Prefer meaningful usage tied to project outcomes over maximizing the number of named features.

## Judging Priorities

### Potential Value

- Define the affected community and the specific decision LotLens helps that community make.
- Make the primary workflow easy to understand on mobile and desktop.
- Address accessibility, equity, adoption barriers, data limitations, and who may be excluded by incomplete coverage.
- Explain how the approach can expand beyond the hackathon without overstating legal accuracy or operational readiness.
- Make the pitch clear about who benefits, why current alternatives are insufficient, and why parcel-level analysis is useful.

### Implementation and Use of Kiro

- Use Kiro strategically across requirements, architecture, implementation, validation, and documentation.
- Prefer a small number of deeply useful integrations and automations over decorative complexity.
- Preserve important experiments and decisions, including rejected options and their trade-offs when they affected the final design.
- Keep generated code reviewable and keep core civic and eligibility logic explicit in version-controlled source code.
- Require human review for legal interpretations, public claims, destructive operations, releases, and submission actions.
- Treat **Best Use of Kiro** as requiring the highest Implementation score while also placing in the top 10% of projects. Optimize for demonstrable depth and impact, not feature-name counting.

### Quality and Design

- Build an intuitive, intentional, accessible interface with a polished end-to-end demonstration path.
- Use public datasets in a reproducible and well-attributed way.
- Cite the source of every consequential number and label estimates distinctly from official facts.
- Do not expose assessor owner names or unnecessary personally identifiable information.
- Include useful loading, empty, unavailable-data, low-confidence, and error states.
- Cache or precompute critical demo data where permitted so transient APIs do not break judging.

## Submission Rights and Administrative Awareness

Before submission, the team Representative must ensure every team member understands and accepts the official rules, including these consequences:

- The team retains ownership of the submission but grants the Sponsor a fully paid, non-exclusive license to use it for judging.
- The Sponsor and Administrator may promote the submission and use contributors' names, likenesses, voices, and images in promotional materials during the Hackathon Period and for three years afterward.
- Some submission materials may be public, while other materials may be reviewed by the Sponsor, Administrator, and judges.
- Rule acceptance includes releases, indemnities, limitations of liability, and binding decisions described in the official rules. This steering file is an engineering checklist, not a substitute for reading those rules.
- A project may win one Overall Prize in a category and up to two Bonus Prizes. Prize or AWS-interview eligibility must never be represented as guaranteed.
- Proof of sending is not proof of receipt. Confirm that the Hackathon website accepted the final submission and retain evidence of the submitted URLs and final commit.

## Validation Gates

For implementation work:

- Keep setup and run instructions synchronized with the actual code.
- Validate behavior against the applicable Spec and acceptance criteria.
- Check accessibility for primary workflows and keyboard use.
- Preserve dataset provenance, versions, transformations, licenses, and confidence limitations.
- Do not commit secrets, private credentials, restricted data, or unlicensed assets.

Before submission:

- Test the repository from a clean checkout using only documented instructions.
- Confirm `.kiro/` is tracked and publicly visible.
- Confirm the public repository and demo URLs work in a logged-out browser.
- Confirm the final video is publicly visible, under three minutes, and demonstrates the working product.
- Confirm all team, Representative, track, description, Kiro write-up, testing, and rights information is complete.
- Record the final submitted commit hash and deployment version.
- After the deadline, treat the submitted commit and deployment as frozen unless an authorized correction is documented.

When a request conflicts with these rules, stop and explain the conflict before changing files, deployments, submission materials, or Git history.
