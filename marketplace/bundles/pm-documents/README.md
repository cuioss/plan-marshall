# CUI Documentation Standards

AsciiDoc and documentation standards enforcement for CUI projects. This bundle provides comprehensive tools for creating, validating, and maintaining technical documentation.

## Purpose

This bundle covers the full documentation lifecycle through three goal-based commands:

1. **CREATE** - Generate new documentation from templates
2. **DOCTOR** - Diagnose documentation issues (format, links, content)
3. **MAINTAIN** - Keep documentation healthy (sync, cleanup, update)

## Components Included

### Commands (3 goal-based orchestrators)

| Command | Purpose | Use When |
|---------|---------|----------|
| **/doc-create** | Create new documentation | Starting a new doc |
| **/doc-doctor** | Diagnose issues | Validating documentation |
| **/doc-maintain** | Maintain documentation | Keeping docs healthy |

#### /doc-doctor (Diagnose)

Unified diagnostic command replacing the deprecated review commands.

```
/doc-doctor [target=<path>] [depth=quick|standard|thorough]

Examples:
  /doc-doctor                              # Current directory, standard depth
  /doc-doctor target=standards/            # Specific directory
  /doc-doctor target=README.adoc           # Single file
  /doc-doctor depth=thorough               # Full review including content
```

**Depth levels:**
- `quick` - Format validation only
- `standard` - Format + link verification (default)
- `thorough` - Format + links + content review

#### /doc-create (Create)

Create new documents from templates.

```
/doc-create type=<type> name=<name> [path=<path>]

Examples:
  /doc-create type=standard name=java-logging
  /doc-create type=readme name=MyProject
  /doc-create type=guide name=setup-guide
```

**Document types:**
- `standard` - Technical specification (→ standards/{name}.adoc)
- `readme` - Project README (→ README.adoc)
- `guide` - How-to guide (→ docs/{name}.adoc)

#### /doc-maintain (Maintain)

Maintenance operations for existing documentation.

```
/doc-maintain action=<action> [target=<path>]

Examples:
  /doc-maintain action=update              # Refresh metadata
  /doc-maintain action=sync target=docs/   # Sync with code
  /doc-maintain action=cleanup             # Remove stale content
```

**Actions:**
- `sync` - Sync documentation with code changes
- `cleanup` - Remove stale/duplicate content
- `update` - Refresh metadata and cross-references

### Skills (3 skills)

**cui-documentation** - Documentation standards skill (9 workflows):

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

**adr-management** - Architectural Decision Records skill (5 workflows):

| Workflow | Purpose |
|----------|---------|
| **list-adrs** | List all ADRs with filtering |
| **create-adr** | Create new ADR from template |
| **read-adr** | Read ADR content by number |
| **update-adr** | Update ADR status |
| **delete-adr** | Delete ADR with confirmation |

**interface-management** - Interface specifications skill (5 workflows):

| Workflow | Purpose |
|----------|---------|
| **list-interfaces** | List all interfaces with filtering |
| **create-interface** | Create new interface from template |
| **read-interface** | Read interface content |
| **update-interface** | Update interface content |
| **delete-interface** | Delete interface with confirmation |

### Templates

Located in skill `templates/` directories:

- `standard-template.adoc` - Technical specification template
- `readme-template.adoc` - Project README template
- `guide-template.adoc` - How-to guide template

## Installation

```bash
/plugin install pm-documents
```

## Usage Examples

### Quick Validation

```
/doc-doctor depth=quick
```

### Full Documentation Review

```
/doc-doctor depth=thorough
```

### Create New Standard

```
/doc-create type=standard name=new-feature
```

### Sync Documentation After Code Changes

```
/doc-maintain action=sync target=docs/
```

### Clean Up Stale Documentation

```
/doc-maintain action=cleanup
```

## Architecture

```
pm-documents/
├── commands/                     # 3 goal-based commands
│   ├── doc-doctor.md             # Unified diagnostic
│   ├── doc-create.md             # Create from templates
│   └── doc-maintain.md           # Maintenance operations
└── skills/
    ├── cui-documentation/        # Core documentation skill (9 workflows)
    │   ├── SKILL.md
    │   ├── references/           # Documentation standards (lookup)
    │   ├── workflows/            # Operational procedures
    │   ├── templates/            # Document templates
    │   └── scripts/              # Automation scripts
    ├── adr-management/           # ADR management skill (5 workflows)
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── templates/
    └── interface-management/     # Interface spec skill (5 workflows)
        ├── SKILL.md
        ├── scripts/
        └── templates/
```

## Goal-Based Command Pattern

```
CREATE:   /doc-create   → cui-documentation → create-from-template
DOCTOR:   /doc-doctor   → cui-documentation → comprehensive-review
MAINTAIN: /doc-maintain → cui-documentation → sync/cleanup/refresh
```

All commands are thin orchestrators (<150 lines) that delegate to skill workflows.

## Bundle Statistics

- **Commands**: 3
- **Skills**: 3 (with 19 total workflows)
- **Templates**: 5+
- **Scripts**: 8+

## Dependencies

### Inter-Bundle Dependencies

- **planning** (optional) - For commit workflow in batch processing
- **plan-marshall** (optional) - For script-runner workflow
