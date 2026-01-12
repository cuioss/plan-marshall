---
name: tools-fix-intellij-diagnostics
description: Retrieve and fix IDE diagnostics automatically, suppressing only when no reasonable fix is available
allowed-tools:
  - Read
  - Edit
  - Task
  - mcp__ide__getDiagnostics
---

# Fix IntelliJ Diagnostics Command

Retrieves diagnostics from IntelliJ IDE via MCP, analyzes issues, applies fixes, and handles unfixable issues through suppression.

## PARAMETERS

**file** - Specific file to check (optional, checks all open files if not provided)

**push** - Auto-push after fixes (optional boolean flag, default: false)

## CRITICAL: File Must Be Active in IDE

IntelliJ MCP server ONLY works on currently active/focused file. If file not active, getDiagnostics will timeout (~60-120 seconds).

**Workflow**: Manually click file in IntelliJ → Call this command

## WORKFLOW

### Step 1: Validate Parameters and Get Diagnostics

**Parameter validation:**
1. If `file` parameter provided:
   - Validate it's one of: 'all', 'active', or valid file path
   - If file path: Use Read to verify file exists, handle errors gracefully
   - If invalid: Display error "Invalid scope. Use 'all', 'active', or valid file path" and abort
2. If no parameter: Default to 'all' (all open files)

**Get diagnostics from IDE:**

**A. If file parameter is specific path**: Open file in IDE, get diagnostics for that file

**B. If file='all' or no parameter**: Get diagnostics for all open files

**C. If file='active'**: Get diagnostics for currently active file only

Use MCP ide tool:
```
mcp__ide__getDiagnostics uri="file:///{absolute_path}"
```

**Error handling:** If MCP getDiagnostics fails or times out:
- Increment mcp_failures counter
- Display: "MCP server not responding or file not active in IDE. Ensure IntelliJ is running and file is focused."
- Prompt user: "[R]etry/[A]bort"
- If retry: Wait 5 seconds, try again (max 3 retries)
- If abort or max retries: Exit with error report

### Step 2: Categorize Issues

Group by:
- Errors vs Warnings (track in issues_found counter)
- Fixable vs Unfixable
- By file (if multiple files analyzed, track in files_analyzed counter)

**Decision logic for each issue type:**
- **Error (severity: Error)**:
  - Display: "ERROR in {file}:{line} - {message}"
  - Options: "[F]ix automatically/[S]uppress with justification/[S]kip this issue"

- **Warning (severity: Warning)**:
  - Display: "WARNING in {file}:{line} - {message}"
  - Options: "[F]ix automatically/[S]uppress with justification/[I]gnore (skip)/[A]bort all"

### Step 3: Attempt Fixes

For each diagnostic marked for automatic fix:

**A. Analyze issue** - Understand problem and possible solutions

**B. Determine if fixable**:
- Code issues → Fix code (increment issues_fixed on success)
- Import issues → Add imports (increment issues_fixed on success)
- Type issues → Fix types (increment issues_fixed on success)
- Style issues → Fix formatting (increment issues_fixed on success)

**C. Apply fix** using Edit tool

**Error handling:** If Edit fails, display error and prompt "[R]etry edit/[S]uppress issue/[S]kip/[A]bort"

### Step 4: Re-verify Build

```
Task:
  subagent_type: pm-dev-builder:maven-builder
  description: Verify fixes
  prompt: Run maven build and verify no errors
```

### Step 5: Handle Unfixable Issues

For issues that cannot be reasonably fixed:

**A. Determine suppression approach** based on tool:
- IntelliJ: `//noinspection {InspectionName}`
- SonarQube: `@SuppressWarnings("java:S####")`
- ErrorProne: `@SuppressWarnings("ErrorProneName")`

**B. Add suppression comment** with justification (increment issues_suppressed counter)

### Step 6: Re-check Diagnostics

Call getDiagnostics again to verify issues resolved.

**Error handling:** If MCP fails during re-check, increment mcp_failures and prompt "[R]etry/[C]ontinue without verification/[A]bort".

### Step 7: Build and Commit

**A. Final build verification**

**B. Commit changes** (if push parameter):
```
Task:
  subagent_type: general-purpose
  description: Commit diagnostic fixes
  prompt: Commit fixes with message describing issues resolved
```

### Step 8: Cleanup and Display Report

**Cleanup:**
- Clear any temporary IntelliJ state (cached diagnostics)
- No file artifacts to clean (MCP is stateless)

**Display comprehensive report:**

```
╔════════════════════════════════════════════════════════════╗
║          Diagnostic Fix Report                             ║
╚════════════════════════════════════════════════════════════╝

Files analyzed: {files_analyzed}
Issues found: {issues_found}
Issues fixed: {issues_fixed}
Issues suppressed: {issues_suppressed}
Remaining issues: {count}

MCP Statistics:
- MCP failures: {mcp_failures}
- Retries attempted: {retry_count}

Build status: {SUCCESS/FAILURE}
Committed: {yes/no}
```

## STATISTICS TRACKING

Track throughout workflow:
- `files_analyzed`: Count of files checked for diagnostics
- `issues_found`: Total diagnostic issues discovered
- `issues_fixed`: Issues successfully fixed automatically
- `issues_suppressed`: Issues suppressed with justification
- `mcp_failures`: Count of MCP getDiagnostics failures/timeouts

Display all statistics in final report.

## CRITICAL RULES

**MCP Constraints:**
- File must be active in IDE
- Timeout ~60-120 seconds if file not active
- Use mcp__ide__getDiagnostics tool
- Handle MCP failures with retry logic (max 3 retries)

**Parameter Validation:**
- Validate 'file' parameter is 'all', 'active', or valid file path
- Use Read to verify file existence before attempting diagnostics
- Clear error messages for invalid parameters

**Fix Priority:**
1. Try reasonable fix first
2. Only suppress if no reasonable fix
3. Always add justification for suppression

**Build Verification:**
- Must verify build after fixes
- Re-check diagnostics after fixes
- Ensure no new issues introduced

**Suppression:**
- Use appropriate tool-specific syntax
- Add comment explaining why suppressed
- Document in commit message

**Error Handling:**
- Prompt user on MCP failures with retry option
- Track all failures in mcp_failures counter
- Allow graceful abort at any decision point

## USAGE EXAMPLES

**Check all open files:**
```
/plan-marshall:tools-fix-intellij-diagnostics
```

**Check specific file:**
```
/plan-marshall:tools-fix-intellij-diagnostics file=src/main/java/Foo.java
```

**Auto-push:**
```
/plan-marshall:tools-fix-intellij-diagnostics file=Foo.java push
```

## ARCHITECTURE

Uses:
- MCP jetbrains server (getDiagnostics)
- pm-dev-builder:maven-builder agent (build verification)
- general-purpose agent (git operations)

## RELATED

- pm-dev-builder:maven-builder agent
- MCP jetbrains server documentation
