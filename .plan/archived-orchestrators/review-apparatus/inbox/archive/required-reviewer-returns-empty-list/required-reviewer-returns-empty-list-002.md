envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:20Z

component=plan-marshall:automatic-review
category=bug
created=2026-09-05
bundle=plan-marshall

# review_completeness check failed 5 times during its own plan's finalize

## Context

The plan `required-reviewer-returns-empty-list` was itself an investigation into the
required reviewer's behaviour. During its finalize, the completeness gate that decides
whether required reviewers participated failed five times on
`plan-marshall:automatic-review:review_completeness check`:

- 3 x argparse rejection (exit 2), first at `2026-09-04T11:15:59Z`. The captured usage
  string shows the parser expecting `--plan-id PLAN_ID [--required-bots [REQUIRED_BOTS]]
  [--optional-bots [OPTIONAL_BOTS]]`, so the caller and the declared surface disagreed.
- 2 x script-internal error (exit 1), first at `2026-09-05T15:19:20Z` — after the plan's
  own landing commit was authored, so these fired on the post-merge re-review path.

The `automatic-review` step re-fired 7 times across the run and recorded one `failed`
outcome among its prior firings.

## Root cause

Not established from the retrospective inputs. The two subtypes are distinct failures
sharing one call site:

- The exit-2 group is a call-site / declared-surface mismatch (the classic
  argparse-rejection family).
- The exit-1 group is an unhandled internal exception. `script-failure-analysis` captured
  no stderr excerpt for it, so the exception itself is not in the retrospective's evidence
  and must be reproduced.

The consequence is shared and is the reason this is filed as a bug rather than noise: a
completeness gate that errors reports nothing, and a required-reviewer gate reporting
nothing is indistinguishable at the call site from one reporting a clean pass unless the
caller checks status. This is the same failure shape the plan was investigating in the
reviewer itself.

## Proposed action

1. Reproduce the exit-1 path and capture the exception; the two occurrences are ~4 hours
   apart on the same day, so the trigger is likely stable rather than racy.
2. Reconcile the exit-2 call site against the live argparse surface for
   `review_completeness check`.
3. Ensure a failed completeness check cannot present to its caller as an absence of
   findings — the check must be able to say "I could not look", distinctly from "I looked
   and everyone participated". This is the same could-not-look-versus-looked-and-found-
   nothing discrimination the plan's own shipped work applied to reviewer outcome states.

## Evidence

- aspect: script_failure_analysis — `anti-pattern, argparse_other, plan-marshall:automatic-review:review_completeness, check, exit 2, first 2026-09-05T11:15:59Z, occurrences 3`
- aspect: script_failure_analysis — `bug, script_internal_error, plan-marshall:automatic-review:review_completeness, check, exit 1, first 2026-09-05T15:19:20Z, occurrences 2`
- `status.metadata.phase_steps["6-finalize"].automatic-review` — `firing_count: 7`, prior firings include one `failed`
