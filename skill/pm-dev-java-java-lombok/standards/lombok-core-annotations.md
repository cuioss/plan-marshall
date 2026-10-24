# Lombok Core Annotations

Standards for `@Delegate`, `@Builder`, `@Value`, `@Data`, and `@UtilityClass`.

## @Delegate - Delegation Over Inheritance

Use `@Delegate` for delegation patterns instead of inheritance:

```java
// CORRECT - delegation with Lombok
public class CachedTokenValidator implements TokenValidator {
    @Delegate
    private final TokenValidator delegate;
    private final Cache<String, ValidationResult> cache;

    public CachedTokenValidator(TokenValidator delegate) {
        this.delegate = delegate;
        this.cache = CacheBuilder.newBuilder().build();
    }

    @Override
    public ValidationResult validate(String token) {
        return cache.get(token, () -> delegate.validate(token));
    }
}

// WRONG - inheritance creates tight coupling
public class CachedTokenValidator extends BaseTokenValidator { }
```

**Use @Delegate for**: Interface composition, wrapping implementations, cross-cutting concerns (caching, logging, metrics), avoiding inheritance hierarchies.

## @Builder - Complex Object Construction

Use `@Builder` for records or classes with multiple optional parameters. **Always use @Builder for types with 4+ constructor parameters** — direct constructor calls with many positional arguments are error-prone and hard to read.

### Records with @Builder

Place `@Builder` on the record's compact constructor for reliable builder generation:

```java
public record TokenConfig(
    String issuer,
    String audience,
    Duration validity,
    int clockSkewSeconds,
    @Singular Set<String> requiredClaims
) {
    @Builder
    TokenConfig {}

    // Partial manual builder to provide defaults (records don't support @Builder.Default)
    public static class TokenConfigBuilder {
        private Duration validity = Duration.ofHours(1);
        private int clockSkewSeconds = 30;
    }
}

// Usage
TokenConfig config = TokenConfig.builder()
    .issuer("https://auth.example.com")
    .audience("my-api")
    .requiredClaim("sub")    // @Singular generates add method
    .requiredClaim("exp")
    .build();
```

**Important limitations with records:**
- `@Builder.Default` does not work on record components — provide defaults via a partial manual builder class instead (see example above)
- `toBuilder = true` is not supported on records
- `@Singular` works normally on collection-type components

### Classes with @Builder

For cases requiring `@Builder.Default` or `toBuilder`, use a class:

```java
@Builder(toBuilder = true)
public class ApiResponse {
    private final String userId;
    private final String status;

    @Builder.Default
    private final int retryCount = 3;

    @Singular
    private final List<String> messages;
}

// Copy with modifications via toBuilder()
ApiResponse modified = response.toBuilder()
    .status("updated")
    .build();
```

**Always add @Singular to collection-type fields** in @Builder classes — it generates convenient single-element add methods and ensures the collection is built as an immutable copy.

### When to Use Records vs Classes with @Builder

- **Records + @Builder**: Default choice for immutable types with many parameters. Accept the limitation that defaults require a partial manual builder class.
- **Classes + @Builder**: Use when you need `@Builder.Default`, `toBuilder`, or Jackson annotations that don't work well on record components.

## @Value - Replaced by Records

`@Value` is superseded by Java records for immutable value objects. Use records instead:

```java
// PREFER - Java record
public record ValidationResult(boolean valid, List<String> errors, Instant validatedAt) {}

// AVOID - Lombok @Value (use only if stuck on Java < 16)
@Value
public class ValidationResult {
    boolean valid;
    List<String> errors;
    Instant validatedAt;
}
```

Records provide the same guarantees as `@Value` (immutability, equals/hashCode, toString, accessors) as a language feature, with the additional benefit of pattern matching support.

## @Data - Mutable Objects (Use Sparingly)

```java
@Data
public class UserPreferences {
    private String theme;
    private Locale locale;
    private int pageSize;
}
```

**Prefer records for immutability**. Use @Data only when mutability is genuinely required.

## @UtilityClass - Static Method Classes

```java
@UtilityClass
public class TokenUtils {
    public static String extractTokenId(String token) {
        // Implementation
    }

    public static boolean isExpired(String token) {
        // Implementation
    }
}
```

Makes class final, constructor private, all methods static.
