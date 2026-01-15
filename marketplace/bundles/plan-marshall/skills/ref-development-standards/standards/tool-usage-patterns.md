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

**Build Commands**:
```
Bash(command="./mvnw clean verify")
Bash(command="npm install")
Bash(command="docker build -t image:tag .")
```

**Shell-Specific Features**:
```
Bash(command="export VAR=value && some-command")
Bash(command="source ~/.bashrc && echo $PATH")
```

**When External Tools Required**:
- Package managers (npm, pip, mvn)
- Version control systems (git, svn)
- Build systems (make, gradle, maven)
- Container tools (docker, kubectl)
- Language runtime operations (java, node, python)

**Rule of Thumb**: Use Bash when the operation truly requires shell execution or external tools. Use non-prompting tools (Glob, Read, Grep) for all file system operations.

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
