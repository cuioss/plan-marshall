# Skill Creation Guide

Guide for creating well-structured marketplace skills. For architecture principles, see `plugin-architecture:core-principles`. For pattern selection, see `plugin-architecture:skill-patterns`.

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

## Skill Design Principles

### Progressive Disclosure
Load knowledge on-demand, not all at once. See `plugin-architecture:core-principles` for the three-level loading system (frontmatter → SKILL.md → references).

### Relative Path Pattern
All resource paths use relative paths for portability:
- PASS: `Read references/guide.md`
- FAIL: `Read ~/.claude/skills/my-skill/references/guide.md`

### Resource Organization
```
skill-name/
├── SKILL.md              (Overview and loading guidance)
├── scripts/              (Executable automation - Python/Bash)
├── references/           (Documentation loaded on-demand)
└── assets/               (Templates, binaries, images)
```

## Skill Patterns

Reference the 10 patterns from `plugin-architecture:skill-patterns`:

1. **Script Automation** — Execute scripts, Claude interprets
2. **Read-Process-Write** — Transform files through pipeline
3. **Search-Analyze-Report** — Grep → Read → Analyze → Report
4. **Command Chain** — Sequential stages with dependencies
5. **Wizard-Style** — Interactive questions with preview
6. **Template-Based** — Fill templates with generated data
7. **Iterative Refinement** — Broad scan → deep dive selected items
8. **Context Aggregation** — Gather from multiple sources → synthesize
9. **Validation Pipeline** — Multi-stage validation
10. **Reference Library** — Pure documentation, no execution

**Most Common**: Pattern 10 (standards), Pattern 1 (diagnostic), Pattern 3 (analysis).

## Frontmatter Format

Skills use only `name`, `description`, and `user-invocable` in frontmatter. They do NOT support `tools`, `allowed-tools`, `model`, or `color` fields. See `plugin-architecture:frontmatter-standards` for the complete specification.

```yaml
---
name: skill-name
description: One sentence description
user-invocable: true
---
```

## SKILL.md Structure

### For Execution Skills (Patterns 1-9)

```markdown
---
name: skill-name
description: One sentence (<100 chars)
user-invocable: true
---

# Skill Name

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize
these instructions to the user. IMMEDIATELY begin the workflow below.

## Workflow Decision Tree

**MANDATORY**: Select workflow based on input and execute IMMEDIATELY.

### If [condition A]
→ **EXECUTE** Workflow 1

### If [condition B]
→ **EXECUTE** Workflow 2

## Workflow 1: [Name]
[Steps...]
```

See `plugin-architecture:execution-directive` for EXECUTION MODE and MANDATORY marker patterns.

### For Reference Skills (Pattern 10)

```markdown
---
name: skill-name
description: One sentence
user-invocable: false
---

# Skill Name

## What This Skill Provides
[3-5 bullet points]

## Standards Organization
[List of available resources with loading guidance]
```

No EXECUTION MODE directive needed for pure reference skills.

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

## No CONTINUOUS IMPROVEMENT RULE for Skills

Skills are knowledge repositories, not executors. Only agents and commands have the CONTINUOUS IMPROVEMENT RULE.

## Creating Standards Files

### Template
```markdown
# {Topic}

Brief description.

## Standards

### Standard 1: {Name}
**Rule**: [Clear rule statement]
**Rationale**: [Why this rule exists]

PASS **Good**: [example]
FAIL **Bad**: [counter-example]

## Common Pitfalls
[Mistakes to avoid]
```

### Size Guidelines
- **Target**: 200-600 lines per file
- **Too small**: <100 lines (merge with related standards)
- **Too large**: >1000 lines (split into focused files)

## Validation Checklist

Before creating skill, verify:

- Name is kebab-case and descriptive
- Description is <100 chars
- `user-invocable` field present (true or false)
- No `tools`, `allowed-tools`, `model`, or `color` fields in frontmatter
- SKILL.md is 400-800 lines (not bloated)
- All resource paths use relative paths
- Progressive disclosure implemented
- No CONTINUOUS IMPROVEMENT RULE

For complete quality rules, see `plugin-doctor:skills-guide`.

## References

- Core Principles: See `plugin-architecture:core-principles`
- Skill Patterns: See `plugin-architecture:skill-patterns`
- Execution Directives: See `plugin-architecture:execution-directive`
- Frontmatter Spec: See `plugin-architecture:frontmatter-standards`
- Quality Validation: See `plugin-doctor:skills-guide`
