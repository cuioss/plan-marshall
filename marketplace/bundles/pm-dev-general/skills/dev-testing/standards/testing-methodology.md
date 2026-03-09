# Testing Methodology

Language-agnostic testing principles for writing reliable, maintainable tests across any technology stack.

## Fundamental Principles

* **No zero-benefit comments**. Do not add `// Arrange`, `// Act`, `// Assert` or similar phase markers — whitespace separation makes the structure clear. Comments are only justified when they explain non-obvious setup or business logic.
* **Use generated test data** — never hardcoded literals. Use randomized generators or factory methods so tests prove behavior works for any valid input, not just `"test"` or `42`. Consult your technology-specific skill for generator APIs.
* **No branching logic in tests**. Tests must never contain `if/else`, `switch`, or ternary operators. Each test exercises exactly one deterministic path. If you need to test multiple scenarios, write separate test methods.
* **Explicit assertions over implicit checks**. Always assert the expected outcome explicitly. Never rely on "no exception thrown" as the only verification.
* **Always test corner cases**: null/undefined inputs, empty collections, boundary values, error paths. Group corner cases in dedicated test classes or nested groups.
* **Boy Scout Rule**. Leave test code cleaner than you found it. When modifying a test file, fix existing issues you encounter — missing assertions, hardcoded data, poor naming, coverage-only tests. Do not defer known test defects. Never dismiss a flaky or invalid test with "not introduced by current changes" — always fix it. If fixes cascade beyond reasonable scope, stop and ask the user how to proceed.

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

* Use framework-specific generators — examples by language:
  * **Java**: [cui-test-generator](https://github.com/cuioss/cui-test-generator) for type-safe generators
  * **JavaScript**: [@faker-js/faker](https://fakerjs.dev) for realistic fake data (names, emails, dates, etc.)
  * **Python**: [Faker](https://github.com/joke2k/faker) for fake data, [Hypothesis](https://github.com/HypothesisWorks/hypothesis) for property-based test generation
* Generate values within valid ranges for the domain
* Use meaningful variable names even for generated data

### Forbidden Patterns

* Hardcoded string literals like `"test"`, `"hello"`, `"John"`
* Magic numbers like `42`, `100`, `999`
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
* **Correct**: Use polling/retry mechanisms — examples by language:
  * **Java**: [Awaitility](https://github.com/awaitility/awaitility) — DSL for polling async conditions with timeout
  * **JavaScript**: [Testing Library `waitFor`](https://testing-library.com) for DOM assertions, Cypress built-in retry for E2E
  * **Python**: [tenacity](https://github.com/jd/tenacity) — retry with backoff/stop conditions, or `asyncio.wait_for()` for async code

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

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Hardcoded test data | Tests prove nothing about general behavior | Use generated data |
| Branching in tests | Non-deterministic coverage | One path per test |
| Fixed delays | Slow and flaky | Polling/event-based waiting |
| Shared mutable state | Order-dependent failures | Isolated test data |
| Missing assertions | Tests pass but verify nothing | Explicit assertions |
| Over-mocking | Tests prove mocks work, not code | Mock at boundaries only, prefer real collaborators |
| Mocking by default | Mock libraries (Mockito, EasyMock, etc.) add complexity and hide bugs | Only use mocks when they save significant setup code; prefer real objects, test doubles, or in-memory implementations |
| Testing implementation | Brittle tests break on refactoring | Test behavior, not implementation |
