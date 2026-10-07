# Run report — 460-audit-ledger-reader-reads-undatable-zero-as-measured (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/audit-ledger-undatable-zero-ef7sl5`    **PR:** [#1278](https://github.com/cuioss/plan-marshall/pull/1278)    **Outcome:** completed

## Skills loaded

Loaded by bundle path (the plugin route was not attempted; the bundle path works in a fresh clone):

| Skill | Why |
|---|---|
| `cloud-plan-lane` (`.claude/skills/cloud-plan-lane/SKILL.md`) | The working contract, loaded as the run's first action |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

Not loaded, deliberately: `persona-implementer`, `plugin-architecture`, `ref-asciidoc`,
`ref-workflow-architecture`, `persona-security-expert` — the change touches one Python reader, its
tests, and one Markdown check doc; no `SKILL.md`, no `.adoc`, no security surface. Every skill named
above was obtainable; none had to be reported unavailable.

## Deliverables

### D0 — consumer audit of `audit.py`'s own zero-handling (derived, not sampled)

`_parse_dispatch_boundary_totals`'s result is consumed at **exactly one site**, established by reading
every occurrence of the `ledger` local across the file rather than by sampling: the per-phase loop in
`_collect_billing_composition_rows` (`audit.py:6932-6943`). Nothing else in `audit.py` reads a
dispatch-boundary ledger — the only other `metrics-dispatch-boundaries` mentions in the file are prose.

| # | Consumer | Field(s) | What it concludes from a zero |
|---|---|---|---|
| C1 | `phase_reconciled = ledger.get("total_tokens", 0) > fields.get("total_tokens", 0)` (`:6935`) | `total_tokens` | **Outside the gate.** `total_tokens` is a legacy column, not in `_BC_LEDGER_UNMEASURABLE_FIELDS`, so D1 does not touch it. An absent ledger reads as `0`, which can never exceed a non-negative row value — no reconciliation is claimed from it. |
| C2a | `if usage_field in fields or ledger_value > 0: has_billing = True` (`:6939`) | the four context-load fields | Strictly `> 0`, so a **measured zero already fails to set `has_billing`** today. An absent field behaves identically. D1 changes nothing here. |
| C2b | `if ledger_value > row_value: phase_reconciled = True` (`:6941`) | same | `row_value >= 0` always, so `0 > row_value` is never true. Measured-zero and absent are indistinguishable. |
| C2c | `billing[usage_field] += max(row_value, ledger_value)` (`:6943`) | same | `max(row_value, 0) == row_value`. Measured-zero and absent are indistinguishable. |
| C3 | `_BillingCompositionRow.weighted` / `.billing_total` / `.billing_share` | `self.billing` | Consume only what C2c built; unchanged because C2c is unchanged. |
| C4 | `has_billing` → `billing_rows` population, `_bc_figure` `population` / `floor_population` | — | Consume only what C2a set; unchanged. |

**Verdict: the asserted absence HOLDS — no consumer is left stale.** Every consumer of the four
context-load fields routes the ledger value through `> 0`, `> row_value`, or `max(row_value, ·)`, in
each of which an absent field and a measured `0` are indistinguishable *by construction*. This is the
property the function's own docstring already claimed for an absent file (`max(row, 0) == row`),
holding one level finer.

**The consequence, stated plainly: D1 is semantically correct but arithmetically INERT in today's
emitted figures.** It does not change any corpus number. What it changes is that the reader stops
*asserting* a measurement it cannot date — which matters for the reader's contract, for the next
consumer added, and for the agreement between the two parallel readers. It would be an over-claim to
present this as correcting wrong corpus figures, and this report does not.

**Verified differentially, not only by reading.** A throwaway instrument ran the whole
`cross_billing_composition` check twice over a six-plan corpus — one plan per ledger shape the gate can
distinguish (fingerprint-free all-zero; nonzero fingerprint; token fingerprint; mixed rows; a ledger
larger than the phase row so `max()` actually fires; an unrecognised cell beside zeros) — once with the
shipped gated reader and once with the pre-fix ungated reader monkeypatched back in. The two full result
dicts compared **equal**, while a pre-patch sanity assertion confirmed the two readers genuinely
disagree on the affected ledger (`input_tokens` absent under the gate, `0` under the pre-fix reader), so
the equality is a real result rather than two identical code paths.

That instrument was **deliberately not committed**. It embeds a whole copy of the pre-fix reader,
which is exactly the stale-double hazard this lane warns about: once `_parse_dispatch_boundary_totals`
moves, the copy silently diverges and the comparison stops testing what its name claims. The method and
the result are recorded here instead; the file itself was disposable and is gone.

### D1 — the provenance gate in `_parse_dispatch_boundary_totals`

Implemented in commit `2ccec2c`. The row loop became two passes:

1. **First pass**, per cell — every verdict that depends on the cell alone. A legacy column keeps its
   numeric-default path untouched. Among the four context-load columns: the `unmeasured` token sets the
   row fingerprint and measures nothing; a non-int is unrecognised and sets **no** fingerprint; a
   nonzero int sets the fingerprint, sums, and marks the field measured; a literal `0` is **deferred**.
2. **Second pass**, per row — the deferred zeros are marked measured only if the row carried a
   fingerprint. The summed value is `+= 0` either way; what the gate decides is whether the field is
   reported as measured at all.

The fingerprint definition is transplanted verbatim in behaviour from `analyze-logs.py`
`_parse_dispatch_boundary_file`: *datable iff the row carries an `unmeasured` token or a nonzero
context-load cell*. The gate is per row, so one dated row does not date its neighbours. A column absent
from the declared header, or one a short row does not reach, is the unmeasured case and sets no
fingerprint — matching the sibling reader's treatment of a column a short row does not have.

*Done-when, both halves met:* over a ledger whose only rows are fingerprint-free all-zero rows the four
context-load fields are **omitted** from the returned totals (test
`test_fingerprint_free_all_zero_ledger_omits_the_context_columns`); over a ledger with a fingerprinted
row, that row's measured zeros still sum and are present (`test_nonzero_fingerprint_keeps_sibling_measured_zeros`).

The archived corpus was not touched. The diff contains no corpus file.

### D2 — docstring cross-reference corrected in lock-step

`_parse_dispatch_boundary_totals`'s docstring now says the cell reads **four** ways, enumerates the
fourth state, and carries a `THE PROVENANCE GATE` paragraph naming the fingerprint rule, the per-row
scope, and the fact that this reader CANNOT express the undatable verdict per column (it sums rather than
emitting per-row states, so it has no `indeterminate_columns` to name) — an undatable `0` merely fails
to mark its field measured, which is observable only where no row datably measured that field.

**One further consumer of the same claim was found beyond the diff and fixed in the same commit:**
`.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md` — the check's own
interpretation guide — restated the claim twice, in two different consumer kinds: the prose
paragraph opening "**The ledger's four context-load columns read three ways.**" under
"Inputs the check reads", and a bullet in the "Absent is not zero" reading-rules list enumerating only *unmeasured* and *unrecognised* as the
contributes-nothing cases. Both corrected. This is a sibling surface inside the same skill that the
diff would otherwise never have opened.

**`data-format.md`'s PROVENANCE WORDING was deliberately not changed**, per the plan's out-of-scope
condition — though the file *is* edited by this PR, in its lock-step list (see R2-3; the two are
different paragraphs and this run reached opposite conclusions about them, for different reasons).

The untouched paragraph is line 893: *"The `plan-retrospective` reader (`_parse_dispatch_boundary_file`)
implements this row-level provenance gate. A reader that does not recover provenance still performs the
cell read above, but reads an undatable `0` as a measured zero."* Both sentences remain **true** after
this change — the first is an existence claim about the retrospective reader, the second a general
conditional about the class of readers that do not recover provenance. Neither asserts that `audit.py`
is in that class, so neither became inaccurate, and the plan's carve-out therefore does not license
editing them.

The paragraph that *was* edited is line 899, the lock-step obligation list, whose description of the
audit-side surface **did** become inaccurate: it named only a constants tuple, leaving a future edit to
§ *Provenance of a measured zero* with no pointer to the gate this change added. That is the carve-out's
condition met, and the edit is count-preserving for the reason R2-3 records.

### D3 — regression tests

The gate's own tests live in a new module
`test_audit_check_billing_composition_ledger_provenance.py` (`TestDispatchBoundaryZeroProvenance`,
7 collected cases from 6 test functions — one is parametrized over two row orders), joined by two
cross-reader tests in `test_record_model_representability.py` and a new shared fixture.

The new module exists because appending the cluster to
`test_audit_check_billing_composition_reconstruction.py` carried it past the 400-line module budget.
Splitting by behaviour cluster into `test_{unit}_{cluster}.py` is what that standard prescribes and
what this suite already does for `billing-composition` (`_emit`, `_reconstruction`, `_scoping`,
`_under_counts`). The two modules now stand at 211 and 259 lines.

| Test | Direction | Pre-fix |
|---|---|---|
| `test_fingerprint_free_all_zero_ledger_omits_the_context_columns` | the fix | **RED** |
| `test_a_fingerprinted_row_does_not_date_its_neighbour[undated-first]` | per-row scope | **RED** |
| `test_a_fingerprinted_row_does_not_date_its_neighbour[dated-first]` | per-row scope | **RED** |
| `test_unrecognised_cell_is_not_a_fingerprint` | an unparseable cell dates nothing | **RED** |
| `test_a_negative_context_load_value_dates_the_row` | the gate turns on `!= 0`, not positivity | green (added in round 2) |
| `test_nonzero_fingerprint_keeps_sibling_measured_zeros` | negative control | green (see below) |
| `test_unmeasured_token_fingerprint_keeps_sibling_measured_zeros` | negative control | green (see below) |
| `test_undatable_fixture_carries_no_post_token_fingerprint` | fixture premise, asserted on bytes | green by construction |
| `test_undatable_zeros_are_not_measurements_in_either_reader` | cross-reader agreement | **RED** at the audit-reader half |

⚠ **The two negative controls could NOT be seen red against the pre-fix reader, and the plan's
"each seen red first" is met for them a different way.** The plan asks for all three directions red
first; that is unattainable for these two by construction, because the pre-fix reader *already* summed
those zeros — the controls exist to stop an **over-correction**, and pre-fix code is not over-corrected.
This report states that plainly rather than reporting three-of-three red. They were instead verified
non-vacuous against a deliberate over-correction mutant (`if False:` in place of `if datable:`, so every
zero is treated as undatable). Under that mutant **both controls fail** — as do
`test_a_fingerprinted_row_does_not_date_its_neighbour` and two PRE-EXISTING tests that already pinned
the measured-zero direction: `test_unmeasured_cells_are_omitted_while_measured_zeros_are_kept` and the
cross-reader test over the `unmeasured/` fixture. Mutant reverted; it was never committed. This is the
stronger check of the two available: it proves the controls kill the failure mode they exist for, which
red-against-pre-fix would not have shown.

⛔ **The per-row test was RED pre-fix and still did not pin the property it claimed** — the round-1
verification refuted it, and the correction is the most valuable thing this run produced. Its docstring
asserted *"the gate is per ROW, never per file"*, but its fingerprint-free row was written **first**, so
a file-level flag that accumulates across rows is still unset when that row is read. Under a
hoist-`datable`-out-of-the-row-loop mutant, all five gate tests and both cross-reader tests passed. The
test now drives **both** row orders; the `dated-first` arm is the one that does the work, and it kills
that mutant (the undated row's `input_tokens` is promoted to a measured `0` by its neighbour's
fingerprint) while `undated-first` still passes under it — the finding itself, restated as a test.
Red-against-pre-fix is therefore *not* sufficient evidence that a test pins its stated invariant, and
this row is the counterexample.

**The cross-reader pinning the plan preferred.** A new read-only fixture
`test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/undatable/work/metrics-dispatch-boundaries-5-execute.toon`
carries the pre-token writer's shape — nine columns, every context-load cell a literal `0`, nothing on
either row dating it. `test_undatable_zeros_are_not_measurements_in_either_reader` drives **both**
readers off that one artifact and asserts the same verdict in each reader's own vocabulary
(`indeterminate_columns` for the retrospective reader; field absence for the audit reader — which is
the audit reader's only observable here precisely because no row in this fixture datably measured
anything). Its
premise — that the file carries no fingerprint — is asserted on the **bytes** in a separate test, so it
does not rest on the code under test. The existing `unmeasured/` fixture could not serve: every one of
its rows carries an `unmeasured` token, so all its zeros are datable.

**The pre-fix run of the cross-reader test is the plan's thesis in one line:** the retrospective half
passed and the audit half failed, on the same bytes. That is precisely the two-readers-disagree defect,
observed rather than argued.

## Build gate

`git diff --name-only origin/main...HEAD` reports `*.py` changes in `audit.py`, the new
`test_audit_check_billing_composition_ledger_provenance.py`,
`test_audit_check_billing_composition_reconstruction.py`, and
`test_record_model_representability.py` — **Python changed, so the gate took its full path.** (Named
rather than counted: this report is itself in the diff, so any total would go stale as it is written.)
The tree was confirmed clean (`git status --porcelain` empty) before the diff was taken, so the diff
sees all the work.

The gate was run **twice**, and only the second run governs. The first (`20470 passed, 14 skipped`,
417.56 s, at commit `2ccec2c`) predated the round-2 test corrections, so it is recorded as history and
not as the gate. The authoritative run is at the final HEAD:

`UV_HTTP_TIMEOUT=600 ./pw verify` → **`=== verify: SUCCESS ===`**, **`20472 passed, 14 skipped`** in
498.37 s, over all six dimensions (mypy production 410 files, ruff, SPDX, plugin-doctor
marketplace-wide, mypy test 761 files, whole-tree pytest). Read from the streamed tool output, not the
exit code. The `+2` against the earlier run is the parametrize arm and the negative-value test round 2
added.

That second run also caught a real defect the first could not have: round 2's `import pytest` broke
ruff's `I001` import ordering, so `./pw verify` reported `verify: quality-gate failed`. It was fixed to
match the ordering this suite already uses (`from pathlib`, blank line, `import pytest`, then the
`_audit_fixtures` import with no separating blank line — the convention in
`test_audit_check_global_log_analysis_cost_rollup.py`) and the gate re-run green. **A failing gate is
recorded here rather than smoothed over**: the run's first `./pw verify` of round 2 was red.

The per-commit gate ran before each `*.py`-touching commit as the contract requires: `./pw quality-gate`
reported `Success: no issues found in 410 source files` (mypy), `All checks passed!` (ruff),
`SPDX-header check passed`, and `issues[0]` (plugin-doctor). The plan-directory commit needed no gate —
it is a `git mv` with no content change.

**No lockfile churn:** `git status --porcelain` was empty after each build, and every commit staged its
deliverable paths explicitly (never `git add -A`).

## Findings

One row per instance. Source is the round-1 or round-2 pre-PR verification sub-agent unless stated.

### Round 1 — dispatched against commit `70d88ce`

| # | Source | Finding | Disposition |
|---|---|---|---|
| R1-H1 | Sub-agent (round 1) | `test_a_fingerprinted_row_does_not_date_its_neighbour` asserts "the gate is per ROW, never per file" but cannot observe the difference: its fingerprint-free row is written FIRST, so an accumulating file-level flag is still unset when that row is read. Under a hoist-`datable` mutant all five gate tests and both cross-reader tests passed. | **Fixed** — parametrized over both row orders; I rebuilt the mutant and confirmed `dated-first` fails under it while `undated-first` passes. Commit `85848a8`. |
| R1-M1 | Sub-agent (round 1) | `test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader` names a state count this change made false. | **Fixed, but not as proposed** — the agent proposed `_reads_four_ways_`; that would be false too, because every row of the `unmeasured/` fixture carries a token and the fourth state never arises in it. Renamed to `test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader`, which names the invariant it actually pins, plus a docstring note that the fourth state is exercised by the `undatable/` fixture instead. |
| R1-M2 | Sub-agent (round 1) | `test_unmeasured_cells_are_omitted_while_measured_zeros_are_kept`'s docstring opens "The three-way cell read, at the ledger reader" — made false by this change; the test now passes for a reason its docstring no longer states (its row carries both fingerprint forms). | **Fixed** — docstring renamed to the invariant and extended to say the row is datable and why. |
| R1-M3 | Sub-agent (round 1) | `data-format.md:899` § *Restating surfaces* describes the audit-side surface as "the hand-copied `_BC_LEDGER_COLUMNS` tuple"; `audit.py` now restates the whole cell read and the gate, and `checks/billing-composition.md` restates them while appearing in no lock-step list. | **Rejected for this plan, recorded as residue.** The count "four surfaces" in that paragraph is **mirrored** in `analyze-logs.py:987` ("names FOUR surfaces… the other three are…"), which the plan puts explicitly out of scope. Widening only `data-format.md` would make that mirror false — introducing precisely the stale-restatement defect this plan removes — and widening both violates the plan's boundary. Verified by reading both. See Residue. |
| R1-M4 | Sub-agent (round 1) | Report named `test_audit_check_billing_composition_reconstruction.py` as a diff member after the split had made it byte-identical to main; and the recorded `./pw verify` predated the split. | **Fixed** — build-gate section rewritten against the final diff, with both runs recorded and only the second treated as the gate. (The file is in the diff again, for the unrelated R1-M2 docstring fix.) |
| R1-L1 | Sub-agent (round 1) | Two further "three ways" test names, `test_record_model_representability.py:455` and `:783`, both describing the RETROSPECTIVE reader. | **Deferred, deliberately.** Made false by plan 420, not by this diff, on a surface this plan scopes out. The line drawn: this run corrects what *this change* made false and records the rest. Recorded in Residue. |
| R1-L2 | Sub-agent (round 1) | The two readers still disagree on three malformed-input classes, because `audit.py` resolves context columns **by name from the declared header** while `analyze-logs.py` resolves **positionally at index 5–8**: a 5-column header with 9-cell rows; a malformed `total_tokens` beside a nonzero context cell; a missing `rows[]{…}:` header line. A reordered header also transposes values between the two. | **Rejected for this plan, recorded as residue.** Pre-existing, not introduced here, and outside the fingerprint gate — the plan's requirement ("the two readers stop disagreeing") is met *for the gate*. Fixing it means touching the out-of-scope reader. See Residue. |
| R1-L3 | Sub-agent (round 1) | Untested edges the change introduces or leaves open: a negative context-load integer dates the row and is summed; a header omitting or reordering a context column; whitespace-padded cells. | **Partly fixed** — added `test_a_negative_context_load_value_dates_the_row`, which pins the `!= 0` predicate and notes the sibling reader makes the same choice. Header-omission and whitespace left untested and recorded in Residue. |
| R1-L4 | Sub-agent (round 1) | Vocabulary drift: `data-format.md` names the fourth state `indeterminate`, `audit.py` names it `UNDATABLE`, and the check doc's "four ways" lead-in listed three states plus a deferral. | **Fixed** — the check doc now names UNDATABLE as a state and cross-references the `indeterminate` spelling, explaining why this reader expresses it as absence. |

### Round 2 — dispatched against commit `85848a8`

| # | Source | Finding | Disposition |
|---|---|---|---|
| R2-1 | Sub-agent (round 2) | The clause *"which this reader expresses as the field's absence"* — written in round 2 to explain the gate — asserts a mechanism that holds only when NO row datably measured the field. In a mixed ledger the field is present and the undatable cell's verdict is expressed **nowhere**. The counterexample is this run's own parametrized test: two columns assert `== 0` from the dated row while the undated row's zeros in those columns produce no observable at all. Present in `checks/billing-composition.md`, in `audit.py`'s docstring, and twice in this report. | **Fixed at all four sites** (commit `7a2168e` for the two code sites; this commit for the report's two). The corrected statement: this reader cannot express the state per column because it sums, so an undatable `0` merely fails to mark its field measured; the gate is observable only where no row datably measured the field, and elsewhere the cell is subsumed — contributing nothing, which for a literal `0` is what summing it would have contributed anyway. |
| R2-2 | Sub-agent (round 2) | `test_a_negative_context_load_value_dates_the_row`'s docstring names a cross-reader divergence as the risk it guards, but the test drives only `audit.py`; a divergence in `analyze-logs.py` would not fail it. | **Fixed** — restated as parity established by **reading** (citing `analyze-logs.py`'s `if value != 0`), with the cross-reader pinning pointed at the module that actually does it. |
| R2-3 | Sub-agent (round 2) | My R1-M3 rejection was **broader than its premise supports**. The premise is confirmed — the "four surfaces" count IS mirrored in `analyze-logs.py:987` — but that only rules out a **count-changing** widening. A count-preserving one (naming more symbols *within* surface #4) falsifies nothing: the mirror asserts the count and identifies the fourth surface as the file, and its own scope is "this schema". | **Rejection withdrawn; fixed.** `data-format.md`'s surface #4 now names the `_parse_dispatch_boundary_totals` cell read and the provenance gate alongside the constants, so a future edit to § *Provenance of a measured zero* has a pointer to this reader. Count left at four. The plan's carve-out permits exactly this — the wording had become inaccurate as a description of what must move in lock-step. |
| R2-4 | Sub-agent (round 2) | The Cost section still cited the superseded `417.56 s` gate run as the largest known component after the Build gate section had declared the `498.37 s` run authoritative. | **Fixed** — Cost now cites the governing run and names the superseded one as superseded. |
| R2-5 | Own sweep (round 2) | `_BC_LEDGER_UNMEASURABLE_FIELDS`'s comment described it only as "the columns that can carry the unmeasured token"; since the gate landed it is also the set the gate applies to and over which a row's fingerprint is computed, so widening it silently widens the gate. | **Fixed** in commit `a487035`. |
| R2-6 | Own sweep (round 2) | Three surviving references to the pre-rename test name. | **Deliberately not edited, all three.** `doc/plans/code-intelligence-substrate/030-…/report-01.md:110` is an archived record of a different landed plan — `CLAUDE.md`'s records exemption says a dated record is not documentation of current state and is not rewritten to match the present. `plan.md:119` is this plan's own explicitly self-hedged lead ("re-derive the exact names… they may have moved"); rewriting it would destroy the record of what was specified. This report's findings row quotes the old name *as the thing that was renamed*. Independently confirmed by the round-2 sub-agent's whole-tree sweep, which found no `.py`, skill-doc, or standard reference. |

**Round-2 verdict on round 1.** The agent confirmed H1, M1 and M2 resolved, and confirmed each of the
three mechanism claims round 2's prose asserted — the file-level mutant behaviour (`dated-first` is the
*unique* kill among all seven scenarios), the sibling reader's `!= 0` parity, and the `indeterminate`
cross-reference — with R2-1 as the one clause it refuted. It also independently substantiated the S-3
era-stamp reasoning and the ruff-convention citation.

### Findings the run produced on itself, before dispatching

| # | Source | Finding | Disposition |
|---|---|---|---|
| S-1 | Own beyond-diff sweep | `checks/billing-composition.md` restated the three-way claim in two different consumer kinds (a prose paragraph and a reading-rules bullet), in a file the diff would never have opened. | **Fixed** in the implementation commit `2ccec2c`. |
| S-2 | Own sweep | `test_record_model_representability.py`'s module docstring opened "Two fixture-backed companions", which the new `undatable/` fixture made stale. | **Fixed** — rewritten to name the fixtures rather than count them. |
| S-3 | Own analysis | The `CHECK_ERA["billing-composition"]` stamp (`#1086`) could plausibly need bumping, since this change alters how the check's reader interprets archived ledgers. | **Deliberately not bumped**, following the explicit `lane-lever-effectiveness` precedent in the same map: bumping asserts that pre-boundary rows read as era-expected and post-boundary rows as regressions, and the D0 differential refutes that — every archived plan's emitted figures are byte-identical across this change. Pinned unchanged by `test_audit_check_inventory_consistency.py:100`. |

### CI

| # | Source | Finding | Disposition |
|---|---|---|---|
| CI-1 | GitHub Actions on PR #1278 | None. `verify / gate`, `generate-check`, `dependency-review`, and `review / review` all concluded `success`; `verify / verify` is the long required job. | **Nothing to fix.** State at the time of arming is recorded under Merge gate. |

### PR review

| # | Source | Finding | Disposition |
|---|---|---|---|
| PR-1 | `cuioss-review-bot` (issue-comment surface, PR Reviewer Guide) | "Deferred zero fields omitted from output": claims `totals` is a `defaultdict(int)`, so a deferred-zero key is never inserted, and the return comprehension over `totals.items()` therefore drops datable zeros instead of emitting them as `0`. | **Rejected — the premise is false, and refuted by passing tests.** `audit.py:6773` builds `totals` with `dict.fromkeys(_BC_LEDGER_FIELDS, 0)`, not a `defaultdict`: every field key exists at `0` from construction, so `+= 0` being skipped cannot remove a key. `measured` is the sole gate on presence. The predicted behaviour is directly covered by `test_nonzero_fingerprint_keeps_sibling_measured_zeros` and `test_unmeasured_token_fingerprint_keeps_sibling_measured_zeros`, both of which assert a datable zero is present as `0` and would raise `KeyError` under the described defect; both pass. Replied on the thread with the citation and the test run. No change made. |

| PR-2 | `coderabbitai` (inline review thread, Major) | "Replace the manual provenance-schema copies with an enforced contract": four surfaces restate the ledger schema, the check doc is in no list, and no mechanism derives them from the standard or detects all drift. Proposes build-generating the schema, a machine-checked surface inventory, and deriving the test's column literal. | **Rejected for this plan; replied on the thread.** Three of the four remedies conflict with deliberate documented choices: the hand-mirror is architectural (`analyze-logs.py:977-996` states the readers run in different processes and cannot import the writer's constants; `audit.py` is outside the marketplace tree entirely), and deriving the test's column literal would make the test **unable to falsify a drift** — the repo's own standard says *"exact literal where the literal IS the contract"*. The fourth (registering the check doc) is already residue, with its blocker stated. The underlying risk is real and worth its own cross-bundle plan; it is far outside a one-reader fix. |
| PR-3 | `coderabbitai` (inline review thread, Minor) | The report says `data-format.md` "was deliberately NOT edited" while this PR *does* edit its lock-step section, which the report itself records elsewhere. | **Accepted and fixed.** A genuine self-contradiction: the sentence was true when round 1 wrote it, and round 2's R2-3 edited line 899 without revisiting it. The paragraph now separates line 893 (provenance wording — not changed, and why) from line 899 (lock-step list — changed, and why). |

Worth recording that PR-1 is the direction the change is *designed* not to break: the two negative
controls exist precisely to catch an over-correction that drops datable zeros, and they were verified
non-vacuous against a mutant that does exactly that. The reviewer named a real failure mode; the suite
already guards it.

⛔ **PR-3 is the sharpest finding of the whole run, and no internal check caught it.** It is the same
defect class this plan exists to remove — a claim made false by a later change, at a site the fix did
not touch — reproduced **in the run's own record**. Both verification rounds missed it because a
verification sub-agent reads the code; the contradiction lived entirely between two paragraphs of the
report. The contract already names this ("the run report is part of that surface… re-read your own
dispositions against the artifacts"), and this run still walked past it twice. It took an external
reviewer to see it.

## Reviewer participation

Population derived from configuration, not transcribed: the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`.
**M = 3.** Each verdict is read from the stored comment **bodies** across all three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`), never from a check-run state.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Published a *PR Reviewer Guide* against the diff on the issue-comment surface, carrying one finding ("Deferred zero fields omitted from output") plus "PR contains tests" and "No security concerns identified". Dispositioned as PR-1 above. |
| `sourcery-ai` | `rate-limited` | `yes` | Review-summary body: *"you have reached your weekly rate limit of 500000 diff characters. Please try again later or upgrade…"* — a **weekly cumulative** quota, not a per-diff size ceiling, so it clears with the week; the notice names no clearing time. Its `Sourcery review` check-run concluded `skipped`, which is **not** the evidence — the body is. |
| `coderabbitai` | `reviewed` | — | Published a review-summary body ("Actionable comments posted: 2") plus **two inline review-thread comments** — PR-2 and PR-3 above. Its review-summary body also notes *"up to 1 review per rolling hour; 0 remain after this review"*, i.e. it is exhausted **after** reviewing, which is not a refusal. |

**Coverage: 2 of 3 `reviewed`.** One reviewer (`sourcery-ai`) was rate-limited; the § Step 8 shortfall
disclosure is recorded in the Merge gate section below.

⚠ **`coderabbitai` was deliberately NOT recorded early.** For several minutes its only body was the
auto-generated *"Currently processing new changes in this PR"* note, with no review summary and no
inline threads — neither `reviewed` nor a refusal. It was carried as in-flight and re-read, rather than
written down as `silent`, which would have been exactly the false verdict this table exists to prevent:
it went on to file the run's most valuable finding (PR-3).

⚠ **A check-run state is not a verdict, and this PR shows why twice.** `Sourcery review` concluded
`skipped` while its body carried a quota refusal; CodeRabbit posts no check at all yet filed two
actionable comments. Both verdicts here come from bodies.

⚠ **Reading only the conversation surface would have missed both CodeRabbit findings.** Its review
summary lives under `get_reviews` and its two findings under `get_review_comments`; `get_comments`
carried only the processing note. A run that stopped at the conversation view would have asserted "all
comments handled" against one bot finding while two — including the report contradiction — sat unread.

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no token counter to the
  running agent, so no figure is given rather than a guessed one.
- **Wall-clock:** ~1 h from the first commit of the run (`2297407`, 2026-08-16T21:09:57Z) to the report
  commit; source is the git committer timestamps on this branch. The single largest known component is
  the authoritative `./pw verify` gate at 498.37 s, reported by pytest itself (the superseded first run
  took 417.56 s; both are recorded under Build gate, and only the second governs).
- **Population:** this single Claude Code cloud session's activity, as the git log and the build's own
  output record it. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary. This run has no
  such boundary — it is one interactive session — so no parity figure is offered.

## Merge gate

State read back from the PR, never inferred from the command that produced it.

**Condition 1 — required contexts.** `mergeable_state: blocked` at the time of writing, from
`pull_request_read method: get` (the MCP payload names this field `mergeable_state`, lowercase — there
is no `mergeStateStatus` key on this path). The blocker is derived from *required ∩ non-green*, not
from whichever pending status is loudest: `verify / verify` is `in_progress`, and it is the long
required job. Everything else has concluded: `verify / gate`, `generate-check`,
`dependency-review / dependency-review`, and `review / review` all `success`; `Sourcery review` and
`auto-merge` `skipped` (both **non-required** — disclosed, never held for).

⚠ **Armed with the required check still in flight, deliberately.** Committing this report re-triggers
`verify` by construction — the report must land *in this PR* (condition 3), and the branch locks the
instant it queues — so the required check is necessarily `in_progress` on the report SHA at arm time.
§ Step 8's carve-out covers exactly this: on a merge-queue repository the queue admits a PR only when
the ruleset's required contexts pass and re-verifies on `merge_group`, so arming defers the
required-green gate to the queue rather than merging anything red.

**Condition 2 — every comment handled.** Three findings across three surfaces, all dispositioned and
all answered on the thread: PR-1 (rejected, premise refuted by citation and a test run), PR-2
(rejected for this plan, with the three conflicting remedies named), PR-3 (**accepted and fixed** — the
report's own self-contradiction). No open, unaddressed comment.

**Condition 3 — the report is this PR's last pre-merge commit**, committed before arming.

**Condition 4 — review-coverage shortfall, DISCLOSED (not a gate).**

> Review coverage: **2 of 3** — `cuioss-review-bot` reviewed; `coderabbitai` reviewed (2 actionable
> comments); `sourcery-ai` **rate-limited on a weekly 500 000 diff-character quota, reopens: yes**
> (a cumulative weekly limit, not a per-diff ceiling — it clears with the week, though the notice names
> no time). Merging on 2-of-3.

The shortfall changes what this run **says**, never whether it merges. Arming proceeded exactly as full
coverage would.

**Landing.** Recorded to the operator from the PR merge event, not embedded here — the squash SHA does
not exist until after this commit is written.

## Contract check (Step 9)

**GitHub access path:** the GitHub MCP server (the cloud path). No `gh` CLI is present in this session.
**Branch form:** harness-assigned (`claude/audit-ledger-undatable-zero-ef7sl5`), kept as-is per § Step 2;
this run created no branch.
**Plugin cache sync:** not performed and **not owed** — a machine-local build step a cloud run never
records as debt (§ Scope and precedence).

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | Named in *Skills loaded*; all obtained by bundle path, none unavailable |
| 2 Branch | **Done** | On `origin`; harness-assigned name kept. Pushed as the run's first action, before any edit — the tree was verified clean first |
| 3 Plan directory | **Done** | `doc/plans/truthful-signals/460-…/plan.md` exists and opens with the first-instruction block (re-checked against the moved file at Step 9, not assumed from Step 3) |
| 4 Implement | **Done** | 9 commits, every one carrying the `Co-Authored-By: Claude` trailer (verified by `git log --format=%(trailers:…)`, not by recollection); D0–D3 all addressed |
| 4 Per-commit gate | **Done** | Each `*.py`-touching commit preceded by `./pw quality-gate` reporting `Success: no issues found in 410 source files`, `All checks passed!`, `SPDX-header check passed`, `issues[0]`. The plan-directory commit is a `git mv` and needed none |
| 4 Pushed | **Done** | `git status -sb` reports no `ahead`; every commit pushed immediately |
| 5 Build gate | **Done** | Git-derived `*.py` verdict and both runs recorded, with the second named authoritative — including the round-2 run that went **red** on ruff `I001` and was fixed |
| 6 Verification sub-agent | **Done, stopped by judgement** | Two rounds; 9 round-1 and 6 round-2 findings, each with a disposition. See the disclosure below |
| 7 PR cycle | **Done** | PR #1278; all three comment surfaces read (`get_comments`, `get_reviews`, `get_review_comments` — the last empty); the one finding dispositioned and answered on the thread; participation table carries a verdict and a `Reopens?` value per reviewer |
| 8 Merge gate | See *Merge gate* | Conditions 1–3 and the condition-4 disclosure recorded there |
| 8 Bridge | **Done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory — no ledger, no status file, no other plan's directory touched. The one edit outside the plan directory that is not a deliverable file (`data-format.md`) is a **declared-deliverable** lock-step correction, not a record |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | One change proposed to the operator below |

⛔ **The verification loop was STOPPED BY JUDGEMENT at round 2, not run to a clean round.** Disclosed
per § Step 6 rather than reported as convergence. The four conditions were met: no round-2 finding
changed code behaviour, a test's meaning, or a deliverable's verdict (all six were prose, a docstring, a
documentation pointer, and the report); the code was verified by something stronger than another read
(a differential run of the whole check against a pre-fix reader, plus four mutants — pre-fix,
over-correction, file-level fingerprint, and positivity — each with an identified unique kill); and the
findings both declined and narrowed to the run's own prose. **This document should be assumed to still
contain prose residue of the kind round 2 found** — an explanatory clause asserting a mechanism that
holds in the case at hand but does not generalise.

**Tree claims re-verified at Step 9, not carried from when they were written.** `.plan/` now holds
`execute-script.py`, `local`, `marshal.json`, `project-architecture`, and `temp` — the build gate
created several of these during the run. Nothing in this report claims otherwise; the entry is here
because the contract requires filesystem claims to be re-read at the end rather than trusted, and this
tree did change under the run.

## What have we learned (Step 9)

**One change is proposed, and it is NOT self-approved or shipped here.** Per § Step 9 it is presented to
the operator with this run's evidence; on approval it ships as a separate `chore/` PR touching only the
skill, never folded into this plan's PR.

**Proposal — red-against-pre-fix is not evidence that a test pins its stated invariant.**

*Evidence from this run.* `test_a_fingerprinted_row_does_not_date_its_neighbour` was written to pin the
gate's per-row scope, its docstring asserting *"the gate is per ROW, never per file"*. It **was** red
against the pre-fix reader, so it cleared the plan's "seen red first" bar and this run recorded it as a
pinned direction. Round 1 of the verification sub-agent refuted that: under a file-level-fingerprint
mutant (`datable` hoisted out of the row loop so it accumulates), the test **passed** — along with every
other gate test — because its fingerprint-free row was written first, so the accumulating flag was still
unset when that row was read. The test detected the *old* defect and was blind to the *named* one. That
is not a slip in this one test; it is a structural gap: red-against-pre-fix proves a test discriminates
the pre-fix behaviour, which is a different claim from "this test would fail if the invariant its
docstring names were violated". The two coincide only when the docstring claims exactly "not the old
behaviour".

*Concrete proposed edit* — in `§ Step 6`, alongside the existing per-round obligations:

> **A test whose docstring names a MECHANISM or a SCOPE is verified against a mutant of that mechanism,
> not only against pre-fix code.** "Seen red first" establishes that the test discriminates the
> behaviour being replaced; it establishes nothing about a stronger claim the docstring makes — "per
> row, never per file", "fails closed", "per column, independently". Those are different propositions,
> and a test can satisfy the first while being blind to the second, most often because its fixture
> orders the inputs so the claimed failure mode cannot arise. So: name the mutant the docstring implies,
> build it, and confirm the test fails under it. Where a mutant is impractical, say in the report that
> the claim rests on inspection.

*Why the contract does not already cover this.* § Step 6 names mutation testing only as a **convergence
condition** ("a mutation test that proves a new guard non-vacuous") — a property of the *round*, not an
obligation on each mechanism-claiming test. And the neighbouring rule about untested additions covers a
field with *no* test, not a test that exists, is red-first, and still does not pin its claim. This run
produced the missing case.

**Not proposed, but worth recording: two contract rules earned their place this run.** The
*invented-rationale* rule caught R2-1 — a clause this run wrote to explain a fix, asserting a mechanism
that holds only in the all-undatable case, with the run's own test as the counterexample. And the
*enumeration-is-a-figure* rule caught S-2, a "Two fixture-backed companions" lead-in the new fixture
made stale. Neither needs changing.

## Residue

- **The two readers still disagree about DATABILITY itself on a malformed input** — the sharpest of the
  set, and the one a follow-on should lead with. `audit.py` resolves the context columns **by name from
  the declared header**; `analyze-logs.py` resolves them **positionally at indices 5–8**. So for a
  ledger whose header declares only the legacy five columns while its rows carry nine cells,
  `audit.py` measures nothing at all, while `analyze-logs.py` measures all four **and dates the row**.
  Two further divergences of the same origin: a malformed `total_tokens` beside a nonzero context cell
  (the retrospective reader drops the whole row; the audit reader keeps it, sums, and dates it), and a
  missing `rows[]{…}:` header line (audit yields `{}`; retrospective parses the row). A reordered
  header additionally transposes values between the two while the measured *set* agrees. **None is
  introduced by this plan and none touches the fingerprint gate** — the plan's requirement is met for
  the gate — but "the two parallel readers of one ledger stop disagreeing about the same bytes" is now
  true of the gate and not yet of the surrounding parse. Fixing it means touching `analyze-logs.py`,
  which this plan scopes out.
- **`checks/billing-composition.md` is a restating surface registered in no lock-step list.** It now
  carries the full gate text. It was deliberately NOT added to `data-format.md`'s list, because that
  list's "four surfaces" count is mirrored in `analyze-logs.py:987` and registering a fifth *file*
  would falsify the mirror (unlike R2-3's count-preserving widening within surface #4). Nothing tests
  that list structurally — only the `termination_cause` enum has an equality guard. A plan that wants
  the check doc registered must move `data-format.md` and the `analyze-logs.py` mirror **together**.
- **Two stale "three ways" test names describing the RETROSPECTIVE reader** —
  `test_record_model_representability.py:455` and `:783`. Made false by plan 420, not by this diff, on
  a surface this plan scopes out. One cost this run created even though the staleness predates it: the
  file is now internally asymmetric, carrying a correctly-named sibling beside them, so a reader cannot
  tell whether the asymmetry is meaningful. A one-line rename in a `chore/` plan closes it.
- **Untested edges, both judged not worth a test.** Whitespace-padded cells: both readers strip, no
  divergence, nothing to protect. A header omitting or reordering a context column: this is the first
  residue item above, where the right remedy is reconciling the two resolution strategies, not pinning
  the current divergence.
- **The two residues plan 420 named remain open and are not this plan's** — a denominator that states
  *when* it was sampled but not *what* it counted, and a partiality verdict blind to a *stale-closed*
  phase. Each deserves its own plan.
