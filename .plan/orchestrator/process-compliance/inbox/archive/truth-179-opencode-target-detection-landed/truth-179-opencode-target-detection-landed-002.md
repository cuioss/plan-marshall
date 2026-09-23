envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-23T20:33:40Z

# Process-rule issue: mailbox probe vs inbox detect disagree on the same file-pointer source_id

Reporter: plan `truth-179-opencode-target-detection-landed` at `1-init -> 2-refine` transition.

Observed:

1. `manage-status transition --completed 1-init` returned `mailbox.probe: not_orchestrated` with reason `request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer), so this plan has no epic and no mailbox`.
2. `orchestrator inbox detect --source-id .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-179-opencode-target-detection-landed-three-gaps-it-exposed-still-stand.md` (the identical string stored as `request.md` source_id by the Step 4 file-pointer branch) returned `orchestrated: true`, `epic: truthful-signals`, `detection: orchestrated`.

Both calls ran in the same checkout minutes apart. The transition-time probe and the standalone classifier disagree on the same input, so the plan's mailbox checkpoint at transition says `not_orchestrated` (no mailbox, no future mail visibility) while the epic-side classifier says the plan belongs to `truthful-signals`.

Impact: if the transition probe is authoritative downstream, this plan will never see mail delivered to it under the `truthful-signals` epic and its landing report routing may queue epic-addressed instead of plan-delivered. If `inbox detect` is authoritative, the transition emitted a false `not_orchestrated` checkpoint into the plan record.

Suggested owner: whoever owns the `MAILBOX_PROBES` vocabulary in `manage-status` vs `inbox detect` in `plan-orchestrator` — the two share a vocabulary but evidently not a classifier. Either unify them on one implementation or record which one governs at phase-transition checkpoints.

Evidence: transition TOON and detect TOON captured this session; `request.md` source_id is the repo-relative spec path above; no `.plan/` file was read directly.
