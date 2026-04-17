# Rule Catalog

Rules that plugin-doctor validates in other components. See the Enforcement block in SKILL.md for this skill's own constraints.

> **Related**: For architectural principles with rationale and examples, see `plugin-architecture:architecture-rules`. This catalog lists validation rules only.

## Agent Rules

**agent-task-tool-prohibited**: Agents cannot declare the Task tool (unavailable at runtime).

**agent-maven-restricted**: Only the maven-builder agent may execute Maven commands.

**agent-lessons-via-skill**: Agents record lessons via manage-lessons skill, not self-invoke commands.

**agent-skill-tool-visibility**: Agents declaring explicit tools must include Skill, otherwise invisible to Task dispatcher.

## Workflow Rules

**workflow-explicit-script-calls**: All script/tool invocations in workflow documentation have explicit bash code blocks with the full `python3 .plan/execute-script.py` command.

**workflow-hardcoded-script-path**: Use executor notation (`bundle:skill:script`) instead of hardcoded file paths.

**workflow-prose-parameter-consistency**: Prose instructions adjacent to `execute-script.py` bash blocks must reference parameter values consistent with the actual script API.

## Command Rules

**command-self-contained-notation**: Components that execute scripts have the exact notation (`bundle:skill:script`) explicitly defined within themselves.

Four detection modes:

| Mode | Catches |
|------|---------|
| A: Delegation | "Execute command from section Nb" - parent-passed |
| B: Notation | `execute-script.py artifact_store` - missing bundle:skill |
| C: Missing Section | "Log the assessment" without ## Logging Command section |
| D: Parameters | `--plan-id` when should be positional (via --help) |

**command-thin-wrapper**: Commands delegate all logic to skills; they are thin orchestrators.

**command-progressive-disclosure**: Load skills on-demand, not all at once.

**command-completion-checks**: Mandatory post-fix verification after applying changes.

**command-no-embedded-standards**: No standards blocks in commands; standards belong in skills.

## Skill Rules

**skill-enforcement-block-required**: Script-bearing skills need an `## Enforcement` block.

**skill-unused-tools-declared**: Skills declare `allowed-tools` that are never referenced in SKILL.md content. Detection is structural (frontmatter extraction); semantic usage analysis is delegated to tool-coverage-agent.

**skill-naming-noun-suffix**: Skill directory names must not end with a reserved noun suffix (`-executor`/`-executors`, `-manager`/`-managers`, `-runner`/`-runners`, `-handler`/`-handlers`, `-orchestrator`/`-orchestrators`). These suffixes are reserved for spawnable marketplace agents. Skills must use verb-first names (e.g. `execute-task` instead of `task-executor`). See `pm-plugin-development:plugin-architecture` `references/skill-design.md` "Skill Naming Convention" for the full rationale. Detection runs during skill structure analysis.

## Script Rules

**argparse_safety** (severity: error): Flags every `argparse.ArgumentParser(...)` constructor call and every `subparsers.add_parser(...)` call in marketplace Python scripts that does not pass `allow_abbrev=False`. Scope: files under `marketplace/bundles/*/skills/*/scripts/` and `marketplace/adapters/`. Tests are exempt (files under `test/`/`tests/` directories or named `test_*.py` / `*_test.py`).

- **Rationale**: Without `allow_abbrev=False`, argparse matches unknown long options by unique prefix. When a flag is renamed or retired, old callers keep working silently via prefix binding — the contract rot is invisible until something behaves wrong under a rename. See driving lesson 2026-04-17-012 (argparse prefix-matching silently binds retired flags).
- **Fix**: Add `allow_abbrev=False` to the constructor or `add_parser(...)` call. The rule is a lightweight AST walk (no parser execution); it flags the exact line and call name (`ArgumentParser` or `add_parser`).
- **Exemptions**: Test files may intentionally exercise argparse default behavior and are excluded from the scan.

## Content Rules

**checklist-pattern**: Checkbox patterns (`- [ ]`, `- [x]`) in LLM-consumed files. These are human UI elements with zero value for LLMs. Exception: files in `/templates/` directories (rendered by GitHub).

## PM-Workflow Rules

**pm-implicit-script-call** (PM-001): Script operations without explicit bash code blocks.

**pm-generic-api-reference** (PM-002): Generic API references instead of specific script notation.

**pm-wrong-plan-parameter** (PM-003): Incorrect plan parameter values in script calls.

**pm-missing-plan-parameter** (PM-004): Missing required plan parameters.

**pm-invalid-contract-path** (PM-005): Invalid contract file path references.

**pm-contract-non-compliance** (PM-006): Contract specification violations.
