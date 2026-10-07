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
(`report-authoring-02.md`) ran **nine** independent verification rounds and received **two**
substantive automated reviews (`coderabbitai` filed findings on two heads; two further review records
from it are reply-only, and the other two reviewers filed nothing of this kind). Every figure here is a
**lead** — re-derive it from that report's series table rather than trusting it. A defect of exactly
this class appeared in **every one of the nine rounds**, and three successive structural remedies each
failed:

| Remedy | What happened |
|---|---|
| Patch the disagreeing sites individually | The next round found the site the patch missed — five rounds running |
| Declare one table authoritative, have the others point at it | A pointing file disagreed with the table **in the commit that created it** |
| Delete the other enumerations and complete the table | The new per-row references contradicted the table on **all seven rows**, **in the commit that added them** |

Only the last two failed inside their own commit; the first failed by leaving a site behind. The
distinction matters: it is why "look harder next round" was tried first and is not the remedy here.

The reviewer reached the same conclusion independently, in both of its substantive reviews: *"Derive
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

1. **D1 — Parse what is declarative, and classify what is not.** A script that reads every plan
   document under `doc/plans/test-quality/` — distinguishing a **plan** from a **record** by the
   presence of the first-instruction block, not by a hand-kept list — and extracts, per plan, the
   `test/` paths its `## Expected surface` claims and its `## Out of scope` excludes. **Parse, do not
   hand-list**: a hard-coded plan list in this script is the same defect this plan exists to close, one
   level down.

   ⛔ **Not every Expected surface is declarative, and the derivation must say so rather than guess.**
   Measured at authoring time, at least four are not: `100`'s is *derived at run time* (the union of six
   other plans' surfaces intersected with a doctor predicate), `020`'s names call sites in prose,
   `090`'s has **conditional** membership ("only where a D1 production change requires its own test"),
   and **this plan's own** names a location by standard rather than by path. Every one of those figures
   is a lead — **re-derive the classification**.

   Each plan therefore lands in exactly one of three classes: **declarative** (paths a parser resolves),
   **derived** (its surface is a function of other plans' — `100`), or **prose** (neither). The first
   two are usable; the third is reported.
   *Done when:* every plan document carries exactly one class with the evidence for it; a plan added
   afterwards is picked up with no edit to the script; the tests pin the parse of each entry shape the
   epic actually uses (a directory, a glob, a named file, a rename arrow, an exclusion, a conditional);
   and **a plan whose class cannot be determined halts the run** rather than defaulting to any class.

2. **D2 — Derive the three sets, and fail on disagreement.** From D1's model plus the doctor's sweep
   output, compute:
   * **the partition** — every entry under `test/` mapped to the plan whose Expected surface claims it,
     with unclaimed and multiply-claimed entries reported;
   * **the collision matrix** — every pair of plans whose Expected surfaces share a path;
   * **the per-slice attribution** — the `test-module-line-budget` findings grouped by owning plan.

   ⛔ **"Unclaimed" and "claimed by a plan I cannot parse" are different verdicts and must never be
   merged.** A `test/` entry claimed only by a **prose**-class plan is reported as *coverage the
   derivation cannot see*, never as a partition defect — otherwise the check manufactures false
   disagreements out of its own parser's limits, and this plan's own claim labels pre-commit a run to
   believing them. The three-class model from D1 is what makes that distinction expressible.

   Then **compare each derived set against what the documents say**, and report every disagreement with
   the document, the line, and both values. The README's collision matrix, its exclusion table, `100`'s
   slice table and every plan's gating claim label are the assertions under test.
   ⛔ **The check must be observed failing.** Introduce each disagreement in turn — remove a matrix row,
   change a count in `100`'s table, add a directory no plan claims — and confirm it reports each. A
   checker never observed failing is not a checker.
   *Done when:* the check reports the three derived sets with their sizes, distinguishes the three
   verdicts (agree / disagree / not-derivable), reports each injected disagreement with a message
   naming the document and both values, and **states every disagreement it finds against the tree as it
   stands rather than silencing it** — the epic's documents were hand-maintained through nine
   verification rounds and this is the first thing ever to compute their answer, so finding some is the
   expected outcome and is not a failure of this deliverable.

3. **D3 — Run it where a *new* drift becomes a red build, without going red on the drift that is
   already there.** Wire the check into the repository's own quality gate so it runs without anyone
   remembering to. Where the epic-specific half does not belong in a general gate, say so and state
   where it does belong.

   ⛔ **D2, D3 and Out of scope deadlock unless the gate is baselined, so it is baselined.** D2 expects
   to find real disagreements; Out of scope forbids this run from resolving them; a gate that fails on
   any disagreement therefore lands `./pw verify` red with no move available that this plan permits.
   The resolution is the one plan `010` already shipped for its doctor rules — **land the check
   non-blocking for what exists, blocking for what is added**:
   * D2 writes the disagreements it finds against the tree as it stands into a **baseline file
     committed in this plan's own directory** (`doc/plans/{epic}/{this-plan}/`), one entry per
     disagreement, each carrying the document, the line and both values.
   * The gate **fails only on a disagreement absent from the baseline**, and reports baselined ones as
     warnings so they stay visible rather than becoming invisible.
   * A baseline entry the derivation **no longer reproduces** is reported as stale — that is a
     document having been fixed, and the row is then removable.

   ⚠️ **The baseline is not the hand-maintained artifact this plan exists to abolish, and the
   distinction is load-bearing.** It defines nothing the check needs: every entry is re-derived from
   the sources on every run, and the baseline only decides whether an already-derived disagreement
   fails the build or warns. A hand-edited entry that the derivation does not produce is reported as
   stale, so the file cannot silently acquire authority over the answer.
   *Done when:* the check runs as part of `./pw verify` (or the gate the repository actually uses,
   named); the gate is **green on the tree as it stands** with the baselined disagreements reported as
   warnings; a **newly** drifted document fails that gate; a baseline entry removed by hand while its
   disagreement persists also fails it; and the failure message tells the reader which document to fix.

4. **D4 — Report the measured deltas.** The three derived sets; every disagreement found against the
   documents as they stand, per instance; the injected-failure demonstrations for D2 and D3; and the
   collected test count before and after.
   *Done when:* the report carries all four, each with the command that produced it.

## Out of scope

* **Editing the epic's plan documents to resolve a disagreement this check finds.** Excluded because a
  run that both writes the checker and edits the documents it checks can make the check pass by moving
  either side, and there is no independent verdict left. **Report the disagreements — in the report and
  in D3's baseline, which is the sanctioned channel for recording them — and let a follow-up resolve
  them.** This is the single most available wrong move in this plan.

  ⚠️ **One narrow write is required rather than excluded, and it is not this.** Registering this
  plan's own new test location in the README's partition (Expected surface below) adds a row for a path
  this run *creates*; it resolves no disagreement and changes no existing row. Without it, every
  reduction plan's gating derivation halts on an entry no plan claims — the epic's most-repeated
  defect, hit four times already. Adding that row is in scope; touching any other line of any epic
  document is not.
* **Generalising the checker beyond this epic.** Excluded because the other epics under `doc/plans/`
  have different section conventions, and a checker that tries to serve all of them will either
  hard-code their variations — the defect this plan closes — or serve none well. A later plan may
  generalise it against measured evidence from a second epic.
* **Any `test/` refactoring.** Excluded because the reduction plans own that surface and `100` may be
  running concurrently. This plan reads the existing test tree and **modifies no file in it** — it adds
  its own new test module (Expected surface), which is an addition to an unclaimed path, not a change
  to a claimed one.
* **Changing the doctor's rules or its output format.** Excluded because plan `090` owns the analyzers
  and this check is a consumer of their output. If the output shape makes the derivation impossible,
  **record it for `090`** rather than changing it here.

## Expected surface

- A new script under the repository's own tooling, placed per
  `pm-plugin-development:plugin-script-architecture` — read that skill for where a script of this kind
  belongs and follow it rather than choosing a location here
- **That script's tests, under `test/`** — `pyproject.toml` sets `testpaths = ["test"]` and
  `python_files = ["test_*.py"]`, so a test module outside that tree is never collected and the tests
  would not exist as far as the suite is concerned. Mirror the script's own bundle/skill path within
  `test/`, per **B10**
- D3's baseline file, in this plan's own directory
- Whatever gate configuration D3 must touch to make the check run — named in the report, since which
  file that is depends on where D3 concludes the check belongs
- **One row** in `README.md`'s partition-exclusion table registering the test location above

⚠️ **This plan writes no file under `doc/plans/test-quality/` other than its own directory and that
single README row.** Its subject is those documents; its surface is the checker.

⛔ **The test location must be registered in the partition, or this plan breaks six other plans.** An
earlier draft of this section forbade writing under `test/` at all, which contradicts `testpaths` above
— the tests have nowhere else to go. But a new entry under `test/` that no plan claims is precisely
what `030`–`080`'s gating derivation halts on, and this epic has already burned four runs on exactly
that. So:
* Prefer a location **inside a directory the partition already assigns**, which needs no README change
  at all. Check first: `README.md` § "The partition, and how a run re-derives it" lists what is claimed.
* Only if the script-architecture standard forces a **new** top-level or new `test/plan-marshall/*`
  entry, add one row to that section's exclusion table naming the new path and this plan as its owner.
  Change no existing row.
* Either way, **state in the report which of the two happened**, with the path.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The epic holds the partition, the collision set and the per-slice attribution in prose in several documents each, with no derivation and no check | OBSERVED | `doc/plans/test-quality/README.md` §§ "The collision matrix" and "The partition, and how a run re-derives it"; `100`'s slice table and claim labels; the six reduction plans' Expected surfaces |
| A defect of this class appeared in every one of **nine** verification rounds, and three structural remedies failed — the last two by contradicting themselves inside their own commit | OBSERVED | `doc/plans/test-quality/report-authoring-02.md` § Findings and § "The stop record" — git-tracked, readable from your clone |
| **Not** every plan's `## Expected surface` is parseable into a set of `test/` paths — at least four are declarative-with-prose, derived, conditional, or path-free | OBSERVED — **gating for D1** | Read every plan document's Expected surface and classify each entry's shape; `100`'s is derived from other plans', `020`'s names call sites in prose, `090`'s is conditional, this plan's names a location by standard. **Re-derive the classification** — the count is a lead. D1's three-class model exists because of this, and D2 must report a prose-class plan's paths as *not derivable*, never as unclaimed |
| The test suite collects only under `test/`, so this plan's own tests must live there | OBSERVED | `pyproject.toml` § `[tool.pytest.ini_options]` — `testpaths = ["test"]`, `python_files = ["test_*.py"]`. Re-read it; a change to either makes this plan's Expected surface wrong |
| A new entry under `test/` that no plan's Expected surface claims halts `030`–`080`'s gating derivation | OBSERVED | `README.md` § "The partition, and how a run re-derives it" step 3 — "An entry claimed by no plan is the dangerous case"; and its record of four consecutive runs halting on `test/pm-code-intelligence/` |
| The doctor's sweep output carries enough to attribute a finding to a plan | HYPOTHESIS — **gating for D2's attribution half** | Run the sweep per `README.md` § "Running the plugin-doctor test-conventions scope" and read a finding row: it names the file, which is what attribution needs. If it does not, that half is **unavailable** and is reported as such |
| The documents currently agree with what the derivation computes | HYPOTHESIS — **and the plan expects it to be REFUTED** | D2's own output. Eight verification rounds found a disagreement every time by hand; a check computing them for the first time should be expected to find more, not fewer. **A run that finds zero disagreements should suspect its derivation before it congratulates the documents** |
| No plan in the epic claims this plan's Expected surface | HYPOTHESIS — asserted absence, **and the `test/` half is the risky half** | Read **every other plan document in the epic**, `010` and `020` included — not `030`–`110` only, which an earlier draft said and which omits the two plans that own `test/conftest.py`, `test/_shared/**` and the doctor's `rule*` modules. The gate config is repository tooling no plan claims; the **script** is not automatically safe — see the `120`↔`090` row in § "The collision matrix", which exists because `marketplace/bundles/**` is `090`'s alone. The **test module** is different: it lands under `test/`, where `030`–`080` partition everything, so its chosen path must be checked against all six before it is written — a collision there is a two-plans-one-file defect, not a bookkeeping one. Confirm rather than assume |

## Verification

**Three conditions, all of which must hold.**

1. **Collected test count does not decrease**, and rises by this plan's own new tests. Record both.
2. **The check fails when it should.** Every injected disagreement in D2 and D3 is demonstrated going
   red and then restored. Record what was injected and what the failure said.
3. **The check passes for the right reason.** A green result is only meaningful if the derivation
   actually ran over a non-empty population: assert the derived sets are non-empty and report their
   sizes, so a check that silently derived nothing cannot report success.

   ⚠️ **Green does not mean "no disagreements" here, and the report must not say it does.** Per D3 the
   gate is green on the tree as it stands *because the disagreements found are baselined*, not because
   there are none. Report the baselined count alongside the green result; a run that reports "the check
   passes" without it has published the opposite of what it measured.

**A fourth check, and it is the one this plan exists for: the derivation must disagree with a document
you deliberately break.** Take the README's collision matrix, delete one row, and confirm the check
names that row. Then take `100`'s slice table, change one count, and confirm the check names it. A
checker that passes both intact and broken is the vacuous-guard defect this epic has documented at
length. Both injections are **new** disagreements, absent from D3's baseline by construction, so both
must turn the gate red rather than merely warn — that coupling is what proves the baseline suppresses
only what it was built from.

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
  maintained by hand through nine rounds; the first thing to compute their answer should be expected
  to find drift. Reporting it is the deliverable — resolving it is a follow-up, and Out of scope says
  why that separation matters.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked.
