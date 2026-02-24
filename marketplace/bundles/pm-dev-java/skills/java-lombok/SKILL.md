---
name: java-lombok
description: Lombok patterns including @Delegate, @Builder, @Value, @UtilityClass for reducing boilerplate
user-invocable: false
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Java Lombok Skill

Lombok standards for reducing boilerplate code while maintaining code quality and testability.

## Prerequisites

```xml
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <scope>provided</scope>
</dependency>
```

## Required Imports

```java
// Lombok Core
import lombok.Builder;
import lombok.Value;
import lombok.Data;
import lombok.Getter;
import lombok.Setter;

// Lombok Advanced
import lombok.Delegate;
import lombok.Singular;
import lombok.experimental.UtilityClass;
import lombok.Builder.Default;
```

## Core Annotations

### @Delegate - Delegation Over Inheritance

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

### @Builder - Complex Object Construction

Use `@Builder` for classes with multiple optional parameters:

```java
@Value
@Builder(toBuilder = true)
public class TokenConfig {
    String issuer;
    String audience;

    @Builder.Default
    Duration validity = Duration.ofHours(1);

    @Builder.Default
    int clockSkewSeconds = 30;

    @Singular
    Set<String> requiredClaims;
}

// Usage
TokenConfig config = TokenConfig.builder()
    .issuer("https://auth.example.com")
    .audience("my-api")
    .requiredClaim("sub")    // @Singular generates add method
    .requiredClaim("exp")
    .build();

// Copy with modifications via toBuilder()
TokenConfig modified = config.toBuilder()
    .validity(Duration.ofHours(2))
    .build();
```

**Use @Builder for**: Classes with 3+ parameters, optional parameters, immutable configuration objects, DTOs with many fields.

### @Value - Immutable Objects

Use `@Value` for immutable value objects and DTOs:

```java
@Value
public class ValidationResult {
    boolean valid;
    List<String> errors;
    Instant validatedAt;
}

// Usage
ValidationResult result = new ValidationResult(true, List.of(), Instant.now());
boolean isValid = result.isValid();  // Getter
```

`@Value` generates: all-args constructor, getters (no setters), equals/hashCode, toString, all fields private final.

**Use @Value for**: Immutable DTOs, value objects, API request/response objects, configuration data.

### @Data - Mutable Objects (Use Sparingly)

```java
@Data
public class UserPreferences {
    private String theme;
    private Locale locale;
    private int pageSize;
}
```

**Prefer @Value or records for immutability**. Use @Data only when mutability is genuinely required.

### @UtilityClass - Static Method Classes

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

## Records vs Lombok @Value

| Criteria | Use Records | Use Lombok @Value |
|----------|-------------|-------------------|
| Java version | Java 21+ (baseline) | Java 11+ |
| Builder pattern | Not built-in | @Value + @Builder |
| Collection builders | Not available | @Singular |
| Pattern matching | Java 21+ | Not available |
| Project context | Minimal dependencies | Already using Lombok |
| Customization | Limited | More flexible |

```java
// Simple case - prefer records
public record User(String id, String name, String email) {}

// Complex case - use Lombok
@Value
@Builder
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiResponse {
    @JsonProperty("user_id")
    String userId;
    String status;
    @Singular
    List<String> messages;
}
```

**Migration guidance**: See `pm-dev-java:java-core` skill for Lombok to records migration.

## Combining Annotations

```java
@Value
@Builder
public class SearchCriteria {
    String query;

    @Builder.Default
    int maxResults = 100;

    @Singular
    Set<String> categories;

    LocalDate startDate;
    LocalDate endDate;
}

// Usage - only specify what differs from defaults
SearchCriteria criteria = SearchCriteria.builder()
    .query("example")
    .category("tech")
    .category("java")
    .build();
```

## Common Pitfalls

| Pitfall | Wrong | Correct |
|---------|-------|---------|
| Overusing @Data | `@Data` for immutable objects | Use `@Value` |
| Missing defaults | Builder without `@Builder.Default` | Add defaults for optional fields |
| No toBuilder | Immutable without copy method | `@Builder(toBuilder = true)` |
| Inheritance | `extends BaseClass` | `@Delegate` with composition |

## Related Skills

- `pm-dev-java:java-core` - Core Java patterns, records migration
- `pm-dev-java:java-null-safety` - Null safety with Lombok
