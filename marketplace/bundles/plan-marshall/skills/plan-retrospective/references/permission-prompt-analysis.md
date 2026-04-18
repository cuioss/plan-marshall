# Aspect: Permission Prompt Analysis

Diagnose permission prompts encountered during the plan by analyzing screenshots, descriptions, chat history, and permission configurations to identify source components and fix paths. Content absorbed from the original `pm-plugin-development/commands/tools-analyze-user-prompted.md` command.

**Conditional**: only meaningful when a `--session-id` is present OR the plan's chat-history analysis surfaced one or more `permission_prompts` entries.

## Inputs

- Session transcript (when `--session-id` provided) — visible prompt screenshots and user reactions.
- Chat-history aspect fragment — pre-identified prompts.
- `~/.claude/settings.json` (global) and `.claude/settings.local.json` (project) — permissions allow/deny/ask lists.
- Active component at prompt time — skill/agent/command markdown.

## Workflow (LLM)

### Step 1: Gather prompt data

For each prompt detected:
- Tool name (Bash, Read, Write, Edit, etc.).
- Operation and target path/resource.
- Visible message from the prompt.
- Active component when the prompt fired.

### Step 2: Load permission configuration

Read both settings files. Extract `permissions.allow`, `permissions.deny`, `permissions.ask`, and `defaultMode`.

### Step 3: Identify the prompted tool

Match the tool call against every pattern in `allow`, `deny`, and `ask`. Record which list (if any) it falls into.

### Step 4: Trace the source component

| Active element | File to read |
|----------------|--------------|
| agent | `{bundle}/agents/{agent-name}.md` — check `allowed-tools` |
| command | `{bundle}/commands/{command-name}.md` — inspect workflow and Task delegation |
| skill | `{bundle}/skills/{skill-name}/SKILL.md` — check `allowed-tools` and workflow |

Locate the exact line where the prompted tool is invoked.

### Step 5: Root-cause classification

| Category | Description |
|----------|-------------|
| **Missing Permission** | No pattern in allow covers the tool call |
| **Wildcarded Path** | Pattern is too narrow (e.g., static path where dynamic path is used) |
| **Agent Tool Declaration** | Agent uses a tool not in its `allowed-tools` |
| **Skill Tool Declaration** | Skill uses a tool not in its `allowed-tools` |
| **Dynamic Path** | Permission uses literal path where runtime path varies |
| **Subagent Inheritance** | Parent agent has permission; subagent does not |

## TOON Fragment Shape

```toon
aspect: permission_prompt_analysis
status: success
plan_id: {plan_id}
prompts[*]{tool,resource,category,source_component,source_file,line,proposal}:
  Bash,"python3 .../manage-files.py add --plan-id X",missing_permission,plan-marshall:phase-4-plan,...,42,"add Bash(python3 .plan/execute-script.py *) to project permissions"
findings[*]{severity,message}:
  warning,"2 permission prompts — project permissions need widening"
```

## Fix Options (prioritized)

Present 1-4 solutions per prompt, concrete snippets:
1. **Add project permission** — new pattern in `.claude/settings.local.json permissions.allow` (preferred — narrowest scope).
2. **Update component declaration** — add missing tool to `allowed-tools`.
3. **Modify workflow** — rewrite step to use an already-permitted tool.
4. **Add global permission** — new pattern in `~/.claude/settings.json permissions.allow` (only when the tool is universally needed).

## LLM Interpretation Rules

- Never propose `Bash(*)` or equivalent overly broad permission.
- Prefer project-local permissions.
- Each prompt becomes a finding with severity `warning` (the plan completed despite the prompt).

## Finding Shape

```toon
aspect: permission_prompt_analysis
severity: warning
category: {category}
tool: {tool}
source_file: {path}
message: "{one-line}"
```

## Out of Scope

- Applying fixes — this aspect surfaces findings; permission-fix skill applies them.
- Security audit of broad permissions — belongs to a separate audit workflow.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-permission-prompt-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect permission-prompt-analysis --fragment-file work/fragment-permission-prompt-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
