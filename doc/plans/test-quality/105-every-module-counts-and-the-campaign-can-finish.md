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

**The rule's count has three permanent residents, and nobody intends to act on them.** Plan `100`'s
stated definition of done is that `test-module-line-budget` reaches zero. Three modules in slice `050`
remain over budget, each a **single class under 500 lines** — 495, 424 and 422 class lines inside 541-,
466- and 465-line modules. Plan `100` § D2 forbids splitting a class, so a follow-up run under that
plan cannot close them; and the campaign's subject was *excessively large files* — the slice it split
held an 8,705-line module — which a 466-line module holding one 424-line class plainly is not. So the
right answer is neither to split them nor to leave them flagged: **it is to decide, and to make the
rule express the decision.** A count that can never reach zero is one every future run must
re-litigate, and a standard whose exceptions live only in a plan's prose is one the next reader will
not find.

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

`test-module-line-budget` measures every module in the test tree rather than only the collected ones,
and stops flagging the one shape the campaign has decided not to act on — so its count is something a
run can drive to zero honestly rather than a number with three permanent residents. And the checks
that make a split safe — fidelity, duplication, attribution — are committed scripts a later run
invokes rather than prose a later run re-implements, each one deriving both ends of every comparison
it reports. And the tree stops carrying ~691 lint suppressions that suppress nothing, without losing
the ~108 that record a judgement the current rule set does not ask about.

## Deliverables

1. **D1 — Re-derive the leftovers, and halt if they are not what this plan describes.**
   Derive, from the tree in your clone rather than from this document: the whole-tree
   `test-module-line-budget` count; the over-budget modules inside slice `050`'s ten directories; for
   each, whether its largest class exceeds the budget **alone**; the non-collected modules over budget;
   and the `RUF100` population, split into its three kinds (see § D7). Record each with the
   command that produced it — and for `RUF100` use `--extend-select`, never `--select`: `--select`
   REPLACES the configured rule set, which makes every directive look non-enabled and inflates the
   count by about 60%. That error was made while authoring this plan and is recorded here so the run
   does not repeat it.
   **This is the gating deliverable.** D2 rests on a shape, not a count: an over-budget module whose
   whole content is one class that is itself under the 500-line ceiling. If a module in slice `050` is
   over budget for any other reason — two classes, or one class above the ceiling — **D2 does not apply
   to it**; it is an ordinary split, plan `100` already permits it, and this run reports it rather than
   silently widening the exemption to cover it. If no module has D2's shape, **halt and report**: the
   exemption would then be a rule change with no instance, which is a different proposal and needs a
   different argument.
   *Done when:* every figure in § Claim labels marked **re-derive** has been recomputed and recorded
   with its command, and any shape mismatch has halted the run with the module named.

2. **D2 — Stop the campaign chasing a shape it has decided to keep.**
   Run 1 left three modules over budget, each a **single class under 500 lines** — 495, 424 and 422
   class lines inside 541-, 466- and 465-line modules. The campaign's subject was **excessively large
   files**: the slice it split contained an 8,705-line module and a ~1,750-line one. A 466-line module
   holding one 424-line class is not that, and splitting a coherent test class to move a module from
   466 lines to two of ~230 buys nothing a reader wants.
   ⚠️ **So the decision is to keep them, and the deliverable is to make the rule say so.** Leaving
   them flagged would be worse than either alternative: `test-module-line-budget` would carry three
   findings nobody intends to act on, the campaign's own definition of done ("the count reaches zero")
   would be permanently unreachable, and every future run would re-litigate them. Add a **bounded,
   documented exemption**: a collected module whose content is a single class, where that class is
   under a stated ceiling, is not flagged. State the ceiling and the reasoning in the standard the rule
   cites, so the exemption is a decision a reader can find and disagree with rather than a silent
   special case in the analyzer.
   The ceiling is **500 lines**, and it is a decision rather than a derivation — record it as one.
   ⛔ **The ceiling is measured on the CLASS, not on the module, and all three modules are kept.**
   That distinction is the whole of the exemption's arithmetic and it is stated because getting it
   backwards silently drops one of the three:

   | Module | Module lines | Its one class | Exempt? |
   |---|---:|---:|---|
   | `plan-retrospective/test_analyze_logs_dispatch_boundary_context_load_columns.py` | 541 | **495** | yes |
   | `manage-lessons/test_list_stalled.py` | 466 | **424** | yes |
   | `manage-lessons/test_restore_from_plan.py` | 465 | **422** | yes |

   A module measured on its own lines would exclude the first at 541, which is **not** the intent: the
   module exceeds its class only by the header, imports and a banner, and none of those is content a
   split could redistribute. The class is the unit a split would have to divide, so the class is the
   unit the ceiling governs.
   ⛔ **The exemption must be narrow, and the narrowness is the whole safety property.** It applies
   only where the module is *one* class: a 900-line module holding two 450-line classes is an ordinary
   split and must stay flagged. Verify that with a fixture for each shape before shipping.
   *Done when:* **all three** modules are unchanged on disk and none is flagged; a module of two
   under-ceiling classes and a module of one over-ceiling class are both still flagged, each pinned by
   a test; and the standard states the ceiling, that it is measured on the class, and the reasoning.

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


7. **D7 — Clear the suppressions whose cause is gone, and refuse to clear the ones whose cause is not.**
   The tree carries about **1,130** `noqa` directives; about **691** suppress nothing. They are not one
   population and a bare `ruff --fix` is wrong for a third of them:

   | Kind | ~Count | What it is | Disposition |
   |---|---:|---|---|
   | Shadowed | 364 | a line-level `# noqa: E402` in a file whose header already says `# ruff: noqa: I001, E402` | **delete the line-level one**; the file header already covers it |
   | Stale | 219 | rule enabled, nothing shadowing, code no longer triggers it | **delete** |
   | Non-enabled | 108 | names a rule this project does not run — `S603`, `BLE001`, `PLC0415`, `ANN*`, `D*` | ⛔ **do not delete** — see below |

   ⛔ **The third kind is why this is not `--fix`.** `# noqa: S603` marks a subprocess call the author
   judged deliberate; `# noqa: BLE001` marks an intentional broad `except`. Those families are absent
   from `select`, so the directives suppress nothing today and `--fix` deletes every one of them —
   discarding the annotation that would matter the moment anyone enables `S` or `BLE`. Convert each to
   a plain comment that states the intent in words (`# deliberate: fixed argv, no shell`), so the
   judgement survives the rule set it was written against. Where the intent cannot be recovered from
   the code, **leave the directive and record it** rather than guess.
   ⚠️ **Measure with `--extend-select RUF100`, never `--select RUF100`** — the latter replaces the
   configured rule set and inflates the count by about 60%. D1 states this; it is repeated here because
   this is the deliverable that acts on the number.
   ⚠️ **This deliverable alone touches ~391 files and will push the PR past both automated reviewers'
   ceilings** (100 and 300 files), forfeiting the review run 1 already lost once. It is taken anyway,
   by decision, because the alternative is carrying it indefinitely. Land it as **its own commit**, so
   a reviewer can verify it by re-running the tool over that commit rather than by reading 391 diffs,
   and say so in the PR body.
   ⛔ **Do not touch the ~148 live E402 suppressions**, which sit on imports that genuinely follow a
   `sys.path` manipulation. Those have a cause; D7 removes annotations whose cause is gone, and
   removing a live one turns a green build red.
   *Done when:* `ruff check --extend-select RUF100` reports zero over the two kinds this deliverable
   clears; every non-enabled directive is either converted to an intent comment or recorded with why it
   was left; `./pw verify` is green; and the count is reported by kind, not as one number.


## Out of scope

* **Fixing the modules D3 newly reports.** Excluded because widening a metric and reducing what it
  then measures are two changes, and bundling them would make it impossible to tell which of the two
  moved the count. D3 reports them; a reduction slice reduces them.
* **Flipping `test-module-line-budget` to `severity: error`.** Excluded because it is a policy decision
  with a named owner (`090` § D7's ladder) and a cloud run has no operator to take it. D1's figures
  are what that decision will need; the decision is not this plan's.
* **Adding any third-party dependency**, including `pytest-randomly`. Excluded because it is a
  user-approval step and this run has no operator. Reverse directory order is what run 1 used to
  establish order-independence and needs no plugin.
* **Widening the exemption beyond one-class modules, or raising the 400-line budget itself.**
  Excluded because D2's exemption is deliberately the narrowest shape that covers the observed cases —
  a module that is *one* class, under a stated ceiling. Changing the budget, or exempting a module
  with two classes, is a change to the campaign's standard for six unrun slices on the evidence of
  three modules, and belongs in plan `100` rather than in a leftovers plan.
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
- **~391 files across `test/` and `marketplace/bundles/`** — D7, one line removed or reworded per dead
  directive. ⛔ **This is by far the widest surface in the plan and it reaches deep into `090`'s tree.**
  It is mechanical and tool-reproducible, but it is not small: check the matrix for `090` immediately
  before running D7, not only at the start, and take D7 **last** so a collision costs only that
  commit

⚠️ **This surface crosses two other plans' territory** — `090`'s (`marketplace/bundles/**`, both at
one analyzer for D3 and across ~250 files for D7) and two other epics' plan directories. Look this plan up in `doc/plans/test-quality/README.md` § "The
collision matrix" before starting, confirm no open PR or in-flight branch exists for any party it
names or for the files above, and **halt and report** rather than editing a file a sibling is holding.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Three modules in slice `050` are over budget, each with one class over budget alone (495/424/422 lines in 541/466/465-line modules) | OBSERVED — **re-derive; it is D2's whole premise and D1 halts on a shape mismatch** | The three files named in § Expected surface, parsed for class extents. Derived at authoring time against the tree run 1 landed |
| `analyze_test_module_line_budget` filters on `_is_collected_module`, so no helper module is ever measured | OBSERVED | `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — `analyze_test_module_line_budget`, and `_is_collected_module` immediately above it |
| About 94 non-collected modules hold about 20,000 lines, roughly 8 of them over budget, none reported | HYPOTHESIS — **re-derive; it sizes D3** | A walk of `test/**/*.py` partitioned by `_is_collected_module`'s own predicate. Re-derive rather than trust: run 1 landed 66 new helpers and the number moves with every slice |
| The `RUF100` population is ~691 across ~391 files, in three kinds (~364 shadowed, ~219 stale, ~108 non-enabled) | OBSERVED — **and the first derivation of it was wrong by 63%** | `uv run ruff check test/ marketplace/ --extend-select RUF100 --output-format json`, partitioned on whether the message says `unused:` or `non-enabled:`, and for the shadowed kind by checking each file's first 12 lines for a `# ruff: noqa:` header naming the same code. ⚠️ The figure first recorded here was **1,127**, from `--select RUF100`, which REPLACES the configured rule set so that every directive reports as non-enabled. Same tool, same tree, two instruments, a 436-diagnostic gap — lesson 4's fifth instance, found while authoring the plan that cites lesson 4 |
| Run 1's instruments were never committed | OBSERVED — **an asserted absence, verify it** | `doc/plans/test-quality/100-module-budget-campaign/report-01.md` § Residue, "For the next campaign run", states it outright. Confirm against the tree: if a fidelity differ or duplication detector already exists under `test/`, D4 extends it rather than creating a second one, and an unverified absence here means building something twice |
| The slice's duplication figure is currently unknown, because run 1's two ends used two definitions | OBSERVED | `report-01.md` § Findings, M45, which records the two definitions and the re-measurement. This is why D1 does **not** ask for a duplication number and D5 waits on D4 |
| About six references in **staged, unexecuted** plans name a module run 1 deleted, against ~270 hits tree-wide of which ~200 are dated records | HYPOTHESIS — **re-derive, and re-derive the CLASSIFICATION, not just the count** | Sweep `doc/` for `test_*.py` names not present under `test/`, then partition by document kind. This claim was itself wrong on first derivation: an unpartitioned sweep returns ~270 and reads as a large defect, when the great majority are `report-NN.md` / `verification.md` / `gaps.md` records the standards exempt, plus the `plan.md` of plans that have already run. `report-01.md` § Residue puts the live set at five; the partition puts it at six. **The number is not the risk — treating a record as a defect is**, and rewriting one would be the worse error |
| Plan `100` § D2 forbids splitting a class, so a follow-up run under it cannot close the three — and the campaign's subject was excessively large files, which these are not | OBSERVED for the first half, **a DECISION for the second** | `doc/plans/test-quality/100-module-budget-campaign/plan.md` § D2 and `report-01.md` § Contract check confirm the prohibition and the reading run 1 applied. That these three should be *kept* rather than split is **not derivable from any artifact** — it is an operator decision taken while authoring this plan, on the reasoning that the slice's original subject was an 8,705-line module and a 466-line one is a different thing. It is recorded as a decision so a reviewer can reject it; if rejected, D2 inverts to a split and D1's gate is unchanged |
| No party the collision matrix names against this plan is in flight | HYPOTHESIS — **gating and halting; check before D2 and again before D3** | `doc/plans/test-quality/README.md` § "The collision matrix", read there rather than restated here |

## Verification

**Four conditions, all of which must hold.**

1. **No test is lost or gained.** D5 moves code. The whole-tree collected count and the
   `Class::test` multiset over the affected directories must be identical before and after — measured
   by D4's differ, which computes both ends itself. **D2 changes no test file at all**, which is its
   own strongest check: `git diff --stat -- test/` must show the three modules untouched.
2. **Order-independence.** The affected directories pass in default **and** reverse directory order.
   D5's hoists change what a module binds at import time, and run 1's seven-test failure from exactly
   that cause is what makes this check necessary rather than ceremonial.
3. **The rule's count moves in exactly three ways, each reported separately.** It *falls* by the three
   modules D2 exempts; it *rises* by the newly-visible over-budget helpers (D3); and nothing else
   moves. A single net figure would hide two of the three behind the third, which is the same
   two-things-in-one-number defect lesson 4 records. Report the three modules by name, so a reader can
   see the exemption did not quietly swallow a fourth.
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
* **This plan will forfeit its automated review, and that is a decision rather than an oversight.**
  Run 1's PR reached 309 files and both automated reviewers refused it on file-count ceilings — 100
  and 300 — so two thirds of the repository's review capacity was structurally unreachable. D7 alone
  touches ~391 files, so this plan lands in the same place. It is taken anyway: the alternative is
  carrying ~691 inert suppressions indefinitely, and the sweep is the one part of this plan a human
  can verify without reading the diff, by re-running the tool over D7's commit. **Keep D7 in its own
  commit** so that verification is available, and say so in the PR body.
  **Record a proposal** for how a slice should be carved into pull requests so a future run does not
  face the same trade; do not take the decision, and do not restructure the lane's one-plan-one-PR
  cycle to fit — that is the contract's, and the run may not amend the contract that governs it.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**. Every artifact cited here is git-tracked or is produced by
  a command this plan states.
