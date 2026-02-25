# Java Core Patterns and Principles

## Code Organization

### Package Structure

* Use reverse domain name notation for package names
* Organize packages by feature rather than layer
* Keep package cohesion high

```java
de.cuioss.portal.authentication     // Authentication feature
de.cuioss.portal.configuration      // Configuration feature
de.cuioss.portal.user.management    // User management feature
```

### Class Structure

* Follow the Single Responsibility Principle
* Keep classes small and focused
* Use proper access modifiers (most restrictive first)

```java
public class TokenValidator {
    private final TokenConfig config;
    private final SignatureVerifier verifier;

    public TokenValidator(TokenConfig config) {
        this.config = config;
        this.verifier = new SignatureVerifier(config.getPublicKey());
    }

    public ValidationResult validate(String token) {
        // Single, focused responsibility
    }
}
```

### Method Design

* Follow Command-Query Separation
* Limit parameters (2 or fewer preferred, use parameter objects for 3+)
* Keep methods short (under 50 lines preferred, 100 max)
* Keep cyclomatic complexity low (prefer <15, max 20)
* Use early returns to reduce nesting

```java
// Query - returns value, no side effects
public boolean isValid() {
    return status == Status.VALID;
}

// Command - modifies state, returns void
public void markAsInvalid() {
    this.status = Status.INVALID;
}
```

### Parameter Objects

Only introduce parameter objects when replacing **3 or more parameters**. Use records for simple parameter objects.

```java
// Good: Multiple related parameters grouped
public record ValidationRequest(
    String tokenId,
    Set<String> expectedScopes,
    Duration maxAge,
    String issuer
) {}

public boolean validate(ValidationRequest request) {
    // Clear, organized parameters
}

// Bad: Too many loose parameters
public boolean validate(String tokenId, Set<String> scopes,
                       Duration maxAge, String issuer, boolean strict) {
    // Hard to read and maintain
}
```

## Exception Handling

Never catch or throw generic exceptions (`Exception`, `RuntimeException`, `Error`, `Throwable`). Always use specific exception types.

```java
// Good - specific exception types
public Configuration loadConfig(Path configPath)
        throws ConfigurationException {
    try {
        return parser.parse(Files.readString(configPath));
    } catch (IOException e) {
        throw new ConfigurationException(
            "Failed to read config file: " + configPath, e);
    } catch (ParseException e) {
        throw new ConfigurationException(
            "Invalid configuration format in: " + configPath, e);
    }
}

// Bad - catches generic Exception
public Configuration loadConfig(Path configPath) {
    try {
        return parser.parse(Files.readString(configPath));
    } catch (Exception e) {  // Too broad
        return null;  // Loses error information
    }
}
```

**Rules:**
- Use checked exceptions for recoverable conditions
- Use unchecked exceptions for programming errors
- Include meaningful error messages
- Preserve exception causes with chaining
- SonarQube rules: S1181 (catch Throwable), S112 (throw generic exceptions)

## Immutability

* Prefer immutable objects with final fields
* Use records for data carriers
* Use `List.of()`, `Set.of()`, `Map.of()` for immutable collections
* Return defensive copies: `Set.copyOf(scopes)`

```java
public final class TokenConfig {
    private final String issuer;
    private final Duration validity;
    private final Set<String> allowedScopes;

    public TokenConfig(String issuer, Duration validity, Set<String> scopes) {
        this.issuer = issuer;
        this.validity = validity;
        this.allowedScopes = Set.copyOf(scopes);
    }

    // Only getters, no setters
}
```

## Collection Usage

* Use interface types for declarations (`List`, not `ArrayList`)
* Prefer immutable collections
* Return `List.copyOf()` / `Set.copyOf()` from getters

```java
// Good - interface type, immutable
public List<User> getActiveUsers() {
    return List.copyOf(activeUsers);
}

// Bad - concrete type, exposes implementation
public ArrayList<User> getActiveUsers() {
    return activeUsers;
}
```

## Design Preferences

* Prefer delegation over inheritance (use Lombok `@Delegate`)
* Use composition for code reuse
* Avoid deep inheritance hierarchies

```java
// Good - delegation
public class CachedTokenValidator implements TokenValidator {
    @Delegate
    private final TokenValidator delegate;
    private final Cache<String, ValidationResult> cache;
}

// Avoid - deep inheritance
public abstract class BaseValidator extends AbstractValidator
        extends CoreValidator implements Validator { }
```

## Anti-Patterns

### Magic Numbers

```java
// Bad
if (user.getAge() >= 18) { }

// Good - named constant
private static final int MINIMUM_AGE = 18;
if (user.getAge() >= MINIMUM_AGE) { }
```

### Primitive Obsession

```java
// Bad - too many string parameters
public void sendEmail(String from, String to, String subject, String body) { }

// Good - domain objects
public void sendEmail(EmailMessage message) { }
```

## Method Complexity

Extract complex conditions into well-named methods. Use early returns:

```java
// Good - low complexity, clear flow
public ValidationResult validate(String token) {
    if (token == null || token.isEmpty()) {
        return ValidationResult.invalid("Token is required");
    }
    if (!hasValidFormat(token)) {
        return ValidationResult.invalid("Invalid token format");
    }
    if (!hasValidSignature(token)) {
        return ValidationResult.invalid("Invalid signature");
    }
    return ValidationResult.valid();
}
```

## Comments

* Write self-documenting code
* Use comments to explain WHY, not WHAT
* Use JavaDoc for public APIs (see `pm-dev-java:javadoc` skill)

```java
// Good - explains why
// 30-second clock skew handles time differences between servers
private static final Duration CLOCK_SKEW = Duration.ofSeconds(30);

// Bad - states the obvious
// This is a duration of 30 seconds
private static final Duration CLOCK_SKEW = Duration.ofSeconds(30);
```
