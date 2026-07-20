# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Repository Overview

This is a **Claude Code Marketplace** repository providing development standards, automation tools, and AI-assisted workflows for CUI (Common User Interface) Open Source projects. It contains 10 production bundles with 149 registered components (145 skills, 2 agents, 2 commands) that integrate with Claude Code's plugin system. For the bundle-by-bundle catalogue and directory layout, read the filesystem under `marketplace/bundles/` or `doc/developer/`.

## Branch Naming

Working branches MUST use one of exactly three canonical prefixes (the set is closed):

| Prefix | Applies to |
|--------|------------|
| `feature/` | New capabilities. Plan-created branches are auto-generated as `feature/{plan_id}`. |
| `fix/` | Bug fixes. |
| `chore/` | Maintenance, refactoring, and documentation-only changes. |

The set is closed because `.github/workflows/python-verify.yml` triggers CI only for `main`, `feature/*`, `fix/*`, `chore/*`, and `dependabot/**`; a branch with any other prefix receives no CI run, so its PR can never produce the required `verify / conclusion` check. The `docs/` prefix is retired — use `chore/` for documentation-only changes.

`python-verify.yml` opts in to a footprint gate (`skip-on-docs-only: true`): a docs-only change (no buildable source) skips the heavy pyprojectx build while the required `verify / conclusion` check still reports green, so the merge queue admits it without stalling. See `.github/workflows/python-verify.yml` for the non-building path set and the exact skip mechanics.

## Script Execution Convention

All marketplace scripts run through the generated executor — never by direct path:

```bash
python3 .plan/execute-script.py {bundle}:{skill}:{script} [subcommand] {args...}
```

Example: `python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add --plan-id my-plan --file task.md`

Regenerate the executor after bundle changes with `/marshall-steward`. See `pm-plugin-development:plugin-script-architecture` for script implementation standards.

## Build Commands

Never hard-code build commands (`./pw`, `mvn`, `npm`, `gradle`) — use the resolved executor commands:

- Compile: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "compile"`
- Quality gate: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"`
- Tests: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"`
- Full verify: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`
- Coverage: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage"`

Append a module name (e.g. `"verify plan-marshall"`) to scope to a single bundle. Always call build commands with a Bash timeout of at least 10 minutes (600000ms); when the architecture-resolved envelope carries `bash_timeout_seconds`/`execution_tier`, pass `timeout: bash_timeout_seconds * 1000` for `execution_tier=per_task`, or hand off to the orchestrator for `execution_tier=orchestrator` (see `plan-marshall:persona-plan-marshall-agent` § "Bash: Timeout from architecture-resolved canonical command"). After each build call, read the result TOON `status`/`errors[]` — the wrapper exits 0 even on failure. See `doc/developer/build.adoc` for build system details.

## Workflow Discipline (Hard Rules)

These rules apply to ALL work in this repository — ad-hoc tasks, plan execution, and agent work alike. They exist because Claude regularly violates them despite softer guidance.

- **`.plan/` access: scripts only** — ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py` manage-* scripts. Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it.
- **Bash: one command per call** — Each Bash call must contain exactly ONE command. Never combine with `&&`, `;`, `&`, or newlines.
- **Bash: no shell constructs** — No `for`/`while` loops, no `$()` substitution, no subshells, no heredocs with `#` lines. Use dedicated tools or multiple Bash calls instead.
- **No shell file operations** — Use Read/Write/Edit/Glob/Grep, never `cat`, `head`, `find`, `ls`, or `grep` via Bash.
- **Workflow steps: no improvisation** — When following a skill or workflow, execute ONLY the documented commands. Never add discovery steps, invent arguments, or skip steps.
- **CI operations: use abstraction layer** — All CI/Git provider operations (PRs, issues, CI status, reviews) MUST go through `plan-marshall:tools-integration-ci:ci` scripts. Never use `gh` or `glab` directly.
- **Build commands: resolve via architecture** — Never hard-code `./pw`, `mvn`, `npm`, or `gradle`. Always resolve via `plan-marshall:manage-architecture:architecture resolve` first, then run the returned `executable`.
- **Triage findings via manage-findings + ext-triage** — Triage decisions on findings (Sonar / PR review / build / lint / test) flow through `manage-findings` + `ext-triage-{domain}`; ambiguous cases escalate via `AskUserQuestion`.
- **Structured queries first** — Before using Glob/Grep for codebase navigation (file discovery, module identification, path resolution), consult `architecture files --module X`, `architecture which-module --path P`, or `architecture find --pattern P`.
- **Temp files under `.plan/temp/`** — Use `.plan/temp/` for ALL temporary and generated files (covered by the `Write(.plan/**)` permission).
- **GitHub access** — Use the `gh` tool (via the CI abstraction), not MCP.

## Documentation Standards

- **No version history** — Never add changelogs, "RECENT CHANGES", or dated update sections.
- **No timestamps** — No dates or version numbers in document content.
- **No duplication** — Cross-reference instead of duplicating information.
- **Current state only** — Document present requirements, not transitional information.
- **AsciiDoc formatting** — Blank line before lists; use `xref:` cross-references.

## Plugin Cache Sync

After editing files in `marketplace/bundles/`, changes don't take effect until the plugin cache is synced. Run `/sync-plugin-cache` (project-local under `.claude/skills/`), which reads from `target/claude/` and mirrors bundles to `~/.claude/plugins/cache/plan-marshall/`. On-main executor regeneration happens at finalize via `project:finalize-step-sync-plugin-cache`. This surface is meta-project-only — consumer projects of plan-marshall do not get it. For the deeper detail (registered marketplace path, one-time developer-machine migration, manual recovery when a commit landed without phase-6-finalize), see `doc/developer/marketplace-build.adoc` and `doc/developer/manual-sync-recovery.adoc`.

## Multi-Assistant Support

Source of truth is `marketplace/bundles/*` (Claude Code native format). The multi-target generator (`python3 marketplace/targets/generate.py --target {claude,opencode,all} --output {dir}`) exports bundles to other assistant formats while keeping Claude Code primary; **only Claude Code is tested as a runtime.** See `doc/developer/marketplace-build.adoc` for the adapter system, OpenCode usage, adding new targets, and how the format relates to the SKILL.md open standard at [agentskills.io](https://agentskills.io).

## Integration Points

- **Git/GitHub**: `gh` tool (via the CI abstraction) for issue/PR management.
- **Build Systems**: Pyprojectx wrapper (`./pw`) for Python testing/linting — invoked only through the resolved executor.
- **IDE**: IntelliJ MCP for diagnostics (file must be active in editor).
