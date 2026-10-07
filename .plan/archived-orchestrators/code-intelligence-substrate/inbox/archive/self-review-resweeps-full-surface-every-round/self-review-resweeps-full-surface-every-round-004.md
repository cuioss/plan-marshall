envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:21:57Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_finding=f2928f
source_aspects=llm-to-script-opportunities,script-failure-analysis

# Widen _detect_count_prose to standards/*.md to match its sibling's file set

`_detect_count_prose` (`_self_review_detectors.py`) resolves the skill directory and then opens **only** `{skill_dir}/SKILL.md`. Its sibling `_collect_skill_contract_sources` in the **same file** globs `standards/*.md`. The asymmetry is two functions apart.

Consequence: **a stale count / range / endpoint / closure claim living in a `standards/*.md` doc is surfaced by NO candidate list — delta or full.** The closing full-surface confirmation pass is not the backstop for that class that a reader would reasonably assume it to be, because "full surface" here means the full *file* surface, not the full *detector* surface.

## Root cause

Two functions in one file resolve the same conceptual input — "the docs that carry this skill's contract" — through different file sets, with no shared resolver and no test pinning that they agree.

## Solution

Widen the detector's file set to match its sibling's glob. Add a **negative-control fixture** pinning that a stale count planted in a `standards/*.md` doc IS surfaced — a positive-only fixture would pass against the current broken resolver.

## Impact

Verified first-party on PR #1126. Six self-review rounds found 5/5/2/3/4/0 findings whose recurring class was exactly restated-count drift, and **the two members that lived in `ext-point-finalize-step.md` (a `standards/` doc) were found only because the operator directed a reader at the file by name** — no candidate list ever surfaced them.

Deliberately NOT fixed during that plan's own finalize: changing detector behaviour after the round-6 clean full-surface verdict would have invalidated the verdict and restarted the loop. The finding is filed `pending` as `f2928f` and outlives the plan.

Confident-signal-hides-a-caveat: the round-6 "self-review clean: 76 candidates examined, no check matched" verdict is true *and* silent about an entire file class the detector cannot see.
