# Aspect: Logging Gap Analysis

Identifies places where the LLM or a component should have logged but didn't — gaps make plan introspection harder and invalidate log-analysis findings. LLM-driven; inputs include the existing logs and the skill references that drive the plan.

## Inputs

- `work.log`, `decision.log`, `script.log` — what was actually logged.
- Skill reference documents in scope (loaded from marketplace based on `references.json` domains).
- `references.json` `modified_files` — evidence of actions that should produce log entries.

## Expected Log Patterns

Phase skills are expected to emit:
- `[STATUS] (plan-marshall:{skill}) Starting {phase} — ...` at entry.
- `[STATUS] (plan-marshall:{skill}) Completed {phase}` at exit.
- `[DECISION] (plan-marshall:{skill}:{sub}) ...` for each non-trivial choice.
- `[ARTIFACT] (plan-marshall:{skill}) ...` when an artifact is produced.
- `[VERIFY] (plan-marshall:{skill}) ...` when verification runs.
- `[ERROR] (plan-marshall:{skill}) ...` on any error.

## TOON Fragment Shape

```toon
aspect: logging_gap_analysis
status: success
plan_id: {plan_id}
expected_vs_actual[*]{category,expected_min,observed}:
  STATUS,12,10
  DECISION,6,2
  ARTIFACT,8,8
  VERIFY,6,6
  ERROR,any,3
gaps[*]{skill_or_phase,category,detail}:
  phase-3-outline,DECISION,"0 decision entries — deliverable packaging decisions not logged"
findings[*]{severity,message}:
  warning,"Decision log sparse in outline phase"
```

## LLM Interpretation Rules

- The ratio `observed / expected_min < 0.5` is a `warning`.
- Zero `DECISION` entries in phases that made visible choices (outline packaging, plan task ordering) is always a `warning`.
- Zero `ARTIFACT` entries is an `error` — artifacts were produced but not announced.
- `ERROR` entries are expected to be zero; count them but do not flag count itself — the errors surface via log-analysis / script-failure-analysis.

## Finding Shape

```toon
aspect: logging_gap_analysis
severity: info|warning|error
category: STATUS|DECISION|ARTIFACT|VERIFY|ERROR
skill_or_phase: "{scope}"
message: "{one-line}"
```

## Out of Scope

- Proposing new log statements line-by-line — emit findings, not diffs.
- Parsing of log bodies beyond tag counts — log-analysis owns that.
