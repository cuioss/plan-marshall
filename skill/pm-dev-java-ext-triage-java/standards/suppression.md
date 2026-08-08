# Java Suppression Syntax

How to suppress various types of findings in Java code.

## @SuppressWarnings Annotation

The primary mechanism for suppressing warnings in Java.

### Scope Levels

| Level | Syntax | Use When |
|-------|--------|----------|
| Method | `@SuppressWarnings("...")` on method | Issue is method-specific |
| Class | `@SuppressWarnings("...")` on class | Issue affects multiple members |
| Statement | `@SuppressWarnings("...")` on local variable | Single statement issue |
| Package | `package-info.java` with annotation | Package-wide suppression |

### Common Suppression Values

| Value | Suppresses | Example |
|-------|------------|---------|
| `"deprecation"` | Deprecated API usage | Using deprecated method |
| `"unchecked"` | Unchecked type operations | Generic casts, raw types |
| `"rawtypes"` | Raw type usage | Using `List` instead of `List<T>` |
| `"null"` | Null-related warnings | Potential null dereference |
| `"unused"` | Unused elements | Unused private methods |
| `"serial"` | Serialization issues | Missing serialVersionUID |
| `"all"` | All warnings | **Use sparingly** |

### Sonar Rule Suppression

```java
// Suppress specific Sonar rule
@SuppressWarnings("java:S1135")  // TODO comments
public void processLegacyCode() {
    // TODO: Refactor this after migration
}

// Suppress with justification (recommended)
@SuppressWarnings("java:S3776")  // Cognitive complexity - legacy code, tracked in JIRA-123
public void complexLegacyMethod() {
    // Complex but tested legacy code
}
```

### Multiple Suppressions

```java
@SuppressWarnings({"deprecation", "unchecked"})
public void legacyInterop() {
    // Uses deprecated API and requires unchecked casts
}
```

## NOSONAR Comment

Line-level suppression for Sonar issues.

```java
String password = "hardcoded"; // NOSONAR - test data only, not production code
```

**Rules**:
- Use only when annotation is not possible
- Always include justification after `NOSONAR`
- Avoid for BLOCKER/CRITICAL issues

## JSpecify Null Annotations

For null-related suppressions, prefer JSpecify annotations over `@SuppressWarnings("null")`:

```java
import org.jspecify.annotations.Nullable;

public void process(@Nullable String input) {
    if (input != null) {
        // Now safe to use input
    }
}
```

## Sonar-Specific Annotations

For more targeted Sonar control:

```java
// Suppress specific issue at method level
@SuppressWarnings("java:S2095")  // Resources should be closed
public void processStream() {
    // Stream is closed by caller
}

// Suppress security hotspot (requires justification)
@SuppressWarnings("java:S5445")  // Insecure random - for non-security use
public int generateDisplayId() {
    return new Random().nextInt(1000);
}
```

## Best Practices

### Always Include Justification

```java
// Good - explains why suppression is appropriate
@SuppressWarnings("unchecked")  // Safe cast - type verified by caller, see Javadoc
public <T> T getCachedValue(String key) {
    return (T) cache.get(key);
}

// Bad - no explanation
@SuppressWarnings("unchecked")
public <T> T getCachedValue(String key) {
    return (T) cache.get(key);
}
```

### Reference Issue Tracker for Deferred Fixes

```java
@SuppressWarnings("java:S3776")  // JIRA-456: Reduce complexity in v2.0 refactor
public void complexMethod() {
    // ...
}
```

### Scope Minimally

```java
// Good - suppression scoped to specific statement
public void process() {
    @SuppressWarnings("unchecked")
    List<String> items = (List<String>) getData();
    // Rest of method is not suppressed
}

// Less ideal - suppresses entire method
@SuppressWarnings("unchecked")
public void process() {
    List<String> items = (List<String>) getData();
    // All unchecked warnings in method are suppressed
}
```

## IDE-Specific Suppressions

### IntelliJ IDEA

```java
// Suppress IntelliJ inspection
@SuppressWarnings("InspectionName")

// Common IntelliJ suppressions
@SuppressWarnings("ConstantConditions")  // Constant value always true/false
@SuppressWarnings("NullableProblems")    // Null-related issues
```

### Eclipse

```java
// Eclipse-specific suppressions (also work in IntelliJ)
@SuppressWarnings("restriction")  // Access restriction
```

## When NOT to Suppress

- BLOCKER severity issues (fix instead)
- CRITICAL vulnerabilities (fix instead)
- Issues that can be fixed with minimal effort
- Issues in new code (only suppress in legacy)
- Issues without clear justification
