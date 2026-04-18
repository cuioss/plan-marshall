# Testing Methodology

Language-agnostic testing principles for writing reliable, maintainable tests across any technology stack.

## Fundamental Principles

* **No zero-benefit comments**. Do not add `// Arrange`, `// Act`, `// Assert` or similar phase markers — whitespace separation makes the structure clear. Comments are only justified when they explain non-obvious setup or business logic.
* **Prefer generated test data** over hardcoded literals. Use randomized generators or factory methods so tests prove behavior works for any valid input, not just `"test"` or `42`. Consult your technology-specific skill for generator APIs. **Exceptions:** specific values are appropriate when testing format-specific parsing (e.g., date patterns, protocol constants), known boundary values from a specification, or exact error messages.
* **No branching logic in tests**. Tests must never contain `if/else`, `switch`, or ternary operators. Each test exercises exactly one deterministic path. If you need to test multiple scenarios, write separate test methods.
* **Explicit assertions over implicit checks**. Always assert the expected outcome explicitly. Never rely on "no exception thrown" as the only verification.
* **Always test corner cases**: null/undefined inputs, empty collections, boundary values, error paths. Group corner cases in dedicated test classes or nested groups.

## Test Categories

**Never write tests just for coverage metrics or a green bar.** Tests that execute code without verifying behavior are always a bug — they create false confidence and must be rewritten. If you encounter assertion-free tests or tests that only check "no exception thrown", treat them as defects. Every test must assert a specific contract. If in doubt about what a test should verify, ask the user.

Every unit test targets the **contract** (API/specification) of the method under test, never its internal implementation. Tests that depend on implementation details break on refactoring without catching real bugs.

Organize tests into these categories, in order of priority:

### 1. Happy Path

Tests that exercise the method as intended by its specification. Use generated data within the defined valid ranges to prove the method works for any conforming input, not just hand-picked examples.

### 2. Parameter Variants

Systematic exploration of the valid input space using generators. Vary parameters across their specified types, ranges, and combinations. This is the rigorous form of happy-path testing — if the spec says "accepts strings of 1-255 characters", generate strings across that range.

### 3. Corner Cases

Inputs deliberately **outside** or **at the boundary** of specified constraints: null/undefined values, empty collections, zero-length strings, minimum/maximum boundary values, invalid formats. These verify the method's defensive behavior.

### 4. Error Conditions

Scenarios where **infrastructure assumptions are not met**: dependencies unavailable, services returning errors, resources missing, timeouts occurring. These verify graceful degradation and proper error propagation.

Each category should be grouped in its own test class or nested group (see Test Class Organization below).

## AAA Pattern (Arrange-Act-Assert)

All tests follow three phases separated by blank lines:

```
test "Should validate input with correct format" {
    // Phase 1: Arrange — set up test data and preconditions
    input = generateValidInput()
    expectedResult = createExpectedResult(input)

    // Phase 2: Act — execute the single operation under test
    result = service.validate(input)

    // Phase 3: Assert — verify expected outcome
    assert result.isValid == true
    assert result.value == expectedResult
}
```

### Rules

* One logical assertion per test (group related assertions using framework features like `assertAll`)
* Descriptive variable names that convey intent
* Generated test data, not hardcoded literals
* Single action in the Act phase — if you need multiple actions, it's an integration test or needs splitting

## Test Class Organization

### Test Class Mapping

Each production type (class, module, component) requires at least one dedicated test class/file.

* Test naming: `{ProductionName}Test` or `{ProductionName}.test` (follow framework convention)
* Test files in the same package/directory structure as production code (in test source root)
* At least one test file per production file — split into multiple when exceeding ~200 lines

### Splitting Large Test Files

When a test file exceeds ~200 lines, split into focused groups:

* `{Name}Test` — happy-path and core behavior
* `{Name}EdgeCaseTest` — corner cases and error paths
* `{Name}IntegrationTest` — integration scenarios

### Grouping Related Tests

Use nesting constructs (JUnit `@Nested`, Jest `describe`, etc.) when **3 or more tests** belong to the same logical group. Do not nest single or two tests.

Typical groups:
* Valid input handling
* Invalid input handling
* Corner cases / edge cases
* Error paths

## Test Naming

Test names should describe the expected behavior:

* **Pattern**: `should{ExpectedBehavior}When{Condition}` or `should{ExpectedBehavior}`
* **Good**: `shouldRejectExpiredToken`, `shouldReturnEmptyListWhenNoResults`
* **Bad**: `test1`, `testValidation`, `itWorks`

## Test Data Principles

### Generated Data

Tests should use generated/random data to prove behavior works for any valid input:

* Use framework-specific generators (consult your language-specific testing skill for recommended libraries)
* Generate values within valid ranges for the domain
* Use meaningful variable names even for generated data

### Forbidden Patterns

* Arbitrary hardcoded literals like `"test"`, `"hello"`, `"John"` or magic numbers like `42`, `100` when the test would work equally well with any valid input (use generators instead)
* Shared mutable test state between tests
* Test order dependencies

### Test Data Factories

For complex objects, create factory methods or builders:

```
// Factory method for test objects
function createValidUser(overrides = {}) {
    return {
        name: generateName(),
        email: generateEmail(),
        ...overrides
    }
}
```

## Test Reliability

### No Fixed Delays

Never use fixed-time waits in tests:

* **Anti-pattern**: `sleep(2000)`, `Thread.sleep(5000)`, `cy.wait(3000)`
* **Correct**: Use polling/retry mechanisms provided by your testing framework (consult your language-specific testing skill for recommended libraries)

Fixed delays make tests slow and flaky — they either wait too long (slow CI) or not long enough (intermittent failures).

### Deterministic Paths

Each test must exercise exactly one deterministic path through the code:

* No conditional logic deciding what to assert
* No try/catch in test code (unless testing exception behavior)
* No loops that may execute 0 times
* No reliance on external state (time, network, filesystem)

### Test Isolation

Each test must be independent:

* Tests must not depend on execution order
* Tests must not share mutable state
* Each test creates its own test data
* Each test cleans up its own resources (or uses framework lifecycle hooks)

## Integration Test Separation

Integration tests must be separated from unit tests:

* **Unit tests**: Fast, isolated, run on every build
* **Integration tests**: May be slower, test component interaction, run in CI/CD
* Separate by naming convention or directory structure per framework
* CI/CD pipelines should be able to run each type independently

## Assertion Quality

### Meaningful Messages

All assertions should include descriptive failure messages:

* Describe what should have happened, not what went wrong
* **Good**: `"Token should be valid"`, `"Result list should contain 3 items"`
* **Bad**: `"Failed"`, `"Token is invalid"`, `"Wrong"`

### One Concept Per Test

Test one logical concept per test method. Use grouped assertions (like `assertAll`) when verifying multiple properties of a single result — but don't test unrelated behaviors in one test.

## Property-Based Testing

Property-based testing complements example-based tests by generating many random inputs and verifying that invariants (properties) hold for all of them. This is particularly effective for:

* **Pure functions** with well-defined input/output contracts
* **Serialization/deserialization** roundtrips (encode then decode yields original)
* **Mathematical properties** (commutativity, associativity, idempotency)
* **Data structure invariants** (sorted output stays sorted, size constraints hold)

### When to use property-based tests

* The function has a clear contract expressible as "for all valid inputs, this property holds"
* Example-based tests feel incomplete — you suspect edge cases exist but can't enumerate them
* The input space is large or complex (strings, collections, nested structures)

### When NOT to use property-based tests

* The behavior is inherently example-specific (UI rendering, specific business rules)
* Generating valid inputs is harder than writing the test
* The function has significant side effects that are hard to verify as properties

### Writing properties

A good property is a universal statement about the function's behavior:

```
// Property: parsing a valid token always succeeds
for all validToken in generateValidTokens():
    assert parse(validToken).isSuccess()

// Property: roundtrip -- serialize then deserialize yields original
for all user in generateUsers():
    assert deserialize(serialize(user)) == user

// Property: sorting is idempotent
for all list in generateLists():
    assert sort(sort(list)) == sort(list)
```

Consult your language-specific testing skill for framework APIs (e.g., Hypothesis for Python, jqwik for Java, fast-check for JavaScript).

## Test Doubles

Test doubles substitute real dependencies in unit tests. Choose the simplest double that makes the test work.

### Taxonomy (simplest to most complex)

| Double | What it does | When to use |
|--------|-------------|-------------|
| **Dummy** | Passed but never used (satisfies a parameter) | Filling required parameters the test doesn't care about |
| **Stub** | Returns canned answers to calls | Controlling indirect inputs (e.g., config values, lookup results) |
| **Fake** | Working implementation with shortcuts (e.g., in-memory database) | When real dependency is slow/unavailable but behavior matters |
| **Spy** | Records calls for later verification | Verifying that a side effect occurred (e.g., event published) |
| **Mock** | Pre-programmed expectations that verify interactions | Complex interaction verification (use sparingly) |

### Guidelines

* **Prefer real objects** when they're fast and deterministic. A real `ArrayList` is better than a mocked `List`.
* **Prefer fakes over mocks** for complex dependencies. An in-memory repository is more realistic than a mocked one.
* **Mock at system boundaries** — external services, databases, file systems, network calls. Don't mock internal collaborators.
* **Don't verify implementation details** with mocks. Verifying that `service.save()` was called is testing implementation. Verifying the entity appears in the repository tests behavior.
* **One mock per test** is a good heuristic. If a test needs many mocks, the unit under test may have too many dependencies (SRP violation).

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Arbitrary hardcoded data | Tests prove nothing about general behavior | Use generated data (except for format-specific, boundary, or spec-defined values) |
| Branching in tests | Non-deterministic coverage | One path per test |
| Fixed delays | Slow and flaky | Polling/event-based waiting |
| Shared mutable state | Order-dependent failures | Isolated test data |
| Missing assertions | Tests pass but verify nothing | Explicit assertions |
| Over-mocking | Tests prove mocks work, not code | Mock at boundaries only, prefer real collaborators |
| Mocking by default | Mock libraries add complexity and hide bugs | Only use mocks when they save significant setup; prefer real objects, fakes, or in-memory implementations |
| Testing implementation | Brittle tests break on refactoring | Test behavior, not implementation |
| Pinning known-wrong behavior as a "documented limitation" | A test that asserts the bug creates friction against fixing it — the test itself becomes the obstacle to the improvement | Assert the *correct* behavior and mark the test expected-to-fail (see below) or skipped with a TODO; never assert the wrong behavior |

### Surfacing limitations without locking them in

When writing tests surfaces a real limitation in the code under test (e.g. a comparator that uses substring matching where boundary matching is required), resist the temptation to write a test that asserts the broken behavior and label it a "documented limitation". Such a test does not express intent — it expresses a workaround masquerading as intent, and a future reviewer wanting to fix the bug must argue both for the fix and for deleting the test that "proves" the bug is intentional.

Instead:

1. **Fix the limitation in the same task** if the fix is small (a handful of lines) and the code path is already being touched.
2. **Write a test that asserts the *correct* behavior** even if the code currently fails it, and mark it expected-to-fail with a clear TODO referencing where the fix will land. Use the language's idiom for expected failure:
   * Python / pytest: `@pytest.mark.xfail(reason="TODO: fix boundary matching — see LESSON-nnnn")` (preferred — reports `XPASS` when the bug is fixed) or `@pytest.mark.skip(reason="…")`.
   * JUnit 5: `Assumptions.abort("TODO: …")` or `@Disabled("TODO: …")`.
   * Jest: `test.skip("TODO: …")` with a TODO comment (Jest has no native expected-fail marker). Vitest: `test.fails("…")` runs the test and records it as a known failure.
3. **Surface the limitation up the chain** — record it in a lesson, a PR body, or an issue — so the follow-up is tracked. Do not encode it as a regression test that future-you has to argue against.

Signals that the anti-pattern is about to be committed: the test name contains phrases like "documented limitation", "known behavior", "future-work", or "trade-off"; the test's docstring explains *why* the assertion is intentionally wrong; the rationale claims an alternative implementation "would be a breaking change" for the test. When reviewing, ask: would the author still write this test if the underlying bug were fixed five minutes before the review? If the answer is "no, the test would be deleted", the test does not deserve to land.
