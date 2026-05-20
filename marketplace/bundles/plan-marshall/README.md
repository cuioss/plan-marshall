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

### Commands (4)

| Command | Description |
|---------|-------------|
| `/marshall-steward` | Project configuration wizard for planning system |
| `/tools-fix-intellij-diagnostics` | Retrieve and fix IDE diagnostics automatically |
| `/workflow-permission-web` | Analyze and consolidate WebFetch domain permissions |
| `/tools-sync-agents-file` | Create or update project-specific agents.md file |

### Skills (18)

| Category | Skills |
|----------|--------|
| **Configuration** | `manage-config`, `run-config`, `marshall-steward` |
| **Permissions** | `tools-permission-doctor`, `tools-permission-fix`, `workflow-permission-web` |
| **Extension API** | `extension-api`, `manage-architecture` |
| **Utilities** | `logging`, `script-executor`, `file-operations-base` |
| **Standards** | `dev-agent-behavior-rules`, `diagnostic-patterns`, `toon-usage` |
| **Lessons** | `manage-lessons` |
| **CI** | `tools-integration-ci` |

### Agents (1)

| Agent | Description |
|-------|-------------|
| `execution-context` | Generic execution-context dispatcher (canonical + 5 level variants). Every `Task:` dispatch in this bundle targets `plan-marshall:execution-context` (canonical, inherits parent model) or `plan-marshall:execution-context-{level}` (variant pinned by level resolved from the role key). The workflow doc and skill list flow through the prompt body. |

## Entry Points and Discoverability

The primary workflow entry points are **skills**, not commands. The `plan-marshall` skill orchestrates the full plan lifecycle (create, outline, execute, finalize), and `marshall-steward` handles project configuration. Both are invoked via `Skill:` directives or by `execution-context-{level}` delegation. The commands in `commands/` serve narrower, tool-specific purposes (IDE diagnostics, agent file sync). To start a planning workflow, load the `plan-marshall:plan-marshall` skill.

## Key Concepts

### Extension API

The `extension-api` skill provides the foundation for domain bundle discovery:

- **ExtensionBase** - Abstract base class for all domain extensions
- **Module Discovery** - Discovers project modules from build files
- **Canonical Commands** - Standardized command vocabulary

### Script Executor

The `script-executor` skill generates `.plan/execute-script.py` with embedded script mappings, enabling notation-based script invocation across all bundles.

### TOON Format

The `toon-usage` skill documents the Tab-separated Object Notation format used for agent communication and persistent storage.

## Plugin cache sync — meta-project tooling (project-local)

In **this meta-project** (the plan-marshall repo itself), the host
plugin cache is mirrored from the multi-target generator output at
`target/claude/`. Both the slash command and the finalize-step
plumbing live as project-local skills under `.claude/skills/`, not in
this bundle — they only make sense for the repo that owns marketplace
bundle sources.

| Component | Path |
|-----------|------|
| `/sync-plugin-cache` slash command + engine | `.claude/skills/sync-plugin-cache/` |
| Phase-6 cache-sync finalize body | `.claude/skills/finalize-step-sync-plugin-cache/` |
| Phase-6 generator finalize body | `.claude/skills/finalize-step-deploy-target/` |
| Multi-target generator | `marketplace/targets/` (repo root, outside any bundle) |

**First-time bootstrap on a fresh checkout** (one-time, before this
repo's first finalize):

```bash
python3 marketplace/targets/generate.py --target claude --output target/claude
rsync -av --delete target/claude/plan-marshall/ ~/.claude/plugins/cache/plan-marshall/{version}/
```

`{version}` comes from `.claude-plugin/plugin.json` (this file's
sibling). After this bootstrap, every subsequent finalize cycle in this
repo runs `project:finalize-step-deploy-target` → `project:finalize-step-sync-plugin-cache`
automatically and keeps the cache fresh.

Consumer projects do not need any of this — they install the
plan-marshall plugin via Claude Code's standard plugin path, which
populates `~/.claude/plugins/cache/plan-marshall/` directly. They have
nothing to publish.
