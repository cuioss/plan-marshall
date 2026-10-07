envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:01Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Re-run the class surfacer over a fix's own diff before closing a self-review round

## Context

Three times in this one run, a fix for defect class C introduced a new instance of class C. The run itself noticed the third and said so in its own resolution text.

1. `8caccf` — TASK-14 set out to harmonise an over-claiming error-status sentence and **replaced a correct three-code enumeration with a false universal**. Its resolution reads: *"This was a REGRESSION my own TASK-14 fix introduced."*
2. `c0c0d5` — the sibling site. TASK-14 swapped an inline four-code list for a cross-reference to the authoritative error set, and thereby **bound the false half to the full error set including any code added later** — the fix widened the very over-claim it was addressing.
3. `5bd6af` — an edit correcting an over-claiming doc **broke the verb list it was editing** (a `Note:` paragraph inserted inside a `Usage:` block, stranding 1 of 8 verbs). Its resolution: *"This is the third occurrence in this run of a fix introducing the defect class it was fixing."*

A fourth instance shipped undetected: D7's new `outline-vs-shipped.md` § Persistence copied the broken sibling's `--diff-file work/footprint.txt` reference into new text (see the sibling candidate-lesson from this plan).

## Root cause

The self-review surfacer runs over the round's accumulated delta and files findings by class. Once a finding is resolved, the fix's **own** diff is never re-surfaced against the class it was fixing. The reviewer's attention has moved to the next class by the time the fix lands.

## Proposed action

After applying the fixes for a round's findings, re-run the surfacer for **exactly the defect classes fixed in that round**, scoped to the fix commits' diff, before marking the round closed. This is narrow — one class-scoped pass over a small diff — not a full re-review.

## Evidence

- aspect: script_failure_analysis / qgate findings — 3 findings in `qgate-6-finalize.jsonl` whose resolution text names the recurrence; the third names it as the third.
- Five pre-submission self-review rounds ran; the recurrence spans rounds 2, 4 and 5, so a single round's discipline would not have caught it.
- The archetype is already in the corpus as "vacuous guards repeatedly introduced BY A FIX for them"; this is the same shape in the doc-contract domain.
