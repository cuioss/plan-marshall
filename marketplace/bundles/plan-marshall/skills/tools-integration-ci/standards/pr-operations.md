# PR Operations

Pull request lifecycle operations: create, view, merge, auto-merge, close, ready, edit.

## Worktree-Isolated Plans

Several operations identify a PR by source branch, and the underlying `gh`/`glab` CLI
derives that branch from `git symbolic-ref HEAD` in the cwd. When a plan runs in an
isolated git worktree (`.claude/worktrees/{plan_id}`) but the Bash tool executes from
the main checkout, the cwd HEAD is the main branch, not the worktree's feature branch —
so cwd-based derivation picks the wrong branch and operations fail (e.g. `pr create`
returns *"No commits between main and main"*).

To handle this, branch-aware operations accept an explicit `--head BRANCH` argument:

| Operation | `--head` semantic |
|-----------|--------------------|
| `pr create` | Source branch for the new PR (forwarded as `gh --head` / `glab --source-branch`) |
| `pr view` | Branch whose PR to view (gh accepts a branch positional; glab uses `mr view {branch}`) |
| `pr merge` | Branch identifying the PR to merge (alternative to `--pr-number`; glab resolves IID via `mr list --source-branch`) |
| `pr auto-merge` | Same as `pr merge` |
| `ci status` | Same as `pr merge` |

For `pr merge`, `pr auto-merge`, and `ci status`, supply **exactly one** of `--pr-number`
or `--head`. Supplying both returns `status: error` with message `specify exactly one of --pr-number or --head`.
Supplying neither returns `status: error` with message `specify either --pr-number or --head`.

Callers running from the main checkout against a worktree-isolated plan branch MUST
pass `--head {plan_branch}` on every branch-aware operation. Callers running from inside
the worktree itself can omit `--head`.

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
the shell boundary, so Claude Code's shell-heading heuristic never fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
    --plan-id {plan_id}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the PR body, bound to this plan and kind.

### Step 2: Write the PR Body

```
Write({path from prepare-body}) with PR body markdown content
```

### Step 3: Create PR

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --plan-id {plan_id} --base main [--head feature/x]
```

The subcommand reads the body from the prepared scratch file, creates the PR,
and deletes the scratch on success. When invoking from the main checkout
against a worktree-isolated plan, pass `--head {plan_branch}` to bypass
cwd-based source-branch derivation. See *Worktree-Isolated Plans* above.

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

Supply exactly one of `--pr-number` or `--head`. From a worktree-isolated plan invoked
from the main checkout, prefer `--head {plan_branch}`.

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

```
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
