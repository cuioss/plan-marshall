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
| `pr view` | _(none — uses current branch)_ | — | Get PR/MR details for the current branch |
| `pr list` | _(none)_ | `--head {branch}`, `--state {open\|closed\|all}` | List PRs with optional branch and state filters |
| `pr create` | `--title`, `--body-file`, `--base` | — | Create a PR. **Never** pass markdown through `--body`; always use `--body-file` |
| `pr merge` | `--pr-number` | `--strategy {merge\|squash\|rebase}`, `--delete-branch` | Merge a PR. Flag is `--strategy`, **not** `--merge-method` |
| `pr auto-merge` | `--pr-number` | `--strategy {merge\|squash\|rebase}` | Enable auto-merge when all checks pass |
| `pr close` | `--pr-number` | — | Close a PR without merging |
| `pr ready` | `--pr-number` | — | Mark a draft PR as ready for review |
| `pr edit` | `--pr-number` | `--title`, `--body` | Edit PR title and/or body |

---

## pr — Review Operations

Source: [pr-review-operations.md](pr-review-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `pr reply` | `--pr-number`, `--body` | — | Post a top-level comment on a PR (not attached to a code line) |
| `pr comments` | `--pr-number` | — | Get inline review comments on a PR. **Not** `pr-comments`; **not** `--branch` |
| `pr reviews` | `--pr-number` | — | Get the approval/change-request reviews for a PR |
| `pr thread-reply` | `--pr-number`, `--thread-id` (must be `PRRT_*`), `--body` | — | Reply inline to an existing review thread. Passing a `PRRC_*` review-comment id fails loudly |
| `pr resolve-thread` | `--pr-number`, `--thread-id` | — | Mark a review thread as resolved (independent of replies) |
| `pr submit-review` | `--pr-number` | — | **GitHub only.** Publish a pending draft review. GitLab returns an explicit error |

---

## ci — CI Status & Logs

Source: [ci-operations.md](ci-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `ci status` | `--pr-number` | — | Check CI status for a PR. **Not** `--branch` |
| `ci wait` | `--pr-number` | — | Poll CI until completion. Use Bash timeout ≥ 1800000 ms (30 min safety net) |
| `ci rerun` | `--run-id` | — | Rerun a failed CI workflow run |
| `ci logs` | `--run-id` | — | Get logs from a CI workflow run |

---

## issue — Issue Operations

Source: [issue-operations.md](issue-operations.md)

| Subcommand | Required Flags | Optional Flags | Purpose |
|------------|----------------|----------------|---------|
| `issue create` | `--title`, `--body` | — | Create an issue |
| `issue view` | `--issue` | — | View issue details |
| `issue close` | `--issue` | — | Close an issue |

---

## Common Anti-Patterns

These specific mistakes have been observed when transferring `gh`/`glab` flag names from memory:

| Wrong | Right | Why |
|-------|-------|-----|
| `ci pr-comments --branch X` | `ci pr comments --pr-number 123` | `pr-comments` is not a subcommand; `comments` lives under `pr`, and PR scoping is via `--pr-number` |
| `ci ci status --branch X` | `ci ci status --pr-number 123` | `ci status` requires `--pr-number`; `--branch` is not accepted |
| `ci pr merge --merge-method squash` | `ci pr merge --pr-number 123 --strategy squash` | Flag is `--strategy`, not `--merge-method` |

When in doubt, load the relevant group standards file (`pr-operations.md`, `pr-review-operations.md`, `ci-operations.md`, `issue-operations.md`) for full examples and result schemas.
