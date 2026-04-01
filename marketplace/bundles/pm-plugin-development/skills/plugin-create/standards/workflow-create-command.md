# Workflow: create-command

**Parameters**:
- `scope` - Where to create (marketplace/global/project, default: marketplace)
- `bundle` - Target bundle (optional, will prompt if not provided)

**Steps**:

## Step 1: Load Foundation Skills

```
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:dev-general-practices
```

These provide architecture principles and non-prompting tool usage patterns.

## Step 2: Load Command Standards

```
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

```
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

Same pattern as agent workflow, using Glob/Grep to find similar commands.

## Step 5: Generate Command File

**Generate frontmatter:**
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type "command" --config "{answers_json}"
```

**Load template:**
```
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
```
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

```
SlashCommand: /pm-plugin-development:plugin-doctor commands command-name={command-name}
```
