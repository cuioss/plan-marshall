envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:38Z

# self_review surface exits 1 with empty stderr on repeat invocation

## Metadata

- component: `pm-plugin-development:ext-self-review-plan-marshall`
- category: bug
- confidence: medium
- observed_in_plan: verdict-staleness-scoping

## Context

`script-failure-analysis` classified two occurrences of
`pm-plugin-development:ext-self-review-plan-marshall:self_review surface` exiting 1 as
`script_internal_error`, first seen at 2026-09-22T14:53:51Z. The recorded `stderr_excerpt` is
empty, so the failure carries no diagnostic for a caller that reads stderr. Over the same run
`pre-submission-self-review` fired 6 times with one `failed` outcome recorded in
`status.metadata.phase_steps`.

## Root cause

Not established from the retrospective inputs. What is established: the exit is non-argparse
(exit 1, not 2), so it is a script-internal error rather than an invocation defect, and it
produced no stderr text. A failure that is silent on both channels cannot be triaged from the
logs, which is why it is worth filing even without a root cause.

## Proposed action

Make `self_review surface` emit a diagnostic on its internal-error path — at minimum the
exception class and the surface being scanned — so the next occurrence is triageable. Then
investigate the two recorded occurrences against the step's 6 firings to see whether the
failure is re-entry-dependent.

## Evidence

- aspect: script_failure_analysis — `bug,script_internal_error,pm-plugin-development:ext-self-review-plan-marshall:self_review,surface,1,2026-09-22T14:53:51Z,"",2`
- source: `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` — `firing_count: 6`, `prior_firings` includes one `failed`
