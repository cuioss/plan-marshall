envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-19T15:00:17Z

envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-19T15:00:00Z

# Missing landing-facts blocks on both PLAN-180 carve-1 landings (test-quality drain)

## What was observed

At the 2026-09-19 test-quality inbox drain, both `kind: landing` messages from
`test-fidelity-rules` carried narrative only — neither contains the
```landing-facts machine-readable block:

- `test-fidelity-rules-001.md` (carve-1 report, PR #1538 still open at file time)
- `test-fidelity-rules-002.md` (carve-1 merged notice, `cd6436a4a`)

`inbox landing-check` on each returned `complete: false` with `missing_keys`
naming the whole required set (9 of 9: schema, plan_id, pr, merge_state,
cleanup_owed, deliverables_total, deliverables_done, total_tokens, steps).

## Cost paid

The drain corroborated the merge facts independently (`ci pr view` #1538
`merged`, merge commit in main history, tree clean, plan archived) and
reconciled on that basis — the hand-recovery the machine-readable block exists
to remove. This is the same pre-fix class as the PLAN-135 and PLAN-176
landings in this epic: three occurrences across two epics and one carve.

## What this is not

The facts themselves are not disputed — every material claim in both messages
verified against ground truth. The defect is the missing block, not the
payload. Both messages drained and archived as partial-carve reconciliations
(no ship semantics; PLAN-180 row stays `running` tracking carves 2–4).

## Suggested direction (for process-compliance triage)

The emit-landing finalize step writes the narrative but not the facts block on
this path. Either the step's contract or its verification gate should require
the block before the message is filed — a `landing-check complete: false` at
file time is currently silent until the drain pays for it.
