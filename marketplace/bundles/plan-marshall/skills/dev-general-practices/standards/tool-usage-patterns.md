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

When a plan runs in an isolated worktree, `{path}` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. When operating against the main checkout, use `git -C .` — never `cd && git`. The same rule applies inside `Skill: plan-marshall:workflow-integration-git` and any agent that delegates git to Bash.

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

### No sleep for external waits

`sleep N` and `until <check>; do sleep ...; done` are forbidden for blocking on
external conditions (CI status changes, PR bot comments, issue state
transitions, label propagation, etc.). A bare `sleep` in an agent/skill blocks
the turn for the full duration, defeats the Monitor-driven notification model,
and is what the Bash safety harness already blocks via its "long leading sleep"
heuristic.

Instead, dispatch to the CI abstraction's `wait-for-*` subcommands — they
implement bounded polling with proper exit codes, timeout handling, and
structured TOON output:

- `pr wait-for-comments --pr-number N --timeout SECS` — block until new bot
  review comments land (or timeout)
- `ci wait-for-status-flip --ref REF --timeout SECS` — block until the CI
  status on a ref transitions (queued → running → success/failure)
- `issue wait-for-close --issue-number N --timeout SECS` — block until an
  issue is closed
- `issue wait-for-label --issue-number N --label L --timeout SECS` — block
  until a specific label is applied (or removed, depending on mode)

If no existing subcommand covers your signal, **extend the CI abstraction**:
add a new `wait-for-*` parser entry in
`marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
alongside the existing `wait-for-comments` parser, wire it through to the
provider implementations, and document it in
`tools-integration-ci/standards/leaf-command-reference.md`. Do not paper over
the gap with a `sleep`.

```
# BAD — blocks the turn, no timeout semantics, no structured result
Bash(command="sleep 180")

# GOOD — bounded wait with TOON result, parseable exit code
Bash(command="python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number N --timeout 180")
```

See [blocking-wait-pattern.md](../../tools-integration-ci/standards/blocking-wait-pattern.md)
in the `tools-integration-ci` standards for the full pattern (polling cadence,
timeout semantics, TOON contract for wait-for-* results, and guidance on
adding new wait-for-* subcommands).

### Reading environment variables

`echo "TERM_PROGRAM=$TERM_PROGRAM"` is the **only** allow-listed env-var Bash
pattern in plan-marshall — installed by the marshall-steward wizard for IDE
hand-off (VS Code vs. default platform opener). Any other `$VAR` expansion
trips the Bash sandbox's `simple_expansion` heuristic and pops a permission
prompt — which is a workflow break, not a heuristic signal.

Forbidden forms (all trigger the sandbox):

- `echo "$ANY_VAR"` for any variable other than `TERM_PROGRAM` — including
  plausible-looking names like `CLAUDE_SESSION_ID` that Claude Code does not
  publish
- `printenv`, `env`, `env | grep` — any form of env-var listing
- `$(...)` command substitution and backticks in Bash calls

For Claude Code runtime state (session id, conversation id, plan id from main
context) the shell is **not** the source — the skill input contract plus the
domain-specific resolver is. For `session_id` specifically, use:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session current
```

The resolver reads a cache populated by the terminal-title hook on every
`UserPromptSubmit`. It never shells out beyond `git rev-parse`, never reads
env vars, and never prompts. See `plan-marshall/SKILL.md` → "Session ID
Resolver" for the cache contract. The same pattern (dedicated resolver script,
no env-var reach) applies when new runtime identifiers emerge — do not
generalize the `TERM_PROGRAM` read into "this is how env vars work" and invent
a variable name.

## Performance Tips

- **Glob once, then Read selectively** — discover files first, read only what you need
- **Grep with output_mode** — use `files_with_matches` for discovery, `content` for details
- **Progressive filtering** — start with `files_with_matches` to find relevant files, then `content` on those files for details
