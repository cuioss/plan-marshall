# Aspect: Permission Prompt Analysis

Diagnose permission prompts encountered during the plan by analyzing screenshots, descriptions, chat history, and permission configurations to identify source components and fix paths. Content absorbed from the original `pm-plugin-development/commands/tools-analyze-user-prompted.md` command.

**Conditional**: only meaningful when a `--session-id` is present OR the plan's chat-history analysis surfaced one or more `permission_prompts` entries.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `collect-fragments` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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
- **Severity floor**: a permission prompt is an observed event, not an inference. Every prompt-derived finding MUST carry at minimum `severity: warning` with `confidence: high`. Elevate to `severity: error` when the user explicitly interrupted the call (e.g., chose "No" / cancelled the prompt) — that signals a workflow break, not a tolerated nag. Never downgrade to `medium` / `low`; doing so causes finalize-step's auto-record filter to drop the finding, which is how the `session_id`-resolver gap slipped through without a recorded lesson (see lesson `2026-04-24-15-001`).
- Rationale: prompts are objective state. The retrospective sees the screenshot or chat entry directly; there is no inference chain whose confidence could reasonably be below high. Calibration is not a modulation dial here — it is a floor.

## Finding Shape

```toon
aspect: permission_prompt_analysis
severity: {warning|error}
confidence: high
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
