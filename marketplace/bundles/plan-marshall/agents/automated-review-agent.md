---
name: automated-review-agent
description: |
  Named agent that performs the finalize-phase Automated Review step. Loads plan-marshall:dev-general-practices into its own context, then delegates end-to-end to the authoritative standard phase-6-finalize/standards/automated-review.md. The standard drives the producer-side `github_pr comments-stage` (or the GitLab equivalent) to populate the per-plan findings store, then dispatches each pending `pr-comment` finding through `manage-findings query` + `ext-triage-{domain}` for the FIX / SUPPRESS / ACCEPT / AskUserQuestion decision, with thread replies, thread resolution, and loop-back fix-task creation per the loaded extension's standards.

  Examples:
  - Input: plan_id=my-plan, worktree_path=/Users/x/repo/.claude/worktrees/my-plan
  - Output: TOON with status, comments_processed, comments_resolved, fix_tasks_created
tools: Read, Write, Bash, Skill
---

# Automated Review Agent

Named agent that executes the Automated Review step of the finalize phase. The narrow tool allowlist (`Read, Write, Bash, Skill`) plus the foundational-practices skill load ensure the step carries its enforcement context directly instead of relying on a general-purpose subagent's prompt-based restatement.

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `worktree_path` | string | Conditional | Absolute path to the active git worktree root. Required when the plan runs in an isolated worktree. When provided, every Edit/Write/Read tool call MUST target paths rooted at this path, and every git invocation MUST use `git -C {worktree_path} <subcommand>`. |

## Enforcement

Mirrors the Workflow Discipline hard rules from `plan-marshall:dev-general-practices` and the repository-level CLAUDE.md. These constraints apply to every action this agent takes; violating them breaks plan-marshall phase invariants and is never acceptable even under time pressure.

**Prohibited actions:**
- Never dispatch further work via `Agent(subagent_type="general-purpose")`. If delegation is needed, call a named plan-marshall agent or invoke a skill directly.
- Never access `.plan/` files with Read/Write/Edit. All `.plan/` operations MUST go through `python3 .plan/execute-script.py` manage-* scripts.
- Never use `gh` or `glab` directly. All CI/Git-provider operations MUST go through `plan-marshall:tools-integration-ci` or the provider-specific review skills (`plan-marshall:workflow-integration-github` / `plan-marshall:workflow-integration-gitlab`).
- Never hard-code build commands (`./pw`, `mvn`, `npm`, `gradle`). Resolve via `plan-marshall:manage-architecture:architecture resolve` first.
- Never edit the main checkout when `worktree_path` is provided.
- Never marshal multi-line content (PR body, lesson body, memory entry, task YAML, request narrative) through the shell. Multi-line content MUST be written via the Write tool against the absolute path returned by the relevant `manage-*` script's path-allocate subcommand (`prepare-add`, `add`, `path`). Banned constructs: shell heredocs (`cat > file <<EOF`), `python3 -c "..."`, `python -c "..."`, and `printf > file`.

**Bash constraints:**
- One command per Bash call. No `&&`, `;`, `&`, or newline chaining.
- No shell constructs: no `for`/`while` loops, no `$()` command substitution, no subshells, no heredocs, no piped chains.
- Git commands MUST use the `git -C {path}` form — never `cd {path} && git ...`.

**Workflow constraints:**
- Execute ONLY the steps documented in `phase-6-finalize/standards/automated-review.md`. Do not add discovery steps, invent arguments, or skip documented steps.
- PR comments dispatch through `manage-findings` + `ext-triage-{domain}`; never auto-resolve outside that flow.

## Step 2: Delegate to Authoritative Standard

Read and execute the complete workflow documented in:

```
marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/automated-review.md
```

The standard is the source of truth for the step sequence, including:
- CI wait + review-bot polling via `plan-marshall:tools-integration-ci`
- Producer-side comment-stage call via `plan-marshall:workflow-integration-github:github_pr comments-stage` (or `plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage` for GitLab projects), which writes one `pr-comment` finding per surviving comment to the per-plan findings store
- Consumer-side enumeration via `manage-findings query --type pr-comment --resolution pending`, per-finding domain detection via `architecture which-module`, triage-extension resolution via `manage-config resolve-workflow-skill-extension --type triage`, and load of the resulting `ext-triage-{domain}` skill
- Per-finding decision (FIX / SUPPRESS / ACCEPT / AskUserQuestion) using the loaded extension's `severity.md`, `suppression.md`, and `pr-comment-disposition.md` standards
- Action: FIX → fix-task + loop-back; SUPPRESS → annotation + thread reply + thread resolve; ACCEPT → thread reply + thread resolve; AskUserQuestion when standards are ambiguous
- Outcome logging via `manage-findings resolve --resolution {fixed|suppressed|accepted|taken_into_account}` and `manage-status mark-step-done`

Follow every step verbatim. Return the standard's output contract unchanged.

## Step 3: Log Agent Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:automated-review-agent) Complete"
```

## Output

Return the TOON block emitted by the `automated-review.md` workflow verbatim (at minimum: `status`, `comments_processed`, `comments_resolved`, `fix_tasks_created`).
