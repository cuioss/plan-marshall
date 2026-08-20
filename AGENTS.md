# AGENTS.md

Guidelines for AI assistants working in the plan-marshall repository.

## What This Repository Is

A **Claude Code Marketplace** of bundled skills, agents, and commands for CUI (Common User Interface) Open Source projects — the bundle set is whatever `marketplace/.claude-plugin/marketplace.json` registers. Source format IS Claude Code native; every other target is an export derived from it. Multi-target distribution is implemented via `marketplace/targets/`, and the set of targets is whatever is registered in `TARGET_REGISTRY` (`marketplace/targets/__init__.py`) — the registry is the source of truth and is deliberately not restated here. Open multi-target work is planned under `doc/plans/multiplattform/`, with the cross-cutting constraints in its `reference/principles.md`.

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

**One bounded exception:** a plan executed from `doc/plans/` runs in the standalone plan lane, which supersedes several of these rules because the machinery they name does not exist in a fresh clone. The lane's contract is `.claude/skills/cloud-plan-lane/SKILL.md`; the exact carve-out is recorded in `CLAUDE.md` § "Standalone Plan Lane". Outside `doc/plans/` execution, every rule below binds without exception.

- **`.plan/` access via scripts only** — Never Read/Write/Edit `.plan/` files directly. Use `python3 .plan/execute-script.py` with manage-* scripts.
- **Bash: one command per call** — No `&&`, `;`, trailing `&`, or newlines; no loops, `$()`, subshells, or heredocs. Use dedicated tools or multiple Bash calls. (`CLAUDE.md` states the same set; keep the two in step.)
- **No shell file operations** — Use Glob/Grep/Read/Edit tools, not `ls`, `find`, `cat`, `grep`, or git's `grep` subcommand. For a content question ("which file contains X?"), use `architecture search --content --pattern P` — see `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § search.
- **Structured queries first** — Before Glob/Grep for navigation, try `architecture files --module X`, `architecture which-module --path P`, `architecture find --pattern P` (path glob), or `architecture search --content --pattern P` (file content).
- **`search --content` covers the INVENTORY, not the tree** — it searches crawled files only, so `.git`, `node_modules`, `target`, caches, gitignored paths (including `.plan/`), and dotfile trees outside the allowlist (`.claude/**`, `.github/**`) are never searched. A zero result means *"not in any inventoried file"*, never *"not in the tree"*. For an out-of-inventory path, fall back to `Glob`/`Grep`/`Read` scoped to that path; if those tools are unavailable in the current envelope, report the coverage gap instead of recording a clean negative. A `count: 0` is trustworthy only over clean coverage — see `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § search → "Complete-coverage rule" for the canonical field list.
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

`marketplace/targets/` is the authoritative multi-target generator framework. Run `uv run python marketplace/targets/generate.py --target {name} --output {dir}` to emit per-target output trees. Valid `{name}` values are **every target registered in `TARGET_REGISTRY`** (`marketplace/targets/__init__.py`), plus `all`, which runs every registered target sequentially. The generator derives its `--target` choices from that registry, so `generate.py --help` always prints the live set — read it there rather than trusting an enumeration copied into prose. Open multi-target workstreams are planned under `doc/plans/multiplattform/`; its `README.md` carries the architecture baseline and the plan queue.

## Key Files for Context

- `CLAUDE.md` — Full project context for Claude Code (more detailed than this file)
- `doc/developer/build.adoc` — Build system details
- `pyproject.toml` — Tool configs (ruff, mypy, pytest)
- `build.py` — Build script with module filtering
- `marketplace/.claude-plugin/marketplace.json` — Master marketplace manifest

## Git Commit Guidelines

- Git commit `Co-Authored-By` trailer: use the **active assistant's** co-author identity — target-aware, not hardcoded to one assistant. On Claude it is `Co-Authored-By: Claude <noreply@anthropic.com>`; on another target it is that target's assistant co-author identity. This is the convention `plan-marshall:workflow-integration-git` applies at commit time. No marketing claims.
