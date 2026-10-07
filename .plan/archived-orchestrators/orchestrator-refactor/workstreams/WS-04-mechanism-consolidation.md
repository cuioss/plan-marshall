# WS-04: Mechanism Consolidation

epic: orchestrator-refactor

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-mechanism-consolidation.md` and is tracked in the
> epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns aspect 4 of the epic: every sibling orchestrator epic (active and archived) was swept
for deliverables that are actually about the ORCHESTRATOR MECHANISM itself rather than that
epic's own domain. Four active siblings (`code-intelligence-substrate`, `review-apparatus`,
`truthful-signals`, `post-run-quality`) carry such items — most sharply, one schema file
(`landing-payload-spec.md`) has three concurrent would-be owners in three ledgers that
structurally cannot see each other. This workstream gives the scattered mechanism work one
owner. It also carries the (lower-confidence, operator-discretionary) `orchestrator.py`
module-split, the same monolith problem as WS-01's ledger split, one layer down in the
script itself.

## Scope

- In scope: taking ownership of `landing-payload-spec.md`, closing the two-parser
  disagreement over `## Expected Surface` between `orchestrator.py` and
  `tools-epic-surface-partition` (cross-bundle), the plan-id detection seam, and recording
  (never performing) the transfer back into each sibling ledger; optionally, splitting
  `orchestrator.py` (4,919 lines, `corpus` alone 33%) into one module per command group,
  mirroring the existing `_orchestrator_inbox.py` split.
- Out of scope: editing any sibling epic's ledger directly (this workstream records what it
  asks for; the sibling epic's own orchestrator session performs the transfer); the
  `status.json` schema shape (WS-01) and the identifier rename (WS-03), except where an
  intake item IS one of those changes and is sequenced behind the owning workstream.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-06-orchestrator-mechanism-intake | staged | Re-grounds every carried item against HEAD (3 of the candidates may already be shipped), takes ownership of `landing-payload-spec.md`, closes the two-parser split. Blocked on `truthful-signals` PLAN-TRUTH-143 (running) landing first — do not re-scope a running plan's surface. |
| PLAN-07-orchestrator-script-decomposition | staged | Lowest confidence of the epic's corpus — no external forcing function, collides with nearly every other plan here. Operator discretion to keep, defer, or drop. Sequenced last if kept. |

## Sequencing and Surface Notes

- PLAN-06 is BLOCKED, not merely sequenced: `truthful-signals` PLAN-TRUTH-143 is `running`
  and declares the widest orchestrator surface of any live spec in the whole corpus
  (`orchestrator.py`, `_orchestrator_inbox.py`, `SKILL.md`, `inbox-envelope.md`,
  `orchestration-model.md`, `analyze.md`, `orchestrate.md`). The running-row exclusion in
  `orchestration-model.md` § Cleanup Contract forbids re-scoping a running plan's brief —
  PLAN-06 must wait for PLAN-TRUTH-143 to land, then re-ground against the new HEAD before
  staging its command.
- PLAN-06 also has narrower overlaps with `truthful-signals` PLAN-TRUTH-149/-146/-144/-167
  (staged), `review-apparatus` PLAN-PR-073 (staged) / -055 / -064 (parked), `post-run-quality`
  PLAN-PRQ-04 (staged), and `code-intelligence-substrate` PLAN-CIS-052 (staged) — all on
  `landing-payload-spec.md` and/or `_orchestrator_inbox.py`. None of these are visible to the
  automated disjointness gate (it does not cross sibling ledgers); PLAN-06's own Deliverable
  D4 is to record the transfer request into each, not to edit them.
- PLAN-07 collides with PLAN-01 (WS-01), PLAN-02 (WS-01), PLAN-05 (WS-03), and PLAN-06 (this
  workstream) — all touch `orchestrator.py`. If kept, it is sequenced strictly last, after
  every other plan in this epic has landed.
- The status-vocabulary fix (95/500 rows unexpressible) appears both as WS-01 PLAN-02's D2
  and as a PLAN-06 intake candidate. It is assigned to PLAN-02 (it is the schema); PLAN-06's
  spec records the assignment rather than duplicating the deliverable.
