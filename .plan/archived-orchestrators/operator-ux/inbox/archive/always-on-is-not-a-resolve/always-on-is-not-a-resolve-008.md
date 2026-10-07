envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:27:07Z

component=project:finalize-step-lessons-housekeeping
category=anti-pattern
created=2026-09-03

# manage-references calls omitted required flags on `get` and `compute-footprint`

During the `project:finalize-step-lessons-housekeeping` re-fire (plan
`always-on-is-not-a-resolve`, 2026-09-03T16:03Z), two consecutive
`plan-marshall:manage-references:manage-references` calls were rejected by
argparse (`exit_code=2`, `failure_kind=argparse_rejection`) because required
flags were absent:

```text
[16:03:55] Add the required flag(s) to `plan-marshall:manage-references:manage-references get`: ['field']
[16:04:10] Add the required flag(s) to `plan-marshall:manage-references:manage-references compute-footprint`: ['worktree-path']
```

Both calls happened inside the same dispatched envelope, back to back — the
first rejection did not stop the caller from issuing a second call with the
same defect class.

## Solution

Quote the flag set verbatim from the script's `--help` (or from
`manage-references` § Canonical invocations) before issuing the call:

- `manage-references get` requires `--field`.
- `manage-references compute-footprint` requires `--worktree-path`.

Where the housekeeping workflow documents these calls, the documented form
must carry the required flags so a caller following the doc cannot omit them.

## Impact

This is the "Never invent script subcommands" recurrence class applied to
required FLAGS rather than to verbs: the rejection is silent to the workflow
narrative (the script body never runs) and the caller continued past it.
Applies to every workflow doc that shows a `manage-references` invocation.
