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

# Reduce the plugin-development and generator test slice

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> five sibling plans are converging on the same harness.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the ten house-style rules **B1**–**B10** this plan
> applies, and the concurrency contract. The landed skills are the authority where they and the README
> disagree.
>
> ⚠️ **One narrow exclusion, because plan `010` owns it.** Plan `010` ships the tests for the four new
> `test-conventions` doctor rules it adds, and owns the three modules that already test that scope —
> `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule1.py`, `rule2.py` and `rule3.py`
> — plus whatever new module it adds beside them. **Do not touch those modules.** Everything else under
> `test/pm-plugin-development/` is yours.

## Problem

The plugin-development and generator slice — the plugin doctor, the marketplace inventory and
dependency resolver, the self-review extension, the multi-target generator's Claude and OpenCode
emitters, the plugin-cache sync, and the per-consumer-bundle plugin tests — carries roughly 58,900
lines of `test_*.py`. `test/pm-plugin-development/plugin-doctor/` alone accounts for roughly 32,900 of
them across roughly 79 modules. Both figures are leads — re-derive them
(`wc -l $(find test/pm-plugin-development/plugin-doctor -name 'test_*.py')`), because they size D1 and
D2 directly.

This slice is where the epic's target architecture **already exists**, which makes it the least
uniform of the six and changes what "reduce" means here.

`test/pm-plugin-development/plugin-doctor/_fixtures.py` is a ~1,550-line shared fixture corpus that
loads every analyzer once through `conftest.load_script_module`, materializes per-rule positive
fixtures under scratch roots, and exposes `assert_analyzer_findings` — a shared
run-analyzer-then-assert-rule-codes scaffold that the per-rule `test_analyze_*.py` modules consume so
each asserts **which** rules fired rather than merely how many findings came back. That is exactly
the shape plans `030`–`070` are trying to reach in their own slices. It also carries the bare
`_fixtures.py` basename that the doctor's own `unique-fixture-basenames` rule forbids — the tool
violating the rule it ships.

Beside it sit modules that do not use the scaffold at all.
`ext-self-review-plan-marshall/test_self_review.py` is ~3,810 lines for ~236 tests;
`plugin-doctor/test_analyze.py` (~2,370), `test_doctor_marketplace.py` (~2,310) and
`test_analyze_manage_invocation.py` (~2,285) are each well over any reasonable module budget.

The `test/marketplace/` half has the opposite profile: its modules are small, well-factored, and
compact — `targets/opencode/test_frontmatter.py` is a good example. What it has instead is the
corpus's clearest **property-based-testing** target. `parse_frontmatter` is a text parser tested with
eight hand-picked example strings covering unterminated fences, embedded `---`, list flattening, and
missing trailing newlines. That is an enumeration of the cases the author thought of, and the
enumeration is the weakness — the contract is universal in the **B8** sense.

## Goal

The slice's scaffold-shaped better half becomes its norm: every per-rule doctor module asserts through
the shared scaffold, the shared fixture module is named so the doctor's own rule can see it, and the
oversized modules are within budget. The generator half keeps its compact shape, and the operator gets
a derived list of the parsers where property-based testing would replace an enumeration with a
property.

## Deliverables

1. **D1 — Rename the shared fixture module and make the scaffold the norm** — rename
   `test/pm-plugin-development/plugin-doctor/_fixtures.py` to `_plugin_doctor_fixtures.py`
   (domain-prefixed, per the doctor's own `unique-fixture-basenames` rule, which forbids the bare
   `_fixtures.py` spelling), update every importer, and convert the per-rule `test_analyze_*.py`
   modules that still run analyzers by hand onto `assert_analyzer_findings`. The conversion is the
   deliverable, not the rename: a module that asserts a finding **count** rather than the **rule
   codes** that fired is asserting something weaker than the scaffold already offers, and converting
   it strengthens the assertion while shortening the module.
   *Done when:* the rename is complete with every importer updated, every `test_analyze_*.py` module
   that runs an analyzer does so through the scaffold, and the report lists the modules converted and
   the ones that legitimately could not be, with the reason.

2. **D2 — Split every module over the budget** — the module budget landed by plan `010`, split by
   behaviour cluster into `test_{unit}_{cluster}.py`. The slice's known over-budget modules include
   `ext-self-review-plan-marshall/test_self_review.py` (~3,810),
   `plugin-doctor/test_analyze.py` (~2,370), `plugin-doctor/test_doctor_marketplace.py` (~2,310),
   `plugin-doctor/test_analyze_manage_invocation.py` (~2,285),
   `tools-marketplace-inventory/test_scan_marketplace_inventory.py` (~1,540),
   `tools-marketplace-inventory/test_resolve_dependencies.py` (~1,100),
   `plugin-doctor/test_analyze_plan_path_in_scripts.py` (~1,090) and
   `plugin-doctor/test_analyze_lesson_id_in_skill_prose.py` (~1,020) — **re-derive the full list**,
   this one is a lead. Do the split **after** D1, because converting a module onto the scaffold is
   what brings several of them under budget without a split.
   *Done when:* every `test_*.py` in the slice is within the landed budget, each new module's name
   states its cluster, and the `plugin-doctor/` directory's own naming convention
   (`test_analyze_{rule}.py`) is preserved rather than replaced.

3. **D3 — Preserve the suite-coverage meta-test through every move** — `_fixtures.py`'s
   `FIXTURE_CORPUS` / `fired_rule_ids()` surface exists to satisfy one contract, stated in its own
   docstring: `registered_rule_ids − fired_rule_ids − EXEMPT_RULE_IDS == ∅`. Every rename, split and
   scaffold conversion in D1 and D2 must leave that contract holding **and still discriminating**.
   The `_EXTRA_FIRED` registry, into which the cross-file verifier-echo test records its emitted
   finding types, is the fragile part: a module split that separates the recording test from the
   meta-test's import path silently shrinks `fired_rule_ids()`, and the meta-test then fails — or,
   worse, an `EXEMPT_RULE_IDS` entry added to make it pass hides the loss.
   *Done when:* the suite-coverage meta-test passes, `EXEMPT_RULE_IDS` has **not** grown, and the
   report states the before/after sizes of `registered_rule_ids`, `fired_rule_ids` and
   `EXEMPT_RULE_IDS`. A grown exempt set is a failed deliverable, not a passing one.

4. **D4 — Normalise preambles, argument construction, and strip history from prose** — apply **B3**,
   **B6** and **B7** across the slice: `conftest.load_script_module` / `get_scripts_dir` for every
   module preamble, `020`'s `parse_ns` for every `argparse.Namespace`, and the removal of plan ids,
   deliverable ids, PR numbers, lesson ids and superseded-behaviour narration from test docstrings and
   comments. Note one genuine tension in this slice and resolve it explicitly: several modules here
   test rules **about** lesson ids and incident references, so their fixtures legitimately contain
   those strings. Strip the prose, keep the fixtures — and where the `test-docstring-historical-prose`
   rule fires on a fixture literal rather than on prose, that is a rule defect to **report to plan
   `010`'s owner**, not to work around by weakening the fixture.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, every `parse_ns` exception is listed with its script, the prose rule's findings over this
   slice are zero **or** each remaining finding is recorded as a fixture-literal false positive with
   the module named.

5. **D5 — Derive the property-based-testing candidate list for the generator half** — a **report
   deliverable, not a code change**. Enumerate every unit under `test/marketplace/` and
   `test/pm-plugin-development/tools-marketplace-inventory/` whose contract is universal in the **B8**
   sense, and for each record: the unit, the module testing it today, the property that would be
   asserted, and the number of hand-picked example rows it currently uses.
   `marketplace/targets/opencode/frontmatter.py`'s `parse_frontmatter` — tested with roughly eight
   hand-picked strings — is the worked case, and its property is a stated one: for any frontmatter
   block, parsing then re-serialising round-trips, and no value containing the fence delimiter
   truncates the block. That is a starting point, **not** the list. Derive it.
   **Anchor on plan `010`, not on plan `060`.** Plan `010` § D6 derives the whole-tree candidate list
   and lands **before** this plan, so its report is git-tracked and readable: use the column set it
   fixed, and state which rows refine its and which are new. Plan `060` § D5 derives the same table
   for its own slice, but `060` and this plan are **mutually parallel** — its report may not exist
   when you run, so it cannot be the anchor.
   *Done when:* the report carries the derived table with one row per candidate and its example-row
   count, states the total, and names its relationship to plan `010`'s whole-tree list.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the D1 conversion list; the D3 rule-id set sizes; the `parse_ns` exception list; and the
   per-rule `test-conventions` finding counts.
   *Done when:* the report carries all seven figures, each labelled with the command that produced it.

## Out of scope

* **`test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py`, plus any new module plan `010` adds beside them.** Owned by plan
  `010`, which ships the tests for the doctor rules it adds. Excluded because `010` may be running or
  may have just landed, and this is the one file path where the two plans' surfaces meet.
* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness. Note that
  `test/conftest.py`'s `collect_ignore` list names four real-tree smoke modules in this slice —
  **do not move or rename those modules**, because their paths are hard-coded in a file this plan may
  not edit. A move that needs a `collect_ignore` update is a **proposal**, not a change.
* **Any file under `marketplace/bundles/**` or `marketplace/targets/**`.** Excluded because test
  refactoring that changes production code is not test refactoring — and this slice tests the plugin
  doctor and the multi-target generator, so an incidental production change here would alter the tool
  that lints every other slice's work. A production defect found while refactoring is **recorded**,
  not fixed.
* **Adding `hypothesis` or writing a property-based test.** Excluded because it is a third-party
  dependency and adding one is a user-approval step with no operator present. D5 produces the
  evidence; plan `010` § D6 carries the standing proposal.
* **Growing `EXEMPT_RULE_IDS` to keep the suite-coverage meta-test green.** Excluded explicitly
  because it is the single most available wrong move in this slice: it converts a real coverage loss
  into a passing build, and the docstring of the module it lives in is the only thing that would say
  so.

## Expected surface

Exactly these paths, and nothing else:

- `test/pm-plugin-development/**` — **excluding** `plugin-doctor/test_test_conventions_rule*.py` and any
  new test-conventions module plan `010` adds beside them
- `test/marketplace/**`
- `test/sync-plugin-cache/`, `test/finalize-step-deploy-target/`,
  `test/finalize-step-sync-plugin-cache/`
- `test/pm-dev-frontend/`, `test/pm-dev-frontend-cui/`, `test/pm-dev-java/`, `test/pm-dev-java-cui/`,
  `test/pm-dev-oci/`, `test/pm-dev-python/`, `test/pm-documents/`, `test/default/`
- `test/test_runner_falsifiability.py`, `test/test_conftest_discipline.py`

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~58,900 lines, of which `plugin-doctor/` is ~32,900 | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `plugin-doctor/_fixtures.py` is a ~1,550-line shared corpus exposing `assert_analyzer_findings`, `FIXTURE_CORPUS`, `fired_rule_ids` and `_EXTRA_FIRED`, and carries the bare basename its own `unique-fixture-basenames` rule forbids | OBSERVED | the file; `doctor-test-conventions.md` § `unique-fixture-basenames` detection step 2, which names `_fixtures.py` explicitly |
| The suite-coverage contract is `registered_rule_ids − fired_rule_ids − EXEMPT_RULE_IDS == ∅` | OBSERVED | the `_fixtures.py` module docstring |
| `marketplace/targets/opencode/frontmatter.py`'s `parse_frontmatter` is tested with roughly eight hand-picked example strings | OBSERVED | `test/marketplace/targets/opencode/test_frontmatter.py` § `TestParseFrontmatter` |
| `test/conftest.py`'s `collect_ignore` hard-codes paths to four real-tree smoke modules in this slice | OBSERVED | `test/conftest.py`'s `collect_ignore` list |
| Some `test_analyze_*.py` modules still run analyzers by hand rather than through `assert_analyzer_findings` | HYPOTHESIS — **gating for D1; it decides the deliverable's size** | Per module in `plugin-doctor/`, record whether it imports `assert_analyzer_findings`. If nearly all already do, D1 is a rename and D2 is the plan's real work — say so and rebalance rather than manufacturing conversions. |
| No module outside `plugin-doctor/` imports its `_fixtures` module by bare name | HYPOTHESIS — **asserted absence; the rename's blast radius depends on it** | `grep -rln 'from _fixtures import\|import _fixtures' test` |
| The partition holds — every directory under `test/plan-marshall/*/` and every top-level `test/` entry appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the two deliberate exclusions. A directory in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

**The three-part done-when. All three must hold; the third alone is not success.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command.
3. **Line count drops by at least 25%** of the slice's starting total. If it cannot be reached without
   violating (1) or (2), **report the shortfall and stop**.

**A fourth check specific to this slice, and it outranks the line floor: the doctor must still catch
what it caught.** Run the doctor's whole-tree **rule-firing** sweep over the full marketplace tree
before the first commit and again before the PR, and diff the rule-id sets in the two outputs. They
must be identical. The subcommand is `quality-gate` — **not** `test-conventions`, which scopes to the
test tree, and not a bare invocation, which only prints help and exits non-zero. Run it through the
two-step recipe in `doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions
scope", which carries the exact command:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate
```

If the executor's generator cannot run, this check is **unavailable** and the plan reports that rather
than proceeding as though it passed — it is the check that outranks the line floor. This slice's tests
**are** the evidence that the linter fires; a refactor that quietly narrows what fires leaves every
other slice's compliance unverifiable, and the suite-coverage meta-test alone will not show it if
`EXEMPT_RULE_IDS` absorbed the loss.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Use the two-step recipe in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" — a **direct**
call to `doctor-marketplace.py` fails with `ModuleNotFoundError: No module named '_dep_detection'`,
because the script has no `sys.path` bootstrap and the generated executor is what supplies the
`PYTHONPATH` it needs. The executor is git-ignored but its generator is tracked, so the recipe
generates it first. If the generator itself cannot run, report the affected measurement
**unavailable** rather than substituting a weaker check.

**By reading — cold read, required for D4.** D4 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading.** After D1, take three converted `test_analyze_*.py` modules and confirm from the module
text alone that each asserts **which rule ids fired**, not merely a finding count. A conversion that
preserved a count assertion has moved the code without taking the strengthening the scaffold exists to
provide.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition, and the one shared file path with plan `010` is restated in this plan's
  header and Out of scope.
* **Order within the plan matters.** D1 before D2: scaffold conversion shrinks modules and changes
  which ones are over budget.
* **This slice already knows how to do what the epic wants.** `_fixtures.py`'s corpus-plus-scaffold
  design is the pattern the other five slices are converging toward. If the run finds a generalisable
  improvement to it, **record it as a proposal for `test/_shared/`** — do not promote it yourself;
  plan `020` owns that surface and five siblings are building against it concurrently.
