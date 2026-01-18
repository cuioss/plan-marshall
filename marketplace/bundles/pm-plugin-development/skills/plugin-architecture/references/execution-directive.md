# Execution Behavior Standards

Standards for ensuring Claude executes skill workflows rather than explaining them.

## Problem Statement

When commands load skills via the Skill tool, Claude may treat skill content as information to display rather than instructions to execute. This violates the command/skill architecture where:
- **Commands** = thin orchestrators that delegate
- **Skills** = contain all logic to be executed immediately

## Root Cause

1. Skill content appears as `<command-message>` in conversation
2. Soft language ("you can", "consider") instead of imperative ("EXECUTE", "RUN")
3. Ambiguity between "reference this file" vs "execute this script"
4. Lack of clear workflow structure with explicit action steps

## Solution: Structural Execution Pattern

Well-structured skills execute naturally without explicit directives. The key is using **action-oriented language** and **clear workflow steps**.

### Key Principles

1. **Action-oriented language**: Use imperatives ("Create", "Run", "Load") not suggestions ("consider", "you might")
2. **Clear workflow structure**: Numbered steps with explicit actions
3. **Code-first pattern**: Show executable code BEFORE explanation
4. **Explicit action modes**: Label operations as EXECUTE, READ, or REFERENCE

### Skill Type Guidance

**For Execution Skills** (user-invocable: true):
- Structure with clear workflow sections
- Use numbered steps with imperative language
- Include explicit bash/code blocks for actions

**For Reference Skills** (user-invocable: false):
- Document clearly that content is reference material
- Use "Load when needed" patterns for progressive disclosure

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

Commands delegate to skills via the Skill tool. Well-structured skills with clear workflow steps execute automatically:

```markdown
## WORKFLOW

1. **Parse parameters** from input

2. **Load and execute skill**:
   ```
   Skill: bundle-name:skill-name
   ```
   The skill's workflow steps execute immediately.
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

## Template: User-Invocable Execution Skill

```markdown
---
name: example-execution-skill
description: Performs X when user needs to Y
user-invocable: true
allowed-tools: Read, Bash, Edit, Glob
---

# Example Execution Skill

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
## Workflow Decision Tree

Based on input parameters, execute the appropriate workflow:
- If component specified → Workflow 1
- If scope specified → Workflow 2
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

1. **user-invocable field present** - All skills must have explicit `user-invocable: true` or `user-invocable: false`
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
