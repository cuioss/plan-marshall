# AGENTS.md

Guidelines for AI assistants working in the plan-marshall repository.

## What This Repository Is

A **Claude Code Marketplace** with 10 bundles of skills, agents, and commands for CUI (Common User Interface) Open Source projects. Source format IS Claude Code native. Multi-target distribution (Claude Code native, OpenCode export) is implemented via `marketplace/targets/`; design history lives in `doc/refactor/`.

## Quick Commands

Build system: Pyprojectx wrapper (`./pw`); only Python 3 is required on the host — Pyprojectx provisions the toolchain. Never invoke `./pw` directly; use the resolved executor commands:

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"        # Full: mypy + ruff + pytest
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "compile"      # mypy
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests" # pytest
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate" # ruff + mypy + plugin-doctor
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage"     # branch coverage, 80% gate
```

**Module filtering**: Append a bundle name inside `--command-args` (e.g. `"verify plan-marshall"`) to scope to a single bundle. Omit for all.

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

## Plugin Cache Sync

After editing skills/agents/commands in `marketplace/bundles/`, sync to Claude Code plugin cache:

```bash
/sync-plugin-cache
```

This copies to `~/.claude/plugins/cache/plan-marshall/` via rsync `--delete`.

## Multi-Target Distribution

`marketplace/targets/` is the authoritative multi-target generator framework. Run `python3 marketplace/targets/generate.py --target {claude,opencode,all} --output {dir}` to emit per-target output trees. The original refactor plan that produced this framework is retired; `doc/refactor/README.md` records the landed baseline and any open workstreams.

## Key Files for Context

- `CLAUDE.md` — Full project context for Claude Code (more detailed than this file)
- `doc/developer/build.adoc` — Build system details
- `pyproject.toml` — Tool configs (ruff, mypy, pytest)
- `build.py` — Build script with module filtering
- `marketplace/.claude-plugin/marketplace.json` — Master marketplace manifest

## Git Commit Guidelines

- Git commit Co-Authored-By line: Use `Co-Authored-By: opencode/{model-version}` — include model name and version, no email address, no marketing claims.
