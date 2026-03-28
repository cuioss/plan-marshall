# Null Safety Implementation Patterns

Patterns for writing null-safe code, handling nullable parameters, collections, testing, and migration.

## Null-Safe Implementation with @NullMarked

```java
// With @NullMarked at package level, everything is non-null by default
public class TokenValidator {

    // Field is non-null by default
    private final TokenConfig config;

    // Parameter is non-null by default
    public TokenValidator(TokenConfig config) {
        // No null check needed if caller respects contract
        // But defensive programming is still acceptable:
        this.config = Objects.requireNonNull(config, "config must not be null");
    }

    // Parameter and return are non-null by default
    public ValidationResult validate(String token) {
        Objects.requireNonNull(token, "token must not be null");
        // Implementation must return non-null
        return new ValidationResult(/*...*/);
    }

    // Mark nullable parameters explicitly
    public String processWithDefault(@Nullable String input) {
        return input != null ? input.toUpperCase() : "DEFAULT";
    }

    // Use Optional instead of @Nullable returns
    public Optional<UserInfo> extractUserInfo(String token) {
        return parseToken(token)
            .map(this::extractUser);
    }
}
```

## Without @NullMarked (Legacy Code)

For code without package-level `@NullMarked`, use explicit `@NonNull` on every field, parameter, and return type. This is verbose — prefer migrating to `@NullMarked` at the package level.

## Nullable Parameters

Use `@Nullable` sparingly for parameters that genuinely accept null:

```java
// Acceptable - null has clear meaning (use default)
public String format(@Nullable Locale locale) {
    Locale effectiveLocale = locale != null ? locale : Locale.getDefault();
    return formatter.format(effectiveLocale);
}

// Better - overload methods instead of nullable parameters
public String format() {
    return format(Locale.getDefault());
}

public String format(Locale locale) {
    return formatter.format(locale);
}
```

Prefer method overloads over `@Nullable` parameters — they make the API clearer and avoid null checks in the implementation.

## Collections and Generics

Apply null-safety to collection types:

```java
// With @NullMarked, all elements are non-null
public List<User> getActiveUsers() {
    // Returns non-null list of non-null User objects
    return users.stream()
        .filter(User::isActive)
        .toList();
}

// Use @Nullable for nullable elements
public List<@Nullable String> getOptionalValues() {
    // List is non-null, but elements can be null
    return Arrays.asList("value1", null, "value3");
}
```

### Generic Type Parameters

```java
// Non-null type parameter (default with @NullMarked)
public <T> List<T> filterNonNull(List<@Nullable T> input) {
    return input.stream()
        .filter(Objects::nonNull)
        .toList();
}

// Map with nullable values
public Map<String, @Nullable Object> getProperties() {
    // Keys are non-null, values may be null
    return properties;
}
```

## Unit Testing

Test that non-nullable methods never return null under any valid input conditions:

```java
@Test
void shouldNeverReturnNull() {
    // With @NullMarked, non-nullable methods must never return null
    assertNotNull(service.processToken("valid"));
    assertNotNull(service.processToken(""));

    // Non-nullable methods should handle edge cases without returning null
    assertNotNull(service.processToken("edge-case"));
}

@Test
void shouldUseOptionalForMissingValues() {
    // Use Optional.empty() instead of null returns
    assertTrue(service.findUser("unknown").isEmpty());
    assertTrue(service.findUser("existing").isPresent());
}

@Test
void shouldRejectNullParameters() {
    // Non-nullable parameters should be validated
    assertThrows(NullPointerException.class,
        () -> service.processToken(null));
}

@Test
void shouldAcceptNullableParameters() {
    // @Nullable parameters should handle null gracefully
    assertNotNull(service.format(null));
    assertEquals("DEFAULT", service.processWithDefault(null));
}
```

## Migration Strategy

### For New Code

1. Add `@NullMarked` to `package-info.java`
2. Write code assuming non-null by default
3. Use `@Nullable` only where null is explicitly allowed
4. Use `Optional<T>` for "no result" return types
5. Validate with unit tests

### For Existing Code

1. Add `@NullMarked` to package
2. Review all public APIs
3. Add `@Nullable` where null is currently accepted/returned
4. Refactor nullable returns to Optional where appropriate
5. Add null checks with `Objects.requireNonNull()` at API boundaries
6. Update tests to verify null-safety contracts

### Migration Checklist

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Add `package-info.java` with `@NullMarked` | Compiles without errors |
| 2 | Annotate nullable parameters with `@Nullable` | No new compiler warnings |
| 3 | Replace `@Nullable` returns with `Optional` | All callers updated |
| 4 | Add `Objects.requireNonNull()` at boundaries | Tests pass |
| 5 | Add null-safety tests | Coverage includes null paths |
