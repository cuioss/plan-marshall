envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=landing
created=2026-08-22T16:25:04Z

## What landed

`spec-corpus-review-and-cleanup-entry-point` shipped as #1134 (merged, squash via merge queue, `c0bbd2d8b`) — the `cleanup` verb for spec-corpus review, reconciliation, and restart-readiness, across 9 deliverables and 14 tasks.

```landing-facts
schema=landing-facts/1
plan_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
pr=#1134
merge_state=merged
deliverables_total=9
deliverables_done=9
total_tokens=5432972
total_wall_seconds=28020
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:in_progress,finalize-step-preference-emitter:pending,record-metrics:pending,finalize-step-print-phase-breakdown:pending,archive-plan:pending
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
step.finalize-step-sync-baseline.work_performed=true
```

## Residue

Five items this run's steps did not record as typed facts. Each is named with what it rests on, rather than absorbed into the block above as if it were measured.

**1. This landing was emitted from `lessons-capture` (order 991), not from `emit-landing` (order 1000).** `emit-landing` is **absent from this plan's `manifest.phase_6.steps`** — the manifest was composed 2026-08-09 with 22 steps, before that step shipped, and its activation predicate is presence in that persisted list. So no step in this run would have emitted a landing at all; the inbox held 6 `candidate-lesson` messages and zero landings before this one. Filed in full as candidate-lesson `-007`. Two consequences for the block above, both direct results of emitting 9 slots early:

- `total_tokens=5432972` is a **floor, population n=5/6 phases**, read from `metrics.md` rather than from `record-metrics`' facts — `record-metrics` (order 998) has not run. The phase-breakdown's own header states 6-finalize was never closed by an `end-phase` boundary, so every column total is a lower bound. `total_wall_seconds=28020` (7h47m) carries the same n=5/6 population. The required-key value is present and real, but it is **not** the closing total a landing from order 1000 would have carried.
- The last five `steps` entries are `in_progress` / `pending` because those steps had not run at emission time. They are not failures.

**2. `pr` and `merge_state` were transcribed from each step's own `display_detail`, not from a typed fact.** `landing-payload-spec.md` sources them from `create-pr`'s `pr_number` fact and `branch-cleanup`'s `merge_state` fact. Neither step recorded a `facts` sub-dict on this run — only `finalize-step-sync-baseline` did — because those step bodies predate typed-fact recording. Both values are still the **step's own claim** (`create-pr` → `#1134`; `branch-cleanup` → `PR #1134 merged via merge queue (squash)`), never a corroboration, so finding #4's boundary is respected. This is the producer-gap shape of spec findings #2 and #6: named here rather than fabricated as a fact, and rather than degraded to `n/a` when the step did in fact claim a value.

**3. Q-Gate findings: 13 counted as "pending" by the dispatcher's signal, 0 actually unresolved.** Enumerated per phase: 2-refine 1, 3-outline 6 (all `taken_into_account`), 4-plan 0, 5-execute 0, 6-finalize 6 (all `fixed`). Every one carries a resolution. The gate signal that dispatched this step therefore reported a pending population that does not exist — worth the epic's attention as a signal-naming defect, since "13 pending" and "13 recorded, 0 pending" are different claims and only the second is true.

**4. Four of the six 6-finalize findings are one defect class re-found three times.** `regex_overfit` in `orchestrator.py`'s markdown scanner was filed, fixed, and re-filed twice more (`e62e54` → `da5425` → `2cc20c`), each round's fix leaving a CommonMark clause the next round found: fence state absent, then fence-close run length, then delimiter indentation. Each fix shipped with tests that passed green while sitting entirely on one side of the boundary the next finding crossed. This is the epic's vacuous-guard archetype recurring inside its own fixes.

**5. HYPOTHESIS (unverified here): the `steps` key's grammar is ambiguous for namespaced step IDs.** The spec defines `steps` as comma-joined `{step}:{outcome}`, but 5 of this plan's 22 step IDs contain a colon themselves (`project:finalize-step-*`, `plan-marshall:plan-retrospective`). A consumer splitting each item on the FIRST colon reads `project` as the step name; splitting on the LAST is correct. I did not read the drain in `analyze.md` to confirm which it does, so this is labelled HYPOTHESIS rather than asserted. The block above uses the composed IDs verbatim, as the manifest declares them.
