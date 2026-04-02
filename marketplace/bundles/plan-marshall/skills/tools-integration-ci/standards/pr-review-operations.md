# PR Review Operations

Operations for interacting with pull request reviews: comments, replies, thread resolution, approval state.

---

## Workflow: Reply to PR

**Pattern**: Provider-Agnostic Router

Post a comment on a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
    --pr-number 123 --body "Fixed as suggested."
```

### Step 2: Process Result

```toon
status: success
operation: pr_reply
pr_number: 123
```

---

## Workflow: Resolve Review Thread

**Pattern**: Provider-Agnostic Router

Resolve (mark as resolved) a review thread on a PR.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
    --pr-number 123 --thread-id PRRT_abc123
```

### Step 2: Process Result

```toon
status: success
operation: pr_resolve_thread
thread_id: PRRT_abc123
```

---

## Workflow: Reply to Review Thread

**Pattern**: Provider-Agnostic Router

Reply to a specific review thread (inline code comment), not a top-level PR comment.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
    --pr-number 123 --thread-id PRRT_abc123 --body "Fixed as suggested."
```

### Step 2: Process Result

```toon
status: success
operation: pr_thread_reply
pr_number: 123
thread_id: PRRT_abc123
```

---

## Workflow: Get PR Reviews

**Pattern**: Provider-Agnostic Router

Get reviews for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_reviews
pr_number: 123

reviews[2]{user,state,submitted_at}:
alice	APPROVED	2025-01-15T10:30:00Z
bob	CHANGES_REQUESTED	2025-01-15T11:00:00Z
```

---

## Workflow: Get PR Comments

**Pattern**: Provider-Agnostic Router

Get inline review comments on a PR.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_comments
provider: github
pr_number: 123
total: 3
unresolved: 2

comments[3]{id,thread_id,author,body,path,line,resolved,created_at}:
IC_abc123	PRRT_thread1	alice	Fix this null check	src/Main.java	42	false	2025-01-15T10:30:00Z
IC_abc124	PRRT_thread1	bob	Done	src/Main.java	42	false	2025-01-15T11:00:00Z
IC_abc125	PRRT_thread2	alice	Typo here	README.md	10	true	2025-01-15T09:00:00Z
```

See [api-contract.md](api-contract.md) for provider-specific field mappings.
