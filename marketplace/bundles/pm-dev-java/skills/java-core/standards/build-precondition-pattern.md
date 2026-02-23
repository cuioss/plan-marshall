= Build Precondition Pattern
:toc: left
:toclevels: 3
:sectnums:

== Overview

This standard defines the build precondition verification pattern for Java implementation tasks. The core principle is **never implement on broken code** - always verify the build is clean before beginning implementation work.

== Core Principle

**Never implement on broken code.** Always verify the codebase compiles cleanly with zero errors and zero warnings before implementing new features, refactoring, or making changes.

== Rationale

=== Why Build Precondition Matters

**Separation of Concerns:**

* **Build failures** are infrastructure/existing code issues
* **Implementation tasks** are new feature/change work
* Mixing these creates ambiguity about what broke what

**Clear Attribution:**

* Pre-implementation failures → Existing code problems
* Post-implementation failures → New code problems
* Without precondition check, cannot determine root cause

**Efficient Workflow:**

* Fixing existing issues first creates stable foundation
* Implementing on broken code multiplies complexity
* Clean build enables focused implementation and testing

== Build Precondition Workflow

=== Step 1: Determine Build Scope

Identify what needs to be built:

[source]
----
If multi-module project:
  Identify module containing changes
  Use Glob to find module's pom.xml
  Build that specific module

If single-module project:
  Build entire project from root pom.xml

Track: module_name, build_scope
----

**Module Detection:**

Use Glob to find pom.xml files:

[source,bash]
----
# Find all pom.xml files
find . -name "pom.xml" -type f

# Count modules
module_count=$(find . -name "pom.xml" -type f | wc -l)

if [ "$module_count" -gt 1 ]; then
  echo "Multi-module project detected"
  # Module parameter required or inferred from types
else
  echo "Single-module project detected"
  # Build from root
fi
----

=== Step 2: Execute Clean Build

Execute Maven build to verify compilation:

[source,bash]
----
# Single-module
mvn clean compile -l target/build-output.log

# Multi-module with specific module
mvn clean compile -pl :module-name -l target/build-output.log
----

**Critical Requirements:**

* **clean** phase: Ensures no stale artifacts
* **compile** phase: Verifies source compilation only (faster than package)
* **-l flag**: Captures full output to log file for analysis
* **Exit code**: Check $? for success (0) or failure (non-zero)

=== Step 3: Parse Build Output

Analyze build log for errors and warnings:

[source]
----
Use builder-maven parse-maven-output.py script:

Input: target/build-output.log
Output: JSON with status and issues

{
  "status": "clean|has-errors|has-warnings",
  "errors": [
    {
      "file": "src/main/java/com/example/Foo.java",
      "line": 45,
      "message": "cannot find symbol",
      "type": "compilation_error"
    }
  ],
  "warnings": [
    {
      "file": "src/main/java/com/example/Bar.java",
      "line": 23,
      "message": "unchecked conversion",
      "type": "compiler_warning"
    }
  ],
  "summary": {
    "error_count": 1,
    "warning_count": 1
  }
}
----

=== Step 4: Decision Point

Based on build status:

[cols="1,1,2"]
|===
|Status |Action |Rationale

|clean (0 errors, 0 warnings)
|**Proceed** to implementation
|Safe to implement on stable codebase

|has-warnings
|**Stop** and return to caller
|Warnings indicate technical debt that must be fixed first

|has-errors
|**Stop** and return to caller
|Cannot implement on code that doesn't compile
|===

== Build Failure Response Format

When build precondition fails, return detailed information:

[source]
----
BUILD PRECONDITION FAILED

Build Status: FAILURE
Module: {module-name or "all modules"}
Command: clean compile

Errors Found: {count}
{
  file: src/main/java/com/example/UserValidator.java
  line: 45
  error: cannot find symbol
  symbol: class Optional
}
{
  file: src/main/java/com/example/TokenService.java
  line: 78
  error: incompatible types: String cannot be converted to Integer
}

Warnings Found: {count}
{
  file: src/main/java/com/example/DataProcessor.java
  line: 23
  warning: unchecked conversion
  required: List<String>
  found: List
}

Required Actions:
Fix all compilation errors and warnings before implementing task.
The codebase must compile cleanly before implementation can proceed.

Cannot proceed until build is clean.
----

== Special Cases

=== Fix-Build Mode

**Exception to the rule:** When the task IS to fix the build.

**Detection Keywords:**

* "fix build"
* "fix compilation"
* "resolve build errors"
* "build is broken"
* "doesn't compile"
* "fix compilation errors"

**Workflow Modification:**

[source]
----
If task description matches fix-build keywords:
  1. Skip build precondition check
     (The broken build IS the task)

  2. Analyze build errors directly
     Execute build → Capture errors → Fix them

  3. Post-fix verification becomes primary check
     Build MUST succeed to complete task

  4. Return format
     "BUILD FIXED" instead of "IMPLEMENTATION COMPLETE"
     Show before/after build status
----

**Example Fix-Build Task:**

[source]
----
types: UserService
description: Fix compilation errors in UserService class
module: auth-service

Workflow:
1. Skip precondition (build is expected to fail)
2. Run build → Capture errors
3. Analyze errors → Fix code
4. Run build → Verify success
5. Return "BUILD FIXED" status
----

=== Test Failures vs Compilation Failures

**Compilation phase (clean compile):**

* Only checks source code compilation
* Does NOT execute tests
* Faster verification

**Test phase (clean test):**

* Executes unit tests
* Slower but more thorough
* Use when test execution is required

**When to use which:**

[cols="1,2"]
|===
|Phase |Use Case

|clean compile
|Pre-implementation verification, refactoring, code changes

|clean test
|Pre-test implementation, test maintenance, full verification
|===

== Integration with Workflows

=== java-implement-code Command

[source]
----
Step 1: Verify implementation parameters
  ↓
Step 2: Verify build precondition ← THIS STANDARD
  ↓
  If FAIL: Return to caller with build status
  If PASS: Continue
  ↓
Step 3: Analyze code context
Step 4: Implement changes
Step 5: Post-implementation build verification
----

=== java-refactor-code Command

[source]
----
Step 1: Parse parameters
  ↓
Step 2: Verify build precondition ← THIS STANDARD
  ↓
  If FAIL: Return to caller
  If PASS: Continue
  ↓
Step 3: Execute refactoring
Step 4: Verify build still clean
Step 5: Run tests
----

=== Execute Maven Build Workflow

Reference builder-maven skill for build execution:

[source,yaml]
----
Skill: pm-dev-java:plan-marshall-plugin
Workflow: Execute Maven Build
Parameters:
  goals: clean compile
  module: {module if specified}
  output_mode: structured

steps:
  1. Determine build scope (module vs project)
  2. Execute Maven clean + phase
  3. Parse build output (parse-maven-output.py)
  4. Return status: SUCCESS|FAILURE with categorized issues

references:
  - standards/build-precondition-pattern.md
  - pm-dev-java:plan-marshall-plugin skill
----

== Error Categories

=== Compilation Errors (Severity: HIGH)

**Characteristics:**

* Code does not compile
* Build fails with non-zero exit code
* Maven reports [ERROR]

**Examples:**

* Cannot find symbol
* Incompatible types
* Method not found
* Package does not exist

**Required Action:** Fix immediately before any implementation

=== Compiler Warnings (Severity: MEDIUM)

**Characteristics:**

* Code compiles but has issues
* Build succeeds but Maven reports [WARNING]
* Indicates technical debt

**Examples:**

* Unchecked conversion
* Deprecated API usage
* Unused variables
* Raw type usage

**Required Action:** Fix before implementation (warnings = technical debt)

=== Build System Warnings (Severity: LOW)

**Characteristics:**

* Maven/plugin configuration warnings
* Not code quality issues
* Build succeeds

**Examples:**

* Plugin version not specified
* Deprecated plugin configuration
* Missing build metadata

**Action:** Can be addressed separately, don't block implementation

== Best Practices

=== For Implementation Tasks

**DO:**

* Always verify build precondition before implementation
* Use clean compile for fast verification
* Parse build output with script (don't manually inspect)
* Return immediately if build fails

**DON'T:**

* Implement on code with warnings (fix warnings first)
* Skip precondition to "save time" (costs more time later)
* Guess at error causes (use build output)
* Mix build fixes with implementation work

=== For Build Fixes

**DO:**

* Use fix-build mode when task is to fix build
* Show before/after build status
* Verify build succeeds after fixes
* Document what was fixed

**DON'T:**

* Apply build precondition when fixing build (circular)
* Implement new features while fixing build
* Leave warnings unfixed
* Commit broken builds

== Script Contract

=== parse-maven-output.py (builder-maven skill)

**Purpose:** Parse Maven build log to extract errors and warnings

**Input:**

* build_log: Path to Maven build log file
* phase: Build phase (compile, test, package)

**Output:** JSON with build status

[source,json]
----
{
  "status": "clean|has-errors|has-warnings",
  "build_phase": "compile",
  "exit_code": 0,
  "errors": [
    {
      "file": "relative/path/to/File.java",
      "line": 45,
      "column": 12,
      "message": "cannot find symbol",
      "type": "compilation_error",
      "symbol": "Optional",
      "context": "Optional<User> user = ..."
    }
  ],
  "warnings": [
    {
      "file": "relative/path/to/File.java",
      "line": 23,
      "message": "unchecked conversion",
      "type": "compiler_warning",
      "context": "List list = new ArrayList();"
    }
  ],
  "summary": {
    "error_count": 1,
    "warning_count": 1,
    "duration_seconds": 12.5
  }
}
----

**Exit Codes:**

* 0: Parse successful (even if build had errors)
* 1: Parse failed (cannot read log file)

== Examples

=== Example 1: Clean Build (PASS)

**Build Command:**

[source,bash]
----
mvn clean compile -l target/build-output.log
echo $?  # 0
----

**Script Output:**

[source,json]
----
{
  "status": "clean",
  "errors": [],
  "warnings": [],
  "summary": {
    "error_count": 0,
    "warning_count": 0
  }
}
----

**Action:** Proceed with implementation

=== Example 2: Compilation Errors (FAIL)

**Build Command:**

[source,bash]
----
mvn clean compile -l target/build-output.log
echo $?  # 1
----

**Script Output:**

[source,json]
----
{
  "status": "has-errors",
  "errors": [
    {
      "file": "src/main/java/com/example/UserService.java",
      "line": 45,
      "message": "cannot find symbol: class Optional"
    }
  ],
  "summary": {
    "error_count": 1
  }
}
----

**Action:** Return BUILD PRECONDITION FAILED to caller

=== Example 3: Warnings Only (FAIL)

**Build Command:**

[source,bash]
----
mvn clean compile -l target/build-output.log
echo $?  # 0 (build succeeds)
----

**Script Output:**

[source,json]
----
{
  "status": "has-warnings",
  "warnings": [
    {
      "file": "src/main/java/com/example/DataService.java",
      "line": 78,
      "message": "unchecked conversion"
    }
  ],
  "summary": {
    "warning_count": 1
  }
}
----

**Action:** Return BUILD PRECONDITION FAILED to caller (warnings must be fixed)

=== Example 4: Fix-Build Mode

**Task:**

[source]
----
types: TokenValidator
description: Fix compilation errors in TokenValidator class
----

**Workflow:**

[source]
----
1. Detect fix-build keywords in description
   ✓ "Fix compilation errors" matches pattern

2. Skip build precondition check
   (Build is expected to fail)

3. Execute build to capture errors
   mvn clean compile -l target/errors.log

4. Parse errors with parse-maven-output.py (builder-maven skill)
   {
     "status": "error",
     "errors": [
       {
         "file": "src/main/java/.../TokenValidator.java",
         "line": 23,
         "message": "cannot find symbol: class Duration"
       }
     ]
   }

5. Fix error: Add import java.time.Duration

6. Verify fix with build
   mvn clean compile -l target/fixed.log
   {
     "status": "clean"
   }

7. Return "BUILD FIXED" status
----

== References

* xref:implementation-verification.md[Implementation Parameter Verification]
* xref:fix-build-mode.md[Fix Build Mode Standard]
* Maven Build Lifecycle: https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html[Apache Maven]
