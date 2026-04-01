---
name: plugin-architecture
description: Architecture principles, skill patterns, and design guidance for building goal-based marketplace components
user-invocable: false
---

# Plugin Architecture Skill

**REFERENCE MODE**: This skill provides reference material. Load specific references on-demand based on current task. Do not load all references at once.

Pure reference skill providing architecture principles, skill patterns, and design guidance for building goal-based marketplace components.

## What This Skill Provides

**Architecture Foundation**: Core principles for building marketplace components that follow skills best practices and goal-based organization.

**Skill Patterns**: 10 implementation patterns for building different types of skills (automation, analysis, validation, etc.).

**Design Guidance**: Workflow-focused skill design, thin orchestrator commands, and proper resource organization.

## Pattern Type

**Pattern 10: Reference Library** - Pure reference skill with no execution logic. Load references on-demand based on current task.

## When to Use This Skill

Activate when:
- **Creating new marketplace components** - Agents, commands, skills, or bundles
- **Refactoring existing components** - Migrating to goal-based architecture
- **Reviewing component design** - Ensuring architecture compliance
- **Learning marketplace architecture** - Understanding principles and patterns

## Core Concepts

### Goal-Based Organization

**Principle**: Organize by WHAT users want to accomplish (goals), not by WHAT component operates on (types).

**User Goals**:
- **CREATE** - Create new marketplace components
- **DOCTOR** - Diagnose and fix quality issues (unified workflow)
- **MAINTAIN** - Keep marketplace healthy
- **ANALYZE** - Investigate failures and permission prompts

### Progressive Disclosure

**Principle**: Minimize initial context load, load details on-demand.

**Levels**:
1. **Frontmatter** - Minimal metadata (~3 lines)
2. **SKILL.md** - Full instructions (~400-800 lines)
3. **References** - Detailed content (thousands of lines, loaded when needed)

### Relative Path Pattern

**Principle**: All resource paths use relative paths from the skill directory for portability across installations.

**Examples**:
```
Read references/core-principles.md
bash scripts/analyzer.py
Load template: assets/template.html
```

When a skill is loaded, Claude knows its installation directory and resolves relative paths from there.

## Available References

Load references progressively based on current task. **Never load all references at once.**

| # | Reference | File | Load When |
|---|-----------|------|-----------|
| 1 | Core Principles | `references/core-principles.md` | Starting component development, learning fundamentals, relative path pattern |
| 2 | Skill Patterns | `references/skill-patterns.md` | Designing a new skill, choosing implementation pattern (10 patterns + combinations) |
| 3 | Goal-Based Organization | `references/goal-based-organization.md` | Understanding goal-based vs component-centric, migration strategies |
| 4 | Architecture Rules | `references/architecture-rules.md` | Validating compliance, self-containment, progressive disclosure requirements |
| 5 | Skill Design | `references/skill-design.md` | Designing workflows, multi-workflow skills, workflow composition |
| 6 | Command Design | `references/command-design.md` | Creating commands, parameter parsing, routing to skill workflows |
| 7 | Token Optimization | `references/token-optimization.md` | Optimizing context, batch processing, token budgeting |
| 8 | Reference Patterns | `references/reference-patterns.md` | Allowed reference types, relative path implementation, portability |
| 9 | Frontmatter Standards | `references/frontmatter-standards.md` | Creating/validating YAML frontmatter, field specs |
| 10 | Script Standards | `references/script-standards.md` | Documenting scripts, shell patterns, rule enforcement. For Python: `Skill: pm-plugin-development:plugin-script-architecture` |
| 11 | Execution Directive | `references/execution-directive.md` | Ensuring execution (not explanation), EXECUTE vs READ vs REFERENCE modes |
| 12 | Minimal Wrapper Pattern | `references/minimal-wrapper-pattern.md` | Thin orchestrators (<150 lines), agent-to-skill delegation, fat agent migration |
| 13 | User-Facing Output | `references/user-facing-output.md` | Output filtering, status messages, anti-patterns (no step numbers, no diffs) |
| 14 | AskUserQuestion Patterns | `references/askuserquestion-patterns.md` | Interactive workflows, free-text input, multi-select, UI constraints |

### Examples

| Example | File | Shows |
|---------|------|-------|
| Goal-Based Skill | `references/examples/goal-based-skill-example.md` | Workflow organization, progressive disclosure in practice |
| Thin Orchestrator Command | `references/examples/workflow-command-example.md` | Parameter parsing, skill invocation, user interaction |
| Pattern Usage | `references/examples/pattern-usage-examples.md` | All 10 patterns applied to marketplace scenarios |

## Usage Workflow

### Step 1: Identify Your Goal and Load References

**Never load all references** — load only what's needed for current task.

| Goal | References to Load |
|------|--------------------|
| Creating component | core-principles.md, skill-patterns.md |
| Understanding architecture | goal-based-organization.md, architecture-rules.md |
| Designing skill | skill-design.md, skill-patterns.md |
| Designing command | command-design.md |
| Optimizing context | token-optimization.md |
| Validating compliance | architecture-rules.md, reference-patterns.md |
| Ensuring execution | execution-directive.md |
| Designing thin wrappers | minimal-wrapper-pattern.md |
| Designing user output | user-facing-output.md |
| Designing user interactions | askuserquestion-patterns.md |

### Step 2: Apply and Validate

Follow guidance in loaded references, then verify:
- Self-contained (no external file references)
- Relative path pattern used throughout
- Progressive disclosure implemented
- Appropriate skill pattern chosen
- Goal-based organization followed

## Integration with Other Skills

- **plugin-doctor** — Uses architecture rules and reference patterns for compliance checking
- **plugin-create** — Uses architecture principles, frontmatter standards, and validation rules
- **plugin-maintain** — Uses architecture rules for fix guidance and compliance criteria

## References

### Source Materials
- Claude Skills Deep Dive: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/
- Claude Code Plugin Documentation: https://docs.claude.com/en/docs/claude-code/plugins

### Related Skills
- plan-marshall:dev-general-practices - Core development principles and tool usage patterns
- pm-plugin-development:plugin-script-architecture - Python implementation, testing, output contracts
