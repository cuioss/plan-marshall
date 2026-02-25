---
name: setup
description: Standards for setting up requirements and specification documentation in new CUI projects with proper directory structure and initial documents
user-invokable: false
---

# Project Setup Standards for Requirements Documentation

Standards for establishing requirements and specification documentation structure in new CUI projects, including directory layout, initial document creation, and prefix selection.

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

- Starting a new CUI project that needs requirements documentation
- Setting up documentation structure before implementation
- Standardizing documentation across multiple projects
- Onboarding teams to CUI documentation practices
- Establishing traceability from project inception

## Workflow

### Step 1: Understand Documentation Principles

Load core principles and directory structure:

```
Read: standards/directory-structure.md
Read: standards/lifecycle-integration.md
```

These standards provide:
- Required directory layout and file organization
- Documentation-first approach principles
- Minimal vs. complete setup guidance
- Integration with project lifecycle phases

### Step 2: Select Requirement Prefix

Load prefix selection guidance:

```
Read: standards/prefix-selection.md
```

This standard provides:
- Recommended prefixes by domain
- Custom prefix guidelines
- Hierarchical prefix patterns
- Cross-domain project guidance

### Step 3: Create Initial Documents

Load document templates:

```
Read: standards/document-templates.md
```

This standard provides templates for:
- Requirements.adoc
- Specification.adoc
- Individual specification files
- LogMessages.adoc

### Step 4: Follow Setup Workflow

Load workflow guidance:

```
Read: standards/setup-workflow.md
```

This standard provides:
- Step-by-step setup process
- Common setup issues and solutions
- Cross-reference verification steps

### Step 5: Verify Quality

Load quality checklist:

```
Read: standards/quality-checklist.md
```

This standard provides:
- Documentation structure verification
- Content quality checks
- Traceability validation

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

- **CUI Documentation Standards**: General AsciiDoc formatting and structure
- **Logging Standards**: LogMessages.adoc content requirements
- **Git Standards**: Committing documentation files
