# JUnit Core Testing Standards

For general testing principles (AAA pattern, test organization, coverage requirements, test reliability), see `plan-marshall:persona-module-tester`. This document covers JUnit 5-specific API and patterns.

## Fundamental Rules

* **Never introduce libraries** without asking the user first. This includes test utilities, assertion libraries, mocking frameworks, and any other dependency.
* Choose generated data or an exact literal by what the contract is. Where the contract is **universal** ("for all valid inputs, P holds" — parsers, validators, normalisers, round-trip encoders), use randomized generators (e.g., `Generators.nonEmptyStrings().next()`, `UUID.randomUUID()`); see `pm-dev-java-cui:cui-testing` for the CUI generator framework. Where **the literal *is* the contract** (a configuration default, a canonical id, a serialized field name, a documented exit code, a spec-defined boundary value), write the value exactly — a generator there replaces the one value that matters with an arbitrary one and asserts nothing. The full statement is `plan-marshall:persona-module-tester` § "Test Data Principles → The discriminator".
* **Never use `Thread.sleep`** for waiting in tests. Use Awaitility for all async waiting — it provides readable, timeout-safe polling. See `standards/testing-async-patterns.md` for patterns.
* **Never use reflection** to access private fields or methods in tests — this is always a bug, not a workaround. If code is hard to test, prefer these alternatives in order:
  1. **Refactor for testability** — extract logic into a testable collaborator or method
  2. **Relax visibility** — change `private` to package-private so the test (same package) can access it directly

## Test Class Requirements

* At least one test class per production class — split into multiple when the class exceeds the **400-line budget**, by behaviour cluster (`{Name}Test`, `{Name}EdgeCaseTest`, `{Name}IntegrationTest`) rather than in arbitrary halves. The budget and its derivation are stated once in `plan-marshall:persona-module-tester` § "Module Budget: 400 lines"
* Test class naming: `{ClassName}Test.java` for production class `{ClassName}.java`
* Test classes in same package structure under `src/test/java`
* **Exceptions:** Enums without custom methods (only constants).

## JUnit 5 AAA Pattern

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

## Removing a Redundant Test

Two tests that prove the same behaviour are one test too many, and removing one is ordinary hygiene. The removal is correct only when the test that stays asserts at least as much as the one that goes.

1. **Name the surviving test.** A test is redundant with respect to one named test, not with respect to "the other tests".
2. **Compare the assertions, not the names or the lines executed.** The two tests may call the same method and differ in what they check — the whole returned object against one of its fields, an exact message against its presence, a counter against no counter.
3. **Move what is stricter before deleting.** Every assertion the removed test makes and the surviving test does not is added to the surviving test first.
4. **Stop when the surviving test cannot be changed.** If it is out of scope for the change, the stricter test stays, and the pair is reported instead of removed.
5. **Check the inputs.** Tests that look identical can differ in the value they feed — a different key size, realm, or boundary value. Where the difference selects a different path, they are not duplicates.

An unchanged coverage figure does not replace step 2 — see `coverage-analysis-pattern.md`, "What an Unchanged Coverage Figure Does Not Show". A lower test count after the removal is expected; state the count before, the number removed, and the count after.

When the removed test is referenced elsewhere — a threat model, a traceability table, a review report — the reference is re-pointed to the surviving test in the same change. Search for the removed method names as well as the removed class names.

## Tests That Cannot Fail

A test that passes on a uniformly wrong implementation is worse than no test: it reports coverage over behaviour nobody checked. Six shapes recur, and each is paired below with the form that can fail. The language-agnostic treatment of matched positive controls and non-vacuity lives in `plan-marshall:persona-module-tester` § "Neutralize State-Dependent Branch Selection at the Fixture Level" and § "Guard a Runtime-Derived Parametrization at the Binding Site"; this section carries only the JUnit-specific before/after and does not restate that guidance.

### Assertion with no concrete anchor

A relational or parity assertion compares two computed values, so a uniformly wrong result satisfies it.

```java
// Before — no anchor: passes when both values are wrong together
assertTrue(result.getWidth() > result.getHeight());
assertEquals(a % 2, b % 2);

// After — one side is the concrete value the contract names
assertEquals(1920, result.getWidth());
assertEquals(1080, result.getHeight());
```

### Test named for a builder default that passes it explicitly

The test's name claims the default, but the arrange step supplies the value, so the default is never read.

```java
// Before — the default is named in the test but supplied by the caller
var config = new ConfigBuilder().timeout(30).build();
assertEquals(30, config.timeout());

// After — the default is reached through the production path
var config = new ConfigBuilder().build();
assertEquals(DEFAULT_TIMEOUT, config.timeout());
```

### Negative assertion vacuous by construction

A new invariant can make the forbidden state unreachable, so the negative assertion passes without ever exercising the branch it names.

```java
// Before — reachable only while the input is unvalidated
assertThrows(IllegalArgumentException.class, () -> service.accept(""));

// After — the positive control shows the call succeeds on valid input, and the
// message pins the branch that rejected the invalid one
assertEquals(ACCEPTED, service.accept("value"));
var exception = assertThrows(IllegalArgumentException.class, () -> service.accept(""));
assertEquals("empty input", exception.getMessage());
```

### Mirrored name list or enum cardinality

A hardcoded copy of a set another file defines stays green when that set grows, because the copy and the production set drift independently.

```java
// Before — the copy and the declaration drift apart in silence
assertEquals(Set.of("admin", "user", "auditor"), service.roles());

// After — the expected set is derived from the declaration it mirrors
var expected = Arrays.stream(Role.values()).map(Role::wireName).collect(Collectors.toSet());
assertEquals(expected, service.roles());
```

### Security test citing a specification without its clause

"Per OWASP" or "per the RFC" names no clause, so a later rule change cannot be traced to the test that should have caught it.

```java
// Before — the citation names a document, not the clause under test
@Test
@DisplayName("Should reject CRLF per OWASP")
void shouldRejectCrlf() { }

// After — the clause the assertion exercises is named and the body proves it
@Test
@DisplayName("Rejects CRLF in the request target (RFC 9112 section 3.2)")
void shouldRejectCrlf() {
    var target = "/search?q=a\r\nb";
    assertThrows(InvalidRequestTargetException.class, () -> parser.parse(target));
}
```

### Fail-open assertion with no stated reason

An assertion that a request is accepted reads the same whether the allowance is deliberate or an accident, so a later tightening cannot tell them apart.

```java
// Before — acceptance asserted with no reason
assertTrue(response.isAccepted());

// After — the deliberate allowance is stated as the contract it is
assertTrue(response.isAccepted(), "anonymous health probe is deliberately unauthenticated");
```

## Test Types

* Unit test classes named `*Test.java`
* Integration test classes named `*IT.java` or `*ITCase.java`
* See `pm-dev-java:junit-integration` skill for Maven Failsafe/Surefire configuration

## Related Skills

- `plan-marshall:persona-module-tester` - Language-agnostic testing principles (AAA, coverage, reliability)
- `pm-dev-java-cui:cui-testing` - CUI-specific test generators and library restrictions
- `pm-dev-java:junit-integration` - Maven Failsafe/Surefire configuration
