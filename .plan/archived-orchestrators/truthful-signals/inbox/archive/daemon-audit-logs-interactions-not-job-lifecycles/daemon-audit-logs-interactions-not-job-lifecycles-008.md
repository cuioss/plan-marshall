envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:04Z

component=project:finalize-step-review-retrospective
category=anti-pattern
bundle=project

# A named ambiguity must be resolved with ci pr comments before a verdict is published

## What was observed

`review-retrospective.md` for PR #1037 states, in its own prose:

> No CodeRabbit (`coderabbitai`) or Sourcery (`sourcery-ai`) findings were staged for this
> PR — **either those bots did not comment, or every comment they posted was dropped by
> the pre-filter as noise** before a finding was ever filed.

The step identified the exact ambiguity, named both branches correctly, and then published
a **Comparative Verdict** anyway. Its `mark-step-done` signal was
`"1 reviewer compared, 0 actionable comments"`, and the plan's landing message summarised
the run as "review-retrospective clean".

One call — `ci pr comments --pr-number 1037` — resolves the ambiguity in a second. Run
post-merge from this retrospective, it shows the second branch was true: both bots DID
comment, and both comments were explicit refusals.

## Why it matters to this epic

The failure is not that the step lacked information. The step *knew what it did not know*,
wrote it down, and still emitted a confident terminal signal on top of it. That is the
epic's theme in its most self-aware form: the caveat existed, in writing, inside the very
artifact whose headline contradicted it.

A hedge in the body does not neutralise a verdict in the header. Downstream consumers —
the landing message, the epic ledger, the operator's merge decision — read the verdict.

## Root cause

The step's input is the plan's own finding store (`artifacts/findings/pr-comment.jsonl`).
When the FIND stage under-collects, the retrospective's population is silently short, and
the step has no independent oracle to detect that. It correctly *inferred* the possibility
and then failed to *verify* it, because verification against the live PR is not part of
its documented workflow.

## Proposed rule

When a review-comparison step observes that an enabled reviewer contributed zero findings,
it MUST NOT publish a verdict until it has queried the live PR through
`plan-marshall:tools-integration-ci:ci pr comments --pr-number N` and classified that
reviewer's actual state as one of: `participated`, `silent`, or `refused`. The verdict
then carries that per-reviewer state explicitly.

Corollary for the terminal signal: `"N reviewers compared"` where N is smaller than the
count of enabled bots MUST surface the shortfall in `display_detail`, not just the count
of what was found. `"1 of 3 enabled reviewers participated"` is truthful;
`"1 reviewer compared"` is not.

## Evidence

- `review-retrospective.md` §§ "Deterministic Per-Reviewer Metrics", "CodeRabbit /
  Sourcery", "Comparative Verdict"
- `status.metadata.phase_steps["6-finalize"]["project:finalize-step-review-retrospective"]`
  → `outcome: done, display_detail: "1 reviewer compared, 0 actionable comments"`
- `ci pr comments --pr-number 1037` → 6 comments incl. both bot refusals
- `manifest.phase_6.step_params["automatic-review"].enabled_bots = "coderabbit,sourcery,pr-agent"`
