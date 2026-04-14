---
name: tools-fix-intellij-diagnostics
description: Retrieve and fix IDE diagnostics automatically, suppressing only when no reasonable fix is available
tools: Read, Edit, Task, mcp__ide__getDiagnostics
---

# Fix IntelliJ Diagnostics Command

Retrieves diagnostics from IntelliJ IDE via MCP, analyzes issues, applies fixes, and handles unfixable issues through suppression.

## Parameters

- `file` — Specific file path, `active`, or `all`. Defaults to `all` (all open files).
- `push` — Boolean. Commit and push after successful fixes. Defaults to false.

## CRITICAL Precondition: File Must Be Active in IDE

IntelliJ's MCP server only responds for the currently focused editor tab. Inactive files will time out after ~60–120 seconds. Manually focus the target file in IntelliJ before invoking this command.

## Workflow

### Step 1 — Get Diagnostics

Validate `file`: must be `all`, `active`, or a path Read can resolve. Abort with a clear message on invalid input.

Call `mcp__ide__getDiagnostics` with `uri="file:///{absolute_path}"` (or without a URI for `all`). On failure or timeout, increment `mcp_failures`, ask the user to Retry / Continue-without / Abort, and proceed accordingly.

### Step 2 — Categorize Issues

Group by severity (error vs warning), fixable vs unfixable, and by file. Track counters `files_analyzed` and `issues_found`.

For each issue, prompt the user (via `AskUserQuestion`) with the options: **Fix automatically**, **Suppress with justification**, **Skip**, and — for warnings — **Ignore** / **Abort all**.

### Step 3 — Apply Fixes

For every issue marked "Fix automatically":

1. Analyze the problem and choose a targeted fix (code, import, type, style).
2. Apply the fix with `Edit`. On success, increment `issues_fixed`.
3. On Edit failure, prompt Retry / Suppress / Skip / Abort.

### Step 4 — Verify Build

Delegate a build run to the maven-builder agent (`Task: subagent_type=pm-dev-builder:maven-builder`) to confirm fixes compile cleanly.

### Step 5 — Handle Unfixable Issues

Add an appropriate suppression with a justification comment (IntelliJ `//noinspection {Name}`, SonarQube `@SuppressWarnings("java:S####")`, or ErrorProne `@SuppressWarnings("Name")`). Increment `issues_suppressed`. Always record the justification.

### Step 6 — Re-check Diagnostics

Re-run `mcp__ide__getDiagnostics` to confirm the fixed and suppressed issues are gone. On MCP failure, prompt Retry / Continue-without-verification / Abort.

### Step 7 — Commit (optional)

If `push=true`, delegate to a general-purpose agent to commit and push the fixes with a message describing the resolved issues.

### Step 8 — Report

Display a final report with: files analyzed, issues found / fixed / suppressed / remaining, `mcp_failures`, retry count, build status, and commit status.

## Critical Rules

- **MCP constraints**: file must be the active editor; retry MCP failures up to 3 times.
- **Fix priority**: attempt a reasonable fix first; only suppress when no fix is viable; always include a justification.
- **Build verification**: run the build after fixes and re-check diagnostics to confirm no regressions.
- **Suppression hygiene**: use the correct tool-specific syntax and document the reason in both code and commit message.
- **User control**: every failure prompt must offer a graceful Abort.

## Usage

```
/plan-marshall:tools-fix-intellij-diagnostics
/plan-marshall:tools-fix-intellij-diagnostics file=src/main/java/Foo.java
/plan-marshall:tools-fix-intellij-diagnostics file=Foo.java push
```

## Architecture

- MCP IntelliJ server provides `getDiagnostics`
- `pm-dev-builder:maven-builder` agent verifies builds
- `general-purpose` agent handles git operations

## Continuous Improvement Rule

If you discover issues or improvements during execution, activate `Skill: plan-marshall:manage-lessons` and record a lesson for the `{type: "command", name: "tools-fix-intellij-diagnostics", bundle: "plan-marshall"}` component with a category (bug | improvement | pattern | anti-pattern), summary, and detail.

## Related

- `pm-dev-builder:maven-builder` agent
- MCP IntelliJ server documentation
