# Command Creation Guide

Comprehensive guide for creating well-structured marketplace commands following thin orchestrator pattern.

## When to Create Commands vs Other Components

### Create a Command When:
- **User-facing utility** - Users invoke directly with `/command-name`
- **Interactive workflow** - Need to ask user questions or gather requirements
- **Orchestration** - Coordinating multiple agents or workflows
- **Parameter routing** - Parse parameters and route to appropriate workflows
- **Delegation** - Need to use Task tool to launch agents

### Create an Agent Instead When:
- **Autonomous execution** - No user interaction after launch
- **Focused task** - Single, well-defined operation
- **Called by commands** - Designed to be invoked by orchestrators

### Create a Skill Instead When:
- **Knowledge provision** - Standards, guidelines, reference material
- **No user invocation** - Loaded by commands/agents, not run directly

## Command Design Principles

### Principle 1: Thin Orchestrators
Commands should be thin orchestrators that parse parameters and route to skills/agents.

**Good** (Thin):
```markdown
Command: diagnose
1. Parse scope parameter (agent/command/skill/all)
2. Route to appropriate skill workflow
3. Display results
```

**Bad** (Fat):
```markdown
Command: diagnose-agents
1. Parse parameters
2. Find all agents (embedded logic)
3. Validate each agent (embedded validation)
4. Generate report (embedded reporting)
5. Display results
```
This logic should be in a skill, not command.

### Principle 2: Parameter-Driven
Commands parse parameters and make routing decisions based on them.

**Good Parameter Design**:
```markdown
## PARAMETERS

**scope** - What to analyze (agent/command/skill/all, default: all)
**name** - Specific component name (optional, analyzes all if omitted)
**fix** - Auto-fix issues (true/false, default: false)
```

### Principle 3: Skill Delegation with Critical Handoff

Commands delegate heavy lifting to skills, but must include explicit handoff rules to ensure Claude EXECUTES the skill rather than explaining it.

**The Problem**: When commands load skills, Claude may treat skill content as information to summarize rather than instructions to execute. This violates the command/skill architecture.

**Solution - CRITICAL HANDOFF RULES**:

Every command that loads a skill MUST include this pattern:

```markdown
## WORKFLOW

When you invoke this command, I will:

1. **Parse parameters** from input

2. **Load skill and EXECUTE its workflow**:
   ```
   Skill: bundle-name:skill-name
   ```

   **CRITICAL HANDOFF RULES**:
   - DO NOT summarize or explain the skill content to the user
   - DO NOT describe what the skill says to do
   - IMMEDIATELY execute the scripts and tools specified in the skill
   - Your next action after loading the skill MUST be a tool call, not text output
   - Follow the skill's workflow decision tree to select the correct workflow
   - Execute MANDATORY steps without commentary

3. **Display results** only after workflow completes
```

**Why This Works**:
- Caps-lock "CRITICAL" forces Claude's attention
- "DO NOT" prohibitions prevent common failure modes
- "MUST be a tool call" creates concrete behavioral expectation
- Lists specific anti-patterns to avoid

**Good Delegation** (with handoff):
```markdown
### Step 1: Load Diagnostic Skill
Skill: pm-plugin-development:plugin-diagnose

**CRITICAL HANDOFF**: Execute skill workflow immediately. Do not explain.

### Step 2: Execute Workflow
Based on scope parameter:
- scope=agent → Execute analyze-agent workflow
- scope=command → Execute analyze-command workflow
- scope=all → Execute analyze-all workflow
```

## Command Structure

### Required Sections

Every command must have:

1. **Frontmatter** (YAML with name, description)
2. **Title** (# Command Name)
3. **Overview** (brief explanation)
4. **CONTINUOUS IMPROVEMENT RULE**
5. **PARAMETERS** (if applicable)
6. **WORKFLOW** (numbered steps)
7. **CRITICAL RULES**
8. **USAGE EXAMPLES**
9. **RELATED** (related commands/skills)

### Optional Sections

- **STATISTICS TRACKING** (if command tracks metrics)
- **ERROR HANDLING** (if complex error scenarios)
- **ARCHITECTURE** (if noteworthy implementation details)

## Frontmatter Format

### Basic Command

```yaml
---
name: command-name
description: One sentence description (<100 chars)
---
```

### Notes

- **NO tools field** in command frontmatter (tools specified in workflow, not frontmatter)
- Name must be kebab-case
- Description must be concise (<100 chars)

## CONTINUOUS IMPROVEMENT RULE for Commands

Commands record lessons learned via the `manage-lessons` skill.

**Pattern for Commands**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "{command-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

**Key Points**:
- Only activate skill when you have lessons to record
- Lessons are stored via `manage-lessons` skill (individual Markdown files)
- Categories: bug, improvement, pattern, anti-pattern

## Parameter Patterns

### Pattern 1: Positional Parameters

```markdown
## PARAMETERS

**component-name** - Name of component to analyze (required)
**options** - Additional options (optional)
```

Usage: `/plugin-diagnose my-agent --fix`

### Pattern 2: Named Parameters

```markdown
## PARAMETERS

**name** - Component name (required)
**scope** - Analysis scope (agent/command/skill, required)
**verbose** - Show detailed output (true/false, default: false)
```

Usage: `/plugin-diagnose name=my-agent scope=agent verbose=true`

### Pattern 3: Flag Parameters

```markdown
## PARAMETERS

**target** - What to analyze (required)
**--fix** - Automatically fix issues (flag, default: true)
```

Usage: `/plugin-fix my-agent`

### Pattern 4: No Parameters

```markdown
## PARAMETERS

None - Command operates on current context
```

Usage: `/plugin-verify`

## Workflow Patterns

### Pattern 1: Direct Skill Routing

```markdown
## WORKFLOW

### Step 1: Load Skill
Skill: pm-plugin-development:plugin-diagnose

### Step 2: Execute Workflow
Execute diagnose-agent workflow with parameters

### Step 3: Display Results
Format and show findings to user
```

### Pattern 2: Conditional Routing

```markdown
## WORKFLOW

### Step 1: Parse Parameters
Determine scope from parameters

### Step 2: Route Based on Scope
If scope=agent:
  Load plugin-diagnose skill, execute analyze-agent workflow
If scope=command:
  Load plugin-diagnose skill, execute analyze-command workflow
If scope=skill:
  Load plugin-diagnose skill, execute analyze-skill workflow

### Step 3: Display Results
```

### Pattern 3: Sequential Workflows

```markdown
## WORKFLOW

### Step 1: Diagnose
Load plugin-diagnose skill, find issues

### Step 2: Confirm Fix
If issues found:
  Ask user: "Fix these issues? [Y/n]"
  If yes: Continue to Step 3
  If no: Exit

### Step 3: Apply Fixes
Load plugin-fix skill, apply fixes

### Step 4: Verify
Re-run diagnosis to confirm fixes applied
```

### Pattern 4: Parallel Delegation

```markdown
## WORKFLOW

### Step 1: Launch Parallel Analysis
Task: code-analyzer agent (analyzes code)
Task: test-analyzer agent (analyzes tests)
Task: doc-analyzer agent (analyzes docs)

### Step 2: Aggregate Results
Combine results from all agents

### Step 3: Display Summary
```

## Quality Standards

### Target Length: <400 Lines

Commands should be concise. If exceeding 400 lines:
- Extract embedded logic to skills
- Move detailed guidance to skill references
- Keep only orchestration logic in command

### No Embedded Templates

❌ **Wrong**:
```markdown
### Step 3: Generate Report

Create report with this structure:
╔═══════════════════════════════════════╗
║  [290 lines of embedded template]     ║
╚═══════════════════════════════════════╝
```

✅ **Correct**:
```markdown
### Step 3: Generate Report

Load report template from skill:
Read assets/templates/report.md
Fill template with findings
```

### Trust AI Inference

Don't over-specify. Let AI infer reasonable behavior.

❌ **Wrong** (Over-specified):
```markdown
### Step 1: Validate Name

If name is empty:
  Show error: "Name required"
  Exit with code 1
If name contains spaces:
  Show error: "Name cannot contain spaces"
  Exit with code 1
If name contains uppercase:
  Show error: "Name must be lowercase"
  Exit with code 1
If name starts with number:
  Show error: "Name cannot start with number"
  Exit with code 1
[...20 more validation rules...]
```

✅ **Correct** (Trust AI):
```markdown
### Step 1: Validate Name

Validate name is kebab-case format.
If invalid: Show error and exit.
```

### Reference Skills for Details

❌ **Wrong** (Duplication):
```markdown
### Step 2: Check Architecture Rules

Rule 1: Skills must be self-contained
  - No cross-skill duplication
  - Use Skill: for cross-references
  - All content in skill directory

Rule 2: Progressive disclosure
  - Minimal SKILL.md
  - References loaded on-demand
  [... 50 more lines of rules ...]
```

✅ **Correct** (Reference):
```markdown
### Step 2: Check Architecture Rules

Load architecture rules:
Skill: pm-plugin-development:plugin-architecture

Validate component against rules
```

## Orchestration Patterns

### Pattern 1: Simple Routing

```markdown
Command → Skill Workflow → Display Results
```

Example: `/plugin-create agent` → plugin-create skill, create-agent workflow

### Pattern 2: Conditional Orchestration

```markdown
Command → Parse Parameters → Route to Different Workflows → Display
```

Example: `/plugin-diagnose scope=X` → plugin-diagnose skill, different workflow per scope

### Pattern 3: Sequential Orchestration

```markdown
Command → Workflow 1 → Workflow 2 → Workflow 3 → Display
```

Example: `/plugin-maintain readme` → scan → update → validate → display

### Pattern 4: Agent Delegation

```markdown
Command → Launch Agent(s) → Aggregate Results → Display
```

Example: `/analyze project` → launch multiple analysis agents → combine results

## Error Handling

### Pattern 1: Validate Early

```markdown
### Step 1: Validate Parameters

Check all required parameters present
Check parameter values valid
If validation fails: Show error and exit

### Step 2: Execute Workflow
[Now safe to proceed]
```

### Pattern 2: Graceful Degradation

```markdown
### Step 3: Run Diagnosis

Execute diagnosis workflow
If diagnosis fails:
  Show warning: "⚠️ Diagnosis failed: {error}"
  Note: "Component created but not validated"
  Suggest: "Run /plugin-diagnose {name} manually"
  Continue (don't abort entire command)
```

### Pattern 3: User Recovery Options

```markdown
### Step 4: Apply Changes

Write changes to files
If write fails:
  Show error: "Failed to write: {error}"
  Prompt: "[R]etry write / [A]bort command"
  If retry: Attempt write again
  If abort: Exit cleanly
```

## Statistics Tracking

Commands often track statistics for transparency.

### Common Counters

```markdown
## STATISTICS TRACKING

Track throughout workflow:
- `questions_answered`: User responses collected
- `validations_performed`: Validation checks executed
- `files_created`: Files successfully created
- `issues_found`: Problems detected
- `fixes_applied`: Corrections made
```

### Display in Summary

```markdown
### Final Step: Display Summary

╔════════════════════════════════════════╗
║   Operation Completed Successfully     ║
╚════════════════════════════════════════╝

Statistics:
- Questions answered: {questions_answered}
- Validations performed: {validations_performed}
- Files created: {files_created}
- Issues found: {issues_found}
- Fixes applied: {fixes_applied}
```

## Command Types

### Type 1: Orchestration Commands

**Purpose**: Coordinate multiple agents or workflows

**Example**:
```markdown
---
name: verify-marketplace
description: Comprehensive marketplace health check across all components
---

# Verify Marketplace Command

Orchestrates complete marketplace verification.

## WORKFLOW

### Step 1: Load Skills
Skill: plugin-diagnose
Skill: plugin-architecture

### Step 2: Run All Diagnostics
Execute diagnose-agents workflow
Execute diagnose-commands workflow
Execute diagnose-skills workflow
Execute validate-metadata workflow

### Step 3: Aggregate Results
Combine all findings

### Step 4: Generate Health Report
Display overall marketplace health score
```

### Type 2: Diagnostic Commands

**Purpose**: Analyze and report on system state

**Example**:
```markdown
---
name: diagnose
description: Analyze marketplace components for issues
---

# Diagnose Command

Analyzes components and reports findings.

## PARAMETERS

**scope** - What to analyze (agent/command/skill/all, default: all)
**name** - Specific component (optional)

## WORKFLOW

### Step 1: Parse Scope
Determine what to analyze from parameters

### Step 2: Execute Analysis
Load plugin-diagnose skill
Execute appropriate workflow based on scope

### Step 3: Display Findings
Show issues found with severity levels
```

### Type 3: Interactive Commands

**Purpose**: Gather requirements through questionnaires

**Example**:
```markdown
---
name: create
description: Create new marketplace component with interactive wizard
---

# Create Command

Interactive wizard for component creation.

## PARAMETERS

**type** - Component type (agent/command/skill/bundle, default: prompt user)

## WORKFLOW

### Step 1: Determine Type
If type parameter provided: Use it
Else: Ask user what to create

### Step 2: Load Creation Skill
Skill: plugin-create

### Step 3: Execute Creation Workflow
Based on type:
- agent → create-agent workflow
- command → create-command workflow
- skill → create-skill workflow
- bundle → create-bundle workflow

### Step 4: Display Summary
Show created component details
```

### Type 4: Automation Commands

**Purpose**: Execute predefined workflows

**Example**:
```markdown
---
name: fix
description: Automatically fix detected issues in components
---

# Fix Command

Applies automated fixes to component issues.

## PARAMETERS

**target** - Component to fix (required)

## WORKFLOW

### Step 1: Diagnose
Load plugin-diagnose skill
Find issues in target component

### Step 2: Categorize Issues
Separate auto-fixable vs manual issues

### Step 3: Apply Fixes
Load plugin-fix skill
Apply automated fixes

### Step 4: Verify
Re-run diagnosis
Confirm fixes applied
```

## Validation Checklist

Before creating command, verify:

- [ ] Name is kebab-case with verb (create-agent, run-tests, diagnose-code)
- [ ] Description is <100 chars
- [ ] Frontmatter has only name and description (no tools)
- [ ] CONTINUOUS IMPROVEMENT RULE uses manage-lessons skill
- [ ] All required sections present
- [ ] Workflow is numbered steps
- [ ] Parameters documented (if any)
- [ ] Usage examples provided
- [ ] Related components listed
- [ ] Command is <400 lines
- [ ] No embedded templates
- [ ] Delegates to skills for heavy lifting
- [ ] Error handling specified

## Common Pitfalls

### Pitfall 1: Fat Commands

❌ **Wrong**: Command contains 800 lines of embedded logic

✅ **Correct**: Command is 150 lines, delegates to skill with logic

### Pitfall 2: Missing CONTINUOUS IMPROVEMENT RULE

❌ **Wrong**: No continuous improvement section

✅ **Correct**: Includes CONTINUOUS IMPROVEMENT RULE with manage-lessons skill

### Pitfall 3: No Parameter Validation

❌ **Wrong**: Assumes parameters are valid

✅ **Correct**: Validates parameters in Step 1, fails early

### Pitfall 4: Over-Specification

❌ **Wrong**: 50 lines describing exact error message format

✅ **Correct**: "Show error and exit" - trust AI

### Pitfall 5: Tools in Frontmatter

❌ **Wrong**:
```yaml
---
name: my-command
description: Does stuff
tools: Read, Write  # Commands don't have tools in frontmatter
---
```

✅ **Correct**:
```yaml
---
name: my-command
description: Does stuff
---
```

## References

- Thin Orchestrator Pattern: See plugin-architecture skill
- Skill Delegation: See plugin-architecture skill references
- Command Quality Standards: See command-quality-standards.md
