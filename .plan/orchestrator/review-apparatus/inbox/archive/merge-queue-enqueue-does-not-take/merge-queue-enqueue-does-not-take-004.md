envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=finding
created=2026-08-03T20:59:06Z

component=plan-marshall:tools-integration-ci
category=bug
title=Three retired --head help quotes survive in test_ci_base.py at ca7cf9bd4
severity=low
actionable=true
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
cross_ref=candidate-lesson merge-queue-enqueue-does-not-take-002.md

# Three retired `--head` help quotes survive in test_ci_base.py at ca7cf9bd4

## The defect

PR #1087 rewrote `add_head_arg`'s help string from `alternative to --pr-number` to `in place of --pr-number` (`ci_base.py:1376`) and updated the docstring and two test sites to match. Its self-review recorded:

> "Verified the dead literal now appears in zero test and source files."

Three occurrences survive in merged main. In `test/plan-marshall/tools-integration-ci/test_ci_base.py`:

- **line 548** — `"""pr merge should accept --head as alternative to --pr-number (both optional)."""`
- **line 561** — `"""pr auto-merge should accept --head as alternative to --pr-number."""`
- **line 569** — `"""checks status should accept --head as alternative to --pr-number."""`

## Why it survived

The sweep was scoped to `marketplace/**` (its own resolution text says "The single remaining **marketplace** occurrence"). These live under `test/**`. The claim, however, was made over "test and source".

They are also **pre-existing** — introduced by `97bb1130d` (#184), not by this diff — so a sweep restricted to the current diff's own edits would never have seen them either.

## Impact

Low but real. These are test docstrings, so nothing executes wrongly. But:
- A maintainer grepping the live help wording to find its consumers gets an incomplete set.
- A maintainer grepping the retired wording to confirm it is gone finds three hits and cannot tell whether the migration completed.
- `pr merge`'s docstring (line 548) is arguably still *accurate* under that verb's exactly-one contract, which is exactly the ambiguity finding `a494d3` resolved for the doc table — the same distinction was not carried into the tests.

## Suggested fix

Update lines 561 and 569 to `in place of --pr-number`. For line 548, decide deliberately: under `pr merge`'s exactly-one contract `--head` genuinely IS an alternative, so either keep it and add a note, or align it for consistency. Then re-run the sweep over `test/**` AND `marketplace/**` with `(?i)`.

## Verification

```
architecture search --content --pattern "alternative to --pr-number"
  -> test/plan-marshall/tools-integration-ci/test_ci_base.py, match_count 3
git log -1 -S "as alternative to --pr-number" -- test/.../test_ci_base.py
  -> 97bb1130d feat(tools-integration-ci): add --head flag to branch-aware operations (#184)
```
