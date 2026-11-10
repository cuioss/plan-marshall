envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T14:27:11Z

Runbook-lane landings of the epic pm-mcp-core-m2-m4-v2 never report `total_tokens` and `plugin_version`: the lane writes `unknown` for both, so `landing-check` reports every such landing incomplete (`missing_keys`: `total_tokens`, `plugin_version`).

Observed on 15 landings from PLAN-V2-83 (2026-10-30) to PLAN-V2-95 (2026-11-09); the latest also shows `surface_delta` `unmeasured`. Same two keys, same harness, same model each time; every landing was reconciled in full by the orchestrator.

Cause as far as the orchestrator can read it: the opencode harness measures no tokens, and the `platform_runtime runtime-info` seam returns no plugin version for the runbook lane. `unknown` is the honest value (unobserved, never zero), so the lane is not wrong; the seam is incomplete.

Candidate lesson for plan-marshall (component: `plan-marshall:platform-runtime` `runtime-info`, and the runbook lane's landing stamp): report the plugin version and a token total for a runbook-lane run, or have `landing-check` treat the two keys as not applicable for that lane, so that a runbook-lane landing can be `complete: true`.

Source: epic.md Open Defects of pm-mcp-core-m2-m4-v2, entry first filed 2026-10-30 (message `rb-v2-83-skills-conformance-foundation-001.md`); condensed 2026-11-09 by the operator's decision "route a lesson, condense the entry".
