envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:20Z

# Lessons ingest: the pushed and merged head carries none of the plan's mandated gates

Severity: **critical** for the Antigravity instance (operator ruling 2026-10-12), high for the Claude Code recurrences. Bundle: `plan-marshall` (`phase-6-finalize` pre-push-quality-gate and push freshness, `manage-execution-manifest` verification-step composition, `phase-5-execute`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-127` | PLAN-41 (#34), Antigravity | Last `verify -Ppre-commit` at 08:30Z; then Spotless commits, a Sonar fix, new tests (11:05Z) and review fixes (11:37Z) were pushed with no later build and no pre-commit run. `verify -Pcoverage` never ran. The PR test plan describes earlier heads. |
| `pm-mcp-core-m2-m4-131` (items 2, 5) | PLAN-41 | The pre-push gate ran only whole-tree `test-compile`, not the quality gate; the freshness gate let the push through. |
| `pm-mcp-core-m2-m4-012` | primitive-spi-and-validators (#18), Claude | Four mandated gates (`verify`, `-Ppre-commit`, `-Pcoverage`, `-Pintegration-tests`) ran once in TASK-8 prose; four fix commits over three rounds re-ran only the two composed manifest steps. The merged head had no local coverage or IT run. |
| `pm-mcp-core-m2-m4-056` | PLAN-06 (#26), Claude | Same shape; the freshness check reported `required_coverage_unknown` and the plan still exited execute "fresh". |

Asked for: the pre-push gate compares the last gate's HEAD with the push HEAD and refuses when source changes lie between; gates a request or project done-rule names are composed into `phase_5.verification_steps` so every re-entry re-runs them; an execute exit refuses "fresh" under `required_coverage_unknown` for a plan that mandates coverage; PR test-plan checkboxes generated from build records for the pushed SHA.

Owner today: PLAN-LB-32 (`head-dependent-step-refire`, staged) is the nearest subject; PLAN-LB-23 (#1729) shipped verify builds. Neither is confirmed to cover the head-versus-gate check. Not re-checked at HEAD by the ingest.
