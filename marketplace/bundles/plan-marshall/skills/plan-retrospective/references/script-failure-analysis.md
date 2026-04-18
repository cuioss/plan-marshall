# Aspect: Script Failure Analysis

Analyze script failures from the plan to identify source components, trace how instructions led to the failed call, and propose fixes. Content absorbed from the original `pm-plugin-development:tools-analyze-script-failures` skill.

**Conditional**: only meaningful when `log_analysis.counts.errors_script > 0`.

## Inputs

- `script.log` — complete list of script invocations and outcomes (via `manage-logging read --type script`).
- `work.log` — surrounding `[ERROR]` entries that reference the failed notation.
- Source components referenced in the failed calls (skill/agent/command markdown files).

## Workflow (LLM)

### Step 1: Extract failure details

For each non-zero-exit script call found in `script.log`:
- Complete notation (`{bundle}:{skill}:{script}`).
- Subcommand and argument string.
- Exit code and error message.

### Step 2: Trace origin

Determine the source component type using surrounding `work.log` `[SKILL]`/`[STEP]` entries:

| Source Type | How to Identify |
|-------------|-----------------|
| **Command** | `[SKILL] (command:/{name})` just above the failure |
| **Agent** | `[SKILL] (agent:{name})` just above the failure |
| **Skill** | `[SKILL] (plan-marshall:{skill-name})` just above the failure |

Read the source component file to find the instruction context.

### Step 3: Root cause classification

| Category | Description | Fix Location |
|----------|-------------|--------------|
| **Missing Script Instruction** | Script not documented in component | Add to component |
| **Wrong Script Parameters** | Parameters incorrect or missing | Fix component instruction |
| **LLM Invented Script** | No instruction, LLM guessed script call | Add flow step to component |
| **Missing API** | Operation needed but no script exists | Create new script |
| **Script Bug** | Script exists but has bug | Fix script implementation |
| **Script Not Found** | Notation invalid or script missing | Fix notation or add script |

## TOON Fragment Shape

```toon
aspect: script_failure_analysis
status: success
plan_id: {plan_id}
failures[*]{notation,exit_code,category,source_component,source_file,proposal}:
  "plan-marshall:manage-files:manage-files",2,wrong_parameters,"plan-marshall:phase-4-plan","marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md","fix --file argument name"
findings[*]{severity,message}:
  error,"1 script failure traced to phase-4-plan instruction"
```

## LLM Interpretation Rules

- Every failure MUST be traced to an exact source file; otherwise mark `source_component: unknown` and `category: llm_invented_script`.
- Propose a fix ONLY when the category is one of: `missing_instruction`, `wrong_parameters`, `llm_invented_script`. `script_bug` and `missing_api` require a separate plan.
- Each failure becomes a finding with `severity: error`.

## Finding Shape

```toon
aspect: script_failure_analysis
severity: error
category: {category}
notation: {notation}
source_file: {path}
message: "{one-line}"
```

## Interactive Resolution (user-invocable mode only)

In user-invocable mode, for each failure use `AskUserQuestion`:

```
question: "How would you like to handle {notation} failure?"
options:
  - "Apply fix"      — Edit the source component to add/correct the instruction
  - "Record lesson"  — Allocate a lesson via manage-lessons add (category=bug)
  - "Skip"           — No action
```

In finalize-step mode, always record lessons for `severity: error` failures; never auto-edit components.

## Out of Scope

- Fixing the underlying script bug — the retrospective surfaces the category and proposal only.
- Analyzing non-failed scripts — that is llm-to-script-opportunities.
