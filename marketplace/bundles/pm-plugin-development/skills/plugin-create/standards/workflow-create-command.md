# Workflow: create-command

**Parameters**:
- `scope` - Where to create (marketplace/global/project, default: marketplace)
- `bundle` - Target bundle (optional, will prompt if not provided)

**Steps**:

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `component` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Step 1: Load Foundation Skills

```text
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:persona-plan-marshall-agent
```

These provide architecture principles and non-prompting tool usage patterns.

## Step 2: Load Command Standards

```text
Read references/command-guide.md
```

This provides command design principles, quality standards, and orchestration patterns.

## Step 3: Interactive Questionnaire

Ask user for:

**A. Command name** (kebab-case with verb)
- Validation: Must match kebab-case pattern, should start with verb
- Error if invalid: "Command name must be kebab-case starting with verb (e.g., create-agent)" and retry

**B. Bundle selection** (same as agent workflow)

**C. Description** (one sentence, <100 chars)

**D. Command type** — Present using `AskUserQuestion`:

```text
AskUserQuestion:
  questions:
    - question: "What type of command is this?"
      header: "Type"
      options:
        - label: "Orchestration"
          description: "Coordinates agents/commands"
        - label: "Diagnostic"
          description: "Analyzes and reports"
        - label: "Interactive"
          description: "User questionnaire"
        - label: "Automation"
          description: "Executes workflow"
      multiSelect: false
```

**E. Parameters** (what parameters command accepts)
- Can be empty for commands with no parameters
- Prompt: "List parameters (comma-separated) or press Enter if none"

**F. Workflow steps** (main steps command performs)
- Validation: Must provide at least 2 steps
- Error if <2: "Command requires at least 2 workflow steps" and retry

**G. Tool requirements** (which tools needed)
- Validation: Must list at least one tool OR "none" for orchestration-only
- Error if empty: "Specify tools needed or 'none' for orchestration-only" and retry

Track `questions_answered` counter.

## Step 4: Duplication Detection

Same pattern as agent workflow: prefer `architecture files --module {bundle}` for module-scoped enumeration of registered components; fall back to Glob/Grep for sub-component discovery and content-level name/description matching.

## Step 5: Generate Command File

**Generate frontmatter:**
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type "command" --config "{answers_json}"
```

**Load template:**
```text
Read assets/templates/command-template.md
```

**Fill template** with:
- Generated frontmatter (name, description only - no tools)
- Command overview
- CONTINUOUS IMPROVEMENT RULE with command-specific improvements
- PARAMETERS section (if applicable)
- WORKFLOW section (numbered steps)
- RULES section
- USAGE EXAMPLES section
- RELATED section

**CONTINUOUS IMPROVEMENT RULE for commands:**
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "{command-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

**Write file:**
```text
Write: {bundle}/commands/{command-name}.md
```

Track `files_created` counter.

## Step 6: Validate Generated Component

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component validate --file "{file_path}" --type "command"
```

Validation checks:
- Frontmatter format correct
- All required sections present (WORKFLOW, USAGE EXAMPLES)
- CONTINUOUS IMPROVEMENT RULE uses manage-lessons skill pattern

## Step 7: Display Summary

Same format as agent workflow.

## Step 8: Run Command Diagnosis

```text
SlashCommand: /pm-plugin-development:plugin-doctor commands command-name={command-name}
```
