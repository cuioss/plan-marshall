# Landing: PLAN-TRUTH-001 — gates do not refire over the loop-back diff

**PR**: #1073 — merged as `8db7b42d4` (corroborated against `origin/main`, not taken from the report)
**Plan id**: `gates-do-not-refire-over-the-loop-back-diff`
**Deliverables**: 3/3 · **Finalize steps**: 22/22 · **Spend**: 4h16m worked / 4.4M tokens
**Archived**: `.plan/local/archived-plans/2026-08-01-gates-do-not-refire-over-the-loop-back-diff`

## Deliverable fidelity vs spec

All three shipped as scoped. The spec's D5 widening into `dispatch-inline-split.md` and the roster test
was carried; the architecture-refresh dispatched/inline classification defect (D1) landed.

⭐ **The load-bearing result is a count correction, and it is the epic's own archetype.** Deriving the
population over all **25 registered steps** from the live registry returned **9 head-dependent, not the
8 the prose asserted**. The missing ninth was `project:finalize-step-era-stamp-fill`: its
`skipped: true → done` record asserts that tracked source carries no unresolved `PR-PENDING` sentinel,
so a loop-back commit introducing one would ship it. ⛔ **Reconciling the numeral down to match the list
would have shipped the exact defect the plan was written to remove** — the standing rule *a request that
states a count states a sample*, confirmed once more, this time against the plan's own premise.

## The plan validated its own thesis, repeatedly

`pre-submission-self-review` found a genuine defect on **all three passes** (six total). **Two were
created by the plan's own earlier fixes.** `finalize-step-simplify` caught a seventh in the third-pass
fix: a **re-introduced hand-maintained membership fragment** — the very archetype being removed,
reproduced by its own author mid-fix. ⇒ **Occurrence 7** of *archetype knowledge does not transfer by
exposure*; a gate that skipped the loop-back diff would have shipped all seven.

## Anomalies and weak signals — reported by the plan against itself

- ⛔ **The merged tree has NO bot review.** `pr-agent`'s only artifact was a participation Guide posted
  against the **pre-rebase head**; the force-push invalidated it. CodeRabbit's bounded 21-minute window
  was declined. `automatic-review` recorded *"1 comment found"* and `review-retrospective` *"1 reviewer,
  0 actionable"* — **a green-looking pair over an unreviewed diff.** This is precisely the epic's
  standing rule that only `ci pr comments` is evidence of participation, and it is why the post-merge
  revisit below is owed rather than optional.
- ⛔ **The plan reproduced its own subject in its own orchestration.** Re-firing the quality gate after a
  mid-loop commit emitted **no second `[STEP]` and no `record-step` row**; only a **77-minute timestamp
  lag** revealed it. ⇒ Direct corroboration of the *finalize step execution is not uniformly logged*
  caveat this orchestrator derived independently from the archived corpus, and a first-party instance
  for **PLAN-TRUTH-031**.
- **Two defects found and deliberately not actioned**, routed to the inbox rather than scope-crept:
  - `pre-commit-verify-freshness` accepted a **`build-npm:js_coverage` row as proof of freshness for a
    Python-only plan** — it matches on `worktree_sha` alone. ⇒ Feeds **PLAN-TRUTH-010** (what is
    genuinely build-class) and **PLAN-TRUTH-026** (the `kind=build` row), and it is a *second* instance
    of the domain-blindness **PLAN-TRUTH-028** covers.
  - The routed build wrapper reported **`duration_seconds: 0` while the inner log recorded a 330 s
    timeout**. ⇒ Direct first-party evidence for **PLAN-TRUTH-026 D3** (duration is produced and
    discarded) and for the standing rule *never trust a routed build's outer status*.

## Reconciliation actions

- Queue: `running → shipped`; `pr=1073`, `landing`, `plan_marshall_plan_id` stamped via `--set-row`.
- **Surface released**: `phase-6-finalize` is free. Unblocks **TRUTH-006** (finalize sync-baseline),
  **TRUTH-028**, **TRUTH-030**, **TRUTH-031**, and the wait-procedure Open Defect — all of which were
  blocked on this plan alone.
- **Cross-epic**: `code-intelligence-substrate`'s **PLAN-CIS-011** was hard-sequenced behind this
  landing and is now unblocked — notified, not assumed.
- **Merge mutex released** → PLAN-TRUTH-026 (PR #1074, CI green, FIFO depth 2) can proceed.
- Inbox: **36 queued** (19 from this plan, 14 from PLAN-57, 3 from `review-apparatus`). ⚠ The plan's
  `lessons-capture` record reads 13 and the run summary reads 19 — **not a discrepancy**: 13 from
  `lessons-capture` plus 6 from `plan-retrospective`. Checked before being recorded as a defect.

## ⛔ Owed

**Post-merge PR revisit on #1073** — operator standing rule, and this landing is the strongest case yet
for it: the merge outran the reviewers, the only bot artifact was invalidated by a force-push, and
CodeRabbit's window has since opened. `ci pr comments --pr-number 1073` is the only thing that settles
what actually reviewed the merged tree.
