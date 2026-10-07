# Run report — 320 the plugin pin trap (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/sync-plugin-cache-updates-1jh33w` (harness-assigned)    **PR:** [#1213](https://github.com/cuioss/plan-marshall/pull/1213)    **Outcome:** completed (landing delegated to the merge queue)

## Skills loaded

Via the bundle-path route (the `plan-marshall` plugin is not installed in this cloud session):

- `plan-marshall:ref-code-quality` (+ standards `code-organization.md`, `error-handling.md`)
- `pm-plugin-development:plugin-script-architecture` (+ `test-scaffolding.md`)
- `plan-marshall:persona-implementer`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

All obtainable by path; none had to be reported as unavailable.

## Deliverables

| # | What was done | Commit | Verification state |
|---|---|---|---|
| **D0** | GATE (mutates nothing). Confirmed **from source, by symbol** that the plugin-cache sync writes only the CACHE and never the REGISTRY. `sync.py::main` → `_rsync_bundle` writes `{cache_root}/{bundle}/{version}/`; `_copy_dist_manifest` writes `{cache_root}/dist-manifest.json` (the marketplace's version manifest, **not** the plugin manager's registry). No registry write path exists anywhere in the sync entry point. The EXECUTOR store is written by a *different* symbol (`generate_executor.py::generate_executor`, atomic `os.replace`), invoked by the finalize/preflight path — never the registry. So the organising claim's "…and the executor" refers to the broader sync **flow**, not `sync.py` alone. | — (analysis) | Established by reading `sync.py` end-to-end; independently re-confirmed by the verification sub-agent. |
| **D1** | Detector oracle (`_plugin_pin_trap.evaluate`): gates on `executor == installPath` and NAMES the field (`GATE_FIELD = 'installPath'`); asserts `installPath == version` as a SEPARATE conjunct (shape 5); marks the unmarked set registry-derived (`_UNMARKED_DERIVED_NOTE`); content-vs-source as `ContentComparison.render()` → "N of M match; K diverge" with a partial-scan note, never a boolean; double-samples via `_volatile_signature`; `indeterminate` is a distinct outcome; publishes sampling instant, population size, newest marker age (age reported, never fed to the oracle); divergence and GC-exposure as separate axes. | `2aab1be` | 35 detector tests green. Sub-agent: SATISFIED. |
| **D2** | `assert_loaded_version(announced_base_dir, pinned_version)` — parses the loader's announced base dir, fails closed, and states which version it got. | `2aab1be` | 3 tests (pass/fail/indeterminate). SATISFIED. |
| **D3** | Operator remedy stated: `REMEDY_OPERATOR` (what to run, operator-only, do-not-write-registry), `REMEDY_NO_RESTART` (a restart does not fix it), `REMEDY_IN_RUN_TEMPLATE` (read the pinned file directly). Assembled into `Verdict.remedy` on FAIL. | `2aab1be` | `test_fail_verdict_states_operator_remedy_*`. SATISFIED. |
| **D4** | `loader_selected_version` mirrors `select_live_version_dir`: newest version-key among the live set (unmarked ∪ retention-pinned newest, whose marker is ignored). D1 uses it and never assumes the loader resolves to the registry pin (shape 3 fires when `loader != installPath`). | `2aab1be` | 4 loader tests + shape-3 divergence test. SATISFIED (deliberate-mirror caveat noted below). |
| **D5** | Three coupled fixes in `generate_executor.py`: (1) `cmd_generate` now `except (Exception, SystemExit)` so discovery's `sys.exit(2)` reaches the glob fallback; (2) `discover_scripts_fallback` matches `test_`/`_test` precisely (keeps `latest.py`); (1)+(2) in the same commit; (3) `verify_executor` + `get_executor_mappings` pass paths via argv, not into `python3 -c` source (all three `-c` sites fixed). | `f4b7df0` | 5 tests + standalone red-first evidence. Ordering constraint honoured (1+2 same commit). SATISFIED. |
| **D6** | `parse_args_with_toon_errors` augments an "unrecognized arguments: --flag" rejection when `--flag` is a declared root-level router flag, naming that it belongs before the verb; unknown flags keep the default rejection; exit code stays 2. | `c4290c9` | 8 tests. SATISFIED. |
| **D7** | Fixture-driven tests: six shapes + shape-6-distinct-from-shape-1, healthy passes, non-pinned load reported, disagreeing samples → indeterminate, the negative control (two agree third differs → FAIL), and SystemExit → glob fallback keeping `latest.py`. | `f4b7df0`, `c4290c9`, `2aab1be` | 48 new tests, all green. SATISFIED. |

Non-blocking caveat (superseded — this statement was wrong on both counts): `loader_selected_version` omitted the real selector's `is_candidate` predicate, and the divergence it caused is NOT confined to the newest dir lacking `skills/`. That is only `collect_script_dirs`' predicate; `resolve_bundle_path` passes a PER-REQUEST `lambda d: (d / subpath).exists()`, which resolves BACKWARD to an older dir whenever the newest one does not carry the subpath being resolved — the mechanism behind the incident this detector was built for. Nor was the omission documented in the module: it carried no such caveat at all. The model now takes an eligibility set and its docstring names both predicates.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production + test Python changed), so the build gate took its full path.

- `./pw quality-gate`: clean — `ruff … All checks passed!`, `mypy … Success: no issues found in 397 source files`, `SPDX-header check passed`, plugin-doctor marketplace-wide clean.
- `./pw` `test-compile` (mypy over the test tree, 730 files): clean **after** the fix below.
- Affected-module suites (`tools-script-executor`, `tools-input-validation`, `plugin-doctor`): 2370 passed locally, no regressions; the 48 new tests green.
- CI (`verify / conclusion`) is the full-suite authority; final state recorded to the operator.
- `UV_HTTP_TIMEOUT=600` was exported on every `./pw` call.

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | CI `verify / test-compile` | `test_plugin_pin_trap.py` annotated helpers with `StoreObservation`, a runtime variable pulled off the `load_script_module`-loaded module; mypy over the test tree rejects a variable used as a type (`valid-type` / `no-any-return`). My local `quality-gate` + scoped `module-tests` did not run `test-compile`, so it slipped through locally. | **fixed** — dropped the two annotations (`5afcdcb`); `test-compile` clean (730 files). |
| 2 | Verification sub-agent | No hard gap in any deliverable D0–D7. Three non-blocking caveats: the `loader_selected_version` deliberate-mirror simplification; the detector is a library+adapters not yet wired into a live gate (declared residue); "seen red first" asserted, not diff-reproducible. | **accepted** — caveats recorded; the red-first claim is backed by standalone reproductions (below). |
| 3 | Red-first evidence (D7) | `'test' in 'latest.py'` is `True` (old drop); `except Exception` lets `SystemExit` escape; a quoted path in an interpolated `-c` yields returncode 1; the pre-fix argparse fall-through emitted no "belongs before" note. | **evidence recorded** — each new fix-test targets the fixed behaviour. |

## Reviewer participation

Expected population derived from `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` (`author_login`), cross-named by `.github/workflows/pr-agent.yml`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide": "PR contains tests / No security concerns identified / No major issues detected" — a clean verdict over the diff. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in 99 minutes"; no review of the diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters"; no review of the diff. |

**Coverage: 1 of 3.** No inline review threads; no actionable review comment on any surface (all three surfaces read: `get_reviews`, `get_comments`, `get_review_comments`). The § Step 8 shortfall disclosure fired: "Review coverage: 1 of 3 — `cuioss-review-bot` reviewed with no findings; `coderabbitai` rate-limited (resets ~99 min); `sourcery-ai` rate-limited (weekly quota)." Rate limits are routine and outside our control; the merge is not held for them.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not surface a per-run token count to the model).
- **Wall-clock:** run on 2026-08-13; PR opened ~16:56 UTC. Merge landing time recorded to the operator on completion.
- **Population:** this single Claude Code cloud session's usage. ⚠ NOT comparable to a plan-marshall `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which this interactive session does not share.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named above; all via the bundle-path route. |
| 2 Branch | Done — harness-assigned `claude/sync-plugin-cache-updates-1jh33w`, pushed to `origin` before any work. |
| 3 Plan directory | Done — `320-…/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed. |
| 4 Per-commit gate | Done — every `*.py` commit was preceded by a clean quality gate; the `test-compile` gap (Finding 1) was caught by CI and fixed. |
| 4 Pushed | Done — no unpushed commit remains. |
| 5 Build gate | Done — Python changed → full path; quality-gate + test-compile + affected module-tests green. |
| 6 Verification sub-agent | Done — dispatched; no hard gaps; findings/caveats recorded. |
| 7 PR cycle | Done — PR #1213; every comment surface read; the only comments are two rate-limit notices + one clean bot guide; nothing actionable. |
| 8 Merge gate | Conditions 1–3 met; auto-merge armed. Landing delegated to the merge queue (see operator note); shortfall disclosed. |
| 8 Bridge | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. |
| 9 This check | This table. |
| 9 What have we learned | Proposal below. |

GitHub access path used: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned** (`claude/*`). A `/sync-plugin-cache` is **not owed** — it is a machine-local build step a cloud run neither performs nor records.

## What have we learned (Step 9)

**Proposal (evidence from this run):** the lane's Step 5 build gate says run `./pw verify`, but a run that optimizes for speed by substituting `./pw quality-gate` + scoped `./pw module-tests {module}` (as this run initially did) **silently omits `test-compile` — the mypy-over-the-test-tree sub-step**. `verify` is exactly `quality-gate` + `test-compile` + `module-tests` (`build.py::cmd_verify`), and `test-compile` is the only one that type-checks the `test/` tree. This run's quality-gate and affected module-tests were both green locally, yet CI's full `verify` failed at `test-compile` on a test-only mypy error (a dynamically-loaded class used as a type annotation — the exact shape the `load_script_module` pattern invites). The fix cost one extra CI round.

The Step 5 wording could name the three sub-steps explicitly and warn that running the pieces separately omits `test-compile`, so a run either invokes the full `./pw verify` or explicitly runs `test-compile` before the PR. This is a wording clarification to the contract (not a mechanism change); it is presented to the operator and, if accepted, shipped as a separate `chore/` PR touching only the skill — never folded into this plan's PR.

Recorded as **proposed, pending operator decision**.

## Residue

- The detector (`_plugin_pin_trap.py`) is a library + adapters with fixture tests; it is not yet wired into a live pre-launch / mid-run flow or a plugin-doctor rule. The plan's Goal ("a detector exists", tested against fixtures) is met; wiring it into a running gate is a natural follow-up, out of this plan's declared scope.
- Per the plan's STOP CONDITION, no live cache/registry/executor measurement was attempted (absent from a fresh clone); every measurement in the plan was treated as motivation, and the detector is tested against fixtures.
- The Step 9 contract-change proposal above awaits an operator decision; if accepted it ships as a separate `chore/cloud-plan-lane` PR.
