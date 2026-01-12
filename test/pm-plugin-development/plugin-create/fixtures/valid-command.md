---
name: test-command
description: Test command for validation purposes
---

# Test Command

This is a test command for validation purposes.

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this command and discover a more precise, better, or more efficient approach, **YOU MUST immediately update this file** using `/plugin-update-command command-name=test-command update="[your improvement]"` with:
1. Enhanced workflow patterns
2. Better error handling
3. Improved user guidance
4. Performance optimizations
5. Any lessons learned about command workflows

This ensures the command evolves and becomes more effective with each execution.

## PARAMETERS

**target** - The target to process (required)
**--verbose** - Show detailed output (flag, default: false)

## WORKFLOW

### Step 1: Parse Parameters
Parse and validate command parameters

### Step 2: Load Required Skills
Skill: test-skill

### Step 3: Execute Workflow
Based on parameters, execute appropriate workflow

### Step 4: Display Results
Format and show results to user

## CRITICAL RULES

- Validate parameters before execution
- Handle errors gracefully
- Provide clear feedback to user

## USAGE EXAMPLES

```bash
# Basic usage
/test-command my-target

# Verbose mode
/test-command my-target --verbose
```

## RELATED

- **Skills**: test-skill
- **Commands**: None
- **Agents**: None
