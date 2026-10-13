envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-12T15:57:09Z

# Follow-up: harden head_at_completion capture timing across head-dependent finalize steps

**From:** lb-37-functional-review (PLAN-LB-37), raised by CodeRabbit on PR #1755 (thread PRRT_kwDOQ3xasM6rh4tG)

## Observation

Head-dependent finalize steps (`pre-push-quality-gate`, `architecture-refresh`, and the new `functional-review` / `code-review`) read the tree at the start of their work. They capture `git rev-parse HEAD` only immediately before the terminal `mark-step-done --head-at-completion`. If a commit landed between the read and the capture, the recorded SHA would name a tree the step never examined, and the dispatcher's re-entry check would skip the step.

## Why it was declined in PLAN-LB-37

Under the current design, finalize steps run sequentially in the one session that owns the worktree. The review author and verifier are read-only, so no commit can land mid-step. Changing only the two new steps would make them inconsistent with the existing convention.

## Suggested follow-up

Consider a system-wide change: capture the SHA at step start and record that SHA, or compare it with HEAD before recording and re-run on mismatch. Apply it uniformly to every step that declares `head_dependent`, and update the convention text in each step doc (e.g. `pre-push-quality-gate.md` "Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA").
