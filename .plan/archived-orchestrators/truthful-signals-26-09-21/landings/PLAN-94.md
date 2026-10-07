# Landing Analysis: PLAN-94 — The orchestrator's read boundary contradicts itself

epic: truthful-signals
workstream: WS-01
pr: 1040 — https://github.com/cuioss/plan-marshall/pull/1040

> Landing record for one shipped plan. Every claim below was corroborated against
> first-party ground truth (the squash commit, the PR comment stream via the CI
> abstraction) before it was recorded — the plan's inbox `landing` message and the
> operator's paste were both treated as leads, not facts.

## Deliverable Fidelity vs Spec

The spec staged **four** deliverables (D1–D4); the plan reported **three**. This is a
merge, not a drop: D1 (settle the boundary) is a decision with no separable artifact,
and it landed folded into D2's rewrite. All four spec obligations are present in the
diff.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — settle the boundary, state the safety mechanism | shipped-as-specified (folded into D2) | `orchestration-model.md` +16/−? in `8b143643`; carve-out renamed to a **write** boundary |
| D2 — rewrite `:82-101` as one coherent rule | shipped-as-specified | `persona-marshall-orchestrator/standards/orchestration-model.md` in the commit stat |
| D3 — sweep the consumers | shipped-**widened** | 5 doc files in the diff, incl. the marketplace-**external** `doc/concepts/orchestration.adoc` — a fourth restatement found at Q-Gate, outside the outline's original fix set |
| D4 — regression failing pre-fix | shipped-as-specified | `test/plan-marshall/marshall-orchestrator/test_orchestrator_read_boundary_contract.py`, +483 lines |

**Footprint corroboration:** squash `8b143643b` (2026-07-28 20:17:29 +0000) touches
exactly **7 files**, matching the plan's declared set 7/7 — no drift, no extras. This
directly **contradicts** the plan's own retrospective, which reported
`affected_files_recall = 0%, all 7 missing`. See candidate-lesson 006 — the retrospective
emitted a false signal about itself.

## Metrics and Anomalies

- Tokens: **2,977,068**; 6/6 phases recorded (per operator paste)
- Duration: **1h57m worked / 5h5m wall**
- Anomalies:
  - One loop-back `6-finalize → 5-execute` (19:15Z) carrying the review-driven fix `dc78a5a4b`.
  - The daemon died mid-run: preflight declared ready at 16:15Z, one routed build succeeded
    at 17:34Z, and every build from 17:36Z onward silently fell back to `in_process`
    (`reason=socket_absent`). Filed as candidate-lesson 009.
  - Nine finalize steps recorded `total_tokens=0` — structural zeros, not measurements.
    `6-finalize` never closed its metrics row, so the epic's most expensive phase renders
    blank. Filed as candidate-lesson 007.
  - Two mid-finalize stops, one on a merge-mutex rationale the operator checked and refuted
    (`branch-cleanup.md:98` documents holder-liveness reclaim). Context caution was the real
    reason. Recorded here because a stated-but-false rationale is exactly this epic's theme.

## Routing and Merge Behavior

- **Review:** 8 comments across 2 bots + operator triage.
  - **PR-Agent (`cuioss-review-bot`)** found the **real defect**: `_is_orchestrator_document()`
    substring-matched the **absolute** path, and this plan's own worktree is named
    `orchestrator-read-boundary-self-contradiction` — so the predicate returned `True` for the
    entire population. A vacuous always-fires detector **inside the test written to prevent
    vacuous detectors**. Fixed in `dc78a5a4b` with a `PROJECT_ROOT`-monkeypatching companion
    test that fails on revert in *any* checkout.
  - **`pre-submission-self-review` reported `42 candidates, 0 findings`** on the commit that
    introduced it. Counter-evidence for PLAN-81 — and note this cuts the other way from #1038,
    where self-review *did* catch a self-inflicted defect at 38 candidates.
  - **CodeRabbit** raised one Major finding (predicate misses `orchestration.adoc`), the
    operator refuted it with a recorded rationale, and CodeRabbit **withdrew it** and stored a
    learning. A clean adversarial exchange.
  - ⛔ **Sourcery was REFUSED** — *"you have reached your weekly rate limit of 500000 diff
    characters"* at 18:52:26Z. The finalize nonetheless reported **"review-retrospective: 2
    reviewers compared"**. This is the **fourth consecutive PR** (#1024, #1032, #1034, #1040)
    carrying an unrecognized refusal, and the second confirmation of the weekly-quota phrasing.
  - ⛔ **Both rate-limit shapes appeared on this one PR**: Sourcery's *quota* refusal AND
    CodeRabbit's *window* refusal (*"Review limit reached… next review available in 6 minutes"*,
    18:52:31Z) — CodeRabbit then reviewed successfully at 19:33Z. This is direct second
    confirmation of PLAN-92 paste item (2).
- **CI/merge:** 11/11 checks green; squash-merged via the merge queue at 20:17:29Z.
  No rebase conflicts, no re-verify signals, no surface collision with any concurrent plan.

### Post-merge PR revisit (new standing rule)

Applied per the rule recorded this session. **Result: clean, and the sibling scan is a
genuine negative.**

| PR | Merged | Latest comment | Post-merge arrivals |
|----|--------|----------------|---------------------|
| #1040 | 20:17:29Z | 20:16:20Z | **none** |
| #1039 | 18:54:48Z | 18:39:58Z | none |
| #1038 | 16:58:44Z | 16:57:16Z | none (88 s margin) |
| #1037 | — | 15:55:47Z | none |

The late-arrival recurrence therefore stands at **n=2** (#1026, #1036) and did **not**
grow in this window. The #1038 margin of 88 seconds is worth noting: the window is narrow,
not absent.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-94 --status shipped`
- [x] row `pr` stamped — `1040`
- [x] row `landing` stamped — `landings/PLAN-94.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator-read-boundary-self-contradiction`
- [x] epic.md queue reconciled from status.json
- [x] defects opened (see Follow-Ups); no watch retired
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

Ten inbox messages drained with this landing (1 landing + 9 candidate-lessons), plus 2
orchestrator-authored findings. Dispositions:

| Message | Disposition |
|---------|-------------|
| 002 relative-path predicate / **always-fires** vacuity pole | **Promoted** to the lessons corpus |
| 003 detector population ⊉ fix-set population | **Folded** into PLAN-61 |
| 004 declared-but-unrun sweep freezes `affected_files` | **Folded** into PLAN-61 |
| 005 no working broad-search primitive in a dispatched leaf | **Staged** as PLAN-105 |
| 006 footprint read outside its window reports 0 as a finding | **Staged** as PLAN-106 |
| 007 inline finalize step records `total_tokens=0` | **Folded** into PLAN-64 |
| 008 confident point estimate with no honest "unknown" | **Folded** into PLAN-101 |
| 009 preflight readiness is point-in-time, reported as standing | **Folded** into PLAN-58 |
| 010 canonical block documents 6 of 11 enum values | **Staged** as PLAN-107 |
| finding 003 hook `timeout` unit (seconds vs ms) | **Staged** as PLAN-108 |
| finding 004 `manage-lessons` mixes local time and UTC | **Staged** as PLAN-109 |

Not re-filed: lesson `2026-07-28-19-001` (`architecture derive-verification` emits an
unresolvable `test-compile` step behind `status: success`) is already in the global corpus.

Residue item 1 from the landing message — the `dispatch-inline-split.md` self-contradiction
(`architecture-refresh` listed dispatched, `phase-6-finalize` says inline) — was **already
tracked** by this epic as the architecture-refresh dual classification handed over from the
test-suite-quality epic. Recorded as a **recurrence** on the existing Open Defect, not a new one.
