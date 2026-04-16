# Tool Usage Patterns

## Core Principle

Use non-prompting tools exclusively for file operations. Bash commands trigger user prompts; dedicated tools (Glob, Read, Grep) execute automatically.

## Tool Availability

When an agent's frontmatter lists required tools, those tools MUST be available. If not, abort with an error. Do not use workarounds or Bash fallbacks.

## Tool Selection Guide

| Operation | Use (no prompts) | Don't use (prompts) |
|-----------|-----------------|---------------------|
| Find files | `Glob` | `find`, `ls` |
| Check file exists | `Read` + error handling | `test -f`, `cat` |
| Check directory exists | `Glob` | `test -d` |
| Search content | `Grep` | `grep`, `rg` via Bash |
| Read files | `Read` | `cat`, `head`, `tail` |
| Count items | `Glob` + count results | `wc -l` via Bash |

## File Operations

**Single file existence** — use Read with error handling (also gives you the content):
```
Read(file_path="/path/to/file")
# Handle error gracefully if file doesn't exist
```

**Quick existence check** — use Glob (no content loaded):
```
Glob(pattern="filename", path="/parent/directory")
# Empty result means file doesn't exist
```

**Directory existence** — use Glob to check if a directory has contents:
```
Glob(pattern="*", path="/path/to/directory")
# Empty result = directory empty or doesn't exist
```

**File discovery by extension:**
```
Glob(pattern="**/*.md", path="/bundle/path")
```

**Content validation** — read and check frontmatter, required fields, etc.:
```
content = Read(file_path="/path/to/file")
# Check starts with "---", find closing "---"
# Extract and validate required fields
```

## Content Search

**Find files containing a pattern:**
```
Grep(pattern="search_term", path="/directory", output_mode="files_with_matches")
```

**Show matching lines with line numbers:**
```
Grep(pattern="pattern", path="/path", output_mode="content", -n=true)
```

**Count occurrences:**
```
Grep(pattern="pattern", path="/path", output_mode="count")
```

**Case-insensitive with context:**
```
Grep(pattern="todo", path="/path", output_mode="content", -i=true, -C=3)
```

**Filter by file type:**
```
Grep(pattern="pattern", path="/path", glob="*.md", output_mode="content")
```

## When Bash IS Appropriate

**Git operations** (always use `git -C {path}` — never `cd {path} && git ...`):
```
Bash(command="git -C /path/to/worktree status")
Bash(command="git -C /path/to/worktree log --oneline -10")
```

When a plan runs in an isolated worktree, `{path}` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. See [Git: use git -C, not cd+git](#git-use-git--c-not-cdgit) below for the rule and rationale.

**CI/Git provider operations (PRs, issues, CI status, reviews):**

All CI/Git provider operations MUST go through the CI integration abstraction layer. Direct `gh` or `glab` calls bypass provider abstraction, execution logging, and audit trail.

```
# BAD - Direct gh calls
Bash(command="gh pr create --title ...")

# GOOD - CI integration scripts
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title ...
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait
```

If a needed operation is missing from the CI abstraction, extend the scripts — do not bypass them.

**Build commands** (MUST resolve via architecture API first):
```
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --name {module} --trace-plan-id {plan_id}
# Then execute the returned 'executable' value
```

Never hard-code build commands (`./pw`, `./mvnw`, `mvn`, `npm`, `gradle`). The architecture API is the single source of truth.

## Bash Safety Rules

### One command per call

Each Bash call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, or `;`. If independent, make parallel Bash calls. If sequential, make separate calls.

### No shell constructs

`$()` substitution, `for` loops, `while` loops, and subshells all trigger Claude Code's security prompt. Make individual Bash calls per iteration instead.

### Git: use `git -C`, not `cd`+`git`

Every repo-targeted git command MUST use `git -C {path} <subcommand>`. The compound form `cd {path} && git <subcommand>` is forbidden because it (a) trips Claude Code's bare-repository security heuristic and pops a permission prompt that disrupts the user, and (b) is two commands joined by `&&`, violating the [One command per call](#one-command-per-call) rule above.

```
# BAD — security prompt + violates one-command-per-call
Bash(command="cd /path/to/worktree && git log --oneline -5")

# GOOD — single command, no prompt
Bash(command="git -C /path/to/worktree log --oneline -5")
```

When a plan runs in an isolated worktree, `{path}` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. When operating against the main checkout, use `git -C .` (or omit `-C` only when the current working directory is unambiguously correct) — never `cd && git`. The same rule applies inside `Skill: plan-marshall:workflow-integration-git` and any agent that delegates git to Bash.

### No heredocs with # lines

Heredocs containing `#`-prefixed lines trigger security prompts. Use the
path-allocate pattern — the script owns the scratch path, so callers never
invent one and no multi-line content crosses the shell boundary:

```
# Step 1: script allocates a scratch path bound to --plan-id
Bash(command="python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id my-plan")
# → returns {path: /abs/.../work/ci-bodies/pr-create-default.md}

# Step 2: Write tool writes the body directly to the returned path
Write(file_path="<path from prepare-body>", content="## Summary\n...")

# Step 3: consumer reads the prepared file and deletes it on success
Bash(command="python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title 'T' --plan-id my-plan --base main")
```

## Performance Tips

- **Glob once, then Read selectively** — discover files first, read only what you need
- **Grep with output_mode** — use `files_with_matches` for discovery, `content` for details
- **Progressive filtering** — start with `files_with_matches` to find relevant files, then `content` on those files for details
