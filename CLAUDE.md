# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Repository Overview

This is a **Claude Code Marketplace** repository providing development standards, automation tools, and AI-assisted workflows for CUI (Common User Interface) Open Source projects. It contains 8 production bundles with 95 components (skills, agents, and commands) that integrate with Claude Code's plugin system.

## Architecture

### Directory Structure

```
plan-marshall/
├── marketplace/                    # Claude Code marketplace system
│   ├── .claude-plugin/
│   │   └── marketplace.json        # Master marketplace configuration
│   └── bundles/                    # 8 production bundles
│       ├── pm-dev-java/            # Java development standards + agents
│       ├── pm-dev-frontend/        # JavaScript/CSS standards + agents
│       ├── pm-dev-builder/         # Maven/Gradle/npm build automation
│       ├── planning/               # Task planning & workflow management
│       ├── pm-documents/           # AsciiDoc, ADRs, interfaces
│       ├── plan-marshall/          # Utility commands & file operations
│       ├── pm-plugin-development/  # Plugin creation toolkit
│       └── pm-requirements/        # Requirements engineering
├── test/                           # Python pytest tests for scripts
├── .plan/                          # Planning and temp files (gitignored)
└── .claude/                        # Project-level Claude Code configuration
```

### Component Model

The marketplace uses a three-tier component hierarchy:

| Component | Count | Purpose |
|-----------|-------|---------|
| **Skills** | 28 | Domain knowledge, standards, and reference documentation |
| **Agents** | 28 | Autonomous task executors with focused responsibilities |
| **Commands** | 39 | User-invokable slash commands that orchestrate workflows |

### Bundle Structure

Each bundle follows a consistent structure:

```
bundle-name/
├── .claude-plugin/
│   └── plugin.json         # Bundle manifest (name, version, components)
├── agents/                 # Specialized task agents (*.md)
├── commands/               # Slash commands (*.md)
├── skills/                 # Development standards
│   └── skill-name/
│       ├── SKILL.md        # Skill definition and workflows
│       ├── standards/      # Detailed standard documents (*.md)
│       ├── scripts/        # Implementation scripts (Python/Bash)
│       └── templates/      # Document/code templates
└── README.md               # Bundle documentation
```

## The 8 Production Bundles

### pm-dev-java
Java development standards covering core patterns, null safety, Lombok, CDI/Quarkus, unit testing with JUnit 5, JavaDoc, and logging. Includes agents for implementation, testing, refactoring, and build fixing.

### pm-dev-frontend
JavaScript and frontend standards for ES modules, modern patterns, CSS, JSDoc, project structure, Maven integration, ESLint/Prettier/StyleLint configuration, Cypress E2E testing, and Jest unit testing.

### builder
Unified build automation supporting Maven, Gradle, and npm. Features environment detection, build output parsing, error routing, and auto-fixing workflows.

### planning
Complete development workflow automation with 14 skills covering task planning, implementation phases, plan refinement, finalization, git workflows, PR management, work logging, and Sonar integration.

### pm-documents
Documentation standards for AsciiDoc, Architectural Decision Records (ADRs), and interface specifications. Includes validation, formatting, and maintenance workflows.

### plan-marshall
Utility commands for script execution, permission management, file operations, memory management, lessons learned tracking, and project configuration.

### pm-plugin-development
Plugin development toolkit with creation wizards, quality diagnosis, marketplace inventory scanning, architecture guidance, and component maintenance workflows.

### pm-requirements
Requirements engineering standards covering authoring, planning, traceability, and project initialization.

## Key Design Patterns

### Skills-First Development
Standards are loaded before any code work begins. Skills provide the domain knowledge that guides implementation.

### Agent Delegation
Commands orchestrate agents for autonomous subtask execution. Agents have focused responsibilities and return structured JSON results.

### Build System Abstraction
Single interface for Maven/Gradle/npm with automatic environment detection. Consistent output parsing and error routing across all build systems.

### Structured Contracts
All agents return JSON with status, data, and metrics. Explicit error paths and partial success states enable iteration.

### Script Execution Convention

All marketplace scripts are executed via the executor:

```bash
python3 .plan/execute-script.py {notation} [subcommand] {args...}
```

**Notation format**: `{bundle}:{skill}:{script}` (e.g., `planning:manage-files:manage-files`)

**Examples**:
- `python3 .plan/execute-script.py planning:manage-files:manage-files add --plan-id my-plan --file task.md`
- `python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets verify`
- `python3 .plan/execute-script.py planning:manage-config:manage-config set --plan-id my-plan --key foo --value bar`

**Executor features**:
- Embedded script mappings (no runtime file I/O)
- Notation-to-path resolution
- Two-tier execution logging (plan-scoped or global)
- Error standardization

**Setup**: Run `/marshall-steward` after bundle changes to regenerate the executor with updated mappings.

**Script Development**: See `pm-plugin-development:plugin-script-architecture` skill for implementation standards.

## Working in This Repository

### File Formats

- **Skills/Commands/Agents**: Markdown with YAML frontmatter
- **Standards documents**: Markdown (some AsciiDoc templates available)
- **Scripts**: Python and Bash in `skills/*/scripts/` directories
- **Configuration**: JSON for plugin.json, marketplace.json, settings

### Naming Conventions

- Files and commands: `kebab-case` (e.g., `java-implement-code.md`)
- Bundles: Descriptive names with domain prefix (e.g., `pm-dev-java`)
- Skills: Domain-specific names (e.g., `cui-java-core`, `plan-refine`)

### Documentation Standards

- **No version history**: Never add changelogs, "RECENT CHANGES", or dated update sections
- **No timestamps**: Never add dates or version numbers to document content
- **No duplication**: Use cross-references instead of duplicating information
- **Current state only**: Document present requirements, not transitional information
- **AsciiDoc formatting**: Ensure blank line before lists, proper cross-references with `xref:` syntax

### Testing

See `pm-plugin-development:plugin-script-architecture` skill for testing standards.

```bash
python3 test/run-tests.py                                          # all tests
python3 test/run-tests.py test/planning/                           # directory
python3 test/run-tests.py test/planning/plan-files/test_parse_plan.py  # single file
```

### Development Notes

- Use `.plan/temp/` for ALL temporary and generated files (covered by `Write(.plan/**)` permission - avoids permission prompts)
- Use proper tools (Edit, Read, Write) instead of shell commands (echo, cat)
- Use `gh` tool for GitHub access, not MCP

### Plugin Cache Sync

When modifying plugin source files (skills, agents, commands), changes won't take effect until the plugin cache is updated. After editing files in `marketplace/bundles/`, run:

```
/sync-plugin-cache
```

This synchronizes all bundles from `marketplace/bundles/` to `~/.claude/plugins/cache/plan-marshall/` using rsync with `--delete` to ensure exact mirroring.

## Integration Points

- **Git**: `git` tool for issue/PR management
- **Build Systems**: none, md only
- **IDE**: IntelliJ MCP for diagnostics (file must be active in editor)
