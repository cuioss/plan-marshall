# Coverage Analysis Pattern

Coverage analysis identifies untested code paths, prioritizes gaps, and guides test improvement efforts.

## Coverage Types and Thresholds

| Type | Minimum | Measurement |
|------|---------|-------------|
| Line Coverage | 80% | Lines executed / Total lines |
| Branch Coverage | 80% | Branches executed / Total branches |
| Method Coverage | 100% public, 80% package-private | Methods executed / Total methods |

**Exclusions:** Test classes, test utilities, generated code, configuration classes.

## Gap Prioritization

| Priority | Characteristics | Action |
|----------|----------------|--------|
| **High** | Public methods, error handling, critical paths, validation, security | Test immediately |
| **Medium** | Package-private methods, helper methods, data transformation | Test after high priority |
| **Low** | Defensive null checks, impossible branches, logging only | Test if time permits |

## Gap Analysis Patterns

| Pattern | Symptom | Strategy |
|---------|---------|----------|
| **Error Handling** | Catch blocks or throw statements uncovered | Mock dependency to throw exception; verify exception propagation |
| **Branch Coverage** | One branch of if/else covered, other uncovered | Add test for uncovered branch; parameterized test |
| **Method Coverage** | Public method with 0% coverage | Add basic test exercising method; verify side effects |
| **Complex Conditional** | `if (a && b && c)` with partial coverage | Truth table analysis; test relevant combinations |

**Example — Error Handling Gap:**

```java
// Code: catch block uncovered
try {
    return repository.find(id);
} catch (NotFoundException e) {  // ← Uncovered
    throw new UserNotFoundException(id);
}

// Test: Mock to trigger exception
@Test
void loadUser_whenNotFound_throwsUserNotFoundException() {
    when(repository.find("123")).thenThrow(new NotFoundException());
    assertThrows(UserNotFoundException.class, () -> service.loadUser("123"));
}
```

## Test Strategies per Gap Type

| Gap Type | Test Strategy |
|----------|---------------|
| Uncovered lines | Add test case exercising that path; parameterized test for variations |
| Uncovered branches | Test both true/false conditions; test all switch cases |
| Uncovered methods | Add happy path test; add error path tests; add null/invalid input tests |

## Best Practices

**Do:**
* Focus on high-priority gaps first
* Use coverage to guide test creation (not as goal)
* Test behavior, not implementation

**Don't:**
* Write tests just to hit coverage targets
* Test private methods directly (test through public API)
* Inflate coverage with trivial tests
