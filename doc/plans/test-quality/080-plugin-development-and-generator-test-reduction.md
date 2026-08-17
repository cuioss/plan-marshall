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

# Make the doctor's own scaffold the norm across the plugin-development and generator slice

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> sibling plans are converging on the same harness.
>
> **A second dependency, on plan `090`, and it is partial.** `090` publishes the parser seams a **B6**
> conversion in this slice would otherwise hit, and widens the citation matchers D3's prose half is
> measured by. If `090` has **not** landed, D1, D2 and D4 are unaffected and proceed; **D3's
> `parse_ns` half stops at the first `ParserSeamNotFound`** and records the blocked call sites rather
> than working around them. Check by reading whether the modules `ParserSeamNotFound` names publish a
> builder — do not assume from the calendar.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10** this plan applies,
> the concurrency contract, and what a reduction run must hold. The landed skills are the authority
> where they and the README disagree.
>
> ⚠️ **One narrow exclusion, because plan `010` owns it.** Plan `010` ships the tests for the four new
> `test-conventions` doctor rules it added, and owns the modules that test that scope —
> `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py`. **Match that glob against
> the tree rather than assuming which numbers exist**: `010` split its own new tests by behaviour
> cluster while landing, so the set is not a contiguous run. **Do not touch any module the glob
> matches.** Everything else under `test/pm-plugin-development/` is yours.

## Problem

The plugin-development and generator slice — the plugin doctor, the marketplace inventory and
dependency resolver, the self-review extension, the multi-target generator's Claude and OpenCode
emitters, the plugin-cache sync, and the per-consumer-bundle plugin tests — carries roughly 60,400
lines of `test_*.py` across 161 modules. `test/pm-plugin-development/plugin-doctor/` alone accounts for
roughly 33,600 of them across 82 modules. All four figures are leads — re-derive them
(`wc -l $(find test/pm-plugin-development/plugin-doctor -name 'test_*.py')`), because they size D1
directly.

This slice is where the epic's target architecture **already exists** — in one file, and almost
nowhere else. That gap is what the plan is for, and it is much wider than earlier drafts of this plan
assumed.

`test/pm-plugin-development/plugin-doctor/_fixtures.py` is a ~1,590-line shared fixture corpus that
loads every analyzer once through `conftest.load_script_module`, materializes per-rule positive
fixtures under scratch roots, and exposes `assert_analyzer_findings` — a shared
run-analyzer-then-assert-rule-codes scaffold that lets a module assert **which** rules fired rather
than merely how many findings came back. That is exactly the shape plans `030`–`070` are trying to
reach in their own slices. It also carries the bare `_fixtures.py` basename that the doctor's own
`unique-fixture-basenames` rule forbids — the tool violating the rule it ships, and today the **only**
finding that rule reports tree-wide.

**The scaffold is almost unused.** Of the `test_analyze_*.py` modules in that directory, roughly
**three of fifty-seven** import `assert_analyzer_findings`; the rest run analyzers by hand. Earlier
drafts of this plan read the situation the other way round — as a rename plus a handful of
conversions — and set the deliverable's size accordingly. Re-derived, D1 is the plan's principal work
and roughly fifty-four modules wide. Both figures are leads; the gating claim below says to re-derive
them before scoping, and what to do if the re-derivation disagrees.

Beside it sit the slice's oversized modules — `ext-self-review-plan-marshall/test_self_review.py`
(~3,900 lines), `plugin-doctor/test_analyze.py` (~2,370), `test_doctor_marketplace.py` (~2,310) and
`test_analyze_manage_invocation.py` (~2,285). Splitting them is real work and it is **not this plan's**:
plan `100` owns the module-budget campaign across all six slices and takes this slice after this plan
lands, because scaffold conversion is what brings several of these modules under budget without a
split at all.

The `test/marketplace/` half has the opposite profile: its modules are small, well-factored, and
compact — `targets/opencode/test_frontmatter.py` is a good example. What it has instead is the
corpus's clearest **property-based-testing** target. `parse_frontmatter` is a text parser tested with
eight hand-picked example strings covering unterminated fences, embedded `---`, list flattening, and
missing trailing newlines. That is an enumeration of the cases the author thought of, and the
enumeration is the weakness — the contract is universal in the **B8** sense.

## Goal

The slice's scaffold-shaped better half becomes its norm: every per-rule doctor module asserts through
the shared scaffold rather than by hand, so it asserts which rules fired instead of how many findings
came back; the shared fixture module is named so the doctor's own rule can see it; the suite-coverage
contract survives every move with its exempt set unchanged; and the operator gets a derived list of
the parsers where property-based testing would replace an enumeration with a property.

## Deliverables

**Five deliverables, and the fifth is the report.** The epic's four executed reduction plans each
completed roughly two to three code deliverables per run, so a plan with more than that is a plan
whose tail does not happen — which is why the module-budget split earlier drafts carried as D2 now
belongs to plan `100`. D1 is this plan's principal work and is large; a run that finishes D1 and D2
and reports the rest as not done has done the valuable half.

1. **D1 — Rename the shared fixture module and make the scaffold the norm** — rename
   `test/pm-plugin-development/plugin-doctor/_fixtures.py` to `_plugin_doctor_fixtures.py`
   (domain-prefixed, per the doctor's own `unique-fixture-basenames` rule, which forbids the bare
   `_fixtures.py` spelling), update every importer, and convert the `test_analyze_*.py` modules that
   run analyzers by hand onto `assert_analyzer_findings`. **The conversion is the deliverable, not the
   rename**: a module that asserts a finding **count** rather than the **rule codes** that fired is
   asserting something weaker than the scaffold already offers, and converting it strengthens the
   assertion while shortening the module.
   **You inherit four extra corpus entries.** Plan `010` — which has landed — added one
   `FIXTURE_CORPUS` entry per new `test-conventions` rule to this same module. They rename with the
   file and must keep firing afterwards; D2's invariant check is what proves they did.
   **This deliverable is roughly fifty-four modules wide and it is acceptable to finish only part of
   it.** Convert in coherent batches, report the count converted and the count remaining, and leave
   the remainder as residue for a follow-up run. What is **not** acceptable is a rename that lands
   without conversions and is reported as D1 complete.
   *Done when:* the rename is complete with every importer updated, the report lists every module
   converted and every module that legitimately could not be with the reason, plan `010`'s four corpus
   entries still fire after the rename, and the count remaining is stated rather than implied.

2. **D2 — Preserve the suite-coverage meta-test through every move** — `_fixtures.py`'s
   `FIXTURE_CORPUS` / `fired_rule_ids()` surface exists to satisfy one contract, stated in its own
   docstring: `registered_rule_ids − fired_rule_ids − EXEMPT_RULE_IDS == ∅`. Every rename and scaffold
   conversion in D1 must leave that contract holding **and still discriminating**. The `_EXTRA_FIRED`
   registry, into which the cross-file verifier-echo test records its emitted finding types, is the
   fragile part: a move that separates the recording test from the meta-test's import path silently
   shrinks `fired_rule_ids()`, and the meta-test then fails — or, worse, an `EXEMPT_RULE_IDS` entry
   added to make it pass hides the loss.
   *Done when:* the suite-coverage meta-test passes, `EXEMPT_RULE_IDS` has **not** grown, and the
   report states the before/after sizes of `registered_rule_ids`, `fired_rule_ids` and
   `EXEMPT_RULE_IDS`. A grown exempt set is a failed deliverable, not a passing one.

3. **D3 — Normalise preambles, argument construction, and strip history from prose** — apply **B7**,
   **B6** and **B3** across the slice: `conftest.load_script_module` / `get_scripts_dir` for every
   module preamble, `020`'s `parse_ns` for every `argparse.Namespace`, and the removal of plan ids,
   deliverable ids, PR numbers, lesson ids and superseded-behaviour narration from test docstrings and
   comments. The slice carries roughly **222** `Namespace(` constructions against **zero** `parse_ns`
   calls — leads to re-derive.

   ⛔ **Two hazards, both paid for by sibling runs.** `load_script_module` **registers** the module it
   builds in `sys.modules` under the script stem, where a bare `spec_from_file_location` does not, so a
   conversion that drops a bespoke `module_name` can collapse two modules onto one registration and
   leak module-level mutable state — plan `030` paid **173 order-dependent failures** for this.
   And `parse_ns` **re-executes the script module on every call**, so hoist it into a fixture or a
   module-level constant rather than calling it per assertion.

   ⚠️ **One tension specific to this slice, resolved explicitly:** several modules here test rules
   **about** lesson ids and incident references, so their fixtures legitimately contain those strings.
   **Strip the prose, keep the fixtures.** Where the `test-docstring-historical-prose` rule fires on a
   fixture literal rather than on prose, that is a rule defect owned by plan `090` — record it there,
   do not work around it by weakening the fixture. Note that the rule already exempts a match inside a
   backtick span or a quoted string, so writing such a value as an inline literal is often the whole
   fix.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, every `parse_ns` exception is listed with its script **and with whether it is blocked on a
   missing parser seam**, the prose rule's findings over this slice are zero **or** each remaining
   finding is recorded as a fixture-literal or data-not-citation case with the module named, and the
   report states how many `parse_ns` calls are hoisted versus per-assertion.

4. **D4 — Derive the property-based-testing candidate list for the generator half** — a **report
   deliverable, not a code change**. Enumerate every unit under `test/marketplace/` and
   `test/pm-plugin-development/tools-marketplace-inventory/` whose contract is universal in the **B8**
   sense, and for each record: the unit, the module testing it today, the property that would be
   asserted, and the number of hand-picked example rows it currently uses.
   `marketplace/targets/opencode/frontmatter.py`'s `parse_frontmatter` — tested with roughly eight
   hand-picked strings — is the worked case, and its property is a stated one: for any frontmatter
   block, parsing then re-serialising round-trips, and no value containing the fence delimiter
   truncates the block. That is a starting point, **not** the list. Derive it.
   **Anchor on plan `010`, not on plan `060`.** Plan `010` § D6 derived the whole-tree candidate list
   and has landed, so its report is git-tracked and readable at
   `doc/plans/test-quality/010-test-authoring-standards-and-enforcement/report-01.md` § "D6 — The two
   decisions this run may not take": use the column set it fixed, and state which rows refine its and
   which are new. Plan `060` § D5 derived the same table for its own slice and has also landed, so its
   report is readable too — but `010`'s is the superset and the anchor.
   *Done when:* the report carries the derived table with one row per candidate and its example-row
   count, states the total, and names its relationship to plan `010`'s whole-tree list.

5. **D5 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the D1 conversion list with the count remaining; the D2 rule-id set sizes; the `parse_ns`
   exception list with each entry's blocking reason; the per-rule `test-conventions` finding counts;
   and the two run conditions the epic README § "What a reduction run must hold" adds — the skipped
   count and the suite's wall-clock, before and after, each with its population named.
   *Done when:* the report carries every figure, each labelled with the command that produced it.

## Out of scope

* **Splitting any module over the 400-line budget.** Excluded because plan `100` owns the budget
  campaign across all six slices, and takes this slice **after** this plan lands — D1's scaffold
  conversion is what brings several of these modules under budget without a split at all, so splitting
  first would be work done twice. This plan therefore **reports** its over-budget count (a lead: 43
  modules) and does not act on it.
* **`test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py`.** Owned by plan `010`,
  which ships the tests for the doctor rules it added. Excluded because that is the one file path where
  the two plans' surfaces meet — and because plan `090` may amend those same rules, which would make a
  concurrent edit here a three-way collision. Match the glob against the tree; do not assume which
  numbers exist.
* **`test/conftest.py` and `test/_shared/**`.** Owned by plans `020` and `090` and consumed read-only
  here. Excluded because sibling reduction plans run concurrently against the same harness. Note that
  `test/conftest.py`'s `collect_ignore` list names real-tree smoke modules in this slice — **do not
  move or rename those modules**, because their paths are hard-coded in a file this plan may not edit.
  A move that needs a `collect_ignore` update is a **proposal**, not a change.
* **Any file under `marketplace/bundles/**` or `marketplace/targets/**`.** Excluded because test
  refactoring that changes production code is not test refactoring — and this slice tests the plugin
  doctor and the multi-target generator, so an incidental production change here would alter the tool
  that lints every other slice's work. A production defect found while refactoring is **recorded**, not
  fixed; where it is a rule defect or a missing parser seam, plan `090` is its owner.
* **Adding `hypothesis` or writing a property-based test.** Excluded because it is a third-party
  dependency and adding one is a user-approval step with no operator present. D4 produces the
  evidence; plan `010` § D6 carries the standing proposal.
* **Growing `EXEMPT_RULE_IDS` to keep the suite-coverage meta-test green.** Excluded explicitly
  because it is the single most available wrong move in this slice: it converts a real coverage loss
  into a passing build, and the docstring of the module it lives in is the only thing that would say
  so.

## Expected surface

Exactly these paths, and nothing else:

- `test/pm-plugin-development/**` — **excluding** every module matched by
  `plugin-doctor/test_test_conventions_rule*.py`
- `test/marketplace/**`
- `test/sync-plugin-cache/`, `test/finalize-step-deploy-target/`,
  `test/finalize-step-sync-plugin-cache/`
- `test/pm-dev-frontend/`, `test/pm-dev-frontend-cui/`, `test/pm-dev-java/`, `test/pm-dev-java-cui/`,
  `test/pm-dev-oci/`, `test/pm-dev-python/`, `test/pm-documents/`, `test/default/`
- `test/test_runner_falsifiability.py`, `test/test_conftest_discipline.py`

⚠️ **Plan `110` also edits inside this surface** — `test/sync-plugin-cache/`,
`test/pm-plugin-development/` and `test/marketplace/` hold most of the tree's skip sites. Before
starting, confirm `110` is not in flight against those directories; if it is, **halt and report it**
rather than editing files two plans own.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~60,400 lines across 161 modules, of which `plugin-doctor/` is ~33,600 across 82 | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `plugin-doctor/_fixtures.py` is a ~1,590-line shared corpus exposing `assert_analyzer_findings`, `FIXTURE_CORPUS`, `fired_rule_ids` and `_EXTRA_FIRED`, and carries the bare basename its own `unique-fixture-basenames` rule forbids | OBSERVED | the file; `doctor-test-conventions.md` § `unique-fixture-basenames` detection step 2, which names `_fixtures.py` explicitly |
| It is the only `unique-fixture-basenames` finding in the whole test tree | HYPOTHESIS | the `test-conventions` sweep over `test/`, reading that rule's finding list |
| The suite-coverage contract is `registered_rule_ids − fired_rule_ids − EXEMPT_RULE_IDS == ∅` | OBSERVED | the `_fixtures.py` module docstring |
| Plan `010`'s four `test-conventions` corpus entries are present in `FIXTURE_CORPUS` | OBSERVED | `_fixtures.py` — the `corpus['test-module-line-budget']`, `['test-helper-module-misnamed']`, `['test-module-preamble-boilerplate']` and `['test-docstring-historical-prose']` assignments |
| `marketplace/targets/opencode/frontmatter.py`'s `parse_frontmatter` is tested with roughly eight hand-picked example strings | OBSERVED | `test/marketplace/targets/opencode/test_frontmatter.py` § `TestParseFrontmatter` |
| `test/conftest.py`'s `collect_ignore` hard-codes paths to real-tree smoke modules in this slice | OBSERVED | `test/conftest.py`'s `collect_ignore` list |
| Roughly **3 of 57** `test_analyze_*.py` modules import `assert_analyzer_findings`; the rest run analyzers by hand | HYPOTHESIS — **gating for D1; it decides the deliverable's size** | Per module in `plugin-doctor/`, record whether it imports `assert_analyzer_findings`. Earlier drafts of this plan assumed the opposite ratio and sized D1 as a rename. **If the re-derivation disagrees with the figure above in either direction, restate the size in the report before starting** — this is the claim the deliverable's whole shape rests on |
| No module outside `plugin-doctor/` imports its `_fixtures` module by bare name | HYPOTHESIS — **asserted absence; the rename's blast radius depends on it** | `grep -rn 'from _fixtures import\|^import _fixtures' test`. Beware a false positive from a sibling module whose own name ends in `_fixtures` — match the import statement, not the substring |
| The slice carries ~222 `Namespace(` constructions against zero `parse_ns` calls | HYPOTHESIS — **it sizes D3** | `grep -c 'Namespace('` and `grep -c 'parse_ns('` over the Expected surface. Leads — re-derive |
| Plan `090` has published a parser seam for every module a `parse_ns` conversion in this slice would otherwise block on | HYPOTHESIS — **it decides how much of D3 is reachable** | Attempt the conversion and read the `ParserSeamNotFound` failures. A module that raises has no seam: **record the call site, do not work around it**, and do not edit the production module — `090` owns it |
| The partition holds — every directory under `test/plan-marshall/*/`, every file at the root of `test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/` itself (which the first two clauses already decompose) appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the **named exclusions**, which four sibling runs have already corrected. An entry in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

**Four conditions, all of which must hold. The line count is measured and reported, not targeted.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command.
3. **The skipped count does not rise, and the suite does not slow down.** Both per
   `doc/plans/test-quality/README.md` § "What a reduction run must hold", with the population of each
   figure named.
4. **The slice is order-independent.** Run it in default order and again with its directories in
   **reverse** order; both must pass. D1's rename and D3's conversions both change `sys.modules`
   registrations, which is the mechanism plan `060` found a live order-dependent failure in.

**A fifth check, and it outranks everything above: the doctor must still catch what it caught.** Run
the doctor's whole-tree **rule-firing** sweep over the full marketplace tree before the first commit
and again before the PR, and diff the rule-id sets in the two outputs. They must be identical. The
subcommand is `quality-gate` — **not** `test-conventions`, which scopes to the test tree, and not a
bare invocation, which only prints help and exits non-zero. Run it through the invocation in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope", which carries
the exact command — the same `PYTHONPATH` prefix as the `test-conventions` call, with `quality-gate`
in place of `test-conventions --test-root {path}`.

If that command cannot be made to run, this check is **unavailable** and the plan reports that rather
than proceeding as though it passed — and records what the check that would have established the
unavailability returned. It is the check that outranks everything else here: this slice's tests **are**
the evidence that the linter fires, a refactor that quietly narrows what fires leaves every other
slice's compliance unverifiable, and the suite-coverage meta-test alone will not show it if
`EXEMPT_RULE_IDS` absorbed the loss.

**On the line count.** Earlier drafts of this plan set a **25%** line floor. It is retired, and the
arithmetic is decisive rather than merely discouraging: 25% of ~60,400 lines is ~15,100, while the
slice's **entire** comment-plus-docstring volume is ~13,400. Deleting every comment and every
docstring in the slice would not reach the floor — and **B3** forbids deleting the rationale at all.
The four executed reduction plans returned 2.56%, 0.58%, 0.52% and 0.72% against floors of 30%, 25%,
20% and 25%, and each independently recommended re-deriving the floors from measured composition.
**Report the slice's line delta as an observation.** A run that deletes an assertion, a docstring's
rationale, or a comment to make the number larger has failed regardless of what the number says.

**By reading — cold read, required for D3's prose half.** D3 rewrites text whose value is what a later
reader takes from it, and the risk is not that too much history is removed but that the **invariant**
is removed along with it — plan `040`'s cold read found four of ten rewritten docstrings from which a
maintainer could not recover why the contract matters. Dispatch the lane's pre-PR verification
sub-agent with **five rewritten test modules and no other context** — not this plan, not the originals
— and ask, for each of ten named tests: "What contract does this test pin, and why does it matter?" A
test whose rewritten docstring cannot answer both has been over-stripped; restore the invariant (not
the history) and re-read. Record the answers verbatim.

**By reading.** After D1, take three converted `test_analyze_*.py` modules and confirm from the module
text alone that each asserts **which rule ids fired**, not merely a finding count. A conversion that
preserved a count assertion has moved the code without taking the strengthening the scaffold exists to
provide — which would make D1 a rename wearing a conversion's name.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded, through the same README invocation — a **bare** call to
`doctor-marketplace.py` fails with `ModuleNotFoundError: No module named '_dep_detection'`, because
the script has no `sys.path` bootstrap.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition and the epic's plan graph, including where `090`, `100` and `110` sit —
  and `110`'s overlap with this surface is restated in Expected surface above, because it is this
  plan's one live collision risk.
* **Order within the plan matters.** D1 before D2: the invariant check exists to prove D1's moves did
  not shrink what fires.
* **This slice already knows how to do what the epic wants — in one file.** `_fixtures.py`'s
  corpus-plus-scaffold design is the pattern the other five slices are converging toward, and the gap
  between that one file and its fifty-odd neighbours is this plan's subject. If the run finds a
  generalisable improvement to the design, **record it as a proposal for `test/_shared/`** — do not
  promote it yourself; plans `020` and `090` own that surface.
* **A run completes two to three code deliverables.** That is the epic's own measured experience
  across four executed reduction plans, not a guess. **Report what was not reached rather than thinning
  what was.**
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked.
