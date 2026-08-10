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

# `main_sha` records the worktree HEAD, and `config_hash` fires at every boundary

**Epic:** truthful-signals
**Branch prefix:** fix

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

Every invariant that names a tree records that tree's sha or records `unknown`; no drift warning can be
emitted from a value the capture could not establish; and a hash that fires every time is either fixed
or renamed to what it actually measures.

## Deliverables

1. **D0 — GATE: confirm the capture mechanism by symbol, for both invariants, and derive the
   population.** Mutates nothing.
   *Done when:* the capture path for each invariant is read and reported, and **every invariant captured
   in the handshake is classified by whether it resolves against an explicit handle or against the
   current working directory.**
   ⛔ **The proposed root cause — that the execute phase pins the working directory to the worktree, so a
   capture resolving "main" via a cwd-relative HEAD resolves to the worktree branch head — was labelled a
   HYPOTHESIS by the person who reported it.** ⚠ It fits the evidence (earlier phases run unpinned and
   are correct; only the execute phase is wrong) but **fitting is not proving.**
   ⭐ **The main-sha invariant is unlikely to be the only one.** ⭐ **And the cheapest first check is to
   re-run the containing-ref query on the recorded commit** — it is still available and settles the
   observation in one command.
2. **D1 — Resolve the main sha against an explicit main-checkout handle**, never a cwd-relative HEAD.
   *Done when:* the capture is handle-based and demonstrably correct from inside a worktree.
   ⭐ **Load-bearing.** This is the same class as the standing rule *never judge a merge lock stale from a
   worktree-scoped store* — **cite that precedent rather than re-deriving it.**
3. **D2 — A capture-time assertion that fails closed.** The main sha **must** be an ancestor of the
   remote main branch. A captured value that is not is a **capture bug**.
   *Done when:* such a value is recorded as **`unknown`**, never as a confident wrong sha.
   ⭐ This is clause-for-clause the fail-closed discipline this project already shipped into its code
   standards — **apply the standard to the machinery that shipped it.**
4. **D3 — Settle the config-hash stability before its warning is trusted OR suppressed.** Determine
   whether the four drifts were real.
   *Done when:* **a determination is recorded.** If the hash is context-dependent, either make it
   context-independent **or rename the field to what it actually measures.**
   ⛔ **A determination IS the deliverable. Do not suppress an unexplained signal.**
5. **D4 — Reconcile the two sha fields.** If they can hold the same value, one is redundant or misnamed.
   *Done when:* the decision is made **and the rejected option is recorded.**
6. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) A capture performed with the working directory pinned to a worktree records the **main
     checkout's** sha.
   - (b) A non-ancestor value yields **`unknown`**, not a warning.
   - (c) The summarizer does **not** emit a drift warning for the observed boundary pair.
   - (d) D0's population is asserted non-empty.
   *Done when:* all four pass, each seen red first.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables, **at the threshold**. Split
evaluated: **D3/D4 are the split point** — the config hash is a separate invariant sharing only the
snapshot. **Kept together because D0's population sweep serves both** and would otherwise run twice.
⛔ **If D0 shows the two invariants have different capture paths, SPLIT before implementation** — this
rationale is recorded so the decision is not silently re-made.

## Out of scope

- ⛔ **Suppressing the config-hash warning.** See D3. Suppression and absence are indistinguishable
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

- ⛔ **D5(a) is the test that matters.** A capture taken from inside a worktree must record the main
  checkout's sha. Every other test here can pass on a capture that is simply never exercised from a
  worktree — which is how this shipped.
- ⛔ **D2's fail-closed path must be exercised deliberately.** Feed a non-ancestor value and assert
  `unknown`. A fail-closed branch never seen to fire is indistinguishable from one that cannot.
- **D3's determination belongs in the report either way.** "The hash is context-dependent and here is
  why" and "the drifts were real and here is what changed" are both successful outcomes. **Silence is
  not.**
- **D0 must report the classified population, not just the two known invariants.** The whole reason for
  the sweep is that the named instance is unlikely to be alone.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing: serialize against anything else reading or writing the plan status document.** At
  least two sibling plans in this epic do.
- ⛔ **Do not go looking for the orchestrator spec, the phase-handshake snapshot, the work log, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. The one
  piece of evidence that **is** reachable — the containing-ref query on the recorded commit — is named
  above as D0's first check.
