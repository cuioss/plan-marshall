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

* `test/plan-marshall/manage-config/test_config_defaults.py` carried ~22 functions sharing the
  `test_default_plan_finalize_includes_{knob}` / `test_get_default_config_includes_{knob}` naming
  shape — **not 11 clean pairs**, since the two prefixes covered different knob sets and only three
  knobs were genuinely crossed against both accessors. Plan `030` collapsed that family, and its
  second run re-derived the module and found **no name-shape family of three or more** left in it.
  The exemplar is kept here because the *lesson* outlived the instance: the naming shape was never the
  evidence, and re-deriving membership before collapsing is what stopped the collapse from dropping
  the assertions the shape concealed.
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
enforced. Plan `010` retired that figure and made the 400-line budget enforced at `severity: warning`.

**B1 is the epic's one structural rule and the one nobody reached.** `010` landed the detector over a
tree carrying **315** violations; after four reduction plans the count is **313** — both leads,
re-derive them. Every reduction plan sequenced its split deliverable last, for the sound reason that
fixture hoisting changes which modules are over budget, and every run ran out of budget before
reaching it. **The split is therefore no longer a reduction plan's deliverable at all**: plan `100`
owns it as a campaign across all six slices, one slice per run, measured against the budget rather
than against a line target. A reduction plan reports its over-budget count and does not act on it.

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
than derived, so it stays a single command with no shell substitution — which the lane's
one-command-per-Bash-call discipline requires, and which is why this is not derived from
`_setup_marketplace_pythonpath` at run time even though that function is the authority.

**The five directories are a lead like any other, and the failure is loud rather than silent.** If the
import chain has grown a sixth, the command dies with `ModuleNotFoundError: No module named '<name>'`,
which **names the missing module** — resolve it to its scripts directory, add that directory to the
prefix, and say so in the report so the next run inherits it. A run that hits this has not lost a
measurement; it has been handed the fix by the error message. What it must not do is silently
substitute a weaker check. If the command cannot be made to run at all, the
measurement is genuinely **unavailable**: report it as such rather than substituting a weaker check.

## What a reduction run must hold

Every reduction run holds the same **five** conditions. The first four are gates; the fifth is a
measurement that is reported rather than targeted.

1. **Collected test count does not decrease.** Measured as pytest's own collected-item count for the
   subtree, before and after. Parametrizing raises it; deleting a case lowers it. This is the guard
   that separates simplification from deletion.
2. **Coverage does not decrease** for the bundle paths the subtree exercises.
3. **The skipped count does not rise.** Measured whole-tree from pytest's own summary, before and
   after. A test converted into a skip is a contract that stopped being checked while the build kept
   reporting success.
4. **The suite does not get slower.** Measured whole-tree, before and after, **with the same command
   and the same scope in both measurements, and the population named**. A `pytest` wall-clock is not
   comparable to a `./pw verify` total — that one also runs the quality gate and the test-compile step
   — and neither is comparable to a figure taken on a different machine. Record the slowest tests
   (`--durations`) alongside, so a regression can be attributed and not merely noticed.
5. **The line delta is measured and reported.** Not targeted. See below.

Conditions 3 and 4 were added after the epic's executed half, and plan `110` builds the instruments,
the exact commands and the exception list they rely on. Until it lands, a run states the two figures
and names how it took them.

⛔ **These five conditions supersede the three-part done-when written into plans `030`–`060`.** Those
four plans landed carrying *"the three-part done-when — all three must hold"* with a percentage line
floor as its third gate. **A run re-entering a landed plan holds the five conditions above, not that
plan's three**, and in particular does not treat its line floor as a gate — § "Why there is no line
floor" is why. The landed plan files each carry a pointer to this section; where one of them and this
section disagree, this section governs and the run reports the disagreement.

### Why there is no line floor

Each of `030`–`060` carried a percentage line floor, and every one of them missed it by more than an
order of magnitude. That is not four runs underperforming; it is a target derived from an impression
of the corpus rather than from its composition. Each of the four measured its own slice and
recommended re-deriving the floors — for the remaining plans as well as its own — and the arithmetic
is decisive:

| Slice | Floor carried | Achieved | Lines | Prose share | What the floor demanded |
|---|---:|---:|---:|---:|---|
| `030` config and manifest | 30% | **2.56%** | ~53,100 | 26.3% | more than all of its prose |
| `040` delivery pipeline | 25% | **0.581%** | ~66,600 | 27.4% | ~91% of every comment and docstring |
| `050` plan state and records | 20% | **0.52%** | ~83,800 | 23.9% | ~84% of every comment and docstring |
| `060` runtime and script substrate | 25% | **0.72%** | ~61,500 | 23.5% | more than all of its prose; its mean test is already 11.7 lines, inside **B2** |
| `070` architecture and orchestration | 20% (retired) | — | ~63,200 | 23.3% | ~86% of every comment and docstring |
| `080` plugin development and generator | 25% (retired) | — | ~60,400 | 22.2% | more than all of its prose |

**Three of the six floors exceed the slice's entire comment-and-docstring volume**, so deleting every
last one would still fall short. Every figure is a lead — re-derive before acting — and the
populations differ. The `030`, `050`, `070` and `080` figures were measured at `main` — the first two
*after* those plans landed, the last two before they start. `040`'s line total is its own report's
pre-change baseline. `060`'s is its report's **post**-change total over the **fifteen** directories it
worked (its plan's fourteen plus `test/pm-code-intelligence/`, which this brief now assigns to `080`),
so the `060` and `080` rows overlap by that directory's ~260 lines. The conclusion does not depend on
any of that: re-measured at `main` today, 25% of `060`'s slice is still larger than all of its prose.

A floor that can only be met by deleting prose collides head-on with **B3**, which says the
*rationale* stays and only the *citation* goes — and plan `040`'s cold read found four of ten
rewritten docstrings from which a maintainer could no longer recover why the contract matters, every
one of them because the rewrite chased the number.

So a run **reports** its line delta and does not chase it. A large delta is a good outcome; a small
one is not a failure; and a delta bought by deleting an assertion, a rationale, or a comment is a
failed run whatever the number says. The corpus review this epic was scoped from said it first, and it
still governs: **the problem is not what the tests assert — it is how much text it takes them to
assert it**, and any plan that deletes an assertion to hit a line target has failed, not succeeded.

### How much one run does

Across the epic's executed half, a cloud run completed roughly **two to three code deliverables**.
Read from the four reports' own verdict tables: `030` left D2 and D3 unstarted, `040` left D2, D3, D4
and half of D5, `050` left D4 unstarted with D2, D3 and D5 partial, and `060` left D2 unstarted with
D3 and D4 partial. Three of the four needed a second or third run to close what the first recorded. That is the planning unit, not a
disappointment: a plan carrying six code deliverables is a plan whose tail does not happen. Author to
it, and where a run cannot finish, **report what was not reached rather than thinning what was**.

## The plans, and what may run at the same time

```text
010 standards + enforcement ─┐          ┌─ 030  config & manifest          ─┐   [landed]
                             ├─→ landed ┤  040  delivery pipeline            │  [landed]
020 shared harness         ──┘          │  050  plan state & records         ├─ mutually parallel
                                        │  060  runtime & script substrate   │  [landed]
                                        │  070  architecture & orchestration │
                                        └─ 080  plugin-development & generator ─┘

090 harness & rule gaps ──→ unblocks the B6/B7 halves of 070 and 080 (see the collision matrix)
100 module-budget campaign ──→ one slice per run; takes 070's and 080's slices after they land
110 every test runs, no slowdown ──→ builds the instruments conditions 3 and 4 rely on
120 derive the cross-file sets ──→ computes the partition, the matrix and the attribution, and
                                   fails when a document disagrees; land it early
```

| Plan | Surface | May run concurrently with |
|---|---|---|
| `010` | `marketplace/bundles/pm-dev-python/skills/pytest-testing/**`, `marketplace/bundles/plan-marshall/skills/persona-module-tester/**`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**`, `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py`, `test/pm-plugin-development/plugin-doctor/fixtures/test_conventions/rule*/`, `test/pm-plugin-development/plugin-doctor/test_doctor_marketplace_commands.py` (the `cmd_test_conventions` cases only), `test/pm-plugin-development/plugin-doctor/_fixtures.py` | `020` only |
| `020` | `test/conftest.py`, `test/_shared/**`, `test/README.md`, and the ≤10 modules it converts as proof-of-use | `010` only |
| `030`–`080` | one disjoint slice of `test/` each, listed in the plan | each other, once `010` **and** `020` have landed |
| `090` | `marketplace/bundles/**` (the doctor analyzers, `script-shared`, `manage-providers`) — **the only plan in the epic that may edit it** — plus `test/conftest.py`'s loader mechanics, and the tests for its own production changes | see § "The collision matrix" — it is the authoritative set, and this cell deliberately does not restate it |
| `100` | one reduction slice per run, `test_*.py` only — plus a seventh run for the one over-budget module plan `010` owns, which no reduction slice covers | nothing running against the same slice; and see § "The collision matrix" for the runs that additionally collide with `090` |
| `120` | repository tooling only — the checker and its tests. It **reads** every plan document and the test tree and writes neither | anything; it shares no surface with any plan in the epic |
| `110` | the tree's skip sites, which **cross** several slices — `test/sync-plugin-cache/`, `test/pm-plugin-development/`, `test/marketplace/` and scattered others — plus `test/conftest.py`'s session preflight and skip guard | nothing running against those directories; see § "The collision matrix" for `090` |

**`090`, `100`, `110` and `120` were added after the epic's executed half**, each from something the
executed runs recorded and none could act on: `090` owns the production and harness defects every reduction plan is
forbidden to fix, `100` owns the module-budget split none of them reached, and `110` owns the two run
conditions none of them measured. `090` should land before `070` and `080` start; `100` takes their
slices only after they land; `110` is best run before all three, because they are what it exists to
watch. **`120` should land earliest of all** — it checks the documents every other plan is executed
from, and eight verification rounds established that nothing else does.

**`010` and `020` are blocking.** The reduction plans consume the harness `020` builds and the style
`010` writes; run either reduction wave before them and it will invent its own harness, which is the
duplication this epic exists to remove.

**`010` and `020` may run concurrently with each other** — their surfaces are disjoint (`010` touches
`marketplace/bundles/**` plus one plugin-doctor test module; `020` touches `test/conftest.py`,
`test/_shared/`, and `test/README.md`).

**`030`–`080` are mutually parallel by construction.** Each owns a disjoint list of `test/`
subdirectories, stated in its Expected surface.

## The collision matrix

⛔ **This table is the ONLY statement in the epic of which plans may not run at the same time.** No
other file enumerates it — `070`, `080`, `090`, `100`, `110`, the plan graph above and the exclusion
table below all point here and say nothing of their own. That is a construction rule, not an
aspiration: the same collision was corrected in one file and left wrong in another across five
verification rounds, and a sixth round that merely *declared* one table authoritative while leaving
five enumerations live was found to have moved the defect rather than removed it.

**If you are about to write "must not run concurrently" anywhere else in this epic, add a row here
instead.**

| A | B | Shared path, and who owns it | Why they collide |
|---|---|---|---|
| `090` | `080` | `plugin-doctor/test_analyze_lesson_id_in_skill_prose.py` — `080`'s | `090` § D5 amends the rule that module tests; `080` owns the module |
| `090` | `110` | `test/conftest.py` — `020`'s, then shared | `090` owns its loader mechanics, `110` its session preflight and skip guard |
| `090` | `100` run 3 | `test/plan-marshall/script-shared/`, `…/manage-providers/` — `060`'s | `090` § D1 adds parser seams and their tests there; run 3 splits that slice |
| `090` | `100` run 6 | `plugin-doctor/test_analyze_lesson_id_in_skill_prose.py` — `080`'s | Same module as row 1: `090` § D5 amends its cases, run 6 splits it (1,020 lines, over budget) |
| `090` | `100` run 7 | `plugin-doctor/test_test_conventions_rule*.py` — `010`'s | `090` § D4 amends the rule whose tests live in `rule6.py`; run 7 splits that same module |
| `110` | `040` | `phase-6-finalize/`, `workflow-integration-git/`, `workflow-integration-github/` — `040`'s | `110` D1–D5 rewrite skip sites in all three |
| `110` | `060` | `lsp-client/`, `platform-runtime/` — `060`'s | `110` D5's in-process stub and D1's scattered sites are written there |
| `110` | `070` | `build-server/` — `070`'s | `110` records that skip as a platform exception; it does not write it, so this is the weakest row in the table — but the file is shared |
| `110` | `080` | `test/sync-plugin-cache/`, `test/pm-plugin-development/`, `test/marketplace/` — `080`'s | Most of the tree's skip sites are inside `080`'s slice |
| `110` | `100` | whichever slice `100` is running | `110`'s skip sites cross every slice, so any campaign run may meet them |

⚠️ **This table is about CONCURRENT EDITING, not about ordering.** Blocking dependencies — `010` and
`020` before every reduction plan, `090` before `070` and `080`'s **B6**/**B7** halves, `070`/`080`
before `100`'s runs 5 and 6 — are stated in § "The plans, and what may run at the same time" and in
each plan's own blocking-dependency note. A pair absent from this table may run at the same time **if
its ordering constraints are met**; the two questions are separate.

⛔ **This table is hand-maintained and nothing derives or checks it — plan `120` is the fix.** Eight verification rounds and
three automated reviews all reached the same conclusion: an ownership set held in prose, with no
derivation and no check, drifts — and three successive attempts to fix that by restructuring the prose
each reproduced the drift inside their own commit. **Treat every row as a lead**: before acting on it,
read the two plans' own Expected surfaces and confirm the shared path is still shared. The residue
**Plan `120` computes this table from the plans' own Expected surfaces and fails when this document
disagrees with it**; until it lands, every row here is a lead.

**How to use it.** Before starting, find your plan in either column. For every row that names it,
confirm no open PR and no in-flight branch exists for the other party — and **halt and report** rather
than editing a file two plans own. `100` states the applicable row per campaign run in its own slice
table's *Depends on* column, as a reference to this table rather than as a restatement of it.

## The partition, and how a run re-derives it

⚠️ **The partition is a hand-written list, so every run re-derives it before acting on it.** The
lists below cover every directory present when they were last reconciled, but a directory added to
`test/` between that reconciliation and a run belongs to **no** plan and would be silently skipped,
with nothing positioned to notice. That is not hypothetical: `test/pm-code-intelligence/` was added
mid-epic and **four consecutive runs each halted on it**, escalated, and were told to proceed — the
same defect, found and dispositioned four times, because the disposition was about that run rather
than about the partition. It is assigned in the exclusion list below. Each reduction plan carries this
as a **gating, halting derivation**, run before its first deliverable:

1. List every directory under `test/plan-marshall/*/`, **every file at the root of
   `test/plan-marshall/`**, and every top-level entry under `test/` **other than `plan-marshall/`
   itself** — that one is decomposed by the first two clauses, so listing it as well would report it
   unclaimed and halt on a non-defect. Skip `__pycache__` wherever it appears: it is git-ignored and
   absent from a fresh clone. The root-level files are not an afterthought either: they are
   exactly the category a slice boundary is most likely to mis-assign, since they sit in one plan's
   tree while being imported from another's.
2. Confirm each appears in **exactly one** of `030`–`080`'s Expected surface, allowing for the
   deliberate exclusions in the table below and no others. Anything not in that table and not in
   exactly one plan's surface is a defect.

   | Excluded entry | Why |
   |---|---|
   | `test/conftest.py` | Plan `020`'s, then shared by `090` (loader mechanics) and `110` (session preflight, skip guard); see § "The collision matrix". Consumed read-only by every reduction plan |
   | `test/_shared/**` | Plan `020`'s, same reason |
   | `test/README.md` | Plan `020`'s D4 deliverable; not a `.py` file |
   | `test/test_shared_harness.py` | Plan `020`'s D5 deliverable, created by its landing commit |
   | `test/fixtures/` | Holds no `.py` |
   | `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` | Plan `010`'s — it ships the tests for the rules it added, and plan `080`'s Expected surface excludes the glob explicitly. **Not unowned**: the one module of the set that is over budget is plan `100`'s campaign row 7. Without this row the partition gate halts on a known, assigned entry |

   ⚠️ **`test/pm-code-intelligence/` is NOT an exclusion — it belongs to plan `080`'s slice**, and
   `080`'s Expected surface names it. It is a `pm-*` bundle test directory, which is the shape `080`
   already owns; the assignment is recorded here so the next run does not re-derive the halt a fourth
   time. Its one open finding — a preamble the shared loader cannot address, because the file it loads
   is a bundle skill's root-level `extension.py` rather than a `scripts/` module — is **plan `090` §
   D2's**, not `080`'s.
3. An entry in **two** lists, or in **none**, is a partition defect: **halt and report it** rather
   than claiming or skipping it unilaterally. An entry claimed by no plan is the dangerous case,
   because it looks exactly like a clean run.

Independently, the six slices' line totals must sum to the corpus total **minus the excluded entries
above** — `wc -l $(find test -name 'test_*.py')` counts `test/test_shared_harness.py` and plan `010`'s
`test_test_conventions_rule*.py` modules, which no reduction slice claims. Subtract those before
comparing: a sum that still falls short means a gap, and one that exceeds it means an overlap. A raw
comparison against the unadjusted total reports a gap that is not one.

Three shared constraints keep the slices disjoint once the partition is confirmed, and every
reduction plan restates them:

* A reduction plan **never edits `test/conftest.py` or `test/_shared/**`**. If it needs a shared
  helper that `020` did not build, it adds it to its own subtree's `_{domain}_fixtures.py` and records
  the promotion as a proposal in its report.
* A reduction plan **never edits a `marketplace/bundles/**` file**. If it finds a production defect,
  it records it; it does not fix it. Test refactoring that changes production code is no longer test
  refactoring. **The defect then goes to plan `090`, which owns that surface** — recording a defect
  with no owner is how four runs each found the same blocker and none could close it.
* A reduction plan **never edits a directory outside its own list**, even to fix something obvious
  there. The neighbouring directory belongs to a concurrently-running sibling.

One narrow carve-out, because two plans would otherwise collide: plan `010` owns every module matched
by `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` — the modules that
already test this scope's rules plus the ones it added — their fixture directories under
`fixtures/test_conventions/rule*/`, the `cmd_test_conventions` cases in
`test_doctor_marketplace_commands.py`, and the `_fixtures.py` corpus entries that make its rules fire
(it ships the tests for the rules it adds). **Match the glob against the tree rather than assuming
which numbers exist**: `010` split its own new tests by behaviour cluster while landing, so the set is
not a contiguous run. Plan `080` owns the rest of `test/pm-plugin-development/**` and excludes those
modules explicitly; plan `090` may amend the rules themselves, and plan `100`'s seventh campaign run
splits the one of them that is over budget. **Which of those may run at the same time is stated in
§ "The collision matrix" and nowhere else** — `080` excludes the glob outright, which is the stronger
guarantee for a plan that never edits them at all.

## Where a recorded finding goes

Every reduction plan records defects it may not fix. Until `090`, `100` and `110` existed, those
records had no owner and accumulated across four runs. They do now, and a run that finds one of these
shapes names the owning plan rather than only the defect:

| Shape of the finding | Owner |
|---|---|
| A `marketplace/bundles/**` production defect — a missing parser seam, an analyzer that mis-matches, a rule whose message names an inapplicable remedy | `090` |
| A `test/conftest.py` or `test/_shared/**` gap — the loader cannot address a file, a helper needs widening, a shared registration needs a guard | `090` |
| A module over the 400-line budget | `100` |
| A test that skips, or a change that makes the suite slower | `110` |
| A promotion candidate for the shared harness — a helper three or more slices would want | `090`, as a proposal in the report first |
| Anything inside the run's own slice | the run itself |
| A document in this epic disagreeing with another about ownership, collisions or the partition | `120` — and once it lands, that disagreement is a red build rather than a finding |

Two items remain **unowned by design**, both recorded rather than assigned because each needs a
decision this epic does not carry: populating the `identifier-validator-corpus` registry, which is a
coverage decision about which production validators the corpus should cover; and the
`broken-relative-link` rule validating a link's file half but not its fragment, which is a new
analyzer capability rather than a widening. Plan `090` § Out of scope states both and why.

### What the executed half left open

`030`–`060` have landed. Each left deliverables unreached and recorded them in its own report's
§ Residue, which is the authoritative account — this index exists so a follow-up run can be
commissioned without reading six reports first, not to replace them. **Every figure here is a lead
taken from the report that recorded it; re-derive before acting.**

| Plan | Still open in its own slice | Now owned elsewhere |
|---|---|---|
| `030` config and manifest (39 over budget) | D3 arrange-into-fixtures, unstarted — the `monkeypatch.setattr`-to-`@pytest.fixture` ratio is untouched, and its `parse_ns` exception list is **empty by non-attempt, not by finding none**. D1's body-shape residue needs re-specifying before anyone attempts it | Its over-budget modules → `100`; the shared-registration guard its reviewer asked for → `090` § D3 |
| `040` delivery pipeline (55 over budget) | D2 fixture corpus, unstarted. D3 subprocess-layer collapse, **not performed at all** — its gating survey ran and licensed no collapse, so ~124 `run_script` sites remain unpaired. D5's `parse_ns` half unstarted against ~391 `Namespace(` sites. A `fixtures/ci-wait/README.md` carrying a plan slug, a lesson id and a dated line | Its over-budget modules → `100`; the ~92 prose citations in shapes the rule does not match → `090` § D4 |
| `050` plan state and records (60 over budget) | D2's remaining namespace builders; D3's five directories with no fixture module; D5's parametrization half, unstarted. Three findings its second run rejected as new scope with reasons recorded | Its over-budget modules → `100` |
| `060` runtime and script substrate (53 over budget) | D4 parametrization beyond one family — ~223 families at ≥80% skeleton similarity, each needing a read because the set includes matched control pairs that must **not** collapse. D4's required cold read, never performed. The randomised hermeticity arm, unrun | Its over-budget modules → `100`, with the bound that exactly one class exceeds the budget alone; 3 latent `sys.modules` registrations → `090` § D3; the structurally-unfixable preambles it found → `090` § D2, **whose instance set that plan derives rather than takes from any count** — `060`'s figure is scoped to the fifteen directories it worked, one of which this brief now assigns to `080`; 27 seam-blocked `parse_ns` sites → `090` § D1 |

A follow-up run against a landed plan re-enters it exactly as `030`, `050` and `060` already did — a
new report ordinal in the same plan directory, and the plan's deliverables unchanged. Its
**Verification** section is the one part that has moved: each of the four now opens with a pointer to
the five conditions above, because the line floor each was written with is retired. What a follow-up
run must not do is treat an unstarted deliverable as satisfied: `030`'s own report says it plainest, that an empty
exception list produced by not attempting the sweep *"tells the operator nothing"* and must not be
read as a clean result.
