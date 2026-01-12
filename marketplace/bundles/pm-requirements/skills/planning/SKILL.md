---
name: pm-requirements:planning
source_bundle: pm-requirements
description: Standards for creating and maintaining project planning documentation with task tracking, status indicators, and traceability to requirements
version: 0.1-BETA
allowed-tools: [Read]
---

# Planning Documentation Standards

Standards for creating, structuring, and maintaining project planning documents that track implementation tasks while maintaining traceability to requirements and specifications.

## What This Skill Provides

### Format Note

**Important**: This skill's standards files are in **Markdown** (`.md`) format as required for marketplace bundles. However, the standards themselves describe how to create **AsciiDoc** (`.adoc`) planning documents in target projects.

- **Transport format** (marketplace): Markdown (`.md`) - these standards files
- **Target format** (projects): AsciiDoc (`.adoc`) - TODO.adoc, ROADMAP.adoc, etc.

Code examples within the standards show AsciiDoc syntax because they demonstrate what users should write in their project's planning documents.

### Comprehensive Planning Standards

This skill provides complete standards for:

- **Document structure** - Location, naming, header format, and core sections
- **Task organization** - Hierarchical structure and grouping strategies
- **Status tracking** - Status indicators, task details, and lifecycle management
- **Traceability** - Linking tasks to requirements and specifications
- **Maintenance** - Keeping planning documents current and high-quality
- **Examples** - Complete working examples demonstrating all patterns

### Core Principles

#### Planning Document Purpose

Planning documents bridge requirements and specifications with actual implementation work by:

- Breaking down high-level requirements into actionable tasks
- Tracking implementation progress
- Maintaining traceability from tasks to requirements
- Providing visibility into project status

#### Separation of Concerns

Planning documents focus on task lists, status tracking, and traceability - not implementation details or rationale. See `standards/document-structure.md` for complete separation of concerns guidance.

#### Living Documentation

Planning documents are dynamic and updated frequently as work progresses - they reflect current project state rather than being archived. See `standards/maintenance.md` for complete living documentation guidance and update frequency recommendations.

## When to Activate This Skill

Activate this skill when:

- **Creating new planning documents** - Setting up TODO.adoc for a new project
- **Organizing tasks** - Structuring implementation work hierarchically
- **Tracking progress** - Marking task status and maintaining current state
- **Maintaining traceability** - Linking tasks to requirements and specifications
- **Reviewing planning quality** - Ensuring planning documents follow standards

## Workflow

### Step 1: Load Document Structure Standards

When creating or reviewing planning document structure:

```
Read: standards/document-structure.md
```

This standard covers:
- Document location and naming conventions
- Header format with proper AsciiDoc configuration
- Core sections every planning document needs
- Separation of concerns between planning, requirements, and specifications

### Step 2: Load Task Organization Standards

When organizing tasks hierarchically:

```
Read: standards/task-organization.md
```

This standard covers:
- Hierarchical task structure using AsciiDoc headings
- Grouping strategies (by component, feature, layer, or phase)
- Testing task organization
- Choosing the right grouping strategy for your project

### Step 3: Load Status Tracking Standards

When tracking task status and lifecycle:

```
Read: standards/status-tracking.md
```

This standard covers:
- Status indicator syntax and meaning
- Status usage examples for all states
- Implementation note patterns
- Task lifecycle (adding, completing, refactoring)

### Step 4: Load Traceability Standards

When linking tasks to requirements:

```
Read: standards/traceability.md
```

This standard covers:
- Linking task groups to requirements
- Linking task groups to specifications
- Handling multiple requirement references
- Traceability benefits for impact analysis and verification

### Step 5: Load Maintenance Standards

When maintaining planning documents:

```
Read: standards/maintenance.md
```

This standard covers:
- Keeping documents current with update frequency guidance
- Archive strategy (don't archive, leave completed tasks)
- Quality standards (clarity, completeness, traceability, maintainability)
- Common anti-patterns to avoid

### Step 6: Load Examples (Optional)

When you need concrete examples:

```
Read: standards/examples.md
```

This standard provides:
- Complete example planning document
- All patterns demonstrated in context
- Key pattern highlights and explanations

## Standards Organization

All planning standards are organized in the `standards/` directory:

- `document-structure.md` - Document location, header, and core sections
- `task-organization.md` - Hierarchical structure and grouping strategies
- `status-tracking.md` - Status indicators, notes, and task lifecycle
- `traceability.md` - Linking to requirements and specifications
- `maintenance.md` - Keeping planning documents current and high-quality
- `examples.md` - Complete working example demonstrating all patterns

## Tool Access

This skill requires:

- **Read**: To load standards files

## Related Skills

### Related Skills in Bundle

- `pm-requirements:requirements-authoring` - Standards for requirements and specification documentation that planning tasks trace to
- `pm-requirements:setup` - Standards for creating initial TODO structure during project setup
- `pm-requirements:traceability` - Standards for linking planning tasks to implementation code

### External Standards

- AsciiDoc formatting standards - For document structure and formatting
- Git commit standards - For tracking task completion in commits
- Project management best practices - For effective task organization and tracking
