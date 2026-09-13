# Planning Document Structure Standards

Standards for planning document location, naming, header format, and core sections.

> **Format note**: Examples use AsciiDoc (`.adoc`) syntax. For AsciiDoc header attributes and formatting rules, see `pm-documents:ref-asciidoc`. This document covers planning-specific structure and content organization.

## Location and Naming

**Primary planning document**: `doc/TODO.adoc`

**Additional planning documents** (if needed):

- `doc/ROADMAP.adoc` - Long-term planning
- `doc/BACKLOG.adoc` - Future work items

## Document Header

Planning documents use the standard document header with table of contents, section numbering, and syntax highlighting. See `pm-documents:ref-asciidoc` → `references/asciidoc-formatting.md` for the header format and attribute configuration.

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
- **Implementation details** (belongs in code and API documentation)

## See Also

- [Task Organization Standards](task-organization.md) - Hierarchical structure and grouping strategies
- [Status Tracking Standards](status-tracking.md) - Status indicators and task lifecycle
- [Requirement Linking Standards](requirement-linking.md) - Linking to requirements and specifications
