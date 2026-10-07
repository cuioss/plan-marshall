envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:57:41Z

component=plan-marshall:automatic-review
category=improvement
title=A review bot's summary card or trigger acknowledgement is not a review claim
enrich_module=default
enrich_verb=insight

## Owed architecture hint

**Target**: `architecture enrich insight --module default`

**Hint text** (verbatim, to be applied post-merge):

> A review bot's persistent summary card and its trigger acknowledgement are
> participation artifacts, not diff-derived claims. Dispose of them as `accepted`
> without opening a fix task, and never read their presence as evidence that the
> bot reviewed the current HEAD — check for a review object stamped with the
> live `reviewed_commit_sha` instead.

## How this generalized

The `(default, pr-comment, accepted)` tuple recurred twice within plan
`post-run-steps-ordered-before-their-evidence` (threshold
`preference_min_recurrence: 2`), from two structurally identical dispositions:

- pr-agent's persistent "PR Reviewer Guide" card — "PR contains tests / No
  security concerns identified / No major issues detected" — carrying no
  diff-derived finding.
- CodeRabbit's trigger acknowledgement — "Review finished. Note: CodeRabbit is
  an incremental review system and does not re-review already reviewed commits"
  — carrying no code content at all.

Both consumed a triage decision to conclude there was nothing to decide. The
generalization is the disposition rule, not the raw comments.

The second case is the sharper one and is why this is filed as an `insight`
rather than a per-module `best-practice`: that acknowledgement was the ONLY
record CodeRabbit produced at the final HEAD, so the participation quorum read
green while the last eight commits carried no review. The disposition rule and
the participation-evidence rule are the same lesson seen from two sides.

## Why the hint is owed rather than written

This step is `post_run_review: true` and runs after the merge gate, so an
`architecture enrich` call here would land tracked source
(`.plan/project-architecture/default/enriched.json`) on `main` as an
uncommitted diff with no push path — the `#990` defect. Per
`source-edit-pushability.md` § "The discover-after-merge rule" the hint is named
here and applied later, never written from this step.
