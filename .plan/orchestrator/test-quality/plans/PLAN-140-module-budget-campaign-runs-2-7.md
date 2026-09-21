# PLAN-140: Module-Budget Campaign, Runs 2–7

epic: test-quality
workstream: WS-04

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Re-staged by the orchestrator during epic ingestion.** PLAN-100 was a seven-run campaign; run 1 landed
> and its verdict is [`landings/PLAN-100.md`](../landings/PLAN-100.md). This spec carries the remaining six
> runs with **corrected sizing**. The original brief is at
> [`archive/100-module-budget-campaign/plan.md`](../archive/100-module-budget-campaign/plan.md).
>
> ⛔ **This spec is emitted ONE RUN AT A TIME.** Each emission takes exactly one row of the table below and
> lands as its own PR. A run that takes two rows is a run whose tail does not happen.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Drive **B1** — the 400-line module budget, the epic's one structural rule — to zero across the five
remaining reduction slices and PLAN-010's rule-test glob. Run 1 took slice `050` from 66 over-budget modules
to 3 and proved the method; what remains is the same method applied five more times, each measured against
the budget rather than against a line target.

## The Six Remaining Runs

⚠️ **Every figure below was re-derived at HEAD `2cd1a19c` during ingestion and is a LEAD.** Re-derive at
dispatch: run 6's own campaign figure was stale by **+16.7%** because it was measured before PLAN-080 landed.

| Run | Slice | Over budget at HEAD | Campaign's stale figure | Ordering prerequisite |
|:-:|---|---:|---:|---|
| 2 | `040` delivery pipeline | **57** | 55 | met |
| 3 | `060` runtime and script substrate | **55** | 53 | met |
| 4 | `030` config and manifest | **40** | 40 | met |
| 5 | `070` architecture and orchestration | **62** | 61 | met (PLAN-070 landed `6514cf24`) |
| 6 | `080` plugin development and generator | **49** | 42 ⛔ **stale** | met (PLAN-080 landed, 2 reports) |
| 7 | PLAN-010's `test_test_conventions_rule*.py` glob | **1** | 1 | met |

**Whole-tree total: 306 at HEAD `09f92b5e`** (was 267 when this table was drawn, then 270, then 279). ⛔ **The six
rows plus slice `050`'s residual 3 no longer sum to it, and the gap is widening in every window
measured**: 267 → 270 → 279 → 306, all of it from other epics' landings. ⛔ **Do not execute this table.
D1 is gating for exactly this reason — re-derive every row before acting on it.**

⛔ **The "no spec claims it" explanation this section previously carried was WRONG and is retracted.**
It attributed the residual to `test/pm-plugin-development/cloud-plan-lane/` being unclaimed. PLAN-120's
derivation reports `unclaimed: 0` whole-tree — that directory is claimed by PLAN-080's recursive
`test/pm-plugin-development/**` glob. The residual is **not** an ownership hole; it is simply population
growth this table has not absorbed.

⚠️ **The per-slice attribution this campaign is sized from does not currently exist in derivable form.**
At HEAD the derivation returns all 279 findings in a single `<multiply-claimed>` bucket, because five
specs carry whole-tree `test/` root claims. **PLAN-170 is staged to fix that and should land before
run 2**, or run 2 sizes itself by the manual pass PLAN-120 was commissioned to remove.

Run 7's single module is `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule6.py` at
**681 lines**, over by 281 — ⛔ **the module PLAN-010 split off specifically to stay under the budget it was
introducing**, now flagged by its own rule.

## Deliverables (per run)

1. **D1 — Re-derive before acting.** ⛔ **Gating.** Derive this run's slice membership from the owning
   plan's own `## Expected Surface`, and its over-budget population from the doctor's own sweep. Compare
   against the table above and **report the delta rather than adopting either figure silently**. Run 1's own
   gating derivation returned 318 against a stated lead of 313 and was right to.
   *Done when:* the slice's directory list, its over-budget module list and its count are each recorded with
   the command that produced them, and any disagreement with this spec is stated.

2. **D2 — Split by behaviour cluster, never by arbitrary halves, and never a class.**
   `test_{unit}_{cluster}.py`. ⛔ **A class is never split** — a module whose whole content is one class
   under the 500-line ceiling is **exempt** by PLAN-105 § D2 and must not be touched; a class *above* that
   ceiling is reported, not split.
   ⛔ **Use PLAN-105's committed instruments** — the fidelity differ, the duplication detector and the banner
   attribution checker — rather than rebuilding them from prose. If PLAN-105 has not landed, **say so in the
   report and state which checks were hand-rebuilt**, because that is the condition under which run 1
   shipped four false figures.
   *Done when:* the slice's over-budget count is reported before and after; every module split is named with
   its resulting modules; and no class has been split.

3. **D3 — Prove nothing was lost.** The `Class::test` multiset and the comment/code-line counts must be
   identical across the move, **both ends derived by one instrument**.
   ⛔ **This is lesson 4 and it has five recorded instances.** A before/after pair whose two sides were
   produced by different scripts, or one of whose sides was quoted from an earlier run, is a defect
   regardless of whether the numbers look right.
   *Done when:* the differ reports both sides with its definition printed, and the multisets are identical.

4. **D4 — Order-independence.** Hoisting changes what a module binds at import time. Run the affected
   directories in **default and reverse** directory order. Run 1 found seven failing tests this way and an
   earlier plan 173.
   *Done when:* the affected directories pass in both orders, and the result is recorded.

5. **D5 — Report the measured deltas.** The slice's budget count before and after; the fidelity multisets;
   the duplication figure at both refs with the detector's definition printed; the reverse-order result; the
   collected item count; the skipped count; and the wall-clock with its population named.
   *Done when:* the report carries every figure with the command that produced it.

## Two Inherited Corrections

⛔ **PLAN-050 § D3's criterion is retired, and this spec is where that is written down.** Run 1 hoisted
fixtures per **source module** rather than per directory and disclosed the deviation — but nothing amended
D3, whose done-when ("each directory has at most one fixture module") is now false in **all ten** of that
slice's directories. **The per-source shape is the campaign's method**; D3's per-directory criterion is
retired exactly as the percentage line floors were. A run does not re-litigate it.

⛔ **Run 1's "method versus outcome" residue is inherited, not closed.** Nine sources were hoisted into one
module plus fixtures without ever being split on class boundaries, licensed by scope rather than by merit —
run 1's own M32 records that *"the report became the optimisation target"*. A run that hits the same wall
**reports it as such** rather than banking the hoist as a split.

## Claim Labels

- OBSERVED: the whole-tree `test-module-line-budget` count is a MOVING population and this spec
  deliberately carries **no point figure**. ⛔ **Re-scoped SEVEN times: 267 → 270 → 279 → 306 → 324 →
  330 → 350 → 351 → 362.** It has risen at every single measurement ever taken, moved by +1 *during a
  single cleanup pass*, and by +11 across the two landings since. ⚠️ **Part of the growth is this
  epic's own instrumentation**: `bf1b7ed6` (PLAN-105 #1407) widened the rule to see helper modules, so
  some increments are newly-VISIBLE population rather than new debt, and ⚠️ **279 and the later figures
  may not measure the same quantity at all** (modules-over-budget vs findings) — a reconciliation that
  has been owed across three cleanups and is still not done. **D1 must separate newly-visible from new
  debt before sizing any run, and must re-derive every slice table at dispatch.** ⛔ **Any number
  transcribed into this spec is stale on arrival — that is the finding, not a caveat on it.**
  - verdict: contradicted | checked_at: fb8aadc9c | by: test-quality/cleanup | rescoped: yes | evidence: re-derived at HEAD fb8aadc9c via doctor-marketplace test-conventions: test-module-line-budget is 362, not the 351 this claim was last re-scoped to nor the 330 in its own headline. Trajectory now 267 -> 270 -> 279 -> 306 -> 324 -> 330 -> 350 -> 351 -> 362, rising at EVERY measurement ever taken. RE-SCOPED DIFFERENTLY THIS TIME: the point figure is REMOVED from the claim rather than replaced, because three consecutive cleanups have substituted a fresh number that went stale before the plan was emitted. The claim now carries the trajectory, the visible-vs-new-debt confound, and the still-unreconciled 279-vs-362 quantity question, with a standing instruction to re-derive at dispatch. Also observed at this HEAD: _test_shape_scan.py, shipped by PLAN-160 last landing, is itself 636 lines and over the 400-line budget by 236 - the epic's own instrument is in this plan's population.
- ⛔ OBSERVED — **the attribution no longer sums with zero residual, but NOT for the reason previously
  recorded.** This row formerly claimed `test/pm-plugin-development/cloud-plan-lane/` was claimed by no
  spec. **PLAN-120's derivation refuted that**: `unclaimed: 0` whole-tree, and that directory falls
  inside PLAN-080's recursive `test/pm-plugin-development/**` glob. The refutation is kept rather than
  deleted because it is the epic's cleanest evidence for why a derivation was commissioned — the
  original finding came from a grep for a literal directory token, which cannot see a recursive glob
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: re-ran the epic-surface-partition attribution tool at bf1b7ed6: no unclaimed bucket appears in the owner buckets table, consistent with the retraction that cloud-plan-lane/ falls inside PLAN-080's recursive glob. The retraction is carried forward as anti-rework record
- ✅ OBSERVED — **the blocker is CLEARED**: this row formerly recorded that the per-slice attribution
  returned a single `<multiply-claimed>` bucket holding all findings, so the campaign could not be sized
  until PLAN-170 landed. **PLAN-170 has shipped (#1385)**, and re-running the tool at `bf1b7ed6`
  discriminates real per-slice buckets: PLAN-030 **44**, PLAN-040 **48**, PLAN-050 **21**, PLAN-080 **31**,
  PLAN-155 **56**, PLAN-165 **13**, PLAN-020 **1**, plus a residual `contested` of **108**. ⚠️ **The
  residual is mostly landed-plan inheritance pairs**, which is the terminal-vs-terminal defect this epic
  records separately — it is not 108 modules of live contention. **The campaign can now be sized per run.**
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: the blocker is CLEARED rather than refuted-and-still-open: PLAN-170 has shipped (#1385), and re-running the tool at bf1b7ed6 discriminates real buckets - PLAN-030 44, PLAN-040 48, PLAN-050 21, PLAN-080 31, PLAN-155 56, PLAN-165 13, PLAN-020 1, plus a contested residual of 108 that is mostly landed-plan inheritance pairs. Re-scoped: the campaign can now be sized per run
- OBSERVED: run 6's campaign figure of 42 is stale — the current figure is **61** at `bf1b7ed6`
  (re-scoped from 49, itself re-scoped from 42), measured over PLAN-080's Expected Surface directories.
  ⚠️ **+45% against the figure this spec was staged with**
  - verdict: contradicted | checked_at: fb8aadc9c | by: test-quality/cleanup | rescoped: yes | evidence: re-derived at HEAD fb8aadc9c: line-budget findings under test/pm-plugin-development/ total 46, not the 61 recorded at bf1b7ed6 and not the 49 or 42 before that. This figure has now moved in BOTH directions across the epic (42 -> 49 -> 61 -> 46), unlike the whole-tree count which has only risen, so run 6 cannot be sized by extrapolating the tree trend onto its slice. Re-scoped to carry the both-directions volatility rather than the new number. Full slice distribution at this HEAD for D1's use: test/plan-marshall 293, test/pm-plugin-development 46, test/marketplace 7, test/_shared 3, test/sync-plugin-cache 2, test/default 2, remainder 1 each. These are LEADS for D1 to re-derive, not a sizing table.
- OBSERVED: run 7's single module is `test_test_conventions_rule6.py` at 681 lines, over by 281
  - verdict: corroborated | checked_at: fb8aadc9c | by: test-quality/cleanup | rescoped: n/a | evidence: re-measured at HEAD fb8aadc9c: test/pm-plugin-development/plugin-doctor/test_test_conventions_rule6.py is exactly 681 lines, unchanged across bf1b7ed6, 9853a7ab and now fb8aadc9c - stable across five landings. Run 7's single module is still the module PLAN-010 split off specifically to stay under the budget it was introducing, still flagged by its own rule.
- ✅ OBSERVED — **CLOSED by PLAN-105 § D3 (#1407)**: the budget rule formerly filtered on
  `_is_collected_module`, so no helper module was measured and run 1 created 66 of them. At `bf1b7ed6`
  `analyze_test_module_line_budget` states it measures **every module the test tree carries, collected and
  helper alike**, and **7** non-`test_`-prefixed files (`conftest.py` plus 6 underscore fixture modules)
  now appear among the 330 findings. ⚠️ **The escape hatch is closed, but the count is not comparable
  across the change** — a rise at `bf1b7ed6` is partly newly-visible population
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: CLOSED rather than merely refuted: analyze_test_module_line_budget at bf1b7ed6 states it measures every module the test tree carries, collected and helper alike, and 7 non-test_-prefixed files now appear among the 330 findings. PLAN-105 D3 landed the widening this claim was waiting on. Re-scoped, with the warning that the count is not comparable across the change
- OBSERVED: run 1's PR reached **309 files** and **both** automated reviewers refused it on file-count
  ceilings (100 and 300). Each remaining run will land in the same place, and the operator decision on how
  to carve a slice into PRs is **still pending**
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: confirmed verbatim at landings/PLAN-100.md:52-53 - the PR reached 309 files and both automated reviewers refused it on file-count ceilings of 100 and 300
- HYPOTHESIS — **re-derive per run; the table is a lead**: each row's count still holds at dispatch time
  (verify-at-outline). Two unrelated epics have already landed new over-budget modules inside PLAN-080's
  slice since it converged
  - verdict: unverifiable | checked_at: fb8aadc9c | by: test-quality/cleanup | rescoped: n/a | evidence: unchanged and unchanged for the same reason: this is an explicit verify-at-outline deferral over the whole slice table rather than a checkable aggregate. Its per-row figures are measured separately and carry their own verdicts. Re-stamped at this HEAD so the record shows the question was re-asked rather than forgotten - the aggregate remains a lead the run must re-derive, and claim 0's re-scope now removes the point figure it would otherwise have been checked against.

## Expected Surface

⛔ **This spec's surface is DERIVED** — it is the union of six other plans' surfaces, one per emission. The
union is enumerated at directory-root granularity below so the disjointness check can resolve it; **a single
emission's surface is one row only**, and a run re-derives that row from the owning plan's own spec.

- OBSERVED: `test/plan-marshall/` — runs 2, 3, 4 and 5
- OBSERVED: `test/pm-plugin-development/` — runs 6 and 7
- OBSERVED: `test/marketplace/` — run 6
- OBSERVED: `test/sync-plugin-cache/` — run 6
- OBSERVED: `test/finalize-step-deploy-target/`, `test/finalize-step-sync-plugin-cache/` — run 6
- OBSERVED: `test/pm-dev-frontend/`, `test/pm-dev-frontend-cui/`, `test/pm-dev-java/`,
  `test/pm-dev-java-cui/`, `test/pm-dev-oci/`, `test/pm-dev-python/`, `test/pm-documents/` — run 6
- OBSERVED: `test/default/`, `test/pm-code-intelligence/` — run 6

**Per emission**, taken from the owning plan's own `## Expected Surface` and re-derived at dispatch:

- OBSERVED: run 2 → PLAN-040's sixteen entries under `test/plan-marshall/`
- OBSERVED: run 3 → PLAN-060's fourteen directories under `test/plan-marshall/`
- OBSERVED: run 4 → PLAN-030's six directories under `test/plan-marshall/`
- OBSERVED: run 5 → PLAN-070's twenty-nine entries under `test/plan-marshall/`
- OBSERVED: run 6 → PLAN-080's sixteen entries, **excluding** `plugin-doctor/test_test_conventions_rule*.py`
- OBSERVED: run 7 → `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` **only**
- OBSERVED: **`test_*.py` only.** A helper module is not this plan's to split — PLAN-105 § D3 makes them
  visible and a **reduction** slice reduces them

## Dependencies and Sequencing

- Depends on: PLAN-030, PLAN-040, PLAN-060, PLAN-070, PLAN-080 (all landed — every ordering prerequisite is
  met), and ⛔ **PLAN-105, which should land first** so D2's instruments exist and D3's widened rule does not
  move the count mid-campaign.
- ⚠️ **PLAN-110 is best run before this plan continues.** A campaign run adds several hundred modules, each
  re-running its own import preamble at collection; PLAN-110 is the instrument that would notice.
- ⛔ **Must not run concurrently with**: PLAN-130 or PLAN-135 (both sweep every slice), PLAN-110 (skip sites
  cross every slice), PLAN-105 § D5 (slice `050`), or PLAN-150 / PLAN-155 (run 5 collides with PLAN-150's
  slice `070`; run 3 with PLAN-155's slice `060`).
- **Surface-disjoint pairing is possible between runs** — two rows touching different slices may in
  principle run together, subject to `parallelization_scope`. ⚠️ **Prefer not to**: run 1's PR already
  forfeited both automated reviews on size, and two concurrent runs make the rebase surface worse without
  making either land sooner.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-140-module-budget-campaign-runs-2-7.md — run {N}, slice {NNN}"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
