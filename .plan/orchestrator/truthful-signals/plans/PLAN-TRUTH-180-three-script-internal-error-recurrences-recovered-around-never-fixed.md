# PLAN-TRUTH-180: Three script-internal-error recurrences recovered around, never fixed

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-25 from three candidate-lessons filed by unorchestrated plan
`truth-179-opencode-target-detection-landed` (PR #1619, merged). Each fired repeatedly
inside one run (7x / 7x / 5x), each was retried or routed around, none was fixed. Archived
evidence: `.plan/orchestrator/truthful-signals/inbox/archive/truth-179-opencode-target-detection-landed/truth-179-opencode-target-detection-landed-001.md`
through `-003.md`, plus that plan's archived `logs/script-execution.log` at the cited
timestamps.

## Objective

**Three scripts fail internally, repeatedly, and every run walks around them.**
`manage-status transition` (7x, silent stderr), `scope_creep_check check` (7x at execute-phase
entry), and `manage-config effort` (5x, traceback naming a `_cmd_finalize` import) all exit 1
from inside their own handlers. Recovered-around failures are invisible failures: the runs
land, so nothing ever compels the fix, and the next run pays the same retries.

## Deliverables

Three deliverables. D0 owns the reproduction; D1 the fixes; D2 the pins.

**D0 — GATE: reproduce all three from the archived logs and publish the population.** Re-run
the transition sequence from `script-execution.log` around 2026-09-24T16:54:23Z, the
scope-creep sequence around 2026-09-24T08:33:59Z, and the effort import from the captured
traceback. ⛔ Publish each root cause or record it as undetermined with the evidence that
defeated the derivation — a member that cannot be reproduced is not a member that is fixed.

**D1 — Fix each reproduced root cause.** The `manage-config` member already names its suspect
(the `_cmd_finalize` import in `manage-config.py`); the other two take whatever D0 establishes.
A fix that only adds retries is a refusal, not a remedy.

**D2 — Regression tests invoking each subcommand clean.** One test per member exercising the
previously-failing path to a clean exit.

## Claim Labels

- OBSERVED: 7 `script_internal_error` hits on `manage-status transition`, first 2026-09-24T16:54:23Z, stderr silent — re-verify at outline against the archived log.
  - verdict: unverifiable | checked_at: e995df45c | by: truthful-signals/cleanup | rescoped: n/a | evidence: Archived script-execution.log around 2026-09-24T16:54:23Z not re-read at cleanup time; D0 owns reproduction per the spec itself
  - Filed 2026-09-25 by the executing plan; cause unknown by the filer's own account.
- OBSERVED: 7 `script_internal_error` hits on `scope_creep_check check`, first 2026-09-24T08:33:59Z — re-verify at outline against the archived log.
  - verdict: unverifiable | checked_at: e995df45c | by: truthful-signals/cleanup | rescoped: n/a | evidence: Archived script-execution.log around 2026-09-24T08:33:59Z not re-read at cleanup time; D0 owns reproduction per the spec itself
  - Filed 2026-09-25 by the executing plan; cause unknown by the filer's own account.
- OBSERVED: 5 `script_internal_error` hits on `manage-config effort` with a traceback naming the `_cmd_finalize` import — re-verify at outline against the archived log and the import line.
  - verdict: unverifiable | checked_at: e995df45c | by: truthful-signals/cleanup | rescoped: n/a | evidence: Named _cmd_finalize import suspect not re-read against manage-config.py at cleanup time; D0 owns confirmation per the spec itself
  - Filed 2026-09-25 by the executing plan with a named suspect.
- ⚠ HYPOTHESIS: the three share one handler-shape cause — ⛔ asserted by nobody; D0 decides (verify-at-outline).
  - verdict: unverifiable | checked_at: e995df45c | by: truthful-signals/cleanup | rescoped: n/a | evidence: Single-cause hypothesis not adjudicated at cleanup time; D0 decides per the spec itself

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — transition handler (D0, D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — check handler (D0, D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` — effort import (D0, D1)
- HYPOTHESIS: `test/plan-marshall/manage-status/`, `test/plan-marshall/phase-5-execute/`, `test/plan-marshall/manage-config/` — D2's regressions (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Shares `manage-status/**` with staged PLAN-TRUTH-147-shipped residue (none — shipped), -156 (parked), -170, -171; `phase-5-execute/**` with -145/-147(shipped)/-175; `manage-config/**` with -168 — sequence, never pair (N=1 makes this automatic, recorded so a future scope change keeps it).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-180-three-script-internal-error-recurrences-recovered-around-never-fixed.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
