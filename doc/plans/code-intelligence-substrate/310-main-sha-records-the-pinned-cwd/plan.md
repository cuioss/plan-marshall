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

# A main-scoped field resolves to the worktree, so every worktree plan emits a false drift warning

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The phase-handshake invariant record captures a field named for the **main** checkout's commit. From
a certain phase boundary onward the working directory is pinned to the plan's own worktree, and from
that boundary on the main-named field silently holds a **feature-branch** commit. The invariant
summariser then reports **drift** at that boundary on **every worktree-backed plan**, while main did
not move.

⭐ **The row disproves itself without any external reference.** A record in which the main commit
equals the worktree commit, **while a separate worktree column exists**, is definitionally wrong
unless the plan runs on main — and these plans do not. **The evidence needed to detect the bug is
already inside the record; nothing consumes it.**

## ⛔⛔ The stated mechanism is REFUTED, the symptom is CONFIRMED — read before scoping

**The symptom is confirmed live and recently** — a second independent instance on a worktree-backed
plan, with the earlier boundary rows correct, **localising the defect to the phase boundary exactly
as predicted.**

⛔⛔ **But the originally-stated mechanism is FALSE at HEAD.** The load-bearing hypothesis was *"the
capture reads HEAD of the current tree with no explicit tree argument."* **Verified first-party: it
does not — the capture already passes an explicit tree.**

⇒ **The obvious remedy ("read it via an explicit main-checkout argument") is ALREADY IMPLEMENTED and
would be a NO-OP.** The defect has moved one layer down: **the helper that resolves the repository
root infers it by walking up from a base directory, and that inference returns the worktree** when the
working directory is pinned there, or when the base-directory environment points at the worktree's own
tree.

⭐ **This is exactly what the plan's own verify-first clause anticipated** — *"if capture already takes
an explicit path and resolves it wrongly, the remedy changes shape."* **It did, and the clause paid
for itself.** The plan gets **smaller and more precise**:

- ⛔ **Do NOT add a second explicit-tree argument at the capture site.** The argument is already there
  and correct; **adding another would leave the real defect and ship a no-op with a green test.**
- ⚠ **The blast radius is WIDER than two fields**: **every consumer of the root-resolution helper
  inherits the mis-resolution.** Enumerating its callers is mechanical and cheap, and it is the honest
  form of the *a reported instance is a sample* rule.

## Goal

A field that claims to describe main is read from main; a self-contradictory record is refused at
capture time rather than persisted; and the historical false drift warnings are documented as
non-actionable rather than silently carried.

## Deliverables

1. **D1 — GATE: derive the population of main-scoped captures, and of the resolver's callers.
   Mutates nothing.**
   Enumerate every field that claims to describe **main** and establish, per field, **which tree it is
   actually read from**. Then enumerate the callers of the root-resolution helper, since all of them
   inherit the defect.
   ⚠ **Population-derived, not the two fields this plan names** — those were found by one run, and a
   reported instance is a sample. A known sibling archetype (a lock judged stale from a
   worktree-scoped store) is evidence the class has more than one member.
   *Done when:* both populations are enumerated from source and published with their counts.
2. **D2 — fix the RESOLUTION, not the call site.** Make the root-resolution helper resolve the main
   checkout under a pinned working directory, so a main-scoped capture reads main rather than the
   worktree that shadows it.
   *Done when:* under a pinned worktree, the resolver returns the main checkout — asserted directly on
   the resolver, not only through the capture.
3. **D3 — fail loud on the impossible state.** Assert at capture time that a worktree-backed plan's
   main commit **differs** from its worktree commit. A violation is a **capture bug, not a valid
   row**: refuse to persist rather than writing a self-contradictory record.
   *Done when:* the assertion rejects an equal pair under a worktree-backed plan and permits it for a
   plan genuinely running on main.
4. **D4 — quarantine the already-written rows.** Historical records carry the mislabelled value, so
   every past drift warning at that boundary is a guaranteed false positive.
   ⛔ **Report the affected count SEPARATELY from the number of plans examined** — volume-read-as-coverage
   is a recorded recurring archetype here.
   ⚠ **Corpus reachability**: those records live under a **machine-local, git-ignored** path **not
   present in this clone** ⛔ **— do not search for it.** If unreachable, **ship the documented rule**
   (pre-fix drift warnings at that boundary are not actionable) and **report the count blocked**.
   No corpus rewrite is in scope either way.
5. **D5 — tests, each verified to FAIL pre-fix.**
   (a) a worktree-backed plan's handshake at that boundary records a main commit **differing** from its
   worktree commit;
   (b) the capture-time assertion rejects an equal pair under a worktree-backed plan;
   (c) the summariser emits no drift warning across that boundary when main did not move.

Five deliverables with D1 a gate — under the split guard.

## Out of scope

- **Adding another explicit-tree argument at the capture site.** ⛔ Excluded because it is **already
  there** — this is the single most likely wrong fix, and it would ship a green test over an unfixed
  defect.
- **Rewriting the archived corpus.** Excluded — D4 assesses and documents; it does not repair.
- **The footprint-read-outside-its-window defect.** Excluded: **same polarity** (a reading taken from
  the wrong tree or the wrong moment) but a **different seam and a different file**, and that plan is
  already at its split guard. ⛔ **Do not merge them.**

## Expected surface

- The phase-handshake capture site — the writer of the main-scoped columns. **OBSERVED**; locate by
  symbol rather than by line.
- The repository-root resolution helper and the base-directory resolution beneath it — **the actual
  defect site.** **OBSERVED.**
- The invariant summariser — the drift-warning consumer. **HYPOTHESIS**, verify at outline.
- The schema documentation for the handshake record, wherever the column contract is stated.
  **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The capture already passes an explicit tree argument | **OBSERVED, verified first-party at HEAD** | The capture function. ⛔ **Read it before scoping** — this refutation is what makes the plan small. |
| The root-resolution helper infers the root by walking up from a base directory, and returns the worktree under a pinned working directory | **OBSERVED** | The resolver in the clone. ⭐ **This is the real defect site.** |
| Every consumer of that resolver inherits the mis-resolution | **HYPOTHESIS** | **D1's caller enumeration** — mechanical and cheap. |
| A worktree-backed plan recorded identical main and worktree commits at the boundary, with earlier rows correct | **OBSERVED, two independent instances** | ⛔ The records are machine-local and **not reachable from this clone — do not look for them.** ⭐ **The claim is settleable in the clone from the resolver's behaviour under a pinned directory** — reproduce that instead. |
| A commit recorded in the main-named field provably never reached main | **OBSERVED, verified by branch containment** | Same reachability caveat; the mechanism above supersedes the need for it. |
| The companion dirty-flag field is captured from the same tree | **HYPOTHESIS** | Same symbol; confirm while reading it. |
| The defect fires on **every** worktree-backed plan | **HYPOTHESIS** | D4's blast-radius wording depends on it. Derive from the resolver's behaviour rather than from a corpus sample. |

An asserted **absence** ("no other field is mis-resolved") is verified exactly as an asserted presence
— which is D1's job, and it is the reason D1 exists rather than going straight to the two-line fix.

## Verification

- **D2 is verified ON THE RESOLVER, not only through the capture.** A test that exercises only the
  capture path can pass for the wrong reason; the resolver is where the defect lives.
- **D3 is verified in both directions**: rejected for a worktree-backed plan, permitted for a
  genuinely-on-main plan. A one-directional assertion would break legitimate on-main runs.
- **Each test is verified to fail pre-fix.** Record the failures — ⛔ this plan's whole hazard is
  shipping a no-op with a green suite.
- **D4 reports two separate numbers** or reports itself blocked. One number is not a coverage claim.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Relation to a standing rule.** This is the same polarity as *never judge a lock stale from a
  worktree-scoped store — query the main checkout; an empty worktree-scoped read is unknown*. Here it
  is violated at a different seam: not an empty read misinterpreted, but **a worktree read mislabelled
  as a main read, with a correctly-named sibling column sitting next to it proving the mislabel.**
- **Sequencing.** No dependency. ⚠ Re-check against the outline-scope-derivation plan before running
  alongside it — both may touch phase-boundary records.
