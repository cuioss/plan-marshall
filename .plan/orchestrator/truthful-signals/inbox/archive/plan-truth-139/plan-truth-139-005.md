envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T14:20:26Z

# A review_body carrying content beneath a status line must not be classified meta

component: plan-marshall:workflow-integration-github
category: improvement
confidence: high
suggested_epic: review-apparatus
source_plan: plan-truth-139
source_pr: 1479

## Context

The per-bot registry's `review_body_summary_patterns` rule strips CodeRabbit's
`Actionable comments posted: N` boilerplate. It is right about the boilerplate and
wrong about the payload: it classifies the WHOLE body by its opening line, so a
`review_body` whose substantive content sits *beneath* the status line is recorded
as meta.

On PR #1479 two such bodies carried real claims and both were classified meta:

- `f7de42` — a **Major**, and the most consequential single finding of round 2. It
  arrived in the review body as an outside-diff comment because GitHub would not
  host it inline: `limit get` routed a READ through the committing `rmw_json`, so a
  corrupt `build-queue.json` is **erased by a read**, after which the next admission
  over-admits past the cap. Verified in triage: `rmw_json` always commits
  (`_locks_core.py:399`) and `_read_json_or_empty` silently yields `{}` on
  corrupt/non-dict input (283-303).
- `bde483` — two nitpicks, both accepted as real gaps: a mirrored ceiling constant
  with no drift test, and control-character coverage showing that **removing
  `report_safe` would leave the suite green** — i.e. the security fix this PR had
  just made was unpinned.

The consequence is measurable in two places. CodeRabbit's `actionable_count` reads
15 when its substantive output on this PR was 17, and `escapes_total` (15) excludes
both — so the single most consequential finding of round 2 is in neither the
actionable count nor the gate-escape set. The honest denominator for its accuracy is
17: 16 fixed, 1 verified-and-declined, 0 wrong.

## Root cause

The classifier's unit is the body, and its evidence is the opening line. A pattern
designed to recognise a *prefix* is being used to decide the disposition of the
*whole document*. A review body is a container, not a message: it can hold a status
line and a payload at the same time, and outside-diff findings are routed into it
precisely because they have nowhere else to go.

Note the direction of harm is the opposite of the sibling noise-filter gap
(`154f51`, already filed): that one lets chatter reach triage and costs attention;
this one hides real claims and costs **coverage**, including of a Major.

## Proposed action

Match the status line and strip it, rather than classifying the body by its
opening. After stripping, a body with no remaining substantive content is meta; a
body with remaining content is actionable and its content is the finding. The two
outcomes are then decided by what the body contains rather than by how it begins.

This also repairs the two measurements the current rule distorts, without touching
either: `actionable_count` and `escapes_total` both derive from the classification.

## Evidence

- review-retrospective.md § "Two measurement artifacts in the numbers above",
  item 2: "`actionable_count: 15` undercounts CodeRabbit by two, and one of the two
  is a Major"
- review-retrospective.md § Recommendations item 2: "The `Actionable comments
  posted: N` rule is right about the boilerplate and wrong about the payload: it hid
  two real claims on this PR, one of them a Major, from `actionable_count` *and*
  from `escapes_total`"
- aspect: log_analysis — decision `f93fc5`: "The OTHER review_body f7de42 was
  treated as substantive precisely because it is the SOLE carrier of the outside-diff
  rmw_json Major, which has no inline thread" — the triage pass had to override the
  classification by hand to see it
- aspect: log_analysis — decision `f93fc5` on the verification: "verified that
  rmw_json always commits (_locks_core.py:399) and _read_json_or_empty silently
  yields {} on corrupt/non-dict (283-303), so a READ erases every active and waiting
  entry"
