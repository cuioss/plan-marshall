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

# The shared test harness the corpus keeps re-implementing

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Read first.** The epic's scoping brief — the corpus census and the ten house-style rules — is
> `doc/plans/test-quality/README.md`, a git-tracked sibling present in your clone. Read it before D1.
> This plan builds the harness that makes rules **B4**, **B5**, **B6**, **B7** and **B10** cheap to
> follow; plan `010` writes those rules into the governing skills.

## Problem

`test/conftest.py` is a substantial, well-built shared surface: script running, module loading by
`(bundle, skill, script)`, four autouse isolation sandboxes, pollution guards, a plan context, and a
build context. Roughly 400 call sites use its `load_script_module`. It is not the problem.

The problem is everything the corpus builds *beside* it, because the shared surface stops short of the
three things test modules actually spend their lines on.

**Argument construction.** Around 2,900 `argparse.Namespace(...)` objects are hand-built across ~292
modules, and around 150 modules define their own private `_ns_*` builder to make that bearable. Each
hand-built namespace is a guess at what the real parser produces: it carries only the attributes the
author remembered, not the parser's defaults. A flag added to a script with a default therefore breaks
production while every one of those namespaces keeps passing. There is no shared helper that builds a
namespace by running the script's own parser, so every module either re-derives one or accepts the
gap.

**Fixture data.** `create_marshal_json` is defined **three times** with three incompatible signatures
— `conftest.create_marshal_json(base_dir, skill_domains=None, extra=None)`,
`test/plan-marshall/manage-config/test_helpers.py::create_marshal_json(fixture_dir, config=None)`,
and `test/plan-marshall/phase-6-finalize/test_triage_extension.py::create_marshal_json(fixture_dir, config)`
— against roughly 253 call sites. Which one a module gets depends on which it imported. Beyond it,
eighty-odd modules inline a `plan.phase-6-finalize` config literal by hand.

**Module preamble.** Around 197 modules still open with a raw `spec_from_file_location` block or a
`Path(__file__).parent.parent.parent.parent` chain to locate the scripts directory, re-implementing
`load_script_module` / `get_scripts_dir` locally — often as a private `_load_module` with a
per-module alias, sometimes seven times in one file.

Two smaller defects compound it. `test/plan-marshall/manage-config/test_helpers.py` is a 223-line
helper module with **zero test functions**, imported by ~23 modules, and named `test_*.py` — so pytest
collects it, finds nothing, and the module is invisible in the run. It is also a bare-name collision
hazard resolved by pytest's rootdir-based import, and the existing `unique-fixture-basenames` doctor
rule cannot see it because that rule only inspects `_`-prefixed files. And `test/conftest.py`'s own
module docstring instructs the reader to "See test/README.md for full documentation" — a file that
does not exist.

## Goal

One shared harness owns argument construction, marshal-config staging, and module loading, and one
git-tracked document tells an author which surface to reach for and where a new helper belongs. A
module written against this harness spends its lines on the behaviour it asserts rather than on
re-deriving the scaffolding, and the six reduction plans that follow have one thing to converge on
instead of six.

## Deliverables

1. **D1 — `parse_ns`: build namespaces from the real parser** — add to `test/conftest.py`. Signature
   in the shape `parse_ns(bundle, skill, script, *argv) -> argparse.Namespace`: resolve the script,
   obtain its real `ArgumentParser`, and return `parser.parse_args(list(argv))` so the namespace
   carries every default the production CLI would apply. Derive the parser through the script's own
   published entry point — do **not** re-implement its subparser graph, and do **not** execute the
   command. Where a script's parser is only reachable by calling a builder function, resolve that
   function by a documented convention and state the convention in the docstring; where a script
   exposes no such seam, raise a clear, named error rather than silently falling back to a
   hand-built namespace, because a silent fallback reintroduces exactly the defect this helper closes.
   *Done when:* `parse_ns` is exported from `test/conftest.py`, a namespace it returns for a script
   with a defaulted flag carries that default without the caller naming it, and the no-seam path
   raises a named error rather than degrading.

2. **D2 — One marshal-config builder** — collapse the three `create_marshal_json` definitions into a
   single `conftest` helper that supersedes all three call shapes: a full-config form (caller supplies
   the whole dict) and a defaults-plus-overrides form (caller supplies only what differs). Add the
   companion `run-configuration.json` builder currently stranded in `test_helpers.py`. Delete the two
   duplicate definitions and repoint their importers. Where the three defaults genuinely differ —
   `conftest`'s `MARSHAL_SCHEMA_DEFAULT` and `test_helpers`' java-flavoured default are not the same
   config — do **not** average them into a third: keep the distinct shapes as **named** presets on the
   one builder, so a caller states which baseline it wants instead of inheriting whichever module it
   imported from.
   *Done when:* exactly one `create_marshal_json` definition exists under `test/` (verify by
   `grep -rn 'def create_marshal_json' test`), every former call site resolves against it, the distinct
   baselines survive as named presets, and the suite passes with no change to the collected test count.

3. **D3 — Retire `test_helpers.py`** — rename
   `test/plan-marshall/manage-config/test_helpers.py` to `_manage_config_fixtures.py` (domain-prefixed
   per the existing `unique-fixture-basenames` rule), move its `create_marshal_json` /
   `create_run_config` into the D2 builder, and update the ~23 importers. The file currently declares
   no test function while matching pytest's collection pattern, so pytest imports it and collects
   nothing.
   *Done when:* no module under `test/` matches `test_*.py` or `*_test.py` while declaring zero test
   functions and zero `Test*` classes (re-derive the check; report the count before and after), and
   every former importer resolves the new name.

4. **D4 — Write `test/README.md`** — the document `test/conftest.py` already tells readers to consult.
   It is a **navigation and ownership** document, not a restatement of the testing standards, which
   live in `pm-dev-python:pytest-testing` and `plan-marshall:persona-module-tester` and are
   cross-referenced rather than copied. It states: the tree layout; what `test/conftest.py` owns and
   what it deliberately does not; what `test/_shared/**` is for and how it differs from a per-subtree
   `_{domain}_fixtures.py`; **the decision rule for where a new helper goes** — used by one subtree,
   it is local; used by three or more subtrees, it is a promotion proposal, not a unilateral edit; and
   the four autouse isolation fixtures with the marker that opts out of each.
   *Done when:* `test/README.md` exists, `test/conftest.py`'s docstring reference resolves, the file
   states the one-subtree / three-subtree promotion rule, and it cross-references the two standards
   files rather than restating their content.

5. **D5 — Protect the harness with its own tests** — a new
   `test/_shared/../test_shared_harness.py` module (place it where the tree's own conventions put a
   root-level meta-test, alongside `test_conftest_discipline.py`) covering: `parse_ns` applies parser
   defaults the caller did not name; `parse_ns` raises the named error for a script with no reachable
   parser seam; the marshal builder's presets produce the distinct baselines D2 preserved; and the
   D3 invariant — no collected module under `test/` declares zero tests — as a whole-tree guard in the
   shape `test_conftest_discipline.py` already uses. The whole-tree guard must assert its **population
   is non-empty before** asserting the offender list is empty, so a mis-rooted walk cannot pass
   vacuously; `test/marketplace/test_prefix_strip_idiom_retired.py` is the pattern to copy.
   *Done when:* each of the four properties has a test, the whole-tree guard carries a population
   assertion, and a deliberately-introduced violation of each fails the corresponding test.

6. **D6 — Convert up to ten modules as proof of use** — pick **at most ten** modules, spread across at
   least four different subtrees, and convert them onto the harness: `parse_ns` for their namespaces,
   the D2 builder for their config, `load_script_module` / `get_scripts_dir` for their preamble. Choose
   them for **evidential value, not size** — the point is to prove the harness serves the shapes that
   exist, so include at least one module whose script has a deep subparser graph, one that stages a
   non-default marshal config, and one that currently opens with a multi-module `_load_module`
   preamble. Report the per-module line delta and the total.
   *Done when:* ten or fewer modules are converted, the set spans four or more subtrees and includes
   the three named shapes, the collected test count for those modules is unchanged, and the report
   carries the per-module line delta.

## Out of scope

* **Bulk conversion of the corpus.** Only the ten proof-of-use modules in D6. Excluded because plans
  `030`–`080` partition the test tree between themselves to run concurrently, and a module this plan
  converted outside its own small proof set is a module one of them then collides with. Ten is a
  deliberate ceiling, not a starting point.
* **Changing the four autouse isolation fixtures, the pollution guards, or the marker registry.**
  Excluded because they are measured, documented, and load-bearing for suite hermeticity; this plan
  adds surface beside them and does not touch their behaviour.
* **Changing `pyproject.toml`'s pytest configuration.** Excluded for the same reason — the timeout,
  `filterwarnings`, marker registry, and xdist settings each carry a recorded derivation and none is
  implicated in what this plan builds.
* **Adding a property-based-testing dependency.** Excluded because `hypothesis` is third-party and
  therefore a user-approval step with no operator present; plan `010` § D6 records that proposal.
* **The two governing skills.** Owned by plan `010`, which may be running concurrently. If building
  the harness teaches you something the standards should say, **record it in the report as a proposal**
  — do not edit those files.

## Expected surface

- `test/conftest.py` — D1, D2
- `test/README.md` — D4 (new)
- `test/plan-marshall/manage-config/test_helpers.py` → `_manage_config_fixtures.py` — D3 (rename)
- `test/plan-marshall/phase-6-finalize/test_triage_extension.py` — D2 (remove the duplicate definition)
- `test/test_shared_harness.py` — D5 (new; sibling of the existing `test_conftest_discipline.py`)
- The ~23 importers of `test_helpers` and the ~253 call sites of `create_marshal_json` — D2, D3
  (import-line updates only)
- Up to ten modules across four or more subtrees — D6

Nothing under `marketplace/bundles/**`. Nothing in `pyproject.toml`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `create_marshal_json` is defined three times with incompatible signatures | OBSERVED | `grep -rn 'def create_marshal_json' test --include=*.py` — three hits: `test/conftest.py`, `test/plan-marshall/manage-config/test_helpers.py`, `test/plan-marshall/phase-6-finalize/test_triage_extension.py` |
| `test/plan-marshall/manage-config/test_helpers.py` declares zero test functions and is imported by ~23 modules | OBSERVED | the file itself; `grep -rln 'from test_helpers import\|import test_helpers' test` |
| `test/conftest.py` references a `test/README.md` that does not exist | OBSERVED | the `conftest.py` module docstring; `ls test/*.md` |
| `test/conftest.py` already exports `load_script_module` and `get_scripts_dir`, and ~197 modules still hand-roll the equivalent | OBSERVED | `test/conftest.py`; `grep -rn 'spec_from_file_location' test --include=*.py` |
| No shared helper builds an `argparse.Namespace` from a script's real parser | HYPOTHESIS — **this is an asserted absence, the higher-risk half** | Read `test/conftest.py` end to end and enumerate `test/_shared/*.py`. If such a helper exists, D1 extends it rather than adding a second. Note that `test/plan-marshall/script-shared/test_argparse_surface.py` exercises an `argparse_surface` module that derives a script's *accept set* by running its `--help` — establish whether that module offers a reachable parser seam D1 should build on before writing a new one. |
| ~2,900 hand-built namespaces across ~292 modules, and ~150 local `_ns_*` builders | HYPOTHESIS | Re-derive: `grep -rn 'Namespace(' test --include=test_*.py \| wc -l`, `grep -rln 'Namespace(' test --include=test_*.py \| wc -l`. Report what you measure. |
| Every script whose namespace a test builds exposes a reachable parser-builder seam | HYPOTHESIS — **settle this before D1's design, it decides the shape** | Sample at least ten scripts across at least four bundles under `marketplace/bundles/*/skills/*/scripts/` and record how each constructs its parser. If a meaningful fraction has no reachable seam, D1's error path is the primary path and D6's module selection must reflect that — say so in the report rather than forcing the helper onto scripts it cannot serve. |

## Verification

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Additionally, and
this is the load-bearing check for a refactor of shared fixtures: capture pytest's **collected-item
count** for the whole `test/` tree before the first commit and again before the PR, and record both in
the report. They must be equal. A shared-fixture change that silently drops a module from collection
is the exact failure this plan is most able to cause, and a green suite does not show it — only the
count does.

**By reading.** D4 is text whose value is what a later author does with it. Dispatch the lane's pre-PR
verification sub-agent with `test/README.md` **and no other context**, and ask: "I have written a
helper used by tests in three different subtrees. Where does it go, and who decides?" The expected
reading is that a helper used by three or more subtrees is a **promotion proposal for the operator**,
not a unilateral edit to `test/conftest.py` or `test/_shared/`. Any other reading means D4's wording
failed. Record the answer verbatim.

## Notes

* **Sequencing.** This plan and plan `010` are the epic's two blocking plans; they may run
  concurrently with each other and must both land before any of `030`–`080` starts. Their surfaces are
  disjoint — `010` touches `marketplace/bundles/**` plus one plugin-doctor test module, this plan
  touches `test/conftest.py`, `test/_shared/`, `test/README.md`, and a bounded proof set.
* **The reduction plans are your consumers.** Six plans will build against this harness concurrently
  and none of them may edit it. That makes D1's and D2's signatures expensive to change later — favour
  the shape that serves the shapes the tree actually has over the shape that is tidiest, and settle the
  parser-seam hypothesis before you commit to `parse_ns`'s signature.
* **`test/marketplace/test_prefix_strip_idiom_retired.py` is the model for D5's whole-tree guard** —
  population asserted non-empty before the offender list is asserted empty, positive controls that
  prove the detector fires, and a negative control that proves it does not over-fire. Copy that shape.
