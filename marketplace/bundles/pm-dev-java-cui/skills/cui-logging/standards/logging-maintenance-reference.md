# Logging Maintenance Reference

Reference guide for maintaining and migrating existing code to CUI logging standards.

## Purpose

This document provides reference material for logger maintenance activities, including:
- Detection criteria for logging violations
- Migration patterns from legacy logging
- Troubleshooting common issues
- Testing requirements specific to maintenance

**Note:** For implementing NEW logging code, see `logging-standards.md`. This guide focuses on fixing EXISTING code.

## Standards Violation Detection

### Logger Configuration Issues

**Wrong Logger Type:**
- **Symptom**: Using slf4j, log4j, or java.util.logging instead of CuiLogger
- **Detection**: Search for `LoggerFactory.getLogger`, `Logger.getLogger`, `@Slf4j`
- **Fix Required**: Replace with `private static final CuiLogger LOGGER = new CuiLogger(ClassName.class)`

**Incorrect Declaration:**
- **Symptom**: Logger not static, not final, wrong name, or wrong instantiation
- **Detection**: Logger declarations not matching pattern
- **Fix Required**: Ensure `private static final CuiLogger LOGGER = new CuiLogger(ClassName.class)`

**System.out/err Usage:**
- **Symptom**: Using `System.out.println()` or `System.err.println()` for logging
- **Detection**: Search for `System.out` and `System.err`
- **Fix Required**: Replace with appropriate LOGGER level calls

**Log Level Prefixes:**
- **Symptom**: Manual prefixes like `[DEBUG]`, `[ERROR]` in log messages
- **Detection**: String patterns like `"[DEBUG]"`, `"[ERROR]"`, `"[INFO]"`
- **Fix Required**: Remove prefixes, use proper log levels

### LogRecord Implementation Issues

**Missing LogRecord Usage:**
- **Symptom**: INFO/WARN/ERROR/FATAL using direct strings instead of LogRecord
- **Detection**:
  ```
  LOGGER.info("Direct string message")
  LOGGER.warn("Warning: {}", param)
  LOGGER.error("Error occurred")
  ```
- **Fix Required**: Convert to LogRecord usage
- **Rule**: INFO/WARN/ERROR/FATAL MUST use LogRecord

**Incorrect LogRecord Usage:**
- **Symptom**: DEBUG/TRACE using LogRecord instead of direct strings
- **Detection**:
  ```
  LOGGER.debug(DEBUG.SOME_RECORD)
  LOGGER.trace(TRACE.ANOTHER_RECORD)
  ```
- **Fix Required**: Convert to direct string logging
- **Rule**: DEBUG/TRACE must NOT use LogRecord

**Wrong Parameter Format:**
- **Symptom**: Using `{}` or `%d` instead of `%s` for substitutions
- **Detection**: Log messages with `{}`, `%d`, `%f` patterns
- **Fix Required**: Replace with `%s` for ALL substitutions
- **Rule**: Always prefer `%s` over `{}`

**Exception Handling:**
- **Symptom**: Exception not as first parameter
- **Detection**:
  ```
  LOGGER.error(ERROR.MESSAGE, exception)  // Wrong order
  ```
- **Fix Required**: Exception must come first
  ```
  LOGGER.error(exception, ERROR.MESSAGE)  // Correct
  ```

### LogMessages Structure Issues

**Missing LogMessages Class:**
- **Symptom**: No module-specific LogMessages class when needed
- **Detection**: Module has ≥10 Java types OR ≥10 INFO+ messages but no LogMessages
- **Fix Required**: Create LogMessages class following DSL-Style Constants Pattern

**Incorrect Hierarchy:**
- **Symptom**: LogMessages not following 4-level DSL structure
- **Detection**: Wrong nesting, missing @UtilityClass, incorrect structure
- **Fix Required**: Must be exactly 4 levels deep with category-level imports only

**ID Range Violations:**
- **Symptom**: LogRecord identifiers outside standard ranges
- **Detection**: Check identifier values in LogRecordModel.builder()
- **Fix Required**:
  - INFO: 001-099
  - WARN: 100-199
  - ERROR: 200-299
  - FATAL: 300-399

**Duplicate IDs:**
- **Symptom**: Same identifier used for multiple LogRecords in module
- **Detection**: Search for duplicate `.identifier(X)` values
- **Fix Required**: Ensure unique identifiers within module

### Documentation Requirements

**Missing doc/LogMessages.adoc:**
- **Symptom**: Module has LogMessages class but no documentation file
- **Detection**: Check for doc/LogMessages.adoc existence
- **Fix Required**: Create documentation file if module has ≥10 types or ≥10 INFO+ messages

**Format Non-Compliance:**
- **Symptom**: Documentation doesn't follow specified table structure
- **Detection**: Review doc/LogMessages.adoc format
- **Fix Required**: Use standard table format per Core Standards

**Content Inaccuracy:**
- **Symptom**: Documented messages don't match implementation
- **Detection**: Compare doc/LogMessages.adoc with actual LogMessages class
- **Fix Required**: Update documentation to match implementation exactly

**Incomplete Coverage:**
- **Symptom**: Not all INFO/WARN/ERROR/FATAL messages documented
- **Detection**: Count LogRecords vs documented entries
- **Fix Required**: Document all production-level messages

### Duplicate Detection Patterns

**Identical Log Messages:**
- **Symptom**: Same message text across different components
- **Example**: Multiple classes logging "User not found"
- **Resolution**: Consolidate into shared LogMessages class

**Similar Message Templates:**
- **Symptom**: Messages that could be consolidated with parameters
- **Example**: "User X created", "User Y updated", "User Z deleted"
- **Resolution**: Create single parameterized message

**Redundant LogRecord Declarations:**
- **Symptom**: Multiple LogRecords for the same purpose
- **Example**: VALIDATION_FAILED, VALIDATE_ERROR, VALIDATION_ERROR all for same thing
- **Resolution**: Choose one canonical LogRecord, remove others

**Duplicate Error Conditions:**
- **Symptom**: Same error logged in multiple places
- **Resolution**: Centralize error logging to single point

**Mixed Parameter Formats:**
- **Symptom**: Some messages using `{}` and others using `%s`
- **Detection**: Search for both patterns
- **Resolution**: Standardize ALL on `%s`

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

### LogRecord Implementation

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
- Always prefer `%s` over `{}` for parameter substitution
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

### LogMessages Structure

**Complete LogMessages template:**

```java
package com.example.mymodule;

import de.cuioss.tools.logging.LogRecord;
import de.cuioss.tools.logging.LogRecordModel;
import lombok.experimental.UtilityClass;

@UtilityClass
public final class MyModuleLogMessages {

    public static final String PREFIX = "MYMODULE";

    @UtilityClass
    public static final class INFO {

        public static final LogRecord USER_LOGIN = LogRecordModel.builder()
            .template("User %s logged in successfully")
            .prefix(PREFIX)
            .identifier(1)
            .build();

        public static final LogRecord PROCESSING_COMPLETE = LogRecordModel.builder()
            .template("Processing completed in %s ms")
            .prefix(PREFIX)
            .identifier(2)
            .build();
    }

    @UtilityClass
    public static final class WARN {

        public static final LogRecord CLOCK_SKEW = LogRecordModel.builder()
            .template("Clock skew detected: %s ms")
            .prefix(PREFIX)
            .identifier(100)
            .build();
    }

    @UtilityClass
    public static final class ERROR {

        public static final LogRecord DATABASE_CONNECTION = LogRecordModel.builder()
            .template("Database connection failed")
            .prefix(PREFIX)
            .identifier(200)
            .build();

        public static final LogRecord VALIDATION_FAILED = LogRecordModel.builder()
            .template("Validation failed for %s: %s")
            .prefix(PREFIX)
            .identifier(201)
            .build();
    }

    @UtilityClass
    public static final class FATAL {

        public static final LogRecord SYSTEM_FAILURE = LogRecordModel.builder()
            .template("Critical system failure: %s")
            .prefix(PREFIX)
            .identifier(300)
            .build();
    }
}
```

**Usage in code:**

```java
import static com.example.mymodule.MyModuleLogMessages.INFO;
import static com.example.mymodule.MyModuleLogMessages.ERROR;

public class MyService {
    private static final CuiLogger LOGGER = new CuiLogger(MyService.class);

    public void processUser(String username) {
        LOGGER.info(INFO.USER_LOGIN, username);

        try {
            // Business logic
        } catch (Exception e) {
            LOGGER.error(e, ERROR.VALIDATION_FAILED, username, e.getMessage());
        }
    }
}
```

### Test Implementation

**Adding LogAsserts to existing business logic test:**

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
// ❌ WRONG - Don't create standalone coverage tests!
@Test
void testLogRecordCoverage() {
    // This is WRONG - just testing the log, not business logic
    LOGGER.error(ERROR.VALIDATION_FAILED.format("test", "test"));
    assertLogMessagePresent(TestLogLevel.ERROR, ...);
}

// ✅ CORRECT - Test in conjunction with business logic
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
   ```bash
   # Search for actual usage
   grep -n "MY_LOGRECORD.format" src/main/java/
   ```

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
   ```java
   @Test
   void shouldLogRateLimit() {
       // Make sure this actually triggers rate limiting!
       for (int i = 0; i < 1000; i++) {
           client.makeRequest();
       }

       // Now logging should have occurred
       assertLogMessagePresent(...);
   }
   ```

### Finding the Right Business Logic Test

**Approach:**

1. **Find production usage:**
   ```bash
   grep -rn "ERROR.VALIDATION_FAILED.format" src/main/java/
   # Output: ValidationService.java:45: LOGGER.error(e, ERROR.VALIDATION_FAILED.format(...))
   ```

2. **Identify the method/class:**
   - Class: `ValidationService`
   - Method: `validate()`

3. **Find corresponding test:**
   - Look for: `ValidationServiceTest.java`
   - Find test method that exercises `validate()`

4. **Add LogAsserts to existing test:**
   ```java
   @Test
   void shouldRejectInvalidInput() {  // Existing test
       // Existing assertions
       assertThrows(ValidationException.class,
           () -> service.validate(badInput));

       // ADD LogAsserts here
       assertLogMessagePresentContaining(TestLogLevel.ERROR,
           ERROR.VALIDATION_FAILED.resolveIdentifierString());
   }
   ```

**Never:**
- Create a new test just for LogRecord coverage
- Test LogRecords in isolation without business logic
- Add LogAsserts without verifying the log is actually produced

### Distinguishing Logged vs Counted LogRecords

Some LogRecords are used for security event counting, not actual logging:

**Only Counted (No LogAsserts needed):**

```java
// Production code
securityEventCounter.increment(EventType.JWKS_JSON_PARSE_FAILED);
// No LOGGER.warn() or LOGGER.error() call with this LogRecord

// Test - no LogAsserts needed for counted-only records
@Test
void shouldIncrementSecurityCounter() {
    service.handleInvalidJwks();
    verify(securityEventCounter).increment(EventType.JWKS_JSON_PARSE_FAILED);
}
```

**Actually Logged (LogAsserts required):**

```java
// Production code - direct method call
LOGGER.warn(WARN.JWKS_JSON_PARSE_FAILED.format(errorMessage));

// OR method reference
errorMessages.forEach(LOGGER::error);
errorMessages.forEach(ERROR.PARSING_FAILED::format);

// Test - LogAsserts required
@Test
void shouldLogJwksParseError() {
    service.handleInvalidJwks();
    assertLogMessagePresentContaining(TestLogLevel.WARN,
        WARN.JWKS_JSON_PARSE_FAILED.resolveIdentifierString());
}
```

**Detection strategy:**

```bash
# Find LogRecord definition
grep -n "JWKS_JSON_PARSE_FAILED" src/main/java/LogMessages.java

# Check if it's actually logged
grep -n "JWKS_JSON_PARSE_FAILED.format" src/main/java/

# Check if it's only counted
grep -n "increment.*JWKS_JSON_PARSE_FAILED" src/main/java/
```

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

### Logger Configuration Checklist

- [ ] Only CuiLogger instances used throughout codebase
- [ ] No slf4j, log4j, or java.util.logging imports
- [ ] No System.out.println() or System.err.println() calls
- [ ] All loggers declared as `private static final CuiLogger LOGGER`
- [ ] Logger instantiated with class: `new CuiLogger(ClassName.class)`
- [ ] No @Slf4j or other logging annotations

### LogRecord Implementation Checklist

- [ ] INFO level uses LogRecord (not direct strings)
- [ ] WARN level uses LogRecord (not direct strings)
- [ ] ERROR level uses LogRecord (not direct strings)
- [ ] FATAL level uses LogRecord (not direct strings)
- [ ] DEBUG level uses direct strings (not LogRecord)
- [ ] TRACE level uses direct strings (not LogRecord)
- [ ] All parameter substitutions use `%s` (not `{}`, `%d`, etc.)
- [ ] Exception parameter comes first in all log calls with exceptions

### LogMessages Structure Checklist

- [ ] Module has LogMessages class if ≥10 types or ≥10 INFO+ messages
- [ ] LogMessages follows 4-level DSL structure
- [ ] All LogMessages classes annotated with @UtilityClass
- [ ] INFO identifiers in range 001-099
- [ ] WARN identifiers in range 100-199
- [ ] ERROR identifiers in range 200-299
- [ ] FATAL identifiers in range 300-399
- [ ] No duplicate identifiers within module
- [ ] All LogRecords follow standard template pattern

### Documentation Checklist

- [ ] doc/LogMessages.adoc exists if module has LogMessages
- [ ] Documentation follows standard table format
- [ ] All INFO/WARN/ERROR/FATAL messages documented
- [ ] Documentation matches implementation exactly
- [ ] Template strings match between docs and code
- [ ] Identifier numbers match between docs and code

### Testing Checklist

- [ ] All INFO level LogRecords tested with LogAsserts
- [ ] All WARN level LogRecords tested with LogAsserts
- [ ] All ERROR level LogRecords tested with LogAsserts
- [ ] All FATAL level LogRecords tested with LogAsserts
- [ ] LogAsserts present in BUSINESS LOGIC tests (not standalone)
- [ ] Tests use @EnableTestLogger annotation
- [ ] Tests use cui-test-juli-logger framework
- [ ] Parameter substitution tested for all LogRecords
- [ ] Exception logging tested where applicable
- [ ] Every LogRecord referenced in at least 2 places:
  - [ ] Production code (where .format() is called)
  - [ ] Business logic test (where LogAsserts verifies it)

### Duplicate Resolution Checklist

- [ ] No identical log messages across different components
- [ ] Similar messages consolidated with parameters
- [ ] No redundant LogRecord declarations
- [ ] Common errors logged from single point
- [ ] All parameter formats standardized to `%s`

## LogRecord Discovery and Coverage Verification

**Systematic script for finding all LogRecords and verifying test coverage:**

```bash
#!/bin/bash
# Find all LogRecords and verify test coverage

MODULE_PATH="${1:-src}"

echo "=== Finding all LogRecords ==="
grep -r "public static final LogRecord" --include="*LogMessages.java" $MODULE_PATH/main/java | \
  awk '{print $5}' | sort -u

echo ""
echo "=== Checking Production and Test Coverage ==="
for record in $(grep -r "public static final LogRecord" --include="*LogMessages.java" $MODULE_PATH/main/java | awk '{print $5}' | sort -u); do
    echo "LogRecord: $record"

    echo "  Production usage:"
    grep -rn "$record\.format\|$record::format" --include="*.java" $MODULE_PATH/main/java | head -3
    PROD_COUNT=$(grep -r "$record\.format\|$record::format" --include="*.java" $MODULE_PATH/main/java | wc -l)

    echo "  Test coverage (must be in business logic test):"
    grep -rn "LogAsserts.*$record\|$record.*resolveIdentifierString" --include="*Test.java" $MODULE_PATH/test/java | head -3
    TEST_COUNT=$(grep -r "LogAsserts.*$record\|$record.*resolveIdentifierString" --include="*Test.java" $MODULE_PATH/test/java | wc -l)

    if [ $PROD_COUNT -eq 0 ]; then
        echo "  ⚠️  WARNING: LogRecord not used in production - consider removing"
    elif [ $TEST_COUNT -eq 0 ]; then
        echo "  ❌ WARNING: No LogAsserts found - add to business logic test"
    else
        echo "  ✅ OK: Production ($PROD_COUNT) and Test ($TEST_COUNT) coverage"
    fi
    echo ""
done

echo "=== Summary ==="
echo "Update plan.md with findings before proceeding"
```

**plan.md Generation Script:**

```bash
#!/bin/bash
MODULE_PATH="${1:-src}"

echo "# LogRecord Test Coverage Status" > plan.md
echo "" >> plan.md
echo "## Summary" >> plan.md

# Count total LogRecords
TOTAL=$(grep -r "LogRecord.*=" --include="*LogMessages.java" $MODULE_PATH/main/java | wc -l)
echo "- Total LogRecords: $TOTAL" >> plan.md

# Count tested LogRecords
TESTED=$(grep -r "LogAsserts.*resolveIdentifierString" --include="*Test.java" $MODULE_PATH/test/java | wc -l)
echo "- Tested with LogAsserts: $TESTED" >> plan.md

# Calculate missing
MISSING=$((TOTAL - TESTED))
echo "- Missing LogAsserts: $MISSING" >> plan.md
echo "" >> plan.md

echo "## LogRecord Inventory" >> plan.md
echo "| LogRecord | Production Location | Business Test Location | Status |" >> plan.md
echo "|-----------|-------------------|----------------------|--------|" >> plan.md

# Find all LogRecords and their usage
for record in $(grep -rh "public static final LogRecord" --include="*LogMessages.java" $MODULE_PATH/main/java | awk '{print $5}' | sort -u); do
  # Find production usage
  PROD_LOC=$(grep -rn "$record\.format\|$record::format" --include="*.java" $MODULE_PATH/main/java | head -1 | cut -d: -f1-2 | sed 's|.*/||')

  # Find test usage
  TEST_LOC=$(grep -rn "LogAsserts.*$record\|$record.*resolveIdentifierString" --include="*Test.java" $MODULE_PATH/test/java | head -1 | cut -d: -f1-2 | sed 's|.*/||')

  if [ -n "$TEST_LOC" ]; then
    STATUS="✅"
  else
    STATUS="❌ Missing"
  fi

  echo "| $record | ${PROD_LOC:-Not found} | ${TEST_LOC:-Missing} | $STATUS |" >> plan.md
done

echo "" >> plan.md
echo "Generated: $(date)" >> plan.md
```

## Related Standards

- logging-standards.md - Standards for writing NEW logging code
- logging-enforcement-patterns.md - Automated enforcement patterns for tooling
- dsl-constants.md - DSL-Style Constants Pattern for LogMessages structure
