# Aspect: Log Analysis

Quantitative summary of `work.log`, `script.log`, and `decision.log` produced by a plan. The script `analyze-logs.py` produces the facts; this document instructs the LLM on how to interpret them.

## Inputs

Facts come from `plan-marshall:plan-retrospective:analyze-logs` which consumes the three log files via `plan-marshall:manage-logging:manage-logging read` (the only supported reader).

## TOON Fragment Shape

```toon
aspect: log_analysis
status: success
plan_id: {plan_id}
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
top_error_tags[5]{tag,count}:
  ...
global_log_signals:
  logs_present: true|false
  folded_log_files: N
  total_lines: N
  error_count: N
  slow_call_count: N
  fixture_leak_count: N
  fixture_leak_signatures[*]: [...]
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
counts and `logs_present: false`.

## LLM Interpretation Rules

- Treat `errors_work > 0` as a finding that MUST surface in the final report.
- Scripts at `p95_ms > 5000` are candidates for the LLM-to-script-opportunities aspect (slow-but-deterministic scripts often reveal batching opportunities).
- A `phases_seen` list missing an expected phase (e.g., `2-refine` absent when the plan was not opted out of refinement) is itself a finding — check `phase-2-refine` config.
- Only flag warnings when their count exceeds 5; individual warnings are not actionable noise.
- `global_log_signals.error_count > 0` is surfaced as a `warning` finding by the script; treat a non-zero count as evidence the plan's own execution produced error/non-INFO lines worth tracing in the script-failure-analysis aspect.
- `global_log_signals.fixture_leak_count > 0` is surfaced as an `error` finding — a synthetic test-fixture id in the plan's real folded-in logs means a test wrote to the real logs instead of an isolated `PLAN_BASE_DIR`; this is always a defect.
- `global_log_signals.slow_call_count` rides the fragment for context; cross-read with `script_duration_p95_ms` and the LLM-to-script-opportunities aspect.

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
