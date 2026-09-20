envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=review-apparatus
kind=finding
created=2026-09-05T07:50:45Z

# `merge_lock rate-window check` echoes a foreign PR's attempt counter

Carried out of plan `preference-admissibility-prose-vs-auditor-code` (PR #1398) as an
out-of-scope finding. Original finding id `1b5171`.

## The defect

`merge_lock.py`'s `_run_rate_window_check` (around line 1491) accepts `--pr-number` and then
**ignores it**, echoing `record['attempts']` unconditionally. The claim path at around line 607
scopes the cap correctly:

```python
attempts_before = record['attempts'] if record is not None and record['pr_number'] == pr_number else 0
```

So `check` publishes an `attempts` / `attempts_remaining` pair that is only meaningful for the
`pr_number` the record happens to hold, while the caller reads it as its own.

## Observed live, twice, in one run

- `rate-window check --bot-kind coderabbit` reported `attempts: 2, attempts_remaining: 0` from a
  stored record naming `pr_number: 1399`, while the querying plan was on PR **1398**, whose real
  count was `0`.
- An earlier probe in the same run saw the same row bound to `pr_number: 1396`.

## Why it matters

A consumer reading `attempts_remaining` for its own PR gets a foreign figure and would escalate
`rate_window_exhausted` on false evidence — refusing a recovery attempt it actually still has, or
believing it has one it does not. In this run it would have aborted the review-recovery path while
the real counter was untouched.

## Suggested remedy

Scope the echo the same way the claim path already does: return `attempts` for the requested
`pr_number` (0 when the stored record names a different PR), or return the stored `pr_number`
alongside so the caller can tell the figure is foreign. The record already carries `pr_number`,
so the discriminator exists.

## Routing note

Routed to `review-apparatus` rather than `truthful-signals`: the surface is the review-bot
rate-window claim, so the PR/review test applies and wins outright.

## Source

- File: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py`
- Component: `plan-marshall:manage-locks`
- Severity: warning
