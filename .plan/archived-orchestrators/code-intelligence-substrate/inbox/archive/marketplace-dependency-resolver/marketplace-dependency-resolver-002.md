envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:14:44Z

component=plan-marshall:build-pyproject
category=bug
title=Scoped compile was structurally unsatisfiable for every thin bundle, and the failure read as the plan's own

# Scoped compile was structurally unsatisfiable for every thin bundle, and the failure read as the plan's own

## What happened

`plan marketplace-dependency-resolver` ran the resolved canonical command
`compile {bundle}` scoped to a bundle it had just touched. The command failed. The
failure presented as a defect in the plan's own change, because the plan had just
edited that bundle and the scope named that bundle.

It was neither. `pyproject.toml`'s `[tool.mypy] exclude` removed every file the
scoped invocation would have type-checked, so mypy received an **empty file set**
and the scope-emptiness guard in `build.py` turned that into a failure rather than a
vacuous pass. The trigger is structural: it fires for EVERY "thin" bundle whose only
`.py` file is `plan-marshall-plugin/extension.py`, which the exclude pattern covers.

## Why it is a lesson and not an incident

The class-wide reach was only established by reproducing the failure on
`pm-dev-frontend-cui` — a bundle this plan **never touched**. Until that
reproduction, every available signal pointed at the plan's own diff:

- the failing command named the bundle the plan had edited,
- the plan had in fact just edited that bundle,
- and the plan had no other green baseline to compare against.

The correct provenance move (`persona-plan-marshall-agent` Principle 8) is to
establish whether the signal is branch-introduced or inherited BEFORE re-attempting
the fix. Here the cheap decisive test was not `git log` and not a re-run — it was
**running the same scoped command against a bundle the branch had not touched**.

## Corrective rule

When a **scoped** build/verify command fails on a target the current change touched,
before treating the failure as branch-introduced, run the SAME scoped command
against a structurally-similar target the change did **not** touch. If it fails
there too, the defect is in the scoping mechanism, not in the diff.

This is cheaper and more decisive than a baseline CI lookup, and it distinguishes
the two classes that a same-target re-run cannot: "my diff broke it" vs "this scope
never worked for this shape of target".

## Secondary rule — an empty scope is not a pass and not a failure

A scope-emptiness guard that resolves to *failure* converts a configuration gap into
a defect signal attributed to the caller. A guard that resolves to *silent pass*
converts it into a false green. Neither is right: an empty resolved file set is a
**third outcome** and must be reported as such — "scope resolved to zero files" —
so the caller can tell a broken scope from a broken change.

## Disposition in this plan

The operator elected to FIX IT HERE as an accepted scope deviation rather than defer
it, because every thin bundle in the marketplace was affected.
