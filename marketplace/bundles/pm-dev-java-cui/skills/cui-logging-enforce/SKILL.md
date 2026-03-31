---
name: cui-logging-enforce
description: Enforce CUI logging standards by validating LogRecord usage, testing coverage, and identifier organization. Supports targeted scan and systematic module-by-module maintenance modes.
user-invocable: false
---

# CUI Logging Enforcer

Enforces CUI logging standards across Java modules. Two operational modes:

- **scan** (default): Targeted enforcement — find violations, batch fix, verify. Use for quick compliance checks on modules already using CuiLogger.
- **maintain**: Systematic module-by-module migration with plan tracking and per-module commits. Use for migrating from SLF4J/Log4j to CuiLogger or full logging overhauls.

## Enforcement

**Execution mode**: Diagnostic scan followed by automated fixes; execute workflow steps sequentially.

**Prohibited actions:**
- Do not modify business logic; only logging-related code is in scope
- Do not skip LogAssert coverage for any LogRecord usage
- Do not remove or rename existing LogRecord identifiers without user approval
- Never create standalone LogRecord coverage tests — LogAsserts must be in existing business logic tests

**Constraints:**
- All INFO/WARN/ERROR/FATAL logging must use LogRecord constants
- DEBUG/TRACE levels must use direct CuiLogger calls (no LogRecord)
- Every LogRecord must have a corresponding LogAsserts verification in tests
- Module parameter must be resolved before scanning begins
- Non-logging bug discovery triggers immediate stop, documentation, and user approval before proceeding
- Bug fixes require separate commits

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "skill", name: "cui-logging-enforce", bundle: "pm-dev-java-cui"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **mode** - `scan` (default) or `maintain`
- **module** - Module name for multi-module projects (optional; asks if multi-module and unset)
- **create-plan** - (maintain mode only) Generate/regenerate plan.md (optional, default: false)

## CRITICAL CONSTRAINTS

### Production Code Protection

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
6. **RESUME** logging maintenance after commit

## WORKFLOW

### Step 1: Setup

**1.1 Verify Module Parameter:**

1. Activate `plan-marshall:manage-run-config` skill to check for module configuration:
   ```
   Skill: plan-marshall:manage-run-config
   Workflow: Read Configuration
   Field: commands.cui-logging-enforce.modules
   ```
2. If parameter unset:
   - Single-module: Proceed with entire project
   - Multi-module: List available modules and ask user which to analyze
3. If module parameter provided, verify it exists using Grep in pom.xml files

**1.2 Build Verification:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command quality-gate --name {module if specified}
```

On build failure (scan mode): Report to caller and stop.
On build failure (maintain mode): Present using `AskUserQuestion` with options "Fix build first" or "Abort".

**1.3 Load Logging Standards:**

```
Skill: pm-dev-java-cui:cui-logging
```

**1.4 Load Configuration:**

1. Read configuration via `plan-marshall:manage-run-config`:
   ```
   Skill: plan-marshall:manage-run-config
   Workflow: Read Configuration
   Field: commands.cui-logging-enforce.modules.{module-name}
   ```
2. Extract `logmessages_classes` and `logmessages_documentation` arrays
3. If missing: discover via Glob (`**/*LogMessages.java`, `**/LogMessages.adoc`), ask user if uncertain, store for future use

### Step 2: Analysis

#### Scan Mode

**2a.1 Find Logging Violations:**

Use `pm-dev-java-cui:cui-logging` skill workflow to detect:
- Missing LogRecord (INFO/WARN/ERROR/FATAL using direct string)
- Prohibited LogRecord (DEBUG/TRACE using LogRecord)

**2a.2 Verify LogRecord Coverage:**

For each LogMessages class:
- Extract all LogRecord definitions
- Find production usage with Grep (`.format()` calls, static imports)
- Find test coverage (LogAsserts, `resolveIdentifierString`)
- Determine status: No references → Remove | Production only → Add tests | Test only → USER REVIEW | Both → Compliant

**2a.3 Generate Execution Plan:**

Group into batches:
1. Fix logging statement violations (production code)
2. Remove unused LogRecords (production code)
3. Add missing LogAsserts (test code)
4. User review for test-only LogRecords (critical)

#### Maintain Mode

**2b.1 Create/Update Planning Document:**

If `create-plan=true` or plan.md doesn't exist, run LogRecord Discovery from `pm-dev-java-cui:cui-logging` skill (logging-maintenance-reference.md#logrecord-discovery-and-coverage-verification). Display inventory status.

**2b.2 Module-by-Module Analysis:**

For each module, run systematic analysis using Explore agents:

- **Logger Audit**: Find `LoggerFactory.getLogger`, `Logger.getLogger`, `@Slf4j`, `System.out/err`
- **LogRecord Audit**: Find direct string logging at INFO/WARN/ERROR/FATAL, LogRecord at DEBUG/TRACE
- **LogMessages Review**: Check DSL-style structure, identifier ranges, `@UtilityClass`
- **Documentation Check**: Verify doc/LogMessages.adoc exists and matches implementation
- **Duplicate Detection**: Find duplicate `.identifier(N)` values or near-identical templates

Present analysis summary per module via `AskUserQuestion` with options: Proceed / Skip / Abort.

### Step 3: Implementation

#### Scan Mode

Execute batches sequentially:

**Batch 1:** Fix logging violations
- Apply migration patterns from `pm-dev-java-cui:cui-logging` skill (`standards/logging-maintenance-reference.md` → "Migration Patterns")
- Verify compilation

**Batch 2:** Remove unused LogRecords
- Remove LogRecord definitions with no production references
- Verify compilation

**Batch 3:** Add LogAssert tests
- Add LogAsserts to existing business logic tests (never standalone coverage tests)
- Use `@EnableTestLogger` and LogAsserts
- Verify tests pass

**Batch 4:** User review for test-only LogRecords
- Report as critical bugs, stop and await user guidance

#### Maintain Mode

Per module, apply fixes sequentially:

**3b.1 Logger Migration:**
- Replace `LoggerFactory.getLogger` / `Logger.getLogger` / `@Slf4j` with `CuiLogger`
- Apply patterns from `pm-dev-java-cui:cui-logging` skill (`standards/logging-maintenance-reference.md` → "Logger Migration")

**3b.2 LogRecord Implementation:**
- Replace direct string logging at INFO/WARN/ERROR/FATAL with LogRecord usage
- Convert `{}` placeholders to `%s`

**3b.3 LogMessages Creation/Update:**
- Follow DSL-style structure from `pm-dev-java-cui:cui-logging` skill (`standards/logging-standards.md` → "LogMessages Class Structure")
- Use standard identifier ranges

**3b.4 Documentation Update:**
- Create or update doc/LogMessages.adoc

**3b.5 Test Implementation:**
- Use Explore agent to find appropriate business logic test for each LogRecord
- Add LogAsserts to existing tests (never standalone coverage tests)
- If no business logic test exists: ask user via `AskUserQuestion`

**3b.6 Module Verification and Commit:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command module-tests --name {module}
```

Then commit:
```
git commit -m "refactor(logging): implement logging standards in {module}

Logging improvements:
- Logger migrations: {count} completed
- LogRecord implementations: {count} completed
- Tests updated: {count} business logic tests
- Documentation: doc/LogMessages.adoc updated

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Proceed to next module.

### Step 4: Finalize (Both Modes)

**4.1 Review and Renumber Identifiers:**

For each LogMessages class:
1. Extract all identifiers with levels
2. Check for gaps, ordering issues, and range compliance
3. Apply renumbering if needed
4. Verify no DEBUG/TRACE LogRecords exist

Standard ranges: INFO 001-099, WARN 100-199, ERROR 200-299, FATAL 300-399

**4.2 Update LogMessages Documentation:**

For each modified LogMessages class:
1. Locate corresponding LogMessages.adoc file (from configuration)
2. Execute documentation workflow via `pm-dev-java-cui:cui-logging` skill
3. If script fails or path not found: warn but continue

**4.3 Final Build Verification:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    resolve --command verify --name {module if specified}
```

**4.4 Summary Report:**

```
LOG RECORD ENFORCEMENT COMPLETE

Module: {module-name or "all modules"}
Mode: {scan or maintain}

VIOLATIONS FIXED:
- Logging statements corrected: {count}
  - Missing LogRecord (INFO/WARN/ERROR/FATAL): {count}
  - Prohibited LogRecord (DEBUG/TRACE): {count}

LOGRECORD MAINTENANCE:
- Logger migrations: {count} (maintain mode only)
- Unused LogRecords removed: {count}
- LogAssert tests added: {count}
- Identifiers renumbered: {count}

BUILD STATUS: {SUCCESS/FAILURE}
COMPLIANCE STATUS: {COMPLIANT / ISSUES REMAINING}
```

## EXECUTION RULES

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

**Configuration Management:**
- Use `plan-marshall:manage-run-config` for all configuration access
- Read path: `commands.cui-logging-enforce.modules`
- Store LogMessages class and documentation locations
- Update configuration for future executions

**Build Verification:**
- Use `plan-marshall:manage-architecture:architecture resolve` for all builds
- Success criteria: Exit code 0, zero errors, zero test failures

## USAGE EXAMPLES

```
# Quick compliance scan (default mode)
/cui-logging-enforce

# Scan specific module
/cui-logging-enforce module=oauth-sheriff-core

# Full migration mode
/cui-logging-enforce mode=maintain

# Migration with plan regeneration
/cui-logging-enforce mode=maintain module=user-api create-plan
```

## RELATED

- Skill: `pm-dev-java-cui:cui-logging` - Logging standards and maintenance reference
  - `standards/logging-standards.md` - Core rules, LogMessages structure, identifier ranges
  - `standards/logging-maintenance-reference.md` - Detection patterns, migration, test coverage
  - `standards/logmessages-documentation.md` - AsciiDoc documentation requirements
