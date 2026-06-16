# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Repository Overview

This is a **Claude Code Marketplace** repository providing development standards, automation tools, and AI-assisted workflows for CUI (Common User Interface) Open Source projects. It contains 10 production bundles with 94 components (skills, agents, and commands) that integrate with Claude Code's plugin system.

## Branch Naming

Working branches MUST use one of exactly three canonical prefixes. The set is closed — see the rationale below.

| Prefix | Applies to |
|--------|------------|
| `feature/` | New capabilities. Plan-created branches are auto-generated as `feature/{plan_id}`. |
| `fix/` | Bug fixes. |
| `chore/` | Maintenance, refactoring, and documentation-only changes. |

**Why the set is closed:** `.github/workflows/python-verify.yml` triggers CI on `push` only for the branch list `main`, `feature/*`, `fix/*`, `chore/*`, and `dependabot/**`. A branch whose prefix is outside that list silently receives no CI run, so its PR can never produce the `verify / verify` check that the branch-protection ruleset requires. An unlisted prefix (e.g. `docs/`) therefore makes the PR structurally unmergeable.

The `docs/` prefix is explicitly retired: it was never an established remote prefix and is not CI-triggered. Use `chore/` for documentation-only changes.

## Architecture

### Directory Structure

```
plan-marshall/
├── marketplace/                    # Claude Code marketplace system
│   ├── .claude-plugin/
│   │   └── marketplace.json        # Master marketplace configuration
│   ├── adapters/                   # Multi-assistant export adapters
│   └── bundles/                    # 10 production bundles
│       ├── plan-marshall/          # Utilities, workflow, and orchestration
│       ├── pm-dev-frontend/        # JavaScript/CSS standards
│       ├── pm-dev-frontend-cui/    # CUI-specific JavaScript standards
│       ├── pm-dev-java/            # Java development standards + agents
│       ├── pm-dev-java-cui/        # CUI-specific Java standards
│       ├── pm-dev-oci/             # OCI container standards + security
│       ├── pm-dev-python/          # Python standards + build operations
│       ├── pm-documents/           # AsciiDoc, ADRs, interfaces
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
| **Skills** | 80 | Domain knowledge, standards, and reference documentation |
| **Agents** | 10 | Autonomous task executors with focused responsibilities |
| **Commands** | 4 | User-invokable slash commands that orchestrate workflows |

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

## The 10 Production Bundles

### plan-marshall
Core infrastructure with script execution, permission management, lessons learned, and project configuration. Includes the complete 5-phase development workflow (init, refine, outline, plan, execute, finalize), task planning, git workflows, PR management, Sonar integration, and build automation for Maven/Gradle/npm.

### pm-dev-java
Java development standards covering core patterns, null safety, Lombok, CDI/Quarkus, unit testing with JUnit 5, JavaDoc, and logging. Includes agents for verification and coverage analysis.

### pm-dev-java-cui
CUI-specific Java standards covering CuiLogger, test generators, value object contracts, HTTP client patterns, and MockWebServer testing.

### pm-dev-frontend
JavaScript and frontend standards for ES modules, modern patterns, JSDoc, ESLint enforcement, and project structure.

### pm-dev-frontend-cui
CUI-specific JavaScript project standards covering Maven integration, Quarkus DevUI, NiFi, and SonarQube configuration.

### pm-dev-oci
OCI container standards covering image building, Dockerfile best practices, multi-platform builds, runtime security, and supply chain controls.

### pm-dev-python
Python development standards and pyprojectx build operations.

### pm-documents
Documentation standards for AsciiDoc, Architectural Decision Records (ADRs), and interface specifications. Includes validation, formatting, verification, and maintenance workflows.

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
- `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify`
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

Tests use pytest via the `pw` (Pyprojectx) wrapper. Only Python 3 is required on the host system. Use the resolved build commands from the Development Notes section below — never invoke `./pw` directly. See `doc/developer/build.adoc` for build system details.

### Development Notes

- Use `.plan/temp/` for ALL temporary and generated files (covered by `Write(.plan/**)` permission - avoids permission prompts)
- Use proper tools (Edit, Read, Write) instead of shell commands (echo, cat)
- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead
- Use `gh` tool for GitHub access, not MCP

### Build Commands

- Never hard-code build commands (./pw, mvn, npm, gradle) — use these resolved commands instead:
  - Compile: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "compile"`
  - Quality gate: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"`
  - Tests: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"`
  - Full verify: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`
  - Coverage: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage"`
  - Append a module name (e.g. `"verify plan-marshall"`) to scope the command to a single bundle module.
  - Always call build commands with a Bash timeout of at least 10 minutes (600000ms). When the architecture-resolved envelope (`architecture resolve` TOON) carries `bash_timeout_seconds` and `execution_tier`, pass `timeout: bash_timeout_seconds * 1000` on the Bash call for `execution_tier=per_task`, or hand off to the orchestrator for `execution_tier=orchestrator` — see `plan-marshall:dev-agent-behavior-rules` § "Bash: Timeout from architecture-resolved canonical command" and lesson `2026-05-27-20-003` for the recurrence signature.
  - After each build call, analyze the result TOON: check `status` for success/error/timeout, review `errors[N]{file,line,message,category}` for failures, and consult `log_file` for full output if deeper investigation is needed.

### Workflow Discipline (Hard Rules)

These rules apply to ALL work in this repository — ad-hoc tasks, plan execution, and agent work alike. They exist because Claude regularly violates them despite softer guidance.

- **`.plan/` access: scripts only** — ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py` manage-* scripts. Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it.
- **Bash: one command per call** — Each Bash call must contain exactly ONE command. Never combine with `&&`, `;`, `&`, or newlines.
- **Bash: no shell constructs** — No `for`/`while` loops, no `$()` substitution, no subshells, no heredocs with `#` lines. These trigger security prompts. Use dedicated tools or multiple Bash calls instead.
- **Workflow steps: no improvisation** — When following a skill or workflow, execute ONLY the commands documented in it. Never add discovery steps, invent arguments, or skip documented steps.
- **CI operations: use abstraction layer** — All CI/Git provider operations (PRs, issues, CI status, reviews) MUST go through `plan-marshall:tools-integration-ci:ci` scripts. Never use `gh` or `glab` directly.
- **Build commands: resolve via architecture** — Never hard-code `./pw`, `mvn`, `npm`, or `gradle`. Always resolve via `plan-marshall:manage-architecture:architecture resolve` first, then execute the returned `executable`.
- **Triage findings via manage-findings + ext-triage** — Triage decisions on findings (Sonar / PR review / build / lint / test) flow through `manage-findings` + `ext-triage-{domain}`; ambiguous cases escalate via `AskUserQuestion`. The structural contract lives in `extension-api/standards/ext-point-triage.md`.
- **Structured queries first** — Before using Glob/Grep for codebase navigation (file discovery, module identification, path resolution), consult `architecture files --module X`, `architecture which-module --path P`, or `architecture find --pattern P`. Glob/Grep is the fallback for sub-module component lookup and exceptional cases, not routine discovery.

### Plugin Cache Sync

When modifying plugin source files (skills, agents, commands), changes won't take effect until the plugin cache is updated. After editing files in `marketplace/bundles/`, run:

```
/sync-plugin-cache
```

This synchronizes all bundles from `marketplace/bundles/` to `~/.claude/plugins/cache/plan-marshall/` using rsync with `--delete` to ensure exact mirroring.

Cluster 02 onward, the slash command and its finalize-step counterpart are project-local under `.claude/skills/` (`.claude/skills/sync-plugin-cache/` for the engine + `/sync-plugin-cache` invocable, `.claude/skills/finalize-step-{deploy-target,sync-plugin-cache}/` for the phase-6 bodies). They read from `target/claude/` (populated by `python3 marketplace/targets/generate.py --target claude --output target/claude`, or by the project-local `project:finalize-step-deploy-target` step) and refuse to sync when that directory is missing or stale relative to `marketplace/bundles/`. Consumer projects of plan-marshall do not get any of this surface — it is meta-project-only.

On-main executor regeneration (`.plan/execute-script.py`) is performed by `project:finalize-step-sync-plugin-cache` immediately after the cache sync, in both worktree and no-worktree finalize flows — `integrate_into_main` performs the plan-dir move-back only and does NOT regenerate the executor. The executor is per-tree derived state (ADR-002): each worktree gets its own generated copy at phase-5 move-in (so main's `.plan/execute-script.py` stays present and untouched throughout phase-5+), and main's copy is refreshed at finalize by the cache-sync step when a plan changed the marketplace script set.

For manual recovery scenarios where a commit landed without running phase-6-finalize (e.g. lesson `2026-05-20-08-005`), see [`doc/developer/manual-sync-recovery.adoc`](doc/developer/manual-sync-recovery.adoc) for the symptom → command decision table.

### Registered Marketplace Path

The Claude Code marketplace registration MUST point at `target/claude/`, not at the source `marketplace/` directory. The source `marketplace/bundles/<bundle>/.claude-plugin/plugin.json` declares only the canonical agent files; the build target expands each role-eligible agent into per-level variants (`{name}-level-1.md` through `{name}-level-7.md`) under `target/claude/<bundle>/agents/` and emits a variant-aware `plugin.json` plus a top-level `target/claude/.claude-plugin/marketplace.json`. Registering the source path makes Claude Code's plugin loader install only the canonicals, so every dispatch site that resolves to `execution-context-{level}` fails with `Agent type not found`.

One-time migration on a developer machine:

1. Ensure `target/claude/` is current: `python3 marketplace/targets/generate.py --target claude --output target/claude`.
2. Re-point the marketplace: edit `~/.claude/plugins/known_marketplaces.json` so the `plan-marshall` entry's `source.path` and `installLocation` point at `/path/to/plan-marshall/target/claude` (NOT `.../marketplace`). Alternatively, in-app: `/plugin marketplace remove plan-marshall` then `/plugin marketplace add /path/to/plan-marshall/target/claude`.
3. Reinstall the plugins so install metadata picks up the variant-aware `plugin.json`: `claude plugin uninstall plan-marshall@plan-marshall && claude plugin install plan-marshall@plan-marshall` (repeat per bundle as needed).
4. Restart Claude Code or run `/reload-plugins`.
5. Verify the variants are registered: ask a fresh session to list `plan-marshall:` entries from its available-agents header. Expect canonical + seven level variants.

## Multi-Assistant Support

The marketplace uses an adapter system to export bundles to other AI assistant formats while keeping Claude Code as the primary, native format. **Only Claude Code is tested as a runtime.** The OpenCode adapter generates output conforming to the OpenCode specification but has not been validated in a live OpenCode environment.

For how this format relates to the `SKILL.md` open standard at [agentskills.io](https://agentskills.io) — where the two conform, where plan-marshall extends the spec, and how the adapter system relates to the standard — see the "Open-Standard Alignment" section in [`doc/developer/marketplace-build.adoc`](doc/developer/marketplace-build.adoc).

```
Source of truth:     marketplace/bundles/*  (Claude Code format)
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    Claude Code (native)  OpenCode       Future adapters
    .claude-plugin/       .opencode/     .cursor/, etc.
```

### Generating OpenCode Output

```bash
# Export all bundles
python3 marketplace/targets/generate.py --target opencode --output target/opencode

# Export specific bundles
python3 marketplace/targets/generate.py --target opencode --output target/opencode --bundles pm-dev-java,plan-marshall
```

The adapter transforms frontmatter, maps tool names, handles `Skill:` directives, and copies standards/scripts verbatim. Agents that rely on Claude-specific tools (`Task`, `Skill`) are excluded from export.

### Using Generated Output with OpenCode

After running the adapter:

1. Copy the generated `.opencode/` directory into your OpenCode project root
2. Copy `opencode.json` into your project root (or merge with existing config)
3. Skills appear automatically in OpenCode's skill tool — invoke them by name (e.g., `pm-dev-java-junit-core`)
4. Agents are available via `@agent-name` in OpenCode's TUI
5. Commands are available as `/command-name`

**Format mapping** (Claude Code -> OpenCode):

| Aspect | Claude Code | OpenCode |
|--------|-------------|----------|
| Skills directory | `.claude/skills/` | `.opencode/skills/` |
| Agents directory | Built-in only | `.opencode/agents/` |
| Commands directory | `.claude/commands/` | `.opencode/commands/` |
| Skill loading | `Skill:` directive in prompts | `skill` tool invoked at runtime |
| Tool names | `Read`, `Write`, `Edit` | `read`, `write`, `edit` |
| Model format | `sonnet`, `haiku`, `opus` | `anthropic/claude-sonnet-4` etc. |
| Agent tool access | `tools:` frontmatter field | `permission:` object |

**Limitations of the adapter output:**

- `Skill:` directives are annotated with comments but not executable — OpenCode loads skills via its built-in `skill` tool based on task matching
- Agents using Claude Code's `Task` or `Skill` delegation tools are excluded (no direct OpenCode equivalent for cross-agent orchestration)
- The `execute-script.py` executor is Claude Code specific — scripts are copied verbatim but the executor integration does not apply
- Standards and reference documents are portable (pure markdown) and work as-is

### Adding New Targets

Implement `marketplace.targets.base.TargetBase` and register the concrete class in `marketplace/targets/generate.py`'s `TARGET_REGISTRY`. Each target owns its frontmatter mapping, body transforms (if any), and per-target output layout under `target/{name}/`.

## Integration Points

- **Git**: `git` tool for issue/PR management
- **Build Systems**: Pyprojectx wrapper (`./pw`) for Python testing/linting
- **IDE**: IntelliJ MCP for diagnostics (file must be active in editor)
