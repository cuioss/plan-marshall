# test-quality

The epic that brings the Python test corpus under a stated, enforced house style and shrinks it
without losing a single assertion.

This is a **standalone epic**: unlike `truthful-signals`, `review-apparatus`, and
`code-intelligence-substrate`, it has no counterpart ledger under `.plan/local/orchestrator/`. It was
opened directly from a whole-corpus review. Everything it needs is in git; nothing in it expects an
orchestrator record to exist.

Read [`../README.md`](../README.md) for the tree layout and the run contract, and
[`../cloud-bridge.md`](../cloud-bridge.md) for the `{NNN}-` prefix rule. This file adds only what is
specific to this epic: the census the plans were scoped from, the house style they converge on, and
the dependency graph that says which of them may run at the same time.

[`findings-test-corpus-review.md`](findings-test-corpus-review.md) is the **evidence** this file is
scoped from — the corpus review itself, with the per-finding detail, the named exemplars, the review's
own coverage limits, and what in the corpus is good enough that a reduction plan must not touch it.
Read it when you need to know *why* a rule below says what it does; this file is the operative brief.

## The census

Every number below is a **lead, not a fact**. It was measured on one clone at one moment; re-derive
anything you are about to act on. The commands are stated so re-derivation is mechanical.

| Measure | Lead | How to re-derive |
|---|---|---|
| `test_*.py` files under `test/` | ~770 | `find test -name 'test_*.py' \| wc -l` |
| Lines in those files | ~377,000 | `wc -l $(find test -name 'test_*.py') \| tail -1` |
| `def test_` declarations | ~17,600 | `grep -rn '^def test_\|^    def test_' test --include=test_*.py \| wc -l` |
| Median file size | ~323 lines | sort the `wc -l` output |
| Files over 400 lines | ~309 (40%) — holding ~73% of all lines | `wc -l $(find test -name 'test_*.py') \| awk '$1>400'` |
| Files over 1000 lines | ~74 | same, `$1>1000` |
| Files using `@pytest.mark.parametrize` | ~179 of 770 | `grep -rl '@pytest.mark.parametrize' test --include=test_*.py \| wc -l` |
| `@pytest.mark.parametrize` decorators | ~497 | `grep -rn '@pytest.mark.parametrize' test --include=test_*.py \| wc -l` |
| Hypothesis usage | **zero** | `grep -rn 'hypothesis' test --include=*.py` |
| `Namespace(` constructions | ~2,900 across ~292 files | `grep -rn 'Namespace(' test --include=test_*.py \| wc -l` |
| Local ad-hoc namespace builders | ~150 | `grep -rn 'def _ns\|def _make_ns\|def .*_ns(' test --include=test_*.py \| wc -l` |
| `monkeypatch.setattr` calls | ~2,397 | `grep -rn 'monkeypatch.setattr' test --include=test_*.py \| wc -l` |
| `@pytest.fixture` declarations | ~221 | `grep -rn '@pytest.fixture' test --include=test_*.py \| wc -l` |
| Raw `spec_from_file_location` preambles | ~197 (against ~401 uses of the `load_script_module` helper that replaces them) | `grep -rn 'spec_from_file_location' test --include=*.py \| wc -l` |
| `run_script(` subprocess calls | ~1,214 across ~197 files | `grep -rn 'run_script(' test --include=test_*.py \| wc -l` |
| Comment lines | ~33,800 (9%) | `grep -rhn '^\s*#' test --include=test_*.py \| wc -l` |
| Blank lines | ~78,500 (21%) | `grep -rh '^\s*$' test --include=test_*.py \| wc -l` |
| `assert` lines | ~42,900 (11%) | `grep -rh '^\s*assert ' test --include=test_*.py \| wc -l` |
| Lines carrying historical narrative markers | ~974 | `grep -rn 'once derived\|used to \|previously\|no longer\|the old \|legacy ' test --include=test_*.py \| wc -l` |
| Lines citing an incident, lesson, or PR number | ~393 | `grep -rn 'lesson-20\|LESSON-\|PR #[0-9]' test --include=test_*.py \| wc -l` |
| Lines citing a plan or deliverable id | ~1,335 | `grep -rn 'deliverable\|D[0-9] —\|this plan' test --include=test_*.py \| wc -l` |

### What the census does *not* say

The corpus is **not** full of coverage-only tests. Tautological assertions number roughly two dozen
tree-wide (`grep -rn 'assert True\|assert 1 ==' test --include=test_*.py`); bare
`assert result is not None` appears ~192 times
(`grep -rn 'assert result is not None$' test --include=test_*.py | wc -l`) and is in almost every case
followed by substantive assertions. Both figures are leads — re-derive them. Individually the tests
are behavioural, they name real contracts, and several subtrees carry deliberate positive/negative
control pairs. **The problem is not what the tests assert — it is how much text it takes them to
assert it.** Any plan in this epic that deletes an assertion to hit a line target has failed, not
succeeded.

Two structural exceptions worth naming, because they are the shape a plan should look for:

* `test/plan-marshall/manage-config/test_config_defaults.py` carries ~22 functions sharing the
  `test_default_plan_finalize_includes_{knob}` / `test_get_default_config_includes_{knob}` naming
  shape. **They are not 11 clean pairs** — the two prefixes cover different knob sets, and only three
  knobs (`admin_merge_on_stuck_state`, `auto_rebase_threshold`,
  `merge_queue_wait_budget_seconds`) are genuinely crossed against both accessors. Those three are the
  collapse target; the remaining functions share the naming shape while several test unrelated
  subjects. Re-derive the pairing before collapsing anything — the naming shape is not the evidence.
* `test/plan-marshall/audit-archived-plan-retrospectives/` carried two oversized modules —
  `test_audit_checks.py` at ~8,700 lines over ~90 test classes, and `test_audit.py` at ~1,500. Plan
  `050` decomposed the first into **49** check-named modules and the second into **15**, with the
  shared builders in `_audit_fixtures.py`. Every check in the skill's 24-entry inventory is now
  reachable by filename, so the directory is the worked example of what this shape looks like when it
  lands.

## House style

The style every plan in this epic converges on. Plan `010` writes it into
`pm-dev-python:pytest-testing` and `plan-marshall:persona-module-tester`; plan `020` builds the
harness that makes it cheap; plans `030`–`080` apply it. Where this file and the landed skills
disagree, **the skills win** — this file is the epic's scoping brief, not the standard.

**B1 — Module budget: 400 lines.** A test module over 400 lines is split by *behaviour cluster*, not
in arbitrary halves: `test_{unit}_{cluster}.py`. 400 is chosen against the corpus, not invented — the
median module is already ~323 lines and ~60% of modules already comply, so the budget describes the
tree's own better half rather than an aspiration. It **replaced** the `~200 lines` figure
`persona-module-tester` previously carried, which ~75% of the corpus violates and which no guard ever
enforced. Plan `010` retired that figure and made the 400-line budget enforced.

**B2 — Test budget: 15 lines of body.** A test function body (excluding its docstring) over ~15 lines
is carrying arrange logic that belongs in a fixture or a factory. This is a review trigger, not a
build failure.

**B3 — Docstrings state the invariant, not its history.** One line, present tense, naming the contract
the test pins. A second paragraph only when the invariant is genuinely non-obvious. **Never**: the
incident that motivated the test, a plan or deliverable id, a PR number, a lesson id, "used to",
"no longer", "the old behaviour". This is not a new rule — it is `CLAUDE.md` § Documentation Standards
("No version history", "Current state only") applied to a tree those standards were never scoped over,
and it is the same rule the `plugin-doctor` `historical-prose-in-skills` /
`incident-reference-in-docs` / `lesson-id-in-skill-prose` rules already enforce over
`marketplace/bundles/**`. The rationale a docstring legitimately carries is *why this invariant is
load-bearing*, which is present-tense and survives the edit; the narrative of how it was discovered
is not.

**"Never cite" is not "never name".** A docstring frequently has to state the exact identifier the
test asserts on, and that is the contract rather than a citation. Write such a value in an inline
literal (``` ``TASK-001`` ```) and leave a citation bare; the `test-docstring-historical-prose` rule
exempts matches inside a backtick span or a quoted string, so the formatting is what carries the
distinction.

**B4 — Arrange goes in a fixture or a factory.** A literal repeated in three or more tests in a module
becomes a module constant. A setup sequence repeated in three or more tests becomes a fixture. An
object built in three or more tests becomes a factory with keyword overrides. The corpus's ~11:1 ratio
of `monkeypatch.setattr` calls to fixture declarations is the measure of how far it is from this.

**B5 — Parametrize the table, not the prose.** Two tests differing only in input and expected output
are one `@pytest.mark.parametrize` with an `ids=` list carrying what the two docstrings said. This is
the single largest available reduction and the corpus's least-used tool.

**B6 — Argument namespaces come from the real parser.** A hand-built `argparse.Namespace` does not
carry the parser's defaults, so a test can pass against a namespace the real CLI would never produce —
and a newly-added flag with a default breaks nothing in the suite while breaking production. Build
command arguments through the shared helper that runs the script's own parser. This is
`persona-module-tester` § "Foundation utilities — tests against the CLI" applied to the ~2,900
hand-built namespaces the corpus currently carries.

**B7 — One import preamble.** `load_script_module` / `get_scripts_dir` from `conftest`. No
`Path(__file__).parent.parent.parent.parent` arithmetic, no per-module `spec_from_file_location`, no
per-module `_load_module` re-implementation.

**B8 — Property-based testing where the contract is universal, examples everywhere else.** Hypothesis
earns its place for text and format parsers, identifier validators, path normalisers, and round-trip
encoders — the places where the contract really is "for all valid inputs". It is **actively wrong**
for most of this corpus: a test asserting that `default:branch-cleanup` seeds
`merge_queue_wait_budget_seconds: 1800` is asserting an exact contract value, and a generator there
would assert nothing at all. `persona-module-tester` previously carried a "prefer generated test data
over hardcoded literals" phrasing that read as a blanket preference; plan `010` replaced it with the
universal-contract / literal-is-the-contract discriminator that scopes it. Hypothesis is a
third-party dependency and therefore a **user-approval step** — plan `010` records the proposal and
names the candidate call sites; it does not add the dependency.

**B9 — One layer per contract.** Where an in-process test and a subprocess test assert the same
behaviour, the in-process one is authoritative and the subprocess one collapses to a single
per-script CLI-plumbing smoke. The subprocess layer's job is to prove the entry point wires up, not to
re-assert the logic.

**B10 — Helper modules are `_{domain}_fixtures.py`.** Never `test_*.py` (pytest collects it, and a
helper module that collects zero tests is a silent no-op in the run), never a nested `conftest.py`,
never a bare `_fixtures.py` or `_helpers.py`.

## Running the plugin-doctor test-conventions scope

Every plan in this epic measures itself with the doctor's `test-conventions` scope, so the invocation
is stated **once, here**, verified to run.

**A bare call to the script fails.** `doctor-marketplace.py` has no `sys.path` bootstrap: its import
chain reaches into *other* skills' scripts directories (`_doctor_shared` → `_dep_detection` under
`tools-marketplace-inventory`; `file_ops` → `toon_parser` under `ref-toon-format`), so
`python3 marketplace/bundles/.../doctor-marketplace.py test-conventions` dies with
`ModuleNotFoundError: No module named '_dep_detection'`.

**Supply the five scripts directories it needs on `PYTHONPATH`, in one command.** This is a single
invocation with no shell substitution, no loop, and — deliberately — **no `.plan/` involvement**: the
lane forbids this run from touching `.plan/` at all, and generating the executor to borrow its
`PYTHONPATH` would violate that prohibition for a convenience the line below does not need.

```bash
PYTHONPATH=marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts:marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts:marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts:marketplace/bundles/plan-marshall/skills/script-shared/scripts:marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts python3 marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py test-conventions --test-root {path}
```

`{path}` is `test/` for a whole-tree sweep, or one directory for a per-directory count. The whole-tree
**rule-firing** sweep that plan `080` diffs before and after is the sibling subcommand `quality-gate`
— same `PYTHONPATH`, and it takes no `--test-root` (it rejects the flag):

```bash
PYTHONPATH=marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts:marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts:marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts:marketplace/bundles/plan-marshall/skills/script-shared/scripts:marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts python3 marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py quality-gate
```

This writes nothing anywhere, so the working tree stays clean and there is nothing to stage. It is a
five-directory subset of the `PYTHONPATH` that `test/conftest.py::_setup_marketplace_pythonpath`
assembles in-process for pytest by globbing every scripts directory — spelled out literally rather
than derived, so it stays a single command with no shell substitution. The five
directories are a lead like any other — if the import chain has grown a sixth, the `ModuleNotFoundError`
names it, so add it and say so in the report. If the command cannot be made to run at all, the
measurement is genuinely **unavailable**: report it as such rather than substituting a weaker check.

## What "reduce the line count" means here

Every reduction plan carries the same three-part done-when, and **all three must hold**:

1. **Collected test count does not decrease.** Measured as pytest's own collected-item count for the
   subtree, before and after. Parametrizing raises it; deleting a case lowers it. This is the guard
   that separates simplification from deletion.
2. **Coverage does not decrease** for the bundle paths the subtree exercises.
3. **Line count drops by at least the plan's stated floor.**

A plan that cannot hit its line floor without violating (1) or (2) reports the shortfall and stops.
The floor is a target, not a licence.

## The plans, and what may run at the same time

```text
010 standards + enforcement ─┐
                             ├─→ 030  config & manifest          ─┐
020 shared harness         ──┘   040  delivery pipeline           │
                                 050  plan state & records        ├─ mutually parallel
                                 060  runtime & script substrate  │
                                 070  architecture & orchestration│
                                 080  plugin-development & generator ─┘
```

| Plan | Surface | May run concurrently with |
|---|---|---|
| `010` | `marketplace/bundles/pm-dev-python/skills/pytest-testing/**`, `marketplace/bundles/plan-marshall/skills/persona-module-tester/**`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**`, `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` (including the `rule4.py` and `rule6.py` it adds), `test/pm-plugin-development/plugin-doctor/fixtures/test_conventions/rule*/`, `test/pm-plugin-development/plugin-doctor/test_doctor_marketplace_commands.py` (the `cmd_test_conventions` cases only), `test/pm-plugin-development/plugin-doctor/_fixtures.py` | `020` only |
| `020` | `test/conftest.py`, `test/_shared/**`, `test/README.md`, and the ≤10 modules it converts as proof-of-use | `010` only |
| `030`–`080` | one disjoint slice of `test/` each, listed in the plan | each other, once `010` **and** `020` have landed |

**`010` and `020` are blocking.** The reduction plans consume the harness `020` builds and the style
`010` writes; run either reduction wave before them and it will invent its own harness, which is the
duplication this epic exists to remove.

**`010` and `020` may run concurrently with each other** — their surfaces are disjoint (`010` touches
`marketplace/bundles/**` plus one plugin-doctor test module; `020` touches `test/conftest.py`,
`test/_shared/`, and `test/README.md`).

**`030`–`080` are mutually parallel by construction.** Each owns a disjoint list of `test/`
subdirectories, stated in its Expected surface.

⚠️ **The partition is a hand-written list, so every run re-derives it before acting on it.** The
lists below were correct when authored and cover every directory then present, but a directory added
to `test/plan-marshall/` between authoring and a run belongs to **no** plan and would be silently
skipped, with nothing positioned to notice. Each reduction plan therefore carries this as a **gating,
halting derivation**, run before its first deliverable:

1. List every directory under `test/plan-marshall/*/`, **every file at the root of
   `test/plan-marshall/`**, and every top-level entry under `test/` **other than `plan-marshall/`
   itself** — that one is decomposed by the first two clauses, so listing it as well would report it
   unclaimed and halt on a non-defect. The root-level files are not an afterthought either: they are
   exactly the category a slice boundary is most likely to mis-assign, since they sit in one plan's
   tree while being imported from another's.
2. Confirm each appears in **exactly one** of `030`–`080`'s Expected surface, allowing for these
   three deliberate exclusions and no others: `test/_shared/` and `test/conftest.py` (both plan
   `020`'s), and `test/fixtures/` (holds no `.py`).
3. An entry in **two** lists, or in **none**, is a partition defect: **halt and report it** rather
   than claiming or skipping it unilaterally. An entry claimed by no plan is the dangerous case,
   because it looks exactly like a clean run.

Independently, the six slices' line totals must sum to the corpus total
(`wc -l $(find test -name 'test_*.py')`); a sum that falls short means a gap, and one that exceeds it
means an overlap.

Three shared constraints keep the slices disjoint once the partition is confirmed, and every
reduction plan restates them:

* A reduction plan **never edits `test/conftest.py` or `test/_shared/**`**. If it needs a shared
  helper that `020` did not build, it adds it to its own subtree's `_{domain}_fixtures.py` and records
  the promotion as a proposal in its report.
* A reduction plan **never edits a `marketplace/bundles/**` file**. If it finds a production defect,
  it records it; it does not fix it. Test refactoring that changes production code is no longer test
  refactoring.
* A reduction plan **never edits a directory outside its own list**, even to fix something obvious
  there. The neighbouring directory belongs to a concurrently-running sibling.

One narrow carve-out, because two plans would otherwise collide: plan `010` owns
`test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` — the three modules that
already test this scope's rules plus the `rule4.py` and `rule6.py` it adds — their fixture directories
under `fixtures/test_conventions/rule*/`, the `cmd_test_conventions` cases in
`test_doctor_marketplace_commands.py`, and the `_fixtures.py` corpus entries that make its new rules
fire (it ships the tests for the rules it adds). Plan `080` owns the rest of
`test/pm-plugin-development/**` and excludes those modules explicitly.
