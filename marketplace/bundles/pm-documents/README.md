# Documentation Standards

AsciiDoc and documentation standards enforcement for projects. This bundle provides comprehensive tools for creating, validating, and maintaining technical documentation.

## Purpose

This bundle provides documentation domain knowledge through two core skills (`ref-asciidoc` for formatting/validation and `ref-documentation` for content quality/review), plus a specialized management skill for interface specifications.

## Components Included

### Skills (11 registered)

**ref-asciidoc** - AsciiDoc formatting and validation skill (5 workflows):

| Workflow | Purpose |
|----------|---------|
| **format-document** | Auto-fix formatting issues |
| **validate-format** | Validate format compliance |
| **verify-links** | Verify links and xrefs |
| **create-from-template** | Create document from template |
| **refresh-metadata** | Update metadata and xrefs |

**ref-documentation** - Content quality and review skill (4 workflows):

| Workflow | Purpose |
|----------|---------|
| **review-content** | Review content quality |
| **comprehensive-review** | Orchestrate all review workflows |
| **sync-with-code** | Sync docs with code changes |
| **cleanup-stale** | Remove stale documentation |

**manage-interface** - Interface specifications skill (5 workflows):

| Workflow | Purpose |
|----------|---------|
| **list-interfaces** | List all interfaces with filtering |
| **create-interface** | Create new interface from template |
| **read-interface** | Read interface content |
| **update-interface** | Update interface content |
| **delete-interface** | Delete interface with confirmation |

**ext-triage-docs** - Extension point for documentation finding triage

**plan-marshall-plugin** - Documentation domain manifest for plan-marshall workflow integration

**recipe-doc-verify** - Recipe for verifying documentation quality (format, links, drift)

**recipe-verify-architecture-diagrams** - Recipe for verifying and updating architecture diagrams

**recipe-verify-ascii-diagrams** - Recipe for verifying ASCII diagrams

**ref-ascii-diagrams** - ASCII diagram authoring standards

**ref-svg-diagrams** - SVG diagram authoring standards

**ref-narrative-styles** - Narrative style standards for documentation

### Templates

Located in skill `templates/` directories:

- `standard-template.adoc` - Technical specification template
- `readme-template.adoc` - Project README template
- `guide-template.adoc` - How-to guide template

## Architecture

```
pm-documents/
└── skills/
    ├── ref-asciidoc/             # AsciiDoc formatting skill (5 workflows)
    │   ├── SKILL.md
    │   ├── references/           # AsciiDoc format standards (lookup)
    │   ├── workflow/            # Link verification protocol
    │   ├── templates/            # Document templates
    │   └── scripts/              # Format/validate/link scripts
    ├── ref-documentation/        # Content quality skill (4 workflows)
    │   ├── SKILL.md
    │   ├── references/           # Tone, core, organization standards
    │   ├── workflow/            # Review orchestration, content review
    │   └── scripts/              # Review/tone analysis scripts
    ├── manage-interface/         # Interface spec skill (5 workflows)
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── templates/
    ├── recipe-doc-verify/        # Documentation verification recipe
    │   └── SKILL.md
    ├── recipe-verify-architecture-diagrams/  # Architecture diagram recipe
    │   └── SKILL.md
    ├── recipe-verify-ascii-diagrams/  # ASCII diagram recipe
    │   └── SKILL.md
    ├── ref-ascii-diagrams/       # ASCII diagram standards
    │   └── SKILL.md
    ├── ref-svg-diagrams/         # SVG diagram standards
    │   └── SKILL.md
    ├── ref-narrative-styles/     # Narrative style standards
    │   └── SKILL.md
    ├── ext-triage-docs/          # Triage extension point
    └── plan-marshall-plugin/     # Extension registration
```

## Dependencies

### Inter-Bundle Dependencies

- **plan-marshall** (optional) - For script-runner workflow
