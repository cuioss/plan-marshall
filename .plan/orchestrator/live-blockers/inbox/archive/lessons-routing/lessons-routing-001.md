envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T14:43:39Z

# Lessons ingest: self-review does not converge and re-fires settled finalize steps

Severity: high. Bundle: `plan-marshall` (`phase-6-finalize`). Backlog reference: `backlog.md` § 1.2.

Three lessons were retired from the lessons corpus by the `lessons-routing` ingest of 2026-10-09 and
are handed to this epic. Their full bodies, with every recurrence and its evidence, are kept at
`lessons-routing/lessons-archive/filed-live-blockers/`.

| Lesson | Statement |
|---|---|
| `2026-09-29-17-001` | The loop has no exit other than a clean round or the ceiling. A round can tell that its findings sit on prose the previous fix wrote, but that signal neither shortens the loop nor offers the operator a close. A clean round whose verdict the verifier refuses is a second non-exit. |
| `2026-10-02-10-005` | Verdict currency is keyed on the commit alone for a step that declares no verdict inputs, so every loop-back re-fires lessons-housekeeping, simplify and plugin-doctor even when the commit cannot change their answer. A finalize step that commits after the review band invalidates the band on every re-entry. |
| `2026-10-07-07-001` | A delta round reads only what the last fix touched, so "found nothing new" and "did not look there" are the same output. The Step 3b verifier needs a second dispatch that a leaf cannot issue, so `acceptance` / `may_close` were never produced by the workflow. |

One further row comes from the PLAN-09 (#1652) retrospective, transferred by `orchestrator-refactor`:
a coverage-class step that lacks the tool to establish coverage should return a coverage-gap verdict,
spend no loop-back, and not count a verifier refusal caused by the missing tool against the ceiling
(fixture: 7 firings, 5 of 5 loop-backs, 263 candidates, operator override, finding `5f65bb`).

## What to check here

This subject is already carried by this epic: PLAN-LB-22 (`finalize-loop-control`, #1718) and the
standalone self-review plan (#1726) shipped, and PLAN-LB-32 (`head-dependent-step-refire`) is staged.
The ingest did not verify which of the proposed actions those landings closed. The ones most likely
to be residual:

- the Step 3b verifier dispatch moved to the orchestrator (`2026-10-07-07-001`);
- the full-surface first round that enumerates the sibling population of each defect class
  (`2026-10-07-07-001`);
- verdict inputs declared per step, and finalize-internal generated commits left out of the currency
  comparison (`2026-10-02-10-005`) — the stated subject of PLAN-LB-32;
- the coverage-gap verdict of the PLAN-09 row.

Fold whatever is residual into PLAN-LB-32 or discard it as shipped.
