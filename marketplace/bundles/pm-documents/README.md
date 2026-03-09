# CUI Documentation Standards

AsciiDoc and documentation standards enforcement for CUI projects. This bundle provides comprehensive tools for creating, validating, and maintaining technical documentation.

## Purpose

This bundle provides documentation domain knowledge through the core `ref-documentation` skill, plus specialized management skills for ADRs and interface specifications.

## Components Included

### Skills (3 skills)

**ref-documentation** - Documentation standards skill (9 workflows):

| Workflow | Purpose |
|----------|---------|
| **format-document** | Auto-fix formatting issues |
| **validate-format** | Validate format compliance |
| **verify-links** | Verify links and xrefs |
| **review-content** | Review content quality |
| **comprehensive-review** | Orchestrate all review workflows |
| **create-from-template** | Create document from template |
| **sync-with-code** | Sync docs with code changes |
| **cleanup-stale** | Remove stale documentation |
| **refresh-metadata** | Update metadata and xrefs |

**manage-adr** - Architectural Decision Records skill (5 workflows, script-only):

| Workflow | Purpose |
|----------|---------|
| **list-adrs** | List all ADRs with filtering |
| **create-adr** | Create new ADR from template |
| **read-adr** | Read ADR content by number |
| **update-adr** | Update ADR status |
| **delete-adr** | Delete ADR with confirmation |

**manage-interface** - Interface specifications skill (5 workflows, script-only):

| Workflow | Purpose |
|----------|---------|
| **list-interfaces** | List all interfaces with filtering |
| **create-interface** | Create new interface from template |
| **read-interface** | Read interface content |
| **update-interface** | Update interface content |
| **delete-interface** | Delete interface with confirmation |

**ext-triage-docs** - Extension point for documentation finding triage

**plan-marshall-plugin** - Extension registration

### Commands (1 command)

| Command | Purpose |
|---------|---------|
| **tools-verify-architecture-diagrams** | Specialized PlantUML verification |

### Templates

Located in skill `templates/` directories:

- `standard-template.adoc` - Technical specification template
- `readme-template.adoc` - Project README template
- `guide-template.adoc` - How-to guide template

## Architecture

```
pm-documents/
├── commands/
│   └── tools-verify-architecture-diagrams.md
└── skills/
    ├── ref-documentation/        # Core documentation skill (9 workflows)
    │   ├── SKILL.md
    │   ├── references/           # Documentation standards (lookup)
    │   ├── workflows/            # Operational procedures
    │   ├── templates/            # Document templates
    │   └── scripts/              # Automation scripts
    ├── manage-adr/               # ADR management skill (5 workflows)
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── templates/
    ├── manage-interface/         # Interface spec skill (5 workflows)
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── templates/
    ├── ext-triage-docs/          # Triage extension point
    └── plan-marshall-plugin/     # Extension registration
```

## Dependencies

### Inter-Bundle Dependencies

- **plan-marshall** (optional) - For script-runner workflow
