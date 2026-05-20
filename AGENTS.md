# AGENTS.md

Guidelines for AI assistants working in the plan-marshall repository.

## What This Repository Is

A **Claude Code Marketplace** with 10 bundles of skills, agents, and commands for CUI (Common User Interface) Open Source projects. Source format IS Claude Code native. Multi-target distribution to OpenCode is in design phase (see `doc/refactor/`).

## Quick Commands

Build system: Pyprojectx wrapper (`./pw`), Python 3.12+ required.

```bash
./pw verify                    # Full: mypy + ruff + pytest
./pw compile [module]          # mypy on bundle (e.g. pm-dev-java)
./pw module-tests [module]     # pytest on test/ or test/<module>
./pw quality-gate [module]     # ruff + mypy (no tests)
./pw lint / ./pw lint-fix      # ruff check / fix
./pw fmt                       # ruff format
```

**Module filtering**: Most commands accept a bundle name (e.g. `plan-marshall`, `pm-dev-java`) to scope to a single bundle. Omit for all.

## Executor Pattern (CRITICAL)

All marketplace scripts run through the generated executor — never by direct path:

```bash
python3 .plan/execute-script.py {bundle}:{skill}:{script} [subcommand] [args...]
```

Examples:
- `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`
- `python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add --plan-id my-plan --file task.md`

**Regenerate executor** after bundle changes: `/marshall-steward`

## Hard Rules

- **`.plan/` access via scripts only** — Never Read/Write/Edit `.plan/` files directly. Use `python3 .plan/execute-script.py` with manage-* scripts.
- **Bash: one command per call** — No `&&`, `;`, `|`, loops, `$()`, subshells. Use dedicated tools or multiple Bash calls.
- **No shell file operations** — Use Glob/Grep/Read/Edit tools, not `ls`, `find`, `cat`, `grep`.
- **Structured queries first** — Before Glob/Grep for navigation, try `architecture files --module X` or `architecture which-module --path P`.
- **CI operations via abstraction** — All PR/issue/CI work goes through `plan-marshall:tools-integration-ci:ci` scripts. Never `gh` or `glab` directly.

## File Formats

- **Skills/Agents/Commands**: Markdown with YAML frontmatter (name, description, tools/permissions)
- **Scripts**: Python and Bash in `skills/*/scripts/`
- **Standards**: Markdown (some AsciiDoc templates)
- **Config**: JSON for `plugin.json`, `marketplace.json`

## Documentation Standards

- **No version history** — Never add changelogs, "RECENT CHANGES", or dated sections
- **No timestamps** — No dates or version numbers in document content
- **No duplication** — Cross-reference instead of duplicating
- **Current state only** — Document present requirements, not transitions

## Architecture

```
marketplace/
├── .claude-plugin/marketplace.json    # Master marketplace manifest
├── targets/                           # Multi-target generators (claude, opencode)
└── bundles/                           # 10 production bundles
    └── {bundle}/
        ├── .claude-plugin/plugin.json # Bundle manifest
        ├── agents/                    # Task agents (*.md)
        ├── commands/                  # Slash commands (*.md)
        └── skills/
            └── {skill}/
                ├── SKILL.md           # Skill definition
                ├── standards/         # Detailed standards (*.md)
                ├── scripts/           # Python/Bash scripts
                └── templates/         # Document/code templates

test/                                  # pytest tests for scripts
doc/                                   # Documentation (AsciiDoc)
doc/refactor/                          # Multi-target distribution design plans
```

## Plugin Cache Sync

After editing skills/agents/commands in `marketplace/bundles/`, sync to Claude Code plugin cache:

```bash
/sync-plugin-cache
```

This copies to `~/.claude/plugins/cache/plan-marshall/` via rsync `--delete`.

## Multi-Target Distribution (In Design)

See `doc/refactor/` for the 7-cluster plan to distribute to both Claude Code and OpenCode:

| Cluster | Document | Topic |
|---------|----------|-------|
| 00 | `00-cleanup-precondition/plan.md` | Source-side prose cleanup of skill bodies (precondition) |
| 01 | `01-design-platform-api/plan.md` | `platform-runtime` API (13 operations) |
| 02 | `02-build-system/plan.md` | Target generator, OpenCode emitter |
| 03 | `03-refactor-for-portability/plan.md` | Skill rewrites for portability |
| 04 | `04-validate-and-document/plan.md` | Test plan, acceptance criteria |
| 05 | `05-distribution/plan.md` | CI/CD, artifact hosting, installation |
| 06 | `06-developer-workflow/plan.md` | Developer inner loop (both platforms) |

**Current state**: `marketplace/targets/` is the authoritative multi-target generator framework. Run `python3 marketplace/targets/generate.py --target {claude,opencode,all} --output {dir}` to emit per-target output trees.

## Key Files for Context

- `CLAUDE.md` — Full project context for Claude Code (more detailed than this file)
- `doc/build-structure.adoc` — Build system details
- `pyproject.toml` — Tool configs (ruff, mypy, pytest)
- `build.py` — Build script with module filtering
- `marketplace/.claude-plugin/marketplace.json` — Master marketplace manifest

## Git Commit Guidelines

- Git commit Co-Authored-By line: Use `Co-Authored-By: opencode/{model-version}` — include model name and version, no email address, no marketing claims.
