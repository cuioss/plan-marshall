# PLAN-07: Degrade session identity on transcript-less targets instead of aborting

epic: finalize-machinery
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-07-session-identity.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Fix the session-identity abstraction bug that hard-blocked finalize on two green plans:
on targets exposing no session concept the execution.md resolver aborts the shipping
pipeline over telemetry that is a documented no-op there. Ship a target-aware resolver
that proceeds unenriched with a logged decision where no transcript can exist, while
keeping the hard block where an absent identity means a broken hook.

## Deliverables

1. Target-aware finalize session resolver: when the active target exposes no session
   identifier (`bind` → `no_session_id`), proceed unenriched with a logged decision
   instead of aborting; keep the hard block for the Claude target.
2. Input-contract update: `session_id` demoted from required to optional on the
   phase-6-finalize contract (or the abort gated on transcript availability), with
   `record-metrics` skipping `enrich` when absent and carrying the gap flag.
3. Regression evidence: one test proving the Claude path still aborts on absent
   identity, one proving a transcript-less target proceeds with the logged decision
   and unenriched metrics.

## Claim Labels

- OBSERVED: two plans (plan-03-review-currency, git-branch-mechanics) were hard-blocked at 6-finalize entry on the opencode target with session_ids absent, hook_not_configured, and bind → no_session_id — read at `.plan/orchestrator/finalize-machinery/inbox/archive/plan-03-review-currency/plan-03-review-currency-003.md` § `abstraction bug`
  - verdict: corroborated | checked_at: ba0317c | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1530: both plans hard-block confirmed; target-aware resolver ships, hook block kept on transcript-capable targets
- OBSERVED: second-plan confirmation with operator-override precedent — plan-03 hit the same block, proceeded under explicit operator direction with sentinel NO_SESSION_IDENTITY and zero enrichment loss beyond the documented no-op; the override path is proven, the structural fix is still owed — read at inbox message plan-03-review-currency-012 (folded here as recurrence, 2026-09-17 drain)
  - verdict: corroborated | checked_at: ba0317c | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1530: override precedent confirmed by this run (NO_SESSION_IDENTITY sentinel, metrics closed unenriched); structural fix now shipped
- OBSERVED: session identity's sole downstream consumer is metrics enrichment, which returns a documented no-op (transcript_not_found) on OpenCode — read at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` § `no session id`
  - verdict: corroborated | checked_at: ba0317c | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1530: enrich-skip with population-carrying gap flag; sole-consumer claim holds, metrics closed unenriched per override
- HYPOTHESIS: gating the abort on transcript availability (target capability) closes the strand-green-plans failure while preserving the broken-hook signal on Claude — confirm/refute at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py` § `bind` (verify-at-outline)
  - verdict: corroborated | checked_at: ba0317c | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1530: target-aware resolver + session-optional contract + regression tests pinning both routings; holder behavior unchanged
- Verify-first clause: the consuming phase confirms the resolver, contract, and enrich-degradation paths against the implementing sources at HEAD before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py` — bind/no_session_id seam
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — finalize resolver contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` — enrich-skip and gap flag
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — transcript-less target behavior

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged — platform-runtime/record-metrics surface is new to this corpus
- Adjacent to: PLAN-05 lessons-pipeline (metrics reporting) — different files, no shared surface

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-07-session-identity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
