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

# Reduce the configuration and manifest test slice

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. It consumes the house style
> `010` writes into `pm-dev-python:pytest-testing` and `plan-marshall:persona-module-tester`, and the
> `parse_ns` / marshal-config helpers `020` adds to `test/conftest.py`. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> five sibling plans are converging on the same harness and a sixth private one defeats the epic.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the ten house-style rules **B1**–**B10** this plan
> applies, and the concurrency contract. The landed skills are the authority where they and the README
> disagree.

## Problem

The configuration and manifest slice of the test tree — `manage-config`,
`manage-execution-manifest`, `manage-run-config`, `manage-references`, `manage-solution-outline`,
`marshall-steward` — carries roughly 53,800 lines of `test_*.py`. It is the epic's clearest instance
of the corpus-wide defect, because what it tests is a table: seeded config knobs, decision-matrix
rows, step orderings, lane overrides. Tables belong in parametrized cases, and almost none of this
slice is written that way.

`manage-config/test_config_defaults.py` is the exemplar. It runs to roughly 3,990 lines for about 202
tests, and around 22 of those functions share the naming shape
`test_default_plan_finalize_includes_{knob}` / `test_get_default_config_includes_{knob}`, each
reaching its knob through the same `_params_for(steps, step_id)` accessor and each carrying its own
multi-paragraph docstring.

**They are not 11 clean pairs, and the distinction decides D1's shape.** The two prefixes cover
different knob sets — roughly 7 functions carry the first, roughly 15 the second — and only **three**
knobs (`admin_merge_on_stuck_state`, `auto_rebase_threshold`, `merge_queue_wait_budget_seconds`) are
genuinely crossed against both accessors. Those three are the clean two-accessor collapse. The rest
share the naming shape while several assert unrelated subjects (`project_block`,
`orchestrator_block`, `cost_size_token_table`, `working_prefixes`) and belong in a
single-accessor table or in no table at all. Every one of those counts is a lead — re-derive the
membership and the crossing before collapsing anything, because the naming shape is not the evidence.

`manage-execution-manifest/test_manage_execution_manifest_compose.py` is the slice's largest module at
roughly 5,400 lines. Its own section comment names its subject as "table-driven cases — one per row of
the matrix", and it then writes each row as a separate function.

The slice also carries the corpus's characteristic preamble tax. `test_config_defaults.py` opens by
computing `Path(__file__).parent.parent.parent.parent / 'marketplace' / 'bundles' / …` by hand,
defining a private `_load_module`, and loading seven modules under bespoke aliases —
re-implementing `conftest.load_script_module`, which resolves by `(bundle, skill, script)` and needs
no path arithmetic at all.

## Goal

This slice is written the way its subject actually is: contract tables expressed as parametrized
tables, arrange logic in fixtures and factories, module preambles resolved through the shared loaders,
and docstrings that state the invariant rather than the history of the plan that produced it. Every
contract the slice pins today is still pinned, in materially fewer lines.

## Deliverables

Work the slice **largest module first** — the line reduction and the review risk are both
concentrated there, and stopping early after the large modules leaves the slice better than stopping
early after the small ones.

1. **D1 — Parametrize the contract tables** — starting with
   `manage-config/test_config_defaults.py`. First **derive the family's real membership**: which knobs
   are crossed against both accessors (the clean two-accessor collapse), which appear under one
   accessor only (a single-accessor table), and which merely share the naming shape while asserting an
   unrelated subject (not a table row at all — leave them). Then collapse each group into a
   parametrized table of `(step_id, param_name, expected_default)` rows with `ids=` carrying what the
   per-test names said. Do **not** assume the naming shape implies a pair; the Problem section above
   records that it does not. Apply the same
   collapse to `manage-execution-manifest/test_manage_execution_manifest_compose.py`'s
   decision-matrix rows and `test_decision_rules.py`. Where a test in such a family carries a genuine
   extra assertion the others do not — a "not a flat sibling anymore" negative, a nested-shape check —
   that assertion **survives**, either as an extra column in the table or as a separate named test
   beside it. Losing it is a regression however much shorter the file gets.
   *Done when:* no `test_*_includes_{knob}`-shaped family of three or more near-identical functions
   remains in the slice, and the collected test count for each converted module is greater than or
   equal to its pre-conversion count.

2. **D2 — Split every module over the budget** — the module budget landed by plan `010`. Split by
   behaviour cluster into `test_{unit}_{cluster}.py`, never in arbitrary halves. The slice's known
   over-budget modules are `test_manage_execution_manifest_compose.py` (~5,400),
   `test_config_defaults.py` (~3,990), `test_cmd_skill_domains.py` (~1,870),
   `test_ceremony_finalize_selection.py` (~1,600), `test_cmd_quality_phases.py` (~1,530),
   `test_decision_rules.py` (~1,310), `test_build_map_seed.py` (~1,210) and
   `test_run_config.py` (~1,110) — **re-derive the full list**, this one is a lead. Do the split
   **after** D1, because parametrizing first is what makes several modules fit without a split at all.
   *Done when:* every `test_*.py` in the slice is within the landed budget, each new module's name
   states its cluster, and no assertion moved between modules without moving intact.

3. **D3 — Arrange goes into fixtures and factories** — apply **B4** across the slice: a literal used by
   three or more tests becomes a module constant; a setup sequence repeated three or more times becomes
   a fixture; an object built three or more times becomes a factory with keyword overrides. Replace
   hand-built `argparse.Namespace` objects with `020`'s `parse_ns`, and the slice's local
   `_finalize_config` / `_compose_ns` / `_load_sensible_number` builders with the shared helpers where
   one exists. Where `parse_ns` cannot serve a call site — a script with no reachable parser seam,
   which `020` documents — leave the hand-built namespace, and **record the call site in the report**:
   the aggregate of those exceptions is what tells the operator whether `parse_ns` needs widening.
   *Done when:* the slice's `monkeypatch.setattr`-to-fixture ratio is reported before and after, no
   local builder duplicates a shared helper, and every `parse_ns` exception is listed.

4. **D4 — One import preamble** — replace every `spec_from_file_location` block, private
   `_load_module`, and `Path(__file__).parent…` chain in the slice with `conftest.load_script_module`
   / `get_scripts_dir`. `test_config_defaults.py`'s seven-module bespoke-alias preamble is the worked
   case.
   *Done when:* `grep -rn 'spec_from_file_location\|Path(__file__).parent.parent.parent' ` over the
   slice returns nothing, and every module resolves its subject by `(bundle, skill, script)`.

5. **D5 — Docstrings state the invariant, not its history** — apply **B3** across the slice. Strip
   plan ids, deliverable ids ("this plan, D1"), PR numbers, lesson ids, and superseded-behaviour
   narration (a docstring recording that a constant "was removed", or naming the PR that removed it)
   from test docstrings and comments. **Keep** the present-tense rationale that says why an invariant is
   load-bearing — that is what a docstring is for. Where stripping a docstring would lose a genuine
   piece of design rationale that belongs somewhere, put it in the module docstring once rather than
   in every function.
   *Done when:* the `plugin-doctor` `test-docstring-historical-prose` rule (landed by `010`) reports
   zero findings over this slice, and the report carries the before/after finding count.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the `parse_ns` exception list; and the per-rule `test-conventions` finding counts over
   the slice. If the line floor in Verification was not reached, state the shortfall and what remains,
   rather than reaching it another way.
   *Done when:* the report carries all six figures, each labelled with the command that produced it.

## Out of scope

* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness, and a
  concurrent edit to it is a guaranteed collision. A helper this slice needs that `020` did not build
  goes into the slice's own `_{domain}_fixtures.py`, and the promotion is **recorded as a proposal**.
* **Any file under `marketplace/bundles/**`.** Excluded because test refactoring that changes
  production code is not test refactoring — and because a production change here would be invisible to
  the five sibling plans' verification. A production defect found while refactoring is **recorded**,
  not fixed.
* **Any test directory outside this plan's list.** Excluded because the neighbouring directory belongs
  to a concurrently-running sibling plan; touching it collides on merge even when the change is
  obviously right.
* **Deleting a test because it looks redundant.** Excluded because "redundant" is exactly the judgement
  a line target corrupts. Two tests that assert the same thing are merged into one parametrized case,
  which preserves the collected count; a test that is genuinely dead is **reported**, not removed.
* **Adopting property-based testing.** Excluded because `hypothesis` is not a dependency of this
  project and adding one is a user-approval step; plan `010` § D6 carries that proposal. Nothing in
  this slice is a parser or a round-trip encoder anyway — it asserts exact contract values, which
  **B8** puts squarely outside the property-based domain.

## Expected surface

Exactly these directories under `test/plan-marshall/`, and nothing else:

- `manage-config/`
- `manage-execution-manifest/`
- `manage-run-config/`
- `manage-references/`
- `manage-solution-outline/`
- `marshall-steward/`

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~53,800 lines across the six listed directories | HYPOTHESIS | Re-derive: `wc -l $(find test/plan-marshall/{manage-config,manage-execution-manifest,manage-run-config,manage-references,manage-solution-outline,marshall-steward} -name 'test_*.py')` |
| `test_config_defaults.py` carries ~202 tests in ~3,990 lines, ~22 of them sharing the `_includes_{knob}` naming shape | OBSERVED | the file itself; `grep -n '^def test_default_plan_finalize_includes_\|^def test_get_default_config_includes_' test/plan-marshall/manage-config/test_config_defaults.py` |
| Only **three** knobs are crossed against both accessors; the rest of the `_includes_` family is unpaired, and several assert unrelated subjects | OBSERVED | Extract the knob suffix under each prefix **separately** and intersect the two sets — a single grep returning the count 22 does **not** establish pairing. The three are `admin_merge_on_stuck_state`, `auto_rebase_threshold`, `merge_queue_wait_budget_seconds`. Re-derive before D1; the collapse shape depends on it |
| The partition holds — every directory under `test/plan-marshall/*/`, every file at the root of `test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/` itself (which the first two clauses already decompose) appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the three deliberate exclusions. An entry in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Almost none of this slice is written as parametrized tables | HYPOTHESIS | `grep -rn '@pytest.mark.parametrize'` over the six directories, against their test-function count. Report the ratio — it is D1's baseline |
| `test_config_defaults.py` opens with a private `_load_module` and a four-level `Path(__file__).parent` chain, loading seven modules under bespoke aliases | OBSERVED | the first ~105 lines of that file |
| `test_manage_execution_manifest_compose.py` describes its own subject as table-driven and then writes each row longhand | OBSERVED | the file's "Decision Matrix Tests — table-driven cases" section comment and the functions under it |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |
| Every `_includes_{knob}`-family pair asserts *only* the same thing, so collapsing loses nothing | HYPOTHESIS — **asserted absence of a difference, the higher-risk half** | Read every member of the family before collapsing and record which ones carry an assertion the others do not. A collapse that silently drops one is a coverage loss a green suite will not show. |

## Verification

> ⛔ **SUPERSEDED IN PART — read this before the three conditions below.** This plan landed carrying a
> three-part done-when whose third part is a **30% line floor**. That floor is **retired**, and so is
> every other per-slice floor in this epic: four executed plans returned between 0.52% and 2.56%
> against floors of 20–30%, and three of the six floors turned out to exceed their slice's entire
> comment-and-docstring volume. A run re-entering this plan holds the **five conditions** in
> `doc/plans/test-quality/README.md` § "What a reduction run must hold" — collected count, coverage,
> skipped count, wall-clock, and a line delta that is **measured and reported, never targeted**.
> Where that section and the text below disagree, **that section governs and the run reports the
> disagreement**. Everything else below — the per-deliverable checks, the cold read, the executable
> gate — stands unchanged.


**The three-part done-when as this plan landed. ⛔ Its third condition is RETIRED — read it as a
historical record, not as a gate.** Conditions 1 and 2 stand and are subsumed by the five in
`README.md` § "What a reduction run must hold", which also add the skipped count and the
wall-clock. **Condition 3 below is superseded**: the line delta is measured and reported, never
targeted, and no run is held to the 30% figure it names.

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Parametrizing raises it; deleting a case lowers
   it. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record the before/after
   percentages and the command.
3. ⛔ **RETIRED — recorded, not required.** **Line count drops by at least 30%** of the slice's starting total. This slice carries the epic's
   highest floor because its content is the most tabular — the collapse in D1 is mechanical and its
   yield is large. If the floor cannot be reached without violating (1) or (2), **report the shortfall
   and stop**. The floor is a target, not a licence.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the doctor's
`test-conventions` scope over each of the six directories, before and after, with the per-rule counts
recorded. Use the invocation in `doc/plans/test-quality/README.md` § "Running the plugin-doctor
test-conventions scope" — a **bare** call to `doctor-marketplace.py` fails with
`ModuleNotFoundError: No module named '_dep_detection'`, because the script has no `sys.path`
bootstrap, so the invocation supplies the five scripts directories it needs on `PYTHONPATH`. It is one
command, touches no `.plan/`, and writes nothing. If it cannot be made to run, report the D5
measurement **unavailable** rather than substituting a weaker check.

**By reading — cold read, required for D5.** D5 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading — D1's tables.** Pick the three largest parametrized tables D1 produced and read each
`ids=` list cold:
a reader who has never seen the pre-collapse functions must be able to say what each row asserts from
its id alone. An `ids=` list of `case0, case1, …` has moved the prose out without putting the meaning
back, and fails this check.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition and the three shared constraints restated in this plan's Out of scope.
* **Order within the plan matters.** D1 before D2: parametrizing first is what brings several modules
  under budget without a split, and splitting first produces modules that then have to be split again.
* **The largest single win in this slice is D1.** If the run's budget is tight, D1 across
  `test_config_defaults.py`, `test_manage_execution_manifest_compose.py` and `test_decision_rules.py`
  is worth more than D3–D5 across everything, and it is the work least likely to be contentious in
  review.
