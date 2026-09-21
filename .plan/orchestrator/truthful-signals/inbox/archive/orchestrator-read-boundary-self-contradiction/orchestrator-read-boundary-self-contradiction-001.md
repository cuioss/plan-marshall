envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=landing
created=2026-07-28T20:08:10Z

## What landed

**Plan**: `orchestrator-read-boundary-self-contradiction` — "The orchestrator's read boundary contradicts itself, and the strict half makes its own verbs unperformable"

**PR**: #1040 (`fix(orchestrator-model): reconcile contradictory read-boundary rules`), 2 commits:

- `fca3756f6` — the substantive change: removed the strict read prohibition from `orchestration-model.md:91`, renamed the "Direct-file-access carve-out" heading to a write-only carve-out, corrected every restatement of the deleted prohibition across the marketplace skill docs **and** the marketplace-external `doc/concepts/orchestration.adoc`, and added a population-derived regression module pinning the reconciled boundary.
- `dc78a5a4b` — a review-driven fix (see candidate-lesson on absolute-path classification).

**Theme fit**: squarely `confident-signal-hides-a-caveat`. The orchestration standard stated a confident, absolute read prohibition; the caveat was that the orchestrator's own documented verbs could not be performed under it, and three further documents restated the prohibition as settled fact.

## Residue the epic should track

1. **`dispatch-inline-split.md` self-contradiction (NOT fixed — out of scope).** That document declares itself the SSOT for dispatched-vs-inline step classification, and lists `architecture-refresh` as **dispatched**, while `phase-6-finalize/SKILL.md` and the step doc itself both say **inline**. This is the identical defect class this plan just closed for the read boundary — a self-declared SSOT that disagrees with the surfaces it governs. Recommend queueing it as a sibling plan; the fix shape is already proven here (reconcile + population-derived regression guard).

2. **No documented working search path inside a dispatched `execution-context` envelope (NOT fixed — out of scope).** See the separate candidate-lesson message. Affects every sweep-class deliverable the epic will stage.

3. **Tool-layer defect already filed globally as lesson `2026-07-28-19-001`** — `architecture derive-verification` emits an unresolvable `test-compile` step behind `status: success`, hard-blocking phase-4 manifest compose. Do NOT re-file; recorded here only so the epic knows this run paid that cost.

## Signals observed this run

- Q-Gate: 4 validator findings + 2 operator review-gate resolutions at `3-outline`, all resolved. One was **error**-severity and materially widened the plan's scope.
- Review: 2 actionable comments across 2 reviewers. PR-Agent found a **real defect** that pre-submission-self-review (42 candidates, 0 findings) missed. CodeRabbit's follow-up was `accepted` as not-a-live-defect with recorded rationale.
- One loop-back `6-finalize → 5-execute` at 19:15Z to carry the review-driven fix.
