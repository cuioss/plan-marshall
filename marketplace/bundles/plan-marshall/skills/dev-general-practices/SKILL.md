---
name: dev-general-practices
description: Foundational development practices covering user interaction, tool usage, research, dependency management, and document proliferation
user-invocable: false
---

# Development Practices Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Foundational development practices applicable across all technology stacks and development activities. Covers when to ask users, how to research best practices, proper tool usage, document management, and dependency governance.

## Workflow

### Step 1: Load Core Development Rules

**Important**: Load this standard at the start of any development work.

```
Read: standards/general-development-rules.md
```

Covers Boy Scout Rule, decision tree for when to ask users, research patterns, tool selection guide, document proliferation guidelines, and dependency approval.

### Step 2: Load Tool Usage Standards (As Needed)

**Tool usage patterns** (load for file operations, content search, or automation work):
```
Read: standards/tool-usage-patterns.md
```

Covers tool selection guide, file operations (discovery, existence checks, validation), content search patterns (Grep modes, filtering), Bash safety rules (one command per call, no shell constructs, no heredocs), and build command resolution via architecture API.

### Step 3: Load Script Argument Naming Conventions (As Needed)

**Script argument naming** (load when authoring or invoking `plan-marshall` `manage-*` scripts):
```
Read: standards/argument-naming.md
```

Covers typed-ID flags (`--lesson-id`, `--plan-id`, `--task-number`, `--module`, `--component`), read-verb canonicalization (`read` vs `get` vs `exists`), `--module` vs `--name`, and Python-stdlib log-level naming. Includes the canonical-forms table for in-scope `manage-*` scripts.

## Hard Rules (never override)

### Bash: One command per call

Each Bash tool call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, or `;`.

### Bash: No file operations

Never use Bash for file discovery or reading. Use Glob, Grep, Read instead.

### Skill workflow: No improvisation

Execute ONLY the commands documented in the loaded skill's workflow. Never add discovery steps, invent arguments, or skip documented steps.

### Git: always use `git -C {path}`, never `cd {path} && git ...`

Every repo-targeted git command MUST use the `git -C {path} <subcommand>` form. The compound form `cd {path} && git <subcommand>` is forbidden — even when the target path is a worktree absolute path that the model already has in context.

Two reasons, both load-bearing:

1. **Security prompt**: Claude Code treats `cd` followed by `git` in the same Bash call as a potential bare-repository-attack pattern and pops a permission prompt that disrupts the user. The `-C` form does not trip the heuristic.
2. **One-command-per-call**: `cd {path} && git ...` is two commands joined by `&&`, which already violates the [Bash: One command per call](#bash-one-command-per-call) rule above. Using `git -C {path} ...` is one command and satisfies both rules at once.

When a plan runs in an isolated worktree, the canonical `{path}` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. When operating against the main checkout, use `git -C .` — never `cd && git`.

## Related

- `dev-general-code-quality` — Complementary quality standards (SRP, CQS, complexity)
- `dev-general-module-testing` — Testing methodology standards (AAA pattern, coverage)

## Standards Reference

| Standard | Purpose |
|----------|---------|
| general-development-rules.md | Boy Scout Rule, ask users, research, tool usage, dependencies |
| tool-usage-patterns.md | Tool selection, file operations, content search, Bash safety, build resolution |
| argument-naming.md | Typed-ID flags, read-verb canonicalization, `--module` over `--name`, stdlib log-level names for `manage-*` scripts |
