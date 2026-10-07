envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:30Z

component=plan-marshall:automatic-review
category=improvement
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Participation quorum passes identically when every required reviewer yields nothing

## Context

Carried verbatim from this plan's review retrospective — not re-derived here.

Reviewer coverage on PR #1425 was **2 of 3 by participation but 1 of 3 by yield**.
`cuioss-review-bot` participated on every HEAD and filed **zero** findings on the same
diffs where CodeRabbit filed nine, two of which were genuine fail-open contract
defects.

The `automatic-review` step recorded
`both required bots participated at HEAD; 3 findings triaged` and passed.

That quorum would have passed **identically had both required reviewers published
nothing at all**, because the gate's predicate is participation, and participation is
satisfied by a comment that contains no findings.

## Root cause

Participation is the only observable the gate can demand — a reviewer cannot be
compelled to find something, and a zero-yield review is a legitimate outcome on a
clean diff. So the predicate is not wrong; the *reporting* is. `both required bots
participated at HEAD` reads as coverage, and coverage is what a reader takes from it.

This is the epic's archetype applied to review: a confident signal over a population
whose actual contribution was never measured.

## Proposed action

1. Record per-reviewer **yield** beside participation on the step record: findings
   filed per bot at the HEAD it reviewed. The data is already in the `pr-comment`
   findings store, keyed by `bot_kind`.
2. Make the `display_detail` state both, e.g.
   `2/2 required participated, 1/2 yielded (coderabbit 9, cuioss-review-bot 0)`.
   The gate outcome need not change; the sentence must stop implying coverage it did
   not measure.
3. Consider a distinct informational signal when a required reviewer's yield is zero
   across every HEAD of a PR that other reviewers found defects in — that is the
   pattern worth noticing, and it is invisible today.

## Evidence

- carried input: this plan's review retrospective — `1 of 4 reviewers measurable, 9 actionable comments, 88.9 pct fixed`
- status.json — `automatic-review.display_detail: "both required bots participated at HEAD; 3 findings triaged"`, `firing_count: 4`
- aspect: manifest_decisions — `required_bots: "cuioss-review-bot,coderabbit"`, `bot_lists_provenance: answered`
