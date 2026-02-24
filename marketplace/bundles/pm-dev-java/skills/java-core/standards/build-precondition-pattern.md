# Build Precondition Pattern

**Never implement on broken code.** Verify the codebase compiles cleanly with zero errors and zero warnings before implementing new features, refactoring, or making changes.

## Build Precondition Workflow

### Step 1: Determine Build Scope

```
If multi-module project:
  Identify module containing changes
  Use Glob to find module's pom.xml
  Build that specific module

If single-module project:
  Build entire project from root pom.xml
```

### Step 2: Execute Clean Build

```bash
# Single-module
mvn clean compile -l target/build-output.log

# Multi-module with specific module
mvn clean compile -pl :module-name -l target/build-output.log
```

Requirements:
- **clean** phase: Ensures no stale artifacts
- **compile** phase: Source compilation only (faster than package)
- **-l flag**: Captures output to log file for analysis

### Step 3: Parse Build Output

Use builder-maven `parse-maven-output.py` script:

```json
{
  "status": "clean|has-errors|has-warnings",
  "errors": [
    {"file": "src/main/java/.../Foo.java", "line": 45, "message": "cannot find symbol", "type": "compilation_error"}
  ],
  "warnings": [
    {"file": "src/main/java/.../Bar.java", "line": 23, "message": "unchecked conversion", "type": "compiler_warning"}
  ],
  "summary": {"error_count": 1, "warning_count": 1}
}
```

### Step 4: Decision Point

| Status | Action | Rationale |
|--------|--------|-----------|
| clean (0 errors, 0 warnings) | **Proceed** to implementation | Safe to build on stable codebase |
| has-warnings | **Stop** and return to caller | Warnings = technical debt, fix first |
| has-errors | **Stop** and return to caller | Cannot implement on code that doesn't compile |

## Build Failure Response Format

```
BUILD PRECONDITION FAILED

Build Status: FAILURE
Module: {module-name or "all modules"}
Command: clean compile

Errors Found: {count}
  file: src/main/java/.../UserValidator.java
  line: 45
  error: cannot find symbol

Warnings Found: {count}
  file: src/main/java/.../DataProcessor.java
  line: 23
  warning: unchecked conversion

Required Actions:
Fix all compilation errors and warnings before implementing task.
```

## Fix-Build Mode

**Exception:** When the task IS to fix the build, skip the precondition check.

**Detection keywords:** "fix build", "fix compilation", "resolve build errors", "build is broken", "doesn't compile"

**Workflow:**
1. Skip build precondition check (broken build IS the task)
2. Execute build to capture errors
3. Parse errors, fix them
4. Verify build succeeds after fixes
5. Return "BUILD FIXED" status with before/after

## Build Phase Selection

| Phase | Use Case |
|-------|----------|
| `clean compile` | Pre-implementation verification, refactoring, code changes |
| `clean test` | Pre-test implementation, test maintenance, full verification |

## Error Categories

### Compilation Errors (HIGH)
Code does not compile. Maven reports `[ERROR]`. Examples: cannot find symbol, incompatible types, method not found. **Fix immediately.**

### Compiler Warnings (MEDIUM)
Code compiles but has issues. Examples: unchecked conversion, deprecated API usage, raw type usage. **Fix before implementation.**

### Build System Warnings (LOW)
Maven/plugin configuration warnings. Not code quality issues. Examples: plugin version not specified. **Can be addressed separately.**

## Integration with Workflows

```
java-implement-code:
  Step 1: Verify implementation parameters
  Step 2: Verify build precondition  ← THIS STANDARD
    If FAIL: Return to caller with build status
    If PASS: Continue
  Step 3: Analyze code context
  Step 4: Implement changes
  Step 5: Post-implementation build verification

java-refactor-code:
  Step 1: Parse parameters
  Step 2: Verify build precondition  ← THIS STANDARD
    If FAIL: Return to caller
    If PASS: Continue
  Step 3: Execute refactoring
  Step 4: Verify build still clean
  Step 5: Run tests
```

## Execute Maven Build Workflow

Reference builder-maven skill for build execution:

```yaml
Skill: pm-dev-java:plan-marshall-plugin
Workflow: Execute Maven Build
Parameters:
  goals: clean compile
  module: {module if specified}
  output_mode: structured
```

## References

- [Implementation Parameter Verification](implementation-verification.md)
- [pm-dev-java:plan-marshall-plugin skill](../../plan-marshall-plugin/SKILL.md)
