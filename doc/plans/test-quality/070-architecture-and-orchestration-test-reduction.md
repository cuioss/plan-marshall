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

# Reduce the architecture, orchestration and build test slice

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

## Problem

The architecture, orchestration and build slice — the architecture query surface, the plan
orchestrator and its inbox, the plan-marshall core and its handshake, the plan lifecycle phases, the
build-system extensions and the build server, plus the finalize-step extensions — carries roughly
61,300 lines of `test_*.py` across twenty-seven directories.

It is the epic's most *fragmented* slice: twenty-seven directories, no single dominant module, and its
largest file (`plan-orchestrator/test_orchestrator_corpus.py`, ~2,230 lines) is under half the size of
the largest module in three of the sibling slices. That fragmentation changes what the work is. There
is no `test_audit_checks.py` here to decompose and no `test_config_defaults.py` here to collapse; the
reduction comes from the same defect repeated in small doses across a wide surface.

Two of those doses are specific to this slice.

The **build-system family** — `build-gradle`, `build-maven`, `build-npm`, `build-operations`,
`build-pyproject`, `build-server` — tests six implementations of one extension contract, and the six
directories stage that contract's fixtures independently.
`test/plan-marshall/build_test_helpers.py` exists to serve that family, but reaches only **four** of
the six: `build-gradle`, `build-maven`, `build-npm` and `build-pyproject` import it;
`build-operations` and `build-server` do not reference it at all. So D1 is two jobs, not one —
consolidating four directories that already share a surface, and onboarding two that never did.
Re-derive the importer set before scoping the work. The helper sits at the tree's root level and
carries no underscore prefix — so nothing marks it as non-collectable, the existing
`unique-fixture-basenames` doctor rule does not inspect it, and its own module docstring records that
loading it through `load_script_module` **re-registers `_build_execute_factory` in `sys.modules`**,
a hazard `test/conftest.py`'s daemon-routing fixture then has to work around by patching closure
`__globals__` dicts rather than a module object.

The **plan-lifecycle phase directories** — `phase-1-init` through `phase-4-plan`, plus `execute-task`,
`manage-lifecycle`, `manage-personas`, `manage-plan-documents` — are each small, each stage a plan
directory by hand, and none shares that staging with the others even though it is the same plan
directory.

## Goal

The slice's shared contracts have shared fixtures: one build-extension fixture surface serving all six
build directories, one plan-lifecycle staging fixture serving the phase directories. Its modules are
within budget, its preambles resolve through the shared loaders, and the root-level helper that leaks
a `sys.modules` registration is named, prefixed, and documented where the hazard is visible.

## Deliverables

1. **D1 — One build-extension fixture surface** — rename `test/plan-marshall/build_test_helpers.py` to
   `test/plan-marshall/_build_extension_fixtures.py` (underscore-prefixed per **B10**, so it is
   non-collectable and the existing `unique-fixture-basenames` rule can see it), update its importers,
   and consolidate into it the extension-contract staging currently duplicated across the six
   `build-*` directories. Preserve — and make more prominent, not less — the module docstring's record
   that loading `_build_execute_factory` through `load_script_module` re-registers it in `sys.modules`,
   because `test/conftest.py`'s `_neutralize_daemon_routing` fixture depends on that fact and works
   around it by patching closure `__globals__`. If the consolidation lets the re-registration be
   avoided altogether, **do not take that decision here**: it changes behaviour `conftest.py` reasons
   about, `conftest.py` is owned by plan `020`, and a concurrent change to both is exactly the
   collision this epic's partition exists to prevent. Record it as a proposal.
   **Rename `test/plan-marshall/discovery_test_helpers.py` to `_discovery_fixtures.py` in the same
   deliverable.** It is the second unprefixed root-level helper, invisible to the same doctor rule for
   the same reason, and its only two importers — `build-npm/test_npm_discover.py` and
   `build-gradle/test_gradle_discover_modules.py` — are both in **this** plan's slice. Plan `060`
   works in the tree it sits at the root of but explicitly does **not** own it, precisely because
   renaming it from there would break two live imports here.

   **One reference lives in a file this plan may not edit.** `test/conftest.py` names
   `test/plan-marshall/build_test_helpers.py` **by path** in the `_routing_namespaces` docstring, as
   part of its explanation of why the daemon-routing fixture patches closure `__globals__`. The rename
   makes that path stale, and `conftest.py` is plan `020`'s surface. Do not edit it: **record the
   stale reference as a proposal in the report**, naming the file, the symbol, and the corrected path,
   exactly as you do for the re-registration question above. The `grep -rln 'build_test_helpers' test`
   in the claim table will surface it — this is what to do when it does.
   *Done when:* both files are renamed with every importer updated, the six `build-*` directories
   stage the extension contract through the shared fixture rather than independently, the `sys.modules`
   hazard is documented at the fixture that causes it, and both the re-registration question and the
   stale `conftest.py` reference are recorded proposals rather than changes.

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

3. **D3 — Split every module over the budget** — the module budget landed by plan `010`, split by
   behaviour cluster into `test_{unit}_{cluster}.py`. The slice's known over-budget modules include
   `plan-orchestrator/test_orchestrator_corpus.py` (~2,230),
   `manage-architecture/test_cmd_client.py` (~1,810), `plan-marshall/test_invariants.py` (~1,580),
   `build-operations/test_extension_implementations.py` (~1,440),
   `plan-orchestrator/test_inbox_envelope.py` (~1,360),
   `plan-orchestrator/test_inbox_channel_contract.py` (~960),
   `build-maven/test_discover_modules.py` (~930) and
   `plan-marshall/test_phase_handshake_findings.py` (~920) — **re-derive the full list**, this one is
   a lead.
   *Done when:* every `test_*.py` in the slice is within the landed budget and each new module's name
   states its cluster.

4. **D4 — Normalise preambles and argument construction** — apply **B6** and **B7** across the slice:
   `conftest.load_script_module` / `get_scripts_dir` for every module preamble, `020`'s `parse_ns` for
   every `argparse.Namespace`. This slice's `manage-architecture` directory is the corpus's heaviest
   user of the architecture query CLI and therefore of hand-built namespaces for it. Where `parse_ns`
   cannot serve a call site, leave the hand-built namespace and **record the call site in the report**.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, and every `parse_ns` exception is listed with its script.

5. **D5 — Parametrize the tabular cases and strip history from prose** — apply **B5** and **B3**. This
   slice's tabular families are the build-system detection matrices (six implementations × the same
   contract questions — the single clearest parametrization target in the slice, and one that spans
   directories, so put the table in D1's shared fixture module), the architecture query filter cases,
   and the inbox envelope shape cases. Separately, strip plan ids, deliverable ids, PR numbers, lesson
   ids, and superseded-behaviour narration from test docstrings and comments, keeping present-tense
   rationale.
   *Done when:* the six build implementations are exercised against the shared contract questions
   through one parametrized surface rather than six copies, no other family of three or more
   near-identical tabular tests remains, the `plugin-doctor` `test-docstring-historical-prose` rule
   reports zero findings over this slice, and both before/after counts are reported.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the `parse_ns` exception list; the `sys.modules` re-registration proposal from D1 if one
   was found; and the per-rule `test-conventions` finding counts.
   *Done when:* the report carries all six figures, each labelled with the command that produced it.

## Out of scope

* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness. This
  constraint bites hardest in this plan: D1 touches the exact seam `conftest.py`'s
  `_neutralize_daemon_routing` fixture reasons about. Changing the fixture is a **proposal**, never an
  edit.
* **Any file under `marketplace/bundles/**`.** Excluded because test refactoring that changes
  production code is not test refactoring. A production defect found while refactoring is **recorded**,
  not fixed.
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
  implementations of it, not five duplicates — D5 parametrizes them, it does not thin them.

## Expected surface

Exactly these directories under `test/plan-marshall/`, plus the two named root-level modules and the
one rename, and nothing else:

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
| The slice is ~61,300 lines across the twenty-seven listed directories plus the named root modules | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `build_test_helpers.py` is a helper module without the underscore prefix, at the tree's root level | OBSERVED | the file path; `doctor-test-conventions.md` § `unique-fixture-basenames` detection step 1, which enumerates only `_`-prefixed files |
| Loading `_build_execute_factory` through `load_script_module` re-registers it in `sys.modules`, and `conftest.py`'s `_neutralize_daemon_routing` works around that by patching closure `__globals__` dicts | OBSERVED | `test/conftest.py`'s `_routing_namespaces` docstring, which states both facts and why patching a module object is silently partial |
| `test/plan-marshall/build-server/` is carved out of `_neutralize_daemon_routing` **by location** | OBSERVED | `test/conftest.py`'s `_DAEMON_ROUTING_CARVE_OUT` constant and the fixture that reads it |
| The six `build-*` directories stage the extension contract independently rather than through a shared surface | HYPOTHESIS — **gating for D1 and D5** | Read the module preamble of one module per `build-*` directory and record which staging each uses. If they already share a surface, D1 is a rename plus a docstring change and D5's parametrization is the whole deliverable — say so. |
| `build_test_helpers` is imported by exactly four `build-*` directories (`build-gradle`, `build-maven`, `build-npm`, `build-pyproject`) and by nothing outside this slice | OBSERVED | `grep -rln 'build_test_helpers' test` — note `test/conftest.py` names it **by path in a docstring**, which the same grep surfaces and which D1 handles as a recorded proposal, not an edit |
| `discovery_test_helpers` is imported only by `build-npm/test_npm_discover.py` and `build-gradle/test_gradle_discover_modules.py`, both in this slice | OBSERVED | `grep -rln 'discovery_test_helpers' test` |
| The phase and lifecycle directories each stage a plan directory by hand and **none shares that staging with another** | HYPOTHESIS — **asserted absence, the higher-risk half; it is D2's entire justification** | Read the staging preamble of one module per directory in the D2 group and record which helper, if any, each uses. If two already share one, D2 is an extension of that surface rather than a new one — say so rather than building a second. |
| The partition holds — every directory under `test/plan-marshall/*/` and every top-level `test/` entry appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the two deliberate exclusions. A directory in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

**The three-part done-when. All three must hold; the third alone is not success.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command.
3. **Line count drops by at least 20%** of the slice's starting total. The floor is low because the
   slice is fragmented: with no dominant module to decompose and no large duplicated-pair family to
   collapse, the reduction is the same defect in small doses across twenty-seven directories. If the
   floor cannot be reached without violating (1) or (2), **report the shortfall and stop**.

**A fourth check specific to this slice: the daemon-routing neutralization must still engage.** D1
touches the seam that fixture patches. After D1, confirm the matched positive/negative control pair
under `test/plan-marshall/script-shared/` still passes **and still discriminates** — run the negative
arm and confirm it fails when the marker that disengages the fixture is removed. A control pair that
passes in both configurations proves nothing, and this deliverable is the one most able to make that
happen.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Invoke the **git-tracked** script — `.plan/execute-script.py` is
git-ignored and absent from a fresh clone, so do not go looking for it:

```bash
python3 marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py test-conventions --test-root {directory}
```

Confirm the argument spelling against that script's own `--help` before relying on it. If the doctor
cannot be invoked, report the affected measurement **unavailable** rather than substituting a weaker
check.

**By reading — cold read, required for D5.** D5 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading.** After D5, read the parametrized build-contract table cold and confirm from its `ids=`
list alone which of the six implementations each row exercises and which contract question it asks. A
matrix whose ids do not name both axes has moved six readable modules into one unreadable one.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition.
* **Order within the plan matters.** D1 and D2 before D3: both shrink modules and change which ones
  are over budget.
* **This slice's value is in D1, D2 and D5, not in the line count.** Six build directories converging
  on one contract fixture, and nine lifecycle directories converging on one plan-staging factory, is
  worth more to the tree than the percentage either produces. Report the convergence explicitly — the
  number of directories now sharing each surface — so the outcome is legible even where the line floor
  is not met.
