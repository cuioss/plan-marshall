# Tool Usage Patterns

## Core Principle

Use non-prompting tools exclusively for file operations. Bash commands trigger user prompts; dedicated tools (Glob, Read, Grep) execute automatically.

## Tool Availability

When an agent's frontmatter lists required tools, those tools MUST be available. If not, abort with an error. Do not use workarounds or Bash fallbacks.

## Tool Selection Guide

| Operation | Use (no prompts) | Don't use (prompts) |
|-----------|-----------------|---------------------|
| Find files | `architecture files --module X` for module-scoped discovery; fall back to `Glob` for sub-module patterns or when the inventory returns elision | `find`, `ls` |
| Identify owning module | `architecture which-module --path P` | `find`, manual path inspection |
| Locate by name/pattern across modules | `architecture find --pattern P` first; fall back to `Glob`/`Grep` for sub-module or content-level searches | repository-wide `grep`, `rg` via Bash |
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

When a plan runs in an isolated worktree, `{path}` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. See [`cd <path> && <anything>` is forbidden for every tool, not just git](#cd-path--anything-is-forbidden-for-every-tool-not-just-git) below for the rule and rationale (the same `cd && X` prohibition applies to every tool, not just git).

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
  resolve --command compile --module {module} --audit-plan-id {plan_id}
# Then execute the returned 'executable' value
```

Never hard-code build commands (`./pw`, `./mvnw`, `mvn`, `npm`, `gradle`). The architecture API is the single source of truth.

## Bash Safety Rules

The foundational "Bash: One command per call" rule lives in [`dev-general-practices` SKILL.md → Hard Rules](../SKILL.md#bash-one-command-per-call). The subsections below extend that anchor with the structural patterns most often violated in practice — chain shape vs chain content, `cd && X` for any tool, and Bash file-authoring impersonation. This document references the foundational rule rather than duplicating it.

### One command per call

Each Bash call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, or `;`. If independent, make parallel Bash calls. If sequential, make separate calls.

### Chain shape, not chain content

The rule applies to chain shape, not chain content. `git diff > /tmp/x.diff && wc -l /tmp/x.diff` is two commands chained with `&&` and is forbidden — even though the redirect target is `/tmp` and neither side contains markdown, heredocs, or `$(...)` substitution. The trivial appearance is the trap: short commands plus a benign redirect target still constitute a compound chain.

The structural rule covers every form of chaining (`&&`, `;`, `&`, newline) regardless of what flows through it. Split into two separate Bash calls, or replace the entire pattern with a single non-Bash tool call (Read/Grep/Glob).

```
# BAD — two commands joined by && in one Bash call
Bash(command="git diff > /tmp/foo.diff && head -200 /tmp/foo.diff")
Bash(command="some-script --emit-json > /tmp/out.json && jq .field /tmp/out.json")
Bash(command="ls -1 src/ > /tmp/files.txt && wc -l /tmp/files.txt")

# GOOD — split into separate Bash calls
Bash(command="git -C /path diff > .plan/temp/foo.diff")
Bash(command="wc -l .plan/temp/foo.diff")

# BETTER — replace with a single non-Bash tool call where possible
Read(file_path="/path/to/file")               # instead of cat / head / tail piped to file
Grep(pattern="...", path="...")               # instead of grep > file && other
Glob(pattern="src/*", path="...")             # instead of ls > files.txt && wc -l files.txt
```

Use `.plan/temp/` for transient artifacts when a Bash redirect is genuinely necessary — `.plan/temp/` is covered by the `Write(.plan/**)` permission and lives inside the workspace, while `/tmp/` is not pre-approved by the harness.

### No shell constructs

`$()` substitution, `for` loops, `while` loops, and subshells all trigger Claude Code's security prompt. Make individual Bash calls per iteration instead.

### `cd <path> && <anything>` is forbidden for every tool, not just git

`cd <path> && <anything>` is forbidden for every tool, not just git. The compound `cd && X` form has no legitimate use in a one-command-per-call regime — it (a) is two commands joined by `&&`, violating the [One command per call](#one-command-per-call) rule above, and (b) for `git` specifically trips Claude Code's bare-repository security heuristic and pops a permission prompt that disrupts the user.

Use the tool's native cwd flag instead:

| Tool | Native cwd flag |
|------|-----------------|
| git | `git -C <path>` |
| uv | `uv --directory <path>` |
| mvn | `mvn -f <path>` |
| npm | `npm --prefix <path>` |
| pytest | `pytest --rootdir <path>` |
| ruff | `ruff check <path>` (positional) |

```
# BAD — every one of these violates one-command-per-call (cd && X shape)
Bash(command="cd /path/to/worktree && git log --oneline -5")
Bash(command="cd /path/to/worktree && uv run ruff check src/")
Bash(command="cd /path/to/worktree && pytest test/")
Bash(command="cd /path/to/repo && mvn verify")
Bash(command="cd /path/to/project && npm test")

# GOOD — single command using native cwd flag, no prompt
Bash(command="git -C /path/to/worktree log --oneline -5")
Bash(command="uv --directory /path/to/worktree run ruff check src/")
Bash(command="pytest --rootdir /path/to/worktree test/")
Bash(command="mvn -f /path/to/repo verify")
Bash(command="npm --prefix /path/to/project test")
```

When a plan runs in an isolated worktree, `<path>` is the worktree absolute path surfaced by `plan-marshall:phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line. When operating against the main checkout, use the tool's cwd flag against `.` — never `cd && X`. The same rule applies inside `Skill: plan-marshall:workflow-integration-git` and any agent that delegates tool invocations to Bash.

### Authoring file contents via Bash is forbidden in every shape

Authoring file contents via Bash is forbidden in every shape — `python3 -c "open(p,'a').write(...)"`, `echo "..." >> file`, `cat <<EOF > file ... EOF`, `printf '...' > file` — even when the file path was just allocated by a path-allocate script (e.g. `manage-lessons add`, `manage-tasks add`). The shell-content-marshalling sandbox catches some of these (heredocs, multi-line content), but the structural rule is broader: Bash is not a file-authoring tool.

Use the dedicated tools:
- `Write(file_path, content)` for creating new files or completely rewriting existing ones.
- `Edit(file_path, old_string, new_string)` for surgical modifications.

```
# BAD — every shape of Bash file authoring is forbidden
Bash(command='python3 -c "import sys; open(sys.argv[1], \"a\").write(sys.argv[2])" /path/to/file.md "## body..."')
Bash(command='echo "## body..." >> /path/to/file.md')
Bash(command="cat <<'EOF' > /path/to/file.md\nbody\nEOF")
Bash(command="printf '...' > /path/to/file.md")

# GOOD — use Write for new content, Edit for modifications
Write(file_path="/path/to/file.md", content="## body...\n")
Edit(file_path="/path/to/file.md", old_string="old", new_string="new")
```

**Path-allocate contract**: Scripts that allocate paths (`manage-lessons add`, `manage-tasks add`, `manage-solution-outline resolve-path`, `pr prepare-body`) deliberately leave the body empty for the caller. The contract is: the script returns a path, the caller writes the body via the `Write` tool. Do NOT chain a Bash redirect to fill the body — even when the path was just returned by the script. The same constraint applies to Edit-time modifications: never use `sed -i`, `awk -i`, or `python3 -c "open(...).write(...)"` to mutate an existing file.

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
