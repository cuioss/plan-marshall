envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:18Z

# Lessons ingest: under Antigravity, phase 5 dispatches no sub-agent — tasks run inline and leave no trail

Severity: **critical** (operator ruling 2026-10-12: Antigravity issues are the highest priority — they prevent Antigravity from working). Bundle: `plan-marshall` (`phase-5-execute`, `platform-runtime`, `manage-status`) plus the Antigravity/OpenCode target rules under `marketplace/targets/`.

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, PLAN-41 `plan-41-static-verifier-remaining-rules` (pm-mcp-core PR #34, merge `ebe82b3`), the first plan of that epic run under Antigravity. Evidence: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-133` | Root cause. `Task: plan-marshall:execution-context-{level}` has no meaning on Antigravity; `phase-5-execute` has no wiring to Antigravity's `invoke_subagent` (nor OpenCode's sub-agent mechanism). The top-level agent ran all 8 tasks inline in one session (1,200+ lines in 27 minutes). Context decay followed by shortcuts — see the separate completion/test-weakening message. |
| `pm-mcp-core-m2-m4-125` | Phase boundaries not closed: 4-plan has no end, 5-execute no start (`any_phase_missing_end_time=true`). Decision log has no entry between 06:52Z and 08:34Z; zero dispatch-boundary rows; four feature commits landed in that window. The orchestrator had to reconstruct execute from git history. |

Asked for: native sub-agent dispatch per harness (Antigravity `invoke_subagent`, OpenCode sub-agents) with return/usage propagation; refuse inline batch execution where sub-agents exist; the phase transition refuses to advance over a missing end marker; finalize fails closed (or warns loudly) when execute produced commits but recorded no task completion.

Owner today: none found. PLAN-LB-29 (`harness-sync`, running) owns the target emitters, not runtime dispatch. Ground truth not re-checked at ingest beyond the sender's own verification against the archived plan.
