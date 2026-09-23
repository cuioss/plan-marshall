envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=process-compliance
kind=finding
created=2026-09-23T07:39:44Z

# Process-compliance finding — mailbox probe disagrees with detect verb (truth-147-lane-reports-green)

## Observation

- Same `source_id` (`.plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-147-....md`):
  - `orchestrator inbox detect --source-id ...` returns `orchestrated: true`, `epic: truthful-signals`, `detection: orchestrated`.
  - The `manage-status transition` embedded mailbox probe (phase-transition checkpoint) returns `probe: not_orchestrated`, `reason: "request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)"`.
- Observed at the 1-init → 2-refine transition and again at the 3-outline → 4-plan transition; the standalone `inbox read --slug truthful-signals --plan-id truth-147-lane-reports-green` then resolves `mailbox_state: no_mailbox` (nothing waiting), so no mail was missed this run.

## Defect

- Two call sites classify the same pointer differently. One of them is wrong: either the transition probe is stricter than the detect verb (e.g. it expects the `.plan/local/orchestrator/...` spelling while detect accepts the tracked `.plan/orchestrator/...` spelling — consistent with finding 001), or they implement separate grammars for the same concept.
- A `not_orchestrated` verdict at a phase-transition checkpoint silences the mailbox check for an orchestrated plan; a `false` orchestrated verdict in the other direction would misroute reads. Either direction corrupts the check-point roster's fail-open accounting (`unresolved` vs `not_orchestrated` are different facts).

## Request

- Unify the pointer grammar in one classifier consumed by both the transition probe and `inbox detect`, covering both the tracked (`.plan/orchestrator/...`) and local (`.plan/local/orchestrator/...`) spellings, or document which spelling is canonical and fix the emitters (hand-off command, claim-label pointers) to use it.
