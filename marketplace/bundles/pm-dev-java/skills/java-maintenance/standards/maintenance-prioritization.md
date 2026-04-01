# Maintenance Prioritization Framework

For general prioritization principles (high/medium/low priority categories, decision tree), see `plan-marshall:dev-general-code-quality` refactoring-triggers.md. This document covers Java-specific maintenance priorities.

## Java-Specific High Priority

### API Contract Issues (Java-Specific)

- Missing `@NonNull` / `@Nullable` annotations on public APIs (see `pm-dev-java:java-null-safety`)
- Inconsistent null safety patterns (`@NullMarked` package-level config)
- Missing or wrong `@throws` declarations in JavaDoc
- Broken serialization contracts (`serialVersionUID` mismatch, missing `Serializable`)

### Concurrency Safety

- Mutable shared state without synchronization
- Non-thread-safe collections used in concurrent contexts
- Missing `volatile` on double-checked locking fields
- `ThreadLocal` usage where `ScopedValue` is appropriate (Java 21+)

**Example — unsafe shared state**:
```java
// HIGH PRIORITY - shared mutable state without synchronization
public class MetricsCollector {
    private final Map<String, Long> counters = new HashMap<>();  // Not thread-safe

    public void increment(String key) {
        counters.merge(key, 1L, Long::sum);  // Race condition
    }
}

// FIXED - use concurrent collection
public class MetricsCollector {
    private final Map<String, LongAdder> counters = new ConcurrentHashMap<>();

    public void increment(String key) {
        counters.computeIfAbsent(key, k -> new LongAdder()).increment();
    }
}
```

## Java-Specific Medium Priority

### Modern Java Adoption

| Legacy Pattern | Modern Replacement | Reference |
|---------------|-------------------|-----------|
| Switch with `break` | Switch expression | `java-17-features.md` |
| Manual data class | Java record | `java-17-features.md` |
| Anonymous `Runnable` | Lambda expression | `java-17-features.md` |
| `instanceof` + cast | Pattern matching | `java-21-features.md` |
| `ThreadLocal` | `ScopedValue` | `java-21-features.md` |
| Verbose string concat | Text blocks | `java-17-features.md` |

**Example — modernization**:
```java
// MEDIUM PRIORITY - legacy switch
String label;
switch (status) {
    case ACTIVE:
        label = "Active";
        break;
    case INACTIVE:
        label = "Inactive";
        break;
    default:
        label = "Unknown";
        break;
}

// MODERNIZED - switch expression
String label = switch (status) {
    case ACTIVE -> "Active";
    case INACTIVE -> "Inactive";
    default -> "Unknown";
};
```

### Code Cleanup

- Unused private fields and methods
- Dead code elimination (with user approval)
- Commented-out code removal
- Redundant type declarations (use `var` where type is obvious from RHS)

## Java-Specific Low Priority

### Style Consistency

- Import ordering (IDE-manageable)
- Whitespace and formatting (IDE-manageable)
- Inconsistent use of `final` on local variables
- Comment style variations (line vs block)

## Workflow Integration

After identifying violations:

1. **Categorize** by violation type (general via `plan-marshall:dev-general-code-quality`, Java-specific here)
2. **Assign priority** using this framework and general prioritization
3. **Execute** systematically within each priority band
4. **Verify** using compliance-checklist.md

## Related Standards

- refactoring-triggers.md - Java-specific detection criteria
- compliance-checklist.md - Verification after fixes applied
- `plan-marshall:dev-general-code-quality` - General prioritization and refactoring triggers
