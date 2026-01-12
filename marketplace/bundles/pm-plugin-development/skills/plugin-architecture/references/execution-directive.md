# Execution Directive Standard

Standards for ensuring Claude executes skill workflows rather than explaining them.

## Problem Statement

When commands load skills via the Skill tool, Claude may treat skill content as information to display rather than instructions to execute. This violates the command/skill architecture where:
- **Commands** = thin orchestrators that delegate
- **Skills** = contain all logic to be executed immediately

## Root Cause

1. Skill content appears as `<command-message>` in conversation
2. No explicit directive tells Claude to ACT rather than EXPLAIN
3. Soft language ("you can", "consider") instead of imperative ("EXECUTE", "RUN")
4. Ambiguity between "reference this file" vs "execute this script"

## Solution: Execution Mode Directive

### Required Header for Execution Skills

All skills that perform actions (not pure reference skills) MUST include an execution directive immediately after the skill title:

```markdown
---
name: skill-name
description: Description with execution triggers
allowed-tools: [Tool1, Tool2]
---

# Skill Name

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below.

## Workflow Decision Tree
...
```

### Variations by Skill Type

**For Execution Skills** (Pattern 1-9):
```markdown
**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below.
```

**For Reference Skills** (Pattern 10):
```markdown
**REFERENCE MODE**: This skill provides reference material. Load specific references on-demand based on current task. Do not load all references at once.
```

**For Hybrid Skills** (execution + reference):
```markdown
**EXECUTION MODE**: You are now executing this skill. Load required references, then IMMEDIATELY execute the workflow. DO NOT explain the workflow to the user.
```

## MANDATORY and CRITICAL Markers

### Purpose

Use MANDATORY and CRITICAL markers to:
1. Force Claude's attention to essential steps
2. Prevent skipping or summarizing
3. Create execution checkpoints

### Usage Patterns

**MANDATORY** - Step cannot be skipped:
```markdown
### Step 1: Run Diagnostics

**MANDATORY**: Execute this script NOW before proceeding:
```bash
bash scripts/analyze-markdown-file.sh <file>
```

Do not continue to Step 2 until this completes successfully.
```

**CRITICAL** - Important constraint or rule:
```markdown
**CRITICAL**: Never modify files without first reading them. Use the Read tool before any Edit operation.
```

**NEVER** - Prohibited action:
```markdown
**NEVER** load all references at once. Load only what's needed for current task.
```

### Placement Rules

1. Place MANDATORY at the start of workflow steps
2. Place CRITICAL before constraint explanations
3. Use CAPS for visibility
4. Bold the entire marker: `**MANDATORY**:`

## Execution vs Reference Clarity

### The Problem

Ambiguous instructions like:
- "See `script.py` for details" - Should Claude read it or run it?
- "Use the analyzer script" - Read the code or execute it?

### The Solution

Always specify the action mode:

**EXECUTE** - Run the script/command:
```markdown
**EXECUTE**: `bash scripts/diagnose.sh <file>`
```

**READ** - Load content into context:
```markdown
**READ**: `references/standards.md` for validation rules
```

**REFERENCE** - Consult if needed (don't load by default):
```markdown
**REFERENCE**: See `references/advanced.md` if basic validation fails
```

### Script Documentation Table

Document all scripts with explicit modes:

```markdown
## Scripts

| Script | Mode | Purpose |
|--------|------|---------|
| `plugin-doctor:analyze markdown` | **EXECUTE** | Run to analyze component structure |
| `plugin-doctor:fix apply` | **EXECUTE** | Run to apply identified fixes |
| `README.md` | Reference | Read only if script errors occur |
| `fix-catalog.md` | READ | Load before applying fixes |
```

## Workflow Decision Trees

### Purpose

Decision trees route Claude immediately to the correct action, preventing deliberation or explanation.

### Structure

```markdown
## Workflow Decision Tree

### If single component specified
→ **EXECUTE** Step 1A: Single Component Analysis

### If component type specified (no specific file)
→ **EXECUTE** Step 1B: Batch Analysis

### If no parameters
→ **EXECUTE** Step 1C: Full Marketplace Scan
```

### Benefits

1. Immediate routing to action
2. No ambiguity about which workflow
3. Parameters drive execution path
4. Prevents "let me explain the options" behavior

## Command Handoff Pattern

Commands must explicitly instruct Claude about skill execution:

```markdown
## WORKFLOW

When you invoke this command, I will:

1. **Parse parameters** from input

2. **Load skill and EXECUTE its workflow**:
   ```
   Skill: bundle-name:skill-name
   ```

   **CRITICAL HANDOFF RULES**:
   - DO NOT summarize or explain the skill content
   - DO NOT describe what the skill says to do
   - IMMEDIATELY execute the scripts and tools specified
   - Your next action after loading must be a tool call, not text output
```

## Imperative Language Guidelines

### Use Directive Commands

**Good** (imperative):
- "Execute the analyzer script"
- "Read the standards file"
- "Run diagnostics on all commands"

**Bad** (suggestive):
- "You might want to run the analyzer"
- "Consider reading the standards"
- "It would be good to run diagnostics"

### Active Voice

**Good**:
- "The script outputs JSON"
- "Parse the results"
- "Report findings"

**Bad**:
- "JSON is output by the script"
- "Results should be parsed"
- "Findings can be reported"

## Code-First Pattern

### Structure

Present executable code BEFORE explanation:

```markdown
### Step 1: Analyze Component

**EXECUTE**:
```bash
bash scripts/analyze-markdown-file.sh /path/to/component.md
```

This script outputs JSON with structural analysis including frontmatter validation, section counts, and rule violations.
```

### Anti-Pattern

```markdown
### Step 1: Analyze Component

First, we need to understand the component structure. The analyzer script examines frontmatter, sections, and compliance rules. It produces JSON output that we can parse to identify issues.

To run it:
```bash
bash scripts/analyze-markdown-file.sh /path/to/component.md
```
```

## Validation Checklist Pattern

Convert passive reading into active verification:

```markdown
## Verification Checklist

After completing the workflow:

- [ ] All diagnostic scripts executed successfully
- [ ] JSON output parsed without errors
- [ ] Issues categorized by severity
- [ ] Safe fixes applied automatically
- [ ] User prompted for risky fixes only
- [ ] Re-ran diagnostics to verify fixes
```

## Template: Complete Execution Skill

```markdown
---
name: example-execution-skill
description: Performs X when user needs to Y. Triggers on: specific condition A, specific condition B
allowed-tools: [Read, Bash, Edit, Glob]
---

# Example Execution Skill

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below.

## Workflow Decision Tree

### If [condition A]
→ **EXECUTE** Workflow 1: Handle Condition A

### If [condition B]
→ **EXECUTE** Workflow 2: Handle Condition B

## Workflow 1: Handle Condition A

### Step 1: Gather Data

**MANDATORY**: Execute this script first:
```bash
bash scripts/gather-data.sh <input>
```

### Step 2: Process Results

**READ**: `references/processing-rules.md`

Apply rules from the reference to the script output.

### Step 3: Apply Changes

**EXECUTE**:
```bash
python3 .plan/execute-script.py {bundle}:{skill}:apply-changes --input results.json
```

**CRITICAL**: Verify changes before proceeding to next component.

## Workflow 2: Handle Condition B

[Similar structure with MANDATORY markers and explicit EXECUTE/READ modes]

## Scripts

| Script | Mode | Purpose |
|--------|------|---------|
| `gather-data.sh` | **EXECUTE** | Collects input data |
| `apply-changes.py` | **EXECUTE** | Applies processed changes |
| `processing-rules.md` | READ | Rules for data processing |

## Verification Checklist

- [ ] Correct workflow selected based on conditions
- [ ] All MANDATORY steps completed
- [ ] Script outputs validated
- [ ] Changes verified
```

## Anti-Patterns to Avoid

### 1. Meta-Explanation

**Bad**:
```markdown
This skill helps you analyze components. When loaded, it provides workflows for different analysis scenarios. You can choose which workflow suits your needs.
```

**Good**:
```markdown
**EXECUTION MODE**: IMMEDIATELY begin workflow based on input parameters.
```

### 2. Passive Language

**Bad**:
```markdown
The script can be run to perform analysis.
```

**Good**:
```markdown
**EXECUTE**: `bash scripts/analyze.sh`
```

### 3. Optional Steps

**Bad**:
```markdown
You may want to run the validator first.
```

**Good**:
```markdown
**MANDATORY**: Run validator before proceeding.
```

### 4. Ambiguous Actions

**Bad**:
```markdown
See the standards file for details.
```

**Good**:
```markdown
**READ**: `references/standards.md` to load validation rules.
```

## Integration with Diagnostics

The plugin-doctor skill should check for:

1. **Execution directive present** - Skills must have EXECUTION MODE or REFERENCE MODE
2. **MANDATORY markers used** - Workflow steps should use MANDATORY for critical actions
3. **Explicit action modes** - Scripts should have EXECUTE/READ/REFERENCE labels
4. **Imperative language** - Check for passive or suggestive phrasing
5. **Code-first pattern** - Code blocks should precede explanations

## References

### Research Basis
- Anthropic Skills Repository analysis
- Claude Code best practices documentation
- LLM prompt engineering patterns for action vs explanation

### Related Standards
- `command-design.md` - Thin orchestrator pattern
- `skill-patterns.md` - Pattern 1-10 implementation
- `core-principles.md` - Imperative language guidelines
