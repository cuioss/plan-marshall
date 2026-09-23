# Landing Analysis: PLAN-LR-07 — The `lessons` verb always resolves to `lessons-routing`

epic: lessons-routing
workstream: WS-01
pr: #1584 (https://github.com/cuioss/plan-marshall/pull/1584)

> Landing record for one shipped plan. Written by the `analyze` verb (inbox-scan mode) after verifying
> the plan's own structured landing message and the pasted operator recap against ground truth: the
> merge commit on `origin/main`, the actual skill source, and `.plan/marshal.json`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 — rewrite the "Dated-slug epic" mode-contract rule to "Fixed-epic sweep" | shipped-as-specified | `orchestration-model.md:387` reads "The `lessons` verb ALWAYS targets the single standing epic `lessons-routing`... No `lessons-handling-{YY-MM-DD}-{NN}` epic is ever opened again" — the three retired dated epics named as closed history |
| D2 — rewrite Step 1 to target the fixed slug, scaffold-if-absent | shipped-as-specified | mode contract's entry-point-placement note at `orchestration-model.md:82` names `lessons` as "entering the fixed `lessons-routing` epic" |
| D3 — rewrite Steps 3–4 to route via `inbox write` instead of self-staging | shipped-as-specified, with one design refinement | `orchestration-model.md:389` ("Sweep findings route outward... never staged into `lessons-routing`'s own `plans[]` queue... single narrow exception... taken only after confirming the defect is not already shipped and is not in fact `truthful-signals`' subject"). **Refinement not in the spec**: cluster routing uses `kind=finding`, not `kind=candidate-lesson` — the plan's own rationale is that a bundled multi-lesson cluster statement doesn't carry the single-lesson `candidate-lesson` payload shape. Reasonable; not independently re-verified against the envelope schema here. |
| D4 — Steps 6/7 + Output record the sweep as a dated `## Lesson Sweeps` subsection in the fixed epic, never a separate ledger | shipped-as-specified | `orchestration-model.md:390` ("Each run's disposition record is a dated subsection under `lessons-routing`'s own `## Lesson Sweeps` section... `compact` preserves it verbatim and never regenerates it") |
| D5 — sweep `SKILL.md`/`orchestration-model.md` for stale dated-slug cross-references, derived not eyeballed | shipped-as-specified | `grep -n "dated-slug\|dated epic\|lessons-handling-{" .../plan-orchestrator/SKILL.md` returns empty post-merge (was 2 hits pre-merge) |

Not independently re-derived line-by-line against `solution_outline.md` for this report — the five
deliverables above were checked directly against the shipped skill source instead.

## Metrics and Anomalies

- Tokens: 10,457,035 total (`status.json` / the landing message's `landing-facts` block agree exactly).
  The plan's own Residue prose rounds this to "10.37M" — a minor prose/fact rounding mismatch, not a
  contradiction; the structured fact is authoritative.
- Duration: 113,158 wall-seconds (~31.4h) / 297.6 worked-minutes per the candidate-lesson's own figure.
- **Anomaly — severe plan-efficiency budget overrun, self-reported and corroborated.** ~8x the
  single_module+bug_fix error anchor on tokens (1.3M anchor vs 10.46M observed), 79% of total tokens
  (8.22M) inside `6-finalize` alone. Driven by 8 `pre-submission-self-review` loop-back iterations
  (12 firings) plus 2 further CodeRabbit re-review rounds on the same fix. The operator interrupted
  mid-run to question a "10 rounds" self-review loop and directed `max_iterations: 20 → 5`, which
  landed in this same PR. Filed as candidate-lesson `plan-lr-07-lessons-verb-routing-001`, promoted to
  the global corpus as `2026-09-23-07-001` (this epic is not its owner — see Reconciliation Actions).
- **Anomaly — two normally-dispatched finalize steps ran inline instead of dispatched.** Per the
  operator's paste: `review-retrospective` and `plan-retrospective` executed in-context inside the
  finalize fork itself, because a fork cannot spawn its own sub-agent dispatches. The qualitative
  sections (review comparison, plan-efficiency writeup, lesson bodies) were composed by that same agent
  rather than a fresh independent reviewer. Not independently re-verified against the dispatch log for
  this report — recorded as the operator's own disclosure.
- **Anomaly — `branch-cleanup`'s `merge_state`/`cleanup_owed` facts were backfilled, not machine-recorded.**
  The operator drove the actual merge-queue routing by hand through `branch-cleanup.md`'s documented
  steps rather than through a scripted step dispatch; the landing message's own `## Residue` section
  discloses this and the facts are corroborated correct (PR is in fact `merged`, `cleanup_owed: false`
  is plausible for a completed merge-queue landing) even though their provenance is manual.
- Surface expansion: `.plan/marshal.json` (`phase-6-finalize.max_iterations: 20 → 5`) landed as a 4th
  file beyond the 3 declared in `## Expected Surface`, per an explicit mid-run operator directive.
  `inbox landing-check`'s `surface_delta` confirms exactly this one-file, fully-disclosed expansion
  (`state: expansion_detected`, `added: [.plan/marshal.json]`, `missing: []`) — matches the plan's own
  disclosure exactly, no undisclosed scope creep.

## Routing and Merge Behavior

- Review: CodeRabbit findings drove 2 extra re-review rounds on TASK-4 before passing clean (see budget
  anomaly above). Not independently itemized here.
- CI/merge: `merge_state: merged`, `cleanup_owed: false` (landing message, manually-driven per above).
  Merge commit `179d4f7f3945738321f5c8ba8a170fd2a93925ac` confirmed as an ancestor of `origin/main` via
  `git merge-base --is-ancestor`, and local `main` already carried it (fast-forward pull was a no-op).
  `step.branch-cleanup.merge_mechanism=merge_queue`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `1584`
- [x] row `landing` stamped → `landings/PLAN-LR-07.md`
- [x] row `plan_marshall_plan_id` stamped → `plan-lr-07-lessons-verb-routing`
- [x] epic.md queue reconciled from status.json (Ordered Queue regenerated; PLAN-LR-07 drops out of the
      live queue as a terminal `shipped` row)
- [x] Decision recorded: R15's operator ruling is now structural in the skill source, not just this
      epic's prose — see epic.md Decisions
- [x] Two off-subject candidate-lessons (self-review budget overrun; mark-step-done HEAD-resolve
      ergonomics) promoted to the global lessons corpus (`2026-09-23-07-001`, `-002`) rather than
      staged or folded here — neither is `lessons-routing`'s own subject; the next `lessons` sweep
      (now shipped as route-not-stage) will carry them to `truthful-signals` and `process-compliance`
      respectively
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- The two promoted lessons are NOT yet routed to their real owners — that happens at the NEXT `lessons`
  sweep of this epic, which is now the correct, shipped mechanism rather than a hand-run workaround.
- The self-review budget-overrun pattern (8 loop-backs, 2 CodeRabbit re-review rounds, ~8x error anchor)
  recurring on what should have been a small, disjoint-surface plan is worth a Watch in `truthful-signals`
  once the sweep delivers it there — not actioned here, outside this epic's scope.
