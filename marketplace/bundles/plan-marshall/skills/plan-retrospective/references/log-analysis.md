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
```

## LLM Interpretation Rules

- Treat `errors_work > 0` as a finding that MUST surface in the final report.
- Scripts at `p95_ms > 5000` are candidates for the LLM-to-script-opportunities aspect (slow-but-deterministic scripts often reveal batching opportunities).
- A `phases_seen` list missing an expected phase (e.g., `2-refine` absent when the plan was not opted out of refinement) is itself a finding — check `phase-2-refine` config.
- Only flag warnings when their count exceeds 5; individual warnings are not actionable noise.

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
