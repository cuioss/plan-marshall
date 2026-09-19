# DSL-Style LogMessages Constants

CUI logging uses the DSL-Style Nested Constants Pattern to organize `LogRecord` instances by log level. For the general pattern (structure, guidelines, naming conventions), see `pm-dev-java:java-core` skill → `standards/dsl-constants.md`.

This document covers only the CUI LogRecord-specific application.

## Identifier Range Allocation

| Level | Range | Purpose |
|-------|-------|---------|
| INFO | 1-99 | Informational messages |
| WARN | 100-199 | Warning messages |
| ERROR | 200-299 | Error messages |
| FATAL | 300-399 | Fatal error messages |

**Note**: DEBUG and TRACE levels do NOT have identifier ranges because they must NOT use LogRecord.

## Related Standards

- [logging-standards.md](logging-standards.md) - Complete LogMessages implementation and CuiLogger rules
- [logmessages-documentation.md](logmessages-documentation.md) - AsciiDoc documentation patterns for LogMessages
- `pm-dev-java:java-core` → `standards/dsl-constants.md` - General DSL-Style Nested Constants Pattern
