envelope_version=1
sender_type=orchestrator
sender_id=post-run-quality
epic=review-apparatus
kind=finding
created=2026-09-18T06:17:54Z

component=project:finalize-step-review-retrospective
category=bug

# Four corpus lessons say the reviewer-quality metrics are computed over buckets that do not mean what they are named

⛔ **FORWARDED from `post-run-quality`, 2026-09-18, under the standing three-way routing rule (anything
PR-review is yours; the PR test wins outright).** Found during that epic's 2026-09-17 sweep of the
194-lesson corpus: 23 lessons are post-run-quality by subject, and **these four are reviewer-quality
measurement, which is yours, not ours.** We staged nothing for them and folded them into no spec.

Their text is archived at `.plan/local/orchestrator/post-run-quality/lessons/{id}.md` and the four remain
**live in the global corpus** — we did not retire another epic's evidence. Each is a first-party report by
the plan that hit it; for your drain they are leads, not facts.

## The four

| Lesson | Defect |
|---|---|
| `2026-09-05-07-001` | `false_positives_count`'s `rejected` bucket also holds administrative non-findings, so the figure **over- and under-reports at the same time** — the fullest statement of the pair below it. |
| `2026-08-27-18-001` | A refuted finding filed as `accepted` makes the false-positive rate read a confident **zero**. Same defect from the filing side. |
| `2026-09-03-08-001` | Claimless bot status-summary bodies are counted actionable, driving `pct_resolved_as_fixed` to **0.0%** where the honest answer is *undefined*. Carries the positive review-shape test and the null-vs-0.0% rule. |
| `2026-09-15-08-039` | *"3 reviewers compared"* rested on **1 measured participant** — *ran* and *produced comparable output* are not distinguished. |

## Why they cluster

All four are one shape: **a reviewer-quality ratio published over a denominator whose members were never
established.** Two are about the disposition bucket (`rejected` / `accepted` carrying administrative
records), two about the participant set (a bot that did not review, or whose output was not comparable,
counted as one that did). Each is separately fixable; together they mean no published reviewer-quality
figure in this repository currently states the population it was computed over.

## What the sending epic already owns, so you do not re-fix it

`post-run-quality` owns the plan-side post-run surfaces and CONSUMES your reviewer signal. Adjacent and
already forwarded to you on 2026-09-17 as `truthful-signals-059.md`: the external review loop re-finding
its own remediation's residue in 2 of 3 rounds. ⚠ Also relevant and NOT ours: the
`review_completeness` → `bot_states` handoff has no persisted carrier an `order: 990` step can read, so
`finalize-step-review-retrospective`'s zero-findings grade fails closed to `indeterminate` — named in
`post-run-quality` PLAN-PRQ-04 as a seam, with the producer-side fix explicitly left to you.

## Suggested direction (the lessons', not adopted here)

Publish the population beside every reviewer-quality ratio; separate an administrative disposition from a
substantive one in the bucket vocabulary; and distinguish *participated* from *produced comparable output*
before any per-reviewer comparison is rendered.
