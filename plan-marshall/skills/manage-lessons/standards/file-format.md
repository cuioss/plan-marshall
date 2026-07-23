# Lessons Learned File Format

Storage format specification for global lessons learned.

## Storage Location

```text
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
```text

## Metadata Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | string | Unique identifier matching filename without `.md` extension |
| `component` | Yes | string | Component that the lesson applies to (e.g., `maven-build`, `plan-files`) |
| `category` | Yes | string | One of: `bug`, `improvement`, `anti-pattern`, `arch-constraint`. The first three match the promotable finding types in `manage-findings/standards/jsonl-format.md`; `arch-constraint` is the exception — it is fed by the lessons-housekeeping machinery from recurring `arch-gate` violations (not by finding promotion) and follows a distinct rule-identity dedup + retire-on-quiet lifecycle (see below) |
| `created` | Yes | string | Creation date in `YYYY-MM-DD` format |
| `bundle` | No | string | Bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |
| `rule` | Conditional | string | Rule identity for `arch-constraint` lessons (the structural rule the arch-gate violation references). Required for `arch-constraint`; it is the dedup key — at most one active `arch-constraint` lesson exists per rule. Absent for other categories. |
| `recurrence_count` | Conditional | string | Integer (stored as string) for `arch-constraint` lessons: `1` on creation, bumped by one on each reinforce-on-recurrence. Absent for other categories. |
| `last_seen` | Conditional | string | `YYYY-MM-DD` of the most recent observation for `arch-constraint` lessons: set to `created` on creation, refreshed on each reinforce. Anchors the retire-on-quiet window. Absent for other categories. |

### Category Definitions

| Category | When to Use |
|----------|-------------|
| `bug` | Script is broken or produces wrong results |
| `improvement` | Script works but could be better |
| `anti-pattern` | Script was misused or documentation unclear |
| `arch-constraint` | A recurring architectural-boundary violation surfaced by `arch-gate` (ArchUnit / import-linter / dependency-cruiser). Deduped by `rule` identity; reinforced on recurrence; retired on quiet |

### arch-constraint lifecycle (rule-identity dedup, retire-on-quiet)

`arch-constraint` lessons follow a distinct lifecycle from the other three categories — deliberately NOT the promote-to-skill path:

- **Rule-identity dedup.** `manage-lessons add --category arch-constraint --rule {id}` looks up an active `arch-constraint` lesson with the same `rule`. If none exists, a new lesson is allocated carrying `rule`, `recurrence_count=1`, and `last_seen={created}`. The `--rule` flag is mandatory for this category.
- **Reinforce-on-recurrence.** When an active lesson already covers the rule, the add REINFORCES it instead of allocating a new one: `recurrence_count` is bumped, `last_seen` is refreshed to today, and a `## Recurrence — {date}` body section is appended (the same `## Recurrence —` marker the `aggregate` verb counts). The add returns the existing lesson's id with `action: reinforced`.
- **Retire-on-quiet.** `manage-lessons retire-quiet [--quiet-days N] [--dry-run]` retires every active `arch-constraint` lesson whose `last_seen` is at least `N` days old (the rule has stayed quiet). Retirement writes a tombstone and unlinks the `.md`, mirroring `cleanup-superseded`. The window resolves from `--quiet-days`, then `system.retention.arch_constraint_quiet_days` in marshal.json, then a hard fallback. A reinforced lesson's refreshed `last_seen` resets the quiet clock.

These lessons surface through the existing architecture-hints pipe; no new surfacing mechanism is introduced.

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
