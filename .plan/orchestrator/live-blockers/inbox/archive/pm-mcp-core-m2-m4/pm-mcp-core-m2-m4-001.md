envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-21T12:58:17Z

# Finding: the generated executor of a consumer checkout pins a `runbook_lane` older than the registry, and the runbook lane then fails at the build gate

Source: epic `pm-mcp-core-m2-m4` (consumer repository `pm-mcp-core`), recurrence over five opencode runbook-lane landings, 2026-10-20 to 2026-10-21. Related, already staged here: PLAN-LB-78 (runbook-lane build resolution), PLAN-LB-40 and PLAN-LB-60 (steward upgrade integrity). This message adds evidence, not a new defect.

## Observed by the orchestrator (2026-10-21)

- `cleanup restart-check` reports the registry pin `0.1.1977` and the executor's mapping of `plan-marshall:runbook-lane:runbook_lane` still at `0.1.1961`; `registry_parity: indeterminate`. The executor was generated before the plugin moved on and nothing regenerated it between the plans.

## Reported by the lane in its landing message (plan-reported, not observable on an unguarded harness)

- PLAN-78 (2026-10-20): the executor maps `runbook_lane` to `0.1.1961` (only `resolve`); the lane skill the run read is newer (`build-classify` exists from `0.1.1969`). The lane met `unknown_verb`; the operator chose "docs-only by inspection", so the Maven gates never ran.
- PLAN-90 (2026-10-21): `build-classify` is `unknown_verb`; `resolve` omits `base_branch`, `build_timeout_seconds` and `guard_log`; the canonical build names were rejected; the operator chose the executor with real Maven arguments.
- PLAN-82 (2026-10-21): `maven run --command-args "module-tests"` fails (the alias is not expanded), and `--project-dir` does not move the build's working directory in the `in_process` fallback, so the lane passed `-f {worktree}/pom.xml`.
- PLAN-83 (2026-10-21): the resolved build names (`quality-gate`, `module-tests`, `test-compile`) reached Maven and failed with "Unknown lifecycle phase"; the lane then read the installed skill documentation under `~/.config/opencode/skills/` to find the invocation surfaces, which the lane contract forbids reading.

## Consequence seen on `main`

PLAN-83's squash (#125) reached `main` without a rewrite the `verify -Ppre-commit` gate applies; the build's rewrite (14 lines of `ServiceUnitInstallerTest`, `throws IOException` to `throws Exception`) had to land afterwards as #127. Whether the gate ran in PLAN-83's lane is not in its landing.

## Suggestion

A runbook lane started on an executor whose pin is older than the registry should refuse at `resolve` with the version skew named, instead of failing later at the build gate, and `cleanup restart-check` should say so before the plan is emitted.
