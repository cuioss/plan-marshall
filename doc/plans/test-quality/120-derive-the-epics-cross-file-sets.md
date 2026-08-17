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

# Derive the epic's cross-file sets, and fail when a document disagrees

**Epic:** test-quality
**Branch prefix:** feature — a checker that does not exist today

> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief. This plan's subject is
> that file and its siblings, so read § "The collision matrix", § "The partition, and how a run
> re-derives it", and § "What the executed half left open" before starting.
>
> **No blocking dependency.** This plan reads the epic's plan documents and the test tree; it consumes
> no other plan's deliverable. It should land **early**, because every plan it checks is one a later
> run executes.

## Problem

This epic holds three cross-file sets in prose, in several documents each, with **nothing deriving
them and nothing checking them**:

* **The partition** — which plan owns which test directory. Stated in six plans' Expected surfaces,
  re-derived by hand in each plan's gating claim label, and summarised in the README's exclusion table.
* **The collision matrix** — which plans may not run concurrently. Stated in the README, and consumed
  by five plans that must not restate it.
* **The per-slice attribution** — how the whole-tree `test-module-line-budget` count distributes across
  the slices. Stated in `100`'s slice table, its claim label, and the README's residue index.

Every one of those is a hand-maintained mirror of information that exists authoritatively elsewhere:
the plans' own Expected surfaces, and the doctor's own sweep output.

**The consequence is measured, not feared.** The epic re-scoping run
(`report-authoring-02.md`) ran **eight** independent verification rounds and received **three**
automated reviews. A defect of exactly this class appeared in **every one of the eight rounds**, and
three successive structural remedies each reproduced the drift **inside their own commit**:

| Remedy | What happened |
|---|---|
| Patch the disagreeing sites individually | The next round found the site the patch missed — five rounds running |
| Declare one table authoritative, have the others point at it | A pointing file disagreed with the table in the commit that created it |
| Delete the other enumerations and complete the table | The new per-row references contradicted the table on **all seven rows**, in the commit that added them |

The reviewer reached the same conclusion independently, in three consecutive reviews: *"Derive
cross-file dependency, collision and ownership sets from their authoritative definitions."* So did the
final verification round: *"the class is not 'restatement' and it is not 'how many places' — it is that
nothing derives these sets and nothing checks them. Prose remedies cannot close a class whose cause is
the absence of a check."*

**The cost is concrete.** A partition claim that drifts sends a gating, halting derivation to halt on a
known, assigned entry — which happened four times in this epic before the entry was assigned, and once
more after a fix reached four of five sites. A collision claim that drifts licenses two plans to edit
the same file at the same time.

## Goal

The three sets are computed from the sources that define them — the plans' own Expected surfaces and
the doctor's own sweep — and a check fails when any document in the epic disagrees with the computed
answer. A drifted table becomes a red build rather than a finding a later verification round may or may
not make.

## Deliverables

**Four, and the fourth is the report.** D1 is the substrate D2 and D3 both consume, so it comes first;
D2 is the deliverable the evidence actually demands.

1. **D1 — Parse the epic's plan documents into a machine-readable model.** A script that reads every
   `doc/plans/test-quality/**/plan.md` and `doc/plans/test-quality/*.md` and extracts, per plan: its
   `## Expected surface` entries, its `## Out of scope` exclusions, and the sections that state a
   cross-file claim. **Parse, do not hand-list**: a hard-coded plan list in this script is the same
   defect the plan exists to close, one level down.
   *Done when:* the parser returns, for every plan in the epic, the set of `test/` paths its Expected
   surface claims and the set it excludes; a plan added to the epic afterwards is picked up with no
   edit to the script; and its own tests pin the parse of at least one entry of each shape the epic
   actually uses (a directory, a glob, a named file, an exclusion).

2. **D2 — Derive the three sets, and fail on disagreement.** From D1's model plus the doctor's sweep
   output, compute:
   * **the partition** — every entry under `test/` mapped to the plan whose Expected surface claims it,
     with unclaimed and multiply-claimed entries reported;
   * **the collision matrix** — every pair of plans whose Expected surfaces share a path;
   * **the per-slice attribution** — the `test-module-line-budget` findings grouped by owning plan.

   Then **compare each against what the documents say**, and **fail when they disagree**. The README's
   collision matrix, its exclusion table, `100`'s slice table and every plan's gating claim label are
   the assertions under test.
   ⛔ **The check must fail, demonstrably.** Introduce each disagreement in turn — remove a matrix row,
   change a count in `100`'s table, add a directory no plan claims — and confirm the check goes red for
   each. A checker never observed failing is not a checker.
   *Done when:* the check reports the three derived sets, fails on each of the injected disagreements
   with a message naming the document and the discrepancy, and passes against the tree as it stands —
   or, if it does not pass, **the disagreements it finds are reported rather than silenced**, because
   the epic's documents were hand-maintained for eight verification rounds and this check is the first
   thing ever to compute their answer.

3. **D3 — Run it where a drift becomes a red build.** Wire the check into the repository's own quality
   gate so it runs without anyone remembering to. Where the epic-specific half does not belong in a
   general gate, say so and state where it does belong.
   *Done when:* the check runs as part of `./pw verify` (or the gate the repository actually uses,
   named), a deliberately drifted document fails that gate, and the failure message tells the reader
   which document to fix.

4. **D4 — Report the measured deltas.** The three derived sets; every disagreement found against the
   documents as they stand, per instance; the injected-failure demonstrations for D2 and D3; and the
   collected test count before and after.
   *Done when:* the report carries all four, each with the command that produced it.

## Out of scope

* **Editing the epic's plan documents to resolve a disagreement this check finds.** Excluded because a
  run that both writes the checker and edits the documents it checks can make the check pass by moving
  either side, and there is no independent verdict left. **Report the disagreements; a follow-up
  resolves them.** This is the single most available wrong move in this plan.
* **Generalising the checker beyond this epic.** Excluded because the other epics under `doc/plans/`
  have different section conventions, and a checker that tries to serve all of them will either
  hard-code their variations — the defect this plan closes — or serve none well. A later plan may
  generalise it against measured evidence from a second epic.
* **Any `test/` refactoring.** Excluded because this plan reads the test tree and never writes it; the
  reduction plans own that surface, and `100` may be running.
* **Changing the doctor's rules or its output format.** Excluded because plan `090` owns the analyzers
  and this check is a consumer of their output. If the output shape makes the derivation impossible,
  **record it for `090`** rather than changing it here.

## Expected surface

- A new script under the repository's own tooling, placed per
  `pm-plugin-development:plugin-script-architecture` — read that skill for where a script of this kind
  belongs and follow it rather than choosing a location here
- That script's tests, placed per the same standard and per **B10**
- Whatever gate configuration D3 must touch to make the check run — named in the report, since which
  file that is depends on where D3 concludes the check belongs

⚠️ **This plan writes no file under `doc/plans/test-quality/` other than its own directory**, and
writes nothing under `test/`. Its subject is those documents; its surface is the checker.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The epic holds the partition, the collision set and the per-slice attribution in prose in several documents each, with no derivation and no check | OBSERVED | `doc/plans/test-quality/README.md` §§ "The collision matrix" and "The partition, and how a run re-derives it"; `100`'s slice table and claim labels; the six reduction plans' Expected surfaces |
| A defect of this class appeared in every one of eight verification rounds, and three structural remedies each reproduced it inside their own commit | OBSERVED | `doc/plans/test-quality/report-authoring-02.md` § Findings and § "The stop record" — git-tracked, readable from your clone |
| Every plan's `## Expected surface` is parseable into a set of `test/` paths | HYPOTHESIS — **gating for D1; the whole plan rests on it** | Read all eleven plan documents' Expected surface sections and classify each entry's shape. If some entries are prose that names no path, D1's model is partial: **say so, state which plans are unparseable and why, and scope D2 to the parseable set** rather than hand-listing the remainder |
| The doctor's sweep output carries enough to attribute a finding to a plan | HYPOTHESIS — **gating for D2's attribution half** | Run the sweep per `README.md` § "Running the plugin-doctor test-conventions scope" and read a finding row: it names the file, which is what attribution needs. If it does not, that half is **unavailable** and is reported as such |
| The documents currently agree with what the derivation computes | HYPOTHESIS — **and the plan expects it to be REFUTED** | D2's own output. Eight verification rounds found a disagreement every time by hand; a check computing them for the first time should be expected to find more, not fewer. **A run that finds zero disagreements should suspect its derivation before it congratulates the documents** |
| No plan in the epic claims this plan's Expected surface | HYPOTHESIS — asserted absence | Read `030`–`110`'s Expected surface sections. This plan's surface is repository tooling, which no reduction plan claims; confirm rather than assume |

## Verification

**Three conditions, all of which must hold.**

1. **Collected test count does not decrease**, and rises by this plan's own new tests. Record both.
2. **The check fails when it should.** Every injected disagreement in D2 and D3 is demonstrated going
   red and then restored. Record what was injected and what the failure said.
3. **The check passes for the right reason.** A green result is only meaningful if the derivation
   actually ran over a non-empty population: assert the derived sets are non-empty and report their
   sizes, so a check that silently derived nothing cannot report success.

**A fourth check, and it is the one this plan exists for: the derivation must disagree with a document
you deliberately break.** Take the README's collision matrix, delete one row, and confirm the check
names that row. Then take `100`'s slice table, change one count, and confirm the check names it. A
checker that passes both intact and broken is the vacuous-guard defect this epic has documented at
length.

**By reading — cold read, required for D2's failure messages.** The message a drift produces is the
whole value of the check: it is read by someone who did not write the drift. Dispatch the lane's
pre-PR verification sub-agent with **the failure output of the injected disagreements and no other
context** — not this plan, not the diff — and ask, for each: "which document is wrong, and what would
you change?" A message that cannot be acted on has failed, however correct its detection.

**Executable.** `./pw verify` (this plan adds Python). Plus the check itself, run over the tree as it
stands, with its output recorded.

## Notes

* **Why this plan exists is recorded rather than asserted.** `report-authoring-02.md` § "The stop
  record" carries the eight-round series, the three failed remedies, and the reviewer's three
  identical diagnoses. Read it before deciding this plan is over-engineered for its subject: the
  cheaper remedies were all tried first, and each failed the same way.
* **The expected outcome of D2 is a list of disagreements, not a green check.** The documents were
  maintained by hand through eight rounds; the first thing to compute their answer should be expected
  to find drift. Reporting it is the deliverable — resolving it is a follow-up, and Out of scope says
  why that separation matters.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked.
