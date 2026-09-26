# PLAN-TRUTH-175: dispatch and phase-boundary measurement integrity — five confident zeros over unmeasured populations

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.

## Objective

Close five distinct measurement-integrity gaps in the metrics/finalize/build-ledger
stack, all surfaced by the same PLAN-TRUTH-143 retrospective and all the same shape:
an aggregate figure or a guard's violation count reads as a checked, honest value
while the population behind it was partially or entirely unmeasured. Each fix follows
the epic's own standing rule — publish the population a figure was computed over,
and use an unmeasured sentinel rather than a structural zero when a value could not
be captured.

## Deliverables

1. `boundary_monotonicity` (manage-metrics): derive its population from every phase
   block carrying both `start_time` and `end_time`, publish that population size
   beside the violation count, and assert `end_time >= start_time` per row — the
   guard currently reports zero violations over a store containing a 1h36m crossed
   boundary (PLAN-TRUTH-143's own `6-finalize`/`5-execute` pair). Add the
   cross-field consistency check between `start_time`/`end_time`/`duration_seconds`
   when all three are present on a phase block.
2. Dispatch-boundary token recording (manage-metrics): distinguish "this dispatch
   spent nothing" from "this dispatch's spend was not captured" — a row whose token
   attribution could not be read must record an unmeasured sentinel, not `0` (same
   discipline as the existing `inline_main_context_tokens: unmeasured`). Publish
   `rows_measured` / `rows_unmeasured` beside `dispatch_boundary_total`, and mark
   the total a FLOOR — ineligible to win a reconciliation-maximum comparison outright,
   or labelled as a floor when it does — whenever `rows_unmeasured > 0`.
3. `context_position_cost` (manage-metrics): populate the four component token
   columns (`input_tokens`, `output_tokens`, `cache_read_input_tokens`,
   `cache_creation_input_tokens`) at `record-dispatch-boundary` time from the same
   `<usage>` source the aggregate `total_tokens` already comes from, so
   `cache_read_per_tool_use` becomes computable. If the current target genuinely does
   not expose the breakdown, record that once as a target capability rather than
   leaving every row individually unmeasured.
4. `[DISPATCH]` work-log emission (phase-6-finalize): emit the `[DISPATCH]` line from
   the single shared dispatch seam in `phase-6-finalize` rather than per finalize-step
   site, so coverage is by construction. Have the finalize dispatcher compare its own
   dispatch count against its emitted line count at phase close and record the delta
   as a first-class gate signal. Qualify or rename `ran_inline` at publication so a
   reader cannot take a zero-token-attribution row as proof of inline execution.
5. Build-time oracle (manage-change-ledger): investigate why the change-ledger holds
   no row for a plan whose own script-execution log records 139 build calls —
   PLAN-TRUTH-143 ran with `use_worktree: true` and its retrospective read from the
   main checkout, which is the first candidate to test. Make the disagreement
   visible at `analyze-logs` time: emit a finding when `ledger_available: false` AND
   `log_build_calls > 0`. Keep the existing `unavailable`-not-zero rendering in
   `plan_efficiency` unchanged — it is working as designed.

## Claim Labels

- OBSERVED: `boundary_monotonicity` returned an empty violation list over
  `work/metrics.toon` recording `6-finalize` `end_time` (12:24:27Z) before
  `start_time` (14:00:01Z) — read from PLAN-TRUTH-143's retrospective finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Cites PLAN-TRUTH-143's work/metrics.toon. That plan's directory no longer exists (no match under .plan/local/plans/, no .plan/local/archive/ at all) - only the landing record survives, and trusting its restated figures is the very thing this epic forbids.
- OBSERVED: 41 of 77 `work/metrics-dispatch-boundaries-6-finalize.toon` rows record
  `total_tokens: 0` / `tool_uses: 0` / `duration_ms: 0` contiguous from a timestamp
  12 seconds after three logged `accumulate-agent-usage` argparse rejections — read
  from PLAN-TRUTH-143's retrospective finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Cites work/metrics-dispatch-boundaries-6-finalize.toon (41 of 77 rows) from the same unreachable PLAN-TRUTH-143 plan directory.
- OBSERVED: `context_position_cost` reported `measured_rows: 0` of `total_rows: 98`
  across all three dispatching phases on PLAN-TRUTH-143 — read from its retrospective
  finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: context_position_cost measured_rows: 0 of 98 is a PLAN-TRUTH-143 retrospective figure; the artifact is gone.
- OBSERVED: `check-dispatch-audit` found only 7 of 15 token-proven dispatched
  finalize steps carrying a `[DISPATCH]` line, `channel_completeness` ratio 0.104 —
  read from PLAN-TRUTH-143's retrospective finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: check-dispatch-audit 7-of-15 / channel_completeness 0.104 is a PLAN-TRUTH-143 retrospective figure; the artifact is gone.
- OBSERVED: `analyze-logs` reported `build_count: 0` / `ledger_available: false`
  beside `log_build_calls: 139` for PLAN-TRUTH-143 — read from its retrospective
  finding
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: build_count: 0 / ledger_available: false beside log_build_calls: 139 is a PLAN-TRUTH-143 retrospective figure; the artifact is gone.
- Verify-first clause: confirm current line numbers and exact field names at outline
  before scoping each of the five deliverables against HEAD — all five are first-party
  retrospective findings, none independently re-read by the orchestrator before
  staging.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md`
- OBSERVED: `test/plan-marshall/manage-metrics/**`
- OBSERVED: `test/plan-marshall/phase-6-finalize/**`
- OBSERVED: `test/plan-marshall/manage-change-ledger/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none known against the current live queue
- Adjacent to: PLAN-TRUTH-174 (plan-retrospective measurement integrity) — same
  retrospective source plan, disjoint component surface

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-175-dispatch-and-phase-boundary-measurement-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
