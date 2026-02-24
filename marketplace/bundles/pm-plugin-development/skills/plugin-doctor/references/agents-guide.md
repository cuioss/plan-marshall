# Agent Quality Standards

Agents are specialized execution units invoked via Task tool by commands. They execute autonomously and return results to the caller.

**Key constraints**: Cannot invoke other agents (Task unavailable at runtime). Cannot invoke commands (SlashCommand unavailable).

## Required Frontmatter

```yaml
---
name: agent-name                            # kebab-case, matches filename
description: One-sentence purpose statement
tools:                                      # array format, must include Skill
  - Read
  - Write
  - Skill
model: sonnet                               # optional, defaults to sonnet
---
```

Common errors: comma-separated tools string (`tools: Read, Write` — wrong), missing `name`/`description`, invalid YAML.

## Tool Coverage

**Tool fit score** = `used_tools / (used_tools + missing_tools) * 100`

| Rating | Threshold |
|--------|-----------|
| Excellent | >= 90% |
| Good | >= 70% |
| Needs improvement | >= 50% |
| Poor | < 50% |

**Target**: >= 90%. Add missing tools (used but undeclared — causes runtime failure). Remove unused tools (declared but not used — over-specification).

Prohibited tools: `Task` (agent-task-tool-prohibited), `SlashCommand` (architectural violation).

## Critical Rules

### agent-task-tool-prohibited

Agents cannot declare or use Task tool (unavailable at runtime). Detection: check frontmatter `tools` for "Task", search content for `subagent_type` patterns. Fix: convert to command, inline logic, or use Skill invocation.

### agent-maven-restricted

Only `maven-builder` agent may execute Maven commands. Detection: search for `mvn`, `./mvnw`, `maven` in Bash calls. Fix: delegate to maven-builder agent via Task tool from the calling command.

### agent-lessons-via-skill

Agents report improvements to caller (not self-invoke commands). The CONTINUOUS IMPROVEMENT RULE section should use the caller-reporting pattern: "report to caller" + structured suggestion. Violation: direct `/plugin-update-agent` invocation instructions.

### command-self-contained-notation

Script commands must be explicitly defined with exact `bundle:skill:script` notation. Four detection modes: (A) delegation patterns, (B) malformed notations, (C) missing command sections, (D) wrong parameters vs `--help`.

### agent-skill-tool-visibility

Agents with explicit `tools:` declarations must include `Skill` to be visible to the Task dispatcher. No violation if `tools:` field is absent (inherits all). Safe fix: append `Skill` to tools list.

## Bloat Thresholds

| Classification | Lines | Action |
|---------------|-------|--------|
| NORMAL | < 300 | Healthy |
| LARGE | 300-500 | Review for extraction |
| BLOATED | 500-800 | Refactor required |
| CRITICAL | > 800 | Immediate refactoring |

Anti-bloat strategies: extract standards to reference files, use Skill dependencies, condense workflow steps, move deterministic logic to scripts.

## Best Practices

- **Single responsibility**: one agent, one focused task
- **Deterministic logic in scripts**: pattern matching, JSON parsing, validation in scripts; judgment and context interpretation in agent
- **Progressive disclosure**: load references on-demand, not all upfront
- **Error handling**: validate inputs, return structured errors with clear messages
- **Output format**: return JSON with `status`, `issues`, counts
- **Tool efficiency**: use Read/Grep/Glob/Edit instead of Bash equivalents; Bash only for builds, git, tests, script execution
- **Required sections**: Purpose, PARAMETERS, WORKFLOW, CONTINUOUS IMPROVEMENT RULE

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Low tool fit score | < 70% score | Add missing tools, remove unused tools |
| Task tool in agent | `Task` in frontmatter | Convert to command or use Skill |
| Direct Maven usage | `mvn`/`./mvnw` calls | Delegate to maven-builder |
| Self-invocation | `/plugin-update-agent` in CI rule | Use caller-reporting pattern |
| Bloat > 500 lines | BLOATED/CRITICAL classification | Extract standards, use skills, condense |

## Summary Checklist

- Frontmatter valid (name, description, tools array with Skill)
- Tool fit score >= 90%
- No agent-task-tool-prohibited violations
- No agent-maven-restricted violations
- No agent-lessons-via-skill violations
- No command-self-contained-notation violations
- No agent-skill-tool-visibility violations
- All script notations match `bundle:skill:script` format
- Bloat classification NORMAL (< 300 lines)
- CONTINUOUS IMPROVEMENT RULE present (caller-reporting)
