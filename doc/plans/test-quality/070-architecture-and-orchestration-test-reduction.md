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

# Give the architecture, orchestration and build slice its shared fixture surfaces

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> sibling plans are converging on the same harness.
>
> **A second dependency, on plan `090`, and it is partial.** `090` publishes the parser seams that
> **B6** conversions in this slice will otherwise hit, and it rewrites the one `test/conftest.py`
> docstring D1's rename would make stale. If `090` has **not** landed, D1, D2 and D4's prose half are
> unaffected and proceed; **D3's `parse_ns` half stops at the first `ParserSeamNotFound`** and records
> the blocked call sites rather than working around them. Check by reading whether the modules
> `ParserSeamNotFound` names publish a builder — do not assume from the calendar.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the house-style rules **B1**–**B10** this plan applies,
> the concurrency contract, and what a reduction run must hold. The landed skills are the authority
> where they and the README disagree.

## Problem

The architecture, orchestration and build slice — the architecture query surface, the plan
orchestrator and its inbox, the plan-marshall core and its handshake, the plan lifecycle phases, the
build-system extensions and the build server, plus the finalize-step extensions — carries roughly
63,200 lines of `test_*.py` across 168 modules in twenty-seven directories. Both figures are leads
measured at authoring time; re-derive them.

It is the epic's most *fragmented* slice: twenty-seven directories, no single dominant module, and its
largest file (`plan-orchestrator/test_orchestrator_corpus.py`, ~2,230 lines) is under half the size of
the largest module in three of the sibling slices. That fragmentation changes what the work is. There
is no `test_audit_checks.py` here to decompose and no `test_config_defaults.py` here to collapse; the
value comes from **convergence** — the same contract staged independently in many places, brought onto
one surface.

Two of those doses are specific to this slice.

The **build-system family** — `build-gradle`, `build-maven`, `build-npm`, `build-operations`,
`build-pyproject`, `build-server` — tests six implementations of one extension contract, and the six
directories stage that contract's fixtures independently.
`test/plan-marshall/build_test_helpers.py` exists to serve that family, but reaches only **four** of
the six: `build-gradle`, `build-maven`, `build-npm` and `build-pyproject` import it;
`build-operations` and `build-server` do not reference it at all. So D1's consolidation is two jobs,
not one: four directories that already share a surface, and two that never did — on top of the two
renames D1 also performs. Re-derive the importer set before scoping the work.

The helper sits at the tree's root level and carries no underscore prefix — so nothing marks it as
non-collectable, the existing `unique-fixture-basenames` doctor rule does not inspect it, and its own
module docstring records that loading it through `load_script_module` **re-registers
`_build_execute_factory` in `sys.modules`**, a hazard `test/conftest.py`'s daemon-routing fixture then
has to work around by patching closure `__globals__` dicts rather than a module object.

The **plan-lifecycle phase directories** — `phase-1-init` through `phase-4-plan`, plus `execute-task`,
`manage-lifecycle`, `manage-personas`, `manage-plan-documents` and `manage-terminal-title` (the nine
D2 names) — are each small, each stage a plan directory by hand, and none shares that staging with the
others even though it is the same plan directory.

## Goal

The slice's shared contracts have shared fixtures: one build-extension fixture surface serving all six
build directories, one plan-lifecycle staging fixture serving the phase directories. Its preambles
resolve through the shared loaders, its argument namespaces come from the real parsers, its tabular
families are tables, and both unprefixed root-level helpers are renamed so the doctor's own rule can
see them — with the `sys.modules` registration hazard documented at the fixture that causes it.

## Deliverables

**Five deliverables, and the fifth is the report.** The epic's four executed reduction plans each
completed roughly two to three code deliverables per run, so a plan with more than that is a plan
whose tail does not happen — which is why the module-budget split that earlier drafts of this plan
carried as D3 now belongs to plan `100`, and why the surviving four are ordered by value rather than
by convenience. If a run cannot finish all four, it finishes D1 and D2 and reports the rest as not
done; those two carry this slice's whole convergence argument.

1. **D1 — One build-extension fixture surface** — rename `test/plan-marshall/build_test_helpers.py` to
   `test/plan-marshall/_build_extension_fixtures.py` (underscore-prefixed per **B10**, so it is
   non-collectable and the existing `unique-fixture-basenames` rule can see it), update its importers,
   and consolidate into it the extension-contract staging currently duplicated across the six
   `build-*` directories. Preserve — and make more prominent, not less — the module docstring's record
   that loading `_build_execute_factory` through `load_script_module` re-registers it in `sys.modules`,
   because `test/conftest.py`'s `_neutralize_daemon_routing` fixture depends on that fact and works
   around it by patching closure `__globals__`. If the consolidation lets the re-registration be
   avoided altogether, **do not take that decision here**: it changes behaviour `conftest.py` reasons
   about, `conftest.py` is owned by plans `020` and `090`, and a concurrent change to both is exactly
   the collision this epic's partition exists to prevent. Record it as a proposal.
   **Rename `test/plan-marshall/discovery_test_helpers.py` to `_discovery_fixtures.py` in the same
   deliverable.** It is the second unprefixed root-level helper, invisible to the same doctor rule for
   the same reason, and its only two importers — `build-npm/test_npm_discover.py` and
   `build-gradle/test_gradle_discover_modules.py` — are both in **this** plan's slice. Plan `060`
   works in the tree it sits at the root of but explicitly does **not** own it, precisely because
   renaming it from there would break two live imports here.

   **The one reference outside this plan's surface is handled by plan `090`, not by you.**
   `test/conftest.py` names `build_test_helpers.py` **by path** in the `_routing_namespaces`
   docstring, and plan `090` § D7 rewrites that docstring to identify the helper by role so the rename
   cannot invalidate it. **Check, do not assume:** run `grep -rn 'build_test_helpers' test/conftest.py`
   before renaming. Empty → `090` has landed and there is nothing to do. Non-empty → `090` has not
   landed; do **not** edit `conftest.py`, and **record the stale reference as a proposal in the
   report**, naming the file, the symbol, and the corrected path.
   *Done when:* both files are renamed with every importer updated, the six `build-*` directories
   stage the extension contract through the shared fixture rather than independently, the `sys.modules`
   hazard is documented at the fixture that causes it, the re-registration question is a recorded
   proposal rather than a change, and the `conftest.py` reference is either already handled by `090`
   or recorded as a proposal — with the grep result stated either way.

2. **D2 — One plan-lifecycle staging fixture** — apply **B4** across the phase and lifecycle
   directories (`phase-1-init`, `phase-2-refine`, `phase-3-outline`, `phase-4-plan`, `execute-task`,
   `manage-lifecycle`, `manage-personas`, `manage-plan-documents`, `manage-terminal-title`). The plan
   directory each of them stages by hand — request, references, status, tasks — becomes one factory
   with keyword overrides, in a `_{domain}_fixtures.py` shared by the group. Build it **on top of**
   `test/conftest.py`'s existing `plan_context` fixture rather than beside it; `plan_context` already
   owns the `PLAN_BASE_DIR` redirect and the `plan_dir_for` resolution, and a second staging surface
   that redirects independently is the duplication this deliverable removes.
   *Done when:* no module in those directories stages a plan directory inline in three or more tests,
   the factory composes with `plan_context` rather than replacing it, and the report names the modules
   that consume it.

3. **D3 — Normalise preambles and argument construction** — apply **B7** and **B6** across the slice:
   `conftest.load_script_module` / `get_scripts_dir` for every module preamble, `020`'s `parse_ns` for
   every `argparse.Namespace`. This slice's `manage-architecture` directory is the corpus's heaviest
   user of the architecture query CLI and therefore of hand-built namespaces for it; the slice carries
   roughly **502** `Namespace(` constructions against **1** `parse_ns` call, which are leads to
   re-derive and which make this the epic's largest remaining **B6** surface.

   ⛔ **Two hazards, both paid for by sibling runs.** First, `load_script_module` **registers** the
   module it builds in `sys.modules` under the script stem, where a bare `spec_from_file_location`
   does not — so a conversion that drops a bespoke `module_name` can collapse two modules onto one
   registration and leak module-level mutable state between them. Plan `030` paid **173
   order-dependent failures** for this. **Preserve each call's original registration name** unless the
   loaded module is demonstrably free of module-level mutable state, and "demonstrably" means read.
   Second, `parse_ns` **re-executes the script module on every call** — its own docstring says so —
   so hoist it into a fixture or a module-level constant rather than calling it per assertion. With
   502 call sites, per-assertion calls are how this slice becomes the one that slows the suite down.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, every `parse_ns` exception is listed with its script **and with whether it is blocked on a
   missing parser seam** (plan `090` § D1's surface) or on something else, and the report states how
   many `parse_ns` calls are hoisted versus per-assertion.

4. **D4 — Parametrize the tabular cases and strip history from prose** — apply **B5** and **B3**. This
   slice's tabular families are the build-system detection matrices (six implementations × the same
   contract questions — the single clearest parametrization target in the slice, and one that spans
   directories, so put the table in D1's shared fixture module), the architecture query filter cases,
   and the inbox envelope shape cases. Separately, strip plan ids, deliverable ids, PR numbers, lesson
   ids, and superseded-behaviour narration from test docstrings and comments, keeping present-tense
   rationale.

   ⚠️ **The prose half's stated risk is over-stripping, and it has materialised before.** Plan `040`'s
   cold read found four of ten rewritten docstrings from which a maintainer could not recover *why*
   the contract matters, in every case because the rewrite removed the consequence along with the
   history. **B3** says to keep the rationale; the citation is what goes. And a lesson id or `TASK-nnn`
   that is the test's own **data** — a seeded filename, an expected return value — is not a citation:
   write it in a backtick span, which is what the rule's literal-span exemption keys on.
   *Done when:* the six build implementations are exercised against the shared contract questions
   through one parametrized surface rather than six copies, no other family of three or more
   near-identical tabular tests remains, the `plugin-doctor` `test-docstring-historical-prose` rule
   reports zero findings over this slice **or** each remaining finding is recorded as a data-not-citation
   case with its module named, and both before/after counts are reported.

5. **D5 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the `parse_ns` exception list with each entry's blocking reason; the `sys.modules`
   re-registration proposal from D1 if one was found; the per-rule `test-conventions` finding counts;
   and the two run conditions the epic README § "What a reduction run must hold" adds — the skipped
   count and the suite's wall-clock, before and after, each with its population named.
   *Done when:* the report carries every figure, each labelled with the command that produced it.

## Out of scope

* **Splitting any module over the 400-line budget.** Excluded because plan `100` owns the budget
  campaign across all six slices, and takes this slice **after** this plan lands — D1's consolidation
  changes which modules are over budget, so splitting first would be work done twice. This plan
  therefore **reports** its over-budget count (a lead: 63 modules) and does not act on it.
* **`test/conftest.py` and `test/_shared/**`.** Owned by plans `020` and `090` and consumed read-only
  here. Excluded because sibling reduction plans run concurrently against the same harness. This
  constraint bites hardest in this plan: D1 touches the exact seam `conftest.py`'s
  `_neutralize_daemon_routing` fixture reasons about. Changing the fixture is a **proposal**, never an
  edit.
* **Any file under `marketplace/bundles/**`.** Excluded because test refactoring that changes
  production code is not test refactoring. A production defect found while refactoring is **recorded**,
  not fixed — and where the defect is a missing parser seam, plan `090` § D1 is its owner, so record
  it there rather than working around it.
* **Any test directory outside this plan's list.** Excluded because the neighbouring directory belongs
  to a concurrently-running sibling plan.
* **`test/plan-marshall/build-server/`'s daemon-routing carve-out.** That directory is carved out of
  the autouse `_neutralize_daemon_routing` fixture **by location**, and its modules own build-server
  routing as their system under test. Its tests may be reduced like any other, but nothing may move a
  module **into or out of** that directory: the carve-out is resolved from the collected node's own
  path, so a relocation silently changes whether the fixture engages — and a module that loses the
  carve-out keeps passing while its assertions become tautologies.
* **Deleting a test because it looks redundant.** Excluded because "redundant" is the judgement a line
  target corrupts. The six build implementations asserting the same contract are six genuine
  implementations of it, not five duplicates — D4 parametrizes them, it does not thin them.

## Expected surface

Exactly these directories under `test/plan-marshall/`, plus the two named root-level test modules and
the two root-level helper renames, and nothing else:

- `build-gradle/`, `build-maven/`, `build-npm/`, `build-operations/`, `build-pyproject/`,
  `build-server/`
- `execute-task/`, `manage-architecture/`, `manage-lifecycle/`, `manage-personas/`,
  `manage-plan-documents/`, `manage-terminal-title/`
- `phase-1-init/`, `phase-2-refine/`, `phase-3-outline/`, `phase-4-plan/`
- `plan-doctor/`, `plan-marshall/`, `plan-orchestrator/`
- `finalize-step-plugin-doctor/`, `finalize-step-preference-emitter/`,
  `finalize-step-review-retrospective/`, `finalize-step-sync-baseline/`,
  `finalize-step-sync-plugin-cache/`
- `q-gate-validation-agent/`, `ref-workflow-architecture/`, `targets-claude/`
- `test_lane_refactor_cleanup_sweep.py`, `test_plan_marshall_plugin_extension.py`
- `build_test_helpers.py` → `_build_extension_fixtures.py` (rename, D1)
- `discovery_test_helpers.py` → `_discovery_fixtures.py` (rename, D1 — both its importers are in this
  slice, which is why plan `060` does not own it)

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~63,200 lines across 168 modules in the twenty-seven listed directories plus the named root modules | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list. Both figures were measured at authoring time and are leads |
| `build_test_helpers.py` is a helper module without the underscore prefix, at the tree's root level | OBSERVED | the file path; `doctor-test-conventions.md` § `unique-fixture-basenames` detection step 1, which enumerates only `_`-prefixed files |
| Loading `_build_execute_factory` through `load_script_module` re-registers it in `sys.modules`, and `conftest.py`'s `_neutralize_daemon_routing` works around that by patching closure `__globals__` dicts | OBSERVED | `test/conftest.py`'s `_routing_namespaces` docstring, which states both facts and why patching a module object is silently partial |
| `test/plan-marshall/build-server/` is carved out of `_neutralize_daemon_routing` **by location** | OBSERVED | `test/conftest.py`'s `_DAEMON_ROUTING_CARVE_OUT` constant and the fixture that reads it |
| The six `build-*` directories stage the extension contract independently rather than through a shared surface | HYPOTHESIS — **gating for D1 and D4** | Read the module preamble of one module per `build-*` directory and record which staging each uses. If they already share a surface, D1 is a rename plus a docstring change and D4's parametrization is the whole deliverable — say so. |
| `build_test_helpers` is imported by exactly four `build-*` directories (`build-gradle`, `build-maven`, `build-npm`, `build-pyproject`) and by nothing outside this slice | OBSERVED | `grep -rln 'build_test_helpers' test` — note `test/conftest.py` names it **by path in a docstring**, which the same grep surfaces and which plan `090` § D7 owns |
| `discovery_test_helpers` is imported only by `build-npm/test_npm_discover.py` and `build-gradle/test_gradle_discover_modules.py`, both in this slice | OBSERVED | `grep -rln 'discovery_test_helpers' test` |
| The phase and lifecycle directories each stage a plan directory by hand and **none shares that staging with another** | HYPOTHESIS — **asserted absence, the higher-risk half; it is D2's entire justification** | Read the staging preamble of one module per directory in the D2 group and record which helper, if any, each uses. If two already share one, D2 is an extension of that surface rather than a new one — say so rather than building a second. |
| The slice carries ~502 `Namespace(` constructions against ~1 `parse_ns` call | HYPOTHESIS — **it sizes D3** | `grep -c 'Namespace('` and `grep -c 'parse_ns('` over the Expected surface. Leads — re-derive |
| Plan `090` has published a parser seam for every module a `parse_ns` conversion in this slice would otherwise block on | HYPOTHESIS — **it decides how much of D3 is reachable** | Attempt the conversion and read the `ParserSeamNotFound` failures. A module that raises has no seam: **record the call site, do not work around it**, and do not edit the production module — `090` owns it |
| The partition holds — every directory under `test/plan-marshall/*/`, every file at the root of `test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/` itself (which the first two clauses already decompose) appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the **named exclusions**, which four sibling runs have already corrected. An entry in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

**Four conditions, all of which must hold. The line count is measured and reported, not targeted.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both. Parametrizing raises it; deleting a
   case lowers it, and that is what this condition exists to catch.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command.
3. **The skipped count does not rise, and the suite does not slow down.** Both per
   `doc/plans/test-quality/README.md` § "What a reduction run must hold", with the population of each
   figure named. D3 is the reason this condition is here: 502 conversions to a helper that re-executes
   its module per call is the epic's clearest opportunity to make the suite slower.
4. **The slice is order-independent.** Run it in default order and again with its directories in
   **reverse** order; both must pass. D1's consolidation and D3's conversions both change `sys.modules`
   registrations, which is the mechanism plan `060` found a live order-dependent failure in — and which
   three same-order runs had reported as passing.

**On the line count.** Earlier drafts of this plan set a **20%** line floor. It is retired, and the
reason is measurement rather than concession. The slice is ~63,200 lines of which ~14,700 (23.3%) is
comment-plus-docstring; 20% is ~12,644 lines, so the floor is reachable only by deleting roughly
**86% of every comment and docstring in the slice** — which **B3** forbids and which plan `040`'s cold
read showed produces docstrings a maintainer cannot use. The four executed reduction plans returned
2.56%, 0.58%, 0.52% and 0.72% against floors of 30%, 25%, 20% and 25%, and each independently
recommended re-deriving the floors from measured composition. **Report the slice's line delta as an
observation.** A run that hits a large delta has done well; a run that hits a small one has not
failed, and a run that deletes an assertion, a docstring's rationale, or a comment to make the number
larger has failed regardless of what the number says.

**A fifth check specific to this slice: the daemon-routing neutralization must still engage.** D1
touches the seam that fixture patches. After D1, confirm the matched positive/negative control pair
under `test/plan-marshall/script-shared/` still passes **and still discriminates** — run the negative
arm and confirm it fails when the marker that disengages the fixture is removed. A control pair that
passes in both configurations proves nothing, and this deliverable is the one most able to make that
happen.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Use the invocation in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" — a **bare**
call to `doctor-marketplace.py` fails with `ModuleNotFoundError: No module named '_dep_detection'`,
because the script has no `sys.path` bootstrap, so the invocation supplies the five scripts
directories it needs on `PYTHONPATH`. It is one command, touches no `.plan/`, and writes nothing. If
it cannot be made to run, report the affected measurement **unavailable** rather than substituting a
weaker check — and record what the check that would have established the unavailability returned.

**By reading — cold read, required for D4.** D4 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading.** After D4, read the parametrized build-contract table cold and confirm from its `ids=`
list alone which of the six implementations each row exercises and which contract question it asks. A
matrix whose ids do not name both axes has moved six readable modules into one unreadable one.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition and the epic's plan graph, including where `090`, `100` and `110` sit.
* **Order within the plan matters.** D1 before D2 before D3 and D4: the consolidation is what the
  parametrized table in D4 lives in, and the renames are what D3's preamble work then resolves through.
* **This slice's value is in D1 and D2, not in the line count.** Six build directories converging on
  one contract fixture, and nine lifecycle directories converging on one plan-staging factory, is
  worth more to the tree than the percentage either produces. Report the convergence explicitly — the
  number of directories now sharing each surface — so the outcome is legible independently of the line
  delta.
* **A run completes two to three code deliverables.** That is the epic's own measured experience
  across four executed reduction plans, not a guess. If this run finishes D1 and D2 and reports D3 and
  D4 as not done, it has done the valuable half; a follow-up run takes the rest, and the report's
  § Residue is what carries it. **Report what was not reached rather than thinning what was.**
* **No `.plan/` path is a source for this plan.** The epic is standalone and has no orchestrator
  ledger, so **do not go looking for one**; every artifact this plan cites is git-tracked.
