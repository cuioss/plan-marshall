# Logging Maintenance Reference

Reference guide for maintaining and migrating existing code to CUI logging standards.

## Purpose

This document provides reference material for logger maintenance activities, including:
- Migration patterns from legacy logging
- Fix patterns for converting violations
- Troubleshooting common issues
- Testing requirements specific to maintenance

**Note:** For implementing NEW logging code, see `logging-standards.md`. This guide focuses on fixing EXISTING code.

## Maintenance Workflow

### Package-by-Package Analysis

Process modules systematically rather than all-at-once:

1. **Identify scope**: List all Java packages in the module
2. **Analyze each package**: For each package, detect violations using the patterns below
3. **Fix in order**: Logger configuration first, then LogRecord migration, then test coverage
4. **Verify**: Run tests after each package to catch regressions early

### Detection Patterns

Use these search patterns to find violations in existing code:

**Logger type violations:**
- `LoggerFactory.getLogger` — slf4j usage, needs CuiLogger migration
- `Logger.getLogger` — java.util.logging usage, needs CuiLogger migration
- `@Slf4j` — Lombok annotation, needs CuiLogger migration
- `System.out` / `System.err` — console output, needs logger migration

**LogRecord violations:**
- `LOGGER.info("` or `LOGGER.warn("` or `LOGGER.error("` or `LOGGER.fatal("` — direct strings at production levels, needs LogRecord
- `LOGGER.debug(DEBUG.` or `LOGGER.trace(TRACE.` — LogRecord at debug/trace levels, must use direct strings
- `{}` in log messages — slf4j placeholder format, must convert to `%s`

**Structural violations:**
- Modules with 10+ Java types or 10+ INFO+ messages but no LogMessages class
- Duplicate `.identifier(N)` values within a module

For complete rules and identifier ranges, see `logging-standards.md`.

## Migration Patterns

### Logger Migration

**From slf4j:**

```java
// BEFORE
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MyClass {
    private static final Logger logger = LoggerFactory.getLogger(MyClass.class);

    public void process() {
        System.out.println("Debug info: " + data);
        logger.info("Processing user {}", username);
    }
}

// AFTER
import de.cuioss.tools.logging.CuiLogger;
import static com.example.MyLogMessages.INFO;

public class MyClass {
    private static final CuiLogger LOGGER = new CuiLogger(MyClass.class);

    public void process() {
        LOGGER.debug("Debug info: %s", data);
        LOGGER.info(INFO.PROCESSING_USER, username);
    }
}
```

**From @Slf4j Lombok annotation:**

```java
// BEFORE
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MyClass {
    public void process() {
        log.info("Processing started");
    }
}

// AFTER
import de.cuioss.tools.logging.CuiLogger;

public class MyClass {
    private static final CuiLogger LOGGER = new CuiLogger(MyClass.class);

    public void process() {
        LOGGER.info(INFO.PROCESSING_STARTED);
    }
}
```

**From java.util.logging:**

```java
// BEFORE
import java.util.logging.Logger;

public class MyClass {
    private static final Logger logger = Logger.getLogger(MyClass.class.getName());

    public void process() {
        logger.info("Processing");
    }
}

// AFTER
import de.cuioss.tools.logging.CuiLogger;

public class MyClass {
    private static final CuiLogger LOGGER = new CuiLogger(MyClass.class);

    public void process() {
        LOGGER.info(INFO.PROCESSING);
    }
}
```

### LogRecord Migration

**From direct logging to LogRecord:**

```java
// BEFORE
LOGGER.info("User {} logged in successfully", username);
LOGGER.error("Database connection failed: {}", e.getMessage());
LOGGER.warn("Clock skew detected: {} ms", skew);

// AFTER
import static com.example.MyLogMessages.INFO;
import static com.example.MyLogMessages.ERROR;
import static com.example.MyLogMessages.WARN;

LOGGER.info(INFO.USER_LOGIN, username);
LOGGER.error(e, ERROR.DATABASE_CONNECTION);
LOGGER.warn(WARN.CLOCK_SKEW, skew);
```

**Key changes:**
- Replace slf4j `{}` placeholders with `%s` in LogRecord templates
- Use `LogRecord.format()` for parameterized messages
- Exception comes first when present

**Parameter format migration:**

```java
// BEFORE
logger.info("User {} logged in at {}", username, timestamp);
logger.error("Failed to process {} items", count);

// AFTER (in LogMessages class)
public static final LogRecord USER_LOGIN = LogRecordModel.builder()
    .template("User %s logged in at %s")  // Changed {} to %s
    .prefix(PREFIX)
    .identifier(1)
    .build();

public static final LogRecord PROCESS_FAILED = LogRecordModel.builder()
    .template("Failed to process %s items")  // Changed {} to %s
    .prefix(PREFIX)
    .identifier(201)
    .build();

// Usage
LOGGER.info(INFO.USER_LOGIN, username, timestamp);
LOGGER.error(ERROR.PROCESS_FAILED, count);
```

For the LogMessages class template and DSL-Style Constants Pattern, see `logging-standards.md` and `dsl-constants.md`.

### Test Coverage Verification

**Adding LogAsserts to existing business logic tests:**

```java
import de.cuioss.test.juli.junit5.EnableTestLogger;
import de.cuioss.test.juli.LogAsserts;
import de.cuioss.test.juli.TestLogLevel;

import static com.example.mymodule.MyModuleLogMessages.INFO;
import static com.example.mymodule.MyModuleLogMessages.ERROR;
import static de.cuioss.test.juli.LogAsserts.*;

@EnableTestLogger
class MyServiceTest {

    @Test
    void shouldLogUserLogin() {
        // given
        String username = "testuser";

        // when - Business logic that triggers logging
        service.processUser(username);

        // then - Verify business outcome AND log message
        assertNotNull(result);

        // Verify exact message (includes parameters)
        assertSingleLogMessagePresent(
            TestLogLevel.INFO,
            INFO.USER_LOGIN.format(username));

        // OR verify LogRecord identifier only (usually sufficient)
        assertSingleLogMessagePresentContaining(
            TestLogLevel.INFO,
            INFO.USER_LOGIN.resolveIdentifierString());
    }

    @Test
    void shouldLogValidationError() {
        // given
        String invalidInput = "";

        // when - Business logic that triggers error
        assertThrows(ValidationException.class,
            () -> service.validate(invalidInput));

        // then - Verify error was logged
        assertLogMessagePresentContaining(
            TestLogLevel.ERROR,
            ERROR.VALIDATION_FAILED.resolveIdentifierString());
    }
}
```

**CRITICAL - What NOT to do:**

```java
// WRONG - Don't create standalone coverage tests!
@Test
void testLogRecordCoverage() {
    // This is WRONG - just testing the log, not business logic
    LOGGER.error(ERROR.VALIDATION_FAILED.format("test", "test"));
    assertLogMessagePresent(TestLogLevel.ERROR, ...);
}

// CORRECT - Test in conjunction with business logic
@Test
void shouldRejectInvalidInput() {
    // Business logic test that happens to verify logging
    assertThrows(ValidationException.class,
        () -> validator.validate(invalidInput));

    // Logging verification as part of business test
    assertLogMessagePresentContaining(TestLogLevel.ERROR,
        ERROR.VALIDATION_FAILED.resolveIdentifierString());
}
```

## Troubleshooting Guide

### LogAsserts Failing Despite LogRecord Usage

**Symptom:**
LogRecord appears to be used in code, but LogAsserts doesn't find the log message in tests.

**Diagnosis Steps:**

1. **Verify actual logging**: Check if LogRecord is logged with `.format()`, not just defined
2. **Check usage type**: Distinguish between logging and counting
   ```java
   // Logged - needs LogAsserts
   LOGGER.warn(WARN.JWKS_PARSE_FAILED.format(message));

   // Only counted - no LogAsserts needed
   securityEventCounter.increment(EventType.JWKS_PARSE_FAILED);
   ```

3. **Verify log level**: Ensure test checks correct level
   ```java
   // If production uses WARN:
   LOGGER.warn(WARN.RATE_LIMIT.format());

   // Test must check WARN, not ERROR:
   assertLogMessagePresent(TestLogLevel.WARN, ...);  // Correct
   assertLogMessagePresent(TestLogLevel.ERROR, ...); // Wrong level!
   ```

4. **Confirm code path**: Ensure test actually triggers the logging condition

### Finding the Right Business Logic Test

**Approach:**

1. **Find production usage**: Search for `ERROR.VALIDATION_FAILED.format` in `src/main/java/`
2. **Identify the method/class** that calls the log statement
3. **Find corresponding test**: Look for `{ClassName}Test.java` with a test that exercises that method
4. **Add LogAsserts to existing test** rather than creating a new one

**Never:**
- Create a new test just for LogRecord coverage
- Test LogRecords in isolation without business logic
- Add LogAsserts without verifying the log is actually produced

### Common Issues and Solutions

**Issue: Test passes but no actual logging verified**
- **Problem**: Test doesn't trigger the code path that logs
- **Solution**: Review business logic, ensure logging condition is met

**Issue: LogAsserts finds multiple messages when expecting one**
- **Problem**: LogRecord is logged multiple times or in loops
- **Solution**: Use `assertLogMessagePresent` (allows multiple) instead of `assertSingleLogMessagePresent`

**Issue: Cannot find business logic test for LogRecord**
- **Problem**: Code path may not be tested
- **Solution**: Add business logic test first, then add LogAsserts to it

**Issue: LogRecord exists but never used**
- **Problem**: Orphaned LogRecord from refactoring
- **Solution**: Remove the LogRecord entirely

## Success Criteria

For the complete list of logging rules (logger configuration, LogRecord usage, identifier ranges, LogMessages structure, documentation, and testing requirements), see the **Quality Rules** section in `logging-standards.md`.

Maintenance-specific success criteria:
- All legacy loggers (slf4j, log4j, java.util.logging) replaced with CuiLogger
- All `System.out` / `System.err` calls replaced with appropriate logger calls
- All `{}` placeholders converted to `%s`
- All INFO/WARN/ERROR/FATAL calls converted to use LogRecord
- No orphaned LogRecords (defined but never used in production code)
- No duplicate log messages across components
- LogAsserts added to existing business logic tests (not standalone coverage tests)

## Related Standards

- logging-standards.md - Standards for writing NEW logging code
- logmessages-documentation.md - LogMessages AsciiDoc documentation standards
- dsl-constants.md - DSL-Style Constants Pattern for LogMessages structure
