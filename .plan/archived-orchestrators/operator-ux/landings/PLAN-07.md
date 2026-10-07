# Landing Analysis: PLAN-07 — Bound user-facing output volume

epic: operator-ux
workstream: WS-04-how-plan-marshall-talks
pr: #1387 — https://github.com/cuioss/plan-marshall/pull/1387

> Landing record for one shipped plan. Lives at `landings/PLAN-07.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Provenance of this record — reconstructed first, then confirmed by a late landing

**This record was written in two passes, and the distinction matters.**

⛔ **Pass 1 — DISCOVERED, not reported.** The landing was found by the `cleanup` verb's
re-grounding pass. At that point the plan had filed five `candidate-lesson` messages and no
`kind: landing` message, and the ledger row still read `staged` while the work was merged. The
divergence surfaced only because A1 re-grounding tested PLAN-07's own absence claim ("no
equivalent bound governs main-context user-facing output") against HEAD and found the bound
already present. Every fact was drawn from git and the CI abstraction directly, because there
was no narrative to corroborate:

- `ci pr view --pr-number 1387` → `state: merged`, head `feature/output-volume-standard`,
  `merge_commit_sha: 9fd0957188f44e8b76844e38aa91172e4cec58d1`.
- `git merge-base --is-ancestor 9fd095718 main` → in `main`. Merged 2026-09-03 10:24 UTC.
- `git show --stat` → **3 files, +64 / −3**.

**Pass 2 — the landing message arrived, 5h48m after the merge.** `output-volume-standard-017.md`
was filed at 16:12 UTC against a 10:24 merge, together with 11 `candidate-lesson` messages.
`inbox landing-check` returns **`complete: true`, `missing_keys[0]`** — every required fact key
supplied with a real value. So the metrics this record previously reported as unavailable are
now DRAINED, and are filled in below rather than left as an unmeasured channel.

⛔ **The correction this forces on Pass 1's finding.** The Open Defect this landing opened said
the plan "filed no landing message". That is now **refuted in its absolute form** — the message
was filed, late. The defect survives in a SHARPER form, and the sharper form is worse: the
window between merge and landing was **5h48m**, and for the whole of it the epic held a merged
plan it did not know about and would have re-emitted. Nothing detects that window. See the
epic's Open Defect, amended rather than closed.

The re-grounding pass and the landing message AGREE on every overlapping fact (PR number, merge
state, deliverable count), so Pass 2 corroborates Pass 1 rather than replacing it.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Output-volume rule appended to `user-communication.md` | shipped-as-specified | `## Rule 3 — Say only what the next decision needs` |
| 2. Narration/outcome distinction, **floor stated first** | shipped-as-specified | `### The floor comes first — an outcome is reported completely` precedes `### The ceiling`, and says so in its own words: "Read the floor before the ceiling, because the ceiling is only ever applied to what the floor has already released" |
| 3. Per-phase-boundary shape | shipped-as-specified | `### The shape of a phase-boundary report` |
| 4. Cross-reference from `citations-only-return.md` naming the sibling | shipped-as-specified | `## Sibling standard — the opposite direction`: "The two are siblings, not layers: neither one's contract reaches the other's leg" |
| 5. Cites the vocabulary glossary rather than restating | shipped-as-specified | `### Vocabulary` section |

**The spec's verify-first clause was honoured in the landed text.** It required the completeness
floor be settled before the brevity ceiling was written, and stated first in the document so a
reader meets it first. The landed section does exactly that, and carries the sentence that makes
it non-negotiable: *"A report that fits on one line because a failure was left out of it is not
a short report — it is a wrong one."*

**One spec claim was CONTRADICTED and correctly absorbed.** The spec's `HYPOTHESIS` — "no
equivalent bound governs main-context user-facing output" — was true when staged and false by
the time the plan ran, because PLAN-06 (#1382) had created `user-communication.md` three hours
earlier. The spec's own re-scope instruction covered this ("re-scopes from author to strengthen
and enforce, which is materially smaller"), and the landed diff is +57 lines onto an existing
file rather than a new one. The re-scope happened as designed.

### Under-declaration: 1 of 3 files, and it was MY error

Declared 2 entries; realized 3. The undeclared file is
`persona-plan-marshall-agent/SKILL.md` — ⛔ **which I explicitly REMOVED from this spec's
Expected Surface** when applying the placement decision, on the reasoning that "the load step
and the pointer are PLAN-06's deliverables". That was wrong: PLAN-07 still had to update the
standards-reference row for its own rule. The under-declaration is an orchestrator authoring
error, not plan drift — recorded here rather than charged to the plan.

## Metrics and Anomalies

**Drained from `landing-facts` (schema `landing-facts/1`), `complete: true`.**

| Fact | Value |
|------|-------|
| Deliverables | 3 / 3 |
| Total tokens | 2,902,587 |
| Total wall | 32,454s (9h00m) |
| Merge mechanism | merge queue |
| Upstream commits absorbed at sync-baseline | 1 |
| Steps reported | 21, of which 20 `done` and 1 `unknown` |

Per-phase, from the operator's paste: 1-init 58,270 · 2-refine 149,600 · 3-outline 459,744 ·
4-plan 355,687 · 5-execute 306,719 · **6-finalize 1,572,567**. Worked time 1h45m against 9h00m
wall — 7h15m idle, most of it the interrupted-session gap in finalize.

- ⛔ **Finalize consumed 54% of the token spend on a three-file documentation change**, and
  5.1× what execute cost. This is the fourth consecutive landing in this epic showing that
  shape and it is now the epic's most-repeated measurement. Corpus lesson `2026-09-03-11-007`
  already records the same ratio from the preceding plan.
- **`archive-plan` was reported `unknown`, and the Residue said to resolve it by observation.**
  Done: `.plan/local/archived-plans/2026-09-03-output-volume-standard` exists, and the plan is
  gone from the active registry. **The step completed** — the `unknown` is a structural blind
  spot (emit-landing runs at `order: 1000`, archive-plan at `1100`), not a failure. The
  operator paste's path for it, `.plan/archived-plans/…`, omits the `local/` segment; the
  directory is at `.plan/local/archived-plans/…`.
- **Anomaly RESOLVED, and its Pass-1 diagnosis was wrong.** Pass 1 inferred from the plan's
  absence from `archived-plans/` that "`archive-plan` did not run" and that the finalize lane
  had stopped after the retrospective. Both parts are false: the lane completed all 21 steps,
  and the plan is archived. What actually happened is the run was **interrupted after the merge
  and resumed in a second session**, which completed the tail from `lessons-capture` onward.
  The absence Pass 1 read was a mid-interruption snapshot, not a terminal state.
- **Review behaviour.** 6 bot comments promoted, 3 substantive (all CodeRabbit), **all
  declined — no bot claim produced an edit.** One (`cde958`) was mis-bucketed `accepted` on a
  rationale that refuted it, and the review retrospective re-bucketed it to `rejected`; that
  bucketing rule is now corpus lesson `2026-09-03-16-004`.
- **Sourcery was credited as participating on a rate-limit refusal** — the third recorded
  instance and the third acceptance. Contained only because sourcery sits in `optional_bots`
  here. Priors `2026-08-25-09-012`, `2026-09-02-08-001`.

## Routing and Merge Behavior

- Merged as `9fd095718`. Head branch `feature/output-volume-standard`.
- **Surface-collision check: the gate predicted correctly.** PLAN-07 was emitted alongside
  PLAN-10 as a disjoint pair. Its realized footprint (persona standards +
  `citations-only-return.md`) shares no file with PLAN-10's declared `manage-config` cluster,
  so the pairing was sound and no correction is owed to either spec.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-07 --status shipped`
- [x] row `pr` stamped — `#1387`
- [x] row `landing` stamped — `landings/PLAN-07.md`
- [x] row `plan_marshall_plan_id` stamped — `output-volume-standard`
- [x] Epic Open Defect opened — a plan can merge without its landing reaching the epic
- [x] PLAN-08 / PLAN-09 dependency state re-derived
- [x] START-HERE and Ordered Queue blocks regenerated

**Second pass, on the late landing message:**

- [x] `inbox landing-check output-volume-standard-017.md` → `complete: true`, `missing_keys[0]`
- [x] Metrics section filled from the drained `landing-facts` block
- [x] `archive-plan` outcome resolved by observation (the Residue asked the epic to do this)
- [x] Pass-1 anomaly diagnosis corrected — the lane completed; it was interrupted, not stopped
- [x] Epic Open Defect AMENDED rather than closed — the absolute claim is refuted, the
      5h48m detection window is the surviving defect
- [x] 12 inbox messages drained and archived (1 landing + 11 candidate-lessons)

## Follow-Ups

- **PLAN-08 is now fully unblocked** — its three prerequisites (PLAN-05, PLAN-06, PLAN-07) have
  all shipped. It is the epic's terminal remediation plan.
- **PLAN-09's PLAN-07 dependency is satisfied**; it still needs PLAN-04.
- **The inbox is now drained.** 12 messages consumed and archived — the late landing plus 11
  candidate-lessons. The five earlier retrospective messages were drained in a prior pass.
- **The late-landing defect is the important residue.** For 5h48m this epic held a merged plan
  it did not know about and would have re-emitted. The landing eventually arrived; nothing
  covered the window. See the epic Open Defect, amended.
- ⛔ **6 of the 11 candidate-lessons were already in the corpus.** Only 5 were new. Two of the
  duplicates (`2026-09-03-11-004`, `2026-09-03-11-005`) were filed by the immediately preceding
  plan in this same epic. The lessons pipeline is re-filing what it already knows, which is a
  new epic-level Open Defect — the corpus is now 68 lessons and the retirement rate is zero.
- **Two contract defects this run worked around, neither owned by any plan in this epic**: the
  `--measured-diff-size` argparse rejection (corpus `2026-08-25-09-014`, now with a second
  observed instance) and `branch-sync-state`'s unreachable `remote_absent_landed` verdict once
  branch-cleanup has removed the worktree. The second is NEW and is recorded as an epic defect.
