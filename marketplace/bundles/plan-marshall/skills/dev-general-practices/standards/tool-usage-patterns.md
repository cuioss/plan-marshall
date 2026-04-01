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

See `file-operations.md` for file/directory patterns and `search-operations.md` for content search patterns.

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
Bash(command="gh pr checks 71 --watch")

# GOOD - CI integration scripts
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title ...
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments
```

If a needed operation is missing from the CI abstraction, extend the scripts — do not bypass them. See `plan-marshall:tools-integration-ci` for the complete API. For the full automated review lifecycle, load `Skill: plan-marshall:workflow-integration-ci`.

**Build commands** (MUST resolve via architecture API first):
```
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --name {module} --trace-plan-id {plan_id}
# Then execute the returned 'executable' value
```

Never hard-code build commands (`./pw`, `./mvnw`, `mvn`, `npm`, `gradle`). The architecture API is the single source of truth.

**External tools:** Version control (git), containers (docker, kubectl), build systems (after resolving via architecture API).

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

- **Glob once, then Read selectively** -- discover files first, read only what you need
- **Grep with output_mode** -- use `files_with_matches` for discovery, `content` for details
- **Search once, parse multiple times** -- broad regex, then filter results in memory
