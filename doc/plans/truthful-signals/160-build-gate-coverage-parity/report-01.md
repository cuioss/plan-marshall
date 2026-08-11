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

_(filled in as implemented — see below)_

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
