# PR Operations

Pull request lifecycle operations: create, view, merge, auto-merge, safe-merge, merge-queue, close, ready, edit. Also covers the `branch delete` leaf, which supports post-merge remote branch cleanup.

## Branch-Aware Operations: `--head BRANCH`

Several operations identify a PR by source branch, and the underlying `gh`/`glab` CLI derives that branch from `git symbolic-ref HEAD` in the cwd. When the Bash tool's cwd HEAD is not the branch the operation should target, cwd-based derivation picks the wrong branch and operations fail (e.g. `pr create` returns *"No commits between main and main"*).

To handle this, branch-aware operations accept an explicit `--head BRANCH` argument:

| Operation | `--head` semantic |
|-----------|--------------------|
| `pr create` | Source branch for the new PR (forwarded as `gh --head` / `glab --source-branch`) |
| `pr view` | Branch whose PR to view (gh accepts a branch positional; glab uses `mr view {branch}`) |
| `pr merge` | Branch identifying the PR to merge (alternative to `--pr-number`; glab resolves IID via `mr list --source-branch`) |
| `pr auto-merge` | Same as `pr merge` |
| `pr safe-merge` | Same as `pr merge` |
| `pr merge-queue` | Same as `pr merge` |
| `ci status` | Same as `pr merge` |

For `pr merge`, `pr auto-merge`, `pr safe-merge`, `pr merge-queue`, and `ci status`, supply **exactly one** of `--pr-number`
or `--head`. Supplying both returns `status: error` with message `specify exactly one of --pr-number or --head`.
Supplying neither returns `status: error` with message `specify either --pr-number or --head`.

Callers whose cwd HEAD does not match the operation target branch MUST pass `--head {branch}`. See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (worktree-isolated plans run from the main checkout against a feature branch and MUST always pass `--head {plan_branch}`).

---

## Workflow: View PR (Current Branch or --head)

**Pattern**: Provider-Agnostic Router

Get PR/MR details for the current branch (or a specific branch via `--head`).

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view [--head {branch}]
```

### Step 2: Process Result

```toon
status: success
operation: pr_view
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
state: open
title: Add feature X
head_branch: feature/add-x
base_branch: main
```

---

## Workflow: List PRs

**Pattern**: Provider-Agnostic Router

List pull requests with optional branch and state filters.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr list \
    [--head {branch}] [--state {open|closed|all}]
```

### Step 2: Process Result

```toon
status: success
operation: pr_list
total: 2
state_filter: open
head_filter: feature/my-branch

prs[2]{number,url,title,state,head_branch,base_branch}:
123	https://github.com/org/repo/pull/123	Add feature X	open	feature/my-branch	main
456	https://github.com/org/repo/pull/456	Fix bug Y	open	feature/my-branch	develop
```

---

## Workflow: Create PR

**Pattern**: Provider-Agnostic Router

Create a pull request using the three-step path-allocate pattern. The script
owns path allocation — callers never invent scratch paths. Markdown bodies are
written directly by the main context with its native Write tool, and the `pr
create` subcommand consumes the prepared file. No multi-line markdown crosses
the shell boundary, so the host platform's shell-heading heuristic never fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
    --plan-id {plan_id}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the PR body, bound to this plan and kind.

### Step 2: Write the PR Body

```text
Write({path from prepare-body}) with PR body markdown content
```

### Step 3: Create PR

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --plan-id {plan_id} --base main [--head feature/x]
```

The subcommand reads the body from the prepared scratch file, creates the PR,
and deletes the scratch on success. See *Branch-Aware Operations: `--head BRANCH`* above for when `--head` is required.

### Step 4: Process Result

```toon
status: success
operation: pr_create
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
```

---

## Workflow: Merge PR

**Pattern**: Provider-Agnostic Router

Merge a pull request.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase] [--delete-branch]
```

Supply exactly one of `--pr-number` or `--head`. See *Branch-Aware Operations: `--head BRANCH`* above for when `--head` is required.

### Step 2: Process Result

```toon
status: success
operation: pr_merge
pr_number: 123
strategy: squash
```

---

## Workflow: Auto-Merge PR

**Pattern**: Provider-Agnostic Router

Enable auto-merge on a pull request (merges automatically when all checks pass).

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase]
```

Supply exactly one of `--pr-number` or `--head`.

### Step 2: Process Result

```toon
status: success
operation: pr_auto_merge
pr_number: 123
enabled: true
```

---

## Workflow: Safe-Merge PR

**Pattern**: Provider-Agnostic Router

Poll the PR's mergeability until it is ready, then merge — hardening the merge against post-force-push `mergeable_state: blocked` staleness, where GitHub reports a PR as not-mergeable while it recomputes mergeability after a push.

On **GitHub only**, when readiness stays `blocked` past the poll timeout AND `--admin-merge-on-stuck-state` is set AND every active ruleset requirement is provably met (required checks all SUCCESS on the head SHA, branch not behind base, required approving reviews met, no required unresolved conversations), the verb falls back to `gh pr merge --admin`. The stuck-state gate fails closed: any unmet or unverifiable requirement refuses the admin merge. On **GitLab** there is no admin equivalent — `--admin-merge-on-stuck-state` is accepted for API uniformity but ignored, and a stuck-past-timeout MR returns an error rather than force-merging.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr safe-merge \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase] [--delete-branch] \
    [--admin-merge-on-stuck-state] [--poll-timeout SECONDS] [--poll-interval SECONDS]
```

Supply exactly one of `--pr-number` or `--head`. The `--admin-merge-on-stuck-state` admin fallback is GitHub-only.

### Step 2: Process Result

```toon
status: success
operation: pr_safe_merge
pr_number: 123
strategy: squash
merge_path: polled_clean
polls: 1
duration_sec: 0
```

`merge_path` is `polled_clean` when the PR became mergeable within the poll window and merged via the normal path, or `admin_fallback` when the GitHub-only stuck-state `--admin` merge was used.

---

## Workflow: Merge-Queue PR

**Pattern**: Provider-Agnostic Router

Enqueue the PR into the **platform merge queue** so the platform re-tests-and-merges it against the latest base branch. Unlike `pr safe-merge` (which merges immediately once the current PR is ready), `pr merge-queue` hands the merge to the platform's serialization mechanism, closing the residual staleness gap a truly-external commit (e.g. a dependabot merge to the base) opens — such a commit never acquires the session-scoped merge mutex, so only the platform queue can serialize against it. It composes with the widened merge mutex: the mutex guards the pre-enqueue rebase/force-push window; the merge queue serializes the merge itself.

On **GitHub**, the verb engages the merge queue via `gh pr merge --auto` (the PR is added to the queue configured on the target branch's protection rules). On **GitLab**, the platform equivalent is a **merge train** — a Premium/Ultimate-tier feature enabled per-project with no stable `glab` CLI surface — so the GitLab handler returns an explicit unsupported error rather than silently falling back to an immediate merge.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
    (--pr-number 123 | --head feature/x) [--strategy merge|squash|rebase] [--delete-branch]
```

Supply exactly one of `--pr-number` or `--head`.

### Step 2: Process Result

```toon
status: success
operation: pr_merge_queue
pr_number: 123
strategy: squash
enqueued: true
delete_branch: true
```

On GitLab the same invocation returns `status: error, operation: pr_merge_queue` with a message naming merge trains as the unsupported platform equivalent — surfaced explicitly (never a silent immediate-merge fallback) so cross-provider callers notice the mismatch.

---

## Workflow: Close PR

**Pattern**: Provider-Agnostic Router

Close a pull request without merging.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr close \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_close
pr_number: 123
```

---

## Workflow: Mark PR Ready

**Pattern**: Provider-Agnostic Router

Mark a draft PR as ready for review.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr ready \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_ready
pr_number: 123
```

---

## Workflow: Edit PR

**Pattern**: Provider-Agnostic Router

Edit a pull request title and/or body. Use the path-allocate pattern when
updating the body. Title-only edits skip Steps 1-2.

### Step 1 (optional): Allocate scratch path for new body

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
    --plan-id {plan_id} --for edit
```

### Step 2 (optional): Write the new body

```text
Write({path from prepare-body}) with new PR body markdown content
```

### Step 3: Execute the edit

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit \
    --pr-number 123 --plan-id {plan_id} [--title "T"]
```

Omit `--title` to update only the body; omit Steps 1-2 to update only the
title. At least one of `--title` or a prepared body must be supplied — the
script rejects calls that change nothing.

### Step 4: Process Result

```toon
status: success
operation: pr_edit
pr_number: 123
```

---

## Workflow: Delete Remote Branch

**Pattern**: Provider-Agnostic Router (REST API)

Delete a branch from the remote. This leaf is the canonical replacement for
direct `git push origin --delete {branch}` calls in post-merge cleanup and
other remote-only branch disposal scenarios. Local branch management stays in
`git -C {path} branch` territory and is intentionally out of scope.

Under the hood:

| Provider | API call |
|----------|----------|
| GitHub | `DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}` via `gh api` |
| GitLab | `DELETE /projects/{id}/repository/branches/{branch}` via `glab api` (project path is URL-encoded as the `{id}`) |

The `--remote-only` flag is **required**: it is an explicit acknowledgement
from the caller that any needed local cleanup has already been handled and
that this call targets only the remote ref. Omitting the flag fails argparse
validation before any network call.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci branch delete \
    --remote-only --branch {branch_name}
```

When the cwd's remote configuration does not match the target, bind subprocesses to a different checkout via the standard router flags: prefer `--plan-id <plan>` (auto-resolves the worktree via `manage-status get-worktree-path`), or fall back to the legacy `--project-dir <path>` escape hatch. The two flags are mutually exclusive — see `tools-integration-ci/SKILL.md` § "Worktree-Aware Invocation" for the full two-state contract and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific path convention.

### Step 2: Process Result

```toon
status: success
operation: branch_delete
branch: feature/old-branch
remote_only: true
already_gone: false
```

When the branch is already gone remotely (HTTP 404 from either provider, or
HTTP 422 from GitHub when the ref has just been removed), the script still
returns `status: success` but with `already_gone: true`. Deletion is
idempotent by design: callers can invoke this leaf safely without needing a
prior existence check.

On other failures (e.g. insufficient permissions, non-idempotent API errors),
the script returns `status: error` with `operation: branch_delete` and a
`message`/`context` pair carrying the underlying `gh`/`glab` stderr — no
retries are attempted.
