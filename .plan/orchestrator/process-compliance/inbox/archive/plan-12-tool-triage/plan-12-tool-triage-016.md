envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:56Z

# `record-dispatch-boundary` stores absent token flags as a measured 0

**Observed (plan-12-tool-triage, finalize `create-pr`):** the subagent's hand-back message arrived before its task-notification carrying the `<usage>` tag. The orchestrator ran item 5c `record-dispatch-boundary --termination-cause step_complete` without the three token flags. The verb accepted the call and persisted `total_tokens: 0, tool_uses: 0, duration_ms: 0` — while in the same payload marking four context-load columns `unmeasured`. The measured usage (120247 / 28 / 99191 ms) arrived seconds later.

**Two defects:**
1. **Tool:** `record-dispatch-boundary` should either require the token triple or record its absence as `unmeasured`, exactly as `record-step` does (phase-6-finalize SKILL item 5e forbids a fabricated `0` for an unmeasured column; this verb produces one silently). The row is now byte-identical to a measured zero-cost dispatch and cannot be corrected through any documented verb.
2. **Process:** SKILL item 5b/5c say "extract from the agent's `<usage>` tag" but do not say the usage tag may arrive in a separate, later notification than the agent's report. The orchestrator error (recording before the usage arrived) is mine; the doc should state that items 5b-5e wait for the completion notification carrying `<usage>`.

A WARNING decision-log entry records the bad row (row 17) and the measured values.

**Recurred later in the same run** (5-execute boundary row 15, TASK-21/22 envelope): the orchestrator again recorded the boundary before the `<usage>` notification arrived and the verb again stored a silent 0 triple. A second WARNING records it. That the same operator error recurred once the context was long is itself the argument for the tool-side fix — the verb must refuse or record `unmeasured` rather than rely on the caller's ordering.
