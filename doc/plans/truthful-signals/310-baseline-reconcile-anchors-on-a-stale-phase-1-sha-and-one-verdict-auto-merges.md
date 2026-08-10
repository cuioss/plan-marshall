> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Branch-state verdicts computed from the wrong state, that then mutate

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`baseline-reconcile` decides whether a branch has diverged from the base branch and, **on one verdict,
merges automatically**. It anchors every range on a SHA captured at **plan initialisation**, which
cannot describe divergence at finalize.

**Observed in one run, firing twice with two answers:**

| Call site | Verdict |
|---|---|
| the baseline-sync step | `classification: no_overlap` |
| the branch-cleanup step | `classification: overlap_no_content_conflict`, **"2 upstream commits"** |

**Ground truth at both moments: the branch was 0 commits behind the base branch.**

⇒ ⭐ **The two answers are not merely different — they are mutually inconsistent, and NEITHER matches
reality.** A detector returning two contradictory verdicts about one state in one run has **no
defensible reading**; there is no way to consume it correctly.

### Root cause, established by code read rather than inferred from the symptom

The baseline resolver documents its own preference order as *the initialisation-time worktree SHA, then
the current HEAD* — and returns the initialisation-time SHA. ⛔ **It never computes a merge-base.** The
upstream listing then runs `{baseline}..origin/{base}`, and the in-flight listing runs
`{baseline}..HEAD`.

⇒ `{initialisation SHA}..origin/main` is **not** *"commits I am behind by"*. It is *"commits reachable
from the base branch but not from the SHA this plan started at."* **Those sets diverge the moment the
branch's own history advances past that anchor.**

⭐⭐ **And the script CAUSES that divergence itself.** Its focused-reconcile path runs a real merge. After
it, the merged-in upstream commits are in the branch's history **yet are still not ancestors of the
stale anchor** — so the next call **re-reports them as upstream**. **That is the "2 upstream commits"
over-report, and it is self-inflicted.**

The same stale anchor inflates the in-flight set, so the overlap between upstream and in-flight files
becomes non-empty **for files the plan never touched**, and the overlap verdict goes spuriously true.

⇒ **The correct anchor is the merge-base of HEAD and the base branch, recomputed per call.**

## ⛔⛔ Why this outranks an ordinary reporting defect: one verdict MUTATES

The overlap verdict routes to the focused-reconcile path, which **runs a merge automatically**. ⇒ **A
verdict derived from a stale anchor triggers an unrequested merge — and that merge makes the next call's
anchor worse.** ⭐ **A wrong read that also writes is a different severity class from a wrong read**, and
this one is **self-amplifying**.

⚠ **The benign-looking verdict is equally unreliable** — it was returned in the same run against the
same state. **A remedy that only fixes the merging path leaves a false-clean verdict live.**

## ⛔⛔ A resolved contradiction between two absorbed plans — read this before scoping D2

Two earlier specs targeted this same code path and **prescribed opposite remedies**:

| Position | Remedy for the auto-merge verdict |
|---|---|
| One | The probe **never mutates**. A trial merge uses a tree-level merge or a discarded detached state. *The probe classifies; it does not reconcile.* |
| The other | The mutation **stays but fails closed** — derived from a freshly computed range, or it declines to classify. |

⛔ **Whichever landed second would have deleted or hollowed the first**, and neither spec named the
other's remedy, so the collision was invisible from inside either one.

**RESOLUTION — the non-mutating remedy WINS.** A classifier probe whose own contract says it *"performs
no writes"* must not move a branch ref; **hardening the write keeps a documented-contract violation
alive in a softer form.**

⭐ **What survives from the other side is the half it never addressed: the stale anchor.** That position
assumed the range was right and only the mutation wrong. **Both halves are needed** — an anchor
recomputed per call **and** a probe that does not write.

## A third, same-shaped defect on the same decision surface

The branch-sync-state verdict **conflates *never-pushed* with *merged-and-deleted***, and its documented
remedy **resurrects a merged branch**. ⭐ **The contract was saved only by an agent declining to obey
it.**

⭐ Same shape, same module, opposite ends of one decision: one is *the range is wrong so the verdict is
wrong*; the other is *the verdict is right but its two causes need opposite remedies*. **Both end in a
destructive git action taken on an under-determined classification.**

## Goal

Every branch-state verdict is computed from a freshly derived range, the classifier probe writes
nothing on any path, two calls in one run against one unchanged state cannot contradict each other, and
no verdict whose causes are ambiguous can route to a destructive action.

## Deliverables

1. **D0 — GATE: derive every consumer of the baseline anchor and every verdict's side effects.** Mutates
   nothing.
   *Done when:* **both directions** are enumerated — sites that **READ** the anchor, and sites that
   **MUTATE** on a verdict — with the population stated.
   ⚠ **The anchor field is also the field a sibling plan found recording the wrong tree.** Check whether
   this consumer **inherits that defect or is independent of it**. ⛔ **Two plans reading one field is
   how a fix in one silently changes the other.**
   ⛔ **Also report whether the historical blast radius is knowable at all** — how often the auto-merge
   has fired on a stale verdict is **NOT ESTABLISHED**, and it has been live for an unknown number of
   plans. **Saying "not knowable" is an acceptable answer; not asking is not.**
2. **D1 — Anchor on the merge-base of HEAD and the base branch, recomputed per call.**
   *Done when:* no range is computed from a stored SHA.
   ⭐ **Load-bearing.** ⛔ **Per call, not cached.** A cached merge-base **re-creates the defect with a
   shorter staleness window, which is harder to observe rather than fixed.**
3. **D2 — The probe is non-mutating on every path.** The classify-only invocation leaves the branch HEAD
   unchanged on **all** classifications, including the one that currently auto-merges. A trial merge is
   performed at tree level or in a discarded detached state — **never a real merge that moves the ref**.
   *Done when:* no classification path moves a ref.
   ⚠ **Confirm no flow depends on the automatic merge happening** before removing it. **If one does, make
   that dependency explicit** rather than silently breaking it.
4. **D3 — Fail-loud guards on both sides.** A post-probe assertion that HEAD is unchanged.
   *Done when:* a regression is caught **at the probe**, rather than discovered at the landing.
5. **D4 — The two verdicts must be reconcilable, and an ambiguous verdict must not route to a
   destructive action.** Two calls in one run against one unchanged state must not produce contradictory
   classifications; and where a verdict has **two causes needing opposite remedies**, it must
   disambiguate or decline.
   *Done when:* **a test pins both.** ⛔ **A test is the deliverable, not a caveat in a document.**
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) **The live fixture**: a branch 0 commits behind, **after a focused reconcile**, reports no
     overlap and zero upstream **at BOTH call sites**.
   - (b) The in-flight set **excludes files the plan never touched**.
   - (c) The merge-base is **recomputed**, not read from stored status.
   - (d) A contradictory verdict pair across two calls **fails**.
   - (e) The classify-only invocation leaves HEAD unchanged on every classification.
   *Done when:* all five pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables. The source spec, after absorbing
two sibling plans, was counted at **nine against a raised cap of twelve**, with its own instruction that
**overlapping deliverables COLLAPSE rather than concatenate.** That collapse is applied. ⭐ **The natural
split seam, if one is ever forced, is anchor versus mutation** — which was the original plan boundary.
**Kept together because the resolved contradiction above is only visible when both are in one plan.**

## Out of scope

- **Changing what the anchor field means for its other consumers.** A sibling plan owns that field's
  correctness. ⛔ **Serialize, and whichever runs second must re-ground** — the first may change what the
  field means.
- **Hardening the auto-merge rather than removing it.** ⛔ **Explicitly rejected above.** It keeps a
  documented-contract violation alive in a softer form, which is harder to find later.
- **A general branch-recovery workflow.** D4 makes an ambiguous verdict decline; designing the recovery
  path for each cause is a separate job with destructive potential and no operator here to approve it.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py`
  — the resolver, the upstream listing, the in-flight listing, and the focused-reconcile path. **Located
  by symbol.**
- The branch-sync-state verdict path in the same skill.
- The finalize step documents for the two call sites, including the one whose contract states the probe
  performs no writes.
- `marketplace/bundles/plan-marshall/skills/manage-status/**` — the anchor field, **shared with a sibling
  plan**.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Two contradictory classifications in one run, neither matching a 0-behind ground truth | HYPOTHESIS | ⛔ **run artifacts under `.plan/`, not reachable here.** ⭐ **Reproduce the shape instead** — D5(a) is that fixture |
| The resolver returns the initialisation-time SHA and **never computes a merge-base** | HYPOTHESIS | that file — ⛔ **an asserted ABSENCE, and the plan's central premise.** ⭐ **A confirming read reported ZERO merge-base occurrences in the file; re-verify it, it is one search** |
| The upstream and in-flight listings both range from that anchor | HYPOTHESIS | the same file, **by symbol** — the reported line numbers are leads |
| The focused-reconcile path runs a real merge | HYPOTHESIS | that path, **by symbol.** ⛔ **This is what makes the defect self-amplifying** |
| The self-inflicted-divergence mechanism fully explains the "2 upstream commits" | HYPOTHESIS | ⭐ **Strong — it predicts the observed number and direction exactly — but it was reasoned from the code, not instrumented.** Confirm by reproducing |
| The step contract states the probe performs no writes | HYPOTHESIS | that step document — ⛔ **this is what makes the mutation a contract violation rather than a design choice** |
| The sync-state verdict conflates never-pushed with merged-and-deleted, and its documented remedy resurrects a merged branch | HYPOTHESIS | that verdict path and its remedy text. ⭐ **The contract was reportedly saved only by an agent declining to obey it** — treat that as a strong hint, not as evidence |
| How often the auto-merge has fired on a stale verdict | HYPOTHESIS | ⛔ **NOT ESTABLISHED. Live for an unknown number of plans.** D0 says whether it is knowable |
| No flow depends on the automatic merge happening | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — **verify before D2 removes it** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(a) is the fixture that proves the whole thesis**: the same state, probed twice, after a
  reconcile, must agree. If it still disagrees, the anchor was not the only cause and the plan re-scopes.
- ⛔ **D5(e) is the safety test.** A classifier that writes is the severity escalation in this plan;
  proving it no longer writes is what closes it.
- **D3's assertion must be seen to fire** — introduce a deliberate ref move and confirm the guard
  catches it at the probe. A guard never seen to fail is indistinguishable from one that cannot.
- **D0's both-directions enumeration must state its population.** A list of mutating sites produced by
  looking is a sample, and a missed mutating site is exactly the kind that surprises someone later.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing: serialize against the sibling plan that owns the anchor field's correctness.** Whichever
  runs second re-grounds.
- ⛔ **Do not go looking for the orchestrator spec, the absorbed specs, the run artifacts, or any landing
  record.** They live under `.plan/`, which is git-ignored and absent from this clone. The mechanism is
  restated in full above so the run can verify it from source alone.
