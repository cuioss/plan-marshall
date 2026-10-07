envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:21:37Z

component=plan-marshall:workflow-integration-git
category=bug
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# worktree-remove reports a 60s git timeout using the dirty-tree hint

## Context

At 17:54:26Z this plan's `branch-cleanup` called `worktree-remove` and got back:

```
error: worktree_remove_failed
message: git worktree remove failed: git timed out after 60 seconds
hint:    Pass --force only after verifying the worktree is clean.
```

The hint describes a **different failure** from the one that occurred. `git worktree remove` did not refuse over uncommitted changes — it was killed by a subprocess budget. This repository's worktree is large enough to exceed 60s for a routine removal, so the timeout is the expected path here, not an edge case.

The agent had to establish that by hand: `git status --porcelain` on the worktree showed exactly four unstaged **deletions** (`LICENSE.md`, `build.py`, `pw`, `pw.bat`) — the timed-out removal's own partial work, all four tracked and present on `main` — and the plan directory had already been moved back by `integrate_into_main`. Only after that did retrying with `--force` become a decision on evidence rather than on the hint's assumed precondition.

## Root cause

`git_provider.run_git` has `_DEFAULT_TIMEOUT_SECONDS = 60` and maps `subprocess.TimeoutExpired` to `(124, '', f'git timed out after {timeout} seconds')`. `cmd_worktree_remove` calls it with no `timeout=` override and then branches on `rc != 0` **once**, attaching a single unconditional hint:

```python
rc, _out, err = run_git(git_args)
if rc != 0:
    return {
        'status': 'error',
        'error': 'worktree_remove_failed',
        'message': f'git worktree remove failed: {err}',
        'hint': 'Pass --force only after verifying the worktree is clean.',
    }
```

Every distinguishable failure — rc 124 (timeout), rc 127 (git not on PATH), and a genuine dirty-tree refusal — is reported with the dirty-tree remedy. The return code that would separate them is already in hand and simply not read.

## Proposed action

Branch the returned payload on `rc`:

- **124** — name it a timeout, state the elapsed budget, and say plainly that `--force` does not address it. Offer the two things that do: a larger `timeout=` for this call site, or removing the worktree with the plan directory already moved back (which is the state that makes a retry safe).
- **127** — `git` not found on PATH; neither `--force` nor a retry helps.
- **anything else** — keep the existing dirty-tree hint, which is correct for the case it was written for.

Separately, consider whether `cmd_worktree_remove` should pass an explicit `timeout=` above the 60s default. `run_git`'s docstring calls 60s a default "that matches the absorbed worktree helper", but worktree removal on a large checkout is precisely the verb most likely to exceed it, and a timeout here leaves a **partially removed** worktree behind — the four staged deletions above are that partial state.

## Evidence

- Source: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git_provider.py` — `_DEFAULT_TIMEOUT_SECONDS = 60`, `except subprocess.TimeoutExpired: return 124, '', f'git timed out after {timeout} seconds'`
- Source: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `cmd_worktree_remove`, the `rc != 0` branch and its single `hint`
- `decision.log` 2026-08-26T17:54:26Z — the run's own record of the misattribution and the manual verification it forced
- aspect: llm_to_script_opportunities — "worktree-remove failure classification", confidence high
