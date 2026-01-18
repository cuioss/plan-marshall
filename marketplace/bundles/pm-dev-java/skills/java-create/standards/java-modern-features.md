# Java Modern Features Standards

## Overview

CUI projects use modern Java features to write concise, readable, and maintainable code. Always use the most recent features from the version you compile against.

## Records for Data Carriers

Use records for simple immutable data carriers (Java 17+):

### Basic Record Usage

```java
// Simple immutable data carrier
public record User(String id, String name, String email) {}

// Usage
User user = new User("123", "John Doe", "john@example.com");
String name = user.name();  // Accessor methods

// Records automatically provide:
// - Constructor
// - Accessor methods (not getters!)
// - equals() and hashCode()
// - toString()
```

### Records with Validation

Add validation in compact constructor:

```java
public record TokenConfig(String issuer, int validitySeconds) {
    // Compact constructor for validation
    public TokenConfig {
        if (issuer == null || issuer.isBlank()) {
            throw new IllegalArgumentException("Issuer is required");
        }
        if (validitySeconds <= 0) {
            throw new IllegalArgumentException("Validity must be positive");
        }
    }
}

// Usage
TokenConfig config = new TokenConfig("https://auth.example.com", 3600);
```

### Records with Static Factory Methods

```java
public record ValidationResult(boolean valid, List<String> errors) {

    // Static factory for success case
    public static ValidationResult valid() {
        return new ValidationResult(true, List.of());
    }

    // Static factory for failure case
    public static ValidationResult invalid(String... errors) {
        return new ValidationResult(false, List.of(errors));
    }

    // Computed property
    public boolean hasErrors() {
        return !errors.isEmpty();
    }
}

// Usage
ValidationResult success = ValidationResult.valid();
ValidationResult failure = ValidationResult.invalid("Invalid signature", "Expired token");
```

### Records with Custom Methods

```java
public record Range(int start, int end) {

    // Validation in compact constructor
    public Range {
        if (start > end) {
            throw new IllegalArgumentException("Start must be <= end");
        }
    }

    // Custom methods
    public int length() {
        return end - start + 1;
    }

    public boolean contains(int value) {
        return value >= start && value <= end;
    }

    public Range extend(int amount) {
        return new Range(start, end + amount);
    }
}
```

### When to Use Records vs Lombok @Value

For comprehensive comparison of records vs Lombok @Value including decision criteria, see `pm-dev-java:java-lombok` skill.

**Migration from Lombok @Value to Records**:

```java
// Before: Lombok @Value
@Value
@Builder
public class UserDto {
    String id;
    String name;
    String email;
}

// After: Java Record with builder pattern
public record UserDto(String id, String name, String email) {
    // Optional: Add builder if needed
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String id;
        private String name;
        private String email;

        public Builder id(String id) { this.id = id; return this; }
        public Builder name(String name) { this.name = name; return this; }
        public Builder email(String email) { this.email = email; return this; }

        public UserDto build() {
            return new UserDto(id, name, email);
        }
    }
}
```

**Note**: Records are simpler but Lombok @Value + @Builder provides more features out-of-the-box. Choose based on project needs and Java version constraints.

## Switch Expressions

Use switch expressions instead of classic switch statements:

### Basic Switch Expression

```java
// ✅ Good - switch expression
String dayType(DayOfWeek day) {
    return switch (day) {
        case MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY -> "Weekday";
        case SATURDAY, SUNDAY -> "Weekend";
    };
}

// ❌ Old style - switch statement
String dayType(DayOfWeek day) {
    String result;
    switch (day) {
        case MONDAY:
        case TUESDAY:
        case WEDNESDAY:
        case THURSDAY:
        case FRIDAY:
            result = "Weekday";
            break;
        case SATURDAY:
        case SUNDAY:
            result = "Weekend";
            break;
        default:
            throw new IllegalArgumentException("Invalid day");
    }
    return result;
}
```

### Switch with Block

```java
String processToken(TokenType type, String token) {
    return switch (type) {
        case JWT -> {
            JwtToken jwt = parseJwt(token);
            yield jwt.getSubject();
        }
        case OAUTH2 -> {
            OAuth2Token oauth = parseOAuth2(token);
            yield oauth.getUserId();
        }
        case LEGACY -> parseLegacy(token);
    };
}
```

### Switch for Validation

```java
ValidationResult validate(Token token) {
    return switch (token.getType()) {
        case JWT -> jwtValidator.validate(token);
        case OAUTH2 -> oauth2Validator.validate(token);
        case LEGACY -> ValidationResult.invalid("Legacy tokens not supported");
    };
}
```

## Stream Processing

Use streams for complex data transformations:

### Basic Stream Operations

```java
// Filter and map
List<String> activeUserNames = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .sorted()
    .toList();

// Find first match
Optional<User> admin = users.stream()
    .filter(user -> user.hasRole("ADMIN"))
    .findFirst();

// Check conditions
boolean allActive = users.stream()
    .allMatch(User::isActive);

boolean anyAdmin = users.stream()
    .anyMatch(user -> user.hasRole("ADMIN"));
```

### Collectors

```java
// Collect to map
Map<String, User> usersById = users.stream()
    .collect(Collectors.toMap(User::getId, Function.identity()));

// Group by
Map<String, List<User>> usersByRole = users.stream()
    .collect(Collectors.groupingBy(User::getRole));

// Join strings
String userNames = users.stream()
    .map(User::getName)
    .collect(Collectors.joining(", "));

// Statistics
IntSummaryStatistics stats = users.stream()
    .mapToInt(User::getAge)
    .summaryStatistics();
```

### FlatMap for Nested Collections

```java
// Flatten nested collections
List<String> allPermissions = users.stream()
    .flatMap(user -> user.getRoles().stream())
    .flatMap(role -> role.getPermissions().stream())
    .distinct()
    .sorted()
    .toList();

// Flatten optional values
List<String> userEmails = users.stream()
    .map(User::getEmail)
    .flatMap(Optional::stream)  // Flatten Optional
    .toList();
```

### Stream Best Practices

```java
// ✅ Good - keep lambda expressions short and clear
users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();

// ✅ Good - extract complex logic to methods
users.stream()
    .filter(this::isEligibleForPromotion)
    .map(this::createPromotionOffer)
    .toList();

// ❌ Bad - complex lambda
users.stream()
    .filter(user -> {
        if (user.getAge() > 18 && user.isActive()) {
            return user.getRoles().contains("PREMIUM") ||
                   user.getRegistrationDate().isBefore(cutoffDate);
        }
        return false;
    })
    .toList();

// ✅ Good - avoid side effects in streams
List<String> names = users.stream()
    .map(User::getName)
    .toList();

// ❌ Bad - side effects in stream
users.stream()
    .forEach(user -> {
        user.incrementLoginCount();  // Modifying state
        log.info("User logged in: {}", user.getName());
    });
```

## Text Blocks

Use text blocks for multi-line strings (Java 15+):

```java
// ✅ Good - text block for JSON
String json = """
    {
        "userId": "%s",
        "email": "%s",
        "roles": ["USER", "ADMIN"]
    }
    """.formatted(userId, email);

// ✅ Good - text block for SQL
String sql = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
      AND u.created_at > ?
    ORDER BY u.name
    """;

// ✅ Good - text block for HTML
String html = """
    <html>
        <body>
            <h1>Welcome, %s!</h1>
            <p>Your account has been activated.</p>
        </body>
    </html>
    """.formatted(userName);
```

## Pattern Matching (Preview/Incubator)

### Pattern Matching for instanceof

```java
// ✅ Good - pattern matching (Java 16+)
if (obj instanceof String str) {
    return str.toUpperCase();
}

// Old style
if (obj instanceof String) {
    String str = (String) obj;
    return str.toUpperCase();
}

// Pattern matching with logical operators
if (obj instanceof String str && str.length() > 10) {
    return str.substring(0, 10);
}
```

### Pattern Matching in Switch (Preview)

```java
// Pattern matching for switch (preview feature)
String describe(Object obj) {
    return switch (obj) {
        case String str -> "String of length " + str.length();
        case Integer i -> "Integer: " + i;
        case null -> "null value";
        default -> "Unknown type: " + obj.getClass();
    };
}
```

## Sealed Classes (Java 17+)

Use sealed classes for restricted hierarchies:

```java
// Define sealed hierarchy
public sealed interface Token
    permits JwtToken, OAuth2Token, LegacyToken {

    ValidationResult validate();
    String getTokenId();
}

// Implementations must be permits
public final class JwtToken implements Token {
    @Override
    public ValidationResult validate() {
        // JWT validation
    }

    @Override
    public String getTokenId() {
        return extractClaim("jti");
    }
}

// Exhaustive switch with sealed types
ValidationResult validate(Token token) {
    return switch (token) {
        case JwtToken jwt -> jwtValidator.validate(jwt);
        case OAuth2Token oauth -> oauth2Validator.validate(oauth);
        case LegacyToken legacy -> ValidationResult.invalid("Not supported");
        // No default needed - compiler ensures exhaustiveness
    };
}
```

## Optional Enhancements

Modern Optional API usage:

```java
// Use orElseThrow for required values
User user = userRepository.findById(id)
    .orElseThrow(() -> new UserNotFoundException(id));

// Use ifPresentOrElse
userRepository.findById(id)
    .ifPresentOrElse(
        user -> log.info("Found user: {}", user.getName()),
        () -> log.warn("User not found: {}", id)
    );

// Use Optional.stream()
List<String> emails = users.stream()
    .map(User::getEmail)
    .flatMap(Optional::stream)
    .toList();

// Chain operations
String result = repository.findById(id)
    .map(User::getProfile)
    .map(Profile::getDisplayName)
    .orElse("Unknown User");
```

## Modern Collection Factories

Use factory methods for immutable collections:

```java
// Immutable lists
List<String> roles = List.of("USER", "ADMIN");

// Immutable sets
Set<String> permissions = Set.of("READ", "WRITE", "DELETE");

// Immutable maps
Map<String, Integer> limits = Map.of(
    "USER", 100,
    "ADMIN", 1000
);

// Larger maps
Map<String, String> config = Map.ofEntries(
    Map.entry("issuer", "https://auth.example.com"),
    Map.entry("audience", "my-api"),
    Map.entry("algorithm", "RS256")
);

// Copy collections to immutable
List<User> users = List.copyOf(mutableUsers);
```

## Local Variable Type Inference (var)

Use `var` for improved readability when type is obvious:

```java
// ✅ Good - type is obvious from right side
var users = userRepository.findAll();
var config = TokenConfig.builder().build();
var result = validator.validate(token);

// ❌ Avoid - type is not obvious
var data = process();  // What type is data?

// ❌ Avoid - for primitives (use explicit type)
var count = 0;  // Use int count = 0;

// ✅ Good - with diamond operator
var userList = new ArrayList<User>();
var configMap = new HashMap<String, String>();
```

## Quality Checklist

- [ ] Records used for simple immutable data carriers
- [ ] Switch expressions used instead of statements
- [ ] Streams used for complex data transformations
- [ ] No side effects in stream operations
- [ ] Text blocks used for multi-line strings
- [ ] Pattern matching used where available
- [ ] Modern collection factories used
- [ ] var used appropriately (type is obvious)
- [ ] Sealed classes considered for restricted hierarchies
- [ ] Optional API used effectively
