# Step Execution Patterns

How to execute steps (file paths) for plugin-domain tasks.

## Step Types

Each step `title` is a file path. Determine operation type from:
1. Task description
2. File existence
3. Deliverable guidance

| File Exists | Task Intent | Operation |
|-------------|-------------|-----------|
| Yes | Update | Modify existing file |
| Yes | Replace | Overwrite file |
| No | Create | Create new file |
| Yes | Delete | Remove file |

## Plugin File Structure

All plugin files (agents, commands, skills) are markdown with YAML frontmatter:

```markdown
---
name: component-name
description: Component description
tools: Tool1, Tool2
---

# Component Title

## Section 1
Content...

## Section 2
Content...
```

## Modification Patterns

### Update YAML Frontmatter

```python
# Pattern: Add or update frontmatter field
old: "tools: Read, Write"
new: "tools: Read, Write, Edit"
```

Use Edit tool with precise old/new strings.

### Update Code Blocks

```python
# Pattern: Replace code block language or content
old: """```{old_language}
{old_content}
```"""

new: """```{new_language}
{new_content}
```"""
```

### Update Section Content

```python
# Pattern: Replace section header or content
old: "## Old Section Title\n\nOld content"
new: "## New Section Title\n\nNew content"
```

## Execution Flow Per Step

### 1. Read Current Content

```
Read: {step.target}
```

Parse the file to understand:
- Frontmatter fields
- Section structure
- Code blocks (language, content)

### 2. Plan Changes

Based on task description, identify:
- What sections to modify
- What code blocks to update
- What patterns to apply

### 3. Apply Changes

Use Edit tool for surgical changes:

```
Edit:
  file_path: {step.target}
  old_string: {exact text to replace}
  new_string: {replacement text}
```

**Prefer multiple small edits over one large write.**

### 4. Verify Changes

After editing, optionally verify:
- File still parses correctly
- YAML frontmatter is valid
- No broken references

## Common Plugin Changes

### Agent: Update Return Structure

Steps:
1. Find "Return" or "Output" section
2. Locate code blocks showing output format
3. Apply changes per task description
4. Update surrounding prose if needed

### Command: Update Workflow

Steps:
1. Find workflow steps section
2. Identify steps to modify
3. Update step content
4. Ensure cross-references remain valid

### Skill: Update Standards Reference

Steps:
1. Find standards or references section
2. Update paths or content
3. Verify linked files exist

## Error Recovery

### Parse Error

If file cannot be parsed:
1. Log error with file path
2. Skip step
3. Mark step as failed
4. Continue to next step

### Edit Conflict

If old_string not found:
1. Read file again (may have changed)
2. Adjust old_string
3. Retry edit
4. If still fails, log and continue

### Validation Failure

If changes break file structure:
1. Log the issue
2. Attempt to restore
3. Mark step as failed
4. Continue to next step
