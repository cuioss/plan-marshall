# Findings — Python test-corpus review

The analysis the `test-quality` epic was scoped from. This document is the **evidence**; the epic's
[`README.md`](README.md) is the scoping brief that turns it into rules, and the eight numbered plans
are the remediation. Where a finding names a rule (**B1**–**B10**) or a slice, those are defined
there and are not restated here.

Every figure is a **lead, not a fact** — measured on one clone at one moment, with the command that
re-derives it. They drift: several figures here moved by a few counts between the review and this
write-up, because unrelated work landed on `main` in between. That is the reason for the
re-derivation commands, and the reason no plan in this epic acts on a number without recomputing
it first. The census table in [`README.md`](README.md) § The census carries the full set; this
document repeats a figure only where a finding turns on it.

## Scope and method — read this before weighing anything below

The corpus is ~770 `test_*.py` modules and ~377,000 lines. **It was not read exhaustively, module by
module.** Claiming otherwise would be the same class of overstatement several of these findings are
about, so the actual method is stated plainly:

* **Whole-corpus, mechanical.** Every quantitative claim below is a tree-wide measurement — file-size
  distribution, declaration counts, idiom frequencies, prose markers. These cover 100% of the corpus
  and are re-derivable from the commands given.
* **Read individually, in full or in substantial part.** Roughly forty modules, chosen to span every
  bundle and both extremes of the size distribution: the shared infrastructure (`test/conftest.py`
  end to end, `test/test_conftest_discipline.py`, the `test/_shared/` helpers), the largest modules in
  each slice, and a deliberate sample of small, well-formed ones to calibrate what "good" looks like
  here rather than against an external ideal.
* **Structurally surveyed.** Class and function inventories, module preambles, and fixture surfaces
  for a much wider set — enough to establish that a pattern found in the read sample recurs, without
  claiming to have read every instance of it.

**What this supports and what it does not.** The quantitative findings are strong: they are census
measurements, not extrapolations. The qualitative findings — that the tests are behavioural, that the
prose is the bulk of the excess, that specific modules are the right exemplars — rest on the read
sample and are labelled where a specific module is named. **What this method cannot support is a
claim that no bad test exists anywhere in the corpus.** It can support the inverse, which is the
finding that matters: the corpus is not *characteristically* bad, and its excess is not
characteristically missing assertions.

## The verdict, up front

**The tests are not the problem. The volume of text around them is.**

The prompt this review answered anticipated a corpus padded with coverage-only tests. That is not what
is there:

| Probe | Result | Command |
|---|---|---|
| Tautological assertions (`assert True`, `assert 1 == …`) | ~20 tree-wide | `grep -rn 'assert True\|assert 1 ==' test --include=test_*.py` |
| Bare `assert result is not None` as the only assertion | ~194 occurrences, almost all followed by substantive assertions | `grep -rn 'assert result is not None$' test --include=test_*.py` |
| `assert` lines overall | ~43,000 (11% of all lines) | `grep -rh '^\s*assert ' test --include=test_*.py` |

Individually the tests name real contracts. Several subtrees carry deliberate positive/negative
control pairs, population assertions that refuse to pass vacuously, and matched-pair fixtures whose
module docstrings state that deleting either arm voids the other's evidentiary value. That is better
than average practice, and a naive line-reduction pass would destroy it.

**The consequence for remediation is the epic's central constraint:** a plan that deletes an assertion
to hit a line target has failed, not succeeded. Every reduction plan therefore gates on an unchanged
collected-test count and unchanged coverage *before* its line floor.

---

## Findings

### F1 — Two thirds of the corpus lives in modules nobody can navigate

~40% of modules exceed 400 lines and hold **~73% of all lines**; ~74 exceed 1,000. The median module
is ~323 lines. Re-derive by sorting `wc -l $(find test -name 'test_*.py')`.

The extreme case is `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_checks.py`:
**~8,700 lines, ~90 test classes**, covering roughly two dozen *independent* audit checks — name
drift, dormation, token economics, quality chain, exploration share, input integrity, cross-check
synthesis, and more. Each check brings its own fixture builders, defined inline at first use. The
tests are good; the file is twenty-four modules wearing one filename.

**Impact.** Navigability, not correctness. But it compounds every other finding: a fixture defined
mid-file at line 2,280 is invisible to the sibling module that needs it, so the sibling writes its
own.

### F2 — The corpus's own module-size standard is violated by three quarters of it

`plan-marshall:persona-module-tester` § "Splitting Large Test Files" instructs authors to split above
**~200 lines**. Roughly 75% of modules exceed that, and no guard has ever enforced it.

**Impact.** This is worse than having no standard. A rule the tree violates at that rate is a number
readers learn to skip, and its presence makes the *absence* of an enforced budget look like an
oversight rather than a decision. Remediation replaces it with a budget derived from the corpus's own
median (**B1**), enforced mechanically.

### F3 — Parametrization is the corpus's least-used tool, against its most tabular content

Only ~179 of 770 modules use `@pytest.mark.parametrize`; ~497 decorators across ~17,600 test
declarations.

The clearest instance is `test/plan-marshall/manage-config/test_config_defaults.py` — ~3,990 lines for
~202 tests. Twenty-two functions share the naming shape
`test_default_plan_finalize_includes_{knob}` / `test_get_default_config_includes_{knob}`, each
reaching its knob through the same `_params_for(steps, step_id)` accessor and each carrying its own
multi-paragraph docstring.

> **A correction worth recording, because it changed the remediation.** This was first characterised
> as ~11 clean pairs asserting the same default twice. It is not. The two prefixes cover *different*
> knob sets — ~7 functions under the first, ~15 under the second — and **only three knobs**
> (`admin_merge_on_stuck_state`, `auto_rebase_threshold`, `merge_queue_wait_budget_seconds`) are
> genuinely crossed against both accessors. Several of the remainder assert entirely unrelated
> subjects. Re-derive by extracting the knob suffix under each prefix separately and intersecting;
> a single grep returning the count 22 does **not** establish pairing. Plan `030` D1 now derives the
> family's real membership before collapsing anything.

`test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_compose.py` (~5,400
lines) is the other exemplar: its own section comment names its subject as "table-driven cases — one
per row of the matrix", and it then writes each row as a separate function.

**Impact.** The single largest available reduction, and the one that *strengthens* the suite —
parametrizing raises the collected-test count while lowering the line count.

### F4 — Hand-built argument namespaces are a correctness defect, not just bloat

~2,900 `argparse.Namespace(...)` constructions across ~292 modules, plus ~150 modules defining their
own private `_ns_*` builder. `test/plan-marshall/manage-metrics/test_manage_metrics.py` opens with
five of them, one per subcommand.

A hand-built namespace carries only the attributes the author remembered — **not the parser's
defaults**. So a flag added to a production script with a default breaks production while every one
of those namespaces keeps passing. The suite cannot see the change it exists to catch.

**This is the corpus's most consequential finding**, and the only one that is a live correctness risk
rather than a maintenance cost. It is also already covered in principle: `persona-module-tester`
§ "Foundation utilities — tests against the CLI" states exactly this rule for the CLI layer. Nothing
carries it down to the namespace layer, and no shared helper makes compliance cheap.

### F5 — Arrange logic is inlined roughly eleven times more often than it is fixtured

~2,397 `monkeypatch.setattr` calls against ~221 `@pytest.fixture` declarations.

`test/plan-marshall/platform-runtime/test_claude_runtime.py` shows the shape: it declares an `rt`
fixture that redirects three module-level roots, and then several of its ~40 classes re-declare
`monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")` **inside every
individual test** — because the class needs the redirect without needing the runtime instance. That
line appears 8 times in that module and 16 more in its sibling.

**Impact.** This is a missing class-scoped fixture, repeated. Note the constraint on fixing it:
`persona-module-tester` § "Compose Isolation, Don't Impose It" specifically forbids converting such
redirects into blanket `autouse` fixtures, because tests that stage their own version of the
redirected resource then break. The remediation is explicit fixtures at the narrowest serving scope,
not a tree-wide default.

### F6 — ~197 modules re-implement a loader `conftest.py` already exports

`conftest.load_script_module(bundle, skill, script)` resolves a script by identity and needs no path
arithmetic. ~404 call sites use it. Another ~197 open with a raw `spec_from_file_location` block or a
`Path(__file__).parent.parent.parent.parent` chain instead — often as a private `_load_module` with
per-module aliases.

`test_config_defaults.py` is the worked case: it computes the scripts directory by hand, defines its
own `_load_module`, and loads **seven** modules under bespoke aliases.

**Impact.** Pure duplication, and brittle: path arithmetic breaks when a module moves, whereas
identity-based resolution does not.

### F7 — Several thousand lines of test prose are history, which this repository forbids everywhere else

Test docstrings routinely run eight to fifteen lines and are frequently longer than the bodies they
document. A large share is narrative, not invariant: which defect the test is named after, what the
code "once derived", what "the fix" now does, which plan or PR changed it.

| Marker class | Lines | Command |
|---|---|---|
| Superseded-behaviour narration | ~974 | `grep -rn 'once derived\|used to \|previously\|no longer\|the old \|legacy ' test --include=test_*.py` |
| Incident / lesson / PR citations | ~393 | `grep -rn 'lesson-20\|LESSON-\|PR #[0-9]' test --include=test_*.py` |
| Plan / deliverable ids | ~1,335 | `grep -rn 'deliverable\|D[0-9] —\|this plan' test --include=test_*.py` |

Those are matching *lines*, not surrounding paragraphs, so they understate the volume.

This is not a new rule being invented. `CLAUDE.md` § Documentation Standards already forbids it ("No
version history", "Current state only"), and `plugin-doctor` already lints it out of
`marketplace/bundles/**` through three rules — `historical-prose-in-skills`,
`incident-reference-in-docs`, `lesson-id-in-skill-prose`. **None has ever been scoped over `test/`.**

**Impact, and the risk in fixing it.** This is the largest single reduction available in the
scenario-heavy slices. It is also the most dangerous, because the rationale worth *keeping* — why an
invariant is load-bearing — sits in the same docstrings as the history worth removing. Every plan
that performs this rewrite therefore carries a mandatory cold read: an independent reader takes the
rewritten modules with no other context and states what contract each test pins and why it matters. A
test whose docstring can no longer answer both has been over-stripped.

### F8 — One shared fixture is defined three times, incompatibly

`create_marshal_json` exists in three places with three different signatures, against ~231 call sites:

| Definition | Signature |
|---|---|
| `test/conftest.py` | `(base_dir, skill_domains=None, extra=None)` |
| `test/plan-marshall/manage-config/test_helpers.py` | `(fixture_dir, config=None)` |
| `test/plan-marshall/phase-6-finalize/test_triage_extension.py` | `(fixture_dir, config)` |

Which one a module gets depends on which it imported. The defaults differ too — `conftest`'s
`MARSHAL_SCHEMA_DEFAULT` and `test_helpers`' java-flavoured default are not the same config — so a
test's baseline is decided by an import line rather than by intent.

### F9 — Two silent defects the tooling cannot see

* **`test/plan-marshall/manage-config/test_helpers.py`** — 223 lines, **zero test functions**,
  imported by ~23 modules, and named `test_*.py`. pytest collects it, finds nothing, and the module is
  invisible in the run. It is also a bare-name collision hazard resolved by pytest's rootdir-based
  import. The existing `unique-fixture-basenames` doctor rule cannot see it, because that rule
  enumerates only `_`-prefixed files.
* **`test/plan-marshall/build_test_helpers.py`** and **`discovery_test_helpers.py`** — root-level
  helper modules with no underscore prefix, invisible to the same rule for the same reason.
* **`test/README.md`** — referenced by `test/conftest.py`'s own module docstring, and does not exist.

### F10 — One contract, asserted at two layers

~1,196 `run_script(` subprocess calls across ~197 modules. In several modules these re-assert
behaviour an in-process test in the same file already covers — a second full assertion surface to
maintain for one contract, at subprocess cost.

**Impact, with a caveat that bounds the fix.** The reduction is real but the deletion risk is high:
subprocess coverage is legitimate and irreplaceable where it is the *only* coverage, and where the
subprocess boundary is itself the subject (environment propagation, exit-code contracts,
stdout/stderr separation). The remediation requires every collapse to name the in-process test that
now carries the contract, and forbids the collected count from dropping.

---

## What is genuinely good, and must survive

A review that only lists defects would mislead the plans that act on it. These patterns are better
than average and several are load-bearing:

* **`test/conftest.py` is a serious piece of infrastructure** — identity-based module loading, four
  autouse isolation sandboxes, a cwd-leak guard that fails loudly rather than restoring silently, and
  pollution guards whose traversal cost is deliberately bounded to the test's own footprint.
* **Population-asserting guards.** `test/marketplace/test_prefix_strip_idiom_retired.py` asserts its
  scan population is non-empty *before* asserting the offender list is empty — refusing to pass
  vacuously — and pairs positive controls that prove the detector fires with a negative control that
  proves it does not over-fire. This is the model the plans cite for every new whole-tree guard.
* **Matched positive/negative control pairs** under `test/plan-marshall/script-shared/`, pinning the
  autouse neutralization fixtures, with module docstrings recording that each arm is evidence only in
  contrast with the other.
* **`test/pm-plugin-development/plugin-doctor/_fixtures.py`** — a shared fixture corpus plus an
  `assert_analyzer_findings` scaffold that makes per-rule modules assert *which* rules fired rather
  than how many findings came back. This is the architecture the other five slices are converging
  toward; it already exists here and works.
* **A hermeticity apparatus that takes machine-global state seriously** — the daemon-routing
  neutralization carved out by location rather than by a registry, so a module added to the owning
  directory inherits the carve-out with nothing to forget to update.

## Judgement: property-based testing, and where the standards are wrong

**Hypothesis has zero adoption** (`grep -rn 'hypothesis' test --include=*.py` returns one unrelated
prose match), despite `pm-dev-python:pytest-testing` documenting it correctly.

**It is worth adding, narrowly.** The domain is text and format parsers, identifier validators, path
normalisers, and round-trip encoders — contracts genuinely expressible as "for all valid inputs, P
holds". `marketplace/targets/opencode/frontmatter.py`'s `parse_frontmatter` is the clearest case: a
text parser tested with roughly eight hand-picked strings covering unterminated fences, embedded
`---`, list flattening, and missing trailing newlines. That is an enumeration of the cases the author
thought of, and the enumeration is the weakness.

**It would be actively wrong almost everywhere else in this corpus.** A test asserting that
`default:branch-cleanup` seeds `merge_queue_wait_budget_seconds: 1800` is asserting an exact contract
value; a generator there asserts nothing at all.

That distinction exposes a real defect in the governing standard. `persona-module-tester` § "Test Data
Principles" states, without domain scoping, that tests "should use generated/random data" and lists
"arbitrary hardcoded data" under Anti-Patterns. **In the majority case for this corpus, that tells an
author to do the wrong thing** — while the technique that would genuinely help has no adoption at all.
The remediation scopes the preference by whether the contract is universal or the literal *is* the
contract (**B8**), rather than removing it.

`hypothesis` is a third-party dependency, so adding it is a user-approval step. The plans therefore
**derive and record the candidate call sites** and stop there; they do not add the dependency.

## Remediation map

| Finding | Addressed by |
|---|---|
| F1, F2 | `010` (module budget + enforcement), `030`–`080` (splits) |
| F3 | `030` primarily; `050`, `060`, `070` for their tabular families |
| F4 | `020` (`parse_ns` helper), `010` (the rule), `030`–`080` (adoption) |
| F5 | `010` (thresholds), `060` primarily |
| F6 | `010` (the rule), `020` (harness), all reduction plans |
| F7 | `010` (rule + doctor lint), every reduction plan, each with a cold read |
| F8 | `020` (one builder, named presets) |
| F9 | `020` (renames, `test/README.md`), `010` (a doctor rule that catches the class) |
| F10 | `010` (the rule), `040` primarily |

## What this review did not examine

Stated so a later reader knows where the edges are:

* **Test *execution* characteristics** beyond what `pyproject.toml` records. The suite reportedly runs
  in ~2.5 minutes under `-n auto`; no independent timing, flakiness survey, or per-test cost analysis
  was performed. Runtime is not among the findings because it was not measured.
* **Coverage adequacy.** No judgement is offered on whether the corpus tests the *right* things, only
  on how it expresses what it tests. Gaps in coverage would need a different method entirely.
* **The non-Python surfaces.** Skill and workflow documents under `marketplace/bundles/**` have their
  own lint apparatus and were examined only where they govern test authoring.
* **Whether every one of the ~770 modules is behavioural.** See § Scope and method. The claim
  supported is that the corpus is not *characteristically* coverage-only; individual bad tests may
  exist and would be found by the per-slice work rather than by this survey.
