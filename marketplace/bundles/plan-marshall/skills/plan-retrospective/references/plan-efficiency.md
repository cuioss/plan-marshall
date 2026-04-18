# Aspect: Plan Efficiency

How much time and how many tokens did the plan consume relative to its scope? LLM-driven; inputs come from `metrics.md` and log counts produced by `analyze-logs.py`.

## Inputs

- `metrics.md` — total_duration_seconds, total_tokens, per-phase breakdown.
- `log_analysis` fragment (already computed) — entry counts, script durations.
- `references.json` `modified_files` — scope size.

## TOON Fragment Shape

```toon
aspect: plan_efficiency
status: success
plan_id: {plan_id}
totals:
  duration_seconds: N
  tokens: N
  files_modified: N
  tasks_completed: N
ratios:
  tokens_per_file_modified: N
  seconds_per_task: N
phase_breakdown[*]{phase,duration_seconds,tokens}:
  1-init,N,N
  ...
findings[*]{severity,message}:
  info,"Plan completed in 45 minutes"
  warning,"4-plan consumed 60% of tokens — consider outline refinement"
```

## LLM Interpretation Rules

- Benchmark ratios (approximate, per plan-marshall corpus):
  - `tokens_per_file_modified` > 50_000 → `warning` (excessive context for scope).
  - `seconds_per_task` > 900 (15 min) → `warning` (tasks too large).
- A single phase consuming > 50% of total tokens is a `warning`.
- `duration_seconds` less than 60 is `info` (fast plan); more than 3_600 (1 hour) is `info` only if scope justifies it.

## Finding Shape

```toon
aspect: plan_efficiency
severity: info|warning|error
message: "{one-line}"
metric: "{metric name + value}"
```

## Out of Scope

- Root-cause of individual slow scripts — log-analysis surfaces candidates; the detailed analysis is out of the retrospective's scope.
- Comparing against prior plans — this is a single-plan aspect.
