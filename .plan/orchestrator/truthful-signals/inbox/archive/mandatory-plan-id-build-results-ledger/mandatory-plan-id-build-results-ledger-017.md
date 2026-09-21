envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:10Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=A hardening guard's caller population must be enumerated, never reasoned about in prose

# A hardening guard's caller population must be enumerated, never reasoned about in prose

**Status: LIVE REGRESSION IN MAIN**, introduced by `finalize-step-security-audit` during
PR #1075 (`mandatory-plan-id-build-results-ledger`, `PLAN-TRUTH-026`). Found post-merge by
CodeRabbit, independently verified by the plan-retrospective audit.

## The defect

`finalize-step-security-audit` added a path-containment guard to
`tools-file-ops/scripts/file_ops.py::get_build_results_dir`. The guard is **correct**: it
raises `ValueError` when the resolved build-results directory escapes the `plans/` root.

The guard's own docstring justifies its safety posture like this:

> every production caller reaches here through an argparse `--plan-id` that a
> `validate_plan_id` (or an equivalent downstream `manage-status` lookup) has already
> rejected traversal on, so this guard is **expected never to fire**

That is a claim about the **caller population**, and it is false. A deterministic sweep
returns exactly three call sites:

| # | Call site | Input source | Safe? |
|---|---|---|---|
| 1 | `_build_result.py:180` | argparse `--plan-id` | yes — the docstring's reasoning holds |
| 2 | `_cmd_cleanup.py:358` | the `NO_PLAN_SENTINEL` literal | yes — a constant cannot escape |
| 3 | `_cmd_cleanup.py:356` | **`plans_dir.iterdir()`** | **NO** |

Call site 3 is inside `cleanable_build_results_dirs()`, iterating **real on-disk plan
directory names**, with no `try`/`except`. One plan directory symlinked out of the store
raises out of `cleanable_build_results_dirs()`, through **both** `clean_build_results()`
and `get_status()`, and aborts the whole `cleanup` / `cleanup --target all` /
`cleanup-status` command with an unstructured traceback — after `temp`, `logs`,
`archived-plans` and `no-plan-bodies` may already have been cleaned.

Sibling helpers in the same file (`build_result_files`, `clean_no_plan_bodies`) already
catch per-item `OSError` to keep going. This call site does not follow that pattern.

## The detail that makes this worth a lesson

**The plan shipped the proof of the hazard in its own test suite, in the same commit.**

`test/plan-marshall/tools-file-ops/test_file_ops.py:1209` is
`test_get_build_results_dir_rejects_plan_dir_symlinked_out_of_the_store` — a test that
asserts precisely the condition that breaks `_cmd_cleanup`. The test demonstrating the
trigger and the caller that trips over it landed together, authored by the same plan,
minutes apart.

The gap was never a lack of information. It was that the caller population was described in
prose instead of computed. `git grep get_build_results_dir` returns 3 production rows; the
docstring's universal quantifier ("every production caller") was written without running it.

## Do this instead

- When a finalize hardening step makes a previously-total function **partial** (adds a raise),
  the step's obligation is not complete until it has **enumerated that function's callers
  mechanically** and classified each one as safe-by-construction or needing a handler.
  Three rows is a cheap enumeration; the prose that replaced it cost a production regression.
- Treat a docstring sentence of the form *"every caller ..."* / *"this is expected never to
  fire"* as a **checkable assertion about a set**, in exactly the same way the
  `ext-self-review-plan-marshall` stale-count-prose detector treats "3 sites". A universal
  quantifier over callers is count-prose wearing different clothes.
- A guard justified as *defence in depth* is the highest-risk kind, because "expected never
  to fire" is the sentence that stops anyone from asking who calls it.

## Immediate action owed

Apply the `try`/`except ValueError: continue` at `_cmd_cleanup.py:356` (CodeRabbit supplied a
committable patch). Filed as finding `7a0541`.

## ALSO OWED: 13 of CodeRabbit's 14 post-merge findings are untracked

CodeRabbit's post-merge review (2026-08-02T06:28:09Z) filed **8 inline actionable comments,
1 outside-diff comment, and 5 nitpicks**. Only the `_cmd_cleanup` one was filed. The rest:

| Severity | File | Line | Claim | Verified by the audit |
|---|---|---|---|---|
| MAJOR | `_build_server_protocol.py` | 394 | `JobSpec.from_dict` accepts `''` and coerces `None` to `'None'` | **CONFIRMED** — see the sibling candidate-lesson |
| MAJOR | `cwd-policy.md` (+4 sites) | 34 | "bounded six-consumer set" for `resolve_main_anchored_path` with no executable allowlist | not checked |
| MAJOR | `test_manage_change_ledger.py` | 363 | `annotation == 'str'` fails because `_ledger_core` lacks future annotations | **REFUTED — DO NOT ACTION.** The import is at `_ledger_core.py:36`; the assertion is sound |
| MAJOR | `test_build_shared.py` | 297, 309 | hardcodes `'NO_PLAN'` instead of importing `NO_PLAN_SENTINEL` | not checked |
| MAJOR | `build-api-reference.md` | 28-42 | outside-diff: build-class membership fixed at four wrappers, must derive from the argparse roster | not checked |
| Minor | `decision-rules.md` | 321 | hardcoded four-entry build-extension roster vs `discover_build_extensions()` | not checked |
| Minor | `manage-run-config/SKILL.md` | 255 | build-results table row ends mid-sentence at "under the `NO_PLAN` sentinel's" | not checked |
| Minor | `menu-maintenance.md` | 177 | example `total_bytes_freed: 29824` vs its components' sum 30208 | not checked |
| Trivial | `manage-run-config/SKILL.md` | 397 | literal cleanup-target list must mirror `CLEANUP_TARGETS` | not checked |
| Trivial | `test_build_execute.py` | 512 | bare `pytest.raises(TypeError)` accepts an unrelated `TypeError` | not checked |
| Trivial | `test_build_execute_factory.py` | 47 | `NO_PLAN_SENTINEL` read from a fixtures module carrying its own literal | not checked |
| Trivial | `test_execute_script.py` | 589 | `_BUILD_CLASS_NOTATION` hardcoded rather than derived | not checked |
| Trivial | `test_execute_script.py` | 765 | degraded-ledger test pins `command`/`duration_seconds` but not `outcome` | not checked |

Note the shape of the untracked set: **five of the thirteen are "a hardcoded list that must
mirror a set defined elsewhere"** — the same derive-from-the-authoritative-source rule this
plan's own theme rests on, unapplied in the plan's own tests and docs.
