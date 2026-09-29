envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=truthful-signals
kind=finding
created=2026-09-28T17:26:35Z

# Recurrences for PLAN-TRUTH-169, PLAN-TRUTH-150 / PLAN-205, and PLAN-TRUTH-175 (from the PLAN-13 run)

**Sender:** `process-compliance` orchestrator, drain 2026-09-28. Routed here because each item matches a
spec in this epic's corpus; process-compliance does not stage it. Source: `process-compliance` inbox
`plan-13-finalize-mechanism-defects-004` (items 5, 21, 22) and `-006` (candidate lesson), archived at
`.plan/orchestrator/process-compliance/inbox/archive/plan-13-finalize-mechanism-defects/`. Run-reported,
not re-verified by process-compliance.

## → PLAN-TRUTH-169 (a timeout verdict describes the wait, not the work)

## 5. The 10-minute Bash ceiling vs. "do not background the daemon wait"

`await-long-running.md` says the build consumer must not `run_in_background` or `sleep` the daemon wait.
Every orchestrator-tier build here exceeded the harness's 600s per-call ceiling (resolved budgets 745–1437s),
so the harness moved each call to the background anyway. The rule cannot be honoured as written; the build
client needs a bounded wait shorter than the harness ceiling with an explicit re-poll.

## 22. The ci-complete wait clamps at 569s, so every CI run here needs 3+ blind re-waits

`ci_complete_precondition resolve` clamps its timeout to 569s (below the Bash ceiling), but this repo's
`verify` CI job takes ~25 min. The first two waits returned `wait_failed / ci_final_status: timeout`
with every check still IN_PROGRESS and none failed. ci-verify's contract would classify that as
`ci_timeout` findings and route them to LLM triage. The orchestrator had to re-run the wait by hand,
which no document describes. A non-terminal in-progress run should resolve as "pending, re-wait", not
as a timeout verdict.

## → PLAN-TRUTH-150 / PLAN-205 (`build_scope_narrow` freshness refusal)

## 21. pre-push-quality-gate's own builds can never satisfy the push freshness gate it anchors

The gate doc claims its just-completed builds are what make `default:push`'s freshness precondition pass
("only this gate's just-completed builds can have written [the ledger row] for the settled tree"). In
this run all four arms went green on the exact tree (quality-gate ×2, test-compile, 28128-test
module-tests), yet `pre-commit-verify-freshness` refused with `stale: build_scope_narrow` — every row is
`canonical_performs_too_few_analyses`, because the gate accepts only a single `verify` row. The finalize
pipeline therefore always pays a second full `verify` (~40 min) after the gate, or the push halts. Either
the gate should run `verify` (it already runs its three arms) or freshness should accept the union of
rows at one sha that together cover compile+lint+test.

## → PLAN-TRUTH-175 (dispatch and phase-boundary measurement integrity)

The candidate lesson below adds the `--step-id` facet (25 of 30 finalize and 8 of 9 execute boundary
rows keyless) beside the `[DISPATCH]` emission gap 175 already owns.

# Forward step_id and emit DISPATCH on every finalize and execute dispatch record

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_aspects: execution_context_dispatch_audit, logging_gap_analysis

## Context

In plan-13-finalize-mechanism-defects, 25 of 30 `6-finalize` dispatch-boundary rows and 8 of 9
`5-execute` rows were recorded without `--step-id`, so `check-dispatch-audit`'s
`firing_comparison` paired only 3 of 30 finalize dispatches with their `record-step` rows and
fell back to timestamp windows for the rest. Separately, 7 finalize steps carry token proof of a
dispatched envelope but only 4 distinct finalize-dispatcher `[DISPATCH]` lines exist, so
`missing_dispatch_emission` is 3 (a floor) and the dispatch channel is graded `confidence: low`.

## Root cause

Both audit channels depend on the orchestrator hand-issuing the recording calls with the right
identity after each return: `record-dispatch-boundary --step-id` is documented as "forward on
EVERY call" but is optional at argparse, and the `[DISPATCH]` line is only emitted when the
resolve call carries `--workflow`. Neither omission fails anything, so the audit degrades
silently over a long finalize with many re-fires.

## Proposed action

1. In the `phase-6-finalize` dispatcher (item 5 post-return block) and `plan-marshall/workflow/execution.md`,
   make `--step-id {step_id}` part of the literal `record-dispatch-boundary` invocation, not prose.
2. Make the dispatch-boundary recorder warn (or refuse) when `--step-id` is absent for a phase
   whose dispatches always have a step key (`6-finalize`).
3. Check that every finalize dispatch site resolves with `--workflow` so the seam emits
   `[DISPATCH]` itself; add a test that the count of dispatched finalize steps equals the count
   of finalize-dispatcher `[DISPATCH]` lines on a fixture run.

## Evidence

- aspect: execution_context_dispatch_audit — `firing_comparison` 6-finalize: `boundary_rows: 30`, `keyless_boundary_rows: 25`, `paired_firings: 3`; `missing_dispatch_emission: 3`, `channel_completeness.confidence: low`
- aspect: logging_gap_analysis — 5-execute `keyless_boundary_rows: 8` of 9
