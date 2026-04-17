---
name: default:create-pr
description: Create pull request
order: 20
---

# Create PR

Create a pull request for the feature branch.

## Prerequisites

- Config field `2_create_pr` is `true`
- Branch has been pushed (Step 3)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` script invocations below MUST pass `--project-dir {worktree_path}`.

## Execution

### Check if PR already exists

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

- `status: success` with `pr_number` → PR already exists, skip creation. Use returned `pr_number` for automated review step.
- `status: error` → no PR exists, proceed to create one.

### Generate PR body

Read the request summary:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section summary
```

Use the path-allocate pattern: the script allocates the scratch path, the main
context writes the body with the Write tool, and `pr create` consumes the file.
No multi-line markdown crosses the shell boundary.

#### Step 1: Allocate the scratch body path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr prepare-body \
  --plan-id {plan_id}
```

Read the `path` field from the returned TOON — it is the canonical scratch
location bound to this plan. Do not invent a path of your own.

#### Step 2: Write the PR body

```
Write({path from prepare-body}) with PR body markdown content
```

Use `templates/pr-template.md` as the format. Include issue link from references
(`Closes #{issue}` if `issue_url` was set).

#### Step 3: Create PR via CI abstraction

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr create \
  --title "{title from request.md}" --plan-id {plan_id} --base {base_branch}
```

The `pr create` subcommand reads the body from the prepared scratch file, creates
the PR, and deletes the scratch on success.

Read `pr_number` and `pr_url` from the TOON output.

### Log PR creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize) Created PR #{pr_number}: {pr_url}"
```

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the PR outcome. The payload differs by branch:

**Branch A — new PR created** (from "Create PR via CI abstraction"): `{pr_number}` is the PR number returned by `pr create`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "#{pr_number}"
```

**Branch B — existing PR re-used** (from "Check if PR already exists"): `{pr_number}` is the PR number returned by `pr view`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "existing PR #{pr_number}"
```

**Branch C — PR creation skipped** (config `2_create_pr` is `false` or otherwise gated):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "skipped"
```
