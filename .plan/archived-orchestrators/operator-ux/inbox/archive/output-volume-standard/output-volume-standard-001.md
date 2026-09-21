envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T11:09:45Z

# Classify executor invalid_invocation rejections from stdout, not stderr alone

component: plan-marshall:plan-retrospective
category: improvement
confidence: high
source_plan: output-volume-standard
source_aspects: script_failure_analysis, logging_gap_analysis

## Context

`plan-marshall:plan-retrospective:script-failure-analysis` classifies a failed script
call by matching its **stderr** against three argparse signatures: `invalid choice:` →
`invented_subcommand`, `the following arguments are required:` → `missing_required_flag`,
`unrecognized arguments:` → `invented_flag`.

On this plan, 4 script failures were recorded and 3 of them carried an **empty**
`stderr_excerpt`. All 4 were bucketed as the residual `argparse_other` — the two precise
subtypes that exist specifically to name the project's documented recurrence signatures
never fired.

## Root cause

The executor (`.plan/execute-script.py`) runs a pre-flight `invalid_invocation` guard that
rejects an unregistered verb or an undeclared flag **before argparse is ever reached**, and
it writes its structured diagnosis to **stdout**, not stderr:

```
args: read --plan-id output-volume-standard --phase 6-finalize
stdout: status: error  error: invalid_invocation  reason: unknown_flag
        rejected: --phase  accepted: plan-id, store
```

```
args: read --plan-id output-volume-standard --document request
stdout: status: error  error: invalid_invocation  reason: unknown_verb
        rejected: read  accepted: list-types, request
```

So the most common rejection path in the system produces a machine-readable cause on a
channel the classifier does not read, while the channel it does read is empty. The
classifier is not wrong about argparse — it simply never sees the guard that fires first.

## Proposed action

Extend `script-failure-analysis`'s classifier to read the recorded **stdout** block as well
as stderr, and map the guard's own `reason` field directly — it is already more precise than
the stderr regexes:

| guard `reason` | subtype |
|---|---|
| `unknown_verb` | `invented_subcommand` |
| `unknown_flag` | `invented_flag` |

Keep the stderr signatures as the fallback for calls that do reach argparse. Also surface the
guard's `accepted:` list in the finding detail, since it names the correct form and turns each
finding into an actionable correction rather than a bare rejection notice.

## Evidence

- aspect: `script_failure_analysis` — 4 failures, 4 unique; 3 with `stderr_excerpt: ""`; every
  one classified `argparse_other`; `invented_subcommand` / `invented_flag` fired zero times.
- aspect: `logging_gap_analysis` — recorded as an `ERROR`-category gap: the failures are
  recorded but their cause is not recoverable through the classifier.
- raw log: `.plan/local/plans/output-volume-standard/logs/script-execution.log` lines 873-876
  and 936-939 carry both guard rejections with their full stdout bodies.
