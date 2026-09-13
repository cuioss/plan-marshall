# Permission Architecture

## Provenance: Claude rule-pack

This document describes the **Claude** permission model's settings architecture. Every
statement here — the settings file hierarchy, the resolution priority, the file-placement
decision tree, and the permission grammar examples — binds only when the target is Claude.
On a non-Claude target the settings paths, resolution order, and grammar may differ
entirely; a reader should not assume any of these rules apply without confirming the
target's own permission model first.

The split is structural: this document is the Claude-specific half of the permission
standards, declared alongside the target-agnostic analysis engine in `permission_doctor.py`.
See `plugin-doctor/references/rule-provenance.md` § "Engine / Claude rule-pack split" for
the architectural precedent.

## `Write(...)` Does Not Grant — `Edit(...)` Does

Claude's file-permission checks consult `Edit(...)` rules only. A `Write(...)` allow rule is
matched by nothing at permission-check time, so it grants no filesystem access — it is inert.
`Edit(...)` is the only rule form that grants write access to a path, and it covers file
creation as well as modification. Every grammar example in this document therefore spells a
file-mutation grant as `Edit(...)`, and never pairs one with a `Write(...)` rule.

The asymmetry cuts both ways, and both directions are security-relevant:

- A `Write(...)` allow rule reported as a risk is a **false positive** — it grants nothing.
- An `Edit(...)` rule left unreported is a **false negative** — it is the rule that grants.

### The Swept Population

The sites carrying a write-intent permission matcher are enumerated below by count and by
path, so a later reader can re-derive the set rather than trust this table. The sweep matches
the **escaped** form (`Write\(` / `Edit\(`), because permission matchers hold their patterns
as regexes.

| Path | Sites with a matcher for write intent |
|------|-------------------------------------:|
| `tools-permission-doctor/scripts/permission_doctor.py` | 12 |
| `platform-runtime/scripts/_claude_runtime_impl.py` | 2 |
| `tools-permission-doctor/standards/permission-anti-patterns.md` | 2 |
| **Total (3 files)** | **16** |

At the time this population was swept, all 16 sites were spelled `Write(...)` and **not one**
was spelled `Edit(...)`: every regex in the swept population that matched a permission rule for
write intent matched the form that grants nothing, and none matched the form that grants.
That is the false premise stated as a measurement, and it is what the correction re-keys. The
claim is bounded by that population — read the Coverage Split below for which substrates it
covers and how each was evaluated.

**Why the escaped form is the matcher.** Sweeping the unescaped literal `Write(` instead
returns a larger set that **omits `permission_doctor.py` entirely** — the very file holding 12 of
the 16 sites — because permission matchers store their patterns regex-escaped. The unescaped sweep
is not a coarser version of this population; it is a different set that omits its largest member.

### Coverage Split

The zero above is an evaluated zero over a stated substrate, not a whole-tree clean negative.
Each substrate is reported with how it was evaluated, so an unevaluated region is visible as
such instead of being absorbed into the zero.

| Substrate | How evaluated | Result |
|-----------|---------------|--------|
| Architecture inventory | `architecture search --content`, escaped form; no unreadable files, no elision, not truncated | 16 write-intent matcher sites across 3 files |
| `.claude/settings.json` | read directly | 0 `Write(...)` rules; its one file-mutation grant is spelled `Edit(.plan/**)` |
| `.claude/**` remainder — `git ls-files .claude` less the row above | every member read as UTF-8 text; 46 of 46 read, 0 unread | 0 `Write(` sites; 0 `Edit(` sites |

`.claude/**` sits outside the architecture inventory (`architecture find --pattern '.claude/**'`
returns 0), so it is reported on its own rows rather than folded into the inventory's zero, and its
substrate is stated as a reproducible rule rather than a bare count: re-run `git ls-files .claude`,
drop the one file the row above covers, and the remainder is what this row's zero ranges over. The
read count and the substrate are therefore drawn from one population, and a member that could not be
read would appear as `unread` rather than silently narrowing the zero. Were any part of the
remainder unread, this row would record that part as unevaluated rather than fold it into the zero —
an unmeasured region published as a clean negative is the same class of false premise this section
exists to correct.

## Settings File Hierarchy

Claude Code uses a three-level settings hierarchy:

1. **Global Settings** (`~/.claude/settings.json`) - User-wide defaults
2. **Project Settings** (`.claude/settings.json`) - Version-controlled project settings
3. **Local Settings** (`.claude/settings.local.json`) - Personal/untracked overrides

### Resolution Priority

These are the preferences the `tools-permission-*` selectors apply when they must pick **one**
project file to read from or write to. They resolve in opposite orders, and each direction picks
whichever file is more specific to the question it is answering.

**For reading/discovery:**
- If `.claude/settings.local.json` exists, it is read; otherwise `.claude/settings.json` is read
- Local settings therefore take precedence over project settings on this path

**For writing:**
- If `.claude/settings.json` exists, write to it (version-controlled)
- Otherwise, write to `.claude/settings.local.json` (personal)

Global settings (`~/.claude/settings.json`) are a separate scope, addressed by `--scope global`
rather than by either preference above; the project selectors never fold them in.

Both selectors return a single path, so neither direction merges the two files — a read that lands
on one of them does not see the other. The single home for both is
`platform-runtime/scripts/claude_runtime.py`
(`_claude_project_settings_read_path` and `_claude_project_settings_path`); this section describes
what those return, and is not a statement about how Claude Code itself layers the three files at
runtime.

### When to Use Each File

| File | Use Case | Git Tracked |
|------|----------|-------------|
| `~/.claude/settings.json` | Universal permissions for all projects | N/A |
| `.claude/settings.json` | Team-shared project permissions | Yes |
| `.claude/settings.local.json` | Personal overrides, temporary permissions | No |

## Global vs Local Separation

**Global Permissions** (`~/.claude/settings.json`):
- Apply to ALL projects universally
- `Read(//~/git/**)` - Universal read access to all git repositories
- All marketplace skills
- `WebFetch(domain:<specific-domain>)` - Trusted domains for web access
- All common Bash commands (git, mvn, grep, find, etc.)

**Project Permissions** (`.claude/settings.json`):
- Version-controlled, shared with team
- Project-specific `Edit(...)` permissions
- Project-specific script execution permissions
- Custom domain permissions for project needs

**Local Permissions** (`.claude/settings.local.json`):
- Personal overrides not shared with team
- Temporary/experimental permissions
- Individual developer preferences
- **Use when**: testing new permissions, personal tooling

**Key Principle:** Use `.claude/settings.json` for team-shared permissions, `.claude/settings.local.json` for personal overrides.

## Universal Access Pattern

- `Read(//~/git/**)` provides universal git access (covers all repos)
- All skills available globally (marketplace skills)
- WebFetch requires explicit domain permissions (see web-security-standards skill)
- No duplication needed in local settings

## Permission Categorization

**Should be Global:**
- Common developer tools (Bash commands)
- Universal read access patterns
- Shared skills and standards
- Common documentation domains

Examples of global permissions:
```text
Read(//~/git/**)
Bash(git:*)
Bash(mvn:*)
Bash(npm:*)
WebFetch(domain:docs.anthropic.com)
WebFetch(domain:docs.github.com)
Skill(cui-java-skills:*)
Skill(cui-frontend-skills:*)
```

**Should be Local:**
- Project-specific `Edit(...)` permissions
- Project-specific script execution
- Project-specific tool configurations

Examples of local permissions:
```text
Edit(//~/git/my-project/**)
Bash(~/git/my-project/scripts/*)
```

The `Edit(...)` rule alone grants file modification for that path. Adding a matching
`Write(//~/git/my-project/**)` rule would grant nothing further — it is inert.

## Decision Tree

When adding a new permission, follow this decision tree:

1. **Is this permission needed across ALL projects?**
   - YES → Add to global settings
   - NO → Continue to step 2

2. **Does this permission modify files?**
   - YES → Add to local settings, as an `Edit(...)` rule. A `Write(...)` rule grants nothing
     and must not be added in its place or alongside it.
   - NO → Continue to step 3

3. **Is this a Read permission for git repositories?**
   - YES → Already covered by `Read(//~/git/**)` global permission
   - NO → Continue to step 4

4. **Is this a common development tool?**
   - YES → Add to global settings
   - NO → Add to local settings

## Architecture Patterns

### Pattern 1: New Project Setup

When setting up a new project in local settings:
```json
{
  "allowed": {
    "edit": [
      "//~/git/new-project/**"
    ]
  }
}
```

### Pattern 2: Project with Custom Scripts

If project has custom scripts:
```json
{
  "allowed": {
    "edit": [
      "//~/git/project-with-scripts/**"
    ],
    "bash": [
      "~/git/project-with-scripts/scripts/*"
    ]
  }
}
```

### Pattern 3: Multiple Projects in Same Workspace

For multiple related projects, use separate local settings per project:
```text
~/git/project-a/.claude/settings.local.json
~/git/project-b/.claude/settings.local.json
```

Do NOT combine in global settings - keeps permissions scoped appropriately.



**Note**: Plan files are NOT git-tracked (excluded by `.gitignore` via `.claude/*` pattern). They are session working documents.

## Anti-Patterns to Avoid

### FAIL Duplicating Read Permissions Locally

```json
{
  "allowed": {
    "read": [
      "//~/git/my-project/**"  // WRONG: Already covered globally
    ]
  }
}
```

### FAIL Adding Edit Permissions Globally

```json
{
  "allowed": {
    "edit": [
      "//~/git/**"  // WRONG: Too broad, security risk
    ]
  }
}
```

### FAIL Using Wildcards in WebFetch Domains

```json
{
  "allowed": {
    "webfetch": [
      "domain:*"  // WRONG: Invalid syntax, security risk
    ]
  }
}
```

## Permission Scope Examples

### PASS Correct Global Settings

```json
{
  "allowed": {
    "read": [
      "//~/.claude/**",
      "//~/git/**",
      "//.claude/**",
      "//claude/**",
      "//standards/**",
      "//scripts/**"
    ],
    "bash": [
      "git:*",
      "mvn:*",
      "./mvnw:*",
      "npm:*",
      "python3:*",
      "docker:*"
    ],
    "skill": [
      "cui-java-skills:*",
      "cui-frontend-skills:*",
      "plan-marshall:*"
    ],
    "webfetch": [
      "domain:docs.anthropic.com",
      "domain:docs.github.com",
      "domain:docs.oracle.com"
    ]
  }
}
```

### PASS Correct Local Settings

```json
{
  "allowed": {
    "edit": [
      "//~/git/plan-marshall/**"
    ]
  }
}
```
