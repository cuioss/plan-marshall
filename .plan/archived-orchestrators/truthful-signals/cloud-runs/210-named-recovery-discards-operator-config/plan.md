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

# The named recovery case discards operator config it calls "always safe" to restore

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Three workflow documents instruct the orchestrator, when a post-dispatch clean-main assertion reports
`.plan/marshal.json` dirty, to emit `Recovery: git checkout -- .plan/marshal.json` — justified in prose
by the claim that restoring it from HEAD **"is always safe."**

**The justification is a non sequitur, and the instruction is destructive.** The guard establishes only
that *the dispatched phase* did not write the file. From that, the documents conclude that *nobody*
wrote it. But the far likelier author of a dirty `marshal.json` in the main checkout is **the
operator** — and `git checkout --` destroys uncommitted, unstaged edits **irrecoverably**: no reflog
covers worktree files.

⭐ **This is the epic's flagship archetype in its most dangerous form**: a confident claim that
suppresses the caveat making it wrong, sanctioned in documentation, and wired to a destructive command.

The exposure is not theoretical. The session that reported this had **uncommitted effort-level changes
to `marshal.json`** that the operator had asked to carry into a plan; following the documented recovery
verbatim would have discarded them, and they survived only because that session parked them to a patch
file. ⚠ **And this repository reproduces the exposure independently** — a merged PR was precisely a set
of operator-set `marshal.json` effort changes, which necessarily sat uncommitted in the main checkout
before landing. Any phase-boundary assertion firing in that window would have printed the recovery
line.

## Goal

No document tells anyone that discarding an artifact is "always safe" on the strength of a guard that
cannot see who wrote it — and the recovery path for a dirty `marshal.json` requires **inspection and an
explicit disposition**, not an unconditional discard.

## Deliverables

1. **D0 — GATE: derive the population of "safe to delete / safe to revert" assertions.** Mutates
   nothing.
   *Done when:* the population is derived by **assertion shape** — a document asserting that an artifact
   is safe to discard, restore, or delete — **not by command string**, and the **population size and hit
   count are reported separately**.
   ⛔ **The three known sites are a SAMPLE, not the population.** They were found by searching one
   command form. **Do not fix the three and declare the class closed** — that is precisely the
   sample-as-population error this project keeps repeating.
2. **D1 — Replace the false inference at every site D0 finds.** The valid inference from *"phase N must
   not have touched it"* is *"**something other than phase N wrote it**"* — which mandates
   **inspection**, not restoration. The recovery must surface the diff and **require an explicit
   operator disposition before any discard**.
   *Done when:* every site instructs inspection first, and ⛔ **the word "always" does not survive in any
   justification.**
3. **D2 — Collapse the triplet.** The three blocks are near-identical copies of one contract restated
   per phase.
   *Done when:* the contract is **ONE authority** the sites reference.
   ⭐ **Per the standing rule: where a copy exists, delete the copy — do not synchronise it.** Fixing
   three copies in parallel is the defect's own recurrence shape, and there is direct evidence the
   copies already drifted: one of them contains a grammatical corruption absent from the others.
4. **D3 — Tests, each verified to FAIL pre-fix.**
   - (a) The recovery text emitted for a dirty `marshal.json` does **not** instruct an unconditional
     discard.
   - (b) D0's population derivation is **asserted non-empty and contains the known members**.
   *Done when:* both hold and each was seen red first.
   ⚠ **A test that pins only the three known sites re-creates the sample-as-population error D0 exists
   to prevent.** Assert the derivation, not the enumeration.

Four deliverables, under the split presumption.

## Out of scope

- **The originating report's primary subject.** That incident was about an agent running a destructive
  recursive delete on an uninspected tree to make a clean-tree guard pass. It belongs to the repository
  that reported it; **this plan takes only the half this project owns.**
- **The phase Enforcement blocks themselves.** They are **read** as the source of the write-prohibition
  premise, and **not modified**. Changing what a phase may write is a much larger decision than fixing
  a recovery instruction.
- **Re-deriving the archetype class independently in a sibling plan.** A sibling plan in this epic
  covers the same archetype on a different surface — a tool offering a live audit trail as
  safe-to-delete. ⭐ **D0 should hand its population results to that plan rather than either re-deriving
  the class.** ⛔ If D0 finds the two surfaces share a root, **say so and re-scope** rather than fixing
  the same thing twice in two shapes.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — § *"Named recovery
  case — `.plan/marshal.json`"*, **located by heading, not by line number**.
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — the same
  heading at **two distinct phase boundaries**.
- Further sites surfaced by D0 — **this is the whole point of D0**, so the surface is open-ended.
- `test/plan-marshall/plan-marshall/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Three sites carry the destructive recovery line under the named-recovery heading | OBSERVED | the two workflow files, **by heading** — read against repository source, not a plugin cache |
| The "always safe" wording and its inference chain appear in all three justifications | OBSERVED | the same three paragraphs — each reasons from the phase's write-prohibition to the safety of discarding |
| The three copies drifted rather than being generated | OBSERVED | one copy contains a grammatical corruption (*"a spurious write that safe to revert"*) the others lack. ⭐ Direct evidence for D2 |
| Operator config edits to `marshal.json` really do sit uncommitted in the main checkout | OBSERVED | git history for the merged effort-config change — read the commit |
| `git checkout --` on an unstaged worktree file is irrecoverable | OBSERVED | git's own semantics — no reflog covers worktree files |
| The three sites are the whole population of this assertion class | HYPOTHESIS | **D0's assertion-shape sweep.** ⛔ **Do not assume it** — a stated count states a sample |
| No automated caller executes the recovery line today | HYPOTHESIS | the consumers of the contract-violation output blocks. ⛔ **Severity rises sharply if anything consumes it programmatically** — an asserted **absence**, and the higher-risk half |
| `marshal.json` is never a phase output artifact | HYPOTHESIS | the phase Enforcement blocks the documents cite. ⛔ **Verify-first: re-read this before D1 re-words anything** — the fix depends on *why* the prohibition exists, and a refutation there re-scopes D1 |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1's replacement text is text-whose-value-is-what-a-reader-does, and this is the check that
  matters most.** Give the Step 6 verification sub-agent **only** the new recovery text, with no other
  context, and ask what it would do about a dirty `marshal.json`. The correct answer is **inspect the
  diff and ask the operator**. If it reaches for `git checkout --`, the wording failed however careful
  it looks — and the failure mode is destroyed operator work.
- ⛔ **D3(b)'s non-empty population assertion is not optional.** A sweep that matched nothing looks
  identical to a clean tree, and this epic is named for exactly that confusion.
- **D2 must be verified as a collapse, not a synchronisation.** Confirm the contract exists **once**;
  three consistent copies is a failed deliverable, because they will drift again.
- **Report the derived population size and the hit count separately.** A count of documents examined is
  a volume, not coverage.
- Documentation and test changes are expected. **Confirm the build gate's path from git evidence rather
  than assuming.**

## Notes

- ⛔ **Sequencing:** a sibling plan in this epic declares itself **exclusive against anything touching
  dispatched workflow docs**, and both files here are exactly that. **These two cannot run
  concurrently.** Neither blocks the other permanently — sequence deliberately.
- ⛔ **Do not go looking for the orchestrator spec, the cross-repository incident report, or any landing
  record.** They live under `.plan/` or in another repository, and are absent from this clone.
  Everything needed is in this file.
