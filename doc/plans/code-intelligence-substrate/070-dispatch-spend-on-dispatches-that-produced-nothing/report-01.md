# Run report — 070-dispatch-spend-on-dispatches-that-produced-nothing (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/dispatch-spend-empty-ds4y39` (harness-assigned)    **PR:** _pending_    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` — the working contract (first action, before reading the plan).
- `plan-marshall:ref-code-quality` — always-load (read from bundle path).
- `pm-plugin-development:plugin-script-architecture` — always-load (read from bundle path).
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

All obtained by reading the bundle-path `SKILL.md` files (the `plan-marshall` plugin is not installed in this cloud session, so `Skill:` notation loads were not used). No skill was unreachable.

## Deliverables

The plan's founding proxy (`error` == "produced nothing") is REFUTED by the plan itself. The work fixes the proxy first (D1), settles the token-column gate (D2), and reports the genuinely-wasted population (D4/D5); the corpus-dependent measurements (D3, and D4's class shares) are blocked in a fresh clone.

### D1 — GATE: taxonomy member for a productive non-completion + widen the audit rule — **DONE**

Confirmed in the clone before changing anything: `DISPATCH_TERMINATION_CAUSES` had no member for a findings-bearing return (settling the refutation claim without the machine-local record — the mis-stamping is structural), and the step-completion surface already carries a `loop_back` outcome + `loop_back_target` classifier while the dispatch ledger had no counterpart.

- Added `returned_with_findings` to `DISPATCH_TERMINATION_CAUSES` (`manage-metrics.py`), the dispatch-ledger counterpart of the step-completion `loop_back` outcome.
- Routed the finalize 5c classification (`phase-6-finalize/SKILL.md`) so a dispatched step whose `mark-step-done` recorded `outcome: loop_back` is stamped `returned_with_findings`, **never** `error`. The classification is now five causes, not four.
- Widened the `DISPATCH_TERMINATION_CAUSE` audit rule (`logging-gap-analysis.md`): its Inputs and precondition covered only `metrics-dispatch-boundaries-5-execute.toon`; they now cover every dispatching phase incl. `6-finalize`. (The programmatic reader `read_dispatch_boundaries_per_phase` in `analyze-logs.py` already globbed all phases — lesson `2026-05-20-12-002`; the *rule doc* was the stale half, and is what the plan's "read by no rule at all" was pointing at.)
- All enum-mirror sites moved in lock-step: `manage-metrics/SKILL.md` (2 brace-forms + bullet), `data-format.md` enum line, `logging-gap-analysis.md` `the accepted causes:` set, and the argparse `description=` string. The existing contract tests (`test_every_documented_termination_cause_site_matches_the_enum`, `test_logging_gap_analysis_termination_cause_set_matches_the_enum`, `test_data_format_termination_cause_enum_matches_the_enum`) and the plugin-doctor `canonical-enum-choices-drift` rule enforce the sync.

Tests that fail before the change: `test_enum_contains_returned_with_findings_cause`, `test_returned_with_findings_recorded_on_the_finalize_boundary` (stamps the new member on the finalize boundary file), `test_analyze_logs_surfaces_the_finalize_boundary_file` (the audit reader reads the finalize file and counts the new cause), `test_logging_gap_analysis_rule_scope_names_the_finalize_boundary_file` (the rule doc widening). Commit `0499cc7`.

### D2 — GATE: the four per-dispatch token columns — **SETTLED (already satisfied by prior work)**

The plan frames D2 as binary (populate or drop) on the belief that the columns "persist as though measured" (write `0` for an omitted flag). **That premise is REFUTED in the current clone.** A prior change (the `unmeasured`-token infrastructure, `UNMEASURED_COLUMN_TOKEN`) already ships a superior third path: an omitted flag writes the literal `unmeasured`, never `0`; a *measured* `0` stays `0`; and readers implement a three-way (measured / unmeasured / unrecognised) read. The measured-vs-unproduced distinction is therefore representable on disk **and comprehensively tested** — `test_record_model_representability.py` pins it in the writer and in BOTH readers (the retrospective reader and the `.claude` audit ledger reader), including the exact negative control the plan's Verification section demands (a measured `0` and an unproduced column are distinguishable).

Producer-absence established first-party (the plan flags this as the higher-burden asserted absence): a repository sweep for `--input-tokens`/`--output-tokens`/`--cache-read-input-tokens`/`--cache-creation-input-tokens` finds them only in the writer's argparse definition, the schema doc, and the SKILL.md — **no** workflow doc or caller (`execution.md`, `planning-outline.md`, `phase-6-finalize/SKILL.md`) forwards them. So the columns are honestly `unmeasured` at every call site, which is the correct representation, not a manufactured zero. D2's gate is met: nothing reads a manufactured zero, and D5 reads `total_tokens` (column 3, produced), not these columns. **No code change was warranted; re-implementing would have shipped a second writer for one taxonomy, which the plan forbids.**

### D3 — re-derive the non-productive population, first-party — **BLOCKED on corpus availability**

D3 mutates nothing; it is a measurement over a corpus of archived run records. That corpus lives under the machine-local, git-ignored `.plan/` tree and is **not present in a fresh cloud clone** (per `CLAUDE.md` and the `cloud-plan-lane` skill). The plan explicitly instructs: "If no population of archived records is reachable here, HALT D3/D4's measurement and report them blocked on corpus availability" and "⛔ Do not search for it." No corpus was reachable; **the measurement is halted and reported blocked.** No share figure was computed or fabricated, and the retired "a third of finalize dispatch spend" figure is not quoted anywhere. Per the plan, a halt with a clear statement of what was unreachable is the D3 deliverable met, not a failure.

### D4 — separate RETRYABLE from TERMINAL — **code DONE; class shares BLOCKED on corpus**

Code half: the reader (`_parse_dispatch_boundary_file`) now reports `retryable_total_tokens` (`blocked_session_restart` + `harness_cancellation` — infrastructure a re-run recovers) **distinctly** from `error_total_tokens` (genuine terminal failure that may be deterministic). They are never summed into one "failure" figure; a test (`test_retryable_total_tokens_reported_distinctly_from_error`) asserts they stay distinct. The named cause-classes are module constants (`_RETRYABLE_CAUSES`, `_TERMINAL_WASTE_CAUSES`). Measurement half (the class shares over archived records): blocked on the same corpus gate as D3.

### D5 — make the waste a reported figure — **DONE**

Genuinely-wasted dispatch spend is emitted as its own field, `error_total_tokens` — the sum of `total_tokens` over `error` rows. After D1, findings-bearing loop-backs are stamped `returned_with_findings`, so what remains under `error` is genuine terminal waste: a dispatch that examined nothing and returned nothing. The field is surfaced in the `dispatch_boundaries` fragment and rendered in the compile-report "Phase Dispatch Boundaries" table (`error_total_tokens (wasted)` column), so a reader sees it without reconstructing it. Covered by `test_error_total_tokens_sums_only_terminal_error_rows` and the compile-report render tests. The productive population it must be told apart from is counted as `returned_with_findings_count`.

**Owning-module resolution (Expected surface was a HYPOTHESIS).** The plan hypothesised D5's field in `manage-metrics`. It is placed instead in `plan-retrospective`'s dispatch-boundary reader + compile-report, because (a) that reader is where termination causes are already interpreted per-cause (`unknown_count`, `clean_exit_queue_empty_count`), (b) the compile-report "Phase Dispatch Boundaries" section is where a human reader actually sees per-phase dispatch data, and (c) it avoids the `manage-metrics` per-phase token-field **lattice** contract, which would force a lattice row and reconciliation coupling for a figure that is a per-cause interpretation, not a dispatched-population measure. The taxonomy member itself (D1) is in `manage-metrics` as hypothesised.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (`manage-metrics.py`, `analyze-logs.py`, `compile-report.py`, and four test files), so the Python gate ran. `./pw verify plan-marshall` → **SUCCESS**: 16077 passed, 1 skipped; quality-gate (ruff / mypy(production 277) / mypy(test 571) / SPDX / plugin-doctor marketplace-wide) all clean; module-tests(plan-marshall) green. Scoped to the `plan-marshall` bundle because the entire diff is within it (sanctioned by the lane contract's "append a bundle name" note); the merge queue runs the full cross-bundle verify.

## Findings

_Verification sub-agent findings pending — filled in after the Step-6 dispatch returns._

## Reviewer participation

_Filled in after the PR review cycle._

## Cost

- **Tokens:** not available to the agent in this session (a Claude Code cloud session does not expose its own token accounting to the running agent).
- **Wall-clock:** single interactive cloud session; `./pw verify plan-marshall` alone was ~6m36s.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary, which a single interactive cloud session does not share. The figures cannot be made comparable, so none is presented as if it were.

## Contract check (Step 9)

_Filled in as the final pre-merge section._

## What have we learned (Step 9)

_Filled in as the final pre-merge section._

## Residue

- **D3 measurement** and **D4's class shares** remain unmeasured, blocked on the archived-records corpus that a fresh clone does not carry. When run where the corpus is present (a local machine with `.plan/local/archived-plans/`), the sweep should: derive the terminal-state vocabulary from the schema (not the two observed names), re-derive against finding-yield (a `returned_with_findings` dispatch is the opposite of the target), report the count + token cost + population size, and compute any share only against a settled denominator (the sibling coverage-ratio plan is the blocker for share figures).
