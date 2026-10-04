# Landing Analysis: PLAN-PRQ-07 — Cross-repo telemetry archive and analyze

epic: post-run-quality
workstream: WS-05
pr: #1694 (`b3aba30aa`), after split part #1692 (`5ec134b0f`); #1691 closed unmerged

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted claim is a lead, never a fact.

⭐ **This is the first landing this epic has ever received through the inbox channel, and the first the
drain-completeness check passed.** PRQ-06's landing never fired at all (23 messages filed by hand);
PRQ-02's arrived as 9 messages. `inbox landing-check` reports `complete: true` with `missing_keys[0]` — the
machine-readable `landing-facts` block carried every required key with a real value, no `n/a` and no
`unknown`. The orchestration-detection control predicted this at launch and the prediction held.

## Deliverable Fidelity vs Spec

The spec declared **5** deliverables; the landing reports `deliverables_total=10` / `deliverables_done=10`,
which is the **outline's** decomposition of the same work, not a different scope. Mapped back to the spec:

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| 1 — scaffold `plan-marshall-telemetry`, main-only, no review-bot pipeline | **shipped** (existence corroborated) | `ci org list-repos --org cuioss` returns `cuioss/plan-marshall-telemetry`, private, default branch `main`. The main-only workflow and bot-free posture are *inside* that repo and were not verified from here |
| 2 — `transfer` project-level skill (telemetry repo) | **unverifiable here** | #1694's body states the repo adds `transfer` and `analyze`; no checkout of that repo exists on this machine, so its contents were not read |
| 3 — `analyze-marshall-quality` finalize step (this repo) | ⛔ **DROPPED by operator ruling, correctly** | `request.md:15-16` of the archived plan records the refine escalation verbatim: *"Do not create a finalize step. Make it only an explicit command in the new repo."* Purpose folded into deliverable 4; `request.md:41` records the explicit non-goal. Confirmed absent at HEAD: `analyze-marshall-quality` appears nowhere in repository source |
| 4 — `analyze` project-level skill (telemetry repo), same report structure as 3 | **unverifiable here**, and its twin-path requirement is **collapsed** | Same reason as 2. The ruling on deliverable 3 collapsed "identical report structure in two paths" to a single path, so the shared-engine-guarantees-identity argument no longer has two consumers to bind |
| 5 — relocate `audit-archived-plan-retrospectives` into the telemetry repo | **shipped-as-specified** | `git diff 2de53ba7c..b3aba30aa`: `SKILL.md`, all 25 `checks/`, and `scripts/audit.py` deleted, plus the 76-file test mirror (74 in #1692, the last 2 in #1694). `finalize-step-era-stamp-fill/` removed in the same act |

⚠ **Two of five deliverables are recorded as UNVERIFIABLE, not as shipped.** They landed in a private
sibling repository this envelope cannot read. Per ADR-019 that is a population that could not be reached,
and it is not evidence of a gap — but neither is it a confirmation, and the distinction is kept because the
landing's own `deliverables_done=10` cannot make it.

## Metrics and Anomalies

- **Tokens:** 13,104,101 total. 6-finalize holds ~51% of it (per the plan's own `plan_efficiency` aspect) —
  the same ~50% share PRQ-06 showed, on a run 1.55× larger.
- **Duration:** 95,851 s wall (≈26.6 h).
- **Anomalies, and all four are first-party instrument failures rather than execution problems:**
  - **Self-review hit the loop-back ceiling after 7 rounds** and was closed by operator override
    (*"make a final round but then go to push"*). Five of those loop-backs re-fired three pre-push steps —
    `lessons-housekeeping`, `simplify`, `plugin-doctor`, `firing_count: 6` each — for **zero edits every
    time**, on HEAD deltas as small as a two-line prose fix.
  - **`scope_creep_check` exited 1 on 9 calls**, reporting ~105 residual files that were all upstream
    commits, never plan work. Two execute leaves raised `--threshold` to get a measured result.
  - **4 of 12 execute dispatch-boundary rows carry `termination_cause=error`** totalling
    **1,285,813 tokens** reported as waste. All four were operator escalations that resolved and continued.
  - **All 33 dispatch-boundary rows are keyless** (no `--step-id`), so the key-first join paired **0 of 33**
    against 41 execution-log rows, and the 6-finalize boundary ledger **stops at 13:16:33Z** while work
    continued to 23:16Z.

## Surface delta — expansion detected

Measured by `inbox landing-check` with the declared and realized sets supplied, base `origin/main`
(`b3aba30aa`, not stale):

| | Count |
|---|---|
| Declared (spec `## Expected Surface`) | 4 |
| Realized (`2de53ba7c..b3aba30aa`) | 152 |
| **Added** — realized, never declared | **44** |
| **Missing** — declared, untouched | **1** |

- `state: expansion_detected`. The 44 undeclared paths are mostly `plan-retrospective`, `automatic-review`,
  `manage-*` and `phase-6-finalize` standards plus their tests — the reference repairs the relocation
  forced, and the self-review rounds' own churn.
- The single `missing` entry is `finalize-step-analyze-marshall-quality/` — the dropped deliverable 3. ⭐
  **This is the surface-delta field working exactly as intended**: a declared-but-untouched path that turned
  out to be a legitimate operator-ruled drop, distinguishable from a silent descope only because the
  mechanism reported it and the ruling was then found in the plan's own `request.md`.
- ⚠ This is the gate's documented **under-declaration** residual class, at roughly its documented
  magnitude. PRQ-07's spec is not re-scoped for it: the plan has landed, so its declaration is now a
  historical record rather than an input to any future disjointness verdict.

## Routing and Merge Behavior

- **Review:** ⛔ The run shipped as two PRs because a **required** reviewer structurally refused the first.
  #1691 carried 151 files; CodeRabbit refused on its 100-file cap and Sourcery on its 150,000-character cap.
  The refusal surfaced only after `push`, `create-pr` and `ci-verify` had run. #1691 was closed unmerged,
  #1692 was cut as a cherry-pick of the test-mirror deletion, and **needed two further fix commits** because
  the still-registered era-stamp step's `verdict_inputs` and a live import kept two mirror files alive — the
  split was cut by file group, and those two files could not leave in part 1. They shipped in #1694.
  `create-pr` fired twice, `ci-verify` three times.
- **CI/merge:** both parts merged via `merge_queue` (`step.branch-cleanup.merge_mechanism=merge_queue`).
  `cleanup_owed=false`. No rebase conflicts and no re-verify signals recorded.
- **Collisions:** none observed. The disjointness gate was **overridden rather than passed** when this plan
  was emitted (`candidate_comparison_determinate: false`), and the override's stated basis — no live-plan
  overlap, every in-corpus overlap against a parked or shipped sibling — **held**: nothing collided. The
  cross-ledger exposure the override did not cover (`code-intelligence-substrate`'s five specs sharing the
  relocated skill) did not materialise either, but it was never serialized and that remains luck rather
  than a guarantee. ⚠ Those five specs now declare a surface this repository **no longer contains**; their
  own epic owns re-grounding them.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-PRQ-07 --status shipped`
- [x] row `pr` stamped `1694` — `orchestrator queue --set-row … --field pr`
- [x] row `landing` stamped `landings/PLAN-PRQ-07.md` — `orchestrator queue --set-row … --field landing`
- [x] row `plan_marshall_plan_id` stamped at launch — `cross-repo-telemetry-archive-and-analyze`
- [x] `epic.md` narrative reconciled; WS-05 closed out; queue annotations updated
- [x] Watch opened — the owed review-bot-disabling guidance (operator-raised during the run)
- [x] Watch opened — CodeRabbit's `**Actionable comments posted: N**` summary counted as actionable
- [x] Watch retired — none; the cross-ledger exposure Watch is *kept*, not retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

Eight `candidate-lesson` messages arrived with the landing and every one was dispositioned:

| Message | Disposition | Where it went |
|---|---|---|
| `-001` re-fire on a verdict-irrelevant delta | **folded** | `PLAN-PRQ-10`, with `verdict-currency.md` added to its Expected Surface in the same act |
| `-002` required-bot size caps / dependency-aware split | **promoted** | global lessons corpus `2026-10-04-09-001` |
| `-003` rate-window await blocks inside a leaf | **discarded here, forwarded** | `review-apparatus` inbox `post-run-quality-002.md` |
| `-004` escalations classified `error`, not `blocked_user_review` | **folded** | `PLAN-PRQ-08` (its "terminal spend classified as waste" half) |
| `-005` `scope_creep_check` type + baseline | **discarded here, forwarded** | `truthful-signals` inbox `post-run-quality-002.md` — a recurrence of a signal routed there on 2026-09-26, plus a second defect |
| `-006` split-PR union + sibling-repo paths in the footprint resolver | **folded** | `PLAN-PRQ-09`, with `manage-references/scripts/` added to its Expected Surface in the same act |
| `-007` keyless dispatch boundaries, recording stops at the ceiling | **folded** | `PLAN-PRQ-08` (its "two ledgers disagree" half) |
| `-008` retired `modified_files` read in lessons-housekeeping Step 1 | **folded** | `PLAN-PRQ-05` |

⛔ **Four of the eight folded into PARKED specs**, which is deliberate: those specs are the PM-MCP
carry-over's evidence chain, and enriching them is how this epic's measurements reach the system that
replaces it. It is also why the carry-over Watch matters more after this landing than before — the document
snapshotted those four specs on 2026-09-26 and now lags them by four folds as well as by PRQ-12's fix.
