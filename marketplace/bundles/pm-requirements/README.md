# CUI Requirements Bundle

Comprehensive standards for requirements and specification documentation in CUI projects, covering the complete lifecycle from project setup through implementation and maintenance.

## Overview

This bundle provides Claude Code with expert knowledge in creating, structuring, and maintaining requirements and specification documentation following CUI standards. It ensures consistent documentation practices across all CUI projects with complete traceability from requirements through implementation.

## Skills Included

| Skill | Description |
|-------|-------------|
| `requirements-authoring` | Standards for creating and maintaining requirements and specification documents with SMART principles, proper structure, and traceability |
| `setup` | Standards for setting up documentation structure and initial documents in new projects |
| `planning` | Standards for planning documents, task tracking, and status indicators |
| `traceability` | Standards for maintaining bidirectional traceability between requirements, specifications, and implementation code |
| `ext-triage-reqs` | Extension point for requirements finding triage |
| `plan-marshall-plugin` | Extension registration |

## What This Bundle Provides

### Requirements Documentation Standards

- SMART requirements principles and practices
- Requirements document structure and formatting
- Requirement numbering and ID schemes
- Requirements maintenance and lifecycle management
- Traceability to specifications and implementation

### Specification Documentation Standards

- Specification document structure and organization
- Backtracking links to requirements
- Implementation status tracking
- Linking to source code and tests

### Project Setup Standards

- Standard directory structure for documentation
- Initial document templates and structure
- Requirement prefix selection process
- Setting up traceability from the start

### Planning Documentation Standards

- TODO lists and task tracking
- Task status indicators and conventions
- Linking tasks to requirements and specifications
- Managing implementation progress

### Implementation Linkage Standards

- Bidirectional traceability between specifications and code
- API documentation standards for referencing specifications (JavaDoc, docstrings, JSDoc)
- Specification updates during and after implementation
- Maintaining holistic system view across documentation levels

## Usage Examples

### Creating Requirements for a New Project

```
Create requirements documentation for a JWT token validation library.
The project should follow CUI standards with proper structure and traceability.
```

### Maintaining Existing Requirements

```
Add a new requirement for token caching to the JWT processor requirements.
Ensure it follows existing numbering and includes proper traceability.
```

### Linking Implementation to Specifications

```
The TokenValidator class is now implemented. Update the specification
to link to the implementation and mark it as complete.
```

## Integration with Other Bundles

### CUI Documentation Standards Bundle

Works closely with general documentation standards:
- Follows AsciiDoc formatting standards
- Uses standard document structure conventions

### Language-Specific Development Bundles

Integrates with language development standards:
- API documentation references to specifications (JavaDoc, docstrings, JSDoc)
- Implementation traceability patterns

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-requirements/
