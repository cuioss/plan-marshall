envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:20:23Z

component=plan-marshall:persona-plan-marshall-agent
category=improvement
bundle=plan-marshall

# The new "Broad content sweep" carve-out prose is duplicated near-verbatim between SKILL.md and tool-usage-patterns.md

## Observation

`finalize-step-simplify` flagged (1 finding, 0 edits) that the "Broad content sweep" section added to `persona-plan-marshall-agent/standards/tool-usage-patterns.md` by PR #1046 restates the SKILL.md carve-out prose almost word for word.

Only SKILL.md is *required* to carry the bounds of the carve-out — it is the always-loaded floor. The `tool-usage-patterns.md` copy is therefore a cross-reference candidate under the project's **No-duplication** documentation standard ("cross-reference instead of duplicating information").

## Why it matters beyond tidiness

Two copies of a normative bound drift. The bound here is exactly the kind that must not drift: it defines when bare `git grep` is permitted. A future edit that tightens or widens the carve-out in one file and not the other produces a document pair that disagrees about what is allowed — the "doc-contract-divergence" archetype already recorded several times in this project.

## Corrective action

Replace the duplicated body in `tool-usage-patterns.md` with a cross-reference to the SKILL.md section that owns the bounds, keeping at most a one-line pointer.

## Status

**NOT FIXED** — flagged by `finalize-step-simplify` during this run and deliberately not actioned inside PR #1046 (it would have re-opened the reviewed diff). Carried to the epic as a small, self-contained follow-up.
