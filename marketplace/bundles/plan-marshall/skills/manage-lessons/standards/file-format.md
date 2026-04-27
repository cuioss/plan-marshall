# Lessons Learned File Format

Storage format specification for global lessons learned.

## Storage Location

```
.plan/lessons-learned/
  2025-12-02-001.md
  2025-12-02-002.md
  ...
```

Lessons are global (not plan-scoped) and persist across plans.

## File Naming Convention

Format: `{YYYY-MM-DD}-{sequence}.md`

- Date is the creation date
- Sequence is a zero-padded 3-digit number starting at 001
- Sequence resets per day (each day starts at 001)

Examples: `2025-12-02-001.md`, `2025-12-02-002.md`, `2026-01-15-001.md`

## File Structure

Markdown with key=value metadata header (no YAML frontmatter):

```markdown
id=2025-12-02-001
component=maven-build
category=bug
created=2025-12-02
bundle=pm-dev-java

# Build fails with missing dependency

When running `mvn clean install`, the build fails with a missing
dependency error for `jakarta.json-api`.

## Solution

Add the dependency explicitly to pom.xml:

```xml
<dependency>
    <groupId>jakarta.json</groupId>
    <artifactId>jakarta.json-api</artifactId>
</dependency>
```

## Impact

This affects all projects using jakarta.json without explicit dependency.
```

## Metadata Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | string | Unique identifier matching filename without `.md` extension |
| `component` | Yes | string | Component that the lesson applies to (e.g., `maven-build`, `plan-files`) |
| `category` | Yes | string | One of: `bug`, `improvement`, `anti-pattern`. These values match the promotable finding types in `manage-findings/standards/jsonl-format.md` |
| `created` | Yes | string | Creation date in `YYYY-MM-DD` format |
| `bundle` | No | string | Bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |

### Category Definitions

| Category | When to Use |
|----------|-------------|
| `bug` | Script is broken or produces wrong results |
| `improvement` | Script works but could be better |
| `anti-pattern` | Script was misused or documentation unclear |

## Content Sections

After the metadata header, lessons follow standard markdown:

| Section | Required | Purpose |
|---------|----------|---------|
| `# Title` | Yes | Descriptive title of the lesson |
| Body text | Yes | Description of the problem or discovery |
| `## Solution` | No | How the issue was resolved |
| `## Impact` | No | Scope of the lesson's applicability |

## Metadata Parsing

The metadata header uses simple `key=value` format (one per line, no quoting). The header ends at the first blank line. Lines after the blank line are treated as markdown content.

## Lesson Lifecycle

Unapplied lesson files live at `.plan/local/lessons-learned/{id}.md`. A lesson becomes "applied" by being moved into a plan directory as `.plan/local/plans/{plan_id}/lesson-{id}.md` via `manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_id}`. The on-disk location is the source of truth for lifecycle state — there is no `applied` metadata field.
