envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=post-run-quality
kind=candidate-lesson
created=2026-09-18T08:52:19Z

component=plan-marshall:plan-retrospective
category=improvement

# Two corpus lessons are yours by subject — handed over with their text, and removed from the corpus after this write

⛔ **FORWARDED from `truthful-signals`, 2026-09-18, at the end of a corpus-wide sweep** (131 active
lessons classified by subject; 124 were ours; corpus 131 → 7 → 0). These two are **post-run-quality by
subject, not ours**, and the operator directed that every remaining lesson be transformed into an inbox
item for its owning epic and then removed from the corpus.

⛔ **After this message the corpus copies are GONE.** Their text survives at
`.plan/local/orchestrator/truthful-signals/lessons/forwarded-to-other-epics/{id}.md` and in the quoted
bodies below. If you decline either, say so and we restore it — but nothing else will.

---

## 1. `2026-09-15-08-003` — split an oversized plan BEFORE executing it, against the anchor the retrospective already owns

component: `plan-marshall:phase-4-plan` · category: improvement · filed 2026-09-15

**The measurement.** One plan consumed **10,488,689 tokens** against the `multi_module + bug_fix` error
anchor of 2.0M — **5.2× over** — and 380 minutes of worked time against a 150-minute error anchor. It
carried 12 deliverables and 44 tasks. `5-execute` alone was 6,330,694 tokens (60% of the plan) across 18
dispatches and 3 phase re-entries; `6-finalize` added 2,412,805 across 12 dispatches with 4 loop-backs.

**Root cause.** Nothing in the plan phase caps deliverable or task count against the `(scope_estimate,
change_type)` anchor **the retrospective later scores the plan against**. A 12-deliverable bug-fix plan is
graded by an anchor calibrated on plans an order of magnitude smaller, and the mismatch is discovered only
after the spend.

**Why it is yours.** The anchor table already exists at
`plan-retrospective/references/plan-efficiency.md` § 2 — this is a READ of an existing calibration, not a
new one. The proposal is that `phase-4-plan` consults it and surfaces a split proposal when the composed
task set projects past the warning column. ⚠ Adjacent to your `PLAN-PRQ-08` D4, which already covers
"the anchor comparison happens where it can still change the outcome" — this is the same clock, one phase
earlier. Fold rather than stage twice.

**Evidence:** `totals_tokens=10488689`; `max_phase_token_share=0.60`;
`total_tokens_per_deliverable=874057.42`; `loop_back_iteration: 4`; `5-execute close_count: 3`; deliverable
5 alone declared 19 files across 8 skills — a plan-sized unit inside a deliverable.

---

## 2. `2026-09-18-06-001` — verify a defect claim handed to the retrospective before reporting it as a finding

component: `plan-marshall:plan-retrospective` · category: anti-pattern

⚠ **Read this one's history before you dispose of it.** It is the restoration of `2026-08-27-16-003`,
which your own sweep retired on 2026-09-17 as `completely_covered`. This session judged it a **standing
agent-facing rule** rather than a work item, the operator agreed, and it was re-filed under a new id one
day ago — deliberately, so sessions would keep recalling it.

**The rule.** Treat a defect claim supplied in a dispatch context as a HYPOTHESIS with a named
verification, never as a finding. Where the claim is a set property over a store you can read, DERIVE it:
list the population, read each member, report the derived count.

**The observation behind it.** A dispatch context asserted *"5 active lessons, every one body-less,
set-body never called after add"*. A census refuted it: `list --status active` returned **6**, and all six
carried full multi-section bodies. The claim was wrong in its universal AND its count, and was one list
call plus six gets away from being checked. Restated, it would have filed a fabricated bug against
`manage-lessons` that read as corroborated *because of where it came from*.

⛔ **The tension, stated plainly so you can settle it rather than inherit it.** Removing it from the
corpus is what the operator asked for; it also ends the agent recall that the restoration existed to
preserve. `PLAN-PRQ-09` D5 owns the defect half (an aspect verifying a handed claim). If you want the
behavioural rule to keep steering sessions, it has to live somewhere sessions read — that is your call as
the owning epic, not ours.
