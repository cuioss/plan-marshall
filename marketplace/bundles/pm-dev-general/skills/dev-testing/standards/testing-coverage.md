# Testing Coverage

Language-agnostic coverage requirements, corner case strategies, and boundary testing patterns.

## Coverage Requirements

### Minimum Thresholds

* **Line coverage**: Minimum 80%
* **Branch coverage**: Minimum 80%
* **No coverage regressions** — new code must not decrease existing coverage

### Critical Path Coverage

Critical paths require near 100% coverage:

* Security-related code (authentication, authorization, input validation)
* Core business logic (calculations, state machines, workflow rules)
* Error handling and recovery paths
* Data validation and sanitization

### Public API Coverage

All public APIs must have tests:

* Every public method/function must be called from at least one test
* All documented parameter combinations should be tested
* Return value contracts must be verified
* Exception/error conditions must be tested

## Corner Case Testing

### Categories

Every feature should have tests for these corner case categories:

**Null/Empty inputs:**
* Null/undefined/nil values for each parameter
* Empty strings, empty collections, empty maps
* Blank strings (whitespace only)

**Boundary values:**
* Minimum and maximum valid values
* Values just inside and just outside valid ranges
* Zero, negative values, maximum integer values
* First and last elements of collections

**Type edge cases:**
* Very long strings (beyond expected length)
* Special characters (unicode, control characters, emoji)
* Deeply nested structures
* Circular references (if applicable)

**Error paths:**
* Network failures, timeouts
* Invalid input formats
* Resource exhaustion (out of memory patterns)
* Concurrent access conflicts

### Boundary Value Analysis

For any value with a valid range, test:

```
Given: Valid range is [min, max]

Test: min - 1  (just below minimum — expect rejection)
Test: min      (minimum valid — expect acceptance)
Test: min + 1  (just above minimum — expect acceptance)
Test: max - 1  (just below maximum — expect acceptance)
Test: max      (maximum valid — expect acceptance)
Test: max + 1  (just above maximum — expect rejection)
```

### Equivalence Partitioning

Divide input space into equivalence classes and test one representative from each:

* Valid equivalence classes (at least one test each)
* Invalid equivalence classes (at least one test each)
* Boundary values between classes

## Coverage Analysis Workflow

### Step 1: Identify Gaps

* Run coverage tool for the target code
* Identify uncovered lines and branches
* Prioritize by criticality (security > business logic > utility)

### Step 2: Categorize Gaps

| Priority | Category | Action |
|----------|----------|--------|
| High | Uncovered public API | Add missing tests |
| High | Uncovered error paths | Add error case tests |
| High | Uncovered validation | Add boundary tests |
| Medium | Uncovered branches | Add condition tests |
| Medium | Uncovered edge cases | Add corner case tests |
| Low | Uncovered logging/debug | Consider if worth testing |

### Step 3: Write Missing Tests

For each coverage gap:

1. Identify the specific code path not covered
2. Determine what input triggers that path
3. Write a focused test with generated data
4. Verify the coverage gap is closed
5. Ensure the test follows AAA pattern and testing methodology standards

## Test Quality Over Quantity

High coverage numbers alone do not guarantee quality:

* **Assertion-free tests** — executing code without asserting anything is worthless coverage
* **Implementation-coupled tests** — testing internal details rather than behavior creates brittle tests
* **Duplicate tests** — multiple tests covering the same path add maintenance cost without value

### Signs of Healthy Coverage

* Each test verifies a distinct behavior or edge case
* Tests break when behavior changes, not when implementation changes
* Coverage gaps are intentional (documented framework constraints) not accidental
* New features come with proportional test coverage

## Measuring Effectiveness

### Mutation Testing (Advanced)

Mutation testing modifies production code and checks if tests catch the change:

* **Killed mutant**: Test detected the code change (good)
* **Survived mutant**: Test missed the code change (gap in assertions)
* High mutation score indicates tests verify behavior, not just execute code

### Coverage Metrics Interpretation

| Metric | Meaning | Goal |
|--------|---------|------|
| Line coverage | Percentage of lines executed | ≥ 80% |
| Branch coverage | Percentage of conditions tested both ways | ≥ 80% |
| Mutation score | Percentage of mutants detected | ≥ 70% |
| Test-to-code ratio | Number of test lines per production line | ~1:1 to 2:1 |
