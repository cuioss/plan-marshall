# PR Review Operations

Operations for interacting with pull request reviews: comments, replies, thread resolution, approval state.

---

## Workflow: Reply to PR

**Pattern**: Provider-Agnostic Router

Post a comment on a pull request using the three-step path-allocate pattern.
The script owns path allocation — callers never invent scratch paths. Markdown
bodies are written directly by the main context with its native Write tool, and
the `pr reply` subcommand consumes the prepared file. No multi-line markdown
crosses the shell boundary, so Claude Code's shell-heading heuristic never
fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-comment \
    --plan-id {plan_id} --for reply --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the reply body, bound to this plan and slot. Pick a `--slot` value
that is unique for each concurrent reply so their bodies do not collide.

### Step 2: Write the Reply Body

```
Write({path from prepare-comment}) with reply body markdown content
```

### Step 3: Post the Reply

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
    --pr-number 123 --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, posts the
comment, and deletes the scratch on success.

### Step 4: Process Result

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

Reply to a specific review thread (inline code comment), not a top-level PR
comment, using the three-step path-allocate pattern. The script owns path
allocation — callers never invent scratch paths. Markdown bodies are written
directly by the main context with its native Write tool, and the `pr
thread-reply` subcommand consumes the prepared file. No multi-line markdown
crosses the shell boundary, so Claude Code's shell-heading heuristic never
fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-comment \
    --plan-id {plan_id} --for thread-reply --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the thread-reply body, bound to this plan and slot. Pick a
`--slot` value that is unique for each concurrent thread-reply so their bodies
do not collide.

### Step 2: Write the Thread-Reply Body

```
Write({path from prepare-comment}) with thread-reply body markdown content
```

### Step 3: Post the Thread-Reply

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
    --pr-number 123 --thread-id PRRT_abc123 --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, posts the
thread-reply, and deletes the scratch on success.

### Step 4: Process Result

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

---

## Workflow: Wait for New Review Comments

See [blocking-wait-pattern.md](blocking-wait-pattern.md) for the general pattern, timeout/interval guidance, and the full wait-for-* subcommand catalog.

**Pattern**: Provider-Agnostic Router (polling, replaces blocking shell sleep)

Block until a new unresolved review comment is posted on the PR or the timeout elapses. Snapshots the unresolved-comment count once on entry, then polls on the standard CI interval and exits as soon as the count grows. Used by `workflow-pr-doctor`'s Automated Review Lifecycle (Step 2) in place of a bash `sleep`, which the harness blocks for long leading durations.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments \
    --pr-number 123 --timeout 180
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--pr-number` | yes | — | PR number |
| `--timeout` | no | 300 (caller usually passes `review_bot_buffer_seconds`) | Max wait time in seconds |
| `--interval` | no | 30 | Poll interval in seconds |

### Step 2: Process Result

```toon
status: success
operation: pr_wait_for_comments
pr_number: 123
timed_out: false
duration_sec: 47
polls: 2
baseline_count: 1
final_count: 2
new_count: 1
```

`status: success` is returned even when `timed_out: true` — the caller should still proceed to fetch comments (`pr comments --unresolved-only`) and triage whatever did arrive. `status: error` is reserved for fetch/auth failures.
