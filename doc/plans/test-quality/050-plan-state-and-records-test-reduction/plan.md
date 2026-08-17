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

# Reduce the plan-state and records test slice

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

The plan-state and records slice — status, tasks, lessons, findings, locks, metrics, retrospectives,
and the archived-plan audit — is the epic's largest at roughly 79,400 lines of `test_*.py`. It is
also the slice where the corpus's structural defect is most extreme, and where it is most clearly a
*packaging* defect rather than a quality one.

`audit-archived-plan-retrospectives/test_audit_checks.py` is a single module of roughly **8,700
lines** carrying about **90 test classes**. It is not a grab bag: it covers roughly two dozen
independent audit checks — name drift, dormation, retrospective-token exclusion, threshold
centralization, exploration share, global-log analysis, token economics, quality chain,
sequence-and-build minimality, input integrity, cross-check synthesis, preference patterns, and more —
each with its own fixture builder defined inline at the point of first use, each with its own
positive/negative controls. The tests are good. They are twenty-four modules wearing one filename.

`manage-metrics/test_manage_metrics.py` is roughly 4,870 lines for about 177 tests, opening with five
hand-written `_ns_*` builders (`_ns_start_phase`, `_ns_end_phase`, `_ns_generate`, `_ns_enrich`,
`_ns_accumulate`) — the private re-implementation of the shared `parse_ns` helper that plan `020`
lands, one per subcommand, none carrying the real parser's defaults.

Across the slice the same two costs recur: fixture builders defined mid-module rather than in a
`_{domain}_fixtures.py`, so a sibling module that needs the same plan-directory staging writes its
own; and per-test staging of plan directories, metrics files, and finding stores that three or more
tests in the same module share verbatim.

## Goal

The slice's modules match the checks they cover: one module per behaviour cluster, its fixture
builders in a named fixture module its siblings can reuse, its argument namespaces built from the real
parser. Every check pinned today is still pinned, discoverable by filename rather than by scrolling.

## Deliverables

Work the slice **largest module first** — in this slice that ordering is not a heuristic, it is where
almost all the value is.

1. **D1 — Decompose `test_audit_checks.py`** — split the ~8,700-line module into one module per audit
   check, named for the check it covers (`test_audit_check_{name}.py`), each within the module budget
   landed by plan `010`. The per-check fixture builders currently defined inline — `_write_token_plan`,
   `_inputs`, and their siblings — move into
   `audit-archived-plan-retrospectives/_audit_fixtures.py` where more than one module needs them, and
   stay module-local where only one does. The module docstring's coverage inventory splits with it:
   each new module's docstring states what its check asserts, in the present tense.
   *Done when:* no module in that directory exceeds the budget, each is named for its check, the
   collected test count for the directory is unchanged, and the shared builders live in one fixture
   module rather than in whichever test module happened to define them first.

2. **D2 — Retire the per-subcommand namespace builders** — apply **B6** across the slice, starting
   with `manage-metrics/test_manage_metrics.py`'s five `_ns_*` builders and the equivalents elsewhere.
   Replace them with `020`'s `parse_ns`, which runs the script's own parser and therefore carries the
   defaults a hand-built namespace silently omits. Where `parse_ns` cannot serve a call site — a script
   with no reachable parser seam, which `020` documents — leave the hand-built builder and **record
   the call site in the report**: the aggregate tells the operator whether `parse_ns` needs widening.
   *Done when:* every per-subcommand `_ns_*` builder in the slice is either replaced or listed as an
   exception with its script named.

3. **D3 — Hoist fixture builders into per-directory fixture modules** — apply **B4** and **B10**. Each
   directory in the slice gets a `_{domain}_fixtures.py` holding the plan-directory, metrics-file,
   finding-store and lesson-store staging its modules share; per-test staging repeated three or more
   times in a module becomes a fixture. `manage-lessons/_lessons_helpers.py`,
   `manage-tasks/_helpers.py` and `plan-retrospective/_plan_retrospective_fixtures.py` already exist —
   extend them rather than adding a second module beside them, and rename `manage-tasks/_helpers.py`
   to `manage-tasks/_manage_tasks_fixtures.py`, since the bare `_helpers.py` spelling is one of the
   three basenames the existing `unique-fixture-basenames` doctor rule forbids **by name**.
   *Done when:* each directory has at most one fixture module, `manage-tasks/_helpers.py` is renamed
   with every importer updated, none of the slice's fixture modules carries a bare generic basename,
   and no module stages the same plan-directory shape inline in three or more tests.

4. **D4 — Split every remaining module over the budget** — after D1 and D3, split what is still over.
   The slice's known over-budget modules include `manage-metrics/test_manage_metrics.py` (~4,870),
   `manage-locks/test_manage_locks_merge_lock.py` (~2,530),
   `manage-status/test_manage_status_transition.py` (~2,030),
   `plan-retrospective/test_analyze_logs.py` (~1,750),
   `manage-findings/test_manage_findings.py` (~1,680), `manage-status/test_planning_lane.py` (~1,670)
   and `manage-locks/test_build_queue.py` (~1,550) — **re-derive the full list**, this one is a lead.
   *Done when:* every `test_*.py` in the slice is within the landed budget and each new module's name
   states its cluster.

5. **D5 — Parametrize the tabular cases and strip history from prose** — apply **B5** and **B3**.
   This slice's tabular families are the threshold and classifier tests: percentile and median
   derivations over a synthetic corpus, severity classifiers, verdict predicates, phase-bucketing
   tables. Collapse each into a parametrized table with an `ids=` list that carries what the per-test
   names said. Separately, strip plan ids, deliverable ids ("D4 — token-economics cross-plan check"),
   PR numbers, lesson ids, and superseded-behaviour narration from test docstrings and comments,
   keeping present-tense rationale.
   *Done when:* no family of three or more near-identical threshold/classifier tests remains, the
   `plugin-doctor` `test-docstring-historical-prose` rule reports zero findings over this slice, and
   both before/after counts are reported.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the module count for `audit-archived-plan-retrospectives/` before and after; the
   `parse_ns` exception list; and the per-rule `test-conventions` finding counts.
   *Done when:* the report carries all six figures, each labelled with the command that produced it.

## Out of scope

* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness, and a
  concurrent edit to it is a guaranteed collision. A helper this slice needs that `020` did not build
  goes into the slice's own `_{domain}_fixtures.py`, and the promotion is **recorded as a proposal**.
* **Any file under `marketplace/bundles/**` — and note this slice's special case:
  `test/plan-marshall/audit-archived-plan-retrospectives/` tests a script under
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, which is **also** out of
  scope.** Excluded because test refactoring that changes the code under test is not test refactoring.
  A production defect found while refactoring is **recorded**, not fixed.
* **Any test directory outside this plan's list.** Excluded because the neighbouring directory belongs
  to a concurrently-running sibling plan.
* **Deleting a test because it looks redundant.** Excluded because "redundant" is the judgement a line
  target corrupts. Two tests that assert the same thing are merged into one parametrized case, which
  preserves the collected count; a test that is genuinely dead is **reported**, not removed.
* **Reworking the audit checks' own coverage.** D1 is a *move*, not a rewrite: every assertion in
  `test_audit_checks.py` survives into exactly one of the new modules, unchanged. Excluded because a
  decomposition that also rewrites assertions cannot be reviewed — a reviewer cannot tell a relocated
  test from a changed one, and this module is ~8,700 lines of it.

## Expected surface

Exactly these directories under `test/plan-marshall/`, plus the three named root-level modules, and
nothing else:

- `audit-archived-plan-retrospectives/`, `manage-adr/`, `manage-change-ledger/`, `manage-findings/`,
  `manage-lessons/`, `manage-locks/`, `manage-metrics/`, `manage-status/`, `manage-tasks/`,
  `plan-retrospective/`
- `test_lessons_capture_workflow.py`, `test_lessons_consult_workflow.py`,
  `test_recipe_lesson_cleanup.py`

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~79,400 lines across the ten listed directories plus the named root modules | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `test_audit_checks.py` is ~8,700 lines with ~90 test classes covering roughly two dozen independent checks | OBSERVED | the file; `grep -n '^class Test' test/plan-marshall/audit-archived-plan-retrospectives/test_audit_checks.py` |
| `test_manage_metrics.py` is ~4,870 lines for ~177 tests and opens with five per-subcommand `_ns_*` builders | OBSERVED | the file's first ~100 lines |
| `manage-tasks/_helpers.py` carries the bare generic basename the existing `unique-fixture-basenames` rule forbids | OBSERVED | the file path; `doctor-test-conventions.md` § `unique-fixture-basenames` detection step 2 |
| Every assertion in `test_audit_checks.py` belongs to exactly one identifiable check, so the decomposition is a clean partition | HYPOTHESIS — **gating for D1; settle it before moving anything** | Map every one of the ~90 classes to its check before the first move, and record the map in the report. A class that spans two checks is the case that decides whether a module is duplicated or a check is split — decide it explicitly, do not let the first move settle it. |
| No test in this slice depends on `test_audit_checks.py`'s module-level import side effects surviving the split | HYPOTHESIS — **asserted absence, the higher-risk half** | The module loads `audit.py` via `spec_from_file_location` and registers it in `sys.modules` under a fixed name at import time. Confirm what else in the tree reads that `sys.modules` entry before splitting the loader across modules; a split that leaves two modules racing to register the same name is a flaky green. |
| The partition holds — every directory under `test/plan-marshall/*/`, every file at the root of `test/plan-marshall/`, and every top-level `test/` entry other than `plan-marshall/` itself (which the first two clauses already decompose) appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the three deliberate exclusions. An entry in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

> ⛔ **SUPERSEDED IN PART — read this before the three conditions below.** This plan landed carrying a
> three-part done-when whose third part is a **20% line floor**. That floor is **retired**, and so is
> every other per-slice floor in this epic: four executed plans returned between 0.52% and 2.56%
> against floors of 20–30%, and three of the six floors turned out to exceed their slice's entire
> comment-and-docstring volume. A run re-entering this plan holds the **five conditions** in
> `doc/plans/test-quality/README.md` § "What a reduction run must hold" — collected count, coverage,
> skipped count, wall-clock, and a line delta that is **measured and reported, never targeted**.
> Where that section and the text below disagree, **that section governs and the run reports the
> disagreement**. Everything else below — the per-deliverable checks, the cold read, the executable
> gate — stands unchanged.


**The three-part done-when. All three must hold; the third alone is not success.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. For D1 specifically, capture the count for
   `audit-archived-plan-retrospectives/` alone before and after the decomposition — it must be
   **exactly** equal, because D1 is a move.
2. **Coverage does not decrease** for the bundle paths this slice exercises, and for
   `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, which is exercised by D1's
   modules but sits outside the default coverage denominator — measure it explicitly.
3. **Line count drops by at least 20%** of the slice's starting total. The floor is the epic's lowest,
   deliberately: D1 is a decomposition, and a decomposition adds per-module preamble even as it
   improves the tree. The value of this plan is concentrated in navigability and in D2/D3/D5, not in
   raw line removal. If the floor cannot be reached without violating (1) or (2), **report the
   shortfall and stop**.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Use the invocation in
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope" — a **bare**
call to `doctor-marketplace.py` fails with `ModuleNotFoundError: No module named '_dep_detection'`,
because the script has no `sys.path` bootstrap, so the invocation supplies the five scripts
directories it needs on `PYTHONPATH`. It is one command, touches no `.plan/`, and writes nothing. If
it cannot be made to run, report the affected measurement **unavailable** rather than substituting a
weaker check.

**By reading — cold read, required for D5.** D5 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much history is removed but that the **invariant** is removed
along with it. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

**By reading.** After D1, list the new module filenames beside the audit checks named in
`.claude/skills/audit-archived-plan-retrospectives/SKILL.md`'s check inventory. A reader must be able
to find the tests for any named check from the filename alone, without opening a file. A check with no
corresponding module, or a module whose name matches no check, is a partition defect — report it
rather than papering over it, since it may mean the check has no tests at all.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition.
* **D1 is this plan.** If the run's budget is tight, decomposing `test_audit_checks.py` correctly and
  reporting the check-to-module map is worth more than every other deliverable combined. Do it first,
  do it as a pure move, and commit it separately from anything that rewrites an assertion so the
  reviewer can read the diff as a relocation.
* **Order within the plan matters.** D1 and D3 before D4: both change which modules are over budget.
