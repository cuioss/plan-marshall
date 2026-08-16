# Aspect: Log Analysis

Quantitative summary of `work.log`, `script.log`, and `decision.log` produced by a plan. The script `analyze-logs.py` produces the facts; this document instructs the LLM on how to interpret them.

## Inputs

Facts come from `plan-marshall:plan-retrospective:analyze-logs` which consumes the three log files via `plan-marshall:manage-logging:manage-logging read` (the only supported reader).

## TOON Fragment Shape

```toon
aspect: log_analysis
status: success
plan_id: {plan_id}
build_time:
  # Build time from the change-ledger (the build-time ORACLE) — spans every build
  # system and every phase. total_build_seconds sums valid (> 0) durations ONLY;
  # a zero / absent duration is counted in suspect_count and NOT summed (a floor
  # when suspect_count > 0). `killed` is SEPARATE from `error`. build_count: 0 =
  # no ledger rows = build time UNAVAILABLE (absent is not zero). The
  # `plan_efficiency` aspect READS total_build_seconds from here into its totals.
  total_build_seconds: NUM
  build_count: N
  suspect_count: N
  pass: N
  error: N
  timeout: N
  killed: N
counts:
  work_entries: N
  decision_entries: N
  script_entries: N
  errors_work: N
  errors_script: N
  warnings_work: N
  warnings_script: N
phases_seen[*]: [1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize]
script_duration_p50_ms: NUM
script_duration_p95_ms: NUM
script_duration_max_ms: NUM
slowest_scripts[3]{notation,duration_ms}:
  ...
script_cost_rollup:
  # CUMULATIVE cost over the SAME lines the percentiles above summarise per-call.
  # `slowest_scripts` ranks by the largest SINGLE call; this ranks by total time
  # owned, so a script that never appears in `slowest_scripts` can top this list.
  # `ranked` is capped at 10 — compare `ranked_count` against `distinct_scripts`
  # to see whether a tail was truncated; the totals always span the whole
  # population, so the residual stays derivable.
  population: plan_script_execution_log
  ceiling_seconds: 30.0
  calls_at_or_over_ceiling: N
  total_calls: N
  total_duration_ms: NUM
  distinct_scripts: N
  ranked_count: N
  ranked[*]{notation,calls,cumulative_ms,share_pct,max_ms}:
    ...
top_error_tags[5]{tag,count}:
  ...
context_position_cost:
  # Unit: CACHED-READ INPUT TOKENS per tool use, BY PHASE — cost as a function of
  # WHERE a step runs, not only what it does. A different currency from
  # `script_cost_rollup` above (which is wall-clock); never add or compare them.
  #
  # And a PARTITION, not a whole: cache-read is ONE of four context-load columns
  # (input, output, cache-read, cache-creation). Every figure here is over that
  # one partition, so a multiple is a multiple on cached-read tokens and is NOT
  # a share of, or a ratio over, the token total.
  #
  # Two DISTINCT exclusion causes, counted apart because they need different
  # remedies: `unmeasured_rows` (the row is missing either half of the rate — a
  # cache-read value or a usable `tool_uses` denominator) and `no_tool_use_rows`
  # (both recorded, `tool_uses` exactly 0, so the ratio is undefined). Neither is
  # ever folded in as a zero. measured + unmeasured + no_tool_use reconciles to
  # total_rows.
  total_rows: N
  measured_rows: N
  unmeasured_rows: N
  no_tool_use_rows: N
  # cache_read_per_tool_use is a float, or `undefined` when the phase has a
  # zero-tool-use row and NO unmeasured row (record complete, ratio has no
  # value), or `unmeasured` in every other no-contribution case — including a
  # phase with no rows at all. `unmeasured` is the weaker claim and the default.
  by_phase[*]{phase,rows,measured_rows,cache_read_per_tool_use}:
    ...
  position_multiple: NUM|unmeasured|undefined
  position_multiple_basis: "{highest_phase}/{lowest_phase}"|unmeasured|undefined
global_log_signals:
  logs_present: true|false
  folded_log_files: N
  total_lines: N
  error_count: N
  slow_call_count: N
  fixture_leak_count: N
  fixture_leak_signatures[*]: [...]
  # Duration-bearing lines with no parseable notation: evaluated against the
  # ceiling like any other timed line, but excluded from the roll-up (which
  # cannot attribute a total to a script it cannot name). So `cost_rollup.calls_at_or_over_ceiling` can be lower than
  # `slow_call_count` — and this field BOUNDS that gap rather than equalling it,
  # because it counts unnamed calls at every duration while the gap counts only
  # the unnamed calls at or over the ceiling.
  unattributable_calls: N
  cost_rollup:
    # The cumulative complement to `slow_call_count`. Same shape as
    # `script_cost_rollup` above, different population.
    population: folded_global_logs
    ...
```

## Folded-in global logs

Under the move-based finalize model the plan's OWN global logs
(`{prefix}-YYYY-MM-DD.log`) are folded into `<plan_dir>/logs/` at
integrate-into-main. `analyze-logs` parses those folded-in copies for per-plan
operational signals (`global_log_signals`) — a complement to the cross-plan
`global-log-analysis` audit check (which does cross-plan live-corpus correlation
over phases 1-4); the per-plan view here surfaces each plan's own folded-in
signals. A plan with no folded-in
global logs (live mode before finalize, pre-fold archives) yields all-zero
counts and `logs_present: false`; its `cost_rollup` is a fully-populated
ZERO-valued fragment (a published `total_calls: 0` with an empty `ranked` list),
never an absent or empty one, so a consumer reads a measured nothing rather than
a missing key.

## LLM Interpretation Rules

- Treat `errors_work > 0` as a finding that MUST surface in the final report.
- Scripts at `p95_ms > 5000` are candidates for the LLM-to-script-opportunities aspect (slow-but-deterministic scripts often reveal batching opportunities).
- A `phases_seen` list missing an expected phase (e.g., `2-refine` absent when the plan was not opted out of refinement) is itself a finding — check `phase-2-refine` config.
- Only flag warnings when their count exceeds 5; individual warnings are not actionable noise.
- `global_log_signals.error_count > 0` is surfaced as a `warning` finding by the script; treat a non-zero count as evidence the plan's own execution produced error/non-INFO lines worth tracing in the script-failure-analysis aspect.
- `global_log_signals.fixture_leak_count > 0` is surfaced as an `error` finding — a synthetic test-fixture id in the plan's real folded-in logs means a test wrote to the real logs instead of an isolated `PLAN_BASE_DIR`; this is always a defect.
- `global_log_signals.slow_call_count` rides the fragment for context; cross-read with `script_duration_p95_ms` and the LLM-to-script-opportunities aspect.
- **Read the ceiling and the roll-up together — neither answers the other's question.** `slow_call_count` and the `script_duration_*` percentiles answer *"is any single call pathological?"*. They are structurally incapable of answering *"what dominates total time?"*: a call at a fraction of a percent of the 30s ceiling, repeated a hundred thousand times, is invisible to every one of them by construction, not by oversight. `script_cost_rollup` / `global_log_signals.cost_rollup` answer the second question. A script ranked first with `calls_at_or_over_ceiling: 0` is exactly that dominant-but-fast class — treat it as a finding even though no per-call signal fired.
- ⛔ **The roll-up is WALL-CLOCK, not billing.** The script-execution log carries no per-call token measurement, so a `share_pct` here does **not** convert into a share of cost. A ranking from this roll-up is an operator-**latency** finding; say which currency you are quoting, and never restate a wall-clock share as a cost share.
- `context_position_cost.position_multiple` reports how many times more **cached-read input tokens** a tool use consumes in the most expensive phase than in the cheapest — a **token** figure, and so a different currency from the wall-clock roll-up above; never add or compare the two — the same mechanical step late in a long phase re-reads a far larger accumulated context. Quote it only with `position_multiple_basis` (which two phases it compares) and `measured_rows` (how many rows it rests on). ⛔ It is also a **partition, not a whole** — cached-read is one of four context-load columns, so a 10x multiple is 10x on cached-read tokens, never 10x on billed cost. A literal `unmeasured` means the corpus could not support the figure — it is never a zero. A literal `undefined` means something different and must not be read as a recording gap: the record is COMPLETE and the ratio still cannot be formed (fewer than two rated phases is `unmeasured`; a zero denominator is `undefined`).

## Finding Shape

When the LLM produces findings from this fragment, each finding takes the shape:

```toon
aspect: log_analysis
severity: info|warning|error
message: "{one-line summary}"
evidence: "{log tag or count that supports the finding}"
```

## Out of Scope

- Root-cause of individual errors — that is the script-failure-analysis aspect.
- Missing log entries for coverage — that is the logging-gap-analysis aspect.
