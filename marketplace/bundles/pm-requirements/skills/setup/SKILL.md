---
name: setup
description: Standards for setting up requirements and specification documentation in new projects with proper directory structure and initial documents
user-invocable: false
---

# Project Setup Standards for Requirements Documentation

## Enforcement

**Execution mode**: Reference library; load standards on-demand for project requirements setup tasks.

**Prohibited actions:**
- Do not create documentation without following the standard directory structure
- Do not skip prefix selection; every project must have a designated requirement prefix
- Do not create partial setups; use the quality checklist to verify completeness
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- Minimum required files: `doc/Requirements.adoc` and `doc/Specification.adoc` (see `pm-documents:ref-asciidoc` for AsciiDoc format rules)
- Requirement prefix must be selected before creating any requirements
- Document templates must be used as the starting point for all initial documents
- Setup must be verified against the quality checklist before proceeding to authoring

Standards for establishing requirements and specification documentation structure in new projects, including directory layout, initial document creation, and prefix selection.

## What This Skill Provides

This skill provides comprehensive standards for:

- **Directory Structure**: Standard layout for requirements documentation
- **Prefix Selection**: Choosing appropriate requirement prefixes for projects
- **Document Templates**: Ready-to-use templates for initial documentation
- **Setup Workflow**: Step-by-step process for establishing documentation
- **Quality Verification**: Checklist for validating setup completeness
- **Lifecycle Integration**: Integrating documentation throughout project phases

## When to Use This Skill

Use this skill when:

- Starting a new project that needs requirements documentation
- Setting up documentation structure before implementation
- Standardizing documentation across multiple projects
- Onboarding teams to documentation practices
- Establishing traceability from project inception

## Workflow

Load standards progressively based on the current task — do not load all at once.

| Task Context | Standard | Key Content |
|-------------|----------|-------------|
| Directory layout and file organization | `standards/directory-structure.md` | Required layout, minimal vs. complete setup |
| Choosing requirement prefixes | `standards/prefix-selection.md` | Recommended prefixes by domain, hierarchical patterns |
| Creating initial documents | `standards/document-templates.md` | Templates for Requirements.adoc, Specification.adoc, LogMessages.adoc |
| Step-by-step setup process | `standards/setup-workflow.md` | Setup sequence, common issues, cross-reference verification |
| Validating setup completeness | `standards/quality-checklist.md` | Structure verification, content quality, traceability checks |

### Lifecycle Integration

**Documentation-First Approach**: Establish documentation structure before implementing core functional components. Create requirements and specifications before writing business logic, APIs, or main features.

1. Create documentation structure (see `directory-structure.md`)
2. Define requirements based on project goals
3. Create specifications with architectural overview
4. Use specifications to guide implementation planning

For the complete lifecycle model (PLANNED → IN PROGRESS → IMPLEMENTED → DEPRECATED), see `pm-requirements:requirements-authoring` → `standards/documentation-lifecycle-management.md`.

## Integration with Other Skills

This skill works with other pm-requirements bundle skills:

**After Setup** → `pm-requirements:requirements-authoring`
- Use after initial setup to create comprehensive requirements
- Provides detailed authoring standards for requirements content

**After Setup** → `pm-requirements:planning`
- Create planning documents for implementation tracking
- Provides task organization and status tracking

**During Implementation** → `pm-requirements:traceability`
- Link requirements to implementation code
- Maintain bi-directional traceability

## Quick Reference

**Typical Setup Sequence**:
1. Create directory structure (`mkdir -p doc/specification`)
2. Select requirement prefix (see prefix-selection.md)
3. Create Requirements.adoc from template
4. Create Specification.adoc from template
5. Create individual specification documents
6. Verify with quality checklist

**Minimum Files Required**:
- `doc/Requirements.adoc`
- `doc/Specification.adoc`

**Complete Setup Includes**:
- Requirements.adoc, Specification.adoc
- Individual specification documents in `doc/specification/`
- LogMessages.adoc (if logging required)

## Related Documentation

- **Documentation Standards**: See `pm-documents:ref-asciidoc` for AsciiDoc formatting and structure
- **Logging Standards**: LogMessages.adoc content requirements
- **Git Standards**: Committing documentation files
