# Landing Analysis: PLAN-130 — Sweep the prose the widened rules can now see

epic: test-quality
workstream: WS-02
pr: [#1436](https://github.com/cuioss/plan-marshall/pull/1436) — merged `5c1c8b2124ba4ee37226df1e80e024e679d8383d`
    + [#1435](https://github.com/cuioss/plan-marshall/pull/1435) — merged `681db9446fdaf0b211f50ba8fdd6b0248f843fba`
    ⛔ **not** #1432 — closed unmerged, `merge_commit_sha: null`, shipped nothing

> Landing record for one shipped plan. Lives at `landings/PLAN-130.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Corroboration basis.** All three PR states read through the CI abstraction; both merge
commits confirmed present on `main`; the union of both diffs read from git (112 files);
**`doctor-marketplace test-conventions` re-run at merged `main`** — the plan's central
measurement re-derived rather than accepted; `manage-solution-outline extract-deliverables`
reproduced live; the archived run's `logs/work.log` counted directly; the
`phase-6-finalize/SKILL.md` Signal-3 derivation read at source.

## Deliverable Fidelity vs Spec

Eight deliverables, **all eight complete**. The plan's central claim was re-derived
independently and holds.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — re-derive both populations, verdict per finding (gating) | shipped-as-specified | 232 findings / 111 files re-derived; verdict per finding |
| D2–D5 — the four slice groups | shipped-as-specified | 112 files across the union of #1436 (76) + #1435 (36) |
| D6 — outside plan-marshall + 3 operator-authorized shared-infra sites | shipped-as-specified | the three sites named and authorised |
| D7 — retire the dated provenance prose from the ci-wait README | shipped-as-specified | `test/plan-marshall/phase-6-finalize/fixtures/ci-wait/README.md` is in the realized set — this closes the epic's own long-carried defect |
| D8 — report the measured deltas, verdict table and residual | shipped-as-specified | figures, verdict table and residual all present |

✅ **The headline measurement is independently confirmed.** `doctor-marketplace
test-conventions` at merged `main` returns `test-docstring-historical-prose: 3` — down
from **232 across 111 files**. Not accepted from the report: re-run here.

### The population re-opened during the run that closed it — verified

⛔ The 3 residual findings are **all in one file**,
`test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py`, at
lines 27, 214 and 313 — each a `plan_deliverable_id` citation of "deliverable 1". `git show
--name-only ef129d6a3` confirms **PR #1425 authored that file**, mid-run, and the finalize
rebase folded it in.

⛔ **This is the second observation of the shape, and it is the decisive input to the
epic's carried warning-to-error decision.** PLAN-080's "211 of 211" was falsified within
two days; PLAN-130's closure was falsified *inside its own 22-hour window*. The plan argued
both sides honestly and this analysis endorses that framing: at `error` severity PR #1425
would have been **blocked** — precisely what the flip buys, and precisely what it costs,
since #1425 is unrelated upstream work that would have been stopped on a docstring rule.
The finding to weigh is not the backlog size. It is that **a population that refills faster
than sweeps drain it is not a backlog problem**, now observed twice.

### Realized vs declared surface — mode 2 again, and it is why this epic runs serial

**112 of 112 realized files (100%) fall inside PLAN-130's declared surface**, with 8 of its
9 declared entries hit.

⛔ **That is not a good declaration — it is PLAN-105's failure mode repeating.** PLAN-130
declared `test/` at ROOT, so nothing it did *could* land outside. The epic now has four
measurements across three distinct modes:

| | PLAN-145 | PLAN-105 | PLAN-110 | PLAN-130 |
|---|---|---|---|---|
| Declared | 5 narrow entries | 10 entries, two whole trees | 15 entries + 1 exclusion | 9 entries, `test/` at root |
| Realized inside | **0 of 3** | **514 of 521** | **16 of 29** | **112 of 112** |
| Mode | inaccurate | no discriminating power | accurate + narrow, still 55% | **no discriminating power** |

A 100% figure and a 0% figure are equally useless to the gate. PLAN-130's root claim is
exactly why every pairing check this cycle returned "collides", and why the epic has run
strictly one plan at a time.

## Metrics and Anomalies

- **Tokens**: 4,300,635 across 6 phases. **5-execute 1,615,513 against 6-finalize's
  1,469,848 — a ratio of 0.91×.**
- ✅ **This breaks the streak.** Finalize outspent execute on PLAN-170, PLAN-145, PLAN-105
  (3.33×) and PLAN-110 (1.29×). PLAN-130 is the **first landing in five where it did
  not**. One point is not a trend, but the direction is now monotone across the last three:
  3.33 → 1.29 → 0.91.
- **Duration**: 81,060 s wall (22 h 31 m).
- **Anomalies**:
  - ⛔ **`create-pr` recorded `pr_number=1432`, a PR that shipped nothing.** Only the FIRST
    `create-pr` invocation writes the fact, so the re-created PRs never updated it. Verified:
    #1432 is `state: closed`, `merge_commit_sha: null`, on the same head branch as #1435. The
    plan **refused to transcribe the stale fact** and reported the observed end state with the
    discrepancy named — the correct call, and the reason this ledger has the right PRs.
  - ⛔ **The same stale fact corrupted the retrospective's own measurement**: the footprint
    resolver returned **36 of 112 files** and emitted a spurious `Recall 32% below threshold`
    naming 76 correctly-shipped files as missing. A write-once producer defect propagating
    into a verification instrument.
  - ⚠️ **Two self-inflicted dispatch costs, both self-reported**: the self-review dispatch
    missing required prompt fields (144 K tokens, none recoverable — though the leaf correctly
    **refused rather than returning a false clean verdict**), and a stale local `main` ref
    inflating the candidate-surfacer scope **64×**.
  - ⚠️ **No whole-tree collected-test baseline before the first fix commit.** The zero-delta
    claim rests on an A/B at the same base — 24,714 with and without the edits — not a
    pre/post comparison of the original tree. The plan stated this rather than implying the
    stronger claim.

## Routing and Merge Behavior

- ⛔ **CodeRabbit's 100-file cap is a structural constraint on this epic's remaining
  sweeps.** A tree-wide sweep of this size cannot be reviewed as one PR. The plan split
  along its own deliverable boundaries into **76 + 36** — a legitimate response, and the
  first time this epic has met the cap by design rather than by surprise.
- ⚠️ **The stacked-PR trap cost two 90-minute quota waits.** After a **squash** merge of
  the base, retargeting the child does **not** recompute its merge base — #1435 kept
  reporting 112 files and kept being refused. The remedy is rebasing the child's own commits
  onto the new base. The retrospective calls the retry blind, which it was.
- **Review**: CodeRabbit reviewed **both** halves, found **2 real defects**, both fixed and
  re-reviewed clean; 15 findings, 0 pending.
- ✅ **Review coverage held this time.** Contrast PLAN-105 (zero bots, size refusal) and
  PLAN-110 (1 of 3 reviewers). Splitting under the cap is what bought it — which makes the
  split a coverage mechanism, not just a workaround.
- **CI/merge**: both PRs merged via the merge queue; `main` up to date; worktree removed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `previous_status: launched`, so the launch handshake held
- [x] row `pr` stamped `#1436, #1435` — deliberately **not** the recorded `1432`
- [x] row `landing` stamped — `landings/PLAN-130.md`
- [x] row `plan_marshall_plan_id` stamped
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated
- [x] **12 inbox messages drained and archived; all 11 candidate-lessons promoted** as
      `2026-09-07-15-001` … `-011`, two of them verified and one upgraded from observation
      to confirmed defect
- [x] Open Defect RETIRED — the `ci-wait/README.md` dated-provenance violation (D7)
- [x] Decision input recorded — the warning-to-error flip, second observation
- [x] Open Defect added — `facts.pr_number` is write-once across re-created PRs
- [x] resume_anchor updated

## Follow-Ups

- ⛔ **Candidate 011 arrived as an unverified observation and this analyze settled it as a
  defect.** The `lessons-capture` Signal Gate forwarded
  `signal_script_failure_clusters_count: 1`. Ground truth from the archived `work.log`: **14
  `[ERROR] … script_failure` lines over 7 distinct failing notations**, of which **6 existed
  before the gate evaluated**. The undercount is **6×, not the 3× observed** — the leaf had
  read only the finalize section. **Both of its own alternative explanations are refuted**:
  a narrower phase scope yields 3, not 1, and the records are in the `work` log the gate
  reads. **Root cause located in the instruction text**: `phase-6-finalize/SKILL.md` § Signal
  3 says to bucket by "the `bundle:skill:script` token in the line", but every line carries
  **two** — the emitting `(plan-marshall:execute-script:2)`, identical on every line, and the
  failing `notation=` value. Taking the first reproduces `1` exactly. Fix: name the field.
  ⚠️ This is a **skip gate** — at zero signals `lessons-capture` never runs — so a counter
  that collapses every distinct failure to one is one step from discarding the class.
  Promoted as `2026-09-07-15-011`.
- ✅ **The inbox channel worked as designed this cycle.** PLAN-110 resolved its orchestration
  verdict late and routed everything to the global corpus; PLAN-130 emitted **11
  candidate-lessons + 1 landing** to this epic. The lower-bound caveat this ledger placed on
  candidate-lesson counts applies to PLAN-110's run, not this one.
- **`manage-solution-outline`'s own description defeats its argparse surface — verified
  live.** `SKILL.md:3` reads "deliverable extraction"; the declared verb is
  `list-deliverables`; `extract-deliverables` is rejected. The plan hit it 5 times, its
  retrospective a 6th, and reproducing it here makes **7**. Promoted as `2026-09-07-15-005`.
  ⚠️ This orchestrator hit three instances of the same class in this session alone
  (`manage_status`, `pr-view`, `--number`), so the class is not the plan's.
- ⚠️ **A standing unattended authorization consumed a `decision=needs_user` gate for the
  second time.** PLAN-110 recorded the identical pre-rebase bypass. Two plans, same gate, so
  this is a recurrence rather than an incident. Both outcomes were correct and both were
  logged rather than silent; the concern is the precedent. Promoted as `2026-09-07-15-007`.
- **Six prose/identifier incoherences left for a follow-up pass** — a de-referenced comment
  beside an identifier still carrying the old number (`D1_CORPUS`, `_SOURCERY_1014_REFUSAL`).
  Renaming identifiers is behaviour-adjacent and correctly outside a prose-only sweep.
  Unowned; a natural fold into PLAN-135 or PLAN-160 when either is next re-grounded.
- **HEAD-current rule populations, captured as a side effect of corroboration** (merged
  `main`, `681db9446`) — these are the next cleanup's re-grounding inputs, already paid for:
  `test-module-line-budget` **343 / 343 files** (PLAN-140's campaign; was 279 at `00b92fca`,
  330 at `bf1b7ed6` — still climbing), `test-module-preamble-boilerplate` **103 / 86 files**
  (PLAN-135), `subprocess-pythonpath` **17** (PLAN-135; unmoved and the sole source of the
  gate's 17 errors), `test-docstring-historical-prose` **3**.
