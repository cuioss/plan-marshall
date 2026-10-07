envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:46:26Z

component=plan-marshall:workflow-integration-git
category=bug

# worktree remove times out at 60s, leaves a partial tree, then refuses the retry

During `branch-cleanup` this run, `git worktree remove` exceeded a **60-second** timeout. The removal had already begun, so the timeout left a **partially-deleted worktree** on disk. The natural recovery — re-run the same command — then **refused**, because the tree was in the inconsistent state the first attempt had produced.

Recovery required an operator-authorised `--force`, granted only after manually verifying that the partial tree contained zero modified files. That verification was the right precaution and it worked, but it was performed by hand, outside any workflow, on a state the tooling created and then would not clean up.

Three distinct defects sit in that sequence:

1. **The timeout is too tight for the operation.** Removing a worktree containing a full checkout plus build artifacts is not a 60-second operation on every machine. The project's own standing rule sets a 10-minute floor for build-class commands precisely because wall-clock varies; worktree removal is closer to that class than to a metadata operation.
2. **The failure is not atomic.** A timeout mid-delete leaves a state that is neither "removed" nor "intact". Any operation that can be interrupted must either be resumable or leave the tree in one of its two valid states.
3. **There is no documented recovery path.** The refusal on retry is arguably correct behaviour in isolation — `git` is protecting against destroying work. But it is the *wrong* answer here, because the only reason the tree looks unsafe is that the previous call was killed. The workflow that owns the removal should own the recovery, including the zero-modified-files check that made `--force` safe, rather than leaving the operator to reason it out.

The safety check the operator performed by hand is the interesting part: it is deterministic, cheap, and exactly the precondition that makes `--force` safe. It should be code.

## Solution

- **Raise the timeout** on `worktree-remove` to a value appropriate for deleting a full checkout, and source it from the same timeout-resolution path the build commands use rather than hard-coding a new constant.
- **Add a bounded, self-verifying recovery to the removal verb.** On a refused retry: confirm the tree has zero modified files and zero untracked non-ignored files, and only then escalate to `--force` automatically. If either check fails, stop and surface the specific files to the operator — that is a genuine escalation, not the one this run hit.
- **Distinguish the two refusal causes in the returned status.** "Refused because you have uncommitted work" and "refused because a previous removal was interrupted" are different conditions with different correct responses, and the current path collapses them into one refusal the caller cannot act on.
- Note the adjacent recurrence risk: the standing project memory records `git worktree remove` by hand as having previously **lost a plan directory**. Any automatic `--force` path must be gated on the zero-modified-files check, never on the refusal alone.

## Evidence

- observed this run during `branch-cleanup`: unforced `git worktree remove` timed out at 60s, leaving a partially-deleted tree; retry refused; operator-authorised `--force` succeeded after manual verification of zero modified files
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail` = `"PR #1061 merged via queue, main pulled, branch + worktree removed"` — the step reports unqualified success; the timeout, the partial state, and the operator escalation leave no trace in the recorded outcome
- that last point is itself the epic's theme: a step that required manual intervention to complete reports the same clean string as one that did not
