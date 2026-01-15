---
name: tools-analyze-user-prompted
description: Analyze permission prompts to identify source and provide solutions
---

# Analyze User Prompted Command

Diagnoses permission prompts by analyzing screenshots, descriptions, chat history, and permission configurations to identify the source component and provide actionable solutions.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "tools-analyze-user-prompted", bundle: "pm-plugin-development"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

**screenshot** - Path to screenshot showing the permission prompt (optional)

**description** - Context about what happened before the prompt (optional)

Both parameters are optional, but at least one should be provided for meaningful analysis.

## WORKFLOW

### Step 1: Gather Input Data

**A. Screenshot Analysis** (if provided):
- Read the screenshot file using Read tool
- Extract: Tool name, operation attempted, file path or resource
- Extract: Any visible error message or prompt text

**B. Description Context** (if provided):
- Parse user's description of what happened
- Note: Which command/agent was running, what task was being performed

**C. Chat History Analysis**:
- Review recent conversation context
- Identify: Last command invoked, active agent (if any), recent tool calls
- Note: What workflow or task was being executed

### Step 2: Identify Permission Configuration

**A. Load Permission Files**:
```
Read: ~/.claude/settings.json (global permissions)
Read: .claude/settings.local.json (project permissions)
```

**B. Parse Permission Structure**:
- Extract `permissions.allow` array
- Extract `permissions.deny` array
- Extract `permissions.ask` array (explicit prompt rules)
- Note `defaultMode` setting

### Step 3: Analyze Technical Problem

**A. Determine Prompted Tool**:
- From screenshot: Extract exact tool name and arguments
- Match against permission patterns in allow/deny/ask

**B. Identify Permission Gap**:
- Check if tool matches any `allow` pattern
- Check if tool matches any `deny` pattern
- Check if tool falls into default mode (ask)

**C. Trace Source Component**:

If an agent was running:
```
Read: {bundle}/agents/{agent-name}.md
```
- Check `allowed-tools` in frontmatter
- Identify if agent's declared tools match prompted tool

If a command was running:
```
Read: {bundle}/commands/{command-name}.md
```
- Check workflow steps for tool invocations
- Check if command delegates to agents with Task tool

If a skill was loaded:
```
Read: {bundle}/skills/{skill-name}/SKILL.md
```
- Check `allowed-tools` in frontmatter
- Review workflow for tool usage patterns

### Step 4: Root Cause Analysis

**A. Categorize Root Cause**:

| Category | Description |
|----------|-------------|
| Missing Permission | Tool not in allow list, falls to ask |
| Wildcarded Path | Permission exists but path pattern too narrow |
| Agent Tool Declaration | Agent uses tool not in its allowed-tools |
| Skill Tool Declaration | Skill uses tool not in its allowed-tools |
| Dynamic Path | Permission pattern static, actual path dynamic |
| Subagent Inheritance | Task agent inherits different permissions |

**B. Document Finding**:
- Source file path with line numbers
- Exact tool call that triggered prompt
- Why permission was not granted

### Step 5: Generate Analysis Report

Display comprehensive analysis:

```
╔════════════════════════════════════════════════════════════╗
║          Permission Prompt Analysis                        ║
╚════════════════════════════════════════════════════════════╝

## What Happened

Tool: {tool_name}
Operation: {operation}
Resource: {path_or_resource}

## Source Component

Type: {agent | command | skill}
Name: {component-name}
Bundle: {bundle-name}
File: {file_path}:{line_number}

Context (source lines):
```
{3-5 lines of code that triggered the prompt}
```

## Root Cause

Category: {category from Step 4A}
Explanation: {why the prompt occurred}

## Permission State

Global allow patterns checked: {count}
Project allow patterns checked: {count}
Matching pattern found: {yes/no}
Pattern that should match: {pattern}
```

### Step 6: Provide Solutions

Present 1-4 solutions based on root cause:

**Solution 1: Add Global Permission** (if missing from allow)
```json
// Add to ~/.claude/settings.json permissions.allow:
"{permission_pattern}"
```

**Solution 2: Add Project Permission** (if project-specific)
```json
// Add to .claude/settings.local.json permissions.allow:
"{permission_pattern}"
```

**Solution 3: Update Component Declaration** (if tool not declared)
```markdown
// Update {component_file}:
allowed-tools:
  - {existing_tools}
  - {missing_tool}
```

**Solution 4: Modify Workflow** (if tool inappropriate)
```markdown
// Alternative approach that uses permitted tools
```

### Step 7: Interactive Resolution

Prompt user:
```
Which solution would you like to apply?
[1] Add global permission
[2] Add project permission
[3] Update component declaration
[4] Manual (show details only)
```

If user selects 1-3:
- Apply the fix using Edit tool
- Verify fix applied correctly

## CRITICAL RULES

**Analysis Accuracy**:
- Always read actual permission files, don't assume
- Trace to exact source file and line number
- Consider both global and project permissions

**Solution Safety**:
- Never suggest overly broad permissions (e.g., `Bash(*)`)
- Prefer project-local permissions over global when appropriate
- Explain security implications of each solution

**Screenshot Handling**:
- Use Read tool to view screenshot files
- Extract all visible text and context
- Handle missing/invalid screenshots gracefully

**Chat History**:
- Only analyze recent relevant context
- Focus on last command/agent activity
- Don't expose unrelated conversation details

## SAMPLE: Shell Metacharacter Permission Issue

**Problem**: Agent executed `manage-task add` with `--verification-commands "grep -l '```json' *.md | wc -l"` and got prompted. The shell metacharacters (pipes `|`, wildcards `*`, escaped quotes) triggered security checks despite the `Bash(python3 .plan/execute-script.py *)` permission existing.

**Solution**: Refactored `manage-task add` to use stdin-based API with heredoc. Complex task definitions (including verification commands with any characters) are now passed via stdin, completely bypassing shell interpretation. See commit `d512d11` for implementation.

## USAGE EXAMPLES

**Analyze with screenshot:**
```
/pm-plugin-development:tools-analyze-user-prompted screenshot=/tmp/prompt.png
```

**Analyze with description:**
```
/pm-plugin-development:tools-analyze-user-prompted description="Got prompted when running /plugin-doctor"
```

**Analyze with both:**
```
/pm-plugin-development:tools-analyze-user-prompted screenshot=/tmp/prompt.png description="Was running maven build"
```

**Analyze current context only:**
```
/pm-plugin-development:tools-analyze-user-prompted
```

## RELATED

- `/plan-marshall:tools-manage-web-permissions` - Manage WebFetch domain permissions
- `plan-marshall:tools-script-executor` - Script execution permission patterns
- `pm-plugin-development:plugin-architecture` - Component tool declarations
