# Bundle Creation Guide

Comprehensive guide for creating marketplace bundles with proper structure, plugin.json configuration, and documentation.

## What is a Bundle?

A **bundle** is a collection of related marketplace components (agents, commands, skills) packaged together with metadata.

**Bundle Structure**:
```
bundle-name/
├── plugin.json           (Metadata and component registry)
├── README.md             (Bundle documentation)
├── agents/               (Agent components)
│   └── README.md
├── commands/             (Command components)
│   └── README.md
└── skills/               (Skill components)
    └── README.md
```

## When to Create a New Bundle

### Create a New Bundle When:
- **New domain** - Covering a distinct technical domain (Java, Frontend, Documentation)
- **Logical grouping** - Components serve related user goals
- **Independent distribution** - Bundle can be used independently
- **Clear ownership** - Single team/maintainer responsible

### Add to Existing Bundle When:
- **Related domain** - Fits existing bundle's scope
- **Extends existing** - Enhances current bundle capabilities
- **Shared dependencies** - Uses same skills as existing components

**Examples**:

✅ **New Bundle** (distinct domain):
```
pm-dev-java         (Java development)
pm-dev-frontend     (Frontend development)
pm-documents (Documentation)
```

✅ **Add to Existing** (related):
```
pm-dev-java/
├── skills/
│   ├── cui-java-core  (existing)
│   └── cui-java-advanced  (NEW - add to existing bundle)
```

## Bundle Structure Requirements

### Required Directories

All three directories must exist (even if empty):

```
bundle-name/
├── agents/
├── commands/
└── skills/
```

**Why**: Marketplace expects consistent structure. Empty directories are fine.

### Required Files

**plugin.json** - Bundle metadata:
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

**README.md** - Bundle documentation:
```markdown
# Bundle Name

[Overview paragraph]

## What This Bundle Provides

[Bullet list of capabilities]

## Components

[List of agents, commands, skills]

## Installation

[How to install]

## Usage Examples

[Common usage patterns]
```

### Optional Files

**Component READMEs**:
- `agents/README.md` - Overview of agents
- `commands/README.md` - Overview of commands
- `skills/README.md` - Overview of skills

**Additional docs**:
- `CHANGELOG.md` - Version history
- `CONTRIBUTING.md` - Contribution guidelines
- `LICENSE` - License information

## plugin.json Configuration

### Required Fields

```json
{
  "name": "bundle-name",           // kebab-case, unique identifier
  "display_name": "Display Name",  // Human-readable name
  "description": "Brief description", // One sentence
  "version": "1.0.0",              // Semantic version
  "author": "Author Name",         // Bundle maintainer
  "components": []                 // Component registry (initially empty)
}
```

### Field Specifications

**name**:
- Format: kebab-case
- Must be unique across marketplace
- Example: `java-development-standards`

**display_name**:
- Format: Title Case or natural language
- User-friendly name
- Example: "Java Development Standards"

**description**:
- Format: One sentence
- Concise purpose statement
- Example: "Comprehensive Java development standards and tools"

**version**:
- Format: Semantic versioning (MAJOR.MINOR.PATCH)
- Start with: `1.0.0`
- Example: `1.2.3`

**author**:
- Format: Person or organization name
- Example: "Development Team"

**components**:
- Format: Array of component objects
- Initially empty: `[]`
- Updated as components are added

### Components Array Format

```json
{
  "components": [
    {
      "type": "agent",
      "name": "agent-name",
      "path": "agents/agent-name.md"
    },
    {
      "type": "command",
      "name": "command-name",
      "path": "commands/command-name.md"
    },
    {
      "type": "skill",
      "name": "skill-name",
      "path": "skills/skill-name"
    }
  ]
}
```

### Updating Components Array

After creating components, update plugin.json:

```bash
# Read current plugin.json
current=$(cat bundle/plugin.json)

# Add new component
jq '.components += [{"type": "agent", "name": "new-agent", "path": "agents/new-agent.md"}]' \
  bundle/plugin.json > bundle/plugin.json.tmp

# Replace file
mv bundle/plugin.json.tmp bundle/plugin.json
```

## Bundle Types

### Type 1: Standards Bundle

**Purpose**: Provide development standards and guidelines

**Example**: `pm-dev-java`
```
pm-dev-java/
├── plugin.json
├── README.md
├── skills/
│   ├── cui-java-core/
│   ├── cui-java-cdi/
│   └── cui-javadoc/
└── commands/  (mostly empty, few diagnostic commands)
```

**Characteristics**:
- Heavy on skills (standards)
- Few commands (mostly diagnostic)
- Minimal agents

### Type 2: Tool Bundle

**Purpose**: Provide commands and agents for tasks

**Example**: `plan-marshall`
```
plan-marshall/
├── plugin.json
├── README.md
├── commands/
│   ├── tool-1.md
│   └── tool-2.md
├── agents/
│   ├── agent-1.md
│   └── agent-2.md
└── skills/
    └── general-rules/  (supporting knowledge)
```

**Characteristics**:
- Heavy on commands/agents (tools)
- Minimal skills (supporting knowledge only)

### Type 3: Mixed Bundle

**Purpose**: Combination of standards and tools

**Example**: `pm-plugin-development`
```
pm-plugin-development/
├── plugin.json
├── README.md
├── skills/
│   ├── plugin-architecture/    (standards)
│   └── plugin-create/          (templates + scripts)
├── commands/
│   ├── plugin-create-agent.md  (tools)
│   └── plugin-diagnose-*.md
└── agents/
    └── analysis-agents.md
```

**Characteristics**:
- Balanced skills, commands, agents
- Standards + tools working together

## README.md Requirements

### Required Sections

```markdown
# Bundle Name

Brief overview paragraph explaining bundle purpose.

## What This Bundle Provides

Bullet list of main capabilities:
- Capability 1
- Capability 2
- Capability 3

## Components

### Skills
- **skill-name** - Description

### Commands
- **/command-name** - Description

### Agents
- **agent-name** - Description

## Installation

[Installation instructions]

## Usage Examples

[Common usage patterns with examples]

## Integration Notes

[How this bundle works with others]
```

### Optional Sections

```markdown
## Prerequisites

[Required setup or dependencies]

## Configuration

[Bundle-specific configuration]

## Best Practices

[Recommended usage patterns]

## Troubleshooting

[Common issues and solutions]

## Contributing

[Contribution guidelines]

## License

[License information]
```

### README Generation Guidelines

**Keep It Concise**:
- Overview: 2-3 paragraphs
- Component descriptions: 1 sentence each
- Examples: 3-5 practical examples

**Trust AI**:
Don't embed 300-line README template. Let AI generate appropriate content based on bundle type and components.

**Avoid Duplication**:
Don't repeat component documentation. Link to component files:
```markdown
### Commands

- **/plugin-create-agent** - Create new agents. See [plugin-create-agent.md](commands/plugin-create-agent.md) for details.
```

## Naming Conventions

### Bundle Naming

**Format**: `{domain}-{type}`

**Examples**:
- `java-development-standards` (domain: java, type: standards)
- `frontend-tools` (domain: frontend, type: tools)
- `documentation-standards` (domain: documentation, type: standards)

**Rules**:
- Use kebab-case
- Start with domain/technology
- End with type (standards, tools, expert)
- Be specific but concise

### Display Name

**Format**: Natural language, Title Case

**Examples**:
- Bundle name: `java-development-standards`
- Display name: "Java Development Standards"

or

- Bundle name: `plan-marshall`
- Display name: "CUI Utilities"

## Component Organization

### Organize by Type

Group components by type (agents/, commands/, skills/):

```
bundle/
├── agents/
│   ├── analyzer-agent.md
│   └── builder-agent.md
├── commands/
│   ├── create-component.md
│   └── diagnose-issues.md
└── skills/
    ├── standards-skill/
    └── patterns-skill/
```

**Don't** organize by feature:
```
❌ bundle/
    ├── feature-a/
    │   ├── agent.md
    │   ├── command.md
    │   └── skill/
    └── feature-b/
```

### Component Naming

**Within Bundle**:
- Agent names: `{purpose}-agent` (e.g., `code-analyzer`)
- Command names: `{verb}-{noun}` (e.g., `create-agent`)
- Skill names: `{domain}-{topic}` (e.g., `java-core`)

**Cross-Bundle References**:
- Use fully qualified: `bundle-name:component-name`
- Example: `pm-dev-java:java-core`

## Bundle Creation Workflow

### Step 1: Plan Bundle

Decide:
- Bundle name and display name
- Bundle type (standards/tools/mixed)
- Initial components to create
- Author and version

### Step 2: Create Structure

```bash
mkdir -p bundle-name/{agents,commands,skills}
```

### Step 3: Create plugin.json

```json
{
  "name": "bundle-name",
  "display_name": "Display Name",
  "description": "Brief description",
  "version": "1.0.0",
  "author": "Author Name",
  "components": []
}
```

### Step 4: Create Bundle README

Generate README with required sections.

### Step 5: Create Component READMEs (Optional)

```markdown
# Agents

This bundle provides the following agents:

[List agents with brief descriptions]

## Usage

[How to use agents in this bundle]
```

Repeat for commands/ and skills/.

### Step 6: Create Initial Components

Use component creation workflows:
- `/plugin-create-agent` for agents
- `/plugin-create-command` for commands
- `/plugin-create-skill` for skills

### Step 7: Update plugin.json

After creating each component, add to components array.

### Step 8: Validate Metadata

Run diagnosis:
```
/plugin-diagnose-metadata
```

Fix any issues found.

## Validation Checklist

Before releasing bundle, verify:

- [ ] Bundle name is kebab-case and descriptive
- [ ] Display name is human-readable
- [ ] Description is concise (<100 chars)
- [ ] Version follows semantic versioning
- [ ] All three directories exist (agents/, commands/, skills/)
- [ ] plugin.json is valid JSON
- [ ] plugin.json has all required fields
- [ ] Components array is up-to-date
- [ ] README.md has required sections
- [ ] Component READMEs exist (if bundle has >3 components per type)
- [ ] No broken component references
- [ ] Bundle is self-contained

## Common Pitfalls

### Pitfall 1: Invalid plugin.json

❌ **Wrong**: Malformed JSON
```json
{
  "name": "bundle-name",
  "version": "1.0.0"  // Missing comma
  "author": "Me"
}
```

✅ **Correct**: Valid JSON
```json
{
  "name": "bundle-name",
  "version": "1.0.0",
  "author": "Me"
}
```

### Pitfall 2: Outdated Components Array

❌ **Wrong**: Created 5 components but plugin.json lists 2

✅ **Correct**: Update plugin.json after each component creation

### Pitfall 3: Missing Directories

❌ **Wrong**:
```
bundle/
├── plugin.json
└── skills/  // Missing agents/ and commands/
```

✅ **Correct**:
```
bundle/
├── plugin.json
├── agents/
├── commands/
└── skills/
```

### Pitfall 4: Inconsistent Naming

❌ **Wrong**:
- Bundle name: `java-tools`
- Display name: "JavaScript Utilities"  // Mismatch!

✅ **Correct**:
- Bundle name: `java-tools`
- Display name: "Java Development Tools"  // Consistent

### Pitfall 5: Massive README

❌ **Wrong**: 500-line README with component documentation duplicated

✅ **Correct**: Concise README linking to component files

## Bundle Scope Guidelines

### Good Scope (Focused)

✅ **java-development-standards**:
- Java coding standards
- Java testing patterns
- Java documentation
- Java build practices

**Rationale**: All related to Java development

### Bad Scope (Unfocused)

❌ **development-standards**:
- Java standards
- JavaScript standards
- Python standards
- Go standards
- Ruby standards
- ...

**Rationale**: Too broad, should be separate bundles

### Right Size

**Small Bundle** (5-10 components):
```
plan-marshall/
├── 2 agents
├── 3 commands
└── 2 skills
```
✅ Good - focused bundle

**Medium Bundle** (10-20 components):
```
pm-dev-java/
├── 3 agents
├── 7 commands
└── 8 skills
```
✅ Good - comprehensive domain coverage

**Large Bundle** (20-40 components):
```
pm-plugin-development/
├── 12 agents
├── 15 commands
└── 8 skills
```
✅ Acceptable - complex domain with many tools

**Too Large** (40+ components):
```
all-tools-bundle/
├── 25 agents
├── 30 commands
└── 20 skills
```
❌ Too large - split into focused bundles

## Examples

### Example 1: Standards Bundle

```json
{
  "name": "css-development-standards",
  "display_name": "CSS Development Standards",
  "description": "Modern CSS standards covering essentials, responsive design, and quality practices",
  "version": "1.0.0",
  "author": "Frontend Team",
  "components": [
    {
      "type": "skill",
      "name": "cui-css",
      "path": "skills/cui-css"
    },
    {
      "type": "command",
      "name": "validate-css",
      "path": "commands/validate-css.md"
    }
  ]
}
```

### Example 2: Tool Bundle

```json
{
  "name": "testing-tools",
  "display_name": "Testing Tools",
  "description": "Automated testing tools for running tests and generating coverage reports",
  "version": "1.0.0",
  "author": "QA Team",
  "components": [
    {
      "type": "agent",
      "name": "test-runner",
      "path": "agents/test-runner.md"
    },
    {
      "type": "agent",
      "name": "coverage-analyzer",
      "path": "agents/coverage-analyzer.md"
    },
    {
      "type": "command",
      "name": "run-tests",
      "path": "commands/run-tests.md"
    },
    {
      "type": "command",
      "name": "generate-coverage",
      "path": "commands/generate-coverage.md"
    }
  ]
}
```

### Example 3: Mixed Bundle

```json
{
  "name": "pm-plugin-development",
  "display_name": "CUI Plugin Development Tools",
  "description": "Tools and standards for creating marketplace components",
  "version": "2.0.0",
  "author": "Marketplace Team",
  "components": [
    {
      "type": "skill",
      "name": "plugin-architecture",
      "path": "skills/plugin-architecture"
    },
    {
      "type": "skill",
      "name": "plugin-create",
      "path": "skills/plugin-create"
    },
    {
      "type": "command",
      "name": "plugin-create-agent",
      "path": "commands/plugin-create-agent.md"
    },
    {
      "type": "command",
      "name": "plugin-diagnose-agents",
      "path": "commands/plugin-diagnose-agents.md"
    },
    {
      "type": "agent",
      "name": "component-analyzer",
      "path": "agents/component-analyzer.md"
    }
  ]
}
```

## References

- Bundle Structure: See marketplace architecture standards
- plugin.json Schema: See metadata standards
- Component Organization: See plugin-architecture skill
