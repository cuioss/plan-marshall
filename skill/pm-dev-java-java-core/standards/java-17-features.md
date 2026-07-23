# Java 17 Features and Patterns

Features stable by Java 17 (Java 9-17). Use these in all Java 17+ projects.

## Records (Java 16)

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

## Switch Expressions (Java 14)

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

## Pattern Matching for instanceof (Java 16)

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

## Sealed Classes (Java 17)

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

## Text Blocks (Java 15)

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

## Collection Factories (Java 9)

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

## Local Variable Type Inference (Java 10)

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

### orElse vs orElseGet

`orElse()` evaluates eagerly; `orElseGet()` evaluates lazily:

```java
// Bad - database call happens EVERY time, even when value exists
String name = user.getName().orElse(database.lookupDefaultName(userId));

// Good - lambda only invoked when Optional is empty
String name = user.getName().orElseGet(() -> database.lookupDefaultName(userId));

// OK - cheap constant, orElse is fine
String value = optional.orElse("");
```

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

### Streams vs Simple Loops

Streams add overhead (lambda objects, Optional wrappers, infrastructure). On hot paths, prefer simple loops:

```java
// Bad on hot path - scattered allocations, cache unfriendly
BigDecimal totalAmount(List<Order> orders) {
    return orders.stream()
        .filter(Order::isActive)
        .map(o -> Optional.ofNullable(o.getAmount())
            .orElse(BigDecimal.ZERO))
        .reduce(BigDecimal.ZERO, BigDecimal::add);
}

// Good on hot path - predictable access, cache friendly
BigDecimal totalAmount(List<Order> orders) {
    BigDecimal sum = BigDecimal.ZERO;
    for (int i = 0; i < orders.size(); i++) {
        Order order = orders.get(i);
        if (!order.isActive()) continue;
        BigDecimal amount = order.getAmount();
        if (amount != null) sum = sum.add(amount);
    }
    return sum;
}
```

**Use streams when**: code runs once per request, readability matters more than microseconds.
**Use simple loops when**: code runs per item in large collections, method appears in profiler hot spots.

### Avoid Optional.ofNullable in Streams

```java
// Bad - creates Optional for every element
items.stream()
    .map(item -> Optional.ofNullable(item.getValue()).orElse(BigDecimal.ZERO))
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// Good - filter nulls directly
items.stream()
    .map(Item::getValue)
    .filter(Objects::nonNull)
    .reduce(BigDecimal.ZERO, BigDecimal::add);
```

### Avoid Stream Creation in Loops

```java
// Bad - creates stream on each iteration (O(n*m) stream creations)
for (Order order : orders) {
    Optional<Product> product = products.stream()
        .filter(p -> p.getId().equals(order.getProductId()))
        .findFirst();
}

// Good - build lookup map once, O(1) lookups
Map<String, Product> productMap = products.stream()
    .collect(Collectors.toMap(Product::getId, Function.identity()));
for (Order order : orders) {
    Product product = productMap.get(order.getProductId());
}
```

### Parallel Streams

Use only for CPU-intensive operations on large datasets. Never for I/O-bound or small collections:

```java
// Bad - parallel for small collection or I/O
smallList.parallelStream().map(this::fetchFromNetwork).toList();

// Good - parallel for CPU-intensive with large data
largeDataset.parallelStream().map(this::complexCalculation).toList();
```
