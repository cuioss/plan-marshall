# Run report — 460-audit-ledger-reader-reads-undatable-zero-as-measured (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/audit-ledger-undatable-zero-ef7sl5`    **PR:** TBD    **Outcome:** TBD

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
scope, and the fact that this reader expresses the undatable verdict as the field's *absence* (it sums
rather than emitting per-row states, so it has no `indeterminate_columns` to name).

**One further consumer of the same claim was found beyond the diff and fixed in the same commit:**
`.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md` — the check's own
interpretation guide — restated the claim twice, in two different consumer kinds: the prose
paragraph opening "**The ledger's four context-load columns read three ways.**" under
"Inputs the check reads", and a bullet in the "Absent is not zero" reading-rules list enumerating only *unmeasured* and *unrecognised* as the
contributes-nothing cases. Both corrected. This is a sibling surface inside the same skill that the
diff would otherwise never have opened.

**`data-format.md` was deliberately NOT edited**, per the plan's out-of-scope condition. Its line 893
reads: *"The `plan-retrospective` reader (`_parse_dispatch_boundary_file`) implements this row-level
provenance gate. A reader that does not recover provenance still performs the cell read above, but
reads an undatable `0` as a measured zero."* Both sentences remain **true** after this change — the
first is an existence claim about the retrospective reader, the second a general conditional about the
class of readers that do not recover provenance. Neither asserts that `audit.py` is in that class. The
plan permits a note naming `audit.py` as a second provenance-recovering reader *only if* the wording
became inaccurate; it did not, so the standard is left alone.

### D3 — regression tests

Five tests in a new module
`test_audit_check_billing_composition_ledger_provenance.py` (`TestDispatchBoundaryZeroProvenance`),
plus two cross-reader tests in `test_record_model_representability.py`, plus a new shared fixture.

The new module exists because appending the cluster to
`test_audit_check_billing_composition_reconstruction.py` carried it to 408 lines, past the 400-line
module budget. Splitting by behaviour cluster into `test_{unit}_{cluster}.py` is what that standard
prescribes and what this suite already does for `billing-composition` (`_emit`, `_reconstruction`,
`_scoping`, `_under_counts`). The two modules are 253 and 178 lines, and the same 32 tests pass before
and after the split.

| Test | Direction | Pre-fix |
|---|---|---|
| `test_fingerprint_free_all_zero_ledger_omits_the_context_columns` | the fix | **RED** |
| `test_a_fingerprinted_row_does_not_date_its_neighbour` | per-row scope | **RED** |
| `test_unrecognised_cell_is_not_a_fingerprint` | an unparseable cell dates nothing | **RED** |
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
zero is treated as undatable). Under that mutant **both controls fail** — as do the new
`test_a_fingerprinted_row_does_not_date_its_neighbour` and two PRE-EXISTING tests that already pinned
the measured-zero direction: `test_unmeasured_cells_are_omitted_while_measured_zeros_are_kept` and the
cross-reader `test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader` (five failures in
all). Mutant reverted; it was never committed. This is the stronger check of the two available: it proves the controls kill the failure
mode they exist for, which red-against-pre-fix would not have shown.

**The cross-reader pinning the plan preferred.** A new read-only fixture
`test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/undatable/work/metrics-dispatch-boundaries-5-execute.toon`
carries the pre-token writer's shape — nine columns, every context-load cell a literal `0`, nothing on
either row dating it. `test_undatable_zeros_are_not_measurements_in_either_reader` drives **both**
readers off that one artifact and asserts the same verdict in each reader's own vocabulary
(`indeterminate_columns` for the retrospective reader; field absence for the audit reader). Its
premise — that the file carries no fingerprint — is asserted on the **bytes** in a separate test, so it
does not rest on the code under test. The existing `unmeasured/` fixture could not serve: every one of
its rows carries an `unmeasured` token, so all its zeros are datable.

**The pre-fix run of the cross-reader test is the plan's thesis in one line:** the retrospective half
passed and the audit half failed, on the same bytes. That is precisely the two-readers-disagree defect,
observed rather than argued.

## Build gate

`git diff --name-only origin/main...HEAD` reports `*.py` changes in `audit.py`,
`test_audit_check_billing_composition_reconstruction.py`, and
`test_record_model_representability.py` — **Python changed, so the gate took its full path.** (Named
rather than counted: this report is itself in the diff, so any total would go stale as it is written.)
The tree was confirmed clean (`git status --porcelain` empty) before the diff was taken, so the diff
sees all the work.

`UV_HTTP_TIMEOUT=600 ./pw verify` → **`=== verify: SUCCESS ===`**, `20470 passed, 14 skipped` in
417.56 s, over all six dimensions (mypy production 410 files, ruff, SPDX, plugin-doctor marketplace-wide,
mypy test 761 files, whole-tree pytest). Read from the streamed tool output, not the exit code.

The per-commit gate ran before the implementation commit as the contract requires: `./pw quality-gate`
reported `Success: no issues found in 410 source files` (mypy), `All checks passed!` (ruff),
`SPDX-header check passed`, and `issues[0]` (plugin-doctor). The plan-directory commit needed no gate —
it is a `git mv` with no content change.

**No lockfile churn:** `git status --porcelain` was empty after the build, and every commit staged its
deliverable paths explicitly (never `git add -A`).

## Findings

_(pending — verification sub-agent, CI, and PR review)_

## Reviewer participation

_(pending)_

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no token counter to the
  running agent, so no figure is given rather than a guessed one.
- **Wall-clock:** ~1 h from the first commit of the run (`2297407`, 2026-08-16T21:09:57Z) to the report
  commit; source is the git committer timestamps on this branch. The single largest known component is
  the `./pw verify` gate at 417.56 s, reported by pytest itself.
- **Population:** this single Claude Code cloud session's activity, as the git log and the build's own
  output record it. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary. This run has no
  such boundary — it is one interactive session — so no parity figure is offered.

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
