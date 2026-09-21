envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:45Z

component=plan-marshall:tools-script-executor
category=improvement
confidence=medium
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=script_failure_analysis

# Notation third-part drift produces four separate internal errors per plan

## Context

Four of this plan's sixteen unique script failures are `script_internal_error` entries that are all the same mistake:

| Rejected notation | Timestamp |
|-------------------|-----------|
| `plan-marshall:manage-architecture:manage-architecture` | 2026-09-19T11:22:31Z |
| `plan-marshall:manage-ci-artifacts:manage_ci_artifacts` | 2026-09-19T13:05:49Z |
| `plan-marshall:phase-6-finalize:phase_handshake` | 2026-09-19T17:39:01Z |
| `plan-marshall:manage-status:manage_status` | 2026-09-19T18:20:31Z |

Each produced the identical diagnostic shape:

```
Invalid notation: '...'
The third part '...' appears to be a subcommand, not a script name.
Correct format: plan-marshall:manage-status:manage-stat...
```

Two distinct sub-shapes are visible: underscore-for-hyphen in the script-name segment (`manage_status`, `manage_ci_artifacts`, `phase_handshake`), and a correct-looking-but-wrong repeat of the skill name (`manage-architecture:manage-architecture`). The second is especially easy to produce because for most skills the third segment *is* the skill name with the same spelling.

## Root cause

The executor already detects the shape precisely and already knows the correct answer — it prints it in the error. It simply declines to act on it. The caller pays an exit-2 round trip, re-reads the message, and retries; four times per plan.

Note that these are recorded as `bug` / `script_internal_error` by `script-failure-analysis`, which is misleading in aggregate: nothing in the executor is broken, and the four rows inflate the plan's internal-error count.

## Proposed action

Emit a single copy-pasteable did-you-mean line as the last line of the diagnostic, e.g.:

```
did-you-mean: plan-marshall:manage-status:manage-status read --plan-id ...
```

reconstructing the full original argv with only the notation corrected. Auto-correcting silently is the wrong trade (it would hide genuine typos), but handing back the exact corrected command removes the re-derivation step.

Separately, consider reclassifying executor-rejected notations out of `script_internal_error` into their own `invalid_notation` subtype in `script-failure-analysis`, so an executor guard firing correctly does not read as a script bug.

## Evidence

- aspect: script_failure_analysis — four `script_internal_error` rows, all with `Invalid notation:` stderr, `occurrence_count: 1` each
- the diagnostic already contains the corrected notation in every one of the four
