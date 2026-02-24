# Java Modern Features Standards

Use modern Java features (21+) to write concise, readable code. Always use the most recent features from the version you compile against.

## Records for Data Carriers

Use records for simple immutable data carriers. Records automatically provide constructor, accessor methods, `equals()`, `hashCode()`, and `toString()`.

```java
// Simple record
public record User(String id, String name, String email) {}

// Record with validation (compact constructor)
public record TokenConfig(String issuer, int validitySeconds) {
    public TokenConfig {
        if (issuer == null || issuer.isBlank()) {
            throw new IllegalArgumentException("Issuer is required");
        }
        if (validitySeconds <= 0) {
            throw new IllegalArgumentException("Validity must be positive");
        }
    }
}

// Record with static factories and computed properties
public record ValidationResult(boolean valid, List<String> errors) {

    public static ValidationResult valid() {
        return new ValidationResult(true, List.of());
    }

    public static ValidationResult invalid(String... errors) {
        return new ValidationResult(false, List.of(errors));
    }

    public boolean hasErrors() {
        return !errors.isEmpty();
    }
}
```

### Records vs Lombok @Value

For comprehensive comparison, see `pm-dev-java:java-lombok` skill. Records are simpler; Lombok `@Value` + `@Builder` provides more features out-of-the-box.

## Switch Expressions

Use switch expressions instead of classic switch statements:

```java
// Good - switch expression
String dayType(DayOfWeek day) {
    return switch (day) {
        case MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY -> "Weekday";
        case SATURDAY, SUNDAY -> "Weekend";
    };
}

// Switch with block and yield
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

## Pattern Matching

### Pattern Matching for instanceof

```java
// Good - pattern matching
if (obj instanceof String str) {
    return str.toUpperCase();
}

// With logical operators
if (obj instanceof String str && str.length() > 10) {
    return str.substring(0, 10);
}
```

### Pattern Matching in Switch

```java
String describe(Object obj) {
    return switch (obj) {
        case String str -> "String of length " + str.length();
        case Integer i -> "Integer: " + i;
        case null -> "null value";
        default -> "Unknown type: " + obj.getClass();
    };
}
```

### Record Patterns

Deconstruct records directly in pattern matching — avoids accessor calls:

```java
public record Point(int x, int y) {}
public record Line(Point start, Point end) {}

// Deconstruct record in switch
String describe(Object obj) {
    return switch (obj) {
        case Point(int x, int y) -> "Point at (%d, %d)".formatted(x, y);
        case Line(Point(int x1, int y1), Point(int x2, int y2)) ->
            "Line from (%d,%d) to (%d,%d)".formatted(x1, y1, x2, y2);
        default -> "Unknown shape";
    };
}

// Deconstruct in instanceof
if (obj instanceof Point(int x, int y)) {
    return Math.sqrt(x * x + y * y);
}
```

## Sealed Classes

Use sealed classes for restricted hierarchies with exhaustive switch:

```java
public sealed interface Token
    permits JwtToken, OAuth2Token, LegacyToken {
    ValidationResult validate();
    String getTokenId();
}

public final class JwtToken implements Token { /* ... */ }

// Exhaustive switch - no default needed
ValidationResult validate(Token token) {
    return switch (token) {
        case JwtToken jwt -> jwtValidator.validate(jwt);
        case OAuth2Token oauth -> oauth2Validator.validate(oauth);
        case LegacyToken legacy -> ValidationResult.invalid("Not supported");
    };
}
```

## Sequenced Collections

`SequencedCollection`, `SequencedSet`, and `SequencedMap` provide uniform access to first/last elements and reverse views:

```java
// First/last element access (replaces verbose workarounds)
SequencedCollection<String> names = new LinkedHashSet<>(List.of("Alice", "Bob", "Charlie"));
String first = names.getFirst();   // "Alice"
String last = names.getLast();     // "Charlie"

// Reverse view
SequencedCollection<String> reversed = names.reversed();

// SequencedMap — ordered map with first/last entry access
SequencedMap<String, Integer> scores = new LinkedHashMap<>();
scores.put("Alice", 95);
scores.put("Bob", 87);
Map.Entry<String, Integer> firstEntry = scores.firstEntry();
Map.Entry<String, Integer> lastEntry = scores.lastEntry();
```

**Interface hierarchy**: `SequencedCollection` extends `Collection`, `SequencedSet` extends `SequencedCollection` and `Set`, `SequencedMap` extends `Map`. Existing classes (`LinkedHashSet`, `LinkedHashMap`, `TreeSet`, `TreeMap`, `ArrayList`) implement the appropriate sequenced interface.

## Stream Processing

### Basic Operations

```java
// Filter, map, sort
List<String> activeUserNames = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .sorted()
    .toList();

// Find first match
Optional<User> admin = users.stream()
    .filter(user -> user.hasRole("ADMIN"))
    .findFirst();

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
```

### FlatMap for Nested Collections

```java
List<String> allPermissions = users.stream()
    .flatMap(user -> user.getRoles().stream())
    .flatMap(role -> role.getPermissions().stream())
    .distinct()
    .sorted()
    .toList();

// Flatten Optional values
List<String> userEmails = users.stream()
    .map(User::getEmail)
    .flatMap(Optional::stream)
    .toList();
```

### Stream Best Practices

```java
// Good - short lambdas, method references
users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();

// Good - extract complex logic to methods
users.stream()
    .filter(this::isEligibleForPromotion)
    .map(this::createPromotionOffer)
    .toList();

// Bad - complex inline lambda (extract to method instead)
users.stream()
    .filter(user -> {
        if (user.getAge() > 18 && user.isActive()) {
            return user.getRoles().contains("PREMIUM") ||
                   user.getRegistrationDate().isBefore(cutoffDate);
        }
        return false;
    })
    .toList();
```

Avoid side effects in streams — do not modify state inside `map`/`forEach`.

## Text Blocks

Use text blocks for multi-line strings:

```java
String json = """
    {
        "userId": "%s",
        "email": "%s",
        "roles": ["USER", "ADMIN"]
    }
    """.formatted(userId, email);

String sql = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
      AND u.created_at > ?
    ORDER BY u.name
    """;
```

## Optional Usage

```java
// orElseThrow for required values
User user = userRepository.findById(id)
    .orElseThrow(() -> new UserNotFoundException(id));

// ifPresentOrElse
userRepository.findById(id)
    .ifPresentOrElse(
        user -> log.info("Found user: {}", user.getName()),
        () -> log.warn("User not found: {}", id)
    );

// Chain operations
String result = repository.findById(id)
    .map(User::getProfile)
    .map(Profile::getDisplayName)
    .orElse("Unknown User");

// Optional.stream() for flatMap
List<String> emails = users.stream()
    .map(User::getEmail)
    .flatMap(Optional::stream)
    .toList();
```

## Collection Factories

```java
List<String> roles = List.of("USER", "ADMIN");
Set<String> permissions = Set.of("READ", "WRITE", "DELETE");
Map<String, Integer> limits = Map.of("USER", 100, "ADMIN", 1000);

// Larger maps
Map<String, String> config = Map.ofEntries(
    Map.entry("issuer", "https://auth.example.com"),
    Map.entry("audience", "my-api"),
    Map.entry("algorithm", "RS256")
);

// Copy to immutable
List<User> users = List.copyOf(mutableUsers);
```

## Local Variable Type Inference (var)

Use `var` when type is obvious from the right side:

```java
// Good - type obvious
var users = userRepository.findAll();
var config = TokenConfig.builder().build();
var result = validator.validate(token);

// Avoid - type not obvious
var data = process();  // What type?

// Avoid - for primitives
var count = 0;  // Use int count = 0;
```
