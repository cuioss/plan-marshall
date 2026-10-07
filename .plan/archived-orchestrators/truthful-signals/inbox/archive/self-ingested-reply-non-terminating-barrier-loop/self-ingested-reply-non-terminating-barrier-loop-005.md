envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:45:29Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# An outline-phase agent reported a config value as non-existent without verifying it

## Observation

During PLAN-111's outline phase, an outline-phase agent reported that `fail_into_loopback` did **not** exist as a value anywhere in the finalize step-param surface. That claim was wrong: `fail_into_loopback` does exist, as the `branch-cleanup.pre_merge_comment_barrier` step-param value. The claim was caught and corrected before it reached the plan, but only because the outline was checked rather than trusted at face value.

## Why it matters

This is the epic's theme (confident signal hides a caveat) in its verification-quality shape: a negative existence claim ("X does not exist") was stated with the same confidence as a positive one, but a negative claim over a config/param surface is only as good as the search that produced it — an incomplete search yields a false negative that reads identically to a genuine absence.

## Corrective rule

A negative existence claim about a value living in project config/param surfaces (step-params, flags, enum values) needs the same evidentiary bar as a positive one: name the search that was run (which file, which key path) so the claim is falsifiable, rather than asserting absence from recollection or a partial scan. When an outline step's conclusion hinges on "X does not exist", the outline should show the query, not just the verdict.

## Status

Corrected before the plan proceeded — no downstream defect shipped from this one. Recorded as a verification-quality note for the epic's pattern-tracking, not because it caused harm this time.
