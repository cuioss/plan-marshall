---
name: cui-logging-enforce
description: Execution reference for enforcing CUI logging standards — batch sequence, validation rules, coverage actions, and production code protection. Loaded by recipe deliverables during task execution.
user-invocable: false
---

# CUI Logging Enforcement — Execution Reference

Task-execution guidance for enforcing CUI logging standards within a single module. This skill is loaded by the task executor (phase-5) when processing deliverables from the `cui-logging-enforce` recipe.

## Enforcement

**Execution mode**: Task-execution reference; provides enforcement workflow and constraints for the phase-5 executor.

**Prohibited actions:**
- Do not modify business logic; only logging-related code is in scope
- Do not skip LogAssert coverage for any LogRecord usage
- Do not remove or rename existing LogRecord identifiers without user approval
- Never create standalone LogRecord coverage tests — LogAsserts must be in existing business logic tests

**Constraints:**
- All INFO/WARN/ERROR/FATAL logging must use LogRecord constants
- DEBUG/TRACE levels must use direct CuiLogger calls (no LogRecord)
- Every LogRecord must have a corresponding LogAsserts verification in tests

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "skill", name: "cui-logging-enforce", bundle: "pm-dev-java-cui"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PRODUCTION CODE PROTECTION

**MUST:**
- Modify ONLY logging-related code
- Preserve all existing functionality

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
6. **RESUME** logging enforcement after commit

## ENFORCEMENT WORKFLOW

Execute these steps sequentially within the module. Load standards first:

```
Skill: pm-dev-java-cui:cui-logging
```

### Step 1: Analysis

**1a. Find Logging Violations:**

Use `pm-dev-java-cui:cui-logging` skill workflow to detect:
- Missing LogRecord (INFO/WARN/ERROR/FATAL using direct string)
- Prohibited LogRecord (DEBUG/TRACE using LogRecord)
- Non-CUI loggers (SLF4J `LoggerFactory.getLogger`, Log4j, `@Slf4j`, `System.out/err`)

**1b. Verify LogRecord Coverage:**

For each LogMessages class:
- Extract all LogRecord definitions
- Find production usage with Grep (`.format()` calls, static imports)
- Find test coverage (LogAsserts, `resolveIdentifierString`)
- Determine status:
  - No references → Remove (unused)
  - Production only → Add tests
  - Test only → USER REVIEW (critical bug)
  - Both → Compliant

### Step 2: Fix in Batch Sequence

**Batch 1: Logger Migration**
- Replace `LoggerFactory.getLogger` / `Logger.getLogger` / `@Slf4j` with `CuiLogger`
- Apply patterns from `pm-dev-java-cui:cui-logging` skill (`standards/logging-maintenance-reference.md` → "Logger Migration")

**Batch 2: LogRecord Implementation**
- Replace direct string logging at INFO/WARN/ERROR/FATAL with LogRecord usage
- Convert `{}` placeholders to `%s`
- Follow DSL-style structure from `pm-dev-java-cui:cui-logging` skill (`standards/logging-standards.md` → "LogMessages Class Structure")

**Batch 3: Remove Unused LogRecords**
- Remove LogRecord definitions with no production references
- Verify compilation

**Batch 4: Add LogAssert Tests**
- Add LogAsserts to existing business logic tests (never standalone coverage tests)
- Use `@EnableTestLogger` and LogAsserts
- If no business logic test exists for a LogRecord: ask user via `AskUserQuestion`

**Batch 5: Critical — Test-Only LogRecords**
- Report as critical bugs, stop and await user guidance

### Step 3: Finalize

**3a. Renumber Identifiers:**

For each LogMessages class:
1. Extract all identifiers with levels
2. Check for gaps, ordering issues, and range compliance
3. Apply renumbering if needed

Standard ranges: INFO 001-099, WARN 100-199, ERROR 200-299, FATAL 300-399

**3b. Update Documentation:**

For each modified LogMessages class, update corresponding LogMessages.adoc documentation via `pm-dev-java-cui:cui-logging` skill.

## VALIDATION RULES

**LogRecord Validation:**
- INFO/WARN/ERROR/FATAL: LogRecord REQUIRED
- DEBUG/TRACE: Direct string REQUIRED
- Every LogRecord MUST have production usage and test coverage

**Coverage Actions:**
- No references → Remove (unused)
- Production only → Add tests
- Test only → USER REVIEW (critical bug)
- Both → Compliant

**Testing Philosophy:**
- LogAsserts MUST be in business logic tests, NEVER standalone coverage tests
- See `pm-dev-java-cui:cui-logging` skill (logging-maintenance-reference.md#test-implementation)

## RELATED

- Skill: `pm-dev-java-cui:cui-logging` — Logging standards and maintenance reference
  - `standards/logging-standards.md` — Core rules, LogMessages structure, identifier ranges
  - `standards/logging-maintenance-reference.md` — Detection patterns, migration, test coverage
  - `standards/logmessages-documentation.md` — AsciiDoc documentation requirements
- Recipe: `pm-dev-java-cui:recipe-cui-logging-enforce` — Outline generation (discovers modules, creates deliverables)
