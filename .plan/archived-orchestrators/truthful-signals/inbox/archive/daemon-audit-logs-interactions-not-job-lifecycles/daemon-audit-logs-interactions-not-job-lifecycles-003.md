envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:47:18Z

component=plan-marshall:build-pyproject
category=anti-pattern
bundle=plan-marshall

# A green quality-gate says nothing about test/ type errors — it is a strictly weaker gate than verify

## What was observed

Whole-tree `quality-gate` passed. `verify plan-marshall` then failed on three mypy
`no-any-return` errors in this plan's new test helpers, requiring a fourth commit
(`test(build-server): annotate fate-reporting test helpers for mypy`) after the
"pre-commit gate" had already reported green.

## Root cause (verified in build.py + pyproject.toml)

The two commands run mypy over **different path sets**:

- `cmd_quality_gate` → `cmd_compile(module)`. For a whole-tree run that is
  `marketplace/bundles` plus `.claude` (`build.py:145-159`). **`test/` is not in the
  set at all.**
- `cmd_test_compile` → `get_test_path(module)`, i.e. `test/` (`build.py:162-166`).
- `cmd_verify` = `quality-gate` **then** `test-compile` **then** `module-tests`
  (`build.py:314-334`).

`quality-gate` does run ruff over `test/`, which is what makes the gap easy to miss:
the command *does* touch `test/`, just not with the type checker. `pyproject.toml`
states the fact plainly at the mypy `exclude` list — "`./pw verify` never mypy-checks
`test/` (cmd_quality_gate compiles only marketplace/bundles), so test-compile is the
sole surface these break" — but that line sits in a config comment, not where the
pre-commit rule is stated.

## Why it matters to this epic

The project's standing discipline is "run quality-gate before committing". That rule
produces a **confident green whose caveat is invisible at the call site**: for any
change that touches `test/`, quality-gate is not the gate the operator believes it is.
The signal is not wrong; its scope is silently narrower than its name implies.

## Proposed rule

When a change touches `test/`, `quality-gate` alone is insufficient — run
`test-compile` (or `verify`) before committing. The durable form of the rule is
scope-derived rather than memorised: a pre-commit gate must cover every path the
change touches, and `quality-gate`'s mypy scope excludes `test/` by construction.

## Suggested scope

Two candidate remedies, orchestrator to choose:

1. **Doc-layer** — state the caveat where the pre-commit rule lives (CLAUDE.md Build
   Commands, `build-pyproject` SKILL.md) rather than only in a `pyproject.toml`
   comment.
2. **Tool-layer** — have `quality-gate` include `test-compile`'s mypy pass, or emit an
   explicit "mypy scope: marketplace/bundles, .claude (test/ NOT type-checked)" line in
   its own output so the green carries its own scope.
