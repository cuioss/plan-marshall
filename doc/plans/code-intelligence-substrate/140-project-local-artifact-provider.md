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

# The plugin-development domain owns the project-local artifact tree

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

The project-local artifact tree is attributed **inconsistently**: one `.claude/` subtree resolves to
a module, while its sibling subtree — the same kind of artifact — resolves to `module: null`. One
tree, two answers.

⭐⭐ **And the consequence is a measured token cost, not untidiness.** The structured index **cannot
answer for these paths at all**. A caller obeying the standing *structured-queries-first* rule asks
the index, gets nothing, and **falls back to a whole-tree scan** — the expensive path the rule exists
to avoid.

⛔ **The word that matters is SILENTLY.** The caller cannot distinguish *"the index looked and there
is nothing there"* from *"the index does not cover this path"*, so the fallback reads as a correct
answer to a completed query rather than as a coverage gap. ⭐ **This epic's flagship archetype landing
on the epic's own flagship rule** — and every query against an unclaimed path pays whole-tree prices,
on every plan, forever.

⇒ Note the direction: closing this is **the good kind of saving** — bytes that buy nothing — not an
examination cut.

The plugin-development bundle is the one that understands Claude Code plugin artifacts. It already
implements bundle-based module discovery and owns the plugin doctor, the marketplace inventory, and
the plugin architecture standards. It should hold this claim.

## Goal

Every path under every project-local artifact subtree resolves to the same module through the
attribution seam; a path under none of them reports **unclaimed** rather than falling through; and
the resolver can say *"not covered"* distinctly from *"covered, no matches"*, so the next uncovered
path does not reproduce this silently.

## Deliverables

1. **D1 — project-local artifact claim** through the attribution seam, covering the surface
   **uniformly**.
   ⛔ **Derive the set of subtrees from the filesystem — do not enumerate it from this plan.** Any
   list here is what one reader saw; the population is what exists.
   *Done when:* every discovered subtree is claimed, and the claim is registered through the seam
   rather than hard-coded.
2. **D2 — the ownership decision, made explicitly and recorded.**
   The existing attribution names one module as the operator-confirmed owner. This plan **may** move
   it, but ⛔ **the move is a decision, not a refactor side effect** — record it, and surface it if
   two readings conflict.
   ⚠ The distinction that matters: these artifacts are *authored in* the meta-project and *understood
   by* the plugin-development domain. **Owner = who understands the content**, which is why the seam
   exists at all.
   *Done when:* the decision and its reasoning are written where a future reader will find them.
3. **D3 — consistency verification across the whole tree.**
   After the claim lands, every path under every subtree resolves to the same module, and a path
   under none reports unclaimed rather than hitting a stale prefix.
   ⭐ **Derive this check from the filesystem population, not from a fixed list of probe paths.**
   ⛔ **N probes of a pure prefix function is ONE assertion repeated N times** — the check that bites
   walks the actual tree and **publishes the population size it walked**.
   *Done when:* the check enumerates rather than samples, and publishes its count.
4. **D4 — the resolver distinguishes "not covered" from "covered, no matches".**
   Claiming the path is **necessary but not sufficient**: without this, the next uncovered path
   reproduces the silent fallback.
   ⚠ **A coverage contract for exactly this already shipped elsewhere in this epic** — a content
   search returning scanned/unreadable/truncated/elided counts. ⛔ **Reuse that contract rather than
   inventing a second one.**
   *Done when:* an uncovered path produces a distinct, named result that a caller can branch on.
5. **D5 — documentation.** The ownership contract in the plugin-development bundle, and the
   project-local attribution row in `doc/concepts/code-intelligence.adoc`.

Five deliverables — at the split guard's edge; evaluate before implementing.

## Out of scope

- **Editing the architecture core.** ✅ **Settled: the hard-coded prefix map has already been
  retired** by the plan that shipped the attribution seam — verified first-party, the core carries no
  such constant. ⛔ **Do not budget a core edit.** The escape clause therefore binds *harder*, not
  softer: **if this plan finds itself editing core for any reason, that is a signal the seam did not
  cover this case — loop back and report it** rather than patching core here.
- **Fixing a consuming project's own inventory data.** Excluded — repo-side, not a bundle item.
- **Changing how these paths are classified by the bookkeeping-prefix logic.** Excluded because a
  sibling plan is replacing that classification with a lookup. Different map, different files, **not
  a duplicate** — but ⚠ **re-check the interaction at outline**, since that plan changes downstream
  classification of the same paths.

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/` — the extension manifest
  and its extension module. **OBSERVED.**
- `doc/concepts/code-intelligence.adoc` — the project-local attribution row. **OBSERVED.**
- `test/pm-plugin-development/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| One project-local subtree resolves to a module and its sibling resolves to null | **OBSERVED** | ⛔ **Re-derive in the clone** by resolving a path from each subtree. This is the plan's founding premise and it is cheap to check. |
| Project-local dotfile trees are never inventoried, so the attribution path is the sole resolution route for them | **OBSERVED** | The query handler that documents the exclusion. Read it. |
| The hard-coded prefix map has already been retired from core | **OBSERVED, verified first-party** | ⛔ **Re-verify**: search core for any project-local prefix constant. If one is present, the seam is incomplete and this plan's shape changes. |
| The plugin-development bundle already implements module discovery | **OBSERVED** | The module-discovery standard's list of existing implementors, plus the bundle's manifest. |
| A third artifact subtree exists in this repository | **HYPOTHESIS — an asserted presence AND an asserted absence, verify like both** | ⛔ **List the project-local directory at outline.** An unverified absence produces either a dead claim or an uncovered tree. |
| Moving the ownership breaks no consumer | **HYPOTHESIS** | ⛔ **Enumerate consumers that branch on the returned module name for these paths.** ⚠ The artifacts' **tests live under a different module's test tree**, so a move may split an artifact from its tests across two modules — **decide whether that is acceptable before moving; it may be exactly why the original owner was chosen.** |
| The index-cannot-answer consequence and its whole-tree fallback | **OBSERVED (reported first-party on a real run)** | Reproduce in the clone: ask the index for a project-local path and observe what comes back. |

An asserted **absence** is verified exactly as an asserted presence and is the higher-risk half — two
claims above are absences, and both are cheap to settle in the clone.

## Verification

- **D3 is verified by enumeration, and the enumeration is the deliverable.** A check that probes a
  fixed list of paths passes against a partially-claimed tree. Walk the tree, publish the count.
- **D4 is verified by a negative control**: an uncovered path must produce a *different* result from
  a covered path with no matches. Assert both; the pair is the point.
- **D2's decision is verified by a cold read** — hand the recorded ownership rationale to the pre-PR
  verification sub-agent and confirm it can state who owns the tree and why. If it cannot, the record
  failed even if the code is right.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Dependency.** The attribution seam must exist; it has landed, but confirm in the clone rather
  than assuming.
- **Serialization.** Several plans touch the plugin-development bundle. ⛔ Do not run this
  concurrently with them without a **file-set** check first — the bundle-level collision may be
  avoidable at file level, but the check comes first.
