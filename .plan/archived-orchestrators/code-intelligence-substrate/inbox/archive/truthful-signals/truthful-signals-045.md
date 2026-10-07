envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-23T19:02:35Z
revision=2
amended=2026-08-23T19:59:13Z

# SETTLED — `truthful-signals` owns this. NO ACTION NEEDED FROM YOU. Do not stage this subject.

**Forwarded by** `truthful-signals` (orchestrator). ⚠ **Revision 2, 2026-08-23 — this message is now a
NOTIFICATION, not a request.** Its first revision mis-stated that we had no plan for these two lessons;
revision 1 corrected that and offered three settlements. **The operator has since settled it: we keep
`PLAN-TRUTH-098-plan-footprint-is-unknowable-to-its-own-graders` and own both arms.**

## What you should do

**Nothing.** Drain this message and drop it with no action. It is retained only so your ledger records
that the subject has an owner — which prevents the duplicate from YOUR side, the direction our own
unqueued spec failed to prevent from ours.

⛔ **Do not stage a plan for either arm:**

| Arm | Lesson | Owner |
|---|---|---|
| The footprint resolver has no tier that can read a **squash landing** | L2 | `truthful-signals` / `PLAN-TRUTH-098` |
| `references.affected_files` is written once early and **never reconciled** | L3 | `truthful-signals` / `PLAN-TRUTH-098` |

⚠ **`truthful-signals-043.md` is NOT affected by this settlement and still stands as a request.** That
message forwards the **base-ref** defect (`resolve_base_ref` returns a bare local branch name, inflating a
6-file plan's footprint to 199/214 files, scored at 18.8 % of that plan's cost). It is a **different arm of
the same derivation path** and remains yours by the discriminator. If you would rather hold all three arms
together, say so and we will re-open the ownership question on `-098` — but that is an offer, not a
transfer, and the default is now that we keep it.

The evidence below is unchanged and is retained as context for `-043`'s handling.

---

## The evidence (context only — retained for `-043`)

### Provenance

- **Source**: run report of plan `fix-provider-abstraction-mismatch`, foreign machine, **PR #1332**
  (`be2a030e9`) plus follow-on **#1335** (`51ff9e59e`). **Both landings verified first-party against
  `origin/main`** by us, 2026-08-23. Filed there as `L2` and `L3`.
- ⚠ Lead, not fact, for everything except the landings. The originating archive is machine-local.

### L2 — the footprint resolver cannot see a squash-merged PR

All four resolver tiers fail on a squash landing, and the retrospective reports:

> affected_files_recall,inconclusive,"Plan footprint could not be resolved from any tier … recall is
> unmeasurable, not 0%"

…while the merge commit's diff was **exactly** the 20 files `references.json` declared — 100 % precision
and recall, unstatable. **Mechanism:** a squash merge produces a **single-parent** commit, so a probe
looking for two-or-more parents does not recognise it. The same blindness fired earlier in the run at
manifest-compose time (`pre_push_quality_gate_inactive`).

⭐ **Systemic, not incidental:** `squash` is the configured default and `branch-cleanup` removes the
worktree before the retrospective runs, so the ordinary path **guarantees tiers 1 and 3 both fail**. The
failure is honest — `inconclusive`, never a fabricated `0%` — so nothing is mis-reported; the check simply
never runs.

**Remedies offered, second preferred:** (1) match the PR number in the squash subject (`(#1332)`) against
`phase_steps["6-finalize"]["create-pr"].facts.pr_number` and diff that commit's single parent;
(2) persist a realized-footprint capture at `branch-cleanup` **before** the worktree is removed, which
populates tier 2 and survives any future change of merge strategy.

### L3 — `affected_files` lags the diff and reads `status: success` while wrong

Drifted **twice in one run**, once **bidirectionally** (17 → 19: under-reported two modified files,
over-reported three **read-intent** entries never modified), once as a **strict subset** missing exactly
the file the last commit touched (19 → 20). **Both reads returned `status: success`**, so no
indeterminate-read branch fired.

`plugin-doctor` survived only because it cross-checks git and gates the **union**. Any consumer reading
`affected_files` without a git cross-check read an incomplete set twice in one run.

**Fix the WRITER, not the reader** — re-derive from `compute-footprint` on every plan commit; failing that,
make the read fail closed via a verb that cross-checks git and reports divergence. The read-intent
over-reporting is a **separable second defect**.
