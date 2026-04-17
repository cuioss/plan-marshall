# Commit and Push

Commit all changes and push to remote. Respects `commit_strategy` from phase-5-execute config.

## Prerequisites

- Config field `1_commit_push` is `true`
- `commit_strategy` from phase-5-execute config (per_deliverable/per_plan/none)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST use `git -C {worktree_path}`.

## Execution

### Check commit_strategy

**If `commit_strategy == none`**: Skip commit entirely.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Commit skipped: commit_strategy=none"
```

**If `commit_strategy == per_deliverable`**: Only commit if there are uncommitted changes remaining (some changes may already be committed per-deliverable during execute phase).

**If `commit_strategy == per_plan`**: Commit all changes as a single commit (default behavior).

### Check for uncommitted changes

```bash
git -C {worktree_path} status --porcelain
```

If output is empty → no changes to commit, done.

### Load git_workflow skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-git"
```

```
Skill: plan-marshall:workflow-integration-git
```

Execute the git_workflow skill's **Workflow: Commit Changes** with:
- `message`: Generated from request.md summary
- `push`: true (always push in finalize)
- `worktree_path`: `{worktree_path}` resolved at finalize entry

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the commit outcome. The payload differs by branch:

**Branch A — commit created**: `{commit_hash}` is the short 7-character hash of the commit produced by the `workflow-integration-git` call above (captured from its return payload):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --display-detail "-> {commit_hash}"
```

**Branch B — no uncommitted changes** (skipped path from "Check for uncommitted changes" above):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step commit-push --outcome done \
  --display-detail "no changes"
```
