# Component Update Guide

Comprehensive guide for updating existing agents and commands.

## Update Principles

Updates should:
- Improve component quality or functionality
- Not introduce bloat or duplication
- Maintain existing structure
- Follow anti-bloat rules

## Using analyze-component.py

Before any update, analyze the component:

```bash
scripts/analyze-component.py {component_path}
```

**Output Fields**:
- `quality_score`: 0-100 quality rating
- `issues`: Array of detected issues
- `suggestions`: Improvement recommendations
- `stats`: Line counts and section info

## Quality Score Interpretation

| Score | Interpretation |
|-------|---------------|
| 95-100 | Excellent - minimal changes needed |
| 80-94 | Good - minor improvements possible |
| 60-79 | Fair - several issues to address |
| 40-59 | Poor - significant work needed |
| <40 | Critical - major restructuring required |

## Common Issue Types

### Bloat Issues

**Symptoms**:
- `total_lines` > 500 (warning)
- `total_lines` > 800 (critical)
- Duplicate paragraphs detected

**Resolution**:
- Extract shared content to skill
- Remove redundant sections
- Consolidate related steps

### Missing Sections

**Required Sections**:
- Purpose
- Workflow
- Examples
- Error Handling (for agents)
- Critical Rules

**Adding Sections**:
```python
{
  "type": "section",
  "section": "Error Handling",
  "content": "- If X fails: Do Y\n- If Z fails: Do W"
}
```

### Tool Compliance

**Rule 6**: Agents cannot use Task tool
**Resolution**: Remove Task from tools declaration

**Rule 7**: Only maven-builder uses Maven directly
**Resolution**: Delegate to maven-builder agent

## Using update-component.py

Apply updates via JSON input:

```bash
echo '{"updates": [...]}' | scripts/update-component.py {component_path}
```

### Update Types

**Frontmatter Update**:
```json
{
  "type": "frontmatter",
  "field": "description",
  "value": "Updated description"
}
```

**Section Update**:
```json
{
  "type": "section",
  "section": "Examples",
  "content": "### Example 1\n\n```bash\n/my-command\n```"
}
```

**Text Replace**:
```json
{
  "type": "replace",
  "old": "old text to find",
  "new": "new replacement text"
}
```

**Append Content**:
```json
{
  "type": "append",
  "text": "New section content"
}
```

## Anti-Bloat Rules

### Target Line Change

**Goal**: 0 to -10% line change

| Change | Interpretation |
|--------|---------------|
| -10% to 0% | Ideal - reducing or maintaining |
| 0% to +10% | Acceptable - minor growth |
| +10% to +25% | Warning - justify growth |
| >+25% | Critical - reconsider approach |

### Consolidation Over Addition

**Before adding content**:
1. Check if already exists elsewhere
2. Check if can be referenced via skill
3. Check if existing content can be improved instead

### Skill Extraction

**Extract to skill when**:
- Same content in 3+ components
- Content is reusable across workflows
- Content exceeds 100 lines

## Workflow Structure Standards

### Step Numbering

```markdown
### Step 1: Initialize
### Step 2: Validate
### Step 3: Process
### Step 4: Report
```

### Error Handling Format

```markdown
**Error handling:**
- If X fails: Do Y
- If Z fails: Do W
```

### Tool Usage Format

```markdown
## Tool Usage

- **Read**: Load files, configuration
- **Write**: Create new files
- **Edit**: Modify existing files
```

## Validation After Update

### Required Checks

1. **File Integrity**: Markdown is valid
2. **Frontmatter**: YAML is parseable
3. **Structure**: All sections present
4. **Quality Score**: Not decreased significantly

### Re-Analysis

```bash
scripts/analyze-component.py {component_path}
```

Compare:
- `quality_score`: Should be same or higher
- `issues`: Should have fewer issues
- `stats.total_lines`: Should follow anti-bloat rules

## Common Update Scenarios

### Adding Error Handling

```json
{
  "updates": [
    {
      "type": "section",
      "section": "Error Handling",
      "content": "- If file not found: Display error and abort\n- If validation fails: Report issues and prompt user"
    }
  ]
}
```

### Updating Description

```json
{
  "updates": [
    {
      "type": "frontmatter",
      "field": "description",
      "value": "More accurate description of component purpose"
    }
  ]
}
```

### Fixing Tool Compliance

```json
{
  "updates": [
    {
      "type": "frontmatter",
      "field": "tools",
      "value": "Read, Write, Edit, Glob"
    }
  ]
}
```

## Backup and Recovery

Scripts automatically create backups:
- Backup file: `{component}.md.maintain-backup`
- Restored automatically on error

Manual restore:
```bash
cp {component}.md.maintain-backup {component}.md
```

## Reporting

After successful update, report:
- Changes made (list)
- Lines added/removed
- Quality score change
- Any warnings

## See Also

- `knowledge-management-guide.md` - Adding knowledge to skills
- `readme-maintenance-guide.md` - README updates
