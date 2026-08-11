# Run report — 160-build-gate-coverage-parity (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/gate-coverage-parity-wra7b0 (harness-assigned)
**PR:** _pending_    **Outcome:** _in progress_

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

## Reviewer participation

_pending PR — see Step 7/8._

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
