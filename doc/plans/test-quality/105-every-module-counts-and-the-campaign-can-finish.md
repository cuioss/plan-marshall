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

# Every module counts, and the campaign can finish

**Epic:** test-quality
**Branch prefix:** feature — widening the budget rule makes it report modules it has never reported

> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10**, the five
> conditions in § "What a reduction run must hold", and § "The collision matrix".
>
> **And read `doc/plans/test-quality/100-module-budget-campaign/report-01.md`.** This plan is
> assembled from that report's § Residue and § What have we learned. It is git-tracked and in your
> clone. Where this plan states a figure, that report is where it came from — and every one is a
> **lead**, to be re-derived rather than trusted.
>
> **Blocking dependency: none, but sequence matters.** Plan `100` run 1 has landed; this plan closes
> what it left. Run it **before** plan `100` run 2 takes slice `040`, because D3 and D4 change what
> run 2 measures and what it must build by hand.

## Problem

The module-budget campaign's first run landed and left four things behind that **no plan in this epic
owns**. Three of them are not defects in that run's work — they are gaps in the campaign's own
apparatus, and each will recur on every one of runs 2 through 7 if it is not closed now.

**The campaign cannot reach its own goal.** Plan `100`'s stated definition of done is that
`test-module-line-budget` reaches zero. Three modules in slice `050` remain over budget, and each is a
**single class that exceeds the budget by itself** — 495, 424 and 422 class lines inside 541-, 466- and
465-line modules. Plan `100` § D2 forbids splitting a class, without qualification, so a follow-up run
under that plan cannot close them. The rule cannot reach zero while a plan forbids the only operation
that would get it there. This plan takes that decision rather than deferring it again: § D2 below
authorises the split, on stated conditions, and the reasoning is written out so a reviewer can
disagree with it.

**The rule cannot see a large and growing part of the tree it governs.**
`analyze_test_module_line_budget` iterates every `*.py` under the test root and then filters on
`_is_collected_module`, which is true only for `test_*.py` and `*_test.py`. **Every helper module is
invisible to it.** Run 1 created 66 `_{domain}_fixtures.py` helpers; the tree now holds roughly 94
non-collected modules totalling about 20,000 lines, of which about 8 are individually over the
400-line budget and none is reported. This is not a hypothetical: the campaign's one metric can be
satisfied by moving bulk out of a collected module and into a helper the metric does not read, and six
more slice splits are scheduled to do exactly that kind of move. A metric that cannot see where the
lines went is not measuring the property it names.

**The campaign's instruments are not in the repository.** Run 1 built a line-faithful splitter, a
multiset fidelity differ, a duplication detector, a banner-attribution checker and a loss classifier.
**None is committed** — they lived in a session scratch directory and died with the VM. Run 1's report
says plainly that a later run "rebuilds it from § D2 and § D4 of this report", and that "the checks
matter more than the tool": every defect run 1 shipped and then caught was caught by one of those
checks or by a reader, and **none by the build**. So the campaign's only real safety net is
hand-rebuilt from prose at the start of every run, by a runtime with no operator to notice it was
rebuilt wrong.

**And the instrument problem has already produced false figures — four of them.** Run 1's § What have
we learned, lesson 4, records the class: *a before/after pair is one claim, and the thing to verify is
that both sides were measured the same way.* Four figures in that run were wrong not in either number
but in the comparison — a duplication headline measured `def`/`class` on one side and included
assignments on the other; a banner delta took its two ends from two different scripts; a collected
count was a stale absolute; and a suite baseline was a run of a tree that no longer existed, against
which the branch read 20% slower when it was in fact faster. Six review rounds checked the arithmetic
of each number and none checked that the two ends were the same measurement. **A committed instrument
is the structural answer**; a further round of care is the remedy that has already failed four times.

## Goal

`test-module-line-budget` measures every module in the test tree rather than only the collected ones;
slice `050` reaches zero over-budget modules, so the campaign has a demonstrated path to its own
definition of done; and the checks that make a split safe — fidelity, duplication, attribution — are
committed scripts a later run invokes rather than prose a later run re-implements, each one deriving
both ends of every comparison it reports.

## Deliverables

1. **D1 — Re-derive the leftovers, and halt if they are not what this plan describes.**
   Derive, from the tree in your clone rather than from this document: the whole-tree
   `test-module-line-budget` count; the over-budget modules inside slice `050`'s ten directories; for
   each, whether its largest class exceeds the budget **alone**; the non-collected modules over budget;
   and the count of `RUF100` unused-`noqa` diagnostics. Record each with the command that produced it.
   **This is the gating deliverable.** If slice `050` holds an over-budget module whose largest class
   is *within* budget, it is an ordinary split that plan `100` already permits and this plan's D2 does
   not apply to it — **halt and report**, because the premise D2 rests on has changed. If the count of
   single-class-over-budget modules is not three, proceed against the derived set and say so; the
   number is a lead, the *shape* is the premise.
   *Done when:* every figure in § Claim labels marked **re-derive** has been recomputed and recorded
   with its command, and any shape mismatch has halted the run with the module named.

2. **D2 — Close the three modules whose one class is over the budget alone.**
   ⚠️ **This deliverable deliberately authorises what plan `100` forbids, and that is its whole
   point.** Plan `100` § D2 says splitting a class is not licensed; run 1 read that as scoped to
   classes over budget alone and honoured it, which is why these three survive. The campaign cannot
   reach zero under that reading, so this plan lifts it **for these modules only** and on conditions:
   a class is split into sibling classes along the behaviour boundaries its own tests already have —
   never in arbitrary halves, never by line count — each sibling named for the behaviour it covers,
   and **no test body, name or assertion changes**. If a class has no internal behaviour boundary to
   split on, that is a finding: record it, leave the module, and say why, rather than inventing a
   boundary to satisfy a count.
   Run 1 has already done this once and it is the precedent to follow: a 399-line class became five
   classes across two modules by extractor, with 14 tests preserved and re-run in both directory
   orders.
   *Done when:* slice `050`'s `test-module-line-budget` count is zero **or** every remaining module is
   recorded with the reason no behaviour boundary exists; the `Class::test` multiset over the affected
   directories is identical before and after, proven by D4's differ; and every affected test passes in
   default **and** reverse directory order.

3. **D3 — Make the budget rule see every module in the tree it governs.**
   `analyze_test_module_line_budget` (`marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py`)
   filters on `_is_collected_module` and therefore never reports a helper. Widen it so a non-collected
   module under the test root is measured too, and make the finding's message say which kind it is —
   a collected module's remedy is "split by behaviour cluster", which is **not** the remedy for a
   fixtures module, and a message naming an inapplicable remedy is the defect shape plan `090` exists
   to remove. Widening will make the rule report modules it has never reported, including
   `test/conftest.py` at roughly 2,300 lines; **that is the point, and the newly-reported set is
   reported, not fixed** — fixing it is a reduction slice's work, not this plan's.
   ⛔ **This edits `marketplace/bundles/**`, which every reduction plan in this epic excludes and the
   README's § "Where a recorded finding goes" assigns to plan `090`.** It is taken here because the
   gap is in the campaign's own metric, `090` has landed with no follow-up commissioned, and a metric
   that cannot see where the lines went makes every remaining campaign run unfalsifiable. **Confirm no
   open PR or in-flight branch touches that file before editing it, and halt rather than collide.**
   *Done when:* the rule reports over-budget non-collected modules; each finding's message names a
   remedy appropriate to its kind; the whole-tree count before and after is recorded with the newly
   reported modules enumerated; and a test pins both kinds.

4. **D4 — Commit the campaign's instruments, each deriving both ends itself.**
   Three checks run 1 built and did not commit, as scripts under the test tree that a later run
   invokes: a **fidelity differ** (comments, code lines and `Class::test` identities as multisets
   between two refs, reporting what is absent at each end); a **duplication detector** (module-level
   definitions identical by name and normalised body across a directory set); and a **banner
   attribution checker** (a construct sitting under a section heading that introduces a different
   section). Each takes **two refs and computes both sides itself** — never one side from an argument
   and the other from the tree, and never a figure passed in. That constraint is the deliverable's
   reason for existing: it is the structural fix for lesson 4, and a script that accepts a
   pre-computed baseline reintroduces exactly the defect it is meant to prevent.
   Each must also **state its own definition in its output** — what it counted as a definition, which
   paths it covered — because two of run 1's four false figures came from two runs of two instruments
   silently using two definitions.
   *Done when:* each script runs against two refs and prints both sides with its definition; each is
   exercised by a test that plants a known loss, a known duplicate and a known misattribution and
   confirms detection; and run 1's own headline comparisons reproduce when re-derived through them.

5. **D5 — Bring the slice's duplication to its floor, measured by D4's detector.**
   Run 1 reduced duplication substantially but reported it against a definition that changed between
   the two ends, so **the honest current figure is unknown** and D1 does not attempt it — D4's
   detector is what settles it. Once that exists, re-derive duplication across slice `050`'s
   directories at the pre-split ref and at HEAD **with one instrument**, and remove what remains that
   has a home: a definition copied into several modules whose consumers already import a shared helper
   belongs in that helper.
   Two constraints run 1 paid for: only the **dominant body** may move when a name carries more than
   one, because two bodies under one name are two behaviours; and a definition that **binds a loaded
   script module** must never be hoisted, because `load_script_module` registers under the script stem
   and a shared binding hands consumers a different module object — that mistake cost run 1 seven
   failing tests and, on an earlier plan, 173 order-dependent ones.
   *Done when:* duplication is reported at both refs by D4's detector with its definition printed, the
   remaining duplicates are each either removed or recorded with why they cannot move, and the whole
   affected suite passes in both directory orders.

6. **D6 — Leave no *live instruction* pointing at a file that does not exist.**
   Run 1 renamed 8 of its 66 sources away and repointed every reference inside its own slice, but §
   Out of scope forbade it from editing other plans' directories. References to its deleted modules
   survive elsewhere — and **most of them must be left exactly as they are**, so the scope of this
   deliverable is a distinction rather than a sweep.

   A sweep of `doc/` for test-module names that no longer resolve returns on the order of 270 hits.
   Roughly 200 sit in `report-NN.md`, `verification.md` and `gaps.md` — **dated records of what was
   true when a run executed**, which the epic's own documentation standards exempt and which it would
   be a defect to rewrite. Another large group sits in the `plan.md` of plans that have **already
   run**: `020` really did retire `test_helpers.py`, and `135` really did delete `test_lsp_facade.py`,
   so those plans naming them is a record too. A third group is deliberate: `truthful-signals/540`
   names a retired module *and supplies the `git show` command to recover it*, which is the correct
   way to cite something that no longer exists.

   What is left is the only class that misleads: a **staged, unexecuted plan** that names a deleted
   module in an instruction a future run will act on — a *Done when:* clause, an Expected-surface
   entry, a deliverable body. Run 1's report puts this at five references; the derivation above finds
   six across four staged plans, in `review-apparatus/550`, `code-intelligence-substrate/520`, and
   `truthful-signals/500` and `550`. **Both figures are leads** — derive the set, classify every hit
   into record / executed-plan / deliberate-citation / live-instruction, and act only on the last.
   *Done when:* every live instruction naming a deleted module has been repointed at the module that
   now holds that behaviour; the classification is recorded with its counts, so a reader can see what
   was deliberately left; and no `report-NN.md`, `verification.md` or `gaps.md` has been edited.


## Out of scope

* **Fixing the modules D3 newly reports.** Excluded because widening a metric and reducing what it
  then measures are two changes, and bundling them would make it impossible to tell which of the two
  moved the count. D3 reports them; a reduction slice reduces them.
* **The tree-wide `RUF100` sweep.** There are roughly 1,127 unused-`noqa` directives and every one is
  auto-fixable, so it is tempting to take them here. Excluded because the sweep would touch enough
  files to push this PR past the automated reviewers' file ceilings — which is precisely the failure
  run 1 recorded, having forfeited two of three reviewers at 309 files. Clearing directives in the
  files this plan already touches is in scope; the tree-wide sweep is recorded as a proposal with its
  measured size, and belongs in a PR whose whole content is one mechanical, tool-reproducible change.
* **Flipping `test-module-line-budget` to `severity: error`.** Excluded because it is a policy decision
  with a named owner (`090` § D7's ladder) and a cloud run has no operator to take it. D1's figures
  are what that decision will need; the decision is not this plan's.
* **Adding any third-party dependency**, including `pytest-randomly`. Excluded because it is a
  user-approval step and this run has no operator. Reverse directory order is what run 1 used to
  establish order-independence and needs no plugin.
* **Splitting a class in any module outside slice `050`.** Excluded because D2's licence is granted
  against three named, derived modules and a general licence to split classes is a change to the
  campaign's standard, which belongs in plan `100` rather than in a leftovers plan.
* **Editing any `report-NN.md`, `verification.md` or `gaps.md`.** Excluded because those are dated
  records of what was true when a run executed, and the epic's documentation standards exempt them for
  exactly that reason. A stale module name in a record is not stale — it is what the tree held at the
  time. D6 depends on this boundary rather than merely respecting it.
* **`.plan/` in any form.** Excluded because the lane forbids it and nothing here needs it.

## Expected surface

- `test/plan-marshall/plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` — D2 (541 lines, one 495-line class)
- `test/plan-marshall/manage-lessons/test_list_stalled.py` — D2 (466 lines, one 424-line class)
- `test/plan-marshall/manage-lessons/test_restore_from_plan.py` — D2 (465 lines, one 422-line class)
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — D3, the rule widening. ⛔ **`090`'s surface; see D3 for why it is taken here and what to check first**
- `test/pm-plugin-development/plugin-doctor/` — D3's tests, beside the existing rule tests
- `test/_shared/` or a sibling the tree's conventions indicate — D4's three instruments and their tests. ⚠️ **`020`'s surface, and shared with `110`**, which writes its session preflight there; `020` has landed, but check the matrix for `110` before writing
- slice `050`'s ten directories under `test/plan-marshall/` — D5, and D2's fidelity check
- `doc/plans/truthful-signals/550-*.md`, `doc/plans/code-intelligence-substrate/520-*.md` and
  `550-*.md`, `doc/plans/test-quality/050-*/plan.md` — D6's five pointers, **other epics' plan
  directories**, edited here only to repoint a dead module name
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — D6's three specimens

⚠️ **This surface crosses two other plans' territory** — `090`'s (`marketplace/bundles/**`) and two
other epics' plan directories. Look this plan up in `doc/plans/test-quality/README.md` § "The
collision matrix" before starting, confirm no open PR or in-flight branch exists for any party it
names or for the files above, and **halt and report** rather than editing a file a sibling is holding.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Three modules in slice `050` are over budget, each with one class over budget alone (495/424/422 lines in 541/466/465-line modules) | OBSERVED — **re-derive; it is D2's whole premise and D1 halts on a shape mismatch** | The three files named in § Expected surface, parsed for class extents. Derived at authoring time against the tree run 1 landed |
| `analyze_test_module_line_budget` filters on `_is_collected_module`, so no helper module is ever measured | OBSERVED | `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — `analyze_test_module_line_budget`, and `_is_collected_module` immediately above it |
| About 94 non-collected modules hold about 20,000 lines, roughly 8 of them over budget, none reported | HYPOTHESIS — **re-derive; it sizes D3** | A walk of `test/**/*.py` partitioned by `_is_collected_module`'s own predicate. Re-derive rather than trust: run 1 landed 66 new helpers and the number moves with every slice |
| Roughly 1,127 `RUF100` unused-`noqa` diagnostics exist, and `RUF100` is not in the enabled rule set | HYPOTHESIS — **it is the out-of-scope entry's justification** | `uv run ruff check test/ marketplace/ --select RUF100 --statistics`, and the `select` list in `pyproject.toml`. An asserted absence — that the rule is *not* enabled — so confirm the select list rather than inferring it from the diagnostics |
| Run 1's instruments were never committed | OBSERVED — **an asserted absence, verify it** | `doc/plans/test-quality/100-module-budget-campaign/report-01.md` § Residue, "For the next campaign run", states it outright. Confirm against the tree: if a fidelity differ or duplication detector already exists under `test/`, D4 extends it rather than creating a second one, and an unverified absence here means building something twice |
| The slice's duplication figure is currently unknown, because run 1's two ends used two definitions | OBSERVED | `report-01.md` § Findings, M45, which records the two definitions and the re-measurement. This is why D1 does **not** ask for a duplication number and D5 waits on D4 |
| About six references in **staged, unexecuted** plans name a module run 1 deleted, against ~270 hits tree-wide of which ~200 are dated records | HYPOTHESIS — **re-derive, and re-derive the CLASSIFICATION, not just the count** | Sweep `doc/` for `test_*.py` names not present under `test/`, then partition by document kind. This claim was itself wrong on first derivation: an unpartitioned sweep returns ~270 and reads as a large defect, when the great majority are `report-NN.md` / `verification.md` / `gaps.md` records the standards exempt, plus the `plan.md` of plans that have already run. `report-01.md` § Residue puts the live set at five; the partition puts it at six. **The number is not the risk — treating a record as a defect is**, and rewriting one would be the worse error |
| Plan `100` § D2 forbids splitting a class without qualification, so a follow-up run under it cannot close the three | OBSERVED — **it is the reason this plan exists rather than a run 2 of `100`** | `doc/plans/test-quality/100-module-budget-campaign/plan.md` § D2, and `report-01.md` § Contract check, which records the scoping reading run 1 applied |
| No party the collision matrix names against this plan is in flight | HYPOTHESIS — **gating and halting; check before D2 and again before D3** | `doc/plans/test-quality/README.md` § "The collision matrix", read there rather than restated here |

## Verification

**Four conditions, all of which must hold.**

1. **No test is lost or gained.** D2 and D5 both move code. The whole-tree collected count and the
   `Class::test` multiset over the affected directories must be identical before and after — measured
   by D4's differ, which computes both ends itself.
2. **Order-independence.** The affected directories pass in default **and** reverse directory order.
   D2 reorders tests within a module by construction, and run 1's own reordering is what made this
   check necessary rather than ceremonial.
3. **The rule's count moves in exactly the two ways expected.** Slice `050`'s count falls to zero
   (D2), and the whole-tree count *rises* by the newly-visible helper modules (D3). Report both
   separately: a single net figure would hide one behind the other, which is the same
   two-things-in-one-number defect lesson 4 records.
4. **Every figure in the report carries the command that produced it, and both ends came from one
   instrument.** This is the run's own application of lesson 4 to itself. A before/after pair whose
   two sides were produced by different scripts, or one of whose sides was quoted from an earlier
   run, is a defect regardless of whether the numbers look right.

**A fifth check, and it is what makes D4 real rather than decorative: each instrument must be
observed detecting.** Plant a known loss (delete a comment and a test), a known duplicate (copy a
definition into a sibling) and a known misattribution (move a construct under a foreign heading),
confirm each script reports it, remove the plant, and record the observation. A detector never seen
detecting is indistinguishable from one that returns clean unconditionally — which is the exact defect
class this epic exists to remove.

**By reading — cold read, required for D3 and D4.** Both deliverables produce text whose entire value
is what a later reader *does* with it, and neither is settled by the text being present and
well-formed. For **D3**, the risk is concrete: a fixtures module reported with a "split by behaviour
cluster" remedy sends that reader to do the wrong thing. Dispatch the lane's pre-PR verification sub-agent with **the
rule's output for one collected and one non-collected module, and no other context** — not this plan,
not the diff — and ask what it would do about each. If both answers are the same, or the helper's
answer is to split it by behaviour cluster, the message failed however complete it looks. Record the
answer verbatim and fix the wording rather than the reader.

For **D4**, the instrument's printed definition is the thing under test: a later run reads it to decide
whether two figures may be compared, which is the judgement lesson 4 records four failures of. Show the
sub-agent one instrument's output for two refs, with no other context, and ask what the numbers mean
and what it would be wrong to compare them against. If it cannot say what was counted, or believes the
figure is comparable with one produced by a different definition, the output failed.

**Executable.** `./pw verify` — the lane's build gate; this plan changes Python. Plus a whole-tree
`pytest` run before and after, and the plugin-doctor test-conventions sweep at both ends.

## Notes

* **Why these six are one plan.** Every one is a leftover of plan `100` run 1 that no other plan owns,
  and D2, D4 and D5 are mutually dependent: D2's fidelity proof needs D4's differ, and D5's figure is
  meaningless without it. Splitting them would mean building the instrument in one plan and first
  using it in another, with nothing exercising it in between.
* **Why the class-split licence is granted here rather than in `100`.** Amending `100` would change the
  standard for six unrun slices on the evidence of three modules. Granting it against three derived,
  named modules keeps the blast radius to what has actually been examined. If runs 2 through 7 hit the
  same wall repeatedly, *that* is the evidence for amending the standard, and it will be a better
  argument than this one.
* **The review-coverage problem is real and is not solved here.** Run 1's PR reached 309 files and both
  automated reviewers refused it on file-count ceilings — 100 and 300 — so two thirds of the
  repository's review capacity was structurally unreachable. This plan keeps its own diff small enough
  to stay under both, which is why the `RUF100` sweep is out of scope. **Record a proposal** for how a
  slice should be carved into pull requests; do not take the decision, and do not restructure the
  lane's one-plan-one-PR cycle to fit — that is the contract's, and the run may not amend the contract
  that governs it.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**. Every artifact cited here is git-tracked or is produced by
  a command this plan states.
