# Plan Marshall Core

## Purpose

Environment setup, permission management, extension API, and cross-cutting utilities for the plan-marshall marketplace. This bundle provides foundational infrastructure that other bundles depend on.

## Architecture

This bundle provides **core infrastructure** organized into functional areas:

- **Configuration** - Project and runtime configuration management
- **Permissions** - Claude Code permission analysis and fixing
- **Extension API** - Domain bundle discovery and module detection
- **Utilities** - Logging, file operations, and inventory scanning

## Components

### Commands (5)

| Command | Description |
|---------|-------------|
| `/marshall-steward` | Project configuration wizard for planning system |
| `/tools-fix-intellij-diagnostics` | Retrieve and fix IDE diagnostics automatically |
| `/tools-manage-web-permissions` | Analyze and consolidate WebFetch domain permissions |
| `/tools-sync-agents-file` | Create or update project-specific agents.md file |
| `/tools-verify-architecture-diagrams` | Analyze and update PlantUML diagrams |

### Skills (20)

| Category | Skills |
|----------|--------|
| **Configuration** | `plan-marshall-config`, `run-config`, `marshall-steward` |
| **Permissions** | `permission-doctor`, `permission-fix`, `web-permissions` |
| **Extension API** | `extension-api`, `analyze-project-architecture` |
| **Utilities** | `logging`, `script-executor`, `file-operations-base`, `json-file-operations` |
| **Inventory** | `marketplace-inventory`, `marketplace-sync` |
| **Standards** | `general-development-rules`, `diagnostic-patterns`, `toon-usage` |
| **Memory** | `manage-memories`, `lessons-learned` |
| **CI** | `tools-integration-ci` |

### Agents (1)

| Agent | Description |
|-------|-------------|
| `research-best-practices` | Web research for best practices and recommendations |

## Key Concepts

### Extension API

The `extension-api` skill provides the foundation for domain bundle discovery:

- **ExtensionBase** - Abstract base class for all domain extensions
- **Module Discovery** - Discovers project modules from build files
- **Canonical Commands** - Standardized command vocabulary

### Script Executor

The `script-executor` skill generates `.plan/execute-script.py` with embedded script mappings, enabling notation-based script invocation across all bundles.

### TOON Format

The `toon-usage` skill documents the Tab-separated Object Notation format used for agent communication and memory persistence.
