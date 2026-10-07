# Landing Analysis: PLAN-155 — Close the Runtime Slice Parametrization

epic: test-quality
workstream: WS-02
pr: #1455 (squash-merged as `9853a7ababf2aa87a59db1e36f2072680eeda96b`)

> Every figure below was re-derived at the merge commit (`HEAD == 9853a7aba`, clean
> worktree), not transcribed. Where the plan's claim and the re-derivation agree the
> agreement is stated; the two places they diverge are recorded as divergences.

## Deliverable Fidelity vs Spec

Eight deliverables, all reported done. The spec staged this as a fourteen-directory slice
sweep with a cold-read audit; the plan executed it as five collapse deliverables (D1–D5,
partitioned by directory group), an audit (D6), a repair pass (D7) and a report (D8).

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1–D5 — collapse the 14 directories group by group | shipped-as-specified | 97 files across exactly the 14 declared directories |
| D6 — cold-read audit of the collapsed cases | shipped-modified (widened) | operator decision: sample → full sweep |
| D7 — repair the flagged cases | shipped-modified (re-sequenced) | followed audit findings, not TASK-7's pre-computed list |
| D8 — report the measured deltas | shipped-as-specified | landing carries every figure |

**Both deviations were operator decisions and both were correct.** The 40-family sample
surfaced 11 defects across 8 families, which is what made the sample untrustworthy as a
stopping point — widening it found 6 more families, including a *second* instance of the
`ids=`-derived-from-a-foreign-object hazard that mislabels silently on reorder. And only 2
of the 8 flagged files carried a repair step, so following TASK-7's list literally would
have left 6 known-defective files untouched. Both deviations chose the evidence over the
plan; recording them as deviations rather than quietly absorbing them is the right shape.

### Corroborated at the merge commit

| Claim | Re-derived | |
|---|---|---|
| 97 files | **97** | ✓ |
| all under `test/plan-marshall/**` | **0** files outside | ✓ |
| merged, squash, on `main` | single parent, ancestor of `origin/main` | ✓ |
| over-budget among touched set → 48 | **48** | ✓ |
| 10.8M tokens / 23h34m | **10,806,358** / 23h34m | ✓ |
| 5 infrastructure lessons filed | all 5 present, ids as named | ✓ |
| `2026-09-08-21-001` (3 deferred nitpicks) | present | ✓ |
| third-instance recurrence on `2026-09-06-07-002` | original + 2 recurrences | ✓ |

**No regression anywhere in the rule set.** At `9853a7aba`: `subprocess-pythonpath` **5**,
`test-module-preamble-boilerplate` **13**, `test-docstring-historical-prose` **3** — all
identical to the PLAN-135 baseline. `test-module-line-budget` moved **354 → 350**
tree-wide. The gate remains `status: fail` on the same 5 error-severity
`subprocess-pythonpath` false positives and nothing else; that is the inherited baseline,
not this plan's doing.

### Two divergences

⚠️ **The diff stats do not match, and the landing message explains why.** The paste and the
message both report **+7143 / −7642 (net −499)**; `git show --stat` on the squash commit
reports **+7345 / −7626 (net −281)**. The message states its figure is measured *against
the merge base* — i.e. before `finalize-step-sync-baseline` rebased onto 6 upstream
commits. **The landed change is net −281.** Both are honest measurements of different
things; the ledger carries the landed figure, and the file count (97) is identical either
way, so nothing downstream is affected.

⚠️ **The mis-routed-lesson count is understated.** The message says "8 plan-retrospective
lessons plus 2 appended recurrences". The corpus holds **11** lessons in the
`2026-09-08-13-*` block, all dated to this run. The extra rows are plausibly
`review-retrospective`'s rather than `plan-retrospective`'s — the message names three
affected producers but counts only one — so this is an under-count in the narrative, not a
contradiction. **The material fact stands: 11 epic-relevant lessons went to the global
corpus and this epic will never see them by draining.**

### Not corroborated — and why

**Collected pytest items 20,766 → 20,954, skips unchanged at 8.** Establishing this
requires running the suite, which is an implementation build and outside the orchestrator's
boundary. Recorded as an **unverified lead**, not a finding. It is the plan's own
non-decreasing invariant and the thing that makes "collapsed" distinguishable from
"deleted", so it matters — but this analyze did not check it.

## Metrics and Anomalies

- **Tokens: 10,806,358** against a stated 2.5M anchor. That is **4.3x** by arithmetic; the
  paste says 4.0x. Either way it is the largest overrun this epic has recorded.
- **Duration: 7h47m worked / 23h34m wall**, with **15h46m idle** — two thirds of the wall
  clock. 13h4m of that idle sits in 6-finalize alone.
- Per-phase: 1-init 185,273 · 2-refine 158,058 · 3-outline 703,113 · 4-plan 463,553 ·
  **5-execute 5,314,683** · **6-finalize 3,981,678**.
- 5-execute is **49.2%** of the total (the paste says 53%; the measured share against the
  spanning total is 49.2%).

### ⛔ The finalize/execute ratio is now a trend, not a direction

**0.75x** this landing — the **third consecutive sub-1.0** after PLAN-130's 0.91x and
PLAN-135's 0.90x, and monotonically decreasing across all three. The prior anchor stated
that a third would make the direction worth acting on. It has arrived, and the series is
now clean in a way the earlier PLAN-170/145 samples were not (those measured wasted
finalize share, a different quantity). **Finalize no longer outspends execute, and the gap
is widening.** What remains expensive in finalize is *wall time*, not tokens: 13h4m idle.

## Routing and Merge Behavior

- **Three loop-back rounds against a ceiling of 5, all productive** — the cold read found
  11 defects, the widened sweep 6 more, CodeRabbit a further 6 our sweeps missed, including
  a real bug where an absolute right-operand made `tmp_path / invalid` discard the fixture
  root.
- **Twice CodeRabbit's detection was right and its prescribed remedy wrong** — once the
  remedy would have made every assertion tautological. Both were caught and corrected
  rather than applied. This is the second consecutive landing where a bot's remedy was
  declined *with measurement* while its observation was taken; the pattern is now worth
  naming as a competence rather than an incident.
- ⛔ **Sourcery reviewed nothing, structurally, on every round** — its 150,000 diff-character
  cap against a measured 14,971 changed lines. It is optional so it blocked nothing, but
  `review_completeness` reports `proves: participation_only`: the quorum was satisfied over
  what is, in review-content terms, a **single-reviewer PR**. That is the third landing in
  five where review coverage was thinner than the quorum implies.
- **CI/merge:** merged via merge queue, all checks green, branch and worktree removed.

### Declaration form: the first informative measurement in this epic

⛔ **This is the finding of the landing.** PLAN-155 realized **97 of 97 files inside its
declared surface** — and unlike every prior measurement, **the declaration was narrow**: 15
entries (14 named directories plus `test/conftest.py`), not a root `test/` claim. All 14
directories were touched; `test/conftest.py` was declared and correctly not needed; nothing
landed outside.

This is the sixth measurement and the **first in which the declaration could have been
violated and was not**. PLAN-130's 112 of 112 and PLAN-135's 89 of 89 were uninformative
because a root claim means nothing *could* land outside. Here the gate had a real
declaration to work with, and it used it: the PLAN-165 collision on
`test/plan-marshall/manage-providers/` was machine-detected from exactly this surface.

⚠️ **This is evidence against the carried retirement of "accurate AND narrow".** That
remedy was retired by PLAN-110 on the grounds that the answer must be a different *shape*.
PLAN-155 is a counterexample: a narrow, accurate, machine-usable declaration, authored
without apparent difficulty, on a 97-file sweep. The retirement should be **re-opened and
re-argued against this instance** rather than left standing unexamined — one counterexample
does not overturn it, but it does oblige a re-argument.

## Reconciliation Actions

- [x] row `status` → `shipped` (from `launched` — see the handshake note below)
- [x] row `pr` stamped `#1455`
- [x] row `landing` stamped `landings/PLAN-155.md`
- [x] row `plan_marshall_plan_id` stamped `close-the-runtime-slice-parametrization`
- [x] Open Defect retired: PLAN-060's D4 parametrization families — the epic's largest unowned item
- [x] Open Defects added: the 11 undrainable lessons; the third-instance mis-routing; the five infrastructure defects; single-reviewer quorum
- [x] Watch retired: finalize/execute direction — promoted to a trend
- [x] Watch added: the "accurate AND narrow" retirement needs re-argument
- [x] START-HERE and Ordered Queue blocks regenerated

### ⛔ The launch handshake was NOT completed for this plan

PLAN-155 went **`staged → launched → shipped`**. The `running` state was never recorded,
because when the start was reported the orchestrator probed for ground truth and found
none — no plan directory, no worktree, no branch, nothing under `.plan/local` touched in
the preceding 30 minutes — and declined to record a state it could not observe. The plan
evidently *did* run (it is archived at
`.plan/local/archived-plans/2026-09-09-close-the-runtime-slice-parametrization`), so the
probe was simply too early or ran against the wrong checkout.

**The refusal was correct and the ledger is honest, but the gap is real**: this epic now
has one plan whose lifecycle skipped `running`, and the two-hop handshake that worked for
PLAN-130 and PLAN-135 did not work here. The cheap fix is to report a start *after* the
plan directory exists.

## Follow-Ups

- **11 lessons this epic cannot drain** (`2026-09-08-13-001` … `-13-011`) — in the global
  corpus because the finalize dispatcher forwarded `orchestrated: false` without running
  the resolution seam. **Third consecutive instance in this epic** (PLAN-145's epic,
  PLAN-135, PLAN-155), recurrence appended to `2026-09-06-07-002`. Until the dispatcher is
  fixed, every landing in this epic loses its lesson stream.
- **Five infrastructure defects**, all filed, none this plan's subject: `2026-09-08-22-001`
  (issue-comment-only bots can never satisfy `head_sha_verified`), `2026-09-08-22-002`
  (`scope_creep_check` crashes at persist on every over-threshold plan), `2026-09-09-01-001`
  (self-review surfacer reports clean on a class it enumerates), `2026-09-09-01-002`
  (loop-backs never re-open the metrics row), `2026-09-09-01-003` (Step 10's commit
  predicate tests the plan's chain tail, not the deliverable's).
- **Three deferred CodeRabbit nitpicks** (`2026-09-08-21-001`) — each needs a
  `marketplace/bundles/**` change PLAN-155's surface excluded. Shared shape: *a test
  mirroring a production set that production does not expose*. → WS-03 / WS-04.
- **Two self-corrections the plan reported** — a fabricated full SHA on a completion record,
  and the `orchestrated: false` forwarding. Both logged by the plan; the second is the
  systemic one.
