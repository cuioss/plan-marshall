envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:19Z

# Lessons ingest: an Antigravity run records zero tokens as a real number and no plan records its harness

Severity: **critical** (operator ruling 2026-10-12: Antigravity issues are the highest priority). Bundle: `plan-marshall` (`platform-runtime`, `manage-metrics`, `manage-execution-manifest record-step`, `plan-orchestrator preflight`, `phase-1-init`).

Source: pm-mcp-core PLAN-41 (PR #34), Antigravity. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-124` | Every `record-step` reads `unmeasured`; `metrics.md` shows `-` throughout; the landing-facts block carries `total_tokens=0`, which passes `landing-check` as complete. A plan with no measurement is indistinguishable from a free one. |
| `pm-mcp-core-m2-m4-132` | No archived plan of the epic (11 Claude Code plans and the Antigravity one) has a `client.toon`: nothing on the `/plan-marshall` start path calls `orchestrator preflight`. The only traces of Antigravity were incidental. The orchestrator cannot tell harnesses apart mechanically, so it cannot apply the stricter Antigravity verification. |

Asked for: a transcript-less runtime emits `total_tokens=unknown`, not `0`; a `transcripts: none` capability flag in the metrics header; `phase-1-init` runs the preflight hook and stamps `harness` into `status.json` metadata; a `harness=` landing-facts key `landing-check` reports.

Owner today: none found. Not re-checked at HEAD by the ingest.
