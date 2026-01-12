# Knowledge Management Guide

Guide for adding and managing external knowledge in skills.

## Knowledge Integration Principles

External knowledge should:
- Provide value not available in existing references
- Be isolated in its own reference file
- Be loaded on-demand to reduce context
- Not duplicate existing skill content

## Using check-duplication.py

Before adding knowledge, check for duplication:

```bash
scripts/check-duplication.py {skill_path} {content_file}
```

**Output Fields**:
- `duplication_detected`: Boolean
- `duplication_percentage`: 0-100
- `duplicate_files`: Array of overlapping files
- `recommendation`: proceed, consolidate, or skip

## Duplication Thresholds

| Percentage | Recommendation | Action |
|------------|----------------|--------|
| 0-30% | proceed | Safe to add |
| 30-40% | proceed-with-caution | Review overlap |
| 40-70% | consolidate | Merge with existing |
| 70-100% | skip | Don't add - already exists |

## Knowledge Document Structure

### Standard Format

```markdown
# {Topic} Knowledge

**Source**: {URL or file path}
**Integrated**: {date}
**Load Type**: {on-demand|conditional|always}

## Overview

Brief introduction to the knowledge.

## Main Content

The extracted and formatted knowledge.

## Examples

Practical examples from the source.

## See Also

- Related references
- Original source link
```

### Source Attribution

Always include attribution:
- Original source URL/path
- Integration date
- Any modifications made

## Load Types

### on-demand (Default)

Load only when explicitly requested:

```markdown
### Step X: Load Additional Knowledge (Optional)

**When needed**: Load {topic} knowledge.

```
Read: references/{knowledge-name}.md
```

Use when: {Brief description}
```

### conditional

Load when specific condition met:

```markdown
### Step X: Load {Topic} Standards (Conditional)

**If** {condition}:
```
Read: references/{knowledge-name}.md
```
```

### always

Load as part of standard workflow:

```markdown
### Step X: Load Core Standards

```
Read: references/{knowledge-name}.md
```
```

## Content Transformation

### AsciiDoc to Markdown

Convert common patterns:
- `= Title` → `# Title`
- `== Section` → `## Section`
- `:toc:` → Remove (not needed)
- `[source,java]` → ` ```java `
- `xref:` → Standard markdown links

### Code Examples

Preserve all code examples exactly:
- Keep language annotations
- Maintain indentation
- Include full examples

### Technical Details

Never simplify or summarize technical details:
- Keep exact syntax
- Preserve configuration values
- Maintain version numbers

## SKILL.md Integration

### Adding Reference

Add to SKILL.md in appropriate location:

```markdown
## Knowledge References

### {Topic}

Load when: {condition or "on-demand"}

```
Read: references/{knowledge-name}.md
```
```

### Updating Workflow

If knowledge affects workflow:
1. Identify affected steps
2. Add reference loading at appropriate point
3. Update step instructions to use knowledge

## Duplication Handling

### consolidate Strategy

When 40-70% overlap:

1. Identify duplicate sections
2. Decide which file is authoritative
3. Remove duplicates from non-authoritative file
4. Add cross-references

### Cross-Reference Format

```markdown
See [{topic}](references/{file}.md) for details on {specific topic}.
```

## Marketplace-Wide Scanning

For thorough duplication check, scan all bundles:

```bash
# List all reference files
find marketplace/bundles -name "*.md" -path "*/references/*"
find marketplace/bundles -name "*.md" -path "*/standards/*"
```

Check each for:
- Same section headings
- Similar code examples
- Overlapping concepts

## Best Practices

### Single Source of Truth

- Each concept should have ONE authoritative source
- Other files reference, not duplicate
- Update source, references stay current

### Appropriate Load Type

| Content Type | Load Type |
|--------------|-----------|
| Core standards | always |
| Domain-specific | conditional |
| Specialized knowledge | on-demand |
| Rarely-used references | on-demand |

### File Naming

Use descriptive kebab-case:
- `java-testing-patterns.md`
- `api-security-guide.md`
- `deployment-best-practices.md`

### Size Guidelines

| Size | Recommendation |
|------|----------------|
| <100 lines | May be too small - consider merging |
| 100-600 lines | Ideal range |
| 600-1000 lines | Consider splitting |
| >1000 lines | Split into multiple references |

## Error Handling

### Content Not Found

```
Error: Content file not found: {path}
Resolution: Verify file path is correct
```

### Skill Not Found

```
Error: Skill directory not found: {path}
Resolution: Verify skill path exists
```

### No References Directory

Script handles gracefully:
- Reports "No existing references directory found"
- Recommends proceeding (no duplication possible)

## Reporting

After adding knowledge, report:
- File created: `{skill}/references/{name}.md`
- Lines: {count}
- Duplication check: {result}
- SKILL.md updated: {yes/no}

## See Also

- `component-update-guide.md` - Updating components
- `readme-maintenance-guide.md` - README updates
