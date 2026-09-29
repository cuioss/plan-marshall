envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:00Z

# push barrier's documented `git -C {wt} push` fails on every first push

**Observed (plan-12-tool-triage, finalize `default:push`):** push.md delegates to workflow-integration-git "Commit Changes" Step 6, whose only documented command is `git -C {worktree_path} push`. A plan's feature branch is created locally by `worktree-create` / `prepare_execute` with no upstream, so the first finalize push always fails: `fatal: The current branch feature/plan-12-tool-triage has no upstream branch` (exit 128).

**What the orchestrator had to do:** improvise `git -C {wt} push --set-upstream origin feature/plan-12-tool-triage` — a command no step documents, in a lane whose hard rule is "execute only documented commands". Both options (halt, or improvise) break the process.

**Why it matters:** the push barrier is on every plan's critical path, so this is not an edge case — the documented form succeeds only on re-pushes. The error-handling table's "git push failure → report error, never force-push" does not cover it either.

**Suggested fix directions:** Step 6 documents `git -C {wt} push --set-upstream origin {branch}` (idempotent on re-push), or `worktree-create` configures the upstream / `push.autoSetupRemote` at branch creation, or a `git-workflow push` verb owns the first-push case.
