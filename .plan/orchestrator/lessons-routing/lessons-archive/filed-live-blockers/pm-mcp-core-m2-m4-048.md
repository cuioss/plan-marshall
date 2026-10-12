envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:13Z

# Outline paths to a sibling repository break when the plan runs in a worktree

## What happened

Deliverables 1, 11, 12 and 13 of plan-06-store-substrate named their affected files and their
`trace.py` verification command relative to the main checkout (`../plan-marshall-documentation/...`).
The plan had `use_worktree=true`. Phase 5 runs with cwd pinned to the plan worktree under
`.plan/local/worktrees/`, where `../plan-marshall-documentation` resolves to
`.plan/local/worktrees/plan-marshall-documentation` — a directory that does not exist. The outline
Q-Gate caught it; the deliverables were rewritten to the absolute main-checkout path and the module
set to `plan-marshall-documentation`.

The repository's CLAUDE.md states relative links that "assume the repositories checked out beside
each other", so the `../` form looks correct when reading the request, which is how it got into the
outline.

## Rule

When a deliverable edits or verifies a file in a sibling repository, the outline must not use a
`../` path relative to the main checkout. State a main-checkout-anchored (absolute) path, or name a
branch/worktree of the sibling repository explicitly, for both the edit and the verification
command, and mark the deliverable as a sibling-repository edit that leaves through its own PR.

## Where it could be enforced

The outline validator could flag any affected-file path that starts with `../` when the plan has
`use_worktree=true`.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-001.md` from plan plan-06-store-substrate (PLAN-06, #26)
