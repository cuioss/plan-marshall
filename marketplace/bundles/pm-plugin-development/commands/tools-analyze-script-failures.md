---
name: tools-analyze-script-failures
description: Analyze script failures to identify source and propose fixes
---

# Analyze Script Failures Command

Analyzes script failures from the current session to identify the source component, trace how instructions led to the failed call, and propose fixes.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "tools-analyze-script-failures", bundle: "pm-plugin-development"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

**description** - Optional context about the failure to focus analysis (optional)

If no description provided, analyzes all script failures from current session.

## WORKFLOW

When you invoke this command, I will:

1. **Parse parameters** from input

2. **Load skill and EXECUTE its workflow**:
   ```
   Skill: pm-plugin-development:analyze-script-failures
   ```

   **CRITICAL HANDOFF RULES**:
   - DO NOT summarize or explain the skill content to the user
   - DO NOT describe what the skill says to do
   - IMMEDIATELY execute the workflow steps specified in the skill
   - Your next action after loading the skill MUST be a tool call, not text output
   - Execute the **Analyze Script Failures** workflow with description parameter

3. **Display results** only after workflow completes

## USAGE EXAMPLES

**Analyze all failures in session:**
```
/pm-plugin-development:tools-analyze-script-failures
```

**Analyze with specific context:**
```
/pm-plugin-development:tools-analyze-script-failures description="The manage-task script failed with invalid notation"
```

**Focus on recent failure:**
```
/pm-plugin-development:tools-analyze-script-failures description="Last script call returned exit code 1"
```

## RELATED

- `/pm-plugin-development:tools-analyze-user-prompted` - Analyze permission prompts
- `plan-marshall:manage-lessons` - Store lessons from failures
- `pm-plugin-development:plugin-script-architecture` - Script development standards
- `/pm-plugin-development:plugin-doctor` - Diagnose component issues
