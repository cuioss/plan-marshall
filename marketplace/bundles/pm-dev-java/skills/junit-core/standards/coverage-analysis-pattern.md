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

## Comparing Coverage Before and After a Change

A claim that a change did not lower coverage needs a comparison that could have shown a loss. Two things make a comparison unable to:

**Accumulated coverage data.** The coverage agent appends to its data file; it does not replace it. A build that reuses the file of an earlier build reports the union of both, so a line the change stopped covering still reads as covered. Delete the data file — or run a clean build — before each of the two runs being compared.

**Run-to-run variance.** Some branches are covered by chance: one that depends on the iteration order of an unordered collection, or on which of two threads arrives first. On an unchanged tree such a class shows different numbers on different runs, in both directions. Before attributing a difference to the change:

1. Run the unchanged tree several times on clean data and note which classes vary.
2. Compare per class, not by the module total, which hides one class's loss behind another's gain.
3. Treat a difference in a class that varies on its own as unattributed, and say so.

A branch that is covered by chance is itself a finding: no test fixes the condition that reaches it. Report it as a test-quality gap rather than leaving it as noise.

### What an Unchanged Coverage Figure Does Not Show

Coverage records which code ran, not what was asserted about it. Two tests that execute the same lines produce the same coverage whether they assert the whole result, one field of it, or nothing. Removing the stricter of the two leaves every per-class figure identical.

An unchanged comparison therefore supports "no code stopped being exercised". It does not support "nothing stopped being checked". When a test is removed or merged, the assertions are compared by reading both tests — see `testing-junit-core.md`, "Removing a Redundant Test".

## Best Practices

**Do:**
* Focus on high-priority gaps first
* Use coverage to guide test creation (not as goal)
* Test behavior, not implementation

**Don't:**
* Write tests just to hit coverage targets
* Test private methods directly (test through public API)
* Inflate coverage with trivial tests
