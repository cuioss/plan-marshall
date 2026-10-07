envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:57:06Z

component=plan-marshall:workflow-integration-git
category=bug
proposed_title=A 60s-timeout worktree remove leaves a partial-delete state the retry then refuses

# A 60s-timeout worktree remove leaves a partial-delete state the retry then refuses

# Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.** Recovery required a manual `--force` outside the workflow. No data was at risk in this instance, but the failure mode is not self-healing and the step's own retry makes it worse.

## What happened

At `10:44:22Z`, `branch-cleanup`'s worktree removal:

1. **First attempt timed out after 60s mid-delete**, leaving 4 tracked-file deletions applied in the worktree (`LICENSE.md`, `build.py`, `pw`, `pw.bat`).
2. **Second attempt refused** — git now saw those partial deletions as *modifications* to a dirty worktree, which is exactly the condition a non-force `worktree remove` is designed to refuse.

The step correctly declined to force, verified via `git status --porcelain` that no untracked and no modified-content entries existed, established that all work was merged in PR #1049, and surfaced the manual recovery command rather than escalating privileges. That disposition is right and should not change.

## The defect

**The retry is anti-correlated with success.** The first attempt's partial progress is precisely what makes the second attempt fail. A timeout mid-delete does not leave the pre-attempt state — it leaves a state that the safety check reads as user-authored dirt. The longer the first attempt ran before timing out, the more certain the retry is to refuse.

Note the residue's composition: all four files are top-level repo-root files (`LICENSE.md`, `build.py`, `pw`, `pw.bat`). These are the same five paths `check-artifact-consistency` reported as `references_only` in this plan's footprint comparison — the deletion residue leaked into the footprint read too.

## Why the 60s timeout is itself suspect

A `git worktree remove` on a tree containing `.plan/`, a full `marketplace/` mirror and build caches is not a 60-second operation on a loaded machine. The ceiling appears to be a default rather than a measured envelope, and it is well below the project's own build-command floor.

## Proposed action

1. **Raise the timeout to a measured envelope** rather than a 60s default, consistent with how build commands resolve `bash_timeout_seconds` via architecture rather than hard-coding.
2. **Make the retry state-aware**: before a second non-force attempt, distinguish *partial-delete residue from the previous attempt* (tracked deletions only, no untracked entries, no content modifications) from *genuine user dirt*. The former is safe to complete; the latter must still refuse. The step already computes exactly this discrimination in its own log line — it just does not act on it.
3. **Alternatively, make removal atomic**: verify-clean → move-aside → remove, so a timeout leaves either the original tree or nothing, never a half-deleted tree.
4. Keep the non-force constraint. The fix is to stop *creating* the state that needs forcing, not to start forcing.

## Evidence

- `logs/work.log` 10:44:22Z — the full failure narrative including the verified `git status --porcelain` result and the manual recovery command
- `status.json` `phase_steps[6-finalize][branch-cleanup]` — `merged via queue, main pulled - worktree removal FAILED, needs manual force`
- `fragment-artifact-consistency.toon` — `references_only[5]: LICENSE.md, build.py, manage-status.py, pw, pw.bat`
