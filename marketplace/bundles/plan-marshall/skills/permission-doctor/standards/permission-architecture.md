# Permission Architecture

## Settings File Hierarchy

Claude Code uses a three-level settings hierarchy:

1. **Global Settings** (`~/.claude/settings.json`) - User-wide defaults
2. **Project Settings** (`.claude/settings.json`) - Version-controlled project settings
3. **Local Settings** (`.claude/settings.local.json`) - Personal/untracked overrides

### Resolution Priority

**For reading/discovery:**
- Project settings (`.claude/settings.json`) takes precedence over local settings
- If `.claude/settings.json` exists, it is used; otherwise `.claude/settings.local.json` is used
- Global settings always apply as baseline

**For writing:**
- If `.claude/settings.json` exists, write to it (version-controlled)
- Otherwise, write to `.claude/settings.local.json` (personal)

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
- All CUI marketplace skills
- `WebFetch(domain:<specific-domain>)` - Trusted domains for web access
- All common Bash commands (git, mvn, grep, find, etc.)

**Project Permissions** (`.claude/settings.json`):
- Version-controlled, shared with team
- Project-specific Edit/Write permissions
- Project-specific script execution permissions
- Custom domain permissions for project needs

**Local Permissions** (`.claude/settings.local.json`):
- Personal overrides not shared with team
- Temporary/experimental permissions
- Individual developer preferences
- **Use when**: testing new permissions, personal tooling

**Key Principle:** Use `.claude/settings.json` for team-shared permissions, `.claude/settings.local.json` for personal overrides.

## Universal Access Pattern

As of 2025-10-27:
- `Read(//~/git/**)` provides universal git access (covers all repos)
- All CUI skills available globally (marketplace skills)
- WebFetch requires explicit domain permissions (see web-security-standards skill)
- No duplication needed in local settings

## Permission Categorization

**Should be Global:**
- Common developer tools (Bash commands)
- Universal read access patterns
- Shared skills and standards
- Common documentation domains

Examples of global permissions:
```
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
- Project-specific Edit/Write permissions
- Project-specific script execution
- Project-specific tool configurations

Examples of local permissions:
```
Edit(//~/git/my-project/**)
Write(//~/git/my-project/**)
Bash(~/git/my-project/scripts/*)
```

## Decision Tree

When adding a new permission, follow this decision tree:

1. **Is this permission needed across ALL projects?**
   - YES → Add to global settings
   - NO → Continue to step 2

2. **Does this permission modify files?**
   - YES (Edit/Write) → Add to local settings
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
    ],
    "write": [
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
    "write": [
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
```
~/git/project-a/.claude/settings.local.json
~/git/project-b/.claude/settings.local.json
```

Do NOT combine in global settings - keeps permissions scoped appropriately.



**Note**: Plan files are NOT git-tracked (excluded by `.gitignore` via `.claude/*` pattern). They are session working documents.

## Anti-Patterns to Avoid

### ❌ Duplicating Read Permissions Locally

```json
{
  "allowed": {
    "read": [
      "//~/git/my-project/**"  // WRONG: Already covered globally
    ]
  }
}
```

### ❌ Adding Edit/Write Permissions Globally

```json
{
  "allowed": {
    "edit": [
      "//~/git/**"  // WRONG: Too broad, security risk
    ]
  }
}
```

### ❌ Using Wildcards in WebFetch Domains

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

### ✅ Correct Global Settings

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

### ✅ Correct Local Settings

```json
{
  "allowed": {
    "edit": [
      "//~/git/plan-marshall/**"
    ],
    "write": [
      "//~/git/plan-marshall/**"
    ]
  }
}
```
