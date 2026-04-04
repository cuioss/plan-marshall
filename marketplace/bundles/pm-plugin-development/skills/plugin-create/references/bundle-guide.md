# Bundle Creation Guide

Guide for creating marketplace bundles with proper structure and plugin.json configuration. For architecture principles, see `plugin-architecture:goal-based-organization`.

## What is a Bundle?

A **bundle** is a collection of related marketplace components (agents, commands, skills) packaged together with metadata.

```
bundle-name/
├── plugin.json           (Metadata and component registry)
├── README.md             (Bundle documentation)
├── agents/               (Agent components)
├── commands/             (Command components)
└── skills/               (Skill components)
```

## When to Create a New Bundle

### Create a New Bundle When:
- **New domain** - Covering a distinct technical domain (Java, Frontend, Documentation)
- **Logical grouping** - Components serve related user goals
- **Independent distribution** - Bundle can be used independently

### Add to Existing Bundle When:
- **Related domain** - Fits existing bundle's scope
- **Extends existing** - Enhances current bundle capabilities

## Bundle Structure Requirements

### Required Directories
All three directories must exist (even if empty): `agents/`, `commands/`, `skills/`

### Required Files

**plugin.json**:
```json
{
  "name": "bundle-name",
  "display_name": "Human Readable Name",
  "description": "Brief description",
  "version": "1.0.0",
  "author": "Author Name",
  "components": []
}
```

**README.md** with sections: overview, capabilities, components list, installation, usage examples.

## plugin.json Configuration

### Required Fields

| Field | Format | Example |
|-------|--------|---------|
| `name` | kebab-case, unique | `java-development-standards` |
| `display_name` | Title Case | `"Java Development Standards"` |
| `description` | One sentence | `"Comprehensive Java development standards"` |
| `version` | Semantic versioning | `"1.0.0"` |
| `author` | Person/organization | `"Development Team"` |
| `components` | Array (initially `[]`) | See below |

### Components Array Format

```json
{
  "components": [
    {"type": "agent", "name": "agent-name", "path": "agents/agent-name.md"},
    {"type": "command", "name": "command-name", "path": "commands/command-name.md"},
    {"type": "skill", "name": "skill-name", "path": "skills/skill-name"}
  ]
}
```

Update this array after creating each component.

## Bundle Types

| Type | Characteristics | Example |
|------|----------------|---------|
| **Standards** | Heavy on skills, few commands | `pm-dev-java` |
| **Tool** | Heavy on commands/agents | `plan-marshall` |
| **Mixed** | Balanced skills + tools | `pm-plugin-development` |

## Bundle Scope Guidelines

- **Small** (5-10 components): Focused bundle — good
- **Medium** (10-20 components): Comprehensive domain — good
- **Large** (20-40 components): Complex domain — acceptable
- **Too Large** (40+): Split into focused bundles

## Naming Conventions

- **Bundle name**: kebab-case, domain-first (e.g., `pm-dev-java`)
- **Display name**: Title Case, natural language
- **Agent names**: `{purpose}` (e.g., `code-analyzer`)
- **Command names**: `{verb}-{noun}` (e.g., `create-agent`)
- **Skill names**: `{domain}-{topic}` (e.g., `java-core`)
- **Cross-bundle refs**: `bundle-name:component-name`

## Bundle Creation Workflow

1. **Plan** — Decide name, type, initial components
2. **Create structure** — `mkdir -p bundle-name/{agents,commands,skills}`
3. **Create plugin.json** — With required fields and empty components
4. **Create README.md** — With required sections
5. **Create components** — Use `/plugin-create` workflows
6. **Update plugin.json** — Add each component to array
7. **Validate** — Run `/plugin-doctor` to check

## Validation Checklist

- Bundle name is kebab-case and descriptive
- Display name matches bundle domain
- Description is <100 chars
- All three directories exist
- plugin.json is valid JSON with all required fields
- Components array is up-to-date
- README.md has required sections
- No broken component references

For metadata validation rules, see `plugin-doctor:metadata-guide`.

## References

- Goal-Based Organization: See `plugin-architecture:goal-based-organization`
- Component Organization: See `plugin-architecture:core-principles`
- Metadata Validation: See `plugin-doctor:metadata-guide`
