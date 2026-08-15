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

# A plan's frozen manifest diverges from live config, and nothing reconciles them

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

A plan's execution manifest is **composed early and frozen**, then consumed at finalize against a
configuration that may have changed since — **including by the plan's own edits**. A self-modifying
plan's frozen manifest therefore references steps that no longer exist, or misses steps that now do.

Separately, after a rebase that changes the script set, the per-tree executor is **not regenerated**,
so a dispatch into a clean environment cannot resolve script notations at all.

Make the frozen view reconcile against the live one instead of silently diverging.

⚠ **This plan carries the oldest claims in its queue, and that is stated rather than hidden.** A
recent reconciliation of the same queue retired one sibling spec **in full** and halved another for
exactly this reason. ⛔ **Expect at least one of these defects to have been closed by unrelated work.**

## Goal

At finalize entry a plan's frozen manifest is **compared against live configuration** and reconciled
in a direction that has been deliberately chosen; a rebase that changes the script set leaves a
regenerated executor behind; and the small prompt/log residue that accumulated alongside them is
cleared.

## Deliverables

1. **D0 — GATE: re-ground all four defects against the implementing source. Mutates nothing.**
   ⛔ **This plan's claims are the oldest in its queue and MUST be re-verified before any is scoped.**
   For each: read the site, state whether the defect is live at HEAD, and drop the ones that are not.
   *Done when:* each of the four carries a confirmed-or-refuted verdict naming the file and symbol
   that settled it. **A refuted item is dropped and recorded, not quietly carried.**
2. **D1 — GATE: establish what diverges and how it is handled today. Mutates nothing.**
   Read the finalize-entry path: is the frozen manifest compared against the live candidate set **at
   all**, and what happens on divergence — a hard failure, a silent pass, or nothing?
   ⛔ **Settle the fail-direction BEFORE writing the fix.** A hard failure on a self-modifying plan
   blocks legitimate work, which is why the originating report asked for **diff-and-backfill, not a
   hard fail**.
   *Done when:* the current behaviour is named and the intended fail-direction is decided and
   recorded.
3. **D2 — reconcile the frozen manifest against live configuration at finalize entry.**
   Diff and backfill per D1's settled direction.
   *Done when:* a frozen manifest referencing a deleted step reconciles rather than failing hard or
   passing silently.
   ⭐ **State the self-exercisability trap this deliverable inherits**: a plan that changes
   finalize-entry behaviour runs **its own** finalize under the manifest frozen at **its own** outline
   — i.e. under the OLD behaviour. ⛔ **Its own green finalize is NOT evidence the fix works.** Name
   the observation point: the next plan composed after this one merges.
4. **D3 — regenerate the per-tree executor after a rebase that changed the script set.**
   *Done when:* a rebase changing the script set leaves a regenerated executor, and a clean-environment
   dispatch resolves notations afterwards.
   ⚠ **Same family as the recurring cache/executor/registry drift tracked elsewhere** — read across,
   but ⛔ **do not absorb the registry-pin work**: another epic owns it and there is a standing
   do-not-duplicate on it.
5. **D4 — finalize prompt and log residue.**
   - The dispatched simplify prompt gains a **line-level** *"pre-existing lines are out of scope"*
     clause under changeset scope; today the boundary is **file-level only**, so a dispatched
     simplifier is invited to rewrite lines the changeset never touched.
   - Suppress the repeated title-token INFO line when the token value is unchanged.
   - Promote the standing rule that a bypass/guard branch is placed **before** the dispatch it guards.
   *Done when:* each is either shipped or recorded as already-closed by D0.
6. **D5 — tests, each verified to FAIL pre-fix.**
   (a) a frozen manifest referencing a deleted step reconciles per D1's direction; (b) a script-set
   rebase leaves a regenerated executor; (c) an unchanged title token emits no repeated line.

Six deliverables with two gates — **at the split guard**. ⚠ **Evaluate the split at outline.** This
arm has the **weakest internal cohesion** of its family and that is stated rather than hidden: D1–D3
are one story (a frozen view going stale mid-run) while D4 is genuinely miscellaneous residue that
was grouped by **who filed it**, not by surface. ⛔ **If the outline finds D4 does not belong beside
D1–D3, drop it to its own trivial plan rather than carrying it.**

## Out of scope

- **The step and dispatch emission arm** (a step that runs and leaves no trace). Excluded — a sibling
  plan owns it from a documented split.
- **The boundary-ledger arithmetic** (a coverage ratio over an undeclared population). Excluded —
  a second sibling owns it.
- **The plugin-registry pin inversion.** ⛔ Excluded with a standing do-not-duplicate: another epic
  owns it. Same failure family, different mechanism; merging them would hide that a fix for one does
  not cover the other.
- **Hard-failing on manifest divergence.** Excluded per D1's reasoning unless D1 explicitly chooses
  it — a hard fail blocks the self-modifying plans that are the main population here.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` — the frozen-versus-live
  reconciliation. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the baseline-sync executor
  regeneration and the simplify prompt. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/manage-status/` — the title-token log emission.
  **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The manifest is composed early and frozen, then consumed at finalize | **OBSERVED** | The manifest composition and the finalize-entry consumption — both in the clone. Read them. |
| A self-modifying plan's frozen manifest references steps that no longer exist | **HYPOTHESIS, and OLD** | The finalize-entry comparison site. ⛔ **D0 re-grounds it.** |
| The per-tree executor is not regenerated after a script-set-changing rebase | **HYPOTHESIS, and OLD** | The baseline-sync step's post-rebase path. ⛔ **D0 re-grounds it.** |
| The simplify prompt's scope boundary is file-level only | **HYPOTHESIS, and OLD** | The prompt body in the clone — a direct read settles it. |
| The title-token line is emitted unconditionally | **HYPOTHESIS, and OLD** | The emission site in the clone. |
| All four are still live at HEAD | ⛔ **ACTIVELY DOUBTED** | These are the oldest claims in the queue, and a recent reconciliation of sibling specs retired one **in full** and halved another. **D0 exists because at least one of these has probably already been closed by unrelated work.** |

An asserted **absence** ("nothing compares the frozen manifest against live config") is verified
exactly as an asserted presence — and it is D1's first question, not an assumption.

## Verification

- **D0's refutations are as valuable as its confirmations** and must appear in the run report. A plan
  that silently carries a dead claim into implementation produces a change that fixes nothing.
- **D2 cannot be verified by this run's own finalize.** State that explicitly and name the observation
  point instead. ⛔ A green finalize here is evidence of nothing for this deliverable.
- **D5's tests are each verified to fail before the fix.** Record the pre-fix failures.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Priority.** This is the lowest-priority arm of its family: it carries the oldest and least
  corroborated claims and **blocks nothing**, unlike its siblings. Sequence it last of the three.
- **Serialization.** Shares the finalize surface with both siblings from the same split — sequence,
  never run concurrently.
