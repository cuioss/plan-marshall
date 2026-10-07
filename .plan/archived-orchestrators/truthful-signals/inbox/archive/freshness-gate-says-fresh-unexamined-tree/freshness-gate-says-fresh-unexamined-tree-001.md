envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:04Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Self-review matched 0 of 75 candidates against shapes it already declares

## Context

`pre-submission-self-review` fired 8 times on this plan (3 of those firings recorded
`outcome: loop_back`) and its terminal record reads
`self-review clean: 75 candidates examined, no check matched`.

CodeRabbit then filed 9 actionable items against the same diff. Four of them are
same-document contradictions and producer/consumer pairs — and
`ext-self-review-plan-marshall` already declares candidate classes for exactly those
shapes: `same-document normative directives`, `producer-consumer pairs`,
`source-of-truth duplicates`, `contract sources`.

Two of the nine were genuine fail-open contract defects in the plan's own
documentation — the class this gate exists to catch before a reviewer sees it.

## Root cause

The gate surfaced 75 candidates and matched none of them. That is not a run over an
empty population, so the failure is in the matching, not in candidate enumeration.
A gate that examines the right population, applies the right classes, and still
returns clean while a downstream reviewer finds four instances of those same classes
is reporting a verdict its checks did not earn.

The `75 candidates examined, no check matched` display string reads as thoroughness
and is the reason nobody looked further: it publishes the population size, which is
the discipline this epic asks for, and then draws the wrong reassurance from it.

## Proposed action

1. Take the four CodeRabbit findings from PR #1425 that fall into declared classes and
   turn each into a fixture for the class it should have matched. A class with no
   failing fixture is a class with no evidence it can fire.
2. Establish, per class, whether the class ever fires on any corpus. A class that has
   never matched in production is indistinguishable from an unimplemented one, and the
   aggregate `no check matched` hides which of the two it is.
3. Have the terminal display distinguish *no candidate matched any check* from
   *k of N checks are known-live*. `75 candidates examined, no check matched` should
   not be renderable when the live-check count is unknown.

## Evidence

- aspect: chat_history_analysis — 8 self-review firings, 3 recorded `loop_back`, all with `loop_back_target: 6-finalize`
- aspect: request_result_alignment — 2 of the 9 review escapes were fail-open contract defects in the plan's own documentation
- status.json — `pre-submission-self-review.display_detail: "self-review clean: 75 candidates examined, no check matched"`, `firing_count: 8`
- carried input: this plan's review retrospective, which measured 9 actionable comments at 88.9 pct fixed
