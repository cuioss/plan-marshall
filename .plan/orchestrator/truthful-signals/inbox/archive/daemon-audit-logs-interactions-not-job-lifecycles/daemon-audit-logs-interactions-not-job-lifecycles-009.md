envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:09Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# fetch_findings re-ingests the plan's own post_responses comment as new reviewer feedback

## What was observed

Two of the three records in this plan's `artifacts/findings/pr-comment.jsonl` are the
plan's OWN output:

```
author: cuioss-oliver
body:  "## Triage dispositions\n\n### In reply to comment_id: `IC_kwDOQ3xasM8AAAABMFchuw`\n\n
        PR-Agent's automated Reviewer Guide summary comment ... informational only ..."
```

filed at 15:53:32 and again at 15:56:28 — after the RESPOND stage posted them at 15:39:15
and 15:55:47. The second record's own `resolution_detail`, written by the triage pass that
had to dispose of it, states the mechanism verbatim:

> Self-authored triage-disposition reply posted by this plan's own post_responses run —
> not external reviewer feedback. Filed as pending because fetch_findings noise-filters
> bot boilerplate but not its own RESPOND output, so each RESPOND cycle manufactures the
> next pre-merge-barrier blocker and `fail_into_loopback` cannot converge. Resolved in
> place instead of looping back.

## Why it matters to this epic

Two ways, both on-theme.

First, it is a **non-terminating feedback loop by construction**: with
`pre_merge_comment_barrier: fail_into_loopback` configured (it is, in this plan's
manifest), every RESPOND cycle creates exactly the blocker that triggers the next cycle.
Convergence here happened only because a human-equivalent judgement call ("resolved in
place instead of looping back") broke the loop out of band — the mechanism did not
converge, the operator's escape hatch did.

Second, it **inflates the review-participation signal with the plan's own voice**. The
finding store reports 3 pr-comments; exactly 1 came from a reviewer. A count of comments
is being read as a measure of review, and two thirds of it is an echo.

## Root cause

The `fetch_findings` pre-filter is keyed on *bot* boilerplate signatures. The plan's own
RESPOND output is authored by the human/token identity that owns the repo, so it passes
every bot-oriented filter. The filter's population model is "external bots vs everything
else", but the real partition is "external feedback vs this plan's own writes".

## Proposed action

Add a self-authored-response filter in the same pre-filter pass, keyed on the conjunction
of (a) the literal `## Triage dispositions` heading the RESPOND stage emits and (b) the
author matching the identity the RESPOND stage posts under. Both halves are needed — the
heading alone would drop a human quoting the format, and the author alone would drop
genuine operator review comments.

A regression test should assert the round-trip: a RESPOND post followed by a
`fetch_findings` run yields zero new findings.

## Evidence

- `artifacts/findings/pr-comment.jsonl` records `0cf3a5` and `30e5d8`
- `ci pr comments --pr-number 1037` → two `cuioss-oliver` "Triage dispositions" comments
- `execution.toon` → `phase_6.step_params["branch-cleanup"].pre_merge_comment_barrier = fail_into_loopback`
- work.log 15:53:49 "post-rebase re-review" dispatch, 15:55:55 second unified-triage completion
