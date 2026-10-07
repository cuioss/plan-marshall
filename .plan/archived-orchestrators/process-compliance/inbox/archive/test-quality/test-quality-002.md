envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-20T20:08:19Z

# PLAN-140 emission underspecified — process-rule issue

## Observation
- Operator task: `implement .plan/local/orchestrator/test-quality/plans/PLAN-140-module-budget-campaign-runs-2-7.md`
- PLAN-140 Hand-Off Command requires `run {N}, slice {NNN}` (spec: "EMITS ONE RUN AT A TIME. Each emission takes exactly one row").
- No run/slice was supplied. Ledger `resume_anchor` names run 3 (slice 060) EMITTED awaiting operator-confirmed launch; queue shows PLAN-140 `launched` and PLAN-176 (run 2, slice 040) `shipped`.
- Proceeding without an explicit run would violate the one-row-per-PR rule and risks taking two rows.

## Process-rule references
- `test-quality/plans/PLAN-140-...md` § "This spec is emitted ONE RUN AT A TIME" + Hand-Off Command
- Orchestration `resume_anchor` contract (status.json is machine authority)
- AGENTS.md `.plan/` access via scripts only (this filing uses `orchestrator inbox write`; spec read via `corpus read`; queue via `queue`; resume via `resume-summary`; inbox presence via `inbox list` — no direct `.plan/` Read/Write/Edit)

## Action taken
- Filed here instead of proceeding silently. Awaiting operator confirmation of run scope before any D1-D5 work.
- Suggested default: run 3, slice 060 (PLAN-060's fourteen directories under `test/plan-marshall/`), per resume anchor and next-in-queue order.

## Request
- Confirm run 3 slice 060, or name a different run/slice, before implementation starts.
