# Skill Creation Guide

Quick-reference guide for creating marketplace skills. This document provides component-type decision guidance and a validation checklist. Detailed content lives in dedicated documents:

- **Creation workflow** (step-by-step procedure): See `standards/workflow-create-skill.md`
- **Design principles** (workflows, composition, progressive disclosure): See `plugin-architecture:references/skill-design.md`
- **Architecture patterns**: See `plugin-architecture:skill-patterns`
- **Frontmatter specification**: See `plugin-architecture:frontmatter-standards`

## When to Create Skills vs Other Components

### Create a Skill When:
- **Knowledge provision** - Providing standards, guidelines, or reference material
- **Progressive disclosure** - Large body of knowledge loaded on-demand
- **Reusable standards** - Multiple commands/agents will reference this knowledge

### Create a Command Instead When:
- **User invocation** - Users run directly with `/command-name`
- **Interactive workflow** - Gathering requirements through questionnaires

### Create an Agent Instead When:
- **Autonomous execution** - Performing specific task after launch
- **Tool usage** - Needs tools to accomplish work

## Skill Types and Directory Patterns

### Standards Skill
```
skill-name/
├── SKILL.md
└── standards/
    ├── category-1.md
    └── category-2.md
```

### Reference Skill
```
skill-name/
├── SKILL.md
└── references/
    ├── guide-1.md
    └── examples/
```

### Diagnostic Skill
```
skill-name/
├── SKILL.md
├── scripts/
│   └── analyze.py
└── references/
    └── interpretation-guide.md
```

## Validation Checklist

Before creating skill, verify:

- Name is kebab-case and descriptive
- Description is <100 chars
- `user-invocable` field present (true or false)
- No `tools`, `allowed-tools`, `model`, or `color` fields in frontmatter
- SKILL.md is 400-800 lines (not bloated)
- All resource paths use relative paths
- Progressive disclosure implemented
- No CONTINUOUS IMPROVEMENT RULE (skills are knowledge repositories, not executors)

For complete quality rules, see `plugin-doctor:skills-guide`.

## References

- Core Principles: See `plugin-architecture:core-principles`
- Skill Patterns: See `plugin-architecture:skill-patterns`
- Execution Directives: See `plugin-architecture:execution-directive`
- Frontmatter Spec: See `plugin-architecture:frontmatter-standards`
- Quality Validation: See `plugin-doctor:skills-guide`
