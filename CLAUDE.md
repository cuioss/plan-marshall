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

The set is the convention because `.github/workflows/python-verify.yml` restricts its **push-triggered** runs to `main`, `feature/*`, `fix/*`, `chore/*`, and `dependabot/**`; a branch with any other prefix gets no push build. That branch filter governs the `push:` trigger only — the `pull_request:` trigger filters on the **base** branch (`main`), so a PR from any head branch is still verified and still produces the required `verify / conclusion` check. The `docs/` prefix is retired — use `chore/` for documentation-only changes.

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

**One bounded exception:** a plan executed from `doc/plans/` runs in the standalone plan lane, which supersedes several of these rules because the machinery they name is unavailable there. See [Standalone Plan Lane](#standalone-plan-lane-docplans) below for the exact carve-out. Outside that lane, every rule here binds without exception.

- **`.plan/` access: scripts only** — ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py` manage-* scripts. Never Read/Write/Edit `.plan/` files directly unless a loaded skill's workflow explicitly documents it.
- **Bash: one command per call** — Each Bash call must contain exactly ONE command. Never combine with `&&`, `;`, `&`, or newlines.
- **Bash: no shell constructs** — No `for`/`while` loops, no `$()` substitution, no subshells, no heredocs with `#` lines. Use dedicated tools or multiple Bash calls instead.
- **No shell file operations** — Use Read/Write/Edit/Glob/Grep, never `cat`, `head`, `find`, `ls`, `grep`, or git's `grep` subcommand via Bash. When the question is about file CONTENT ("which file contains X?"), the remedy is `architecture search --content --pattern P` — see `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § search.
- **Workflow steps: no improvisation** — When following a skill or workflow, execute ONLY the documented commands. Never add discovery steps, invent arguments, or skip steps.
- **CI operations: use abstraction layer** — All CI/Git provider operations (PRs, issues, CI status, reviews) MUST go through `plan-marshall:tools-integration-ci:ci` scripts. Never use `gh` or `glab` directly.
- **Build commands: resolve via architecture** — Never hard-code `./pw`, `mvn`, `npm`, or `gradle`. Always resolve via `plan-marshall:manage-architecture:architecture resolve` first, then run the returned `executable`.
- **Triage findings via manage-findings + ext-triage** — Triage decisions on findings (Sonar / PR review / build / lint / test) flow through `manage-findings` + `ext-triage-{domain}`; ambiguous cases escalate via `AskUserQuestion`.
- **Structured queries first** — Before using Glob/Grep for codebase navigation (file discovery, module identification, path resolution, content search), consult `architecture files --module X`, `architecture which-module --path P`, `architecture find --pattern P` (path glob), or `architecture search --content --pattern P` (file content).
- **`search --content` is inventory-scoped** — the content sweep covers the crawled inventory, so always-ignored directories (`.git`, `node_modules`, `target`, caches), anything a `.gitignore` rule excludes (including `.plan/`), and dotfile trees outside the allowlist (`.claude/**`, `.github/**`) are **not** searched. A zero result is a trustworthy *"not in any inventoried file"* — it is **not** *"not in the tree"*. When the target may live outside the inventory, fall back to `Glob`/`Grep`/`Read` scoped to that path; when those tools are unavailable in the current envelope, surface the coverage gap rather than reporting a clean negative. And a `count: 0` is only trustworthy when the sweep's coverage is clean — see `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § search → "Complete-coverage rule" for the canonical field list.
- **Temp files under `.plan/temp/`** — Use `.plan/temp/` for ALL temporary and generated files (covered by the `Write(.plan/**)` permission).
- **GitHub access** — Use the `gh` tool (via the CI abstraction), not MCP.

## Standalone Plan Lane (`doc/plans/`)

Plans under `doc/plans/` execute **outside the plan-marshall command lifecycle** — no `/plan-marshall`, no `/marshall-orchestrator`, no `.plan/execute-script.py`, no `.plan/` state at all. The lane exists because `.plan/` is git-ignored: its state (plan directories, orchestrator ledgers, findings, locks, and the generated executor) lives only on the machine that created it, so a cloud session at claude.ai/code clones the repository and has none of it. Everything a `doc/plans/` plan needs is in git.

**The complete working contract is the `cloud-plan-lane` skill** (`.claude/skills/cloud-plan-lane/SKILL.md`), loaded as the first action of every run:

```text
Skill: cloud-plan-lane
```

It owns the plan directory lifecycle, the conditional Python build gate, the pre-PR verification sub-agent, the branch/PR/review-comment cycle, the merge gate, the persisted run report, and the closing self-check. See `doc/plans/README.md` for the tree layout.

Within this lane only, these hard rules are superseded — the tooling they mandate depends on the generated executor, which does not exist in a fresh clone:

| Hard rule | Replaced by |
|-----------|-------------|
| Build commands: resolve via architecture | `./pw verify` called directly, gated on a git-derived Python-change check |
| CI operations: use abstraction layer | The GitHub MCP server (the cloud path) or `gh` directly |
| GitHub access: `gh`, not MCP | The GitHub MCP server is the expected path in a cloud session |
| `.plan/` access: scripts only | Not applicable — the lane never touches `.plan/` |
| Temp files under `.plan/temp/` | The system temp dir (`$TMPDIR`) — never the repository, never `.plan/` |
| Structured queries first | Not applicable — `architecture` requires the executor; Glob/Grep/Read are used instead |
| Triage findings via manage-findings + ext-triage | Findings recorded per instance in the run report |

Two further obligations stated elsewhere in this document do not apply in the lane. **Plugin Cache Sync** is inert there: `/sync-plugin-cache` reads the git-ignored `target/` tree and writes `~/.claude/`, neither of which a fresh clone has or the lane may touch — a lane plan that edits `marketplace/bundles/` records in its run report that a local sync is owed. And **No shell file operations** binds with one clarification: `git mv` and `mkdir -p` are permitted for the plan-directory step, since that rule's target is reading and searching file content, which still goes through Read/Glob/Grep.

One narrow documentation-standards exemption applies: a lane **run report** (`doc/plans/{epic}/{plan-name}/report-NN.md`) carries a date and an ordinal, because it is a dated record of one execution rather than documentation of the current state. The "No timestamps" and "Current state only" standards govern documentation; they do not govern records. No other file in `doc/plans/` takes this exemption — the plan itself and every README follow the standards unchanged.

**Branch naming in a cloud session.** A Claude Code cloud session pre-assigns a branch named `claude/{slug}-{hash}` and refuses to push to a different branch without explicit operator permission, so requiring a closed-set prefix fires an operator prompt on every cloud run and defeats unattended operation. A cloud session therefore MAY keep its harness-assigned branch. The closed prefix set applies to branches the run itself creates — every local run, and a cloud run where no branch was pre-assigned. This is safe because CI verifies the PR regardless of head-branch name: the branch filter in `python-verify.yml` governs push-triggered runs only, while `pull_request:` matches on the base branch (see [Branch Naming](#branch-naming)). The run records in its report which branch form it used.

Every other rule — the rest of the documentation standards, the one-command-per-Bash-call discipline — binds in this lane exactly as elsewhere. This carve-out is scoped to `doc/plans/` execution and to nothing else; ordinary work in this repository, including work done in a cloud session that is not executing a `doc/plans/` plan, follows the hard rules unchanged.

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
