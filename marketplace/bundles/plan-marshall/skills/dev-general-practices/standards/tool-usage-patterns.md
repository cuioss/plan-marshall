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

**Git operations:**
```
Bash(command="git status")
Bash(command="git log --oneline -10")
```

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

### No heredocs with # lines

Heredocs containing `#`-prefixed lines trigger security prompts. Write to a temp file instead:
```
Write(file_path=".plan/temp/pr-body.md", content="## Summary\n...")
Bash(command="some-cli --body-file .plan/temp/pr-body.md")
```

## Performance Tips

- **Glob once, then Read selectively** — discover files first, read only what you need
- **Grep with output_mode** — use `files_with_matches` for discovery, `content` for details
- **Progressive filtering** — start with `files_with_matches` to find relevant files, then `content` on those files for details
