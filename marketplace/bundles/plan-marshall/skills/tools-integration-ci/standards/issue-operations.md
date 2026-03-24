# Issue Operations

Issue lifecycle operations: create, view, close.

---

## Workflow: Create Issue

**Pattern**: Provider-Agnostic Router

Create an issue.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X" --body "Description"
```

### Step 2: Process Result

```toon
status: success
operation: issue_create
issue_number: 789
issue_url: https://github.com/org/repo/issues/789
```

---

## Workflow: View Issue

**Pattern**: Provider-Agnostic Router

View issue details.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view \
    --issue 123
```

### Step 2: Process Result

```toon
status: success
operation: issue_view
issue_number: 123
issue_url: https://github.com/org/repo/issues/123
title: Bug in authentication flow
body: When users try to login...
author: username
state: open
created_at: 2025-01-15T10:30:00Z
updated_at: 2025-01-18T14:20:00Z

labels[2]:
- bug
- priority:high

assignees[1]:
- alice
```

---

## Workflow: Close Issue

**Pattern**: Provider-Agnostic Router

Close an issue.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue close \
    --issue 123
```

### Step 2: Process Result

```toon
status: success
operation: issue_close
issue_number: 123
```
