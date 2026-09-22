# Landing Analysis: PLAN-100 — Module-Budget Campaign (Run 1 of 7)

epic: test-quality
workstream: WS-04
pr: #1314

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf.
> ⚠️ **This plan is a campaign of seven runs. Run 1 has landed; runs 2–7 have not.** The row is
> `landed` for run 1 only; the remaining six are re-staged as **PLAN-140**.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — re-derive the whole-tree budget count and the per-slice attribution before acting | **shipped-as-specified** | The run's own re-derivation returned **318**, already 5 above the plan's stated 313 lead — the gating derivation doing exactly its job |
| D2 — split run 1's slice (`050`) by behaviour cluster, never splitting a class | **shipped-as-specified** | 66 over-budget modules → **3**. The 3 survivors are exactly the single-class exceptions D2's own exception clause licenses, confirmed by name and line count on disk |
| D3 — fidelity: no test lost or gained | **shipped, self-verified** | The run's multiset `Class::test` check. Not re-run here |
| D4 — duplication reduction across the slice | **shipped-partial, and the figure is unknown** | Reduction was substantial, but the two ends were measured with **two different definitions**, so the honest current figure is **unknown**. The run recorded this itself (M45) |
| D5 — report the measured deltas | **shipped-as-specified, with four figures self-corrected** | Every figure carries a command |

## The Verified Partition — the ingestion's strongest single result

The whole-tree `test-module-line-budget` count at HEAD is **267**, and the per-slice attribution sums to
it **exactly, with no residual bucket** — independently cross-checked with `sort | uniq -d` returning
zero duplicate file attributions. **The epic's partition is confirmed holding at HEAD.**

| Campaign run | Slice | Status | Over budget at HEAD | Campaign's own figure |
|---|---|---|---:|---:|
| 1 | `050` plan state and records | **done** | **3** | 66 → 3 |
| 2 | `040` delivery pipeline | open | **57** | 55 |
| 3 | `060` runtime and script substrate | open | **55** | 53 |
| 4 | `030` config and manifest | open | **40** | 40 |
| 5 | `070` architecture and orchestration | open (**now unblocked**) | **62** | 61 |
| 6 | `080` plugin development and generator | open (**now unblocked**) | **49** | 42 ⛔ **stale by +16.7%** |
| 7 | `010`'s rule-test modules | open | **1** | 1 |
| | | | **267** | |

Run 7's single module is `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule6.py` at
**681 lines**, over by 281 — the module PLAN-010 split off specifically to stay under the budget it was
introducing.

## Metrics and Anomalies

- ⛔ **Anomaly — four false figures, none wrong in either number.** Each was wrong in the **comparison**:
  a duplication headline measuring `def`/`class` on one side and including assignments on the other; a
  banner delta taking its two ends from two different scripts; a stale absolute collected count; and a
  suite baseline run against a tree that no longer existed, against which the branch read 20% slower
  when it was in fact **faster**. Six review rounds checked the arithmetic of each number and **none
  checked that the two ends were the same measurement.** This is the campaign's lesson 4 and the reason
  PLAN-105 § D4 exists.
- ⛔ **Anomaly — the PR reached 309 files and *both* automated reviewers refused it** on file-count
  ceilings (100 and 300). Two thirds of the repository's review capacity was structurally unreachable.
  Runs 2–7 will each land in the same place.
- **Anomaly — the campaign's instruments died with the VM.** A line-faithful splitter, a multiset
  fidelity differ, a duplication detector, a banner-attribution checker and a loss classifier were all
  built and **none committed**. Every defect the run shipped and then caught was caught by one of those
  checks or by a reader; **none by the build.**

## Routing and Merge Behavior

- Review: refused by both bots on size. The run's own checks and readers were the entire safety net.
- CI/merge: landed as PR #1314.

## Reconciliation Actions

- [x] row `status` → `landed` (run 1 only)
- [x] row `pr` stamped → `#1314`
- [x] row `landing` stamped → `landings/PLAN-100.md`
- [x] Runs 2–7 re-staged as **PLAN-140** with corrected sizing
- [x] Open Defect opened — the metric is blind to helper modules
- [x] Open Defect opened — D3's per-directory fixture criterion, broken by this run's deviation
- [x] Open Defect opened — three of four process lessons never reached the lane contract

## Follow-Ups

- ⛔ **The campaign's own metric cannot see where the lines went.** `analyze_test_module_line_budget`
  filters on `_is_collected_module`, so **no helper module is measured** — and this run created **66**
  `_{domain}_fixtures.py` helpers. A falling budget count is therefore **not** evidence that lines left
  the tree, and six more slice splits are scheduled to make exactly that kind of move.
  Owned by **PLAN-105 § D3**, which must land before run 2.

- ⛔ **This run silently retired PLAN-050 § D3's criterion.** It hoisted per **source module** rather
  than per directory and disclosed the deviation in its own report — but nothing amended D3, whose
  done-when ("each directory has at most one fixture module") is now false in every one of the ten
  directories. This is the same shape as the retired line floors and needs the same **explicit**
  retirement. Folded into **PLAN-140**.

- ⛔ **Run 6's sizing is materially stale** — 42 measured before PLAN-080 landed, **49** now. Corrected
  in PLAN-140; a campaign run that dispatches against the plan's stated figures rather than re-deriving
  will under-scope itself.

- ⛔ **Three of this run's four process lessons never reached the lane contract.** PLAN-090's single
  lesson (stale-base re-verification) **did** land in `cloud-plan-lane/SKILL.md`; this run's four
  (multiset-diff-for-moves, measurement-invalidated-by-edit, PR-size-forfeits-review,
  before/after-same-instrument) appear in neither `cloud-plan-lane` nor `author-cloud-plan`. **The
  harness-improvement loop is running slower than the campaign that is supposed to consume it.**
  Recorded in the epic's `## Open Defects`.

- **D2's "method versus outcome" residue** — nine sources hoisted into one module plus fixtures without
  ever being split on class boundaries, licensed by scope rather than by merit, with the run's own M32
  noting *"the report became the optimisation target"*. Folded into **PLAN-140**.
