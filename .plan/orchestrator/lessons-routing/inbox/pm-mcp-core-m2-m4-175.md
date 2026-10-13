envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:13Z

# Candidate (Q-Gate 3-outline, fixed): sibling-repository deliverable used relative paths that break under use_worktree

Source: Q-Gate finding c103cb, phase 3-outline, warning; resolution fixed.

## Finding

Deliverable 8 listed its files as `../plan-marshall-documentation/...`. Those paths resolve from the main checkout, but with use_worktree: true they resolve against `.plan/local/worktrees/verify-not-resolve` at phase 5 and point to a directory that does not exist. Phase-6 also opens only this repository's PR.

## Resolution

Deliverable 8 switched to absolute paths under `/Users/oliver/git/plan-marshall-documentation`. Its own task branches, commits, pushes and opens the documentation PR; the operator merges.

## Lesson shape

A deliverable that edits a sibling repository must use absolute paths (or a declared sibling-checkout root) and must name who opens that repository's PR. Paths relative to the checkout are wrong as soon as a worktree is in use. This should be caught at outline-authoring time, not by the gate.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-009.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
