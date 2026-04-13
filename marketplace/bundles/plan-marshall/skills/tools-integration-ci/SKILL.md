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

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:{script} {command} {args}`
- Provider routing is config-driven; do not hard-code provider names

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
| `standards/health-setup.md` | Detecting provider, verifying tools, persisting config |
| `standards/pr-operations.md` | Creating, viewing, merging, or managing PRs |
| `standards/pr-review-operations.md` | Replying to reviews, resolving threads, checking approvals |
| `standards/ci-operations.md` | Checking CI status, waiting for CI, rerunning, getting logs |
| `standards/issue-operations.md` | Creating, viewing, or closing issues |
| `standards/architecture.md` | Understanding static routing and skill boundaries |
| `standards/api-contract.md` | Understanding shared TOON output formats |

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
