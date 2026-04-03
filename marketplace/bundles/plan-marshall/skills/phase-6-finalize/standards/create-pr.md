# Create PR

Create a pull request for the feature branch.

## Prerequisites

- Config field `2_create_pr` is `true`
- Branch has been pushed (Step 3)

## Execution

### Check if PR already exists

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

- `status: success` with `pr_number` → PR already exists, skip creation. Use returned `pr_number` for automated review step.
- `status: error` → no PR exists, proceed to create one.

### Generate PR body

Read the request summary:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section summary
```

Write PR body using the Write tool (**never** pass markdown through Bash `--body` arguments):

```
Write(.plan/plans/{plan_id}/artifacts/pr-body.md) with PR body markdown content
```

Use `templates/pr-template.md` as the format. Include issue link from references (`Closes #{issue}` if `issue_url` was set).

### Create PR via CI abstraction

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --title "{title from request.md}" --body-file .plan/plans/{plan_id}/artifacts/pr-body.md --base {base_branch}
```

Read `pr_number` and `pr_url` from the TOON output.

### Log PR creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize) Created PR #{pr_number}: {pr_url}"
```
