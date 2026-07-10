---
name: tools-integration-ci
description: CI provider abstraction with unified API for GitHub and GitLab operations (PR, issues, CI status)
user-invocable: false
mode: script-executor
---

# Tools Integration CI Skill

Unified CI provider abstraction using **static routing** - one script per provider, config stores full commands.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not call `gh` or `glab` directly; all CI operations go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass provider detection logic
- Do not transfer `gh`/`glab` flag names from memory when invoking `ci` leaf subcommands — flag names diverge from the underlying tools (e.g., `ci pr merge` uses `--strategy`, not `--merge-method`)

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:{script} {command} {args}`
- Provider routing is config-driven; do not hard-code provider names
- Before invoking any `ci` leaf subcommand whose exact flags you do not already know, Read [`standards/leaf-command-reference.md`](standards/leaf-command-reference.md) (or the relevant group standard). Never guess

## What This Skill Provides

- Provider detection and health verification
- PR operations (create, view, merge, auto-merge, safe-merge, merge-queue, close, ready, edit)
- PR review operations (comments, wait-for-comments, reply, resolve-thread, thread-reply, reviews)
- CI status, wait, rerun, and logs (with automatic failure-log download + error-extraction filtering)
- Issue operations (create, view, close)
- Repo operations (merge-queue probe/enable — platform merge queue / merge train)
- Unified TOON output format across providers

## Consumers

This skill is a script-only library (not registered in plugin.json). It is consumed by:
- `workflow-integration-github` — GitHub PR review comment workflows
- `workflow-integration-gitlab` — GitLab MR review comment workflows
- `workflow-integration-git` — git commit workflows
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with PR creation

---

## Architecture

**Static Routing Pattern**: Config stores full commands, wizard generates provider-specific paths.

```text
marshal.json                          Scripts
ci.commands.pr-create ─────────────► ci.py pr create ──► {provider}_ops.py
ci.commands.ci-status ─────────────► ci.py checks status ──► {provider}_ops.py
```

`ci.py` is the pure passthrough router; the per-provider handler bodies live in `{provider}_ops.py` (`github_ops.py` / `gitlab_ops.py`) in the `workflow-integration-{github,gitlab}` bundles — there is no `github.py` / `gitlab.py` in this skill's `scripts/`.

**Load Reference**: For full architecture details:
```text
Read standards/architecture.md
```

---

## Skill Structure

```text
tools-integration-ci/
├── SKILL.md                     # This file (API index)
├── standards/
│   ├── architecture.md          # Static routing, skill boundaries
│   ├── api-contract.md          # Shared TOON output formats
│   ├── github-impl.md           # GitHub-specific: gh CLI
│   ├── gitlab-impl.md           # GitLab-specific: glab CLI
│   ├── health-setup.md          # Provider detection, verification, config persistence
│   ├── pr-operations.md         # PR create, view, merge, auto-merge, safe-merge, merge-queue, close, ready, edit
│   ├── pr-review-operations.md  # PR comments, reply, resolve-thread, thread-reply, reviews
│   ├── ci-operations.md         # CI status, wait, rerun, logs
│   └── issue-operations.md      # Issue create, view, close
└── scripts/
    ├── ci_health.py             # Detection & verification
    ├── ci.py                    # Provider-agnostic passthrough router
    ├── ci_base.py               # Shared argparse surface (pr/checks/issue/branch/repo sub-verbs)
    └── _ci_log_filter.py        # Failure-log error-extraction filter
```

Provider handler bodies are NOT in this skill — they live in `github_ops.py` / `gitlab_ops.py` under the `workflow-integration-{github,gitlab}` bundles (GitHub PR-merge handlers are further split into `_github_pr.py`; GitLab defines its `pr` handlers inline in `gitlab_ops.py`).

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | Provider detection & verification |
| ci | `plan-marshall:tools-integration-ci:ci` | Provider-agnostic router |
| github_ops | `plan-marshall:workflow-integration-github:github_ops` | GitHub handler bodies via gh CLI (routed to by `ci.py`) |
| gitlab_ops | `plan-marshall:workflow-integration-gitlab:gitlab_ops` | GitLab handler bodies via glab CLI (routed to by `ci.py`) |

---

## Standards (Load On-Demand)

Load the relevant standard when performing specific operations:

| Standard | When to Load |
|----------|-------------|
| `standards/leaf-command-reference.md` | Before invoking any unfamiliar ci leaf subcommand |
| `standards/health-setup.md` | Detecting provider, verifying tools, persisting config |
| `standards/pr-operations.md` | Creating, viewing, merging, or managing PRs |
| `standards/pr-review-operations.md` | Replying to reviews, resolving threads, checking approvals |
| `standards/ci-operations.md` | Checking CI status, waiting for CI, rerunning, getting logs |
| `standards/issue-operations.md` | Creating, viewing, or closing issues |
| `standards/architecture.md` | Understanding static routing and skill boundaries |
| `standards/api-contract.md` | Understanding shared TOON output formats |

---

## Worktree-Aware Invocation (`--plan-id` / `--project-dir`)

Every `ci` leaf subcommand accepts an optional top-level routing flag
placed **before** the command/subcommand pair. When supplied, every
underlying `gh`/`glab` subprocess runs with `cwd=<resolved_path>`, so
branch-aware operations (`pr view`, `ci status`, `pr create`, `pr merge`,
…) resolve HEAD against the specified checkout instead of the Python
process cwd.

The router implements the canonical two-state contract:

* `--plan-id X` and `--project-dir Y` together — error
  `mutually_exclusive_args`. Pick one.
* `--plan-id X` only — auto-resolve via `manage-status get-worktree-path`.
  When `use_worktree=true` the persisted worktree path is used; when
  `use_worktree=false` (or metadata absent) the main checkout is used.
* `--project-dir Y` only — explicit override (legacy / escape hatch).
* Neither — main checkout via `git rev-parse --show-toplevel`.

```bash
# Preferred: bind the call to a plan's worktree by id.
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id EXAMPLE-PLAN \
  pr view --head EXAMPLE-PLAN-branch

# Escape hatch: bind to an explicit path (test fixtures, ad-hoc).
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --project-dir <worktree_path> \
  pr view --head EXAMPLE-PLAN-branch
```

Both flags are consumed by the `ci.py` router before the provider
script is dispatched; provider scripts behave unchanged. The router
scans the entire argument vector and strips the routing flag before
the provider parser runs.

Required when invoking CI operations from a checkout whose HEAD is not
the branch you want to operate on. See
`workflow-integration-git/standards/worktree-handling.md` for the
worktree-specific application of this rule (path convention, dispatch
protocol, two-state contract reference).

---

## Automatic Failure-Log Download on `checks wait` / `checks status`

When a `checks wait` or `checks status` call observes one or more checks with
`result: failure`, it automatically downloads and filters the failing-job log
for every failing check — no separate user-callable subcommand is involved. The
behavior is built into the existing `checks wait` and `checks status` verbs.

For each failing check, two files are written under the plan-scoped artifact tree
`artifacts/ci-runs/{run_id}/`:

```text
artifacts/ci-runs/{run_id}/{slug}.log           # raw downloaded failing-job log
artifacts/ci-runs/{run_id}/{slug}.filtered.log  # error-extraction filtered variant
```

`{slug}` is the failing check's name slugified — lowercased, with each run of
non-alphanumeric characters collapsed to a single `-` (e.g. check `verify / verify`
→ slug `verify-verify`). A single run can fail multiple checks, each with its own
distinctly-slugged pair of files.

These paths are surfaced **per entry** inside the failure TOON's `failing_checks[]`
array — as the `log_file` and `filtered_log_file` fields of each entry — and are
**never** scalar top-level keys. `failing_checks[]` is the subset of the standard
`checks[]` table whose `result` is `failure`, enriched with the two file paths plus
`run_id` and `error_style`.

### `--error-style` selector

Both `checks wait` and `checks status` accept an optional `--error-style` flag that
governs how the raw log is filtered into its `.filtered.log` variant:

| `--error-style` | Filtering heuristic |
|-----------------|---------------------|
| `maven` | Routes through the Maven build parser; falls back to generic. |
| `gradle` | Routes through the Gradle build parser; falls back to generic. |
| `npm` | Routes through the npm/node build parser; falls back to generic. |
| `generic` | **Default.** Error-context heuristic (`ERROR\|FAIL\|Exception\|Traceback`, case-insensitive) plus surrounding context lines. Used when no style is given or the job's build system is unknown. |

The normative specification for the download/filter behavior, the `failing_checks[]`
transport shape, the slug naming scheme, and multi-failure worked examples lives in
[`standards/api-contract.md`](standards/api-contract.md) (CI Failure Log Download &
Filtering). That document is authoritative; see also
[`standards/ci-operations.md`](standards/ci-operations.md) for the workflow-level
walkthrough.

---

## PR Comment Vocabulary

GitHub and GitLab expose several overlapping concepts for "commenting on a PR".
Use the exact subcommand that matches the intent — they are NOT interchangeable:

| Subcommand | Target | Publishing | Notes |
|------------|--------|------------|-------|
| `pr comment` / `pr reply` | Top-level issue comment on the PR | Immediate | Not attached to any line of code or review thread. |
| `pr thread-reply` | Inline reply on an existing code-review thread | Immediate | Uses `addPullRequestReviewThreadReply` on GitHub and the `/discussions/{id}/notes` endpoint on GitLab. Requires a real thread id (`PRRT_*` on GitHub). Does NOT create or extend a pending review. |
| `pr resolve-thread` | Collapse a review thread | Immediate | Independent of replies — resolving a thread neither posts nor requires a reply. |
| `pr submit-review` | Publish a pending draft review | Immediate | **GitHub-only safety net.** Use when a previous call accidentally queued a reply into a draft `PullRequestReview`. GitLab has no equivalent — discussions are always immediate, so the GitLab handler returns an explicit error. |

**Breaking change note**: `pr thread-reply --thread-id` requires a real review-thread node id (`PRRT_*`). Passing a review-comment id (`PRRC_*`) is no longer supported and will fail loudly — previous behavior silently queued replies into a PENDING draft review.

---

## Error Handling

All operations return TOON error format on failure:

```toon
status: error
operation: pr_create
error: Authentication failed
context: gh auth status returned non-zero
```

Exit codes:
- `0`: Success (stdout)
- `1`: Error (stderr)

---

## Canonical invocations

The canonical argparse surface for `ci.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation". Each top-level subcommand carries nested sub-verbs; the first positional after the notation is the subcommand, the second is the sub-verb.

### pr

Sub-verbs: `view`, `list`, `reply`, `resolve-thread`, `thread-reply`, `reviews`, `comments`, `wait-for-comments`, `merge`, `auto-merge`, `safe-merge`, `merge-queue`, `update-branch`, `close`, `ready`, `submit-review`, `edit`, `prepare-body`, `prepare-comment`, `create`.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --title TITLE --plan-id PLAN_ID [--slot SLOT] [--base BASE] [--draft] [--head HEAD]
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr safe-merge \
  (--pr-number PR_NUMBER | --head HEAD) [--strategy merge|squash|rebase] [--delete-branch] \
  [--admin-merge-on-stuck-state] [--poll-timeout SECONDS] [--poll-interval SECONDS]
```

`pr safe-merge` polls readiness before merging; `--admin-merge-on-stuck-state` (the GitHub-only stuck-state `--admin` fallback) has no effect on GitLab.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
  (--pr-number PR_NUMBER | --head HEAD) [--strategy merge|squash|rebase] [--delete-branch]
```

`pr merge-queue` enqueues the PR into the platform merge queue so the platform re-tests-and-merges against the latest base, serializing a truly-external commit the session-scoped merge mutex cannot. On GitHub it engages the merge queue via `gh pr merge --auto`; on GitLab it performs a real merge-train enqueue via `POST /projects/:id/merge_trains/merge_requests/:iid`. On GitLab the merge train is a Premium/Ultimate-tier feature enabled per-project — when the project/tier does not offer it the handler returns the actionable ineligible error rather than silently falling back to an immediate merge.

### checks

Sub-verbs: `status`, `wait`, `rerun`, `logs`, `wait-for-status-flip`.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status \
  [--pr-number PR_NUMBER] [--head HEAD] [--error-style maven|gradle|npm|generic]
```

`status` and `wait` accept `--error-style` (default `generic`) to select how the
auto-downloaded failure log is filtered when any check fails. See § "Automatic
Failure-Log Download on `checks wait` / `checks status`" above.

### issue

Sub-verbs: `create`, `comment`, `prepare-body`, `prepare-comment`, `view`, `close`, `wait-for-close`, `wait-for-label`.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
  --title TITLE --plan-id PLAN_ID [--labels LABELS] [--slot SLOT]
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue comment \
  --issue ISSUE --plan-id PLAN_ID [--slot SLOT]
```

### branch

Sub-verb: `delete`.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci branch delete \
  --remote-only --branch BRANCH
```

### repo

A `merge-queue` noun grouping two sub-verbs: `probe`, `enable` (the 3-level
`repo merge-queue probe` / `repo merge-queue enable` shape).

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue probe
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue enable
```

`repo merge-queue probe` reports the platform merge-queue eligibility as one of
the shared discriminators — `eligible_configured`, `eligible_unconfigured`,
`ineligible`, or `unsupported`. `repo merge-queue enable` configures the platform
merge queue (GitHub: a `merge_queue` ruleset on the default branch; GitLab: the
per-project `merge_trains_enabled` setting) and is idempotent — an
already-configured repo is left unchanged. Both verbs return the actionable error
(never a stack trace) on an auth-scope failure, and `enable` refuses with the
actionable ineligible message when the platform gates the feature off.

## References

- `standards/architecture.md` - Static routing and skill boundaries
- `standards/api-contract.md` - Shared TOON output formats
- `standards/github-impl.md` - GitHub-specific implementation
- `standards/gitlab-impl.md` - GitLab-specific implementation
