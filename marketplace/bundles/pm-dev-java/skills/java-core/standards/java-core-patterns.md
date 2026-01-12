# Java Core Patterns and Principles

## Overview

This document defines core Java development principles and patterns for CUI projects, ensuring consistent, maintainable, and high-quality code across all Java projects.

## Key Principles

1. **Code Readability**: Write code that is easy to read and understand
2. **Maintainability**: Design code that is easy to modify and extend
3. **Consistency**: Follow consistent patterns across the codebase
4. **Testability**: Write code that is easy to test
5. **Performance**: Consider performance implications in design decisions

## Code Organization

### Package Structure

* Use reverse domain name notation for package names
* Organize packages by feature rather than layer
* Keep package cohesion high
* Group related classes in the same package

**Example**:
```java
de.cuioss.portal.authentication     // Authentication feature
de.cuioss.portal.configuration      // Configuration feature
de.cuioss.portal.user.management    // User management feature
```

### Class Structure

* Follow the Single Responsibility Principle
* Keep classes small and focused
* Use proper access modifiers (public, protected, private)
* Place most restrictive modifier first

**Good example**:
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

* Use meaningful method names
* Follow the Command-Query Separation principle
* Limit method parameters (3 or fewer preferred, use parameter objects for 4+)
* For method complexity and length guidelines, see "Method Complexity" section below

**Command-Query Separation**:
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

When methods require many parameters, consider creating parameter objects to group related parameters:

**Guidelines**:
* Only introduce parameter objects when replacing **3 or more parameters**
* Parameter objects should represent cohesive concepts where parameters naturally belong together
* Avoid creating parameter objects for just 2 parameters unless they represent a clear domain concept
* Use records for simple parameter objects in Java 17+

```java
// ✅ Good: Multiple related parameters grouped into a cohesive object
public record ValidationRequest(
    String tokenId,
    Set<String> expectedScopes,
    Duration maxAge,
    String issuer
) {}

public boolean validate(ValidationRequest request) {
    // Clear, organized parameters
}

// ❌ Avoid: Parameter object for just 2 unrelated parameters
// Instead, use the parameters directly:
public void log(String message, CuiLogger logger) {
    // Two parameters are fine
}

// ❌ Bad: Too many parameters
public boolean validate(String tokenId, Set<String> scopes,
                       Duration maxAge, String issuer, boolean strict) {
    // Hard to read and maintain
}
```

## Coding Practices

### Naming Conventions

* Use meaningful and descriptive names
* Follow standard Java naming conventions:
  - Classes: PascalCase (e.g., `TokenValidator`)
  - Methods/variables: camelCase (e.g., `validateToken`)
  - Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`)
  - Packages: lowercase (e.g., `de.cuioss.portal`)
* Avoid abbreviations unless widely understood
* Use intention-revealing names

**Good examples**:
```java
// Good - clear, descriptive names
public class UserAuthenticationService {
    private static final int MAX_LOGIN_ATTEMPTS = 3;

    public AuthenticationResult authenticateUser(String username, String password) {
        // Implementation
    }
}

// Bad - unclear abbreviations
public class UsrAuthSvc {
    private static final int MAX_ATT = 3;

    public AuthRes authUsr(String un, String pw) {
        // What does this do?
    }
}
```

### Exception Handling

**CRITICAL: NEVER catch or throw generic exceptions.**

* **NEVER catch**: `Exception`, `RuntimeException`, `Error`, or `Throwable`
* **NEVER throw**: `Exception`, `RuntimeException`, `Error`, or `Throwable`
* **ALWAYS use specific exception types** - both when catching and throwing
* Use checked exceptions for recoverable conditions
* Use unchecked exceptions for programming errors
* Include meaningful error messages
* Preserve exception causes with exception chaining

```java
// ✅ Good exception handling - specific exception types
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

// ❌ Bad - catches generic Exception
public Configuration loadConfig(Path configPath) {
    try {
        return parser.parse(Files.readString(configPath));
    } catch (Exception e) {  // NEVER - too broad
        return null;  // Loses error information
    }
}

// ❌ Bad - throws generic Exception
public void processData(String data) throws Exception {  // NEVER
    // Should throw specific exception type
}

// ❌ Bad - catches Throwable
public void riskyOperation() {
    try {
        performOperation();
    } catch (Throwable t) {  // NEVER - catches even Errors
        log.error("Operation failed", t);
    }
}

// ❌ Bad - throws RuntimeException
public void validateInput(String input) {
    if (input == null) {
        throw new RuntimeException("Invalid input");  // NEVER - use specific type
    }
}

// ✅ Good - throws specific exception type
public void validateInput(String input) {
    if (input == null) {
        throw new IllegalArgumentException("Input must not be null");
    }
}

// ❌ Bad - swallows exception
public Configuration loadConfig(Path configPath) {
    try {
        return parser.parse(Files.readString(configPath));
    } catch (IOException e) {
        // Silent failure - no logging, no re-throw
        return Configuration.empty();
    }
}
```

**Rationale:**
* Generic exceptions hide the actual problem and prevent proper error handling
* Catching `Error` or `Throwable` can mask serious JVM issues (OutOfMemoryError, StackOverflowError)
* Specific exception types enable targeted recovery strategies
* SonarQube rule violations: S1181 (catch Throwable), S112 (throw generic exceptions)

## Best Practices

### Immutability

* Prefer immutable objects
* Use final fields where appropriate
* Consider using records for data carriers
* Use immutable collections

```java
// Good - immutable class
public final class TokenConfig {
    private final String issuer;
    private final Duration validity;
    private final Set<String> allowedScopes;

    public TokenConfig(String issuer, Duration validity, Set<String> scopes) {
        this.issuer = issuer;
        this.validity = validity;
        // Defensive copy for immutability
        this.allowedScopes = Set.copyOf(scopes);
    }

    // Only getters, no setters
    public String getIssuer() { return issuer; }
    public Duration getValidity() { return validity; }
    public Set<String> getAllowedScopes() { return allowedScopes; }
}
```

### Collection Usage

* Use interface types for declarations
* Prefer immutable collections
* Use appropriate collection types for use cases
* Use `List.of()`, `Set.of()`, `Map.of()` for immutable collections

```java
// ✅ Good - interface type, immutable
public List<User> getActiveUsers() {
    return List.copyOf(activeUsers);
}

// ✅ Good - appropriate collection type
public Set<String> getUniqueRoles() {
    return Set.copyOf(roles);  // Set for uniqueness
}

// ❌ Bad - concrete type in declaration
public ArrayList<User> getActiveUsers() {
    return activeUsers;  // Exposes implementation
}
```

### Design Preferences

* Prefer delegation over inheritance
* Use composition for code reuse
* Prefer imports over fully qualified class names
* Keep related code together

```java
// ✅ Good - delegation (use Lombok @Delegate)
public class CachedTokenValidator implements TokenValidator {
    @Delegate
    private final TokenValidator delegate;
    private final Cache<String, ValidationResult> cache;

    public CachedTokenValidator(TokenValidator delegate) {
        this.delegate = delegate;
        this.cache = CacheBuilder.newBuilder().build();
    }
}

// ❌ Avoid - deep inheritance hierarchies
public abstract class BaseValidator extends AbstractValidator
        extends CoreValidator implements Validator {
    // Complex inheritance chain
}
```

## Code Quality

### Readability

* Use whitespace effectively
* Break long lines appropriately
* Group related code together
* Add blank lines between logical sections

### Method Complexity

* Keep methods short and focused (under 50 lines preferred, 100 lines maximum)
* Keep cyclomatic complexity low (prefer <15, maximum 20)
* Extract complex conditions into well-named methods
* Use early returns to reduce nesting

```java
// ✅ Good - low complexity, clear flow
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

// ❌ Bad - high nesting, complex
public ValidationResult validate(String token) {
    if (token != null && !token.isEmpty()) {
        if (hasValidFormat(token)) {
            if (hasValidSignature(token)) {
                return ValidationResult.valid();
            } else {
                return ValidationResult.invalid("Invalid signature");
            }
        } else {
            return ValidationResult.invalid("Invalid format");
        }
    } else {
        return ValidationResult.invalid("Token is required");
    }
}
```

### Comments

* Write self-documenting code
* Use comments to explain WHY, not WHAT
* Keep comments up to date with code
* Use JavaDoc for public APIs

```java
// ✅ Good - explains why
// We use a 30-second clock skew to handle time differences
// between servers in distributed environments
private static final Duration CLOCK_SKEW = Duration.ofSeconds(30);

// ❌ Bad - states the obvious
// This is a duration of 30 seconds
private static final Duration CLOCK_SKEW = Duration.ofSeconds(30);
```

## Anti-Patterns to Avoid

### Magic Numbers

```java
// ❌ Bad - magic numbers
if (user.getAge() >= 18) {
    // What does 18 represent?
}

// ✅ Good - named constant
private static final int MINIMUM_AGE = 18;

if (user.getAge() >= MINIMUM_AGE) {
    // Clear intent
}
```

### Primitive Obsession

```java
// ❌ Bad - primitive obsession
public void sendEmail(String from, String to, String subject, String body) {
    // Too many string parameters
}

// ✅ Good - domain objects
public void sendEmail(EmailMessage message) {
    // Clear, type-safe
}

public record EmailMessage(
    EmailAddress from,
    EmailAddress to,
    String subject,
    String body
) {}
```

### God Classes

```java
// ❌ Bad - does everything
public class UserManager {
    public void authenticate() {}
    public void authorize() {}
    public void sendEmail() {}
    public void validateInput() {}
    public void logActivity() {}
    // ... 50 more methods
}

// ✅ Good - single responsibility
public class UserAuthenticator {
    public AuthenticationResult authenticate(Credentials credentials) {
        // Focused on authentication only
    }
}
```

## Documentation Requirements

* Follow JavaDoc standards for all public APIs
* Document non-obvious behavior
* Document assumptions and preconditions
* For detailed JavaDoc requirements, see `pm-dev-java:javadoc` skill
* For CUI logging standards, see `pm-dev-java-cui:cui-logging` skill

## Quality Checklist

- [ ] Classes follow Single Responsibility Principle
- [ ] Methods are short and focused (< 50 lines preferred, < 100 lines maximum)
- [ ] Method parameters limited (≤ 3 preferred, use parameter objects for 4+)
- [ ] Meaningful names used throughout (PascalCase classes, camelCase methods, UPPER_SNAKE_CASE constants)
- [ ] Exception handling is appropriate (specific exceptions, meaningful messages, preserved causes)
- [ ] Immutability used where possible (final fields, immutable collections)
- [ ] No magic numbers or strings (use named constants)
- [ ] Code is self-documenting (clear names, minimal comments explaining why not what)
- [ ] Public APIs are documented (JavaDoc with parameters, returns, throws)
- [ ] Design patterns applied appropriately (delegation over inheritance, composition)
- [ ] No god classes or deep inheritance (prefer flat, focused classes)
