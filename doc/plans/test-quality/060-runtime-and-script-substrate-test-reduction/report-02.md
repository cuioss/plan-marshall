# Run report — 060-runtime-and-script-substrate-test-reduction (run 02)

**Date (UTC):** 2026-08-16    **Branch:** `claude/runtime-script-substrate-tests-qqeuoj`    **PR:** [#1265](https://github.com/cuioss/plan-marshall/pull/1265)    **Outcome:** completed

A follow-up run closing the one deliverable half that run 01 left unstarted: **D3's B6 sweep**,
building argument namespaces from the real parser instead of by hand.

Run 01 landed as PR [#1263](https://github.com/cuioss/plan-marshall/pull/1263) (merge commit
`8872700`). Because that PR is merged, this run restarted the same branch name from the merged `main`
rather than stacking on already-merged history, and opens a **new** PR.

## Why B6 did not run in run 01

Stated plainly, because run 01's report recorded the omission but not the cause: **there was no
technical blocker.** Run 01 spent its budget on D1, D3's preamble half, D4's prose half, D5 and D6, and
never started B6. Run 01's report said so — *"empty because the sweep did not run … not because every
call site converted"* — and this run is that sweep.

The seam was available the whole time **for the scripts this sweep converts** — every one of those
exposes a reachable parser. It is NOT true of every script in the slice: the exception table below
records 27 call sites whose scripts expose no seam at all, and those were probed rather than assumed.
An earlier draft of this sentence claimed the stronger thing and contradicted its own table.

## Deliverable

### D3 (B6) — argument namespaces come from the real parser — **done**

**168 hand-built `argparse.Namespace(...)` constructions now go through `conftest.parse_ns`.** AST-derived
construction count over the slice: **197 → 29**. `parse_ns` call sites: **0 → 168**. Collected test
count unchanged at **3,827**.

| Module | converted |
|---|---:|
| `tools-permission-fix/test_permission_fix_behavior.py` | 27 |
| `tools-permission-fix/test_permission_fix.py` | 26 |
| `manage-logging/test_manage_logging.py` | 25 |
| `manage-files/test_manage_files.py` | 24 |
| `tools-permission-doctor/test_permission.py` | 17 |
| `manage-files/test_manage_files_detect_ide.py` | 8 |
| `manage-files/test_manage_files_cli.py` | 7 |
| `manage-files/test_manage_files_open_in_ide.py` | 7 |
| `tools-permission-doctor/test_permission_doctor_behavior.py` | 7 |
| `lsp-client/test_lsp_client.py` | 7 |
| `extension-api/test_derivation_resolver_roster.py` | 7 |
| `lsp-client/test_lsp_integration.py` | 6 |
| **TOTAL** | **168** |

**What the conversion buys, concretely.** `parse_ns` returns what the production parser produces, so a
converted call site now carries defaults the hand-built namespace omitted. Measured on two examples:
`manage-logging work` gains `store='plans'`, and `permission_doctor detect-suspicious` gains
`scope=None, approved_file=None`. The production code had been defending against exactly this with
`store = getattr(args, 'store', 'plans')` — a getattr that exists because hand-built namespaces omit
the attribute the real CLI always sets.

**The flag table is derived from each script's own parser, not hand-maintained** — and that is a
finding, not a stylistic note. A hand-written table was tried first and produced **two defects** the
derived table does not:

| Defect | Why it happened | How it surfaced |
|---|---|---|
| `--no-move-marketplace` is a **`store_false`** flag, so omitting a `False` value **inverts** its meaning | The hand-written table recorded flag *names* but not *action kinds*, and the converter's "omit False" rule is correct only for `store_true` | 2 failures in `TestRemoveRedundant` |
| `--limit` is **`int`-typed**, and a bare `int` in `argv` is not a string | Same omission — the table carried no type information | `TypeError: 'int' object is not subscriptable` in `test_read_work_log_with_limit` |

Both were caught by running the tests, both were structural rather than incidental, and both
disappeared when the table was re-derived by introspecting each parser's own `_actions` (flag string,
action kind, `type`, `nargs`). The lesson generalises: a table *about* a parser should be read *from*
the parser.

Two scripts needed **nested** subcommand support (`derivation-resolver set`, `language-server set`),
and the `lsp-client` tests drive **two different scripts** (`lsp_client.py` and `run_config.py`), so
both the script and the subcommand are resolved per callee rather than per module.

### The `parse_ns` exception list — the 29 that remain

D3's done-when requires every exception to be listed **with its script**. All 29 are recorded here, and
each has a concrete reason rather than "not done":

| Sites | Module | Script | Why `parse_ns` cannot serve |
|---:|---|---|---|
| 11 | `script-shared/test_build_execute_factory.py` | `script-shared/scripts/build/_build_execute_factory.py` | **No parser seam.** The module publishes no `main()` and no builder in `PARSER_BUILDER_NAMES`; `build/_build_cli.py` likewise. Probed directly — `parse_ns` raises `ParserSeamNotFound`. `cmd_run` is dispatched by the build CLI, whose parser is constructed elsewhere |
| 2 | `script-shared/test_build_timeout_truthfulness.py` | same | same — no seam |
| 1 | `script-shared/test_build_queue_slot.py` | same | same — no seam |
| 1 | `script-shared/test_daemon_routing_neutralization.py` | same | same — no seam |
| 9 | `manage-providers/test_list_providers.py` | `manage-providers/scripts/_list_providers.py` | **No parser seam** — no `main()`, no published builder. The tests call module-level `run_list_providers` / `run_find_by_category` / `run_discover_and_persist` entry points directly, which is not a CLI invocation |
| 2 | `manage-providers/test_ensure_denied.py` | `manage-providers/scripts/_cred_ensure_denied.py` | same — a module-level `run_ensure_denied` entry point, no seam |
| 1 | `manage-providers/test_cred_edit_extra.py` | `manage-providers/scripts/_cred_edit.py` | same — no seam |
| 1 | `manage-files/test_manage_files_cli.py` | `manage-files/manage-files.py` | The namespace is built for a **helper**, not a subcommand invocation |
| 1 | `tools-permission-fix/test_permission_fix_behavior.py` | `tools-permission-fix/permission_fix.py` | `resolve_settings_arg(...)` takes a namespace but **is not a CLI entry point** — there is no subcommand it corresponds to, so there is no argv that would produce it |

**Subtotals, re-derived from the table rather than eyeballed** — an earlier draft of this paragraph
said "14" and "26", both of which are wrong against the rows above:

| Grouping | Sites |
|---|---:|
| `script-shared` (build CLI) | **15** |
| `manage-providers` | **12** |
| `manage-files` (helper) | 1 |
| `tools-permission-fix` (not a CLI entry point) | 1 |
| **blocked on a missing parser seam** | **27** |
| **not a CLI invocation at all** | **2** |
| **TOTAL** | **29** |

**The dominant reason is one thing, and it is worth naming: 27 of the 29 are blocked on production
modules that expose no parser seam at all, and 15 of those are the `script-shared` build CLI.** That is
a property of the production code, not of this sweep — and it is the shape of proposal a later run
could act on: giving `_build_cli.py` a published `build_parser()` would make all 15 convertible at a
stroke.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` non-empty (12 test modules) → the gate applies.
`./pw quality-gate` clean: `ruff … All checks passed!`, `mypy … Success: no issues found in 408 source
files`, `SPDX-header check passed`.

Full `./pw verify`: **`=== verify: SUCCESS ===`**, whole-tree **20,322 passed, 14 skipped, 0 failed**
in 461s, with all three sub-steps including `test-compile` (mypy over the whole test tree). The
whole-tree total is higher than run 01's 20,272 because `main` gained tests from other merges in
between — the figure counts the tree at this run's base, not a delta attributable to this change.

## Verification

| # | Condition | Result |
|---|---|---|
| 1 | Collected test count does not decrease | **PASS** — 3,827 → 3,827 |
| 2 | Coverage does not decrease | **PASS** — no production code touched; the converted call sites drive the *same* handlers through the *real* parser |
| 3 | Line count | Not the subject of this run. Slice total 61,467 → 61,366 (−101) as a side effect |

**Parallel arm re-run:** `pytest <15 dirs> -o addopts="" -q -n auto` → **3,827 passed** in 102s.

**The order-dependence recorded in run 01 (F10) is unchanged and still open** — it is pre-existing, and
this run did not touch `test_extension_discovery.py`.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| G1 | B6 conversion | A hand-maintained flag table mis-modelled `--no-move-marketplace` (`store_false`), inverting the flag's meaning when the value was `False` | **Fixed** — table re-derived from the parser's own `_actions`, including action kind |
| G2 | B6 conversion | The same table omitted `type`, so `--limit 2` emitted a bare `int` into `argv` | **Fixed** — same re-derivation; non-string literals are rendered as strings |
| G3 | B6 survey | `script-shared`'s build CLI modules (`_build_cli.py`, `_build_execute_factory.py`) expose **no parser seam** — no `main()`, no published builder | **Recorded, not fixed** — production code is out of scope for a test-refactoring plan. 14 call sites are blocked on it; a published `build_parser()` would unblock all 14 |
| G4 | B6 survey | `manage-providers`' `_list_providers.py` / `_cred_*.py` are module-level entry points with no parser seam | **Recorded** — 12 call sites |
| G5 | B6 conversion | The production `handle_write` already carries `store = getattr(args, 'store', 'plans')` — a defensive default that exists *because* callers hand-build namespaces missing it | **Recorded as evidence for B6**, not changed |
| G6 | PR review (`coderabbitai`) | `test_separator_default_type` is named and commented "separator **defaults** to work log type … without `--type`", but passed `type='work'` explicitly — so it never exercised the default and a regression in that default would pass. **Pre-existing**: the hand-built namespace at `8872700` already hard-coded it, and the conversion faithfully preserved it | **Fixed** — `--type` is now omitted, so the parser's own default (`'work'`, confirmed by probe) selects the log. This is only fixable *because* of B6: with a hand-built namespace there is no default to fall back to, so the test had to state one. 88 tests pass |
| G7 | PR review (`coderabbitai`) | This report's own § "Why B6 did not run" claimed *"every script probed here exposes one [seam]"*, contradicting its own exception table, which records 27 sites whose scripts expose none | **Fixed** — the claim is narrowed to the scripts the sweep converts, and points at the table for the rest |
| G8 | PR review (`coderabbitai`) | This report's prose subtotals said 14 `script-shared` sites and 26 seam-blocked; the table's rows total **15** and **27** | **Fixed** in `f4bf557`, before the review arrived — the subtotals are now a table computed from the rows rather than eyeballed prose |

## Reviewer participation

_(completed at the merge gate)_

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** ~1h for this follow-up run.
* **Population:** one Claude Code cloud session, continuing after PR #1263 merged. ⛔ Not comparable to
  a plan-marshall `metrics.toon` total.

## Contract check (Step 9)

_(completed as the final pre-merge commit)_

## What have we learned (Step 9)

_(completed as the final pre-merge commit)_

## Residue

Everything from run 01's residue **except** D3's B6 sweep, which this run closed. Specifically still
open: the order-dependent failure (run 01 F10), the six new `sys.modules` registrations (run 01 F11),
D2 in full, D4's parametrization beyond one family, `test/pm-code-intelligence/`'s own D3 finding,
run 01's third D1 group, the randomised hermeticity arm, and D4's cold read.

**New from this run:** the 29 recorded `parse_ns` exceptions above — **27** of which are blocked on
production modules lacking a parser seam (15 in the `script-shared` build CLI, 12 in
`manage-providers`), and would be unblocked by publishing one. The remaining 2 are not CLI invocations
at all.
