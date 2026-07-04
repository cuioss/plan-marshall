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

### Commands (2)

| Command | Description |
|---------|-------------|
| `/tools-fix-intellij-diagnostics` | Retrieve and fix IDE diagnostics automatically |
| `/tools-sync-agents-file` | Create or update project-specific agents.md file |

Configuration (`marshall-steward`) and WebFetch permission consolidation (`workflow-permission-web`) are skills, not commands.

### Skills (71)

| Category | Skills |
|----------|--------|
| **Workflow phases** | `phase-1-init`, `phase-2-refine`, `phase-3-outline`, `phase-4-plan`, `phase-5-execute`, `phase-6-finalize` |
| **Orchestration** | `plan-marshall`, `execute-task`, `plan-doctor`, `plan-retrospective`, `marshall-steward` |
| **Personas** | `persona-plan-marshall-agent` plus 7 role personas (`persona-auditor`, `persona-code-reviewer`, `persona-documenter`, `persona-implementer`, `persona-integration-tester`, `persona-module-tester`, `persona-security-expert`) |
| **Services (`manage-*`)** | `manage-adr`, `manage-architecture`, `manage-change-ledger`, `manage-ci-artifacts`, `manage-config`, `manage-execution-manifest`, `manage-files`, `manage-findings`, `manage-lessons`, `manage-locks`, `manage-logging`, `manage-metrics`, `manage-personas`, `manage-plan-documents`, `manage-providers`, `manage-references`, `manage-run-config`, `manage-solution-outline`, `manage-status`, `manage-tasks`, `manage-terminal-title` |
| **Build systems** | `build-gradle`, `build-maven`, `build-npm`, `build-pyproject` |
| **Workflow integrations** | `workflow-integration-git`, `workflow-integration-github`, `workflow-integration-gitlab`, `workflow-integration-sonar`, `workflow-pr-doctor`, `workflow-permission-web` |
| **Tools** | `tools-file-ops`, `tools-input-validation`, `tools-integration-ci`, `tools-permission-doctor`, `tools-permission-fix`, `tools-script-executor` |
| **Recipes** | `recipe-agentfile-hygiene`, `recipe-code-review`, `recipe-lesson-cleanup`, `recipe-refactor-to-profile-standards`, `recipe-security-audit`, `recipe-simplify-codebase` |
| **References** | `ref-agentfile-hygiene`, `ref-code-quality`, `ref-toon-format`, `ref-workflow-architecture` |
| **Extension / infrastructure** | `extension-api`, `plan-marshall-plugin`, `platform-runtime`, `script-shared`, `untrusted-ingestion` |

### Agents (2)

| Agent | Description |
|-------|-------------|
| `execution-context` | Generic execution-context dispatcher (canonical + 7 level variants). Every `Task:` dispatch in this bundle targets `plan-marshall:execution-context` (canonical, inherits parent model) or `plan-marshall:execution-context-{level}` (variant pinned by level resolved from the role key). The workflow doc and skill list flow through the prompt body. |
| `execution-context-reader` | Read-only counterpart with a restricted tool surface (`WebSearch`, `WebFetch`, `Read`, `Grep`), used for untrusted-ingestion research dispatches. Same canonical + 7 level variant expansion. |

## Entry Points and Discoverability

The primary workflow entry points are **skills**, not commands. The `plan-marshall` skill orchestrates the full plan lifecycle (create, outline, execute, finalize), and `marshall-steward` handles project configuration. Both are invoked via `Skill:` directives or by `execution-context-{level}` delegation. The commands in `commands/` serve narrower, tool-specific purposes (IDE diagnostics, agent file sync). To start a planning workflow, load the `plan-marshall:plan-marshall` skill.

## Key Concepts

### Extension API

The `extension-api` skill provides the foundation for domain bundle discovery:

- **ExtensionBase** - Abstract base class for all domain extensions
- **Module Discovery** - Discovers project modules from build files
- **Canonical Commands** - Standardized command vocabulary

### Script Executor

The `tools-script-executor` skill generates `.plan/execute-script.py` with embedded script mappings, enabling notation-based script invocation across all bundles.

### TOON Format

The `ref-toon-format` skill documents the Tab-separated Object Notation format used for agent communication and persistent storage.

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
