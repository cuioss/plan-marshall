---
name: default:create-pr
description: Create pull request
order: 20
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Create PR

Pure executor for the `create-pr` finalize step. Creates a pull request for the feature branch.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `create-pr` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Inputs

- Branch has been pushed (handled by `commit-push` earlier in the manifest list)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override). The two flags are mutually exclusive. Examples below use the literal `--project-dir {worktree_path}` form; substitute `--plan-id {plan_id}` to use auto-resolution.

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:tools-integration-ci"
```

```
Skill: plan-marshall:tools-integration-ci
```

### Resolve branch context

Read the plan's branch and base-branch from `references.json`. This step grounds the `{base_branch}` placeholder used in every subsequent git diff and `ci pr create` call — do NOT improvise a branch-context read from any other source.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

Parse the returned TOON and bind:

- `{branch}` ← `branch` field (the feature branch, e.g. `feature/{plan_id}`)
- `{base_branch}` ← `base_branch` field (e.g. `main`)

Both fields are required. If `status: error` is returned, STOP and return an error TOON — the plan has no references context and the PR cannot be created.

### Check if PR already exists

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Inspect the returned TOON — branch on BOTH `status` AND `state` (an open PR is reusable; a merged/closed one is not):

- `status: success` AND `state == open` → an open PR already exists for this branch. Skip creation; reuse the returned `pr_number` for the automated review step (Mark Step Complete → Branch B).
- `status: success` AND `state ∈ {merged, closed}` → the returned PR is a **stale association**, not a reusable PR. This happens when the branch name is reused across runs (a deterministic `feature/{plan_id}` whose prior run already merged): `gh pr view <branch>` returns the most-recent PR for the branch name regardless of state when no open PR exists, so a merged/closed PR resolves here. The current branch's new commits need their own PR — do NOT reuse it. Proceed to create a fresh PR (Mark Step Complete → Branch A). Recipe plan_ids carry a `{yyyy-mm-dd-hh}` suffix (see `phase-1-init/SKILL.md` Step 2 "From recipe") precisely to avoid this branch-name reuse, but this state guard is the structural backstop if a collision ever occurs by another path.
- `status: error` → no PR exists, proceed to create one (Branch A).

### Generate PR body

Read the request summary:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section summary
```

Use the path-allocate pattern: the script allocates the scratch path, the main
context writes the body with the Write tool, and `pr create` consumes the file.
No multi-line markdown crosses the shell boundary.

#### Step 1: Resolve the changed-file set

Before drafting any body content, ground the body against the actual diff so
file references cannot be fabricated. The diff is a local operation and is
resolved with `git` directly (the `tools-integration-ci` abstraction covers
provider-side operations such as PR creation, reviews, and threads — local
working-tree diffs are out of its scope):

```bash
git -C {worktree_path} fetch origin {base_branch}
```

```bash
git -C {worktree_path} diff --name-only origin/{base_branch}...HEAD
```

Read the returned file list as `{changed_files}`. This is the authoritative
diff scope for the body. Use `origin/{base_branch}...HEAD` (three dots) so
the comparison runs against the merge base — the same file set GitHub /
GitLab will show on the PR — rather than including unrelated changes that
have landed on `{base_branch}` since the feature branch diverged.

#### Step 2: Allocate the scratch body path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr prepare-body \
  --plan-id {plan_id}
```

Read the `path` field from the returned TOON — it is the canonical scratch
location bound to this plan. Do not invent a path of your own.

#### Step 3: Write the PR body

```
Write({path from prepare-body}) with PR body markdown content
```

Use `templates/pr-template.md` as the format. Include issue link from references
(`Closes #{issue}` if `issue_url` was set).

**File-reference constraint**: Every file path mentioned in the PR body MUST
belong to `{changed_files}` from Step 1. Fabricating file references that are
not in the resolved diff scope is a workflow violation — it undermines the
reviewer trust model that the rest of the finalize pipeline is built on. If a
template section calls for a file that is not in `{changed_files}`, omit the
section rather than invent a reference.

#### Step 4: Create PR via CI abstraction

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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "#{pr_number}"
```

**Branch B — existing PR re-used** (from "Check if PR already exists"): `{pr_number}` is the PR number returned by `pr view`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step create-pr --outcome done \
  --display-detail "existing PR #{pr_number}"
```

Note: there is no "skipped" branch — when the manifest excludes `create-pr`, the dispatcher does not run this document at all, so no step record is written. The renderer treats absent records as "not configured" rather than "skipped".

## Output

```toon
status: success | error
display_detail: "<#{pr_number} or 'existing PR #{pr_number}'>"
pr_number: {pr_number}
branch: {branch}
```

The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above; it is the same string the orchestrator surfaces.
