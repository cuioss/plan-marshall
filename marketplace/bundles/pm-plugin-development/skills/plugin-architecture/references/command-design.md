# Command Design Principles

Design principles for goal-based commands that act as thin orchestrators routing to skill workflows.

## Thin Orchestrator Pattern

**Principle**: Commands parse parameters and route to skill workflows. They don't contain execution logic.

**Command Responsibilities**:
- Parse user parameters
- Determine scope/intent
- Route to appropriate skill workflow
- Display results to user
- Handle user interaction

**NOT Command Responsibilities**:
- Execute complex logic (delegate to skills)
- Contain knowledge/standards (use skills)
- Duplicate workflow logic (invoke skills)

## Goal-Based Command Structure

### Command Organization

Commands organized by user goals, not component types:

```markdown
# ✅ GOOD: Goal-based with bundle prefix
commands/
├── plugin-create.md     # CREATE any component type
├── plugin-diagnose.md   # DIAGNOSE any scope
├── plugin-fix.md        # FIX identified issues
├── plugin-maintain.md   # MAINTAIN marketplace health
└── plugin-verify.md     # VERIFY complete marketplace

# ❌ BAD: Component-centric
commands/
├── create-agent.md    # Component-specific
├── create-command.md  # Component-specific
├── diagnose-agents.md # Component-specific
└── diagnose-commands.md # Component-specific
```

### Command Template

```markdown
---
name: command-name
description: Brief description matching user goal
---

# Command Name

Description of what this command helps users accomplish.

## Usage

Examples of command invocation with different parameters.

## Workflow

### Step 1: Parse Parameters
Determine user intent from parameters

### Step 2: Invoke Skill
Route to appropriate skill workflow

### Step 3: Display Results
Show results to user

### Step 4: Handle Follow-up (if needed)
Ask user for next action or additional input
```

## Parameter Parsing Strategies

### Positional Parameters

```markdown
# Simple, single-value parameter
/plugin-create agent
/plugin-diagnose marketplace
```

**Pattern**:
```markdown
Step 1: Parse Command Parameter
- If parameter = "agent" → component_type = "agent"
- If parameter = "command" → component_type = "command"
- If parameter = "skill" → component_type = "skill"
- If parameter = "bundle" → component_type = "bundle"
```

### Named Parameters

```markdown
# Key-value pairs
/plugin-diagnose agent=my-agent
/plugin-diagnose agents
/plugin-maintain update component=my-agent
```

**Pattern**:
```markdown
Step 1: Parse Parameters
- Extract key-value pairs (e.g., "agent=my-agent")
- Identify scope flags (e.g., "agents" = all agents)
- Detect options (e.g., "--fix")
```

### Optional Flags

```markdown
# Boolean flags
/plugin-diagnose marketplace --fix
/plugin-verify --verbose
```

**Pattern**:
```markdown
Step 1: Check for Flags
- If "--fix" present → auto_fix = true
- If "--verbose" present → verbose_output = true
```

## Routing to Skill Workflows

### Direct Routing

```markdown
## Step 2: Invoke Skill Workflow

Based on parameters:
- component_type = "agent" → Skill: plugin-create, Workflow: create-agent
- component_type = "command" → Skill: plugin-create, Workflow: create-command
- component_type = "skill" → Skill: plugin-create, Workflow: create-skill
```

### Conditional Routing

```markdown
## Step 2: Determine and Invoke Workflow

If component_path provided:
  Skill: plugin-diagnose
  Workflow: analyze-component
  Parameters: {component_path, component_type}

Else if component_type provided:
  Skill: plugin-diagnose
  Workflow: analyze-all-of-type
  Parameters: {component_type}

Else:
  Skill: plugin-diagnose
  Workflow: validate-marketplace
```

### Chained Routing

```markdown
## Step 2: Diagnose

Skill: plugin-diagnose
Workflow: appropriate-workflow
Parameters: {parsed parameters}

## Step 3: Fix (if --fix flag present)

If auto_fix = true:
  Skill: plugin-fix
  Workflow: apply-fixes
  Parameters: {issues from Step 2}
```

## User Interaction Patterns

### When to Ask Users

**Ask when**:
- Ambiguous intent (multiple valid interpretations)
- Missing required information
- Confirming destructive operations
- Choosing between multiple options

**Don't ask when**:
- Clear default exists
- Single valid interpretation
- Information can be inferred
- Safe, non-destructive operation

### Asking Patterns

**Using AskUserQuestion**:
```markdown
Step 1: Determine Component Type

If component type not provided:
  AskUserQuestion:
    Question: "Which type of component do you want to create?"
    Options:
      - Agent (focused task executor)
      - Command (user-invoked utility)
      - Skill (knowledge and workflows)
      - Bundle (collection of components)
```

**Confirmation for Risky Operations**:
```markdown
Step 3: Confirm Deletion

AskUserQuestion:
  Question: "This will delete 14 old commands. Continue?"
  Options:
    - Yes, proceed with deletion
    - No, cancel operation
```

## Result Display Patterns

### Structured Output

```markdown
Step 3: Display Results

Show results in clear, structured format:

✅ CREATED: my-agent.md
📁 Location: marketplace/bundles/my-bundle/agents/
🎯 Pattern: Script Automation (Pattern 1)
📋 Next Steps:
  1. Implement workflow in my-agent.md
  2. Create scripts in scripts/ directory
  3. Test agent with /test-agent my-agent
```

### Summary + Details

```markdown
Step 3: Display Diagnosis Results

## Summary
- Total Components: 25
- Issues Found: 12
- Severity: 3 high, 6 medium, 3 low

## Details
[Detailed issue list]

## Recommendations
[Suggested actions]
```

### Progressive Results

```markdown
Step 2: Process Components

For each component (with progress):
  Processing [3/25]: my-agent.md
  ✅ Format: Valid
  ✅ Links: All valid
  ⚠️  Content: 2 suggestions
```

## Command Examples

### Example 1: plugin-create Command

```markdown
---
name: plugin-create
description: Create new marketplace component (agent, command, skill, or bundle)
---

# Create Marketplace Component

## Usage

```
/plugin-create agent
/plugin-create command
/plugin-create skill
/plugin-create bundle
```

## Workflow

### Step 1: Parse Component Type

If not provided, ask user:
  AskUserQuestion: "Which type do you want to create?"

### Step 2: Route to Creation Workflow

Skill: plugin-create
Workflow: create-{component_type}

### Step 3: Display Results

Show created file path and next steps
```

### Example 2: plugin-diagnose Command

```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components
---

# Diagnose Marketplace Issues

## Usage

```
/plugin-diagnose agent=my-agent
/plugin-diagnose agents
/plugin-diagnose marketplace
/plugin-diagnose marketplace --fix
```

## Workflow

### Step 1: Parse Parameters

Determine scope:
- Specific component (agent=name)
- Component type (agents)
- Entire marketplace (marketplace)

Check for --fix flag

### Step 2: Invoke Diagnostic Workflow

Skill: plugin-diagnose
Workflow: [based on scope]
Parameters: {parsed from Step 1}

### Step 3: Display Results

Show issues categorized by severity

### Step 4: Offer Fix Option

If --fix not provided and issues found:
  Ask: "Apply automatic fixes?"

### Step 5: Apply Fixes (if confirmed)

Skill: plugin-fix
Workflow: apply-fixes
Parameters: {issues from Step 2}
```

## Command Quality Standards

### Clear Purpose

**Each command should**:
- Serve single user goal
- Have clear, predictable behavior
- Provide helpful error messages

### Minimal Logic

**Commands should**:
- Parse parameters (simple logic)
- Route to skills (delegation)
- Display results (formatting)

**Commands should NOT**:
- Implement complex algorithms
- Contain domain knowledge
- Duplicate skill logic

### Helpful Feedback

**Provide**:
- Clear progress indicators
- Meaningful error messages
- Actionable next steps
- Examples when parameters incorrect

### Consistent Patterns

**Follow**:
- Standard parameter syntax
- Consistent error handling
- Predictable output format
- Common interaction patterns

## Best Practices Summary

**1. Thin Orchestration**:
- Parse parameters
- Route to skills
- Display results
- Don't implement logic

**2. Goal-Based**:
- Organized by user goals
- Not by component types
- Clear user mental model

**3. Smart Parsing**:
- Handle positional, named, and flag parameters
- Provide sensible defaults
- Ask when ambiguous

**4. User-Friendly**:
- Clear output formatting
- Progress indicators
- Helpful error messages
- Actionable next steps

**5. Skill Delegation**:
- All complex logic in skills
- Commands coordinate only
- Reuse skill workflows

## Related References

- Skill Design: references/skill-design.md
- Skill Patterns: references/skill-patterns.md
- Goal-Based Organization: references/goal-based-organization.md
