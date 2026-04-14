---
name: tools-analyze-user-prompted
description: |
  Analyze permission prompts to identify source and provide solutions.
  Input: optional screenshot path, optional description text.
  Output: Permission prompt analysis report with root cause, source component, and fix solutions.
tools: Read, Edit, Bash, Skill, AskUserQuestion
---

# Analyze User Prompted Command

Diagnoses permission prompts by analyzing screenshots, descriptions, chat history, and permission configurations to identify the source component and provide actionable solutions.

## Parameters

- `screenshot` — Path to a screenshot of the prompt (optional).
- `description` — Free-form context about what happened before the prompt (optional).

At least one parameter should be provided for a meaningful analysis.

## Workflow

### Step 1 — Gather Input

Read the screenshot (if provided) and extract the prompted tool name, the operation, the target path/resource, and any visible message. Parse the `description` for the command or agent in play. Review the recent conversation for the last command invoked, the active agent, and recent tool calls.

### Step 2 — Load Permission Configuration

Read both `~/.claude/settings.json` (global) and `.claude/settings.local.json` (project). Extract `permissions.allow`, `permissions.deny`, `permissions.ask`, and `defaultMode`.

### Step 3 — Identify the Prompted Tool

From the screenshot, recover the exact tool name and argument string. Match it against every pattern in `allow`, `deny`, and `ask`. Record which list (if any) the tool falls into and note whether it defaults to ask.

### Step 4 — Trace Source Component

Depending on which element was active when the prompt fired, read the corresponding file:

- An agent → `{bundle}/agents/{agent-name}.md` (check `allowed-tools` in frontmatter).
- A command → `{bundle}/commands/{command-name}.md` (inspect workflow steps and any Task-tool delegation).
- A skill → `{bundle}/skills/{skill-name}/SKILL.md` (check `allowed-tools` and workflow tool usage).

Locate the exact line where the prompted tool is invoked.

### Step 5 — Root Cause Analysis

Categorize the root cause as one of: **Missing Permission**, **Wildcarded Path** (pattern too narrow), **Agent Tool Declaration** (agent uses tool not in its `allowed-tools`), **Skill Tool Declaration** (skill uses tool not in its `allowed-tools`), **Dynamic Path** (static pattern vs dynamic path), or **Subagent Inheritance**. Record the source file, line number, exact offending tool call, and the reason the permission was not granted.

### Step 6 — Report

Display a structured analysis report containing: what happened (tool, operation, resource), source component (type, name, bundle, file, line number, 3–5 surrounding source lines), root cause (category and explanation), and permission state (global/project allow patterns checked, whether any matched, and the pattern that should match).

### Step 7 — Propose Solutions

Present 1–4 solutions based on the root cause, each with a concrete code/config snippet:

1. **Add global permission** — new pattern in `~/.claude/settings.json permissions.allow`.
2. **Add project permission** — new pattern in `.claude/settings.local.json permissions.allow`.
3. **Update component declaration** — add the missing tool to the component's `allowed-tools`.
4. **Modify workflow** — rewrite the step to use an already-permitted tool.

### Step 8 — Interactive Resolution

Use `AskUserQuestion` to present the solutions (`Add global permission`, `Add project permission`, `Update component declaration`, `Manual — show details only`). When the user picks an action that is not "Manual", apply the fix with `Edit` and verify it.

## Critical Rules

- **Analysis accuracy**: always read the actual permission files; never assume. Trace the exact source file and line number. Consider both global and project permissions.
- **Solution safety**: never suggest overly broad permissions (e.g. `Bash(*)`). Prefer project-local permissions when a broader scope is not needed. Explain security implications for each proposal.
- **Screenshot handling**: read screenshots through the `Read` tool, extract all visible text and context, and fail gracefully on missing or unreadable screenshots.
- **Chat history**: only analyze recent, relevant context; do not expose unrelated conversation details.

## Sample: Shell Metacharacter Permission Issue

An agent executed `manage-task add` with `--verification-commands "grep -l '\`\`\`json' *.md | wc -l"` and was prompted because shell metacharacters (pipes, wildcards, escaped quotes) triggered security checks despite the `Bash(python3 .plan/execute-script.py *)` permission. The fix refactored `manage-task add` to accept complex task definitions via a stdin-based API, bypassing shell interpretation entirely.

## Usage Examples

```
/pm-plugin-development:tools-analyze-user-prompted screenshot=/tmp/prompt.png
/pm-plugin-development:tools-analyze-user-prompted description="Got prompted when running /plugin-doctor"
/pm-plugin-development:tools-analyze-user-prompted screenshot=/tmp/prompt.png description="Was running maven build"
/pm-plugin-development:tools-analyze-user-prompted
```

## Continuous Improvement Rule

If you discover issues or improvements during execution, activate `Skill: plan-marshall:manage-lessons` and record a lesson for the `{type: "command", name: "tools-analyze-user-prompted", bundle: "pm-plugin-development"}` component with a category (bug | improvement | pattern | anti-pattern), summary, and detail.

## Related

- `/plan-marshall:workflow-permission-web` — Manage WebFetch domain permissions
- `plan-marshall:tools-script-executor` — Script execution permission patterns
- `pm-plugin-development:plugin-architecture` — Component tool declarations
