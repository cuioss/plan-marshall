# Workflow: create-agent

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

## Step 2: Load Architecture Standards

```
Read references/agent-guide.md
```

This provides agent design principles, tool selection guidelines, and architecture rules.

## Step 3: Interactive Questionnaire

Ask user for:

**A. Agent name** (kebab-case validation)
- Validation: Must match kebab-case pattern
- Error if invalid: "Agent name must be kebab-case (lowercase-with-hyphens)" and retry

**B. Bundle selection**
- List available bundles using Glob
- Validation: Must select valid bundle from list
- Error if invalid: "Please select a bundle from the list" and retry

**C. Description** (one sentence, <100 chars)
- Validation: Must not be empty, ≤100 chars
- Error if invalid: "Description required (max 100 chars): {current_length}/100" and retry

**D. Agent type** — Present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What type of agent is this?"
      header: "Type"
      options:
        - label: "Analysis agent"
          description: "Code review, diagnostics"
        - label: "Execution agent"
          description: "Build, test, deploy"
        - label: "Coordination agent"
          description: "Multi-step workflows"
        - label: "Research agent"
          description: "Information gathering"
      multiSelect: false
```

**E. Detailed capabilities** (what agent does)
- Validation: Must not be empty
- Error if empty: "Agent capabilities description required" and retry

**F. Required tools** (which tools agent needs)
- Examples: Read, Write, Edit, Glob, Grep, Bash, WebFetch
- Validation: Must list at least one tool
- Error if none: "At least one tool required" and retry
- **Task Tool validation**:
  - If user lists `Task`: Error — "Agents cannot use Task tool (Rule 6) — unavailable at runtime. Create a command instead if delegation needed."
  - Force removal from list or abort
- **Maven Execution validation**:
  - If user lists `Bash` AND agent name is not "maven-builder":
  - Prompt: "Does this agent need to execute Maven commands?"
  - If yes: Error — "Only maven-builder agent may execute Maven (Rule 7)"
  - If no: Continue

**G. When should agent be used** (trigger conditions)
- Validation: Must provide use cases
- Error if empty: "Usage conditions required" and retry

**H. Expected inputs/outputs**
- Validation: Must describe inputs and outputs
- Error if empty: "Input/output description required" and retry

Track `questions_answered` counter.

## Step 4: Duplication Detection and Architecture Validation

**Check for duplicates:**
1. Prefer `architecture files --module {bundle}` to enumerate the bundle's registered components when the marketplace's architecture inventory covers it; fall back to Glob for sub-component discovery (agents are component-level files inside the bundle, finer-grained than module-scoped queries).
2. Use Grep as the documented fallback to search agent file contents for similar names/descriptions (content search inside the discovered files).
3. If duplicates found:
   - Display: "Similar agents found: {list with descriptions}"
   - Present using `AskUserQuestion`:
     ```
     AskUserQuestion:
       questions:
         - question: "Similar agents already exist. How would you like to proceed?"
           header: "Duplicate"
           options:
             - label: "Continue anyway"
               description: "Create the agent despite similarities"
             - label: "Rename agent"
               description: "Go back and choose a different name"
             - label: "Abort creation"
               description: "Cancel agent creation"
           multiSelect: false
     ```
   - If rename: Return to Step 2A
   - If abort: Exit workflow
   - Track in `duplication_checks` counter

**Validate architecture compliance:**
- Self-contained (no cross-agent dependencies)
- Proper tool fit (agent needs listed tools)
- No prohibited tools (Task, Maven for non-maven-builder)

Track `validations_performed` counter.

## Step 5: Generate Agent File

**Generate frontmatter:**
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type "agent" --config "{answers_json}"
```

Where answers_json contains:
```json
{
  "name": "agent-name",
  "description": "One sentence description",
  "model": "optional_model_name",
  "tools": ["Tool1", "Tool2", "Tool3"]
}
```

**Load template:**
```
Read assets/templates/agent-template.md
```

**Fill template** with:
- Generated frontmatter
- Agent name (title case for heading)
- Purpose statement from capabilities
- Workflow steps (numbered, based on agent type)
- Tool usage guidance
- Critical rules (based on selected tools)
- CONTINUOUS IMPROVEMENT RULE with 3-5 improvement areas specific to agent type

**Continuous Improvement Rule pattern**:
Agent template uses this pattern:
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "{agent-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

**Write file:**
```
Write: {bundle}/agents/{agent-name}.md
```

Track `files_created` counter.

## Step 6: Validate Generated Component

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component validate --file "{file_path}" --type "agent"
```

Validation checks:
- Frontmatter format correct (comma-separated tools)
- No Task tool present
- CONTINUOUS IMPROVEMENT RULE uses manage-lessons skill pattern
- All required sections present

If validation fails: Display errors and present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Validation failed. How would you like to proceed?"
      header: "Validate"
      options:
        - label: "Retry generation"
          description: "Regenerate the component and validate again"
        - label: "Abort"
          description: "Cancel component creation"
      multiSelect: false
```

Track `validations_performed` counter.

## Step 7: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║          Agent Created Successfully                        ║
╚════════════════════════════════════════════════════════════╝

Agent: {agent-name}
Location: {file-path}
Bundle: {bundle-name}
Type: {agent-type}

Statistics:
- Questions answered: {questions_answered}
- Validations performed: {validations_performed}
- Duplication checks: {duplication_checks}
- Files created: {files_created}

Next steps:
1. Review agent file: {file-path}
2. Run diagnosis: /plugin-doctor agents agent-name={agent-name}
3. Test agent functionality
```

## Step 8: Run Agent Diagnosis

```
SlashCommand: /pm-plugin-development:plugin-doctor agents agent-name={agent-name}
```

If diagnosis fails: Display warning but don't abort (agent already created).
