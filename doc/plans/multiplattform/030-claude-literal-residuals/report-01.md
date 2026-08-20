# Run report — 030-claude-literal-residuals (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/claude-literal-residuals-tcyauu`    **PR:** _pending_    **Outcome:** _in progress_

> **Verification loop exit:** _pending_

## Skills loaded

Loaded via the plugin notation where it resolved, else by bundle path — the route is recorded
because the `plan-marshall` plugin is often absent in a cloud session.

| Skill | Route | When |
|---|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, resolved) | first action |
| `plan-marshall:ref-code-quality` | bundle path | Step 1 |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Step 1 |
| `pm-dev-python:python-core` | bundle path | conditional — Python production code |
| `pm-dev-python:pytest-testing` | bundle path | conditional — Python tests |

Stated precisely, because "loaded" can be read wider than it is: for each of the four bundle-path
skills the `SKILL.md` was read. All four are **reference-mode** skills that index further
standards under `standards/`, and those sub-documents were **not** read — the changed files sit
inside an established house style and every edit follows the surrounding module's own
conventions. That is a choice, not a claim that the standards were consulted.

`plan-marshall:persona-implementer` and `pm-plugin-development:plugin-architecture` were **not**
loaded. The first is a work-identity persona the lane lists for production code; the second
governs `SKILL.md`/bundle structure, and this run's two `SKILL.md` edits are single table rows in
existing tables, not structural changes. Both omissions are disclosed rather than argued away.

No skill was unobtainable by both routes.

## Deliverables

_pending_

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
