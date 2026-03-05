# DSL-Style LogMessages Constants

For the general DSL-style nested constants pattern (structure, guidelines, best practices, examples), see the `pm-dev-java:java-core` skill standard: `standards/dsl-constants.md`.

This document covers only the CUI LogRecord-specific application of that pattern.

## LogMessages Structure with LogRecord

CUI logging uses the DSL constants pattern to organize `LogRecord` instances by log level:

```java
@UtilityClass
public final class ModuleLogMessages {
    public static final String PREFIX = "MODULE";

    @UtilityClass
    public static final class INFO {
        public static final LogRecord USER_LOGIN = LogRecordModel.builder()
            .template("User %s logged in successfully")
            .prefix(PREFIX)
            .identifier(1)
            .build();
        // Additional INFO messages (identifiers 1-99)
    }

    @UtilityClass
    public static final class WARN {
        // Warning messages (identifiers 100-199)
    }

    @UtilityClass
    public static final class ERROR {
        // Error messages (identifiers 200-299)
    }
}
```

## Identifier Range Allocation

| Level | Range | Purpose |
|-------|-------|---------|
| INFO | 1-99 | Informational messages |
| WARN | 100-199 | Warning messages |
| ERROR | 200-299 | Error messages |
| FATAL | 300-399 | Fatal error messages |

## Usage with CuiLogger

```java
// Static import at category level
import static com.example.ModuleLogMessages.INFO;
import static com.example.ModuleLogMessages.ERROR;

LOGGER.info(INFO.USER_LOGIN, username);
LOGGER.error(exception, ERROR.DATABASE_ERROR, details);
```

## Related Standards

- [logging-standards.md](logging-standards.md) - Complete LogMessages implementation, CuiLogger rules, and testing strategies
- [logmessages-documentation.md](logmessages-documentation.md) - AsciiDoc documentation patterns for LogMessages
