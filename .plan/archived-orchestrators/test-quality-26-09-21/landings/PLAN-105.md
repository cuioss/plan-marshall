# Landing Analysis: PLAN-105 — Every module counts and the campaign can finish

epic: test-quality
workstream: WS-04
pr: [#1407](https://github.com/cuioss/plan-marshall/pull/1407) — merged `bf1b7ed6707e2e752fea6ac83f467c2da0deccb3`

> Landing record for one shipped plan. Lives at `landings/PLAN-105.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Eight deliverables, **seven complete and one partial** — the plan's own report, corroborated by the
`landing-facts` block (`deliverables_total=8`, `deliverables_done=7`) and by the merge diff.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — re-derive the campaign leftovers, gate the run on their shape | shipped-as-specified | leftovers re-derived and the run gated |
| D2–D4 — budget-rule widening, helper-module visibility, instrument commits | shipped-as-specified | `test/test_definition_duplication_instrument.py` (+187) and `test_fidelity_diff_instrument.py` (+185) are the instruments, now committed scripts rather than prose recipes |
| D5 — slice 050 dedup | ⚠️ **shipped-partial** | `test_footprint_resolver.py` and `test_footprint_tier_precedence_control.py` were never touched, and **nothing records whether the survey judged them non-removable** |
| D6–D8 — noqa retirement and the two sweeps | shipped-as-specified | 521 files, 3,707 insertions / 2,466 deletions |

⛔ **D5's partiality is a hole in the record, not merely in the delivery.** Two declared paths went
untouched and no artifact says whether that was a judgement (non-removable) or an omission. Those are
different facts with different follow-ups, and the run cannot now be asked which one it was.

### Realized vs declared surface — the opposite failure from PLAN-145

Applying the check this epic adopted at PLAN-145's landing: **514 of 521 realized files (98.7%) fall
inside PLAN-105's declared surface.** Only 7 fall outside — `.plan/marshal.json`, three files under
`.claude/skills/`, and three under `marketplace/targets/`.

⛔ **That near-perfect coverage is not a good declaration; it is the reason nothing could ever pair
with this plan.** PLAN-105 declared `test/` and `marketplace/bundles/` at root, so almost nothing
*could* land outside it. The two landings together give the epic both failure modes of the same gate,
one week apart:

| | PLAN-145 | PLAN-105 |
|---|---|---|
| Declared | 5 entries, narrow and specific | 10 entries, two of them whole trees |
| Realized inside declaration | **0 of 3** | **514 of 521** |
| Gate consequence | invisible collisions — declaration described a different plan | no discriminating power — everything collides, the slot can never be filled |

⛔ **Both are honest-looking declarations the gate cannot use.** A declaration is only useful when it
is both *accurate* and *narrow*, and nothing in the current form asks for the second. The plan's own
candidate-lesson 003 reaches the same conclusion from inside: **57% of what shipped sits outside every
deliverable's declared surface** (521 realized against 221 declared-and-hit), because a sweep's real
scope is a predicate and the outline offers only a path list. That is the root cause worth fixing, and
it is now recorded as corpus lesson `2026-09-04-17-003`.

## Metrics and Anomalies

- **Tokens**: 4,675,938 total across 6 phases. **6-finalize spent 2.40 M against 5-execute's 0.72 M.**
- **Duration**: 135,219 s wall (37 h 33 m).
- **Anomalies**:
  - ⛔ **~20 gate re-fires across five head-dependent steps**, every one tracing to the verdict-currency
    classifier returning `invalidated` because no head-dependent step declares a `verdict_inputs`
    surface. Two rebases onto a moving `origin/main` multiplied it. **This is the epic's third
    independent measurement of one shape** — PLAN-170 at 59%, PLAN-145 at 66%, PLAN-105 with finalize
    at 3.3× execute.
  - `pyproject_build` ran **155 times for 16,262,880 ms — 71.1% of all in-plan script time** — while
    the plan-efficiency aspect reports `total_build_seconds: unavailable`, because the build wrapper
    appends no change-ledger row and the ledger is the declared oracle. The contract behaved exactly as
    specified; the oracle was simply never fed.
  - A structural ordering gap: `finalize-step-simplify` (order 8) commits *after* `pre-push-quality-gate`
    (order 5) certified its tree, so the gate/review delta was `excluded` on
    `gate_head_sha != reviewed_head_sha` and `structural_share` reports `null` rather than `0`.
  - `check-manifest-consistency` emitted a **false `fail`** — `branch_cleanup_without_changes` with
    `diff.files_total: 0` against a 521-path footprint — because branch-cleanup is manifest step 13 and
    the retrospective is step 17, so `--base-ref origin/main` is legitimately empty post-merge.

## Routing and Merge Behavior

- ⛔ **No bot reviewed this diff.** At 515 files, Sourcery refused on the GitHub API's 300-file
  diff-fetch ceiling and CodeRabbit on its 100-file plan limit; `cuioss-review-bot` was triggered with
  `/review` and never answered. **Neither refusal was recognised at FIND time** — Sourcery was credited
  `participated` and CodeRabbit recorded `absent` — until commit `394e0fcf` registered both wordings as
  `cause=size` refusals mid-run.
- The operator accepted the coverage gap under a `barrier-ask-override` merge authorization, **granted
  twice** because the first lapsed when a rebase moved HEAD.
- **Machine verification is what stands behind this merge**: whole-tree verify green at 24,246 tests,
  CI green, and the merge queue re-verified against the latest base before landing.
- **CI/merge**: merged via queue as `bf1b7ed6`; branch and worktree removed; `main` up to date.

⚠️ **The lost review coverage and the scope growth are one event, not two.** The sweeps declared an
outline-time snapshot, execution reached ~300 files beyond it, and the resulting 515-file diff is what
every reviewer then refused. Fixing the declaration form is also the fix for the review gap.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-105 --status shipped`
- [x] row `pr` stamped `#1407`
- [x] row `landing` stamped — `landings/PLAN-105.md`
- [x] row `plan_marshall_plan_id` already stamped
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated
- [x] 16 inbox messages drained and archived; queue re-enumerated clean
- [x] **15 candidate-lessons promoted** to the global corpus as `2026-09-04-17-001` … `-015`
- [x] Watch retired — the concurrent-pair watch, now fully resolved
- [x] Open Defect added — D5's unrecorded partiality
- [x] Open Defect added — the declaration-form root cause, with both failure modes measured
- [x] resume_anchor updated

## Follow-Ups

- **All 15 candidate-lessons promoted, none discarded.** Unlike PLAN-145's batch — where all 14 were
  already in the corpus and promotion would have duplicated — none of these subjects existed in the
  corpus, so the inbox channel worked exactly as designed here. Verified before promoting.
- ⚠️ **`2026-05-08-14-001`, the `recurrence_of` pointer on candidate 007, does not resolve.** It is
  absent from the corpus at `--status all`, so it is not merely superseded or removed. The lesson was
  promoted as `2026-09-04-17-007` on its own merits; the dangling pointer is recorded as a defect.
- **Candidate 009's item 1 — add reverse-order (`PM_TEST_ORDER=reverse`) to the gate — was NOT folded
  into PLAN-110**, deliberately. It is adjacent to PLAN-110's charter but not in it (PLAN-110 owns zero
  skips and wall-clock, not order-independence), and PLAN-110 already sits **at the split guard's
  six-deliverable threshold with a recorded decision not to split**. Adding an eighth deliverable is
  exactly the bloat the guard exists to catch. Recorded as corpus lesson `2026-09-04-17-009` and named
  in the epic's Unowned list. ⚠️ This epic has itself recorded that *retention is not an application
  mechanism*, so this is a known-weak resting place — stated rather than papered over.
- **The `verdict_inputs` remedy is now three-for-three** and remains **out of this epic's scope**. Not
  staged. It belongs to the measurement-instrumentation cluster.
- **Two defects the run named as unfixable from inside**: lesson `2026-09-03-17-001` is fully covered
  but unretirable because YAML frontmatter makes 12 corpus lessons invisible to id-keyed verbs
  (tracked as `2026-09-03-22-001`), and `check-manifest-consistency`'s false fail above. Both unowned,
  both out of scope.
