# README Maintenance Guide

Guide for maintaining README files across marketplace bundles.

## README Maintenance Principles

READMEs should:
- Accurately reflect current components
- Use descriptions from component frontmatter
- Follow consistent formatting
- Be auto-generated where possible

## Using generate-readme.sh

Generate README content for a bundle:

```bash
scripts/generate-readme.sh {bundle_path}
```

**Output Fields**:
- `bundle_name`: Name from plugin.json
- `components`: Counts of commands, agents, skills
- `readme_content`: Generated markdown
- `commands/agents/skills`: Arrays with names and descriptions

## Generated README Structure

```markdown
# {Bundle Name}

## Commands

- **{command-name}** - {description from frontmatter}

## Agents

- **{agent-name}** - {description from frontmatter}

## Skills

- **{skill-name}** - {description from frontmatter}

## Installation

Add to your Claude Code settings or install via marketplace.
```

## Frontmatter as Source of Truth

Descriptions come from component YAML frontmatter:

```yaml
---
name: my-component
description: This description appears in README
---
```

**If no description**: Shows "No description"

## Bundle README.md Format

### Standard Sections

1. **Title**: Bundle name as H1
2. **Description**: Brief bundle overview (optional, manual)
3. **Commands**: List with descriptions
4. **Agents**: List with descriptions
5. **Skills**: List with descriptions
6. **Installation**: Standard installation text

### Component List Format

```markdown
## Commands

- **command-name** - Description from frontmatter
- **another-command** - Another description
```

### Alphabetical Ordering

Components listed alphabetically by name for consistency.

## Comparing Generated vs Existing

### Detecting Changes

Compare generated content with existing README:

1. **Missing Components**: In actual but not documented
2. **Obsolete Components**: In documented but not actual
3. **Description Mismatches**: README differs from frontmatter

### Manual Edits Detection

Check for content not matching generated pattern:
- Custom sections (not Commands/Agents/Skills)
- Modified descriptions
- Additional documentation

## Handling Manual Edits

### force=false (Default)

If manual edits detected:
1. Display what will change
2. Ask user: Update, Skip, or Force
3. Preserve manual sections if updating

### force=true

Overwrite README entirely with generated content.

**Warning**: Manual edits will be lost.

## Multi-Bundle Processing

When processing all bundles:

```
For each bundle in marketplace/bundles/:
  1. Generate README content
  2. Compare with existing
  3. Apply updates if needed
  4. Report results
```

### Progress Reporting

```
[UPDATE] bundle-name/README.md
  ✓ Added 2 missing components
  ✓ Removed 1 obsolete component
  ✓ Updated 3 descriptions
```

## Project Root README

### Project README.adoc

The project root has README.adoc (AsciiDoc format):
- Lists all bundles
- Provides project overview
- Links to bundle READMEs

### AsciiDoc Formatting

```asciidoc
== Marketplace Bundles

* xref:marketplace/bundles/bundle-name/README.md[Bundle Name] - Description
* xref:marketplace/bundles/another/README.md[Another Bundle] - Description
```

### Keeping Root Updated

When bundles added/removed:
1. Update bundle listings
2. Update descriptions
3. Maintain alphabetical order

## Error Handling

### Missing plugin.json

```
Error: Missing plugin.json in bundle: {path}
Resolution: Bundle must have plugin.json
```

### Read Failures

If bundle README can't be read:
- Log warning
- Continue with next bundle
- Report failure in summary

### Edit Failures

If README update fails:
- Log detailed error
- Track in `failed_updates`
- Continue with remaining bundles
- Report all failures at end

## Statistics Tracking

Track throughout workflow:
- `bundles_discovered`: Total bundles found
- `bundles_analyzed`: Successfully examined
- `readmes_updated`: Files modified
- `components_added`: Missing components added
- `components_removed`: Obsolete removed
- `descriptions_updated`: Descriptions corrected
- `failed_updates`: Edit failures

## Best Practices

### Consistent Formatting

- Use markdown list format for components
- Maintain alphabetical ordering
- Keep descriptions concise (one line)

### Description Quality

Good descriptions:
- Start with verb or noun
- Explain what component does
- Avoid implementation details
- ~10-15 words maximum

### Regular Maintenance

Run README maintenance:
- After adding/removing components
- After updating component descriptions
- As part of release process

## Reporting

### Success Report

```
README Maintenance Summary
==========================
Bundles processed: 5
READMEs updated: 3
  Components added: 7
  Components removed: 2
  Descriptions updated: 4
Documentation Status: UP-TO-DATE
```

### With Failures

```
README Maintenance Summary
==========================
...
⚠️ Failed Updates:
  - bundle-name: Edit failed - no match found

Next Steps:
  1. Review error messages
  2. Manually fix failed updates
  3. Re-run maintenance
```

## See Also

- `component-update-guide.md` - Updating components
- `knowledge-management-guide.md` - Adding knowledge
