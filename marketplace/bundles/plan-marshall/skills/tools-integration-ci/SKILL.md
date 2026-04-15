---
name: tools-integration-ci
description: CI provider abstraction with unified API for GitHub and GitLab operations (PR, issues, CI status)
user-invocable: false
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
- PR operations (create, view, merge, auto-merge, close, ready, edit)
- PR review operations (comments, reply, resolve-thread, thread-reply, reviews)
- CI status, wait, rerun, and logs
- Issue operations (create, view, close)
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

```
marshal.json                          Scripts
ci.commands.pr-create ─────────────► github.py pr create
ci.commands.ci-status ─────────────► github.py ci status
```

**Load Reference**: For full architecture details:
```
Read standards/architecture.md
```

---

## Skill Structure

```
tools-integration-ci/
├── SKILL.md                     # This file (API index)
├── standards/
│   ├── architecture.md          # Static routing, skill boundaries
│   ├── api-contract.md          # Shared TOON output formats
│   ├── github-impl.md           # GitHub-specific: gh CLI
│   ├── gitlab-impl.md           # GitLab-specific: glab CLI
│   ├── health-setup.md          # Provider detection, verification, config persistence
│   ├── pr-operations.md         # PR create, view, merge, auto-merge, close, ready, edit
│   ├── pr-review-operations.md  # PR comments, reply, resolve-thread, thread-reply, reviews
│   ├── ci-operations.md         # CI status, wait, rerun, logs
│   └── issue-operations.md      # Issue create, view, close
└── scripts/
    ├── ci_health.py             # Detection & verification
    ├── ci.py                    # Provider-agnostic router
    ├── github.py                # GitHub operations via gh
    └── gitlab.py                # GitLab operations via glab
```

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | Provider detection & verification |
| ci | `plan-marshall:tools-integration-ci:ci` | Provider-agnostic router |
| github | `plan-marshall:tools-integration-ci:github` | GitHub operations via gh CLI |
| gitlab | `plan-marshall:tools-integration-ci:gitlab` | GitLab operations via glab CLI |

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

## Worktree-Aware Invocation (`--project-dir`)

Every `ci` leaf subcommand accepts an optional top-level `--project-dir PATH`
flag placed **before** the command/subcommand pair. When supplied, every
underlying `gh`/`glab` subprocess runs with `cwd=PATH`, so branch-aware
operations (`pr view`, `ci status`, `pr create`, `pr merge`, …) resolve HEAD
against the specified checkout instead of the Python process cwd.

```bash
# Run from the main checkout, but target a worktree-isolated plan branch:
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --project-dir /repo/.claude/worktrees/my-plan \
  pr view --head my-plan-branch
```

**Semantics:**

- The flag is consumed by the `ci.py` router before the provider script is
  dispatched — provider scripts (github_ops, gitlab_ops) see their normal
  argument vector and behave unchanged.
- Under the hood the router calls `ci_base.set_default_cwd(PATH)`, and every
  `run_cli` invocation threads that value into `subprocess.run(cwd=…)`.
- When the flag is **omitted** behaviour is identical to before: subprocesses
  inherit the Python process cwd.
- Place the flag before the `pr` / `ci` / `issue` command word. Placing it
  after will cause the provider parser to reject it as an unknown argument.

Required when invoking CI operations from a checkout whose HEAD is not the
branch you want to operate on — most notably during `phase-6-finalize` when
the main agent runs in the main checkout but the plan branch lives in
`.claude/worktrees/{plan_id}`.

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

## References

- `standards/architecture.md` - Static routing and skill boundaries
- `standards/api-contract.md` - Shared TOON output formats
- `standards/github-impl.md` - GitHub-specific implementation
- `standards/gitlab-impl.md` - GitLab-specific implementation
