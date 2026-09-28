# PLAN-17: Concurrent-plan isolation at the planning boundaries

> ✅ **Staged 2026-09-27 under explicit operator directive ("issues about current problems are to be fixed, not
> relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-17-concurrent-plan-isolation.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make the planning lane safe to run while sibling plans of the same epic run. Two defects
break that today: the main-checkout cleanliness assertions fire on sanctioned writes made by
OTHER actors, and a fixed staging filename under `.plan/temp/` lets two concurrent refines
persist each other's content.

## Deliverables

1. **Main-checkout assertions measure this phase's own writes.** The 1→2 and 2→3
   `Post-dispatch contract assertion` blocks in `plan-marshall/workflow/planning.md`
   (`git -C . status --porcelain` must be empty) and the `main_dirty` handshake invariant
   stop on ANY dirt, including pre-existing dirt and sanctioned writes to the git-tracked
   orchestrator store (`.plan/orchestrator/**`: the plan's own inbox message, sibling plans'
   inbox messages, the orchestrator's `epic.md` edits). Observed: PLAN-13's refine returned
   clean yet hit the assertion on 7 entries it did not write. The guarantee — "this phase did
   not edit the main checkout" — needs a baseline: snapshot porcelain before the phase and
   assert on the delta, and/or exempt `.plan/orchestrator/**`. Regression test: pre-existing
   dirt plus a concurrent orchestrator-store write does not trip the assertion; a real
   phase-made edit still does. **Scope (folded 2026-09-28):** the same porcelain block is
   repeated at the outline and plan boundaries in `plan-marshall/workflow/planning-outline.md`
   — fix the whole population, not only `planning.md`. The two guards must share ONE
   exemption set: `phase_handshake verify` already reports these paths as
   `main_dirty_exempted` (informational) while the porcelain assertion stops the run on
   them, so the guards disagree today. The recovery text ("revert them or move them into
   `.plan/local/plans/{plan_id}/**`") must not tell a plan to revert other actors' ledger
   writes.
3. **Handshake blocking count reconciles with its buckets.** A `2-refine` capture reported
   `pending_findings_blocking_count: 1` while every `pending_findings_by_type` bucket was
   `0` (the one open item was a refine Q-Gate flag-not-block). A blocking count must be
   derivable from the per-type buckets it summarises, or carry the missing bucket.
2. **Plan-scoped staging paths.** `phase-2-refine` (and `phase-3-outline`, which cites the
   same file) stage `.plan/temp/module_mapping.toon` — a literal shared across plans — before
   `manage-files write --content-file`. A concurrent refine for another plan overwrote it
   mid-run. Every `.plan/temp/` staging path named in a workflow doc must include the plan
   id; sweep the phase docs for any other fixed staging filename and fix the whole population.

## Claim Labels

- OBSERVED: refine clean-main assertion tripped on 7 sanctioned `.plan/orchestrator/process-compliance/` entries not written by the refine — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-002.md` § 2 (porcelain quoted); prior instance `plan-09-outline-sweep-003.md` (main-dirt assertion fires on pre-existing dirt, originally folded into PLAN-10 without a deliverable — now carried here)
- OBSERVED: two further runs hit the same assertion on sanctioned orchestrator-store writes, with `phase_handshake verify` classifying the same paths `main_dirty_exempted` — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-006.md` § Observed and `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-003.md` § 3
- HYPOTHESIS: the blocking count is computed from a population the per-type buckets do not enumerate (Q-Gate flags) — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `pending_findings_blocking_count` (verify-at-outline); observation cited at `plan-12-tool-triage-006.md` § Secondary observation
- OBSERVED: `.plan/temp/module_mapping.toon` overwritten by a concurrent refine — cited at `plan-13-finalize-mechanism-defects-002.md` § 3 (refine sub-agent report, not reproduced); the literal is confirmed at HEAD in `phase-2-refine/SKILL.md`, `phase-2-refine/standards/refine-workflow-detail.md`, `phase-3-outline/SKILL.md`

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — both post-dispatch assertions
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — outline/plan-boundary post-dispatch assertions (folded 2026-09-28)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` — exemption set + blocking-count contract (folded 2026-09-28)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — `main_dirty` invariant, `pending_findings_blocking_count`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py` — porcelain helper
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/` — staging filename
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` — staging filename
- OBSERVED: `test/plan-marshall/plan-marshall/` — invariant regression test

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-10 (shares `plan-marshall/workflow/planning.md` and `test/plan-marshall/plan-marshall/` — sequence, do not parallelize); PLAN-18 (shares `planning.md` and `planning-outline.md` — sequence)

## Folded inbox material (same act)

- `plan-13-finalize-mechanism-defects-002.md` items 2, 3 (finding): deliverables 1, 2
- `plan-09-outline-sweep-003.md` (finding, previously folded into PLAN-10 with no deliverable): deliverable 1
- `plan-12-tool-triage-006.md` (finding, drain 2026-09-28): deliverable 1 (recurrence, scope widened to `planning-outline.md` + shared exemption set), deliverable 3 (secondary observation)
- `plan-13-finalize-mechanism-defects-003.md` item 3 (finding, drain 2026-09-28): deliverable 1 (recurrence)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-17-concurrent-plan-isolation.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
