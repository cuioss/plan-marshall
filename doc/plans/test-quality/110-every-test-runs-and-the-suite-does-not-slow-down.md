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

# Every test runs, and the suite does not get slower

**Epic:** test-quality
**Branch prefix:** fix — a skipped test is a contract nothing checks, and the guards are new behaviour

> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10**, and the run
> conditions this plan adds two of.
>
> **Blocking dependency.** Plans `010` and `020` must have landed — confirm with
> `grep -n 'def parse_ns' test/conftest.py` and the module-budget section of
> `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> Nothing else in the epic blocks this plan, and this plan blocks nothing — but the guards it builds
> are worth having **before** plans `070`, `080` and `100` run, because those three are the changes
> most able to move the figures it guards.

## Problem

Two properties of the suite are unmeasured by every plan in this epic, and one of them is quietly
false today.

**A skipped test is a contract nothing checks, and the suite skips.** Every build gate run recorded
across the epic's landed reports ends the same way — `20066 passed, 14 skipped`, `20097 passed, 14
skipped`, `20279 passed, 14 skipped`, `20322 passed, 14 skipped` — a passed count that climbs and a
skipped count that never moves. Those figures are leads and must be re-derived, but the constancy is
the tell: nothing in the epic looked at them.

The mechanism is a population of **environment-conditional guards** spread across the tree.
`grep`-derived at authoring time: roughly 60 skip sites under `test/`, in about fourteen distinct
stated reasons, concentrated in `test/sync-plugin-cache/` (~32 sites, gated on `git` and `rsync` being
on `PATH`) and `test/pm-plugin-development/` (~12 — of which about seven are gated on "real marketplace not
available", three on "real executor not present", and two on `pyright-langserver`, which is a
different class and is treated as one below). Both figures are leads.

They fall into kinds that need opposite treatment, and lumping them together is why nobody has fixed
them:

* **Guards on a tool the build already requires.** `git` and `rsync` are gated per test, in about
  thirty places. On any machine that can run this repository's build, both are present, so the guard
  never fires and buys nothing; on a machine where one is missing, thirty tests vanish silently and
  the run still reports success. That is the *false-clean signal* shape the epic exists to remove,
  applied to the suite's own reporting.
* **Guards on a tree that is always present here.** "Real marketplace not available" and
  "`marketplace/bundles` not available in this checkout" gate roughly a dozen tests. This repository
  **is** the marketplace; the condition is defensive code written for a consumer checkout, inside a
  suite that only ever runs here.
* **Guards on something genuinely absent.** `pyright-langserver` gates a whole module through a
  `pytestmark`, plus two further sites; `pytest-randomly` is absent too, which is why plan `060`'s
  randomised hermeticity arm has gone unrun across three runs. Installing either is a third-party
  dependency decision, which is a user-approval step a cloud run may not take.
* **Guards on a genuinely variable platform.** Windows symlink semantics and `/proc` availability.
  These are legitimate and are not a defect — but nothing today distinguishes them from the three
  kinds above, so nothing stops the population growing.
* **An inverted guard.** One test skips when *an MCP server is reachable*, so it runs on a developer
  machine and silently does not run where one happens to be listening.

**And nothing measured how long the suite takes.** Until the epic re-scoping run that authored this
plan, the epic's done-when covered collected count, coverage and lines — not duration, and not skips.
The README now states both as conditions; what neither has is an instrument, which is this plan's
subject. Re-derived for this plan from GitHub Actions' own timings
for the `Run verification` step of `verify / verify` on `main` (the only instrument that is
comparable across runs, because it is the same job on the same runner class): **781 s** at
`7de3084`, **786 s** at `24271bc` — two commits before plan `020` landed, and the nearest
pre-epic measurement of a full build — and **788 s** at `7cadb98`, the last test-quality PR to land. So across the epic's entire executed
half the suite cost **about two seconds more**, while the collected count rose by roughly 1.3%.
**There is no regression to fix.** Every one of those figures is a lead: re-derive them, and note that
the whole-workflow duration is a far noisier instrument than the step — same-day runs on `main` range
from about 9 to 27 minutes — so the step is what to compare.

What is missing is the instrument, and the risk it would catch is immediately ahead rather than
behind. `test/conftest.py`'s `parse_ns` docstring states its own cost plainly: *"this re-executes the
script module on every call … A test that builds many namespaces should hoist the call into a fixture
or a module-level constant rather than calling it per assertion."* Plans `070` and `080` carry
roughly 502 and 222 hand-built `argparse.Namespace` constructions between them and one `parse_ns` call
in total, so the epic's largest remaining **B6** conversion is still to come; plan `100` will add
several hundred modules, each re-running its own import preamble at collection. Those are exactly the
changes that could move the number, and no plan measures it.

## Goal

The suite reports **zero skipped tests** on the CI runner, with a small, named, guarded exception set
for genuinely variable platform behaviour; and both the skipped count and the suite's wall-clock are
measured on every reduction run, so a regression in either is caught by the run that causes it rather
than found later.

## Deliverables

1. **D1 — Derive the live skip set, and classify every member.** Run the whole suite and capture
   pytest's own skip report (`-rs`), which names each skipped test and its reason — the **live** set,
   which is much smaller than the population of skip *sites*, because most conditions are false here.
   Classify every live skip into exactly one of: *tool the build already requires*, *tree that is
   always present in this repository*, *genuinely absent dependency*, *genuinely variable platform*,
   or *inverted guard*. Do the same for every skip **site**, so a guard that does not fire in this
   environment but would fire in CI is not missed.
   **This is the gating deliverable.** The remaining deliverables act on its classification, and a
   member that fits no class halts the run rather than being assigned to the nearest one.
   *Done when:* every live skip and every skip site carries exactly one class, the run's own skipped
   count is recorded with the command that produced it, and any unclassifiable member has halted the
   run with the member named.

2. **D2 — Replace a per-test tool guard with one preflight that fails.** For every guard on a tool the
   build already requires, remove the per-test `skipif` and assert the requirement **once**, at
   session scope, so a missing tool fails the run loudly instead of deleting thirty tests quietly.
   State the required tools in one place. The reasoning is the epic's own: a guard that never fires
   buys nothing, and on the one machine where it does fire it converts a broken environment into a
   green build.
   *Done when:* no `test_*.py` carries a `skipif` on a tool the preflight requires, the preflight
   fails with a message naming the missing tool (demonstrate this by making the check see an empty
   `PATH` entry and watching it go red), and the tests that were gated now run.

3. **D3 — Turn "the tree might not be here" into an assertion.** For every guard on
   `marketplace/bundles` or the real marketplace tree, replace the skip with an assertion that the
   tree is present. The suite only runs in this repository, and a test that silently does not run
   when the repository's own tree is missing reports nothing about a condition that cannot occur.
   *Done when:* those tests run unconditionally, and the assertion's failure message names the path
   it expected.

4. **D4 — Close the generated-executor gap without generating one.** Several tests skip because
   `.plan/execute-script.py` is absent — it is generated and git-ignored, so it is absent in CI by
   construction and **must stay that way**: the lane forbids this run from touching `.plan/` at all.
   Give those tests a fixture-built executor under `tmp_path` that stands in for the real one, so the
   contract they assert is exercised rather than skipped. Where a test genuinely requires the real
   generated executor and cannot be served by a fixture, that is a *genuinely absent dependency* and
   D5 governs it.
   *Done when:* no test skips on executor absence, each converted test asserts the same contract it
   asserted before, and any test moved to D5's exception list is named with why a fixture cannot serve
   it.

5. **D5 — Bound the exceptions, and guard the boundary.** Two kinds legitimately remain: *genuinely
   variable platform* (Windows symlink semantics, `/proc`) and *genuinely absent dependency*. Record
   them as a **named, enumerated exception list**, and add a guard test that fails when a skip appears
   outside it.

   **The absent-dependency class has two members, not one.** `pyright-langserver` gates a module and
   two further sites. And **`pytest-randomly` is absent too** — plan `060` recorded its slice's
   randomised hermeticity arm as unrun for exactly that reason across all three of its runs, and no
   plan could close it because adding the dependency is a user-approval step. Treat both the same way,
   and do both halves for each: **record a proposal** to add it to `[dependency-groups].dev` — a
   third-party dependency is a user-approval step and this run has no operator, so the run proposes
   and does not decide — **and** cover the contract another way meanwhile, with a stub or fake for the
   language server, and with a **reverse-order** run for hermeticity, which needs no plugin at all and
   is what plan `060` actually used to find a live order-dependent failure.
   Fix the inverted guard here too: a test that skips when something is *reachable* is isolated from
   the ambient environment, not gated on it.
   *Done when:* the exception list exists and is enumerated, the guard fails when a skip is introduced
   outside it (demonstrate by adding one, watching it go red, and removing it), a dependency proposal
   is recorded for **each** absent dependency with the call sites it would unblock, the whole-tree
   reverse-order arm has been run and its result recorded, and the inverted guard no longer consults
   the ambient environment.

6. **D6 — Give the two run conditions an exact command.** `doc/plans/test-quality/README.md` § "What
   a reduction run must hold" **already states** conditions 3 (skipped count) and 4 (wall-clock) — they
   were added by the epic re-scoping run that authored this plan. What that section does **not** carry
   is a literal command for either, and without one two runs produce figures that are not comparable:
   the section says the population must be named and warns that a `pytest` wall-clock is not a
   `./pw verify` total, but it leaves each run to invent the invocation.
   Supply the command, for both conditions, in that section — **this plan's one edit outside `test/`**,
   declared here as a deliverable. Include the slowest-tests capture (`--durations`) so a regression
   can be attributed rather than merely detected. Do **not** restate the conditions themselves; they
   are already there, and a second statement of them is a second thing to drift.
   *Done when:* § "What a reduction run must hold" carries a literal, runnable command for condition 3
   and one for condition 4, the report carries this run's own before/after figures for both, and the
   slowest-tests capture is recorded.

7. **D7 — Report the measured deltas.** Skipped count before and after, whole-tree; the classified
   skip inventory with one row per site; the wall-clock before and after with its population named;
   the slowest-tests capture; the collected item count before and after; and the D5 exception list.
   *Done when:* the report carries every figure with the command that produced it.

## Out of scope

* **Adding `pyright-langserver`, `hypothesis`, or any other third-party dependency.** Excluded
  because adding one is a user-approval step and a cloud run has no operator to ask. D5 records the
  proposal; it does not take the decision.
* **Making CI faster.** Excluded because this plan's subject is *not getting slower*, which is a
  different and far cheaper commitment. An optimisation pass would need its own profiling evidence and
  would compete with the epic's reduction work for the same files.
* **Any `marketplace/bundles/**` file.** Excluded because test refactoring that changes production
  code is not test refactoring. A production defect found here is **recorded**, not fixed. Plan `090`
  owns that surface.
* **Splitting any module over the 400-line budget.** Excluded because plan `100` owns the budget
  campaign; a split here would collide with it.
* **`.plan/` in any form, including generating the executor.** Excluded because the lane forbids this
  lane from touching `.plan/` at all — D4 exists precisely to reach the contract without it.
* **Deleting a test because making it run is awkward.** Excluded because a deleted test and a skipped
  test report the same thing, and the second at least says so.

## Expected surface

- `test/conftest.py` — D2's session-scoped preflight, and D5's guard, if the tree's conventions put
  them there rather than in a root-level meta-test module. ⚠️ **Shared with plan `090`**, which owns
  this file's loader mechanics (`load_script_module`, `get_scripts_dir`, the registration behaviour,
  the `_routing_namespaces` docstring). This plan owns the preflight and the skip guard and touches
  nothing else in the file. **The two must not run concurrently against it** — check for an open PR or
  in-flight branch for `090` before starting, and halt on a live collision
- `test/test_conftest_discipline.py` or a sibling root-level meta-test — D5's exception guard, placed
  per the convention that module already sets
- `test/sync-plugin-cache/` — D2, the largest concentration of tool guards
- `test/pm-plugin-development/` — D3, D4
- `test/marketplace/` — D3
- `test/plan-marshall/lsp-client/`, `test/pm-plugin-development/plan-marshall-plugin/` — D5's absent
  dependency and its in-process stub
- `test/plan-marshall/tools-file-ops/`, `test/plan-marshall/build-server/` — D5's platform exceptions,
  recorded rather than changed
- `test/plan-marshall/platform-runtime/`, `test/plan-marshall/workflow-integration-git/`,
  `test/plan-marshall/workflow-integration-github/`, `test/plan-marshall/phase-6-finalize/`,
  `test/marketplace/targets/claude/` — the remaining scattered sites D1's classification assigns
- `doc/plans/test-quality/README.md` — D6 only, the two run conditions

**This surface crosses several reduction slices deliberately, and that is a collision risk.** The skip
sites do not respect the epic's partition. **Run this plan when no reduction plan is running against
the same directories**, or confirm before starting that `070`, `080` and `100` are not in flight
against `test/sync-plugin-cache/`, `test/pm-plugin-development/` or `test/marketplace/`. If one is,
**halt and report it** rather than editing a file a sibling owns.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The suite reports 14 skipped, and the figure did not move across the epic's executed half | HYPOTHESIS — **gating for D1** | The Build gate sections of the landed reports under `doc/plans/test-quality/*/report-*.md`. **Re-derive** with a whole-tree run: the reports measured different trees at different commits |
| There are ~60 skip sites under `test/` across ~14 distinct stated reasons | HYPOTHESIS — **it sizes D2–D5** | `grep -rn 'pytest.skip\|@pytest.mark.skipif\|pytestmark.*skipif' test --include=*.py`. Re-derive; a site added since authoring belongs to whichever class D1 assigns it |
| `test/sync-plugin-cache/` holds ~32 of them, gated on `git` and `rsync` | HYPOTHESIS | the same grep, scoped to that directory |
| A `skipif` on `git` or `rsync` never fires in an environment that can run this build | HYPOTHESIS — **it is D2's entire justification, and it is an asserted absence** | Check both tools resolve on `PATH` in the CI image *and* in this session, and confirm the live skip report (D1) contains no `git`/`rsync` reason. If it does, D2's premise is refuted: those tests **are** silently not running, which strengthens the deliverable rather than cancelling it — report which |
| This repository always contains `marketplace/bundles/`, so a guard on its absence cannot fire here | OBSERVED | the directory itself, in the clone |
| `.plan/execute-script.py` is generated and git-ignored, so it is absent in a fresh clone | OBSERVED | `.gitignore`; `CLAUDE.md` § "Standalone Plan Lane", which states that `.plan/` state exists only on the machine that created it |
| The `Run verification` step on `main` took 781 s / 786 s / 788 s at `7de3084` / `24271bc` / `7cadb98`, so the epic's executed half cost ~2 s | HYPOTHESIS — **it is this plan's reason for building an instrument rather than hunting a regression** | ⚠️ **This artifact is NOT git-reachable**, which every other claim in this table is: it lives in the GitHub Actions API (job steps of the `verify / verify` job of the `Python Verify` workflow, at those three commits on `main`). The three commits themselves are in your clone and can be confirmed in the stated order; the timings need the API. The figures are also restated in `doc/plans/test-quality/report-authoring-02.md`, which **is** git-tracked — read that as the recorded measurement, and the API as the way to re-derive it. If the API is unreachable, report the re-derivation **unavailable** rather than substituting a local run, whose population is not comparable. Either way the deliverable set is unchanged: D7 reports a regression or its absence, whichever the measurement says |
| `parse_ns` re-executes the script module on every call | OBSERVED | `test/conftest.py` — `parse_ns`, its docstring's "Cost:" paragraph |
| Slices `070` and `080` carry ~502 and ~222 hand-built `Namespace(` constructions and 1 and 0 `parse_ns` uses | HYPOTHESIS | `grep -c 'Namespace('` and `grep -c 'parse_ns('` over each plan's Expected surface. Leads — re-derive |
| No reduction plan is running against this plan's directories, and plan `090` is not in flight against `test/conftest.py` | HYPOTHESIS — **gating and halting; check before D2** | The presence of an open PR or an in-flight branch for `070`, `080`, `100` or `090`. Unresolvable → treat as a collision and halt |

## Verification

**Three conditions, all of which must hold.**

1. **Collected test count does not decrease, and the passed count rises.** A skipped test is still a
   *collected* test, so this plan leaves the collected count unchanged while moving tests out of the
   skipped column and into the passed one. Record all three counts — collected, passed, skipped —
   before and after; the pair that must move is passed-up and skipped-down.
2. **Coverage does not decrease** for the bundle paths the un-skipped tests exercise — and it should
   **rise**, because tests that were not running now are. Record before/after and the command; a
   coverage figure that does not move where a formerly-skipped test now runs means the test is not
   reaching the code it names.
3. **Zero skipped, outside the enumerated exception list.** The whole-tree run reports no skip that
   D5's list does not name.

**A fourth check, and it is what makes D2 and D3 real rather than cosmetic: a converted test must be
able to fail.** For each converted test, break the behaviour it asserts and confirm it goes red. A
test that was skipped and now passes without ever having been observed failing is indistinguishable
from a test that asserts nothing — and converting a silent skip into a silent pass would be the same
false-clean signal in a new costume. Record which tests were mutation-checked and how.

**A fifth check: the exception guard must fire.** D5's guard is a detector, and a detector that has
never been observed detecting is not a guard. Add a skip outside the list, watch the guard go red,
remove it, and record the observation.

**By reading — cold read, required for D6.** D6's text is a run condition two later plans will act
on, and its whole value is whether a later reader produces a *comparable* number. Dispatch the lane's
pre-PR verification sub-agent with **the amended README section and no other context** — not this
plan, not the diff — and ask: "what exact command would you run to produce this figure, and what would
you compare it against?" If two readings of the section produce two different commands, or a reading
compares a `pytest` wall-clock against a `./pw verify` total, the wording failed however complete it
looks. Record the answer verbatim and fix the wording rather than the reader.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus a whole-tree
`pytest` run with `-rs` and `--durations`, before and after, for the skip report and the timing
evidence.

## Notes

* **Why the two halves are one plan.** Both are properties of *the suite as a whole* rather than of
  any slice, both are unmeasured by every other plan in the epic, and both are read from the same
  whole-tree run. Splitting them would double the number of whole-tree measurement runs for no gain.
* **The duration half is a guard, not a repair.** The re-derived figures say the epic's executed half
  cost about two seconds. Do not go looking for a regression to fix; build the instrument, record the
  baseline, and let the plans that follow be measured by it. If the re-derivation contradicts the
  figures above, that is a finding for the report — and the deliverables are unchanged either way.
* **Sequencing.** Best run before `070`, `080` and `100`, because those three are what the instrument
  exists to watch. It is not a blocking dependency for any of them: a later run can still take the
  baseline, it will just take it after the change rather than before.
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked or is
  produced by a command it states.
