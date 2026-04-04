# Commit and Push

Commit all changes and push to remote. Respects `commit_strategy` from phase-5-execute config.

## Prerequisites

- Config field `1_commit_push` is `true`
- `commit_strategy` from phase-5-execute config (per_deliverable/per_plan/none)

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
git status --porcelain
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
