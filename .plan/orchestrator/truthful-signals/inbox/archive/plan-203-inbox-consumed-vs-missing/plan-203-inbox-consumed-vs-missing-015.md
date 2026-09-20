envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:23:09Z

# Review retrospective cannot distinguish a reviewer that did not review from one with zero comments

component: project:finalize-step-review-retrospective
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

PLAN-203's own generated `review-retrospective.md` contains this sentence, verbatim:

> ### sourcery-ai
>
> No `pr-comment` findings were recorded for this reviewer on this PR — it **either did not review or
> produced zero comments; the finding store carries no evidence either way.**

That is PLAN-203's target defect, restated by a sibling finalize step about its own data, on the same
PR, in the same run. `inbox validate` collapsed archived-and-consumed into `file_not_found`; the
review-findings store collapses reviewer-absent into reviewer-clean.

## Why it matters

Sourcery is an operator-retained additional reviewer. A silently-absent reviewer and a reviewer that
saw the diff and had nothing to say produce byte-identical evidence: zero rows in the finding store.
Combined with the pre-merge barrier defect filed alongside this message, the pipeline can merge a PR
believing reviewers participated when the store simply has nothing recorded.

The standing epic note already says: *only `ci pr comments --pr-number N` is evidence of
participation*, and *a comment from a bot is not a review by it*. This finding is the storage-layer
counterpart — participation state is not persisted at all, so no downstream consumer can recover it.

## Root cause

The findings store records comments, not review events. Absence of comments is the only
representation available, and it is overloaded across three distinct states: not invited, invited and
did not run, and ran and found nothing.

## Proposed action

1. Persist a per-reviewer participation record (`invited` / `ran` / `refused` / `absent`) alongside the
   comment findings, sourced from `workflow-integration-github:github_pr bot_completion` — the verb
   already exists for exactly this question.
2. `review_retrospective` MUST render the participation state, not infer it from row count. When the
   state is genuinely unknown, say `participation_unknown` rather than narrating both possibilities.
3. Apply the same three-state distinction PLAN-203 introduced for `inbox list`
   (`inbox_missing` / `epic_not_found` / genuinely-empty) to the reviewer store.

## Evidence

- review-retrospective.md § sourcery-ai (generated 09:27:49 for PR #1064)
- decision.log 09:50:13 — `unproven_bots=pr-agent`, showing the pipeline already has a notion of
  "unproven" that the retrospective surface does not consume
- execution.toon `automatic-review.optional_bots: "coderabbit,sourcery"`, `required_bots: pr-agent`
