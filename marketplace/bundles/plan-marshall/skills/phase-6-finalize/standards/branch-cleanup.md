# Branch Cleanup

Merge PR (with `--delete-branch`), wait for CI, and pull latest.

## Prerequisites

- Config field `8_branch_cleanup` is `true`
- A PR exists for the current branch (from Step 4: Create PR)
- Branch name available from references context (`branch` field)

## Execution

### Gather Context

Collect all information needed for the user confirmation dialog.

#### Get PR state

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

Extract: `pr_number`, `pr_url`, `state` (open/merged/closed), `head_branch`, `base_branch`.

If no PR found (status: error) → skip cleanup, log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: no PR found for current branch"
```

#### Check for other open PRs using this branch

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr list --head {head_branch} --state open
```

Extract count and details of other open PRs (excluding the current PR).

### User Confirmation Gate

**MANDATORY**: Present all context and ask user before any destructive action.

Determine planned actions based on PR state:
- **If `state == open`**: Actions = merge PR (with --delete-branch), wait for CI, pull latest
- **If `state == merged`**: Actions = pull latest

```
AskUserQuestion:
  questions:
    - question: "Branch cleanup will perform the following actions. Proceed?"
      header: "Branch Cleanup"
      description: |
        **PR**: {pr_url} ({state})
        **Branch**: {head_branch} → {base_branch}
        **Other open PRs for this branch**: {count} {details if any}

        **Actions**:
        {- Merge PR #{pr_number} with --delete-branch (if state == open)}
        {- Wait for CI checks to complete (if merging)}
        - Pull latest
      options:
        - label: "Yes, proceed"
          description: "Execute branch cleanup"
        - label: "No, skip"
          description: "Leave branch as-is"
      multiSelect: false
```

**If user selects "No, skip"**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup skipped: user declined"
```
→ Done, return.

### Safety Check: Other Open PRs

If other open PRs were found using this branch as head:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup aborted: {count} other open PR(s) use branch {head_branch}"
```

→ Abort cleanup. The user was already informed about these PRs in the confirmation dialog but confirmed anyway — however, deleting a branch with dependent PRs is too destructive. Log and skip.

### Merge PR (if not yet merged)

**Only if `state == open`**:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge \
    --pr-number {pr_number} --delete-branch
```

If merge fails with branch protection error ('base branch policy prohibits the merge'), fall back to auto-merge:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge \
    --pr-number {pr_number}
```

Log the fallback:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Branch cleanup: direct merge blocked by branch protection, enabled auto-merge"
```

If auto-merge also fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: PR merge failed - {error}"
```

### Wait for Merge CI

**Only if PR was just merged** (state was open):

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
    --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net).

If CI fails → log warning but continue (PR is already merged):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level WARN --message "[WARN] (plan-marshall:phase-6-finalize) Branch cleanup: post-merge CI failed — continuing with branch cleanup"
```

### Pull Latest

The `--delete-branch` flag on merge already deletes the remote branch, deletes the local branch, and switches to the base branch. Only `git pull` is needed to fetch the merge commit.

```bash
git pull
```

If pull fails → log error and abort:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Branch cleanup: git pull failed - {error}"
```

### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Branch cleanup complete: merged PR #{pr_number}, pulled latest on {base_branch}"
```
