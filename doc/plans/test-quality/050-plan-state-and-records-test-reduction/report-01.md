# Run report — 050-plan-state-and-records-test-reduction (run 01)

**Date (UTC):** 2026-08-16 **Branch:** `claude/test-quality-plan-execution-evap45` **PR:** [#1258](https://github.com/cuioss/plan-marshall/pull/1258) **Outcome:** partial

⛔ **The line-count floor is NOT met, and the plan's Verification section says to report the
shortfall and stop.** The slice fell from 79,763 to 79,304 lines — **−459 lines, −0.6%**, against a
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

### D1 — Decompose `test_audit_checks.py` — **SUBSTANTIALLY DONE, one done-when clause unmet** (commit `d7a4586`, prose restored in `e0bfab2`)

The plan's own guidance: *"If the run's budget is tight, decomposing `test_audit_checks.py` correctly
and reporting the check-to-module map is worth more than every other deliverable combined."* It was
done first, as a pure move, in its own commit.

`test_audit_checks.py` (8,705 lines, 92 top-level classes) became **49 modules**, each named for the
audit check it covers, plus `_audit_fixtures.py`. The directory went from 3 modules to 51.

**⚠ D1's done-when is not fully met.** It requires *"no module in that directory exceeds the
budget"*. The 49 new modules all comply (largest: 286 lines), but the pre-existing sibling
`test_audit.py` is **1,500 lines** and untouched. Splitting it is D4 work — and it is the same file
that holds the five checks the by-reading check could not map. Reported as unmet rather than deferred
silently.

**Unit for the fixture-module count, since a bare number here is ambiguous:** `_audit_fixtures.py`
carries **32 module-level names** — 26 functions and 6 constants. Of those, **3 are the loader triple**
(`_AUDIT_SCRIPT`, `_load_audit`, `audit`), leaving **29 shared staging helpers** (25 functions + 4
constants). Earlier text in this report said "29 shared helpers" without naming the unit; the
independent verifier read it as a function count and flagged it as wrong. Both counts are correct
under their own unit; only the unit was missing.

**Verified as a pure move, three independent ways:**

| Evidence | Before | After |
|---|---|---|
| Collected items, `audit-archived-plan-retrospectives/` | 542 | **542** |
| Test-function inventory (AST, `class::function`) | 446 | **446**, zero missing, zero extra |
| `audit.py` coverage (stmts/miss/branch/BrPart) | 2742 / 209 / 1146 / 116 — 90% | **identical** |

The coverage figures are identical down to the partial-branch count, which is stronger evidence than
the item count alone: the same lines and the same branches execute.

An **independent AST comparison** by the pre-PR verification sub-agent confirms it at a finer grain
than this run measured: 92/92 classes, 446/446 test methods, and **zero diffs** in method bodies
(`ast.unparse`, docstring-stripped), method docstrings, class docstrings, bases, decorators,
signatures, class-level statements, 46/46 module-level helper functions, and 16/16 constants — each in
exactly one module, none duplicated. Collection node-id **sets** (not merely counts) are byte-identical
between `origin/main` and HEAD.

**But the move was not pure in prose, and that is a real defect in a commit labelled a pure move.**
The same verifier found **162 column-0 comments dropped**. Most were `# ====` banners (52) or bare `#`
(9), and most narrative reappears as per-module docstrings — but **eight rationale blocks survived
nowhere**, and each stated a fixture invariant or a cross-reference rather than history: why
`_LEDGER_NOTATION_MAVEN` is Maven rather than pyproject (it proves the single-tool blindness closed);
why `_CONCRETE_REQUEST` passes S5 concreteness (so S5/S1 do not fire and the other signals drive the
counterfactual); why `_NON_BREAKING_COMPAT` is non-breaking; the case-insensitive matching rule and
machine-readable-identity note on the shipping-partition constants; the `data-format.md`
cross-reference on `_LEDGER_HEADER`; the 11-line table mapping each upstream check to the structured
result shape the synthesis critic consumes; and the inline-phase coupling stating that the check takes
its carve-out **from the recorder** and carries no inline branch of its own.

**All eight are restored** in `e0bfab2`, each placed beside the symbol it explains (the ledger-notation
rationale split across two files, because the two constants themselves split — the pyproject one is
shared, the Maven one module-local). This is exactly the invariant-versus-history failure D5's cold
read exists to catch, found here in D1 instead.

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

`test-docstring-historical-prose` over the slice: **66 → 24**. Of those 42 cleared, **one** was
cleared by D1's module-docstring rewrite, **40** by this deliverable's own commit (`984c257`, 22
files per `git show --stat`), and **one** by the cold-read repair commit (`19c7a69`).

**The done-when says "zero findings", and zero is not reachable without deleting contract.** The 24
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
`plan_deliverable_id` kinds match on shape alone. Over this slice that is a **24/24 false-positive
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
| Slice lines | 79,763 | 79,304 | **−459 (−0.58%)** | `wc -l` over the Expected-surface `test_*.py` set |
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
| `test-docstring-historical-prose` | 66 | **24** |
| `test-module-line-budget` | 60 | **59** |
| `test-module-preamble-boilerplate` | 40 | 40 |
| `unique-fixture-basenames` | 1 | **0** |
| `identifier-validator-corpus` | 0 | 0 |
| `subprocess-pythonpath` | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 |
| **total** | **167** | **123** |

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
| 13 | D5 prose pass | `test-docstring-historical-prose` cannot separate a lesson/task-id **citation** from a **datum** of the same shape; 24/24 residual findings are false positives | **Recorded, not fixed** — rule lives in `marketplace/bundles/**`, out of this plan's scope |
| 14 | D5 self-review | A rewrite in `test_manage_tasks_loop_exit_guard.py` left a dangling sentence | **Fixed** before commit |
| 15 | D5 self-review | Residual "is now" / "new subcommand" narration survived the first pass in 2 modules | **Fixed** before commit |
| 16 | D5 cold read | Citation strip left 5 sentences un-re-flowed, breaking at the excision point | **Fixed** (`19c7a69`) |
| 17 | D5 cold read | `test_mark_step_migrates_stale_legacy_key_on_detail_refresh` states the contract, not its cost — PARTIAL | **Fixed** — names what a duplicate key breaks |
| 18 | D5 cold read | `test_pair_outcome_emissions_regression_missing_outcome` names no consumer — PARTIAL | **Fixed** |
| 19 | D5 cold read | `test_detect_outcome_for_diffed_tasks_regression` docstring is a 7-word fragment — PARTIAL | **Fixed** — states why pending is excluded |
| 20 | D5 cold read | `test_read_dispatch_boundaries_per_phase_present` gives no motivation — PARTIAL | **Fixed** |
| 21 | D5 cold read | Cross-reference to `test_measured_zero_context_load_stays_zero`, which does not exist, describing a model the block contradicts | **Fixed** — re-pointed at the real test |
| 22 | D5 cold read | "the four phase-5-execute fact extractors"; the class's own test asserts three | **Fixed** |
| 23 | D5 cold read | "These six tests pin the contract" over a module carrying ~25 | **Fixed** |
| 24 | D5 cold read | "four concrete defects: among them" naming two | **Fixed** |
| 25 | D5 cold read | Comment citing "this lesson" with no lesson named in the file | **Fixed** |
| 26 | D5 cold read | Lesson id written as the placeholder `2026-05-15-X` | **Fixed** |
| 27 | D5 cold read | Two tests in the same role captioned "negative control" and "positive control" | **Fixed** — both are positive controls |
| 28 | D5 cold read | `detect_outcome_for_diffed_tasks` name and return key say *diff*; selector is `status == 'done'` | **Recorded, not fixed** — resolving it needs `_analyze_logs.py`, a `marketplace/bundles/**` file out of scope. Possible production defect |
| 29 | D5 cold read | `plan_id = 'mark-step-legacy-force'` reused by two tests | **Recorded** — safe under current `plan_context` isolation; would misreport as a canonicalization bug if that weakens |
| 30 | Verification sub-agent | D1's move dropped 162 column-0 comments; **8 rationale blocks** (fixture invariants and cross-references, not history) survive nowhere | **Fixed** (`e0bfab2`) — each restored beside the symbol it explains |
| 31 | Verification sub-agent | `test_assert_step_recorded.py` docstring tense-broken across a leftover wrap | **Fixed** (`e0bfab2`) |
| 32 | Verification sub-agent | `test_dispatch_termination_cause_regression.py` half-stripped: `D1:` vs `D2 (Defect 2):`, "fixes" with no antecedent, `TASK-001` citation left | **Fixed** (`e0bfab2`) |
| 33 | Verification sub-agent | `test_merge_authorization.py` docstrings open `D5(a):`/`D5(b):` — deliverable ids left with no expansion after the strip removed their anchor | **Fixed** (`e0bfab2`) |
| 34 | Verification sub-agent | `test_manage_metrics.py::test_legacy_unknown_value_still_rejected` — "was removed" narration under-stripped | **Fixed** (`e0bfab2`) |
| 35 | Verification sub-agent | `doc/plans/test-quality/README.md:71-72` describes `test_audit_checks.py` as live | **Recorded, deliberately not fixed** — shared epic brief read concurrently by `030`–`080`; outside this plan's surface |
| 36 | Verification sub-agent | `findings-test-corpus-review.md:92-96` likewise | **Recorded, deliberately not fixed** — same reason |
| 37 | Verification sub-agent | Report said "29 shared helpers" without naming the unit | **Fixed** — unit stated: 32 module-level names, 29 shared staging helpers, 3 loader names |
| 38 | Verification sub-agent | D1's done-when ("no module in that directory exceeds the budget") unmet: `test_audit.py` is 1,500 lines | **Accepted** — D1 downgraded in this report from COMPLETE to substantially-done-with-one-clause-unmet |
| 39 | Verification sub-agent | Commit `984c257`'s message says "66 to 25"; tool says 24 at HEAD | **Recorded** — message is immutable; report carries the re-derived figure |

### D5 cold-read verification (the plan's required "By reading — cold read")

Dispatched per the plan: **five rewritten modules and no other context** — no plan, no diff, no
originals, no git access — asked, for each of **ten named tests**, "what contract does this test pin,
and why does it matter?" Ratings and answers recorded; the full verbatim answers are in the agent
transcript, and the ratings are reproduced here.

| # | Test | Rating |
|---|---|---|
| 1 | `test_mark_step_failed_happy_path` | ANSWERABLE |
| 2 | `test_mark_step_force_migrates_legacy_bare_string_preserving_prior_outcome` | ANSWERABLE ("the best-argued docstring in the five modules") |
| 3 | `test_mark_step_default_prefixed_records_under_bare_key` | ANSWERABLE |
| 4 | `test_mark_step_migrates_stale_legacy_key_on_detail_refresh` | **PARTIAL** |
| 5 | `test_check_lapses_when_head_advances` | ANSWERABLE |
| 6 | `test_reader_returns_the_row_count_alongside_the_sum` + module docstring | ANSWERABLE |
| 7 | `test_manage_tasks_loop_exit_guard` module docstring | ANSWERABLE |
| 8 | `test_pair_outcome_emissions_regression_missing_outcome` | **PARTIAL** |
| 9 | `test_detect_outcome_for_diffed_tasks_regression` | **PARTIAL** |
| 10 | `test_read_dispatch_boundaries_per_phase_present` | **PARTIAL** |

**Six of ten ANSWERABLE, four PARTIAL, none UNANSWERABLE.** Per the plan — *"a test whose rewritten
docstring cannot answer both has been over-stripped; restore the invariant (not the history) and
re-read"* — all four PARTIALs were repaired in commit `19c7a69`, each by naming the **consequence**
rather than the shape.

The read found **15 defects in total**, all fixed in `19c7a69`:

**Five caused by the citation strip itself.** Removing a mid-sentence reference left the line
un-re-flowed, so the prose broke at exactly the point the citation had occupied. The cold reader
identified the pattern before its cause: *"all five sit at exactly the point where a citation, a
PR/issue reference, or a defect id would have been."* This is the single clearest lesson of the run —
see § What have we learned.

**Six pre-existing false or dangling statements**, none of which the doctor rule can see and none of
which any count-based check would catch:

| Defect | Why it matters |
|---|---|
| Cross-reference to `test_measured_zero_context_load_stays_zero` — **no such test exists**, and the two-state model it describes contradicts the four-state model the surrounding block asserts | a reader following it is led to the wrong model |
| "the **four** phase-5-execute fact extractors" — the class's own end-to-end test asserts **three** sub-keys and that `dispatch_boundaries` is *not* among them | the class docstring counts as phase-5 an extractor the class itself proves is not |
| "These **six** tests pin the contract" over a module carrying ~25, whose first test sits in a block the docstring does not admit exists | the reader's first encounter with the file is undocumented |
| "four concrete defects: among them" naming **two**, over a class whose nine tests do not map onto the enumeration | promises a census it does not deliver |
| a comment citing "this lesson" with no lesson named anywhere in the file | unresolvable from the module |
| a lesson id written as `2026-05-15-X` — an unfilled placeholder | not an identifier |

**One terminology defect:** two tests playing the identical role were captioned "negative control" and
"positive control". Both are positive controls.

**Two recorded, not fixed** (neither is prose, and neither is in this plan's remit):

- `test_analyze_logs.py::detect_outcome_for_diffed_tasks` — the function name and its return key
  `tasks_with_diff_no_outcome` both say *diff*, but the selector is purely `status == 'done'`; nothing
  in the test involves a diff or a footprint. Either the name is stale or the test under-specifies the
  real selector. Resolving it requires reading `_analyze_logs.py`, which is a `marketplace/bundles/**`
  file this plan may not edit — **recorded as a possible production defect**.
- `test_mark_step_done.py` reuses `plan_id = 'mark-step-legacy-force'` in two tests (lines ~309 and
  ~834). Safe today because `plan_context` gives each test a fresh plan root, but if that isolation
  ever weakens the second `cmd_create` collides and the failure will present as a canonicalization bug
  rather than a fixture-name collision.

**Worth recording as a positive:** the cold reader named `test_merge_authorization.py` as the model
for the corpus — module docstring stating the binding, every non-obvious test carrying both the rule
and the concrete fail-open scenario it forecloses, every control labelled as a control. *"If the other
four modules were held to this standard, [six of the findings] would not exist."*

### Independent pre-PR verification (contract Step 6)

Dispatched read-only against the plan's requirements rather than the diff's apparent intent. It wrote
its own AST comparison scripts rather than reading, which is why it caught what this run's own checks
did not.

**Confirmed:**

| Check | Verdict |
|---|---|
| D1 a pure move at code level | **YES** — zero diffs across every AST dimension; node-id sets byte-identical |
| `sys.modules['audit_under_test']` single registration | **CONFIRMED** — one writer, no other reader; neighbours use distinct keys (`audit_anchors_under_test`, `era_stamp_fill`) |
| No undeclared collateral change | **CONFIRMED** — 89 test files + 2 doc files; the doc files are the lane's own plan-directory lifecycle. Zero touches to `test/conftest.py`, `test/_shared/**`, `marketplace/bundles/**`, or `audit.py` |
| `parse_ns` conversions faithful | **CONFIRMED** field-by-field against the retired shapes; no default changed a test's meaning |
| Doctor figures | **Independently re-measured and matching this report exactly** |
| No new basename collisions | **CONFIRMED** across the whole tree |

On the one structural `parse_ns` change it went further than this run did: `_ns_dispatch` used to
leave an omitted context-load column as an **absent attribute**, where the new builder supplies
`None`. The verifier traced `cmd_record_dispatch_boundary`'s read to `getattr(args, column, None)`
(`manage-metrics.py` ~2666) and confirmed absent and `None` are the same input — so the UNMEASURED
path the docstring claims is genuinely exercised. That closes the one place the conversion could have
changed behaviour.

**It also found what this run missed** — the 162 dropped comments (above) and four prose defects in
the D5 commit, all fixed in `e0bfab2`:

| Defect | Fix |
|---|---|
| `test_assert_step_recorded.py` — "must not break … **or** the entry … **shadowed**": tense-broken across a leftover mid-clause wrap | rewritten as a present-tense consequence |
| `test_dispatch_termination_cause_regression.py` — half-stripped: `D1:` beside `D2 (Defect 2):`, a title citing "fixes" with no antecedent, and a `TASK-001` citation left in place | module docstring rewritten as two named properties |
| `test_merge_authorization.py` — docstrings still opening `D5(a):` / `D5(b):`, deliverable ids now with **no expansion anywhere**, because the strip removed the anchor beside them | replaced with the rule names ("The lapse rule", "The re-grant rule") |
| `test_manage_metrics.py` — "The legacy fallback value 'unknown' **was removed**": superseded-behaviour narration | rewritten, and now states why the handler-level check exists |

**Two stale cross-document references — recorded, deliberately NOT fixed:**

- `doc/plans/test-quality/README.md:71-72` and `findings-test-corpus-review.md:92-96` both describe
  `test_audit_checks.py` as a live ~8,700-line / ~90-class module. It no longer exists.
- **Why not fixed:** both are the epic's shared scoping briefs, read concurrently by plans `030`–`080`.
  The plan's own constraint — *"a reduction plan never edits a directory outside its own list"* — and
  the collision risk the epic README itself warns about both point the same way. The verifier reached
  the same conclusion independently and reported rather than prescribed. **For the epic owner**, not
  for this PR.

**What the verifier explicitly did NOT check**, recorded so a reader does not over-read its clean
verdict: it did not run `./pw verify` (it ran pytest over the slice and `ruff` over three directories),
did not re-measure coverage, did not audit whether the D5 cold-read dispatch happened as specified, and
did not independently re-derive the per-class check map. **This run covers the first two**: `./pw
verify` is green whole-tree (20,272 passed), and coverage was measured on both sides via a temporary
`origin/main` worktree.

**One discrepancy it caught that cannot be fixed:** commit `984c257`'s message says the prose count
went "66 to 25". The tool says 24 at HEAD, and the message was written when the figure was 25 — before
the cold-read repair cleared one more. The message is immutable history; this report carries the
re-derived figure.

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

Re-read against what actually happened, per step, with the artifact that proves it.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **NOT DONE as specified** | Only `cloud-plan-lane`. The two always-load skills and the Python-test conditional were not loaded — see § Skills loaded, where it is recorded rather than narrated as equivalent |
| 2 Branch | **DONE** | Harness-assigned `claude/test-quality-plan-execution-evap45`, kept as-is per the cloud rule. It was **absent from `origin`** on arrival and pushed as the run's first action, before any edit |
| 3 Plan directory | **DONE** | `doc/plans/test-quality/050-plan-state-and-records-test-reduction/plan.md` exists via `git mv`, numeric prefix preserved; the first-instruction block was present and needed no repair |
| 4 Implement | **DONE** | 14 commits, each with the trailer, no "Generated with Claude Code" footer. Deliverables addressed to the extent recorded above |
| 4 Per-commit gate | **DONE** | Every commit touching `*.py` preceded by a clean direct `./pw quality-gate` — read from the tools' own output (`ruff … All checks passed!`, `mypy … Success: no issues found in 408 source files`, `SPDX-header check passed`), since the direct path emits no TOON log |
| 4 Pushed | **DONE** | Pushed after every commit; `git status -sb` reports no `ahead` |
| 5 Build gate | **DONE** | git-derived verdict: 89 `*.py` of 91 changed files → gate applies. `./pw verify` → `=== verify: SUCCESS ===`, 20,272 passed. First run was RED (3 × `no-any-return` under `test-compile`); fixed and re-run |
| 6 Verification sub-agent | **DONE, and it found real defects** | Two passes. The independent pre-PR verifier (§ Independent pre-PR verification) and the plan-mandated D5 cold read (§ D5 cold-read verification). 15 + 10 findings, dispositions in § Findings |
| 7 PR cycle | **DONE** | PR #1258. No `skip-bot-review` — 89 `*.py` files, so it keeps full review. Comment surfaces and participation below |
| 8 Merge gate | see § Reviewer participation | conditions 1–3 and the condition-4 disclosure recorded there |
| 8 Bridge | **DONE** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. The two stale epic-brief references were **deliberately not edited** (§ Findings 35–36) — which also keeps this clause clean |
| 9 This check | **DONE** | this table |
| 9 What have we learned | **DONE** | below |

**GitHub access path:** the GitHub MCP server (the cloud path). No `gh` CLI in this session.
**Branch form:** harness-assigned, kept.
**Plugin cache sync:** not owed. This run edited no `marketplace/bundles/` file, and a cloud run neither
performs nor owes a sync in any case.

**Two steps are reported as not fully done**, per the rule that a skipped step is reported as skipped:
Step 1 (skills), and D1's budget clause inside Step 4 (§ Deliverables).

## What have we learned (Step 9)

**One proposal, and this run produced the evidence for it twice.**

### Proposal: an AST-faithful move is not a text-faithful move, and the contract's Step 6 sub-agent instruction should say so

**What happened.** D1 moved 92 classes by slicing source between `node.lineno` and `node.end_lineno`.
That is exact for every construct the AST models — and **silently drops every comment that precedes a
top-level definition**, because a leading comment is not part of the node. 162 column-0 comments went
missing from a commit whose message called it a pure move. Eight of them carried fixture invariants
that survive nowhere else: why a constant is Maven rather than pyproject, why a request body passes S5
concreteness, a `data-format.md` cross-reference, and the table mapping each upstream check to the
structured shape the synthesis critic consumes.

**Why nothing caught it.** Every check this run ran was AST- or behaviour-shaped and all of them were
green: 542 = 542 collected items with byte-identical node-id sets, 446 = 446 test functions, identical
coverage down to the partial-branch count, `ruff` clean, `./pw verify` SUCCESS. **A pure-move check
built on the AST cannot see a comment, because the AST does not contain one.** The defect was found
only because an independent verifier chose to diff comments as a separate dimension — a choice the
contract does not currently ask for.

**The same root cause, second instance.** D5's citation strip removed text *inside* sentences. Five
sentences were left semantically correct and mechanically broken — a clause with no subject, a tense
that no longer agrees, a line wrapped at the excision point. `ruff`, `mypy`, and the doctor rule were
all green over every one, and re-reading my own edits did not surface them; a cold reader with no
context found all five and identified the pattern before knowing its cause: *"all five sit at exactly
the point where a citation would have been."*

**The generalisation, which is what makes it worth a contract change:** *the site of a deletion is
itself a defect surface.* Step 6 currently directs the sub-agent to sweep for statements a change makes
**false** — stale claims, retired values, restatements by consumer kind. That is a *semantic* sweep,
and it is aimed at text the change did not touch. Neither instance above is a false statement. Both are
**text the change damaged in place**: still true, no longer coherent, and invisible to every automated
gate because no gate reads prose for coherence.

**Concrete proposed edit** to `.claude/skills/cloud-plan-lane/SKILL.md` § Step 6, as a bullet in the
sub-agent's instruction list:

> - when the change **removes** text rather than adding it — a citation struck from a sentence, a
>   clause deleted, a block relocated by line range — the instruction to check the **removal sites
>   themselves**, not only what the removal made false elsewhere. A deletion leaves two failure modes
>   no build gate can see: prose that is still true but no longer coherent (a clause with no subject,
>   a tense that no longer agrees, a line wrapped at the excision point), and **content the tool
>   carrying the change could not represent** — a line-range or AST-based move silently drops comments
>   that precede a definition, because a leading comment belongs to no node. Verify a "pure move" by
>   diffing **comments and prose as their own dimension**, not only the AST: an AST-faithful move is
>   not a text-faithful move.

**Per the contract, this is presented, not self-approved.** Shipping it is a separate `chore/` PR
touching only the skill, kept out of this plan's PR so the two changes do not share a review audience.
**Operator decision pending; no contract change has been made by this run.**

### Considered and NOT proposed

- **The `./pw verify` vs narrower-calls trap.** It fired exactly as the contract documents —
  `quality-gate` and `module-tests` green, `test-compile` red on three `no-any-return` errors. That is
  the contract **working**, not a gap. No change.
- **"A claim is not an outcome."** A stale generated module survived a regeneration and inflated the
  collected count 542 → 566; checking the count against the baseline rather than assuming it caught the
  defect immediately. Again the contract working. No change.
- **Step 1 skill loading.** This run did not load the named skills. That is a deviation by the run, not
  a defect in the contract, and it is recorded as such. No change proposed.

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
