envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T15:59:21Z

# Replace a drifted restatement with a pointer, never with a corrected restatement

component: pm-plugin-development:ext-self-review-plan-marshall
category: anti-pattern
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

Plan `planning-lane-change-type-scope-execution-manifest` filed 51 finalize Q-Gate findings across 19 firings of `pre-submission-self-review`. Fourteen of those 51 (27%) carry an explicit `SELF-SEEDED`, `SELF-AUTHORED`, "the previous round's own fix", or "class-closure miss" marker in their own detail text. They form five chains in which a round's correction authored the next round's finding.

The longest chain runs four consecutive rounds in one file, `phase-6-finalize/workflow/pre-submission-self-review.md`:

- `e39a6b` — the `failed`→`loop_back` rename left the surfacer-error path with no destination. Fix: add Branch C.
- `28e6e8` — "SELF-AUTHORED by the previous round's own fix (bb0cf7125)": Branch C interpolated an unresolved `{sha}`, wedging the round loop. Fix: resolve the SHA, and replace the branch *enumeration* with "every branch", because enumeration is what let a later-added branch read as covered.
- `883f55` — two more stale branch-set enumerations, "the SAME archetype the previous commit's own message named — surviving two lines from where that message named it".
- `6825ee` + `fd2e74` — two `same_document_contradiction` findings, both in text the same change had just authored.

A second chain oscillated. In `manage-execution-manifest/SKILL.md` around line 330: `c764a0` extended a 10-key TOON header to the emitter's 12; `17d208` then found `execution_log_rows: 11` stale, marked it self-seeded by round 9, and resolved it by **deletion**; `553e45` then found the field under-declared because of that deletion, marked itself self-seeded by round 10, and **restored** it as a non-numeric placeholder. The third fix undid the second.

A third chain sits in `manage-execution-manifest/standards/decision-rules.md`: round 13 rewrote a worked `0,0,0` row to `unmeasured,unmeasured,unmeasured`; `f9ddde` found that this **inverted an exemplar the plan itself had settled** (a measured zero on a skipped step is the sanctioned case) and resolved it by deleting the duplicated example; `8fa871` then found an over-claiming justification an earlier round had authored.

## Root cause

Both obvious repair moves re-seed the class.

**Correcting** a restatement authors a fresh claim with the same audit surface as the one just fixed — the corrected text must now be kept in lock-step with its source, and the next round finds it. **Deleting** the restatement outright removes information the payload genuinely needs, so a later round has to put something back.

The move that actually terminated every one of the five chains was neither: replace the restatement with a **pointer at its declaring source**. The resolutions record this in their own words — "names `VALID_RECORD_OUTCOMES` and points at its declaring source", "points at `summarize_refires`' own emitted set instead of re-enumerating it, so it cannot go stale when a column is added", "cross-referenced SKILL.md and manifest-schema.md ... there is no third copy left to drift".

## Proposed action

Add a resolution-shape rule to the self-review contract: when a finding's class is *restatement drift* (a stale enum, a stale count, a stale enumeration, a stale cross-reference, a duplicated worked example), the accepted resolution is a pointer at the declaring source. A corrected restatement is accepted only when the pointer is genuinely unavailable, and a bare deletion only when the surrounding text already carries the information. Have the surfacer flag the two re-seeding shapes at review time rather than discovering them a round later.

The second half is a corollary already visible in the record: prefer a **branch-count-free / member-count-free** formulation over any enumeration, because "enumerating them is what let a later-added branch fall outside the rule while reading as covered" — a sentence the run itself wrote, two lines above where the same archetype then recurred.

## Evidence

- aspect: lessons_proposal — 14 of 51 finalize Q-Gate findings carry an explicit self-seeded or class-closure-miss marker; five chains named with their hash ids
- aspect: logging_gap_analysis — 19 firings of `pre-submission-self-review`, 15 returning `loop_back`, `loop_back_iteration` reaching the `max_iterations: 17` ceiling
- aspect: plan_efficiency — 6-finalize consumed 11.27M of 13.92M dispatched tokens; the self-review rounds are the bulk of it
