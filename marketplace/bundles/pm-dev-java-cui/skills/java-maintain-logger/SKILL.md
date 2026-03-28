---
name: java-maintain-logger
description: Execute systematic logging standards maintenance with plan tracking and comprehensive test coverage
user-invocable: false
---

# Logger Maintain Skill

Systematically implements and maintains logging standards across modules while preserving functionality and tracking progress via plan.md.

## Enforcement

**Execution mode**: Module-by-module logging standards implementation with build verification after each module.

**Prohibited actions:**
- Never modify non-logging production code without explicit user approval
- Never alter business logic behavior or change method signatures/APIs
- Never create standalone LogRecord coverage tests — LogAsserts must be in existing business logic tests

**Constraints:**
- Non-logging bug discovery triggers immediate stop, documentation, and user approval before proceeding
- Bug fixes require separate commits
- Each workflow step that performs a script operation has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- Track all statistics (logger_migrations, logrecord_implementations, tests_updated, bugs_found/fixed) throughout workflow

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "skill", name: "java-maintain-logger", bundle: "pm-dev-java-cui"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **module** - Module name for single module (optional, processes all if not specified)
- **create-plan** - Generate/regenerate plan.md from current state (optional, default: false)

## CRITICAL CONSTRAINTS

### Production Code Protection

**MUST:**
- Modify ONLY logging-related code
- Preserve all existing functionality
- Focus exclusively on logging implementation and testing

**MUST NOT:**
- Make non-logging production code changes
- Alter business logic behavior
- Change method signatures or APIs

### Bug Handling Protocol

When non-logging production bugs discovered:
1. **STOP** maintenance immediately
2. **DOCUMENT** bug (location, description, impact)
3. **ASK USER** for approval to fix
4. **WAIT** for explicit confirmation
5. **SEPARATE COMMIT** for bug fix if approved
6. **RESUME** logging maintenance after commit

**Never fix non-logging bugs without user approval.**

### Testing Philosophy - CRITICAL

**LogAsserts MUST be in business logic tests - NEVER standalone coverage tests.**

See `pm-dev-java-cui:cui-logging` skill (logging-maintenance-reference.md#test-implementation) for detailed examples.

## WORKFLOW

### Step 0: Parameter Validation

- If `module` specified: verify module exists
- If `create-plan` specified: will regenerate plan.md
- Determine processing scope (single module vs all)

### Step 1: Load Logging Standards

```
Skill: pm-dev-java-cui:cui-logging
```

This loads comprehensive logging standards including:
- logging-standards.md - Implementation standards for new code
- logging-maintenance-reference.md - Maintenance reference for existing code
- dsl-constants.md - DSL pattern for LogMessages structure

**On load failure:** Report error and abort command.

### Step 2: Pre-Maintenance Verification

**2.1 Build Verification:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command quality-gate --name {module if specified}
```

**On build failure:** Present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Pre-maintenance build failed. How would you like to proceed?"
      header: "Build"
      options:
        - label: "Fix build first"
          description: "Fix build issues before starting maintenance"
        - label: "Abort"
          description: "Cancel logger maintenance"
      multiSelect: false
```

Track in `pre_verification_failures`.

**2.2 Module Identification:**

If `module` parameter not specified:
- Use Glob to identify all Maven modules
- Determine processing order (dependencies first)

**2.3 Standards Review Confirmation:**

Display loaded standards summary and confirm readiness with user.

### Step 3: Create/Update Planning Document

**3.1 Generate plan.md:**

If `create-plan=true` OR plan.md doesn't exist, run LogRecord Discovery Script from `pm-dev-java-cui:cui-logging` skill (logging-maintenance-reference.md#logrecord-discovery-and-coverage-verification).

**3.2 Display Status:**

```
Total LogRecords: {total}
Tested: {tested}
Missing: {missing}
Completion: {percentage}%
```

**3.3 Store Inventory:** Parse plan.md table for progress tracking.

### Step 4: Module-by-Module Analysis

For each module, run systematic violation detection using Explore agent:

**4.1 Logger Audit:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Audit logger configuration
  prompt: |
    Identify logging configuration violations in module {module}.
    Apply detection patterns from `pm-dev-java-cui:cui-logging` skill:
    logging-maintenance-reference.md → "Detection Patterns" section.
    Search for: LoggerFactory.getLogger, Logger.getLogger, @Slf4j, System.out/err.

    Return structured list of violations with locations.
```

**4.2 LogRecord Audit:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Audit LogRecord usage
  prompt: |
    Check LogRecord usage compliance in module {module}.
    Apply rules from `pm-dev-java-cui:cui-logging` skill:
    logging-standards.md → "LogRecord Usage" section.
    Find: LOGGER.info(" or LOGGER.warn(" etc. (direct strings at production levels),
    and LOGGER.debug(DEBUG. etc. (LogRecord at debug/trace levels).

    Return structured findings.
```

**4.3 LogMessages Review:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Review LogMessages structure
  prompt: |
    Review LogMessages class structure in module {module}.
    Apply patterns from `pm-dev-java-cui:cui-logging` skill:
    logging-standards.md → "LogMessages Class Structure" section.
    Check: DSL-style organization, identifier ranges, @UtilityClass usage.

    Return findings with specific violations.
```

**4.4 Documentation Check:**

Verify doc/LogMessages.adoc exists and matches implementation.

**4.5 Duplicate Detection:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Detect duplicate log messages
  prompt: |
    Identify duplicate logging patterns in module {module}.
    Search for duplicate .identifier(N) values within LogMessages classes.
    Search for identical or near-identical log message templates.

    Suggest consolidation opportunities.
```

**4.6 Display Module Analysis Summary** and present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Review the module analysis above. How would you like to proceed?"
      header: "Module"
      options:
        - label: "Proceed"
          description: "Start implementing logging fixes for this module"
        - label: "Skip"
          description: "Skip this module and move to next"
        - label: "Abort"
          description: "Stop logger maintenance"
      multiSelect: false
```

### Step 5: Implementation Phase

Apply fixes using /java-implement-code command with patterns from `pm-dev-java-cui:cui-logging` skill:

**5.1 Logger Migration:**

Migrate logger to CuiLogger in each file:
- Replace `LoggerFactory.getLogger` / `Logger.getLogger` / `@Slf4j` with `CuiLogger`
- Apply migration pattern from `pm-dev-java-cui:cui-logging` skill: `standards/logging-maintenance-reference.md` → "Logger Migration"
- CRITICAL: Only modify logging code, no other changes

**5.2 LogRecord Implementation:**

Convert direct logging to LogRecord in each file:
- Replace direct string logging at INFO/WARN/ERROR/FATAL with LogRecord usage
- Convert `{}` placeholders to `%s`
- Apply pattern from `pm-dev-java-cui:cui-logging` skill: `standards/logging-maintenance-reference.md` → "LogRecord Migration"
- CRITICAL: Only modify logging code

**If non-logging bug discovered:** Apply bug handling protocol (stop, document, ask user, wait).

**5.3 LogMessages Creation/Update:**

Create or update LogMessages class for the module:
- Follow DSL-style structure from `pm-dev-java-cui:cui-logging` skill: `standards/logging-standards.md` → "LogMessages Class Structure"
- Use standard identifier ranges: INFO 001-099, WARN 100-199, ERROR 200-299, FATAL 300-399
- CRITICAL: Only create/modify LogMessages, no other changes

**5.4 Documentation Update:**

Create or update doc/LogMessages.adoc following standard format.

**5.5 Test Implementation - CRITICAL STEP:**

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Find business logic test for LogRecord
  prompt: |
    Find the appropriate business logic test for LogRecord {logrecord_name}.
    Follow troubleshooting guide from `pm-dev-java-cui:cui-logging` skill:
    logging-maintenance-reference.md → "Finding the Right Business Logic Test" section.

    Return: test file, test method, line number for LogAsserts.
    CRITICAL: Must be EXISTING business logic test, not new coverage test.
```

Then add LogAsserts to existing test (see `pm-dev-java-cui:cui-logging` skill → `standards/logging-maintenance-reference.md` → "Test Coverage Verification").

**If no business logic test exists:** Present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "No business logic test exists for this LogRecord. How would you like to proceed?"
      header: "Test"
      options:
        - label: "Create business test first"
          description: "Create a new business logic test, then add LogAsserts"
        - label: "Skip"
          description: "Skip this LogRecord's test"
        - label: "Abort"
          description: "Stop logger maintenance"
      multiSelect: false
```

### Step 6: Verification Phase

**6.1 Module Build Verification:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command module-tests --name {module}
```

**On failure:** Analyze cause, apply bug handling protocol if non-logging.

**6.2 LogRecord Coverage Verification:**

For each LogRecord in module:
1. Verify production reference (Grep for `.format()` calls)
2. Verify test reference (Grep for LogAsserts usage)
3. Update plan.md status

**6.3 Full Build Verification:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command clean-install --name {module}
```

**6.4 Module Commit:**

```
Bash: git add {module files} plan.md
Bash: git commit -m "$(cat <<'EOF'
refactor(logging): implement logging standards in {module}

Logging improvements:
- Logger migrations: {count} completed
- LogRecord implementations: {count} completed
- Tests updated: {count} business logic tests
- Documentation: doc/LogMessages.adoc updated

plan.md status: {tested}/{total} LogRecords tested

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Proceed to next module.

### Step 7: Final Verification

**7.1 Complete Build:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command clean-install
```

**7.2 Final plan.md Update:** Update with completion timestamp.

**7.3 Generate Final Report:** Review all plan.md files and generate summary.

### Step 8: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║       Logger Maintenance Summary                           ║
╚════════════════════════════════════════════════════════════╝

Scope: {module or 'all modules'}

Modules Processed: {modules_completed} / {total_modules}

Logger Migrations: {logger_migrations}
LogRecord Implementations: {logrecord_implementations}
Tests Updated: {tests_updated}
LogRecord Coverage: {tested_logrecords}/{total_logrecords} ({coverage_percentage}%)
Documentation: {doc_count} files created/updated
Bugs Found: {bugs_found} ({bugs_fixed} fixed, {bugs_skipped} skipped)

Build Status: {SUCCESS/FAILURE}
Time Taken: {elapsed_time}

See plan.md for detailed LogRecord inventory.
```

## STATISTICS TRACKING

Track throughout workflow:
- `pre_verification_failures` - Pre-maintenance build failures
- `modules_completed` / `modules_skipped` - Module processing
- `logger_migrations` - Total logger migrations
- `logrecord_implementations` - Total LogRecord implementations
- `tests_updated` - Business logic tests updated with LogAsserts
- `tests_missing` - LogRecords without business logic tests
- `bugs_found` / `bugs_fixed` / `bugs_skipped` - Bug handling
- `module_verification_failures` - Module verification failures
- `total_logrecords` / `tested_logrecords` - Coverage metrics
- `elapsed_time` - Total execution time

Display all statistics in final summary.

## ERROR HANDLING

**Build Failures:** Display detailed errors, distinguish logging vs non-logging, apply bug handling protocol.

**Test Failures:** Analyze cause, fix if logging-related, apply bug handling protocol if non-logging.

**Missing Business Logic Tests:** Document LogRecords without tests, prompt user for guidance.

**Non-Logging Bugs:** STOP immediately, document thoroughly, ask user approval, separate commit if approved.

## USAGE EXAMPLES

```
# Process all modules
/java-maintain-logger

# Process single module
/java-maintain-logger module=auth-service

# Generate/regenerate plan
/java-maintain-logger create-plan

# Process module and regenerate plan
/java-maintain-logger module=user-api create-plan
```

## ARCHITECTURE

Orchestrates skill workflows and direct code edits:
- **`pm-dev-java-cui:cui-logging` skill** - Logging standards and maintenance reference
- **Explore agent** - Violation detection and business test location
- **Direct code edits** - Logger migration, LogRecord implementation, LogAssert addition
- **Build system** - Build verification via `plan-marshall:manage-architecture:architecture resolve`
- **pm-dev-java:plan-marshall-plugin skill** - Java domain extension

## RELATED

- `pm-dev-java-cui:cui-logging` skill - Logging standards and maintenance reference
- `pm-dev-java-cui:java-enforce-logrecords` skill - Targeted enforcement scan (use for quick validation; use this skill for full migration)
- `pm-dev-java:plan-marshall-plugin` skill - Java domain extension with workflow integration
