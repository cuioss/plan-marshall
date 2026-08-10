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

# `config_hash` fires at every boundary and cannot fail usefully

**Epic:** truthful-signals
**Branch prefix:** fix

> ⛔⛔ **OWNERSHIP CORRECTION — READ BEFORE SCOPING. THE `main_sha` HALF IS NOT THIS PLAN'S.**
>
> A plan in the `code-intelligence-substrate` epic —
> `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd.md` — **owns the
> main-scoped-field defect in full**: the same field, the same resolver, the same fail-closed capture
> assertion, the same population sweep. **It is the same defect, not an adjacent one.**
>
> ⛔ **And it is further along than this plan was.** It has **verified first-party at HEAD** that the
> capture **already passes an explicit tree argument**, so the obvious remedy — *"resolve it against an
> explicit main-checkout handle"* — **is ALREADY IMPLEMENTED and would be a NO-OP with a green test.**
> The real defect sits one layer down, in the repository-root resolution helper.
>
> ⇒ **This plan is narrowed to the `config_hash` half, which that plan does not cover.** ⛔ **Do not
> implement the sha half here.** Read that plan first; if it has landed, re-ground against it.
>
> ⭐ The sha half is retained below **as context only**, because it is what makes the `config_hash`
> finding legible — both were captured in one snapshot.

## Problem

An invariant **named for one tree records the sha of a different tree**, and the drift detector built on
it then reports **a drift that never happened**. A second invariant in the same snapshot fires at **4 of
4** boundaries and therefore carries no information at all.

⭐ Two failure modes, one snapshot: **a confidently wrong value**, and **a detector that cannot fail
usefully.**

### A — `main_sha` holds a commit that was never on the main branch

An execute-phase snapshot recorded a `main_sha` whose only containing ref was **the plan's own feature
branch**. The commit was authored *by that plan*, and reached the main branch only later, as part of a
squash. **It was never on main at the moment of capture.**

⭐⭐ **The same status document simultaneously held the RIGHT value** under the same name in its metadata,
and the work log shows that correct value being written. ⇒ **Two fields under one name, one correct and
one not, in one document** — so this cannot be blamed on the sha being unobtainable.

The downstream consequence was duly reported: a warning describing a **drift of the main branch that did
not occur**. A reader reconciling against it is reasoning from a fabricated fact. ⚠ The snapshot
separately carries a worktree-sha invariant — so **the two fields are recording the same tree under two
names**, which is also why the drift looked plausible.

### B — `config_hash` drifted at all four boundaries over a footprint with no config file

Four successive hash values across four boundaries, while the plan's merged footprint **contained no
configuration file at all**.

⇒ Either something outside the plan mutated configuration four times in thirteen hours, **or the hash is
not stable across the contexts it is computed in.** ⭐ **A drift signal that fires at 4/4 cannot
discriminate "config changed" from "hash is noisy"** — the definition of a detector that cannot fail
usefully.

⛔ **Do not "fix" it by suppressing the warning.** Suppression is indistinguishable in effect from the
signal being absent, which is this epic's own archetype.

## ⛔ SURFACE CORRECTION — an earlier reading named the wrong module

An initial scoping pointed at the status-management skill. **Verified: its scripts contain zero
occurrences of the relevant field names.** The capture surface actually lives in the plan skill's
invariants module — the per-invariant capture functions, the invariant registry, and the blocking-phase
maps — with the change-ledger script as the heaviest non-test consumer.

⇒ **A plan aimed at the status skill would have found nothing.** Re-derive the surface before scoping.

⛔ **And the premise itself is PLAUSIBLE, NOT SETTLED.** The main-sha capture resolves through a
repository-root helper whose **own docstring asserts it is the main checkout root** — but whether it is
depends entirely on whether the underlying base-directory resolution is main-anchored when called from
inside a worktree. **Settle it by reading that resolution, not the docstring.** ⭐ A docstring asserting
"main" while the resolution may return the worktree **is itself the doc-contract-divergence archetype**,
and would make the invariant's name a claim rather than a fact.

## Goal

A drift signal that fires at every boundary is either fixed so it can discriminate, or renamed to what
it actually measures — and in neither case is it silenced.

## Deliverables

1. **D0 — GATE: confirm the config-hash capture by symbol, and derive its inputs.** Mutates nothing.
   *Done when:* the hash's computation is read and reported, and **every input it consumes is named**,
   so a context-dependent input is identifiable rather than inferred.
   ⚠ **Classify the capture by whether it resolves against an explicit handle or against the current
   working directory** — the sibling sha defect (owned elsewhere, see the ownership block) turned on
   exactly that distinction, and the same resolver may be in this path too.
   ⛔ **If D0 finds the config hash shares the mis-resolving root helper that the sibling plan owns,
   STOP and hand this to that plan** rather than fixing the resolver twice.
2. **D1 — Settle the stability question before the warning is trusted OR suppressed.** Determine whether
   the four observed drifts were real.
   *Done when:* **a determination is recorded.** If the hash is context-dependent, either make it
   context-independent **or rename the field to what it actually measures.**
   ⛔ **A determination IS the deliverable. Do not suppress an unexplained signal** — suppression and
   absence are indistinguishable downstream, which is the defect this epic exists to remove.
3. **D2 — Tests, each verified to FAIL pre-fix.**
   - (a) The same configuration hashed from two different contexts produces the **same** value — or, if
     D1 concludes the field is inherently context-scoped, the renamed field is asserted to mean that.
   - (b) A genuine configuration change **still** produces a drift signal. ⛔ **The control that stops
     this fix from silencing the invariant altogether.**
   *Done when:* both pass, each seen red first.

Three deliverables — **narrowed from six** by the ownership correction above.

⭐ **Split-guard verdict, recorded before hand-over:** the original scoping carried six deliverables and
recorded that **D3/D4 were the split point, because the config hash is a separate invariant sharing only
the snapshot with the sha work.** ⛔ **That split has now been forced by the duplication finding rather
than chosen** — the sha half is owned by another epic's plan, so what remains here is exactly the half
the split guard already identified as separable. The earlier rationale is preserved so nobody re-merges
them.

## Out of scope

- ⛔⛔ **THE ENTIRE `main_sha` HALF — resolver fix, capture-time ancestor assertion, the two-sha-field
  reconciliation, and the population sweep of main-scoped captures.** Owned in full by
  `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd.md`. ⛔ **Implementing it
  here would duplicate a plan that has already refuted the obvious remedy** — and would most likely ship
  that refuted no-op, with a green test over an unfixed defect.
- ⛔ **Suppressing the config-hash warning.** See D1. Suppression and absence are indistinguishable
  downstream, which is the defect this epic exists to remove.
- **A second `.plan/` path-exemption defect found at the same site.** The dirty-path filter drops every
  path beginning with `.plan/` on the rationale that such writes are normal bookkeeping — **the identical
  exemption another guard uses, with the identical hole**: a number of files under `.plan/` are
  git-**tracked**, so a tracked edit there is invisible to this invariant too. ⛔ **Second site, same
  class — it belongs to the plan that owns that exemption.** Record it; do not fix it here.
- **The related wrong-commit-recorded-confidently instance in baseline reconciliation.** Related in
  **kind**, not in surface. **Cite it, do not merge it.**

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — the per-invariant
  capture functions, the invariant registry, and the blocking-phase maps. **Located by symbol.**
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py` — the
  heaviest non-test consumer.
- The base-directory resolution helper the capture depends on — ⛔ **read its resolution, not its
  docstring.**
- The invariant summarizer that emits the drift warning.
- Tests.

⛔ **NOT the status-management skill.** An earlier reading named it and it contains none of these fields.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The recorded main sha's only containing ref was the plan's own feature branch | HYPOTHESIS | ⭐ **`git branch -a --contains {sha}` — cheap, still available, and D0's very first check.** Reported first-party with the result quoted, but **not independently re-derived** |
| The same document held the correct value in its metadata | HYPOTHESIS | ⛔ the status document is under `.plan/` and **not reachable from this clone.** Reproduce the shape instead: capture from a worktree and compare the two fields |
| A drift warning was emitted describing a change to main that did not occur | HYPOTHESIS | the summarizer's logic — **checkable from source**, independent of the run record |
| Four config-hash values drifted across four boundaries over a footprint with no config file | HYPOTHESIS | ⛔ same provenance caveat. ⚠ **Genuinely undetermined — both branches are live.** D3 must **decide** it, not assume it |
| The capture resolves through a cwd-relative HEAD because the execute phase pins the working directory | HYPOTHESIS | ⛔ **so labelled by the reporter. Confirm by symbol before scoping** — it fits the evidence, and fitting is not proving |
| The repository-root helper's docstring asserts "main" while its resolution may not be main-anchored | HYPOTHESIS | that helper and the base-directory resolution beneath it. ⭐ **If true, this is the doc-contract-divergence archetype at the same site** |
| The status-management skill contains none of these fields | OBSERVED | those scripts — an asserted **absence** that **re-scoped the whole plan**, and cheap to re-confirm |
| The two sha fields can hold the same value | HYPOTHESIS | both capture paths — **D4's premise** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D2(b) is the control and the most important test here.** A genuine configuration change must
  still produce a signal. Without it, "the hash no longer fires at every boundary" is satisfied by a
  hash that never fires at all — which is the same defect with the sign flipped.
- **D1's determination belongs in the report either way.** "The hash is context-dependent and here is
  why" and "the drifts were real and here is what changed" are both successful outcomes. **Silence is
  not.**
- ⛔ **D0's hand-off condition must be checked explicitly.** If the config hash resolves through the
  same root helper the sibling plan is fixing, **say so and stop** — two plans fixing one resolver in
  parallel is exactly the collision this review exists to remove.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing: serialize against anything else reading or writing the plan status document**, and
  ⛔ **against the sibling epic's main-scoped-field plan**, which may touch the same capture site.
- ⛔ **Do not go looking for the orchestrator spec, the phase-handshake snapshot, the work log, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. The one
  piece of evidence that **is** reachable — the containing-ref query on the recorded commit — is named
  above as D0's first check.
