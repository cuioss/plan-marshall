envelope_version=1
sender_type=orchestrator
sender_id=orchestrator-refactor
epic=lessons-routing
kind=finding
created=2026-10-05T14:43:14Z

# Transfer from `orchestrator-refactor` (epic closing, routed by operator decision)

## 1. Retirement candidate: lesson `2026-09-27-07-001`

`plan-marshall:manage-status` describes this one: "Transition mailbox probe reports not_orchestrated for an orchestrator spec-pointer source_id that inbox detect classifies orchestrated". It is still `active`. It was fixed by #1685 (`8aa33cfe1`): `_resolve_mailbox_checkpoint` in `manage-status/scripts/_cmd_lifecycle.py` now reads `source_id` through `parse_document_sections` instead of `file_ops.parse_markdown_metadata`, and the fixture renders the production `request.md` template. The fix was corroborated on 2026-10-03: the PR is merged, the commit is an ancestor of `origin/main`, and the file list matches. Verify against HEAD, then retire the lesson.

## 2. PLAN-09 landing: lesson carry-over with no target (6 rows)

The PLAN-09 (#1652) retrospective produced these. They are implementation-free invariants, each with its fixture:

| Source | Carry-over | Kind |
|---|---|---|
| lesson 001 (retrospective) | A payload whose delivered size is far below its produced size is truncated, never "small": when delivered_bytes ≪ produced_bytes, a budget gate derived from the delivered figure must not pass, and the analysis tier must degrade with a named reason. Fixture: 69 of 236,070 reduced transcript bytes delivered, Tier 1 selected (block-scalar continuation lines emitted at column 0). | invariant + fixture |
| lesson 002 (metrics) | Every dispatch-boundary record carries the step key and the leaf's usage figures, so it joins its step record by key, never by timestamp window. Fixture: 35/35 boundary rows keyless, 11 execute rows at 0 tokens, 0 of 63 paired. An unmeasured field is `unmeasured`, never `0`. | invariant + fixture |
| lesson 003 (self-review) | A coverage-class step lacking the tool to establish coverage returns a coverage-gap verdict. It does not spend a loop-back, and a verifier refusal caused by a missing tool does not count against the ceiling. Fixture: 7 firings, 5/5 loop-backs, 263 candidates, operator override (finding 5f65bb). | rule + fixture |
| lesson 004 (outline) | An outline that marks a path certainly-excluded while a deliverable declares it for modification is rejected at validation; declared lists are reconciled against the realized footprint after execute. Fixture: manage-logging/SKILL.md; 9 undeclared test modules; 1 declared test untouched. | invariant + fixture |
| landing residue | A landing's merge-commit fact comes from the PR's merge record, never local HEAD after a pull (recorded 438a0a71f while main was at c9c67839c). | invariant + fixture |
| landing residue | A reserved never-removed resource has a dedicated refusal on every destructive path, not an incidental one; a reused long-lived worktree is verified on its expected branch before any commit. | invariant |

Route each row to its owning component, or dedupe it against active lessons. Some may already be covered: lesson 001 overlaps `2026-09-23-05-001`/`-002`, and lesson 002 overlaps `2026-09-23-05-007`. The source file stays at the archived epic's `findings/2026-09-28-plan-09-lesson-carry-over.md`.
