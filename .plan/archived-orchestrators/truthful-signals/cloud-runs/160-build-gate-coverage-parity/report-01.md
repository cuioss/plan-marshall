# Run report — 160-build-gate-coverage-parity (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/gate-coverage-parity-wra7b0 (harness-assigned)
**PR:** #1174 (https://github.com/cuioss/plan-marshall/pull/1174)    **Outcome:** completed (auto-merge armed; landing confirmed post-merge / delegated to collect)

## Skills loaded

- `cloud-plan-lane` (contract, first action)
- `plan-marshall:ref-code-quality` — read `standards/error-handling.md` (fail-closed classifier rules (b)/(d)/(e) — the canonical framing for D4/D5)
- `pm-plugin-development:plugin-script-architecture`
- `plan-marshall:persona-implementer`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

All loaded by bundle path (the `plan-marshall` plugin is not installed in this cloud session).

## D1 — Parity population, derived from tool configuration on both sides

**Files that define each side (named, not guessed):**

- **CI side:** `.github/workflows/python-verify.yml` delegates to the reusable
  `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml@v0.19.0`. That
  workflow runs `./pw <verify-goals>` where `verify-goals` defaults to `verify` and is overridable by
  `.github/project.yml` → `pyprojectx-verify-goals`. `.github/project.yml` sets **no** such key, so
  **CI runs `./pw verify`** = `build.py:cmd_verify(None)`, reading the identical `pyproject.toml` tool
  config. CI restores only the uv package cache (`cache-dependency-glob: uv.lock`); it does **not**
  restore `.mypy_cache` (upload-on-failure only), so **CI runs mypy cold**.
- **Local in-house gate side:** the finalize step
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`,
  backed by `derive_gate_bundles.py` and `script-shared/scripts/build/_test_scope_divergence.py`, plus
  the shared `build.py`. Ruff/mypy config: `pyproject.toml` `[tool.ruff.lint]` / `[tool.mypy]`.

**Key structural fact:** CI and every local `./pw` call read the **same** `pyproject.toml`. There is
no separate CI ruff/mypy config. So a "CI checks X, local doesn't" divergence is only possible where
the *in-house gate* runs a **subset** of `verify`, or where the **cache state** differs — not where
the tool config differs (it can't).

### Parity table (derived from code, both axes)

| Axis / dimension | Local in-house gate | CI (`./pw verify`) | Verdict | Evidence |
|---|---|---|---|---|
| **Scope:** mypy production | whole-tree `quality-gate` arm → `cmd_compile(None)` (bundles+.claude) | same | **EQUAL** | `build.py:244-252`; `pre-push-quality-gate.md` whole-tree arm |
| **Scope:** ruff rules | `[tool.ruff.lint] select` (RUF absent) | same file | **EQUAL** | `pyproject.toml:238`; `git log -S'"RUF"'` → never present |
| **Scope:** ruff path set | `ruff check [bundles, test, .claude]` | same | **EQUAL** | `build.py:340-342` |
| **Scope:** mypy test (`test-compile`) | whole-tree `test-compile`, unconditional | `cmd_test_compile(None)` | **EQUAL** | `pre-push-quality-gate.md` test-compile gate; `build.py:255-261,418` |
| **Scope:** SPDX header path set | `[bundles, test, .claude, targets, build.py]` | same | **EQUAL** | `build.py:349-352` |
| **Scope:** plugin-doctor | whole-tree `quality-gate` arm | `cmd_quality_gate(None)` | **EQUAL** | `build.py:361-371` |
| **Scope:** pytest module scope | divergence gate: whole-tree when `divergence_possible`, else scoped/none | always whole-tree | **CONDITIONAL SUBSET** | `_test_scope_divergence.py:254-255` — heuristic ignores reverse cross-module coupling → **sibling territory (D3 dedup)** |
| **Freshness:** mypy incremental cache | **incremental (warm on a dev machine)** | **cold (fresh clone, no cache restore)** | **OPEN** | `build.py:243,252,261` bare mypy, no `--no-incremental`; `.gitignore` ignores `.mypy_cache`; reusable workflow restores only `uv.lock` |
| **Honest-coverage property (D5):** verdict names its coverage boundary | no — degradation is log-only; default `display-detail` can misreport an un-run arm as "green" | n/a (CI exit code) | **OPEN** | `pre-push-quality-gate.md` honest-degradation WARNINGs decoupled from `mark-step-done` outcome |

**Population is NON-EMPTY** (the D6 assertion target): it contains the freshness cell (OPEN) and the
honest-coverage property (OPEN), plus seven evaluated scope dimensions (six EQUAL, one conditional
subset). Derived from the tool configuration on both sides, per the table above — not from the plan's
five-instance sample.

### The five sampled holes, re-adjudicated (sample ≠ population)

1. **RUF absent from local ruff `select=`** → **REFUTED as a parity gap.** RUF is absent from the one
   shared `[tool.ruff.lint] select`, so **neither** CI nor local checks it. Not a local-vs-CI
   divergence. Adding RUF would change what *both* sides check (out of scope: "Changing what CI
   checks"). No action.
2. **Pre-push gate lacks `mypy test/` parity; quality-gate excludes `test/`** → **CLOSED.**
   `cmd_quality_gate` indeed type-checks production only, but the finalize gate and `cmd_verify` both
   run a whole-tree `test-compile` unconditionally. Parity holds at the gate/verify level.
3. **Zero-scoped-modules → docs-only → clean-pass branch** → **CLOSED** (already fixed, sibling
   fail-closed plan). Empty footprint (`divergence_possible=False`, benign) is distinguished from
   "resolves to no registered module" (`unresolved_paths` non-empty → `divergence_possible=True` →
   whole-tree) by the `bool(unresolved_paths)` disjunct. Branch 5 is hard-ordered before branch 6 to
   stop a null `recommended_target` interpolating `module-tests None`.
4. **`marketplace/targets/**` not escalated to whole-tree gate** → **CLOSED as a parity gap.** The
   whole-tree `quality-gate` arm is **unconditional** and SPDX-checks `marketplace/targets` — exactly
   what CI's `cmd_verify` covers for that path. (Shared absolute caveat, not a divergence: ruff/mypy
   never see `marketplace/targets` in **either** arm; identical on both sides, so parity holds.)
5. **Stale mypy incremental cache** → **OPEN.** Confirmed: incremental is enabled (default; no
   `--no-incremental`/`incremental=false`/`cache_dir`), caches are git-ignored, CI is cold, local is
   warm, and there is **no** duration/plausibility/freshness sanity check anywhere. This is the one
   genuinely open hole among the five, and the sharpest — a scope-only fix cannot close it.

**Consequence for the deliverables:** the scope holes (D2, D3) are already closed by shared config and
the sibling's divergence fix; the real open work is **D4 (freshness)** and **D5 (honest coverage)**.
D2/D3 are discharged by verification-with-evidence, not by manufacturing a change (the honest outcome
the plan's "sample ≠ population" mandate and the lane both require). The conditional pytest-scope
subset is the sibling's divergence-classification territory (D3 dedup constraint) — recorded and
deferred, not re-fixed here.

### Serialization pairing & cross-epic coupling (re-verified at outline, against live state)

- **Serialization pair (D3 dedup):** the sibling "fail-closed-signal-integrity" fix — distinguishing
  "no module matched" from "no tests needed" — is **present in the live tree**
  (`_test_scope_divergence.py` empty-vs-unresolved handling + `pre-push-quality-gate.md` branch 5). I
  re-grounded D3 against that actual fix rather than the staging note: the conflation is already
  closed, so this plan does **not** re-implement it. The deeper reverse-cross-module-coupling subset
  in the pytest-scope dimension remains the sibling's divergence-classification domain.
- **Cross-epic coupling (`pre-push-quality-gate.md`):** this run's D5 edits that file. Recorded here
  so the deferral is retired by checking; the PR will name the coupling.

## Deliverables

- **D1 — parity population, derived.** Done (see the § "D1" table above). Derived from tool config on
  both sides; population asserted non-empty by `test_parity_population_is_non_empty`. Mutated nothing.
- **D2 — linter / type-check parity.** **No code change — already at parity, verified with evidence.**
  The local rule set and file set already match CI's because both read the one shared `pyproject.toml`
  (`ruff select`, `[tool.mypy]`), and the in-house gate runs a whole-tree `test-compile` unconditionally.
  RUF is absent from *both* sides (`git log -S'"RUF"'` → never present), so it is not a divergence to
  close; adding it would change what CI checks (out of scope). Manufacturing a change here would be the
  sample-not-population mistake D1 exists to prevent.
- **D3 — divergence-gate branch integrity.** **No code change — already closed (sibling fix), verified.**
  `_test_scope_divergence.resolve_test_scope` distinguishes empty footprint (benign) from
  unresolved-module (fail-closed to whole-tree) via `bool(unresolved_paths)`; branch 5 is hard-ordered
  before branch 6. `marketplace/targets/**` is escalated by the **unconditional** whole-tree
  quality-gate arm (SPDX, matching CI). The reverse-cross-module-coupling pytest-scope subset is the
  sibling's divergence-classification territory (dedup constraint) — recorded, not re-fixed.
- **D4 — freshness.** Done, `build.py` + `_gate_coverage.py`. (1) Every mypy invocation runs cold
  (`--no-incremental`) via `_run_mypy`, so a stale incremental cache can no longer produce a clean
  verdict — the local gate now matches CI's cold run. (2) `classify_check_duration` is a duration sanity
  check: an implausibly-fast success over a substantial file set (throughput above a conservative
  ceiling) fails closed with `_FRESHNESS_SUSPECT_RC`; a plausibly-timed run — cold or small-scope — is
  not flagged (demonstrated both directions in `test_gate_coverage` + `test_build_verify`).
- **D5 — gate reports what it did NOT check.** Done, `build.py` + `_gate_coverage.py` +
  `pre-push-quality-gate.md`. `CoverageBoundary` / `render_coverage_summary` make `verify` /
  `quality-gate` emit a COMPLETE-vs-PARTIAL coverage verdict naming any un-certified dimension (the
  cold-read: a PARTIAL verdict reads "not safe to push", never a clean pass). The finalize doc's
  `--display-detail` misreporting is fixed (a degraded whole-tree arm no longer reports "green"), and a
  "Coverage parity with CI, freshness, and honest coverage" section documents the property.
- **D6 — tests, red-first.** Done. `test_gate_coverage.py` (11 tests: duration both directions,
  coverage boundary, non-empty population) + 5 new integration tests in `test_build_verify.py`. The 5
  integration tests + 3 updated argv assertions were **seen red first** (8 failed against the
  unmodified `build.py`; see Findings) and green after the fix. Caveats recorded in Findings: the four
  already-closed scope holes have no red to show (closed by shared config / the sibling), and the
  zero-scoped-modules distinction is already covered by the sibling's landed tests.

## Build gate

Python changed (`git diff --name-only origin/main...HEAD -- '*.py'` non-empty: `build.py`,
`_gate_coverage.py`, two test files) → full `./pw verify` required.

- `./pw quality-gate` (per-commit gate, whole-tree): **clean** — all plugin-doctor analyzers 0 issues,
  `issues[0]` empty, and the run printed `coverage: COMPLETE — ... mypy(production) [393 files, cache
  disabled] ...` (cold run, freshness plausible).
- `./pw verify` (full, Step 5): **SUCCESS** — 19060 passed, 14 skipped (304s). Final line:
  `coverage: COMPLETE — ... mypy(production) [393 files, cache disabled] ... mypy(test) [708 files,
  cache disabled], module-tests [whole-tree pytest]` then `=== verify: SUCCESS ===`. The cold-run
  (`--no-incremental`) and freshness-plausible verdicts are visible in the summary, confirming D4/D5
  in the real gate.

## Findings

**Verification sub-agent (D1 cross-check, pre-implementation):** an independent `general-purpose` agent
audited the five sampled holes from code only. It confirmed holes 1–4 CLOSED (RUF absent from both
sides; whole-tree `test-compile` unconditional; empty-vs-unresolved distinguished; `marketplace/targets`
covered by the unconditional whole-tree arm) and hole 5 (freshness) OPEN, and surfaced one item not in
the five — the pytest module-scope conditional subset (sibling divergence-classification territory).
All findings accepted and drove the D1 table and the D2/D3 no-change-with-evidence dispositions.

**D6 red-first evidence (build gate):** the 5 new integration tests in `test_build_verify.py` plus the
3 updated argv assertions were run against the **unmodified** `build.py` → **8 failed, 17 passed**
(`test_compile_runs_mypy_cold_with_no_incremental`, `test_quality_gate_fails_closed_...`,
`test_quality_gate_does_not_flag_...`, `test_verify_prints_complete_coverage_summary_on_success`,
`test_verify_prints_partial_coverage_when_a_step_is_freshness_suspect`, and the three
`--no-incremental` argv assertions). After the fix → all green. The `test_gate_coverage.py`
pure-module tests exercise new capability (no pre-fix behaviour to see red). **Caveats, recorded per
the plan's D6:** the four already-closed scope holes (RUF, test-compile, zero-scope, `targets`) have no
red to demonstrate — they were closed by shared config / the sibling before this run; the
zero-scoped-modules-vs-docs-only distinction is already covered by the sibling's landed
`test_test_scope_divergence.py`. These are honest gaps in "one red per closed hole", not skipped work.

**CI/full-suite co-evolution (found by `./pw verify`, all fixed):** the first full run surfaced 5
failures in tests that drive the whole-tree/large-scope `quality-gate` with a stubbed subprocess —
each a legitimate consequence of the new behaviour, fixed at the test:

- `test_spdx_enforcement.py::test_quality_gate_fails_when_header_missing` — `cmd_compile` stub
  signature did not accept the new `boundary` kwarg → added `boundary=None`. Fixed.
- `test_spdx_enforcement.py::test_quality_gate_passes_when_all_headers_present` — same. Fixed.
- `test_pyproject_build.py::test_quality_gate_full_tree_invokes_plugin_doctor` — stubbed instant mypy
  tripped the freshness backstop before the plugin-doctor step under test → patched
  `time.monotonic` to a plausible advancing clock. Fixed.
- `test_pyproject_build.py::test_quality_gate_full_tree_propagates_plugin_doctor_failure` — same. Fixed.
- `test_pyproject_build.py::test_quality_gate_module_scoped_skips_plugin_doctor` — same. Fixed.

Re-run of `./pw verify` after the fixes: 19060 passed, 14 skipped, 0 failed.

**D5 cold-read verification (plan Verification requirement):** an independent sub-agent was shown ONLY
the PARTIAL coverage verdict text — a freshness-suspect `mypy(test)` — with no other context, and asked
"is it safe to push?" It answered **"No"**, correctly naming that mypy over the test tree was not
verified (the green came from a cache, not analysis of the current tree) and recommending a real
cache-disabled run before pushing. The reader did NOT take the partial verdict as a pass — the wording
does not reproduce the defect. D5's coverage-boundary output passes its cold read.

**Pre-PR verification sub-agent (Step 6):** an independent `general-purpose` agent verified the diff
against the plan's D1–D6, Out-of-scope, and Verification. Verdict: **all six deliverables PASS.** Dedup
constraint honored (`_test_scope_divergence.py` and its test are untouched — confirmed empty in
`--stat`); D4 cold-run + both-directions duration check confirmed; D5 boundary + finalize-doc fix
confirmed; out-of-scope compliance PASS; beyond-diff sweep found **no new stale claim** introduced by
the change. Two findings, both accepted as out-of-scope disclosures (see Residue). No findings required
a fix.

## Reviewer participation

Expected population derived from the registry docs
(`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,sourcery,pr-agent}.md`
→ `author_login`), cross-named by `.github/workflows/pr-agent.yml`. Verdicts read from the stored
comment/review bodies on PR #1174, not from check states:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "PR Reviewer Guide 🔍" over the diff: "PR contains tests / No security concerns identified / No major issues detected". A review with nothing to report. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in 41 minutes … used all free OSS reviews" — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" — engaged but did not review this diff. |

**Coverage: 1 of 3 reviewed.** Shortfall disclosure (Step 8 condition 4) fired: `cuioss-review-bot`
reviewed (no issues); `coderabbitai` rate-limited (window reopens ~41 min); `sourcery-ai` rate-limited
(weekly diff-character quota). Both rate limits are routine and outside our control — disclosed, **not**
blocked on. No inline review threads (0), no actionable review comment to fix or reply to.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not surface
  a token count to the running agent).
- **Wall-clock:** the run spanned roughly one interactive cloud session; the two full `./pw verify`
  runs cost ~305 s and ~351 s (measured from their own summaries), and the environment cold-boot (uv
  venv + interpreter download) was a one-time cost on the first `uv run`.
- **Population:** this single Claude Code cloud session's activity. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's per-task billing boundary — a boundary this single interactive session does not
  share. The figures above are wall-clock only; no commensurable token total exists to report.

## Cost

_pending_

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (all by bundle path; plugin not installed). |
| 2 Branch | Done — harness-assigned `claude/gate-coverage-parity-wra7b0` kept as-is; pushed to `origin` before any work. |
| 3 Plan directory | Done — `doc/plans/truthful-signals/160-build-gate-coverage-parity/plan.md` exists and opens with the first-instruction block (present on arrival; no repair needed). |
| 4 Implement / per-commit gate | Done — commits carry the trailer; the `*.py` commit was preceded by a clean `./pw quality-gate` (`total_issues: 0`, empty `errors[]`, `coverage: COMPLETE`). |
| 4 Pushed | Done — every commit pushed; the final report commit is the last push before arming. |
| 5 Build gate | Done — Python changed → full `./pw verify`; green (19060 passed) after fixing 5 test co-evolution failures. |
| 6 Verification sub-agent | Done — all six deliverables PASS; findings dispositioned in § Findings (none required a fix). |
| 7 PR cycle | Done — PR #1174; both comment surfaces read; no actionable comment; per-reviewer participation recorded. |
| 8 Merge gate | Conditions 1–3 met, shortfall (1-of-3) disclosed, auto-merge armed (see § Build gate / operator disclosure). Landing confirmed post-merge / delegated to collect. |
| 9 This check | This table. |

GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned**. A
`/sync-plugin-cache` is **not owed** — a cloud run neither performs nor records it (machine-local build
step). The PR touches `marketplace/bundles/**` bundle source; a local developer sync is a local concern,
not a debt of this run.

## What have we learned (Step 9)

**None proposed.** Every contract step applied cleanly in this environment and produced its named
artifact: the branch was kept and pushed; the conditional build gate took its full `*.py` path; the
verification sub-agent produced findings; the PR cycle read both comment surfaces and derived the
reviewer population from configuration; the merge gate's disclose-not-block shortfall rule fit the
observed 1-of-3 coverage exactly. No step was ambiguous, unproducible, or contradicted by the actual
tooling, so this run produced no evidence for a contract change. (The one friction — a stop-hook
flagging uncommitted changes while I paused mid-run to await a sub-agent — is a harness hook, not a lane
step, and is resolved by committing coherent units, which the contract already prescribes.)

## Residue

Two **pre-existing** imprecise comments the Step-6 sub-agent surfaced during the beyond-diff sweep.
Neither was introduced by this change, neither is affected by it, and both are out of this plan's
scope (which moves the gate's freshness/coverage honesty, not build-system help strings). Disclosed
here rather than silently fixed:

- `build.py` `verify` subparser `help='Full verification (quality-gate + module-tests)'` omits
  `test-compile`. Already stale before this change (`cmd_test_compile` was already chained into
  `cmd_verify`), and **explicitly documented as a deliberately-deferred item** in
  `pre-push-quality-gate.md` § "Adjacent item deliberately not covered". Fixing it here would
  contradict that recorded deferral. Leave to whoever retires that deferral.
- `pyproject.toml` `[tool.mypy]` comment "`./pw verify` never mypy-checks `test/`" is loosely worded
  (verify's `test-compile` arm does mypy-check `test/`; the comment's intent is that
  `cmd_quality_gate`'s *compile* step checks only `marketplace/bundles`). Pre-existing and unchanged
  by this diff. A future test-compile-registration change is the natural place to tighten it.

The pytest module-scope conditional subset (reverse cross-module coupling) remains the sibling
divergence-classification plan's territory — recorded in the D1 table (`pytest-scope: subset`), not
fixed here (D3 dedup constraint).
