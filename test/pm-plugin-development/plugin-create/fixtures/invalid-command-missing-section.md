---
name: invalid-command
description: This command is missing the required WORKFLOW section
---

# Invalid Command

This command is missing the WORKFLOW section (required for commands).

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this command and discover a more precise, better, or more efficient approach, **YOU MUST immediately update this file** using `/plugin-update-command command-name=invalid-command update="[your improvement]"` with improvements.

## PARAMETERS

**target** - The target to process (required)

## CRITICAL RULES

- Validate parameters before execution
- Handle errors gracefully

## USAGE EXAMPLES

```bash
# Basic usage
/invalid-command my-target
```

## RELATED

- **Skills**: None
- **Commands**: None
