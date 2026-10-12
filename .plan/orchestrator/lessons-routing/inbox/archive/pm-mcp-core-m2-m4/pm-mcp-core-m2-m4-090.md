envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:34Z

# Candidate lesson: cross-repository documentation paths in a worktree plan must be absolute

Component: plan-marshall:phase-3-outline (outline authoring for plans that also edit plan-marshall-documentation)
Category (proposed): improvement
Source: plan code-analysis-base, Q-Gate finding e4e7f7 (3-outline), resolved in-run

## Observation

The outline listed the documentation edits of deliverables 8-10 as `../plan-marshall-documentation/doc/...`. With `use_worktree: true` the plan runs from `.plan/local/worktrees/...`, where `../` does not reach the sibling checkout. The paths also counted the sibling repository's files into this repository's footprint. Fixed in-run by using the absolute documentation root, marking the module as cross-repository, and stating that those edits happen on a branch of the documentation repository and land through its own PR.

## Recurring rule for this epic

Every plan of this epic that changes a specification or requirement (CLAUDE.md requires it to update plan-marshall-documentation directly) should, at outline time: name the documentation checkout by absolute path, declare those deliverables cross-repository with their own branch and PR, and keep them out of this repository's affected-files footprint. A staged-spec template note would prevent the Q-Gate round.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-008.md` from plan code-analysis-base (PLAN-36, #31)
