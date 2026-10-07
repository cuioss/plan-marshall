envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:50:46Z

component=plan-marshall:audit-archived-plan-retrospectives
category=bug
title=audit.py's report-write path derives from Path.cwd() and ignores --plan-dir, so a sandboxed corpus read still writes into the real .plan tree

# audit.py's report-write path derives from Path.cwd() and ignores --plan-dir

## Observation

TASK-11 of plan `exploration-share-is-unmeasured` added a D3 test that invokes `audit.py`'s CLI. The test sandboxed the corpus **read** via `--plan-dir`, but the run still polluted the developer's real `.plan/local` tree: `write_persisted_report` derives its output path from `Path.cwd()` and **never consults `--plan-dir`**. The read was isolated; the write was not.

The leak was invisible locally. The dev worktree already contained `.plan/local/audit-reports`, so the emitted entry was not *new* there and the repository pollution guard — which fires on new entries — stayed silent. A clean CI checkout was the only environment where the guard could fire, and that is where it did.

Under `-n auto`, the leak additionally blamed **3 unrelated tests** as collateral, so the failure signal did not point at the offending test.

## What was done

TASK-11 fixed only the **test** side (`monkeypatch.chdir`). The production defect is still live.

## Rule

- A CLI that accepts a `--plan-dir`-style root argument MUST route **every** path derivation through it — reads *and* writes. A write path that falls back to `Path.cwd()` is an unsandboxable side effect, not a default.
- Fix at the tool layer when we own it: patching the *caller* (a test `chdir`) leaves the production defect intact and converts a real bug into an invisible one.
- **A guard that fires on "new entries" is blind in a tree that already contains the artifact.** Local green from such a guard is environment-dependent and is not evidence. Verify pollution guards in a clean checkout, or make the guard state-independent.
- When a pollution/isolation failure fans out under parallel execution (`-n auto`), the extra failures are collateral — attribute to the writer, not to the blamed tests.

## Residue

The production fix (make `write_persisted_report` honour `--plan-dir`) is **not yet done** and is owed.
