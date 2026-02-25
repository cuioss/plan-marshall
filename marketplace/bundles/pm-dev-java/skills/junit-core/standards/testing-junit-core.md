# JUnit Core Testing Standards

## Fundamental Rules

* **Never introduce libraries** without asking the user first. This includes test utilities, assertion libraries, mocking frameworks, and any other dependency.
* **No zero-benefit comments**. Do not add `// Arrange`, `// Act`, `// Assert` or similar phase markers — whitespace separation makes the structure clear. Comments are only justified when they explain non-obvious setup or business logic.
* **Use generators for test data** — never hardcoded literals. Use randomized generators (e.g., `Generators.nonEmptyStrings().next()`, `UUID.randomUUID()`) so tests prove behavior works for any valid input, not just `"test"` or `42`. See `pm-dev-java-cui:cui-testing` for CUI generator framework.
* **Never use `Thread.sleep`** for waiting in tests. Use Awaitility for all async waiting — it provides readable, timeout-safe polling. See `standards/testing-async-patterns.md` for patterns.
* **Never use reflection** to access private fields or methods in tests — this is always a bug, not a workaround. If code is hard to test, prefer these alternatives in order:
  1. **Refactor for testability** — extract logic into a testable collaborator or method
  2. **Relax visibility** — change `private` to package-private so the test (same package) can access it directly
  Neither is perfect, but both are better than reflection hacks or brittle tests that break on internal renames.
* **Always test corner cases**: null inputs, empty collections, boundary values, error paths. Group corner cases in `@Nested` classes or dedicated test types.

## Test Class Requirements

Each type (class, interface, enum with behavior) requires at least one dedicated test class.

* Test class naming: `{ClassName}Test.java` for production class `{ClassName}.java`
* Test classes in same package structure under `src/test/java`
* One test class per production class (1:1 mapping)

**Splitting large test classes**: When a test class exceeds ~200 lines, split into multiple types:
* `{ClassName}Test.java` — happy-path and core behavior
* `{ClassName}EdgeCaseTest.java` — corner cases and error paths
* `{ClassName}IntegrationTest.java` — integration scenarios

**Exceptions:** Enums without custom methods (only constants).

## Test Coverage

* Minimum 80% line coverage
* Minimum 80% branch coverage
* Critical/hot paths: aim for near 100% coverage (security, validation, error handling, core business logic)
* All public APIs must be tested
* No coverage regressions allowed

## AAA Pattern (Arrange-Act-Assert)

All tests follow the AAA pattern — separated by blank lines, no phase comments:

```java
@Test
@DisplayName("Should validate token with correct issuer")
void shouldValidateTokenWithCorrectIssuer() {
    var issuer = Generators.nonBlankStrings().next();
    var token = createTokenWithIssuer(issuer);

    var result = validator.validate(token);

    assertTrue(result.isValid(), "Token should be valid");
    assertEquals(issuer, result.getIssuer(), "Issuer should match");
}
```

* One logical assertion per test (use `assertAll` to group related assertions)
* Descriptive variable names
* Generated test data, not literals

## JUnit 5 Assertion Features

Use the full JUnit 5 assertion API — do not reimplement what the framework provides:

```java
// Type checking — use assertInstanceOf, not instanceof + cast
assertInstanceOf(TokenValidationException.class, exception, "Should be validation exception");

// Grouped assertions — verify multiple properties without stopping at first failure
assertAll("User properties",
    () -> assertEquals(expectedName, user.getName(), "Name should match"),
    () -> assertNotNull(user.getEmail(), "Email should be present"),
    () -> assertTrue(user.isActive(), "User should be active")
);

// No-throw verification
assertDoesNotThrow(() -> service.process(validInput), "Valid input should not throw");

// Timeout assertions
assertTimeout(Duration.ofSeconds(2), () -> service.computeResult(), "Should complete within 2s");
```

All assertions include meaningful failure messages (20-60 characters). Messages describe what should have happened:
- `"Token should be valid"` (correct)
- `"Token is invalid"` (wrong — describes failure, not expectation)

### Exception Testing

Use `assertThrows` — move setup code outside the lambda, keep only the throwing statement inside:

```java
@Test
@DisplayName("Should throw exception on invalid input")
void shouldThrowExceptionOnInvalidInput() {
    var input = Generators.nonBlankStrings().next();
    service.validateInput(input);

    var exception = assertThrows(
        TokenValidationException.class,
        () -> service.processInput(input),
        "Invalid token should trigger validation exception"
    );

    assertNotNull(exception.getMessage(), "Exception should have message");
}
```

## Test Organization with @Nested

Use `@Nested` extensively to group related tests. This improves readability and structures test output. Use nesting when **3 or more tests** belong to the same logical group — do not nest single or two tests.

```java
@DisplayName("Token Validator Tests")
class TokenValidatorTest {

    @Nested
    @DisplayName("Valid Token Handling")
    class ValidTokenTests {
        @Test
        void shouldAcceptTokenWithValidSignature() { }

        @Test
        void shouldAcceptTokenWithFutureExpiry() { }

        @Test
        void shouldAcceptTokenWithAllRequiredClaims() { }
    }

    @Nested
    @DisplayName("Invalid Token Handling")
    class InvalidTokenTests {
        @Test
        void shouldRejectExpiredToken() { }

        @Test
        void shouldRejectTokenWithInvalidSignature() { }

        @Test
        void shouldRejectTokenWithMissingClaims() { }
    }

    @Nested
    @DisplayName("Corner Cases")
    class CornerCaseTests {
        @Test
        void shouldHandleNullToken() { }

        @Test
        void shouldHandleEmptyToken() { }

        @Test
        void shouldHandleMalformedBase64() { }
    }
}
```

## Test Types

### Unit Tests

* Test a single unit in isolation
* Mock or stub dependencies
* Test classes named `*Test.java`

### Integration Tests

* Test interaction between components
* May use real dependencies or test doubles
* Test classes named `*IT.java` or `*ITCase.java`
* See `standards/testing-integration.md` for naming conventions, separation patterns, and nesting
* See `pm-dev-java:junit-integration` skill for Maven Failsafe/Surefire configuration

## Related Skills

- `pm-dev-java-cui:cui-testing` - CUI-specific test generators and library restrictions
- `pm-dev-java:junit-integration` - Maven Failsafe/Surefire configuration
