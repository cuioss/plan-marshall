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

# The test-authoring standards say the wrong thing, and nothing checks the right thing

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Read first.** The epic's scoping brief — the corpus census, the ten house-style rules this plan
> writes down, and the dependency graph — is `doc/plans/test-quality/README.md`, a git-tracked sibling
> present in your clone. Read it before D1. This plan is the authority for *what changes*; that file
> explains *why these rules and not others*.

## Problem

Two skills govern how tests are written in this repository, and both are actively misleading about the
thing the corpus most needs help with.

`plan-marshall:persona-module-tester` — `standards/testing-methodology.md` § "Splitting Large Test
Files" — instructs authors to split a test file "when exceeding ~200 lines". Roughly three quarters of
the corpus's `test_*.py` modules exceed that, the median module is around 323 lines, and no guard has
ever enforced it. A rule that the tree violates at that rate is not a standard; it is a number a
reader learns to ignore, and its presence makes the *absence* of an enforced budget look like an
oversight rather than a decision.

The same file's § "Test Data Principles" states, without domain scoping, that tests "should use
generated/random data" and lists "arbitrary hardcoded data" as an anti-pattern. Most of this corpus
asserts exact structured contracts — a seeded config knob's default value, a canonical step id, a TOON
field name, an argparse flag spelling. For those, the literal *is* the contract and a generator would
assert nothing. The blanket phrasing tells an author to do the wrong thing in the majority case while
the genuinely valuable technique — property-based testing over parsers, validators, and round-trip
encoders — has **zero** adoption anywhere in the tree (`grep -rn 'hypothesis' test`).

`pm-dev-python:pytest-testing` — `standards/testing-pytest.md` — documents Hypothesis, parametrization,
fixtures, and the `_fixtures.py` helper-module convention correctly, but frames all of them as
available techniques rather than as the default. It says nothing about docstring content, nothing
about where arrange logic lives, and nothing about how command arguments are constructed. The corpus
answers all three by accident: ~2,900 hand-built `argparse.Namespace` objects that bypass the real
parser's defaults, ~2,397 `monkeypatch.setattr` calls against ~221 fixture declarations, and several
thousand lines of docstring narrating incidents, plan ids, and PR numbers inside test modules — the
exact class of prose that `CLAUDE.md` § Documentation Standards forbids and that `plugin-doctor`
already lints out of `marketplace/bundles/**`, but which no rule has ever been scoped over `test/`.

The enforcement surface for all of this already exists and is fully wired:
`pm-plugin-development:plugin-doctor` ships a `test-conventions` scope
(`scripts/_analyze_test_conventions.py`, `standards/doctor-test-conventions.md`, a registered
`doctor-marketplace test-conventions` subcommand) carrying three rules over the `test/` tree. Nothing
about the structural defects above is among them.

## Goal

The two governing skills state a house style that describes what a good module in this tree actually
looks like — a stated module budget, docstrings that carry the invariant and not its history,
fixtures and factories as the default home for arrange logic, parametrization as the default for
tabular cases, real-parser argument construction, and property-based testing scoped to the contracts
where it means something. The `plugin-doctor` `test-conventions` scope gains rules that catch the
structural half of that style mechanically, so the reduction plans that follow are measured against a
check rather than against a reviewer's memory.

## Deliverables

1. **D1 — Replace the module-split rule with a budget the tree can meet** — in
   `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`
   § "Test Class Organization". Retire the `~200 lines` figure. State a **400-line module budget** and
   the splitting taxonomy that goes with it: split by behaviour cluster into
   `test_{unit}_{cluster}.py`, never in arbitrary halves. State the derivation in one sentence — the
   budget is set above the corpus median so it describes the tree's own compliant majority rather than
   an aspiration — and state that the budget is enforced (D5), which the retired figure never was.
   *Done when:* the `~200 lines` figure appears nowhere in the file, the 400-line budget and the
   cluster-split taxonomy are stated, and the derivation sentence names the median as its basis.

2. **D2 — Scope the generated-data preference, and give property-based testing a domain** — in the
   same file, § "Test Data Principles" and § "Property-Based Testing", and in
   `marketplace/bundles/pm-dev-python/skills/pytest-testing/standards/testing-pytest.md`
   § "Property-Based and Adversarial Testing". State the discriminator explicitly: **generated data
   where the contract is universal** (text and format parsers, identifier validators, path
   normalisers, round-trip encoders, anything expressible as "for all valid inputs, P holds");
   **exact literals where the literal is the contract** (a seeded default value, a canonical step id,
   a serialized field name, an argparse flag spelling) — and in that second case a generator asserts
   nothing and is the defect, not the fix. Keep the existing exception list; it is subsumed, not
   contradicted.
   *Done when:* both files state the universal-contract / literal-is-the-contract discriminator, the
   "Forbidden Patterns" table entry for hardcoded data is qualified by it, and neither file can be
   read as a blanket preference for generated data.

3. **D3 — Write the docstring-content rule into both skills** — a test docstring states the invariant
   in the present tense; a second paragraph only where the invariant is genuinely non-obvious. It does
   not narrate the incident that produced the test, and it does not cite a plan id, a deliverable id,
   a PR number, a lesson id, or a superseded behaviour. Ground the rule where it comes from: this is
   `CLAUDE.md` § Documentation Standards ("No version history", "Current state only") applied to a
   tree those standards were never scoped over, and it is the same rule the existing `plugin-doctor`
   `historical-prose-in-skills` / `incident-reference-in-docs` / `lesson-id-in-skill-prose` rules
   enforce over `marketplace/bundles/**`. State what a docstring *should* carry in the non-obvious
   case — why the invariant is load-bearing, which is present-tense and survives an edit.
   *Done when:* both skills carry the rule with its grounding and with a worked before/after example
   drawn from a real module in this tree, and neither states it as a style preference.

4. **D4 — Write the arrange-placement, parametrization, argument-construction, test-budget and
   assertion-layer rules** — into `pm-dev-python:pytest-testing` § "Test Organization" (and the
   SKILL.md Quick Reference table). Six rules, each stated with the threshold that triggers it:
   * a literal repeated in **three or more** tests in a module becomes a module constant;
   * a setup sequence repeated in three or more tests becomes a fixture;
   * an object built in three or more tests becomes a factory with keyword overrides;
   * two tests differing only in input and expected output are one `@pytest.mark.parametrize` whose
     `ids=` carries what the docstrings said;
   * command arguments are built through the shared real-parser helper, never as a hand-written
     `argparse.Namespace` — because a hand-built namespace does not carry the parser's defaults, so a
     newly-added defaulted flag breaks production while the suite stays green. Cross-reference
     `persona-module-tester` § "Foundation utilities — tests against the CLI", which already states
     the principle for the CLI layer; this is the same principle at the namespace layer;
   * a **test function body over ~15 lines, excluding its docstring**, is carrying arrange logic that
     belongs in a fixture or a factory. State this as a **review trigger, not a build failure** —
     genuine scenario tests legitimately exceed it, and D5 ships no rule for it precisely because a
     mechanical line count cannot tell a scenario from a bloated unit.

   Additionally, into **both** skills, the **one-layer-per-contract** rule: where an in-process test
   and a subprocess test assert the same behaviour, the in-process test is authoritative and the
   subprocess coverage collapses to a single per-script CLI-plumbing smoke that proves the entry point
   wires up. State the two exceptions that keep it safe — do not collapse where the subprocess test is
   the *only* coverage, and do not collapse where the subprocess boundary is itself the subject
   (environment propagation, exit-code contracts, stdout/stderr separation) — and state that every
   collapse must name the in-process test that now carries the contract. Plans `030`–`080` all inherit
   this; without it in the skills, only the one plan that spells it out would apply it.
   *Done when:* all six rules plus the one-layer-per-contract rule are stated with their thresholds,
   the namespace rule names the defaults-bypass as its reason, the test-budget rule is explicitly a
   review trigger rather than a gate, the one-layer rule names both exceptions, and the SKILL.md Quick
   Reference table has a row for each.

5. **D5 — Add the structural rules to the `plugin-doctor` `test-conventions` scope** — implement in
   `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py`,
   document in the sibling `standards/doctor-test-conventions.md` (a `###` section per rule matching
   the three existing ones, plus a Severity Summary row), and register each in the module's
   `RuleDescriptor` list. Four rules, all at **`severity: warning`** — see D6 for why not `error`:
   * `test-module-line-budget` — a `test_*.py` module over 400 lines. The message carries the module's
     line count and the budget.
   * `test-helper-module-misnamed` — a module under the test tree matching pytest's collection
     patterns (`test_*.py` / `*_test.py`) that declares no test function or `Test*` class. Such a
     module is collected, contributes nothing, and is invisible in the run.
   * `test-module-preamble-boilerplate` — a `spec_from_file_location` call, or a
     `Path(__file__).parent` chain of depth three or more, in a module under the test tree. Both have
     a `conftest` helper (`load_script_module`, `get_scripts_dir`) that resolves by
     `(bundle, skill, script)` instead of by the test file's own location.
   * `test-docstring-historical-prose` — a docstring or comment under the test tree citing a lesson id,
     a `PR #` reference, or a deliverable/plan id. Reuse the detection shape the existing
     `incident-reference-in-docs` and `lesson-id-in-skill-prose` analyzers already use over
     `marketplace/bundles/**` rather than writing a second matcher.
   Ship the tests in `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule4.py` — a
   **new** module continuing the numbering of the three that already test this scope's existing rules
   (`test_test_conventions_rule1.py`, `rule2.py`, `rule3.py`), all four of which this plan owns. Give
   each rule a positive fixture that fires it and a negative control that does not.

   **The doctor has a provenance contract for new rules, and it applies here.**
   `references/rule-provenance.md` § "Provenance contract for new rules" requires, per rule: a
   corpus-feasibility check recording the legitimate-occurrence count for the pattern; a **positive
   unit test that actually fires the rule** (a rule firing on no positive test is presumed dead and
   must be dropped or justified — mechanically enforced by the suite-coverage invariant in
   `test_zero_match_suite_coverage.py`); a row in `references/rule-catalog.md`; a row in the
   `rule-provenance.md` table; and a source citation. Complete all five per rule. Note the tension the
   citation requirement creates with D3 — a citation may be a lesson id, and D3 forbids lesson ids in
   *test prose*, not in the doctor's own provenance table, which is where they belong. Do not resolve
   that by dropping the citation.

   ⚠️ **The zero-match invariant will fail this plan's own build gate unless you feed it.**
   `registered_rule_ids()` globs the analyzer modules, so the four new rules become registered the
   moment D5's emitter lands, and `test_zero_match_suite_coverage.py` then requires
   `registered − fired − EXEMPT == ∅`. Until they fire, **`./pw verify` — this plan's armed build gate
   — is red.**

   Add one **`FIXTURE_CORPUS` entry per new rule** in
   `test/pm-plugin-development/plugin-doctor/_fixtures.py`, exactly as the three existing
   test-conventions rules do. That file is therefore in this plan's Expected surface. Two things make
   this the right route rather than the `record_fired(...)` escape hatch that also lives there:

   * **`FIXTURE_CORPUS` is process-independent; `record_fired` is not.** `fired_rule_ids()` executes
     `build_fixture_corpus()` itself, in whichever process the meta-test runs in, so a corpus entry
     always fires. `record_fired` populates a module-level `_EXTRA_FIRED` set, and the canonical gate
     runs under `pytest-xdist` (`-n auto --dist=loadgroup`), so a rule recorded in one worker can be
     invisible to a meta-test collected in another. The cross-file precedent is not a
     counter-example: `fired_rule_ids()` re-derives those ids independently from
     `crossfile_verified_findings()` precisely "so the meta-test never depends on test ordering" —
     `record_fired` is belt-and-braces there, not the mechanism.
   * **Ordering against plan `080`, which renames that file.** `080` may not start until this plan
     has **landed on `main`** — every reduction plan gates on it. (Whether any two plans in this epic
     may run at the same time is stated in the epic README § "The collision matrix" and nowhere else;
     this bullet states ordering only.) `080` D1 inherits a `_fixtures.py` already carrying four
     test-conventions entries and renames it with them intact.

   **Do not add an `EXEMPT_RULE_IDS` entry** — that would register four rules and then excuse them
   from ever firing, which is the defect the invariant exists to catch.

   Landing four `warning` rules into this scope **falsifies two blanket statements in the standards
   doc it lands in**: `doctor-test-conventions.md` currently opens its § Rules with "All three rules
   emit findings with `severity: error`" and closes its § Severity Summary with "All three rules ship
   with build-failing severity … Suppression is not provided." Both become false the moment a
   `warning` rule exists there. Correct them in the same change — a standards doc that contradicts its
   own rule table is the misleading-signal defect this epic is about.
   *Done when:* running the doctor's `test-conventions` scope over `test/` emits findings for all four
   rule ids over the live tree, each rule has a matched positive/negative test pair, the two blanket
   severity statements are corrected to match the shipped rule set, and the run reports the per-rule
   finding counts.

   > **Invoking the doctor.** A bare call to `doctor-marketplace.py` fails with
   > `ModuleNotFoundError: No module named '_dep_detection'` — it has no `sys.path` bootstrap and its
   > import chain reaches into other skills' scripts directories.
   > `doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" carries
   > the verified single-command invocation, which supplies those directories on `PYTHONPATH` and
   > touches no `.plan/` — follow it there rather than reconstructing it. If it cannot be made to run,
   > report the deliverable **blocked** rather than substituting a weaker check.

6. **D6 — Record the two decisions this run may not take** — in the run report, as proposals for the
   operator, not as changes:
   * **Hypothesis adoption.** `hypothesis` is a third-party dependency; adding it to
     `[dependency-groups].dev` in `pyproject.toml` is a user-approval step that the governing skill
     already marks as such. Record the proposal **and** name the candidate call sites — derive them,
     do not guess: the parsers, identifier validators, and round-trip encoders under test today.
     Candidates the review already saw include `marketplace/targets/opencode/frontmatter.py`'s
     `parse_frontmatter`, the shared `toon_parser`, and the identifier validators registered in
     `doctor-test-conventions.md` § "Rule 3 — Validator Registry". Re-derive the list; report it with
     the count.

     **This is the whole-tree list, and two later plans refine halves of it.** Plan `060` § D5 derives
     the candidates in the runtime and script-substrate slice; plan `080` § D4 derives them in the
     generator slice. Both run after this one and both seed from the same three examples. State that
     relationship in the report and fix the table's column set here, so the operator receives one list
     refined twice rather than three lists with no stated relationship.
   * **Flipping the D5 rules to `error`.** They ship at `warning` because the tree currently violates
     all four at scale, and a build-failing rule landed over a non-compliant tree fails every
     subsequent build until the reduction plans finish. Record what the per-rule violation counts are
     at the moment of the report, and propose the flip as a follow-up conditioned on those counts
     reaching zero.
   *Done when:* the report carries both proposals, the Hypothesis candidate list is derived rather
   than copied from this plan, and the per-rule violation counts are re-derived at report time.

## Out of scope

* **Refactoring any test module to comply.** This plan writes the rules and the checks; plans `030`
  through `080` apply them. Excluded because the reduction plans partition the test tree between
  themselves to run concurrently, and a module this plan rewrote would be a module one of them then
  collides with.
* **Adding `hypothesis` to `pyproject.toml`.** Excluded because it is a third-party dependency and the
  governing skill marks that as a user-approval step — and this run has no operator to approve it. D6
  records the proposal instead.
* **Flipping the D5 rules to `error` severity.** Excluded because the tree violates all four at scale
  today; a build-failing rule over a non-compliant tree makes every subsequent build in this epic red
  and blocks the very plans that would fix it.
* **The `run-tests.py` runner and the pytest configuration in `pyproject.toml`.** Excluded because the
  runner's false-confidence defects were already addressed by
  `doc/plans/truthful-signals/380-test-suite-false-confidence/`, and the pytest configuration
  (markers, timeout, `filterwarnings`, xdist) is measured, documented, and not implicated in anything
  this plan touches.
* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020`, which may be running
  concurrently. Excluded to keep the two surfaces disjoint.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md` — D1, D2, D3
- `marketplace/bundles/plan-marshall/skills/persona-module-tester/SKILL.md` — reference-table rows
  for the new rules
- `marketplace/bundles/pm-dev-python/skills/pytest-testing/standards/testing-pytest.md` — D2, D3, D4
- `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` — Quick Reference rows (D4)
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — D5
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md` — D5
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md` — D5
  (one row per new rule, required by the provenance contract)
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — D5
  (one row per new rule, with its class and source citation)
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md` — Workflow 10 and the
  rule-index list (D5)
- `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule4.py` — D5 (new)
- `test/pm-plugin-development/plugin-doctor/_fixtures.py` — D5 (one `FIXTURE_CORPUS` entry per new
  rule, so the zero-match invariant is satisfied; plan `080` renames this file later, after this
  plan has landed)

Nothing under `test/` other than that one new module and the `_fixtures.py` corpus entries that make
its rules fire. Nothing under `test/conftest.py` or
`test/_shared/`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `persona-module-tester` § "Splitting Large Test Files" states the `~200 lines` figure | OBSERVED | `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md` |
| `persona-module-tester` § "Test Data Principles" states an unscoped preference for generated data and lists hardcoded data under "Anti-Patterns" | OBSERVED | same file, § "Test Data Principles" and § "Anti-Patterns" |
| `pytest-testing` documents Hypothesis but the tree has zero usage | OBSERVED | `standards/testing-pytest.md` § "Property-Based and Adversarial Testing"; `grep -rn 'hypothesis' test --include=*.py` returns one unrelated prose match |
| The `test-conventions` scope exists, is registered, and carries exactly three rules | OBSERVED | `scripts/_analyze_test_conventions.py` `RuleDescriptor` list; `scripts/doctor-marketplace.py` subparser registration; `standards/doctor-test-conventions.md` § "Severity Summary" |
| `plugin-doctor` already has historical-prose / incident-reference / lesson-id analyzers scoped over `marketplace/bundles/**` and **not** over `test/` | OBSERVED | `scripts/_analyze_historical_prose_in_skills.py`, `_analyze_incident_reference_in_docs.py`, `_analyze_lesson_id_in_skill_prose.py` — read their root argument before reusing their matchers |
| Roughly three quarters of test lines sit in modules over 400 lines, and the median module is ~323 lines | HYPOTHESIS | Re-derive: `wc -l $(find test -name 'test_*.py')`, sort, take the median and the `>400` share. D1's derivation sentence must cite the number you measure, not the number written here. |
| No existing `plugin-doctor` rule already covers any of the four D5 rule ids | HYPOTHESIS — **this is an asserted absence, the higher-risk half** | Enumerate every `RuleDescriptor(rule_id=…)` across `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_*.py` and confirm none of the four ids, or a rule with equivalent detection, is already registered. If one is, extend it rather than adding a second. |
| `test_test_conventions_rule1.py`, `rule2.py` and `rule3.py` exist and `rule4.py` does not, so the new module continues an established numbering rather than inventing a convention | HYPOTHESIS — the absence half is the higher-risk one | `ls test/pm-plugin-development/plugin-doctor/`. If a `rule4.py` already exists, extend it rather than colliding with it |

## Verification

**Executable.** `./pw verify` (the lane's build gate — this plan changes Python under
`marketplace/bundles/`, so the gate is armed). Additionally run the doctor scope itself over the live
tree and record the per-rule finding counts in the report, using the invocation in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" (see the note
under D5 for why a bare call fails), with `--test-root test/`.

A rule reporting **zero** findings over a tree the census says violates it is a broken detector, not a
clean tree — treat a zero as a failure to investigate, not as a pass.

**By reading — cold read, required.** D1 through D4 are text whose entire value is the behaviour they
produce in a later author; "implemented as specified" cannot verify them. Dispatch the lane's pre-PR
verification sub-agent with the amended `testing-methodology.md` and `testing-pytest.md` **and no
other context** — not this plan, not the epic README — and ask it three questions:

1. What is the module line budget, and what does it say to do when a module exceeds it?
2. Given a test that must assert `default:branch-cleanup` seeds `merge_queue_wait_budget_seconds: 1800`,
   do these standards tell you to use a generated value or an exact literal? Quote the sentence that
   settles it.
3. May a test docstring say which PR introduced the regression it pins? Quote the sentence that
   settles it.

The expected readings are **400 / split by behaviour cluster**, **exact literal**, and **no**. Any
other reading means the wording failed however complete the text looks — fix the wording and re-read.
Record the sub-agent's answers verbatim in the report.

## Notes

* **Sequencing.** This plan and plan `020` are the epic's two blocking plans; they may run
  concurrently with each other and must both land before any of `030`–`080` starts. See
  `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time".
* **The one shared file with plan `080`.** Plan `080` refactors `test/pm-plugin-development/**` and
  explicitly excludes the `test_test_conventions_rule*.py` modules and the new module this plan adds
  beside them, all of which this plan owns. Do not touch any other
  module under that directory.
* **Plugin cache sync.** This plan edits `marketplace/bundles/`, so a local `/sync-plugin-cache` is
  owed on a developer machine afterwards. The lane cannot run it (it reads the git-ignored `target/`
  tree). Record that in the report per `CLAUDE.md` § Standalone Plan Lane.
* **Reuse before you write.** D5's fourth rule and the D5 preamble rule both have close relatives among
  the existing analyzers. A second matcher for prose this repository already knows how to detect is the
  duplication this epic exists to remove — extend or parameterize the existing analyzer where its
  detection is genuinely the same, and say in the report which choice you made and why.
