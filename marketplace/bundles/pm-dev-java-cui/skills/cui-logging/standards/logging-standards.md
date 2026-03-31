# CUI Logging Standards

## Required Imports

```java
// CUI Logging Framework
import de.cuioss.tools.logging.CuiLogger;
import de.cuioss.tools.logging.LogRecord;
import de.cuioss.tools.logging.LogRecordModel;

// Lombok (for LogMessages DSL pattern)
import lombok.experimental.UtilityClass;

// Static imports for LogMessages usage
import static com.example.YourLogMessages.INFO;
import static com.example.YourLogMessages.WARN;
import static com.example.YourLogMessages.ERROR;
import static com.example.YourLogMessages.FATAL;
```

For test imports (`EnableTestLogger`, `LogAsserts`, `TestLogLevel`), see `pm-dev-java-cui:cui-testing` → `standards/testing-juli-logger.md`.

## Overview

CUI projects use the CUI logging framework from cui-java-tools. This document defines standards for logger configuration, log message organization, and logging best practices.

## Logger Configuration

### Required Setup

All CUI projects MUST use `de.cuioss.tools.logging.CuiLogger`:

```java
import de.cuioss.tools.logging.CuiLogger;

public class TokenValidator {
    private static final CuiLogger LOGGER = new CuiLogger(TokenValidator.class);
}
```

**Requirements**:
* Use `CuiLogger` - not SLF4J, Log4j, or java.util.logging
* Logger must be `private static final`
* Logger constant name must be `LOGGER`
* Pass the class to logger constructor: `new CuiLogger(YourClass.class)`

### Prohibited Practices

**DO NOT**:
* Use log4j or slf4j directly
* Use `System.out.println()` or `System.err.println()`
* Use `@Slf4j` or other logging annotations
* Use prefixes like `[DEBUG_LOG]` - always use log levels
* Directly instantiate loggers in multiple places

```java
// Avoid: WRONG
@Slf4j
public class MyClass {
    System.out.println("Debug: " + message);
    log.info("[DEBUG_LOG] Processing...");
}

// Preferred: CORRECT
public class MyClass {
    private static final CuiLogger LOGGER = new CuiLogger(MyClass.class);

    public void process() {
        LOGGER.debug("Processing started");
        LOGGER.info("Processing completed");
    }
}
```

## Logging Methods

### Method Signature Rules

* **Exception parameter always comes first** when logging with exceptions
* **Use '%s' for string substitutions** (not '{}', '%d', '%f', etc.)
* Use `LogRecord` for structured logging

### Basic Logging

```java
// Simple messages
LOGGER.debug("Starting token validation");
LOGGER.info("Token validated successfully");
LOGGER.warn("Clock skew detected");
LOGGER.error("Validation failed");
LOGGER.fatal("Critical system failure");

// With parameters (%s for all substitutions)
LOGGER.info("User %s logged in from %s", username, ipAddress);

// With exception (exception comes FIRST)
LOGGER.error(exception, "Failed to connect to database: %s", url);
```

## LogRecord Usage

### Core Requirements

**CRITICAL RULES**:
* **REQUIRED**: LogRecord MUST be used for INFO, WARN, ERROR, and FATAL levels
* **PROHIBITED**: LogRecord MUST NOT be used for DEBUG or TRACE levels
* Use `LogRecord#format()` for parameterized messages
* Use `LogRecord#resolveIdentifierString()` for testing

**Rationale**:
- INFO/WARN/ERROR/FATAL are production-critical messages that require structured identifiers for monitoring, alerting, and documentation
- DEBUG/TRACE are development-only messages that don't need the overhead of LogRecord structure

### LogMessages Class Structure

Aggregate LogRecords in module-specific 'LogMessages' class:

```java
@UtilityClass
public final class AuthenticationLogMessages {
    public static final String PREFIX = "AUTH";

    @UtilityClass
    public static final class INFO {
        public static final LogRecord USER_LOGIN = LogRecordModel.builder()
            .template("User %s logged in successfully")
            .prefix(PREFIX)
            .identifier(1)
            .build();
    }

    @UtilityClass
    public static final class WARN {
        public static final LogRecord RATE_LIMIT = LogRecordModel.builder()
            .template("Rate limit exceeded for user %s")
            .prefix(PREFIX)
            .identifier(100)
            .build();
    }

    @UtilityClass
    public static final class ERROR {
        public static final LogRecord VALIDATION_FAILED = LogRecordModel.builder()
            .template("Token validation failed: %s")
            .prefix(PREFIX)
            .identifier(200)
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

### Message Identifier Ranges

Organize identifiers by log level:

| Level | Range | Example |
|-------|-------|---------|
| INFO | 001-099 | `identifier(1)` |
| WARN | 100-199 | `identifier(100)` |
| ERROR | 200-299 | `identifier(200)` |
| FATAL | 300-399 | `identifier(300)` |

**Note**: DEBUG and TRACE levels do NOT have identifier ranges because they must NOT use LogRecord.

### LogMessages Best Practices

LogMessages classes follow the DSL-Style Constants Pattern. For comprehensive DSL pattern documentation including nested structure and import patterns, see [dsl-constants.md](dsl-constants.md).

### LogMessages Documentation Requirements

**REQUIRED**: Every LogMessages class MUST have corresponding documentation at `doc/LogMessages.adoc`.

See [logmessages-documentation.md](logmessages-documentation.md) for complete documentation standards.

## Usage Examples

### Using LogRecord with Static Import

```java
import static com.example.AuthenticationLogMessages.INFO;
import static com.example.AuthenticationLogMessages.ERROR;

public class AuthenticationService {
    private static final CuiLogger LOGGER = new CuiLogger(AuthenticationService.class);

    public void authenticateUser(String username) {
        try {
            LOGGER.info(INFO.USER_LOGIN, username);
        } catch (DatabaseException e) {
            LOGGER.error(e, ERROR.DATABASE_ERROR, e.getMessage());
            throw new AuthenticationException("Authentication failed", e);
        }
    }
}
```

### LogRecord with Exception

```java
// Exception parameter always comes FIRST
LOGGER.error(exception, ERROR.VALIDATION_FAILED, exception.getMessage());
LOGGER.fatal(exception, FATAL.SYSTEM_FAILURE, "Database unavailable");
```

## Testing

For testing logging in unit tests, see `pm-dev-java-cui:cui-testing` → `standards/testing-juli-logger.md`.

## Log Levels

| Level | Usage | LogRecord |
|-------|-------|-----------|
| DEBUG | Technical details for diagnosing problems | PROHIBITED |
| TRACE | Fine-grained execution details | PROHIBITED |
| INFO | Important business events, lifecycle events | REQUIRED |
| WARN | Potentially harmful situations, recoverable issues | REQUIRED |
| ERROR | Failed operations, recoverable errors | REQUIRED |
| FATAL | Unrecoverable errors, critical system failures | REQUIRED |

### Examples by Level

```java
// DEBUG/TRACE - simple strings (LogRecord PROHIBITED)
LOGGER.debug("Parsing JWT token with algorithm: %s", algorithm);
LOGGER.trace("Entering method validateToken");

// INFO/WARN/ERROR/FATAL - LogRecord REQUIRED
LOGGER.info(INFO.USER_LOGIN, username);
LOGGER.warn(WARN.RATE_LIMIT, userId);
LOGGER.error(exception, ERROR.VALIDATION_FAILED, tokenId);
LOGGER.fatal(FATAL.SYSTEM_FAILURE, "database unreachable");
```

## Best Practices

### 1. Use LogRecord for Production Levels Only

```java
// Preferred: Good - LogRecord for INFO/WARN/ERROR/FATAL
LOGGER.info(INFO.USER_LOGIN, username);
LOGGER.warn(WARN.RATE_LIMIT, userId);

// Preferred: Good - simple strings for DEBUG/TRACE
LOGGER.debug("Validating token signature");

// Avoid: Bad - simple string for production levels
LOGGER.info("User " + username + " logged in");  // MUST use LogRecord

// Avoid: Bad - LogRecord for debug/trace
LOGGER.debug(DEBUG.TOKEN_DETAILS, token);  // PROHIBITED
```

### 2. Exception Parameter First

```java
// Preferred: Good
LOGGER.error(exception, ERROR.VALIDATION_FAILED, tokenId);

// Avoid: Bad
LOGGER.error(ERROR.VALIDATION_FAILED, tokenId, exception);  // Won't work
```

### 3. Use %s for All Substitutions

```java
// Preferred: Good
LOGGER.info("Processing %s records in %s ms", count, duration);

// Avoid: Bad
LOGGER.info("Processing %d records", count);  // Use %s
```

### 4. Don't Log Sensitive Information

```java
// Avoid: Bad
LOGGER.info("User password: %s", password);

// Preferred: Good
LOGGER.info("User authenticated: %s", username);
```

---

For compliance verification patterns (violation detection, coverage analysis, identifier validation), see `logging-maintenance-reference.md`.

---

## Quality Rules

### Implementation
- CuiLogger used (not SLF4J or Log4j)
- Logger is private static final named LOGGER
- LogRecord REQUIRED for INFO/WARN/ERROR/FATAL
- LogRecord NOT used for DEBUG/TRACE
- LogMessages class follows DSL pattern
- Identifiers in correct ranges
- Exception parameter comes first
- %s used for all substitutions
- No sensitive information logged
- No System.out or System.err usage

### Documentation
- doc/LogMessages.adoc exists and is up-to-date
- LogMessages.adoc includes all production-level messages

### Compliance
- All production-level logging uses LogRecord
- All LogRecords have test coverage
- Identifiers are sequential within ranges
