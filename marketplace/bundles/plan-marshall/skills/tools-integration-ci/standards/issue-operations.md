# Issue Operations

Issue lifecycle operations: create, comment, view, close — plus the two
path-allocate verbs the body-consuming pair depends on, `prepare-body` and
`prepare-comment`. The group also carries two polling verbs, `wait-for-close`
and `wait-for-label`; their flags are listed in
[leaf-command-reference.md](leaf-command-reference.md) and the pattern they
implement is in [blocking-wait-pattern.md](blocking-wait-pattern.md).

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `ci` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Plan-less callers: `--plan-id NO_PLAN`

`--plan-id` is required on all four body-store verbs here (`prepare-body`,
`create`, `prepare-comment`, `comment`) and the body store is their only body
channel. A caller with no plan runs the identical steps with `--plan-id
NO_PLAN`, the plan-less sentinel: it resolves to the shared plan-less body
store and binds to the main checkout. Use it only when the caller genuinely has
no plan — a `--plan-id` that failed to resolve must be corrected, never replaced
with the sentinel. The semantics are identical for every verb and are stated
once in [`tools-integration-ci/SKILL.md`](../SKILL.md) § "The `NO_PLAN` sentinel
— one plan-less convention for every `--plan-id` verb"; they are not repeated
per workflow below.

---

## Workflow: Create Issue

**Pattern**: Provider-Agnostic Router

Create an issue using the three-step path-allocate pattern. The script owns path
allocation — callers never invent scratch paths. The issue body is written
directly by the main context with its native Write tool, and the `issue create`
subcommand consumes the prepared file. No multi-line markdown crosses the shell
boundary, so the host platform's shell-heading heuristic never fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue prepare-body \
    --plan-id {plan_id} --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the issue body, bound to this plan and slot.

### Step 2: Write the Issue Body

```text
Write({path from prepare-body}) with issue body markdown content
```

### Step 3: Create Issue

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X" --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, creates the issue,
and deletes the scratch on success.

### Step 4: Process Result

```toon
status: success
operation: issue_create
issue_number: 789
issue_url: https://github.com/org/repo/issues/789
```

---

## Workflow: Comment on Issue

**Pattern**: Provider-Agnostic Router

Post a comment on an existing issue using the same three-step path-allocate
pattern as issue creation. The script owns the scratch path; the comment body is
written by the main context with its native Write tool, and the `issue comment`
subcommand consumes the prepared file. No multi-line markdown crosses the shell
boundary. On GitHub the comment is posted via `gh issue comment {n} --body`; on
GitLab via `glab issue note {iid} --message`.

### Step 1: Allocate Scratch Comment Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue prepare-comment \
    --plan-id {plan_id} --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the comment body, bound to this plan and slot.

### Step 2: Write the Comment Body

```text
Write({path from prepare-comment}) with comment markdown content
```

### Step 3: Post the Comment

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue comment \
    --issue {issue_number} --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, posts the comment,
and deletes the scratch on success. When no body has been prepared the subcommand
returns a `body_not_prepared` error and leaves no comment.

### Step 4: Process Result

```toon
status: success
operation: issue_comment
issue_number: 123
output: https://github.com/org/repo/issues/123#issuecomment-456
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
