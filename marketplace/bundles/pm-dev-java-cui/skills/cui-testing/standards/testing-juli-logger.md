# CUI Test JULi Logger

## Required Imports

```java
// CUI Test JULi Logger
import de.cuioss.test.juli.junit5.EnableTestLogger;
import de.cuioss.test.juli.LogAsserts;
import de.cuioss.test.juli.TestLogLevel;
```

## What is it?

Provides classes simplifying the configuration and asserting of logging in the context of unit tests using Java Util Logging (JUL).

## How To Use It

### Enable for a Unit Test

```java
@EnableTestLogger
class PortalHealthServletTest {}
```

### Configure for All Tests

```java
@EnableTestLogger(rootLevel = TestLogLevel.INFO, trace = List.class, error = Set.class)
class PortalHealthServletTest {}
```

The logger and level are reset for each test.

### Asserting Log Statements

Assert whether log statements were written or not:

```java
@EnableTestLogger
class PortalHealthServletTest {

    @Test
    void shouldAssertLogs() {
        LogAsserts.assertLogMessagePresent(TestLogLevel.DEBUG, "Should be there at least once");
        LogAsserts.assertSingleLogMessagePresent(TestLogLevel.INFO, "Should be there exactly once");
        LogAsserts.assertLogMessagePresentContaining(TestLogLevel.INFO, "part of the expected message");
        LogAsserts.assertNoLogMessagePresent(TestLogLevel.WARN, PortalHealthServlet.class);
        // and many more asserts
    }
}
```

### Changing LogLevel Dynamically

```java
TestLogLevel.DEBUG.addLogger(PortalHealthServlet.class);
// Set Root-level to debug
TestLogLevel.DEBUG.setAsRootLevel();
```

## Testing Log Output with LogAsserts

The `LogAsserts` class provides comprehensive assertion methods for verifying log output in tests.

### Basic Log Assertions

```java
@EnableTestLogger
class TokenValidatorTest {

    @Test
    void shouldLogValidationSuccess() {
        validator.validate(validToken);

        // Assert log message was written at least once
        LogAsserts.assertLogMessagePresentContaining(TestLogLevel.INFO, "validated");

        // Assert log message was written exactly once
        LogAsserts.assertSingleLogMessagePresent(TestLogLevel.INFO, "Token validated successfully");
    }

    @Test
    void shouldLogValidationError() {
        validator.validate(invalidToken);

        // Assert error was logged
        LogAsserts.assertLogMessagePresentContaining(TestLogLevel.ERROR, "validation failed");
    }

    @Test
    void shouldNotLogWarnings() {
        validator.validate(validToken);

        // Assert no warning messages were logged
        LogAsserts.assertNoLogMessagePresent(TestLogLevel.WARN, TokenValidator.class);
    }
}
```

**Diagnostic Support**: When a `LogAsserts` assertion fails, the failure message automatically includes all recorded log messages, making it easy to diagnose what was actually logged versus what was expected. This is implemented in all assertion methods via `testHandler.getRecordsAsString()` (see [LogAsserts.java:91](https://github.com/cuioss/cui-test-juli-logger/blob/main/src/main/java/de/cuioss/test/juli/LogAsserts.java#L91)).
```

### Testing with LogRecord Identifiers

When using CUI LogRecord for structured logging, verify that the correct LogRecord was used:

```java
import static com.example.TokenValidatorLogMessages.INFO;

@EnableTestLogger
class TokenValidatorTest {

    @Test
    void shouldLogCorrectIdentifier() {
        validator.validate(token);

        // Verify the correct LogRecord was used by checking its identifier
        String expectedIdentifier = INFO.TOKEN_VALIDATED.resolveIdentifierString();
        LogAsserts.assertSingleLogMessagePresentContaining(
            TestLogLevel.INFO, expectedIdentifier);
    }

    @Test
    void shouldLogWithCorrectParameters() {
        String userId = "user123";
        validator.validate(token, userId);

        // Verify both identifier and parameter values
        String identifier = INFO.VALIDATION_SUCCESS.resolveIdentifierString();
        LogAsserts.assertLogMessagePresentContaining(TestLogLevel.INFO, identifier);
        LogAsserts.assertLogMessagePresentContaining(TestLogLevel.INFO, userId);
    }
}
```

## Integration with CUI Logging Framework

This testing framework integrates seamlessly with the CUI logging standards:

- **CuiLogger**: Production code uses `CuiLogger` for logging
- **LogRecord**: Production INFO/WARN/ERROR/FATAL messages use `LogRecord` for structured logging
- **cui-test-juli-logger**: Test code uses `@EnableTestLogger` and `LogAsserts` to verify log output

**Test Scope**: Add `<scope>test</scope>` to the Maven dependency:

```xml
<dependency>
    <groupId>de.cuioss.test</groupId>
    <artifactId>cui-test-juli-logger</artifactId>
    <scope>test</scope>
</dependency>
```

## References

**Source:**
- [README Documentation](https://github.com/cuioss/cui-test-juli-logger/blob/main/README.adoc)

**Additional Resources:**
- [cui-test-juli-logger on GitHub](https://github.com/cuioss/cui-test-juli-logger)