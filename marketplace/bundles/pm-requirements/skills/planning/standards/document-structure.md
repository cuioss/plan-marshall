# Planning Document Structure Standards

Standards for planning document location, naming, header format, and core sections.

## Location and Naming

**Primary planning document**: `doc/TODO.adoc`

**Additional planning documents** (if needed):

- `doc/ROADMAP.adoc` - Long-term planning
- `doc/BACKLOG.adoc` - Future work items

## Document Header

All planning documents should use this header format:

```asciidoc
= [Project Name] TODO List
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js
```

## Core Sections

Every planning document should include:

1. **Overview**: Purpose and scope of the document
2. **Implementation Tasks**: Organized by functional area
3. **Testing Tasks**: Test implementation requirements
4. **Additional Sections**: As needed (Security, Documentation, Performance, etc.)

## Separation of Concerns

Planning documents focus on:

- **What needs to be done** (task lists)
- **Current status** (tracking progress)
- **Traceability** (linking to requirements and specs)

Planning documents do NOT include:

- **How to implement** (belongs in specifications)
- **Why it's needed** (belongs in requirements)
- **Implementation details** (belongs in code and JavaDoc)

## See Also

- [Task Organization Standards](task-organization.md) - Hierarchical structure and grouping strategies
- [Status Tracking Standards](status-tracking.md) - Status indicators and task lifecycle
- [Traceability Standards](traceability.md) - Linking to requirements and specifications
