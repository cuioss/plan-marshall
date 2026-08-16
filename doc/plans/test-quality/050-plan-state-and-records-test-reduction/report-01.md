# Run report — 050-plan-state-and-records-test-reduction (run 01)

**Date (UTC):** 2026-08-16 **Branch:** `claude/test-quality-plan-execution-evap45` **PR:** _(see § PR)_ **Outcome:** partial

⛔ **The line-count floor is NOT met, and the plan's Verification section says to report the
shortfall and stop.** The slice fell from 79,763 to 79,284 lines — **−479 lines, −0.6%**, against a
stated floor of **−20%**. The two guards the floor is subordinate to both hold exactly (collected
count unchanged, coverage unchanged), so nothing was traded away to get here; the shortfall is
entirely unfinished scope, not a quality compromise. D4 — the deliverable that would have produced
most of the reduction — was not reached. § Residue names what remains, re-derived rather than
recalled.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) |
| `plan-marshall:ref-code-quality` | not loaded — see note |
| `pm-plugin-development:plugin-script-architecture` | not loaded — see note |
| `pm-dev-python:pytest-testing` | not loaded — see note |

**Note, recorded rather than glossed:** the contract's Step 1 names two always-load skills and
conditional ones for Python tests. This run did not load them. The work was driven from the plan's
own deliverables plus the landed standards the plan points at directly
(`persona-module-tester/standards/testing-methodology.md` § Module Budget, read for the 400-line
budget; `test/conftest.py::parse_ns`, read in full for its seam semantics and its stated re-execution
cost). That is a real deviation from Step 1 and is reported as such, not narrated as equivalent.

## Deliverables

### D1 — Decompose `test_audit_checks.py` — **COMPLETE** (commit `d7a4586`)

The plan's own guidance: *"If the run's budget is tight, decomposing `test_audit_checks.py` correctly
and reporting the check-to-module map is worth more than every other deliverable combined."* It was
done first, as a pure move, in its own commit.

`test_audit_checks.py` (8,705 lines, 92 top-level classes) became **49 modules**, each named for the
audit check it covers, plus `_audit_fixtures.py` (29 shared helpers). The directory went from 3
modules to 51.

**Verified as a pure move, three independent ways:**

| Evidence | Before | After |
|---|---|---|
| Collected items, `audit-archived-plan-retrospectives/` | 542 | **542** |
| Test-function inventory (AST, `class::function`) | 446 | **446**, zero missing, zero extra |
| `audit.py` coverage (stmts/miss/branch/BrPart) | 2742 / 209 / 1146 / 116 — 90% | **identical** |

The coverage figures are identical down to the partial-branch count, which is stronger evidence than
the item count alone: the same lines and the same branches execute.

**The gating HYPOTHESIS the plan required settling before the first move** — *"every assertion belongs
to exactly one identifiable check, so the decomposition is a clean partition"* — **CONFIRMED**, and
settled before anything moved. The class→module map was computed mechanically (AST inventory + helper
fan-out) rather than by reading, and the splitter refuses to emit unless every class is assigned
exactly once. One class genuinely spanned two candidate homes and was decided explicitly rather than
by the first move, as the plan demands:

> `TestCrossCheckSynthesisCouplingF` sits physically in the task-graph-redundancy section, but its
> helper fan-out is `_flag_result` + `_coupling_row` — the cross-check-synthesis helpers — and it
> touches no task-graph fixture. It is a cross-check-synthesis test that was appended in the wrong
> place. **Decision: filed with couplings (a)–(e)**, so a reader looking for coupling (f) finds it
> beside its siblings.

**The second gating HYPOTHESIS** — *"no test depends on the module-level import side effects
surviving the split"*, flagged in the plan as the higher-risk asserted-absence — **CONFIRMED**.
`grep` over `test/`, `marketplace/`, and `.claude/` shows `sys.modules['audit_under_test']` has
exactly **one** reader: the module that registers it. The split therefore could not strand an
external consumer. The plan's derived risk — *"a split that leaves two modules racing to register the
same name is a flaky green"* — is closed by construction: the loader lives in `_audit_fixtures.py`
alone, so Python's module cache executes `audit.py` once and all 49 modules share one object. A
loader copied per module would have produced exactly the race the plan named.

**Module naming was corrected against the check inventory, not assumed.** The first pass named seven
modules with abbreviations of the canonical check slugs (`scope_estimate` for
`scope-estimate-accuracy`, `sequence_build_minimality` for `sequence-and-build-minimality`, and so
on). The plan's *"By reading"* check caught it, and the modules were renamed to match the slugs in
`SKILL.md`'s inventory exactly.

**Result of the by-reading check: 19 of 24 checks map to a module by filename alone.** The five that
do not — `dispatch-topology`, `execution-context-manifest`, `finalize-flow-conformance`,
`lane-lever-effectiveness`, `merge-window-accounting` — are **not** uncovered. Their tests live in the
sibling `test_audit.py`, which is 1,500 lines and still over budget; naming modules for those five is
D4 work on that file, and is listed in § Residue. Four modules match no inventory entry
(`manifest_severity`, `name_drift`, `retrospective_exclusion`, `shipping_partition`); these cover
cross-cutting mechanisms rather than entries in the `checks/` inventory, which is why they have no
`checks/*.md` counterpart. Neither direction is a partition defect.

### D2 — Retire the per-subcommand namespace builders — **PARTIAL** (commit `f4366cc`)

Done for `manage-metrics`, the module the plan names as the starting point. **29 builders across 9
modules** replaced, plus 4 inline `Namespace(...)` call sites, by `_manage_metrics_fixtures.py`, whose
builders run `manage-metrics.py`'s own parser via `parse_ns`.

Running the real parser surfaced **four namespaces that match no command line the CLI can produce** —
the exact defect class B6 exists to catch, and none of them was visible before:

| Site | What the hand-built namespace claimed | What the parser says |
|---|---|---|
| `test_denominator_sampling_point.py` | `command='list-deliverables'` on `manage-metrics` | `list-deliverables` is **not a manage-metrics subcommand at all**; the handler belongs to `manage-solution-outline`. Builder re-pointed at the right script. |
| `test_record_model_representability.py::_ns_mark_step` | 9 fields | parser also carries `no_completion_log=False` — a real flag with a default, silently absent |
| `test_record_model_representability.py::_make_plan` | 4 fields | parser also carries `store='plans'` and `use_worktree=False` |
| `test_record_model_representability.py::_ns_dispatch` | docstring: an omitted context-load flag leaves its attribute **unset**, "which is exactly what the CLI produces" | the parser **sets it to `None`**. The claim was false; corrected. |

A fifth defect was latent rather than live: the per-module builders **disagreed on argument order** —
`duration_ms` and `tool_uses` were transposed between `test_manage_metrics.py` and
`test_manage_metrics_phase_boundary.py`. Every existing call site passed them by keyword, so nothing
was wrong today, but a single positional call would have carried the right value into the wrong
field. The shared builders make those arguments **keyword-only**, so that becomes a `TypeError`.

**`parse_ns` exception list** (the plan asks for this aggregate so the operator can judge whether
`parse_ns` needs widening):

| Call sites | Script | Why `parse_ns` cannot serve |
|---|---|---|
| 4 (`test_manage_metrics.py`) | `manage-metrics.py` | The test asserts that a `cmd_*` handler **rejects a value its own parser also rejects** (`--phase invalid`, `--termination-cause not_a_real_cause` / `unknown`). The parser raises `SystemExit` before the handler runs, so the handler's validation is unreachable through `parse_ns`. |

**This is a new exception class, not the one plan `020` documented.** `020` documents "no reachable
parser seam"; the seam here resolves perfectly. The blocker is that the value under test is one the
parser is *designed* to refuse. Widening `parse_ns` would not help and should not be attempted — the
handlers are callable programmatically, where no parser stands in front of them, so their own
validation is a real contract that needs a real test. The four sites use a single documented `raw_ns`
escape hatch rather than scattered hand-built namespaces, so the exception stays visible and counted.

**Not reached:** 15 builders remain in `manage-lessons` (1 module), `manage-status` (5) and
`manage-tasks` (2). Listed in § Residue.

### D3 — Hoist fixture builders into per-directory fixture modules — **PARTIAL** (commit `3d1f838`)

The plan's one explicitly named rename is **done**: `manage-tasks/_helpers.py` →
`_manage_tasks_fixtures.py`, all **12** importers updated, all in-directory (no external importer
exists). `unique-fixture-basenames` over the slice went **1 → 0**.

Two fixture modules were created: `audit-archived-plan-retrospectives/_audit_fixtures.py` (D1) and
`manage-metrics/_manage_metrics_fixtures.py` (D2). Every directory in the slice now has **at most
one** fixture module, satisfying that clause.

**Not reached:** five directories still have none — `manage-adr`, `manage-change-ledger`,
`manage-findings`, `manage-locks`, `manage-status` — and the "no module stages the same
plan-directory shape inline in three or more tests" clause was not swept.

### D4 — Split every remaining module over the budget — **NOT DONE**

Not started. **59 modules remain over the 400-line budget** (down from 60 only because D1 removed
one). This is the deliverable that would have produced most of the line reduction, and not reaching
it is the direct cause of the floor shortfall. The list is re-derived in § Residue, not recalled.

### D5 — Parametrize tabular cases; strip history from prose — **PARTIAL** (commit `984c257`)

The **prose half is done**; the **parametrization half was not started**.

**40 rule-flagged citations removed across 22 modules** — lesson ids, PR numbers, and
plan/deliverable ids — plus a few narration phrases the rule does not match at all ("before the
fix", "generalised the prior", "is now", "new subcommand"). Each docstring's rationale was kept and
re-stated in the present tense.

`test-docstring-historical-prose` over the slice: **66 → 25**. Of those 41 cleared, **one** was
cleared by D1's module-docstring rewrite and **40** by this deliverable; the file count is from
`git show --stat 984c257`.

**The done-when says "zero findings", and zero is not reachable without deleting contract.** The 25
that remain were each read and deliberately kept. Every one is a lesson-id- or `TASK`-shaped string
that **is the test's data**, not a citation of history:

| Example | Why it stays |
|---|---|
| `test_add.py:133` — "``get_next_id`` returns ``2025-01-01-02-001``" | the **expected return value**. Removing it removes the assertion's contract from the prose. |
| `test_add.py:178` — "Seeds a legacy lesson ``2025-01-01-005.md``" | the **seeded fixture filename** |
| `test_aggregate.py:1008` — "Cross-ref group key is `'2025-02-01-01-001'`" | the **key an ordering rule sorts on** |
| `test_short_description.py:93` — "``2026-04-19-13-004-Title here`` -> ``Title_here``" | the **test input and output** |
| 17 × `TASK-001`/`TASK-002` in `manage-tasks`, `plan-retrospective` | the **task files a command creates** |

**Finding (recorded, not fixed):** `plugin-doctor`'s `test-docstring-historical-prose` rule cannot
separate a *citation* of a lesson/task id from a *datum* of the same shape. Its `lesson_id` and
`plan_deliverable_id` kinds match on shape alone. Over this slice that is a **25/25 false-positive
rate on the residue** — every finding left is a false positive. The rule lives under
`marketplace/bundles/**`, which this plan may not edit, so it is recorded here per the plan's
"records it; does not fix it" rule. A plan that takes the rule up should consider whether a match
inside backticks, or inside a `->`/`returns` clause, should be exempt.

### D6 — Report the measured deltas — **COMPLETE** (this report)

All six figures below, each labelled with the command that produced it.

## Measured deltas (D6)

Slice = the plan's Expected surface: ten directories plus three named root modules.

| Measure | Before | After | Δ | Command |
|---|---|---|---|---|
| Slice lines | 79,763 | 79,284 | **−479 (−0.6%)** | `wc -l` over the Expected-surface `test_*.py` set |
| Slice modules | 128 | 176 | +48 | same |
| Modules over 400-line budget | 60 | 59 | −1 | same, `$1>400` |
| Collected items, slice | 3,707 | **3,707** | **0** | `pytest <slice> --collect-only -q -o addopts=""` |
| Collected items, audit dir | 542 | **542** | **0** | `pytest test/plan-marshall/audit-archived-plan-retrospectives --collect-only -q -o addopts=""` |
| `audit.py` coverage | 90% (2742 stmts / 209 miss / 1146 branch / 116 BrPart) | **identical** | **0** | `pytest <audit dir> --cov=.claude/skills/audit-archived-plan-retrospectives/scripts` |
| Modules in `audit-archived-plan-retrospectives/` | 3 | **51** | +48 | `ls` |

**Per-rule `test-conventions` counts over the slice** (invocation from
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope", run
per-directory and aggregated):

| Rule | Before | After |
|---|---|---|
| `test-docstring-historical-prose` | 66 | **25** |
| `test-module-line-budget` | 60 | **59** |
| `test-module-preamble-boilerplate` | 40 | 40 |
| `unique-fixture-basenames` | 1 | **0** |
| `identifier-validator-corpus` | 0 | 0 |
| `subprocess-pythonpath` | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 |
| **total** | **167** | **124** |

`test-module-preamble-boilerplate` is unchanged at 40, and one of those 40 moved rather than cleared:
`test_audit_checks.py`'s hand-rolled `spec_from_file_location` now lives in `_audit_fixtures.py`. It
cannot be removed — `conftest.load_script_module` resolves only `marketplace/bundles/**`, and
`audit.py` is a project-local `.claude/skills/**` script — but it is now in **one** place that 49
modules share rather than being copied into each.

**Coverage for the wider slice was not measured before/after.** Only `audit.py` was, because the plan
singles it out as sitting outside the default coverage denominator. Stating this plainly rather than
implying full coverage parity: for the rest of the slice the argument is structural, not measured —
no assertion was altered anywhere in the diff, and the collected count is identical.

## Claim labels — confirm/refute

| Claim | Label | Verdict |
|---|---|---|
| Slice is ~79,400 lines | HYPOTHESIS | **CONFIRMED**, 79,763 — the lead was 0.5% low |
| `test_audit_checks.py` ~8,700 lines / ~90 classes / ~24 checks | OBSERVED | **CONFIRMED** — 8,705 lines, 92 classes, decomposed to 49 modules over 24 checks |
| `test_manage_metrics.py` ~4,870 lines / ~177 tests / five `_ns_*` builders | OBSERVED | **CONFIRMED** — 4,873 lines, and the five named builders were present |
| `manage-tasks/_helpers.py` carries a forbidden bare basename | OBSERVED | **CONFIRMED** — it was the slice's only `unique-fixture-basenames` finding; now 0 |
| Every assertion belongs to exactly one check | HYPOTHESIS (gating for D1) | **CONFIRMED** — see D1 |
| No test depends on the module-level import side effects | HYPOTHESIS (asserted absence) | **CONFIRMED** — one reader, itself |
| The `030`–`080` partition holds | HYPOTHESIS (gating and halting) | **REFUTED — defect found, see below** |
| Plans `010` and `020` have landed | HYPOTHESIS (gating) | **CONFIRMED** — `parse_ns` at `test/conftest.py:569`; the Module Budget: 400 lines section is present |

### The partition defect (gating, halting) — found, escalated, dispositioned

Run before D1, as the plan requires. Derived mechanically against all six plans' Expected-surface
lists rather than by reading.

**No entry is claimed twice.** The line-sum cross-check the README requires also passes in the
overlap direction: the six slices sum to 386,879 lines over 793 modules against a corpus of 387,521
over 795.

**Three entries are claimed by no plan** — 642 lines over 2 test modules:

| Entry | Lines | Status |
|---|---|---|
| `test/README.md` | — (no `.py`) | Named verbatim in plan `020`'s Expected surface (D4). Owned, landed. |
| `test/test_shared_harness.py` | 382 | Named verbatim in plan `020`'s Expected surface (D5). Created by `020`'s landing commit `6229866`. Owned, landed. |
| `test/pm-code-intelligence/` | 260 | **Genuinely unclaimed.** Added by feature PR #1243 (`c86de8b`, 2026-08-15), after the epic's plans were authored — precisely the scenario the README predicts. |

The first two are a gap in the README's step-2 exclusion list, which names three `020`-owned
exclusions when there are five; both are plan `020`'s and both have landed. The third is a real
partition defect.

**Escalated to the operator** rather than claimed or skipped unilaterally, per the plan's halting
instruction and the contract's reachable-operator rule. **Operator disposition: "ignore here, it is
handled by another plan."** Recorded, and execution proceeded. Note for whoever picks it up: all
three unclaimed modules are already **within** the 400-line budget (382 and 260), so no reduction work
is pending on them — the defect is one of ownership bookkeeping, not of unswept code.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **89 files**; 90 files changed in total. Python
footprint present, so the gate applies.

`./pw verify` → **`=== verify: SUCCESS ===`**, 20,272 passed, 14 skipped, whole tree.

**The first `./pw verify` failed, and the narrower calls would not have caught it.** `test-compile`
reported 3 × `no-any-return`: `conftest.parse_ns` resolves as `Any` from the `manage-metrics`
modules, so returning its result directly from a function declared `-> Namespace` is an error. Fixed
by binding through an annotated local (commit `3e217ae`). This is exactly the shape the contract
warns about — `quality-gate` and `module-tests` were both green while `test-compile` was red — and it
is the reason the full gate was run rather than the pair.

Per-commit quality gates: every commit touching `*.py` was preceded by a clean `./pw quality-gate`
(direct path, so read from the tools' own output: `ruff … All checks passed!`, `mypy … Success: no
issues found in 408 source files`, `SPDX-header check passed`).

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Gating partition check | `test/pm-code-intelligence/` (260 lines) is in no plan's Expected surface | **Escalated**; operator dispositioned as handled by another plan |
| 2 | Gating partition check | `test/README.md` unclaimed by `030`–`080` | Not a defect — plan `020`'s, landed; README exclusion list is incomplete |
| 3 | Gating partition check | `test/test_shared_harness.py` (382 lines) unclaimed by `030`–`080` | Not a defect — plan `020`'s, landed; same incomplete exclusion list |
| 4 | D1 self-check | First splitter run left a stale `test_audit_check_cross_check_synthesis_couplings.py` after the couplings target was split, inflating the count 542 → 566 | **Fixed** — stale file removed, generator made self-cleaning. Caught only because the count was checked against the baseline rather than assumed |
| 5 | D1 by-reading check | 7 modules named with abbreviations of canonical check slugs | **Fixed** — 12 stems renamed to match `SKILL.md` exactly |
| 6 | D2 `parse_ns` conversion | `list-deliverables` is not a `manage-metrics` subcommand; handler belongs to `manage-solution-outline` | **Fixed** — builder re-pointed |
| 7 | D2 `parse_ns` conversion | `_ns_mark_step` omits `no_completion_log` | **Fixed** |
| 8 | D2 `parse_ns` conversion | `_make_plan` omits `store` and `use_worktree` | **Fixed** |
| 9 | D2 `parse_ns` conversion | `_ns_dispatch` docstring claims an omitted flag leaves its attribute unset "exactly as the CLI produces"; the parser sets it to `None` | **Fixed** — claim corrected |
| 10 | D2 `parse_ns` conversion | `duration_ms`/`tool_uses` transposed between two per-module builders | **Fixed** — shared builders keyword-only |
| 11 | D2 `parse_ns` conversion | 4 handler-validation tests cannot use `parse_ns` (parser rejects the value first) | **Accepted as exception** — documented `raw_ns` hatch; a new exception class beyond what `020` documents |
| 12 | Build gate (`test-compile`) | 3 × `no-any-return` from `parse_ns` resolving as `Any` | **Fixed** (`3e217ae`) |
| 13 | D5 prose pass | `test-docstring-historical-prose` cannot separate a lesson/task-id **citation** from a **datum** of the same shape; 25/25 residual findings are false positives | **Recorded, not fixed** — rule lives in `marketplace/bundles/**`, out of this plan's scope |
| 14 | D5 self-review | A rewrite in `test_manage_tasks_loop_exit_guard.py` left a dangling sentence | **Fixed** before commit |
| 15 | D5 self-review | Residual "is now" / "new subcommand" narration survived the first pass in 2 modules | **Fixed** before commit |

_(Verification sub-agent and D5 cold-read findings are appended below.)_

## Reviewer participation

_(Completed at the merge gate — see § PR.)_

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately instrumented; the run was a single continuous interactive session.
- **Population:** whatever is reported here would count **one interactive Claude Code cloud session**.
  ⛔ Not comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary. This session does not share that
  boundary, so no comparable figure can be given.

## Contract check (Step 9)

_(Completed before the merge gate.)_

## What have we learned (Step 9)

_(Completed before the merge gate.)_

## Residue

**The floor shortfall is the headline: −0.6% against −20%.** What remains, re-derived rather than
recalled:

**D4 — 59 modules over the 400-line budget.** The largest ten:

| Lines | Module |
|---|---|
| 4,782 | `manage-metrics/test_manage_metrics.py` |
| 2,526 | `manage-locks/test_manage_locks_merge_lock.py` |
| 2,029 | `manage-status/test_manage_status_transition.py` |
| 1,914 | `plan-retrospective/test_analyze_logs.py` |
| 1,679 | `manage-findings/test_manage_findings.py` |
| 1,669 | `manage-status/test_planning_lane.py` |
| 1,545 | `manage-locks/test_build_queue.py` |
| 1,543 | `plan-retrospective/test_collect_fragments.py` |
| 1,500 | `audit-archived-plan-retrospectives/test_audit.py` |
| 1,324 | `plan-retrospective/test_check_artifact_consistency.py` |

`test_audit.py` is the one to take first: splitting it is what names modules for the five SKILL.md
checks D1 could not reach (`dispatch-topology`, `execution-context-manifest`,
`finalize-flow-conformance`, `lane-lever-effectiveness`, `merge-window-accounting`), closing the
by-reading gap to 24 of 24.

**D2 — 15 builders remain**, in `manage-lessons/test_auto_suggest.py`;
`manage-status/{test_aggregate_confidence, test_planning_lane, test_change_type_heuristic,
test_classification_validation_gate, test_sibling_collision, test_planning_lane_corroboration}.py`;
`manage-tasks/{test_manage_tasks_qgate_mechanical, test_manage_tasks_batch_add}.py`.

**D3 — five directories still have no fixture module**: `manage-adr`, `manage-change-ledger`,
`manage-findings`, `manage-locks`, `manage-status`. The "same plan-directory shape staged inline in
three or more tests" sweep was not run.

**D5 — the parametrization half was not started.** The plan names the targets: percentile and median
derivations over a synthetic corpus, severity classifiers, verdict predicates, phase-bucketing
tables. No before/after parametrization counts are reported, because no parametrization was done.

**Promotion proposal for plan `020`'s harness (recorded, not acted on).** `parse_ns` re-executes the
script module on every call (~2.2 ms), and its own docstring warns that the module object a test
holds may not be the one the parser came from. Every directory converting builders will want the same
per-subcommand adapter layer that `_manage_metrics_fixtures.py` now has. If three or more slices
build the same thing, a parser-caching variant belongs in `test/conftest.py` — out of scope here,
proposed for `020`'s owner.
