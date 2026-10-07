# Landing Analysis: PLAN-45 — routed-verdict client-side cross-check

epic: truthful-signals
workstream: WS-01
pr: #993 (https://github.com/cuioss/plan-marshall/pull/993) — squash-merged, 9f2e55e71

> Landing record for one shipped plan. Corroborated against the merged diff at
> 9f2e55e71 and the commit narrative; migrated from the closed `plan-server` epic
> as the client-side defense-in-depth backstop to the already-shipped daemon-side
> false-green fix (#979).

## Deliverable Fidelity vs Spec

Spec staged D2–D4 (client affirm + errors[] fidelity + dual-mode test). All shipped;
corroborated against the merged file set.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D2 — client independently affirms verdict, fail-closed | shipped-as-specified | _build_execute_factory.py (+25) `_daemon_result_to_direct` now downgrades success→error when `job_status==success` but the log-verdict disagrees |
| Single-point-of-truth relocation (implied by D2) | shipped-as-specified (added structure) | `read_log_verdict`/`LogVerdict`/`_toon_scalar` relocated out of _marshalld_supervisor.py (−67) into shared `_build_server_protocol.py` (+73) so daemon and client consult one implementation |
| D3 — routed-failure errors[] fidelity | shipped-as-specified | _build_execute_factory.py errors[] surfacing |
| D4 — failing build returns status:error under BOTH in_process AND daemon modes w/ stubbed lying daemon | shipped-as-specified | test_build_execute_factory.py (+197), test_build_server_protocol.py (+86), test_marshalld_supervisor.py refactored to shared module |

## Metrics and Anomalies

- Tokens: 1,330,359 total. Duration: 2h32m wall / 1h13m worked. Diff 396 insertions /
  119 deletions, 6 files.
- Routing: light lane resolved the D1 GATE during outline (3-outline ~4s); 1 deliverable → 2 tasks.
- Anomalies: none flagged. The relocation to `_build_server_protocol.py` shrank
  _marshalld_supervisor.py by 67 lines — a net simplification, single source of truth.
  D1 GATE re-trace confirmed the wait TOON already carries the daemon's job log, so the
  lossless client-side re-read (option b) was correct — no new wire fields.

## Routing and Merge Behavior

- Review: not separately captured; merged clean (no loop-back recorded).
- CI/merge: green, squash-merged via merge queue. Surface (build-execute/build-server-client)
  disjoint from the concurrently-launched PLAN-46 (terminal-title) — no collision.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated → shipped, pr 993, landing landings/PLAN-45.md
- [x] epic.md queue reconciled from status.json
- [x] Watch (2) daemon-routing VERDICT-INVERSION → CLIENT RESIDUAL: RESOLVED — the client
      no longer trusts `job_status` verbatim; single-point-of-truth via _build_server_protocol.py
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- Consistency held with the truthful-status contract (PLAN-24 #963 + PLAN-32 #972) as the
  spec required.
- RELAY still owed (spec D-note): #909 half-(b) bound-expiry terminal-status hoist — carried
  as an open thread; check merged #972 first. Not a blocker for this landing.
- Flagship archetype instance (2) of n=7 now closed at the tool layer (client end).
