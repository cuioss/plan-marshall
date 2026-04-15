# PR Operations

Pull request lifecycle operations: create, view, merge, auto-merge, close, ready, edit.

---

## Workflow: View PR (Current Branch)

**Pattern**: Provider-Agnostic Router

Get PR/MR details for the current branch.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
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

Create a pull request using config-stored command.

**CRITICAL**: Never pass multi-line markdown through Bash `--body` arguments. Markdown headings (`##`) after newlines in quoted strings trigger Claude Code's shell security heuristic. Always use the Write tool for the body file, then reference it with `--body-file`.

### Step 1: Write PR Body

Use the Write tool to create the body file:

```
Write({artifact_path}/pr-body.md) with PR body markdown content
```

### Step 2: Create PR

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --body-file path/to/pr-body.md --base main
```

### Step 3: Process Result

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
    --pr-number 123 [--strategy merge|squash|rebase] [--delete-branch]
```

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
    --pr-number 123 [--strategy merge|squash|rebase]
```

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

Edit a pull request title and/or body.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit \
    --pr-number 123 [--title "T"] [--body "B"]
```

### Step 2: Process Result

```toon
status: success
operation: pr_edit
pr_number: 123
```
