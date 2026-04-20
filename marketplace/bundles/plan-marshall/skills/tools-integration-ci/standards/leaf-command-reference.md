# Leaf Command Reference

Consolidated cheat sheet of every `ci` leaf subcommand. Read this file before invoking any leaf subcommand whose exact flags you do not already know — do not transfer flag names from `gh` or `glab` memory.

All commands use the canonical form:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci {group} {subcommand} [flags]
```

Each row lists the subcommand, its required flags, optional flags, and a one-line purpose. For full examples and result schemas, load the linked group standards file.

---

## pr — Pull Request Operations

Source: [pr-operations.md](pr-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `pr view` | _(none — uses current cwd HEAD)_ | `--head {branch}` | Get PR/MR details for current branch (or `--head` branch) |
| `pr list` | _(none)_ | `--head {branch}`, `--state {open\|closed\|all}` | List PRs with optional branch and state filters |
| `pr prepare-body` | `--plan-id` | `--for {create\|edit}`, `--slot {name}` | Allocate a script-owned scratch path for a PR description (path-allocate pattern). |
| `pr prepare-comment` | `--plan-id` | `--for {reply\|thread-reply}`, `--slot {name}` | Allocate a script-owned scratch path for a PR comment consumed by `pr reply` / `pr thread-reply`. |
| `pr create` | `--title`, `--plan-id` | `--base`, `--head {branch}`, `--slot {name}`, `--draft` | Create a PR. Body is consumed from the scratch file allocated by `pr prepare-body`. Pass `--head` from main checkout against worktree branch. |
| `pr merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy {merge\|squash\|rebase}`, `--delete-branch` | Merge a PR. Flag is `--strategy`, **not** `--merge-method` |
| `pr auto-merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy {merge\|squash\|rebase}` | Enable auto-merge when all checks pass |
| `pr close` | `--pr-number` | — | Close a PR without merging |
| `pr ready` | `--pr-number` | — | Mark a draft PR as ready for review |
| `pr edit` | `--pr-number`, `--plan-id` | `--title`, `--slot {name}` | Edit PR title and/or body. Body (if updated) is consumed from the scratch file allocated by `pr prepare-body --for edit`. |

**Worktree-isolated plans**: When invoking from the main checkout against a plan running
in `.claude/worktrees/{plan_id}`, pass `--head {plan_branch}` on every branch-aware
operation (`pr create`, `pr view`, `pr merge`, `pr auto-merge`, `ci status`). The
underlying gh/glab CLIs derive the source branch from cwd HEAD, which would otherwise
resolve to `main`. Examples:

```bash
# Create PR from worktree branch while running from main checkout.
# Step 1: allocate scratch path, Step 2: Write body, Step 3: create.
ci pr prepare-body --plan-id my-plan
# (Write the PR body to the returned path via the Write tool)
ci pr create --title "T" --plan-id my-plan --base main --head plan/jwt-auth

# Inspect that PR by branch (no PR number needed)
ci pr view --head plan/jwt-auth

# Check CI status by branch
ci ci status --head plan/jwt-auth

# Merge by branch
ci pr merge --head plan/jwt-auth --strategy squash --delete-branch

# Enable auto-merge by branch
ci pr auto-merge --head plan/jwt-auth --strategy squash
```

---

## pr — Review Operations

Source: [pr-review-operations.md](pr-review-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `pr reply` | `--pr-number`, `--plan-id` | `--slot {name}` | Post a top-level comment on a PR. Body is consumed from the scratch file allocated by `pr prepare-comment --for reply`. |
| `pr comments` | `--pr-number` | — | Get inline review comments on a PR. **Not** `pr-comments`; **not** `--branch` |
| `pr reviews` | `--pr-number` | — | Get the approval/change-request reviews for a PR |
| `pr thread-reply` | `--pr-number`, `--thread-id` (must be `PRRT_*`), `--plan-id` | `--slot {name}` | Reply inline to an existing review thread. Body is consumed from the scratch file allocated by `pr prepare-comment --for thread-reply`. |
| `pr resolve-thread` | `--pr-number`, `--thread-id` | — | Mark a review thread as resolved (independent of replies) |
| `pr submit-review` | `--pr-number` | — | **GitHub only.** Publish a pending draft review. GitLab returns an explicit error |

---

## ci — CI Status & Logs

Source: [ci-operations.md](ci-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `ci status` | _exactly one of_ `--pr-number` _or_ `--head` | — | Check CI status for a PR. Use `--head {branch}` from the main checkout against a worktree branch |
| `ci wait` | `--pr-number` | — | Poll CI until completion. Use Bash timeout ≥ 1800000 ms (30 min safety net) |
| `ci rerun` | `--run-id` | — | Rerun a failed CI workflow run |
| `ci logs` | `--run-id` | — | Get logs from a CI workflow run |

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
| `issue view` | `--issue` | — | View issue details |
| `issue close` | `--issue` | — | Close an issue |

---

## Common Anti-Patterns

These specific mistakes have been observed when transferring `gh`/`glab` flag names from memory:

| Wrong | Right | Why |
|-------|-------|-----|
| `ci pr-comments --branch X` | `ci pr comments --pr-number 123` | `pr-comments` is not a subcommand; `comments` lives under `pr`, and PR scoping is via `--pr-number` |
| `ci ci status --branch X` | `ci ci status --head X` _or_ `ci ci status --pr-number 123` | The branch flag is `--head`, **not** `--branch` |
| `ci pr merge --merge-method squash` | `ci pr merge --pr-number 123 --strategy squash` | Flag is `--strategy`, not `--merge-method` |

When in doubt, load the relevant group standards file (`pr-operations.md`, `pr-review-operations.md`, `ci-operations.md`, `issue-operations.md`) for full examples and result schemas.
