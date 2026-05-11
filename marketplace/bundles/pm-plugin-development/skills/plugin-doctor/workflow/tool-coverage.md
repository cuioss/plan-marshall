---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Tool Coverage Workflow

Semantic analysis of tool declarations vs actual usage in a single marketplace component. Dispatched under the `cross.plugin-doctor` role key with `scope=tool-coverage`.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `file_path` | Yes | Path to component file (agent, command, or skill SKILL.md). |
| `declared_tools[]` | Yes | List of tools from the component's frontmatter. May be empty `[]` when the file declares no `tools:` field. |
| `component_type` | Yes | One of `agent`, `command`, `skill`. |
| `plan_id` | Yes | Plan identifier (sentinel `none` for free-standing analysis runs). |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |

## Workflow

### Step 1: Read the component

Read the file at `{file_path}` via the `Read` tool. For skills with sub-documents (`references/`, `standards/`), also `Grep` the skill directory for tool-invocation patterns across the whole tree — coverage analysis must include the standards/references the SKILL.md cross-references.

### Step 2: Identify actual tool invocations

Pattern table — these are the canonical invocation signals to recognise:

| Tool | Invocation patterns |
|------|---------------------|
| Read | `Read:`, `Read tool`, `using Read` |
| Write | `Write:`, `Write tool`, `using Write` |
| Edit | `Edit:`, `Edit tool`, `using Edit` |
| Glob | `Glob:`, `Glob tool`, `Glob pattern` |
| Grep | `Grep:`, `Grep tool`, `search with Grep` |
| Bash | `Bash:`, `Bash command`, `execute via Bash` |
| Task | `Task:`, `Task tool`, `spawn.*agent`, `subagent_type` |
| Skill | `Skill:`, `Skill tool`, `load.*skill`, `activate.*skill` |
| SlashCommand | `SlashCommand:`, `SlashCommand(`, `run.*command` |
| WebFetch | `WebFetch:`, `WebFetch tool`, `fetch.*url` |
| WebSearch | `WebSearch:`, `WebSearch tool`, `search.*web` |
| AskUserQuestion | `AskUserQuestion:`, `prompt.*user`, `ask.*user` |
| TodoWrite | `TodoWrite:`, `update.*todo`, `track.*progress` |

### Step 3: Distinguish usage from documentation

- **Actual usage**: instructions to USE the tool (e.g., "Use Read tool to…").
- **Documentation**: describing what tools exist (e.g., "The Task tool is for…").
- **Examples**: showing usage in code blocks as reference.
- **Negative instructions**: "NEVER use Task" is NOT usage.

This is the LLM-judgement core — pattern matching alone produces false positives; the workflow needs context-aware classification.

### Step 4: Apply Rule 6 for agents

If `component_type == "agent"`, the `Task` tool MUST NEVER be reported as missing or suggested — agents cannot dispatch `Task:` at runtime. Canonical definition: [`pm-plugin-development:plugin-create/references/agent-guide.md`](../../plugin-create/references/agent-guide.md) § "Rule 6: Agents CANNOT Use Task Tool".

## Output

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
file_path: "{path}"
component_type: "{type}"

declared_tools[N]:
  - Read
  - Write

used_tools[N]:
  - Read

analysis:
  missing_tools[N]:
    - Skill
  unused_tools[N]:
    - Write
  false_positives[N]{tool,reason}:
    Task,"Mentioned in Rule 6 documentation, not actual usage"

confidence: "high" | "medium" | "low"
notes: "{optional clarification}"
```

## Rules

- **Semantic understanding required** — don't pattern-match without context.
- **Rule 6 enforcement** — never suggest `Task` as missing for agents.
- **Conservative on missing** — only flag a tool as missing when it is clearly invoked in the component's prose / code.
- **Document false positives** — when a tool name appears in the file but is not actual usage, list it in `false_positives` with the reason.
