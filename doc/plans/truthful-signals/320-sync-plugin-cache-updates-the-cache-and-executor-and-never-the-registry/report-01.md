# Run report — 320 the plugin pin trap (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/sync-plugin-cache-updates-1jh33w` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Via the bundle-path route (the `plan-marshall` plugin is not installed in this cloud session):

- `plan-marshall:ref-code-quality` (+ standards `code-organization.md`, `error-handling.md`)
- `pm-plugin-development:plugin-script-architecture` (+ `test-scaffolding.md`)
- `plan-marshall:persona-implementer`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

All obtainable by path; none had to be reported as unavailable.

## Deliverables

| # | What was done | Commit | Verification |
|---|---|---|---|
| **D0** | GATE (mutates nothing). Confirmed **from source, by symbol** that the plugin-cache sync writes only the CACHE and never the REGISTRY. `sync.py::main` → `_rsync_bundle` writes `{cache_root}/{bundle}/{version}/` and `_copy_dist_manifest` writes `{cache_root}/dist-manifest.json`; there is **no registry write path** anywhere in the sync entry point. The EXECUTOR store is written separately by `generate_executor.py::generate_executor` (atomic `os.replace`), invoked by the finalize/preflight path — never the registry. The registry (`installPath`/`version` per entry) is the plugin manager's file. | — (analysis) | Established by reading `sync.py` end-to-end; the absence is bounded by the sync entry point's own surface, which contains no `~/.claude/**config` write. |
| **D1** | Detector oracle (`_plugin_pin_trap.evaluate`): gates on `executor == installPath` and NAMES the field (`GATE_FIELD = 'installPath'`); asserts `installPath == version` as a SEPARATE conjunct (shape 5); marks the unmarked set registry-derived (`_UNMARKED_DERIVED_NOTE`); content-vs-source as `ContentComparison.render()` → "N of M match; K diverge" with a partial-scan note, never a boolean; double-samples via `_volatile_signature`; `indeterminate` is a distinct outcome; publishes sampling instant, population size, newest marker age; divergence and GC-exposure as separate axes. | `2aab1be` | 35 detector tests. |
| **D2** | `assert_loaded_version(announced_base_dir, pinned_version)` — parses the loader's announced base dir, fails closed, and states which version it got. | `2aab1be` | 3 tests (pass/fail/indeterminate). |
| **D3** | Operator remedy stated: `REMEDY_OPERATOR` (what to run, operator-only, do-not-write-registry), `REMEDY_NO_RESTART` (a restart does not fix it), `REMEDY_IN_RUN_TEMPLATE` (read the pinned file directly). Assembled into `Verdict.remedy` on FAIL. | `2aab1be` | `test_fail_verdict_states_operator_remedy_*`. |
| **D4** | `loader_selected_version` models `select_live_version_dir`: newest version-key among the live set (unmarked ∪ retention-pinned newest, whose marker is ignored). D1 uses it and never assumes the loader resolves to the registry pin. | `2aab1be` | 4 loader tests + shape-3 divergence test. |
| **D5** | Three coupled fixes in `generate_executor.py`: (1) `cmd_generate` now `except (Exception, SystemExit)` so discovery's `sys.exit(2)` reaches the glob fallback; (2) `discover_scripts_fallback` matches `test_`/`_test` precisely (keeps `latest.py`); (1)+(2) in the same commit; (3) `verify_executor` + `get_executor_mappings` pass paths via argv, not into `python3 -c` source. | `f4b7df0` | 5 tests + standalone red-first evidence. |
| **D6** | `parse_args_with_toon_errors` augments an "unrecognized arguments: --flag" rejection when `--flag` is a declared root-level router flag, naming that it belongs before the verb; unknown flags keep the default rejection; exit code stays 2. | `c4290c9` | 8 tests. |
| **D7** | Fixture-driven tests (live cache/registry/executor absent from a fresh clone): six shapes + shape-6-distinct-from-shape-1, healthy passes, non-pinned load reported, disagreeing samples → indeterminate, the negative control (two agree third differs → FAIL), and SystemExit → glob fallback keeping `latest.py`. | `f4b7df0`, `c4290c9`, `2aab1be` | 48 new tests total, all green. |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production + test Python changed), so the build gate took its full path.

- `./pw quality-gate`: **clean** — `ruff … All checks passed!`, `mypy … Success: no issues found in 397 source files`, `SPDX-header check passed`, plugin-doctor marketplace-wide clean.
- Affected-module test suites (`tools-script-executor`, `tools-input-validation`, `plugin-doctor`): **2370 passed**, no regressions.
- The 48 new tests: all green.
- `UV_HTTP_TIMEOUT=600` was exported on every `./pw` call (cloud PyPI fetch path).

## Findings

Red-first evidence (pre-fix would fail), confirmed by standalone reproduction:

- D5.2 — `'test' in 'latest.py'.lower()` is `True`: the old bare-substring check dropped `latest.py`.
- D5.1 — `except Exception` lets `SystemExit` escape: the old fallback never ran on `sys.exit(2)`.
- D5.3 — a single quote in an interpolated `-c` path yields a `SyntaxError` (returncode 1).
- D6 — the pre-fix `orig(message)` fall-through produced no "belongs before the verb" note.

Verification sub-agent (Step 6): _pending — dispatched, awaiting report._
CI: _pending._
PR review: _pending._

## Reviewer participation

Expected population derived from `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` (`author_login`), cross-named by `.github/workflows/pr-agent.yml`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | _pending_ | — |
| `coderabbitai` | _pending_ | — |
| `sourcery-ai` | _pending_ | — |

Coverage: _pending (N of 3)._

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not surface a per-run token count to the model).
- **Wall-clock:** run started ~2026-08-13; PR/merge times recorded to the operator on completion.
- **Population:** this single Claude Code cloud session's usage. ⚠ NOT comparable to a plan-marshall `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which this interactive session does not share.

## Contract check (Step 9)

_Filled at Step 8 condition 3, before arming auto-merge._

## What have we learned (Step 9)

_Filled at Step 8 condition 3._

## Residue

- The detector (`_plugin_pin_trap.py`) is a library + adapters with fixture tests; it is not yet wired into a live pre-launch / mid-run flow or a plugin-doctor rule. The plan's Goal is "a detector exists" tested against fixtures, which is met; integration into a running gate is a natural follow-up but out of this plan's declared scope.
- Per the plan's STOP CONDITION, no live cache/registry/executor measurement was attempted (absent from a fresh clone); every measurement in the plan was treated as motivation, and the detector is tested against fixtures.
