---
name: planning
description: Standards for creating and maintaining project planning documentation with task tracking, status indicators, and traceability to requirements
user-invocable: false
---

# Planning Documentation Standards

## Enforcement

**Execution mode**: Reference library; load standards on-demand for planning documentation tasks.

**Prohibited actions:**
- Do not include implementation details or rationale in planning documents; focus on task lists, status, and traceability
- Do not archive completed tasks; leave them in the planning document with updated status
- Do not create planning documents without traceability links to requirements
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- Planning documents follow the project's documentation format (see `pm-documents:ref-asciidoc` for AsciiDoc format rules)
- Status indicators must follow the defined set (PLANNED, IN PROGRESS, IMPLEMENTED, etc.)
- Task groups must link to originating requirements or specifications
- Documents must be kept current as living documentation

Standards for creating, structuring, and maintaining project planning documents that track implementation tasks while maintaining traceability to requirements and specifications.

## What This Skill Provides

### Format Note

This skill's standards files are in Markdown (`.md`) format as required for marketplace bundles. The standards describe planning document structure and conventions that are format-agnostic. Code examples use AsciiDoc syntax; for AsciiDoc formatting rules, see `pm-documents:ref-asciidoc`.

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

Load standards progressively based on the current task — do not load all at once.

| Task Context | Standard | Key Content |
|-------------|----------|-------------|
| Creating/reviewing document structure | `standards/document-structure.md` | Location, naming, header format, core sections, separation of concerns |
| Organizing tasks hierarchically | `standards/task-organization.md` | Heading structure, grouping strategies (component/feature/layer/phase) |
| Tracking task status and lifecycle | `standards/status-tracking.md` | Status indicators, usage examples, implementation notes, task lifecycle |
| Linking tasks to requirements | `standards/requirement-linking.md` | Requirement/specification links, multiple references, traceability |
| Maintaining planning documents | `standards/maintenance.md` | Update frequency, archive strategy, quality standards, anti-patterns |
| Need concrete examples | `standards/examples.md` | Complete example document with all patterns demonstrated |

## Related Skills

### Related Skills in Bundle

- `pm-requirements:requirements-authoring` - Standards for requirements and specification documentation that planning tasks trace to
- `pm-requirements:setup` - Standards for creating initial TODO structure during project setup
- `pm-requirements:traceability` - Standards for linking planning tasks to implementation code

### External Standards

- `pm-documents:ref-asciidoc` - AsciiDoc formatting and structure
- `plan-marshall:workflow-integration-git` - Committing planning document changes
