# Leaf Command Reference

Consolidated cheat sheet of every `ci` leaf subcommand. Read this file before invoking any leaf subcommand whose exact flags you do not already know — do not transfer flag names from `gh` or `glab` memory.

All commands use the canonical form:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci {group} {subcommand} [flags]
```

Each row lists the subcommand, its required flags, optional flags, and a one-line purpose. For full examples and result schemas, load the linked group standards file.

Every group table below carries one row per registered sub-verb of that group — the tables are the complete index, not a selection. When a sub-verb is added, its row is added in the same change.

## `--plan-id` and the `NO_PLAN` sentinel

Two different flags spell `--plan-id` in these tables, and both accept the plan-less sentinel `NO_PLAN`:

- The **top-level routing flag**, placed before the group/sub-verb pair, binds the `gh`/`glab` subprocess cwd. It is optional on every invocation and is not repeated per row.
- The **verb-scoped body-store flag**, listed in the rows below, binds the prepared body file. Ten verbs take it: `pr prepare-body`, `pr prepare-comment`, `pr create`, `pr edit`, `pr reply`, `pr thread-reply`, `issue prepare-body`, `issue prepare-comment`, `issue create`, `issue comment`.

`--plan-id NO_PLAN` means the same thing everywhere: the shared plan-less body store, bound to the main checkout. It is the only plan-less convention — there is no `--body-file` and no per-verb escape hatch. Use it only when the caller genuinely has no plan; a `--plan-id` that failed to resolve must be corrected, not replaced with the sentinel. Full semantics: [`../SKILL.md`](../SKILL.md) § "The `NO_PLAN` sentinel — one plan-less convention for every `--plan-id` verb".

---

## pr — Pull Request Operations

Source: [pr-operations.md](pr-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `pr view` | _(none — uses current cwd HEAD)_ | _at most one of_ `--pr-number` _or_ `--head {branch}` | Get PR/MR details by number, by branch, or for the current branch. A landing poll MUST use `--pr-number` — the merge queue deletes the head branch as it merges |
| `pr list` | _(none)_ | `--head {branch}`, `--state {open\|closed\|all}` | List PRs with optional branch and state filters |
| `pr prepare-body` | `--plan-id` | `--for {create\|edit}`, `--slot {name}` | Allocate a script-owned scratch path for a PR description (path-allocate pattern). |
| `pr prepare-comment` | `--plan-id` | `--for {reply\|thread-reply}`, `--slot {name}` | Allocate a script-owned scratch path for a PR comment consumed by `pr reply` / `pr thread-reply`. |
| `pr create` | `--title`, `--plan-id` | `--base`, `--head {branch}`, `--slot {name}`, `--draft`, `--label {name}` (repeatable) | Create a PR. Body is consumed from the scratch file allocated by `pr prepare-body`. Pass `--head` from main checkout against worktree branch. |
| `pr merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy {merge\|squash\|rebase}`, `--delete-branch` | Merge a PR. Flag is `--strategy`, **not** `--merge-method` |
| `pr auto-merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy {merge\|squash\|rebase}` | Enable auto-merge when all checks pass |
| `pr merge-queue` | _exactly one of_ `--pr-number` _or_ `--head` | — | Enqueue the PR into the platform merge queue / merge train. Takes **no** `--strategy` or `--delete-branch` |
| `pr update-branch` | _exactly one of_ `--pr-number` _or_ `--head` | — | Update the PR branch with base-branch changes |
| `pr safe-merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy {merge\|squash\|rebase}`, `--delete-branch`, `--admin-merge-on-stuck-state`, `--poll-timeout {seconds}`, `--poll-interval {seconds}` | Poll readiness then merge. GitHub-only `--admin` stuck-state fallback (gated by `--admin-merge-on-stuck-state` + provably-met ruleset); ignored on GitLab |
| `pr close` | `--pr-number` | — | Close a PR without merging |
| `pr ready` | `--pr-number` | — | Mark a draft PR as ready for review |
| `pr edit` | `--pr-number`, `--plan-id` | `--title`, `--slot {name}` | Edit PR title and/or body. Body (if updated) is consumed from the scratch file allocated by `pr prepare-body --for edit`. |

**Worktree-isolated plans**: When invoking from the main checkout against a plan running
in `.plan/local/worktrees/{plan_id}`, never rely on cwd derivation on a branch-aware
operation (`pr create`, `pr view`, `pr merge`, `pr auto-merge`, `pr safe-merge`, `checks status`) —
the underlying gh/glab CLIs derive the source branch from cwd HEAD, which would otherwise
resolve to `main`. Pass `--head {plan_branch}`, except that on every one of those operations
but `pr create` (which has no PR yet) `--pr-number {number}` is the equally valid selector and
the *required* one for a landing poll. Examples:

```bash
# Create PR from worktree branch while running from main checkout.
# Step 1: allocate scratch path, Step 2: Write body, Step 3: create.
ci pr prepare-body --plan-id EXAMPLE-PLAN
# (Write the PR body to the returned path via the Write tool)
ci pr create --title "T" --plan-id EXAMPLE-PLAN --base main --head plan/jwt-auth

# Inspect that PR by branch (no PR number needed)
ci pr view --head plan/jwt-auth

# Check CI status by branch
ci checks status --head plan/jwt-auth

# Merge by branch
ci pr merge --head plan/jwt-auth --strategy squash --delete-branch

# Enable auto-merge by branch
ci pr auto-merge --head plan/jwt-auth --strategy squash

# Poll readiness then merge by branch (GitHub stuck-state admin fallback when enabled)
ci pr safe-merge --head plan/jwt-auth --strategy squash --delete-branch --admin-merge-on-stuck-state
```

---

## pr — Review Operations

Source: [pr-review-operations.md](pr-review-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `pr reply` | `--pr-number`, `--plan-id` | `--slot {name}` | Post a top-level comment on a PR. Body is consumed from the scratch file allocated by `pr prepare-comment --for reply`. |
| `pr comments` | `--pr-number` | — | Get inline review comments on a PR. **Not** `pr-comments`; **not** `--branch` |
| `pr wait-for-comments` | `--pr-number` | `--timeout {seconds}`, `--interval {seconds}` | Block until new review comments are posted (replaces a shell `sleep` loop) |
| `pr reviews` | `--pr-number` | — | Get the approval/change-request reviews for a PR |
| `pr thread-reply` | `--pr-number`, `--thread-id` (must be `PRRT_*`), `--plan-id` | `--slot {name}` | Reply inline to an existing review thread. Body is consumed from the scratch file allocated by `pr prepare-comment --for thread-reply`. |
| `pr resolve-thread` | `--pr-number`, `--thread-id` | — | Mark a review thread as resolved (independent of replies) |
| `pr submit-review` | `--pr-number` | — | **GitHub only.** Publish a pending draft review. GitLab returns an explicit error |

---

## checks — CI Status & Logs

Source: [ci-operations.md](ci-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `checks status` | _exactly one of_ `--pr-number` _or_ `--head` | `--error-style {maven\|gradle\|npm\|generic}` | Check CI status for a PR. Use `--head {branch}` from the main checkout against a worktree branch |
| `checks wait` | `--pr-number` | `--error-style {maven\|gradle\|npm\|generic}` | Poll CI until completion. Use Bash timeout ≥ 1800000 ms (30 min safety net) |
| `checks wait-for-status-flip` | `--pr-number` | `--expected {success\|failure\|any}`, `--timeout {seconds}`, `--interval {seconds}` | Block until the CI status flips off `pending` (default: any non-pending flip) |
| `checks rerun` | `--run-id` | — | Rerun a failed CI workflow run |
| `checks logs` | `--run-id` | — | Get logs from a CI workflow run |

---

## branch — Branch Operations

Source: [pr-operations.md](pr-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `branch delete` | `--remote-only`, `--branch {name}` | — | Delete a remote branch via REST API. `--remote-only` is required and explicit — local branches are managed via `git -C {path} branch`, never via this leaf. |

---

## issue — Issue Operations

Source: [issue-operations.md](issue-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `issue prepare-body` | `--plan-id` | `--slot {name}` | Allocate a script-owned scratch path for an issue description. |
| `issue create` | `--title`, `--plan-id` | `--labels`, `--slot {name}` | Create an issue. Body is consumed from the scratch file allocated by `issue prepare-body`. |
| `issue prepare-comment` | `--plan-id` | `--slot {name}` | Allocate a script-owned scratch path for an issue comment consumed by `issue comment`. |
| `issue comment` | `--issue`, `--plan-id` | `--slot {name}` | Post a comment on an existing issue. Body is consumed from the scratch file allocated by `issue prepare-comment`. |
| `issue view` | `--issue` | — | View issue details |
| `issue close` | `--issue` | — | Close an issue |
| `issue wait-for-close` | `--issue-number` | `--timeout {seconds}`, `--interval {seconds}` | Block until the issue leaves the `open` state. Flag is `--issue-number`, **not** `--issue` |
| `issue wait-for-label` | `--issue-number`, `--label` | `--mode {present\|absent}`, `--timeout {seconds}`, `--interval {seconds}` | Block until a label is added (default) or removed. Flag is `--issue-number`, **not** `--issue` |

---

## repo — Repository Operations

Source: [pr-operations.md](pr-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `repo merge-queue probe` | _(none)_ | — | Probe platform merge-queue eligibility/state; returns one of `eligible_configured` / `eligible_unconfigured` / `ineligible` / `unsupported` (GitHub merge queue / GitLab merge train). |
| `repo merge-queue enable` | _(none)_ | — | Enable/configure the platform merge queue (idempotent — an already-configured project is left unchanged). |
| `repo label ensure` | `--label` | `--color {6-hex-digit RGB, no leading #}`, `--description {text}` | Create the repository label if missing (idempotent — an existing label is a no-op success). |

---

## barrier — Finalize-Wait Coordinator (router-level verb)

Source: [`../SKILL.md`](../SKILL.md) § "barrier"

Not a group: `barrier` is handled by the `ci.py` router directly — no provider dispatch, no CI provider required, no worktree resolution.

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `barrier` | `--settled-head {sha}`, `--signal NAME:STATE[:HEAD]` (repeatable) | — | Compute the per-signal-proceed / bounded-re-settle decision for the phase-6 concurrent finalize wait. Pure computation. |

---

## Common Anti-Patterns

These specific mistakes have been observed when transferring `gh`/`glab` flag names from memory:

| Wrong | Right | Why |
|-------|-------|-----|
| `ci pr-comments --branch X` | `ci pr comments --pr-number 123` | `pr-comments` is not a subcommand; `comments` lives under `pr`, and PR scoping is via `--pr-number` |
| `ci checks status --branch X` | `ci checks status --head X` _or_ `ci checks status --pr-number 123` | The branch flag is `--head`, **not** `--branch` |
| `ci pr merge --merge-method squash` | `ci pr merge --pr-number 123 --strategy squash` | Flag is `--strategy`, not `--merge-method` |
| `ci issue wait-for-close --issue 123` | `ci issue wait-for-close --issue-number 123` | The two `issue wait-for-*` verbs take `--issue-number`; the rest of the `issue` group takes `--issue` |
| `ci pr create --body-file body.md` | `ci pr prepare-body --plan-id NO_PLAN` → Write → `ci pr create --title T --plan-id NO_PLAN` | `gh pr create` has a `--body-file`; this leaf does not. The prepare/consume body store is the only body channel, and `NO_PLAN` is the plan-less route into it |

When in doubt, load the relevant group standards file (`pr-operations.md`, `pr-review-operations.md`, `ci-operations.md`, `issue-operations.md`) for full examples and result schemas.
