# Tool Usage Patterns for Diagnostic Commands

## Core Principle

**Use non-prompting tools exclusively to avoid user interruptions during diagnostics.**

Bash commands trigger user prompts. Non-prompting tools execute automatically.

## CRITICAL: Tool Availability Requirements

**If required tools are not available: FAIL IMMEDIATELY.**

When an agent's frontmatter lists tools:
```yaml
tools:
  - Read
  - Grep
  - Edit
```

These tools MUST be available. If not:
1. **DO NOT use workarounds** (Bash commands, alternative tools)
2. **ABORT with error:**
   ```
   ERROR: Required tools not available

   This agent requires: Read, Grep, Edit
   Cannot execute without these tools.
   ```

No circumvention. No silent failures. Fail hard and loud.

## Tool Selection Guide

| Operation | ❌ Don't Use (Prompts) | ✅ Use (No Prompts) | Pattern Reference |
|-----------|----------------------|-------------------|------------------|
| Find files | `find`, `ls` | `Glob` | Pattern 1 |
| Check file exists | `test -f`, `cat` | `Read` + try/except | Pattern 2 |
| Check directory exists | `test -d` | `Glob` | Pattern 2 |
| Search content | `grep`, `rg` via Bash | `Grep` | Pattern 3 |
| Read files | `cat` via Bash | `Read` | Pattern 4 |
| Count items | `wc -l` via Bash | Count results | Pattern 5 |
| List directory | `ls -la` via Bash | `Glob` | Pattern 1 |

## Pattern 1: File Discovery

Use **Glob** tool for all file and directory discovery operations.

**Quick Example**:
```
# Find all .md files recursively
Glob(pattern="**/*.md", path="/path/to/root")
```

**For detailed patterns including**:
- Finding files by extension
- Recursive searches
- Finding directories
- Multiple file types
- Counting files
- Error handling strategies

**See**: `file-operations.md` - File Discovery section

## Pattern 2: Existence Checks

Use **Read** (with error handling) for file existence, **Glob** for directory existence.

**Quick Example**:
```
# Check if file exists by trying to read
try:
    content = Read(file_path="/path/to/file")
    file_exists = True
except:
    file_exists = False
```

**For detailed patterns including**:
- File existence checks (Read vs Glob trade-offs)
- Directory existence checks
- Empty directory detection
- Required structure validation
- Frontmatter validation
- Batch existence checking

**See**: `file-operations.md` - File and Directory Checking section

## Pattern 3: Content Search

Use **Grep** tool for all content searching operations.

**Quick Example**:
```
# Search for pattern with line numbers
Grep(
    pattern="search_term",
    path="/path/to/directory",
    output_mode="content",
    -n=true
)
```

**For detailed patterns including**:
- Finding files containing patterns
- Counting matches
- Case-insensitive searches
- Context lines (before/after matches)
- Multi-pattern searches
- Regex patterns
- Result parsing strategies
- Error handling

**See**: `search-operations.md` - Complete content search patterns

## Pattern 4: File Reading

Use **Read** tool for all file reading operations.

**Quick Example**:
```
# Read complete file
content = Read(file_path="/path/to/file")
```

**For detailed patterns including**:
- Reading entire files
- Reading with line limits and offsets
- Reading specific sections
- Error handling for missing files
- Memory considerations for large files

**See**: `file-operations.md` - File Reading section

## Pattern 5: Combining Patterns

**Quick Example**:
```
# Discover files and validate each
agents = Glob(pattern="*.md", path="/bundle/agents")
for agent_path in agents:
    try:
        content = Read(file_path=agent_path)
        # Validate content
        if content.startswith("---"):
            valid = True
    except:
        valid = False
```

**For detailed patterns including**:
- Discover and validate workflows
- Search and analyze pipelines
- Recursive validation
- Batch processing with error handling
- Result aggregation strategies

**See**: Both `file-operations.md` and `search-operations.md` for comprehensive error handling patterns

## Common Pitfalls to Avoid

### ❌ Don't Use Bash for File Operations

```
# BAD - Triggers prompts
Bash(command="find /path -name '*.md'")
Bash(command="test -f /path/file")
Bash(command="ls -la /path")
Bash(command="grep pattern /path/file")
```

### ❌ Don't Chain Bash Commands

```
# BAD - Triggers multiple prompts
Bash(command="find /path -name '*.md' | wc -l")
```

### ❌ Don't Use Bash for Conditional Checks

```
# BAD - Triggers prompts
Bash(command="test -d /path && echo 'exists' || echo 'missing'")
```

### ✅ Use Non-Prompting Tools

```
# GOOD - No prompts
files = Glob(pattern="*.md", path="/path")
file_count = len(files)
```

## When Bash IS Appropriate

While this skill focuses on non-prompting tools, Bash is still necessary for certain operations:

### ✅ Legitimate Bash Use Cases

**Git Operations**:
```
Bash(command="git status")
Bash(command="git log --oneline -10")
Bash(command="git diff main...HEAD")
```

**Build Commands** (MUST resolve via architecture API first):
```
# ALWAYS resolve the command first:
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --name {module} --trace-plan-id {plan_id}

# Then execute the returned 'executable' value:
Bash(command="{resolved_executable}")
```
Never hard-code build commands (`./pw`, `./mvnw`, `mvn`, `npm`, `gradle`, etc.). The architecture API is the single source of truth for build commands — different projects use different build systems. This applies to ALL phases including discovery, verification, and testing.

**Shell-Specific Features**:
```
Bash(command="export VAR=value && some-command")
Bash(command="source ~/.bashrc && echo $PATH")
```

**When External Tools Required**:
- Version control systems (git, svn)
- Container tools (docker, kubectl)
- Build systems and package managers — but ONLY after resolving the command via `architecture resolve`

### ❌ Never Combine Commands in a Single Bash Call

Each Bash call must contain exactly ONE command. Never combine commands using newlines, `&`, `&&`, or `;` separators. Newline-separated commands trigger Claude Code's security prompt ("Command contains newlines that could separate multiple commands").

```
# BAD - Triggers security prompt
Bash(command="python3 script.py --arg value 2>&1 &\ngit branch --show-current 2>&1")

# BAD - Also triggers prompt
Bash(command="command1 && command2")

# GOOD - Separate Bash calls
Bash(command="python3 script.py --arg value")
Bash(command="git branch --show-current")
```

If two commands are independent, make two parallel Bash tool calls. If sequential, make two separate calls.

### ❌ Never Use Shell Constructs in Bash Commands

Shell constructs like `$()` command substitution, `for` loops, `while` loops, and subshells trigger Claude Code's security prompt — even when the inner command is in the allow list. This breaks automated execution.

```
# BAD - Triggers "Command contains $() command substitution" prompt
Bash(command="for i in $(seq 1 10); do python3 script.py --task $i; done")

# BAD - Also triggers prompt
Bash(command="result=$(python3 script.py --query status)")

# BAD - Subshell
Bash(command="(cd /tmp && python3 script.py)")
```

Instead, make individual Bash calls per iteration:

```
# GOOD - One call per task, no shell constructs
Bash(command="python3 script.py --task 1")
Bash(command="python3 script.py --task 2")
Bash(command="python3 script.py --task 3")
```

For batch operations, emit multiple parallel Bash tool calls rather than shell loops.

### ❌ Never Use Heredocs for Multi-Line Arguments

Heredocs (`<<'EOF'`) with content containing `#`-prefixed lines trigger Claude Code's security prompt ("quoted newline followed by a #-prefixed line"). Use file-based alternatives instead.

```
# BAD - Triggers security prompt (markdown headings start with #)
Bash(command="gh pr create --body \"$(cat <<'EOF'\n## Summary\n...\nEOF\n)\"")

# GOOD - Write to temp file, pass via --body-file
Write(file_path=".plan/temp/pr-body.md", content="## Summary\n...")
Bash(command="gh pr create --body-file .plan/temp/pr-body.md")
```

Same pattern applies to any CLI that accepts file input: `--body-file`, `--message-file`, `-F`, etc.

**Rule of Thumb**: Use Bash when the operation truly requires shell execution or external tools. Use non-prompting tools (Glob, Read, Grep) for all file system operations. All build/compile/lint/test commands must be resolved via architecture API before execution.

## Performance Considerations

### Glob is Fast
- Efficient file system scanning
- Returns results immediately
- Can filter by pattern

### Read is Efficient
- Loads file once
- Can limit lines read
- Use for existence check + content

### Grep is Optimized
- Fast pattern matching
- Can filter by file type
- Returns structured results

### Combine for Efficiency

```
# EFFICIENT: Glob once, then Read only needed files
all_files = Glob(pattern="*.md", path="/path")
files_with_issues = []

for file_path in all_files:
    content = Read(file_path=file_path)
    if has_issue(content):
        files_with_issues.append(file_path)
```

## Summary

**Golden Rule**: If the operation involves the file system, use Glob/Read/Grep, never Bash.

**Quick Reference**:
- File discovery → `Glob`
- File exists → `Read` + try/except or `Glob`
- Directory exists → `Glob`
- Content search → `Grep`
- Read content → `Read`
- Count/list → `Glob` + len()

**Result**: Zero user prompts, fully automated diagnostics.
