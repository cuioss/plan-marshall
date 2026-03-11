# Java Core Patterns and Principles

For general code organization principles (SRP, CQS, complexity thresholds, error handling), see `plan-marshall:dev-general-code-quality`. This document covers Java-specific patterns, idioms, and conventions.

## Package Structure

* Use reverse domain name notation for package names
* Organize packages by feature rather than layer

```java
com.example.authentication          // Authentication feature
com.example.configuration           // Configuration feature
com.example.usermanagement          // User management feature
```

## Parameter Objects

Use records for simple parameter objects (3+ parameters):

```java
public record ValidationRequest(
    String tokenId,
    Set<String> expectedScopes,
    Duration maxAge,
    String issuer
) {}

public boolean validate(ValidationRequest request) {
    // Clear, organized parameters
}
```

## Java Exception Handling

Java-specific exception rules beyond the general principles in `plan-marshall:dev-general-code-quality`:

* Use checked exceptions for recoverable conditions
* Use unchecked exceptions for programming errors
* Never catch `Throwable` or `Error` (SonarQube S1181)
* Never throw generic `Exception` or `RuntimeException` (SonarQube S112)
* Preserve exception causes with chaining

```java
// Good - specific exception types with cause chaining
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
```

## Immutability

* Prefer immutable objects with `final` fields
* Use records for data carriers
* Use `List.of()`, `Set.of()`, `Map.of()` for immutable collections
* Return defensive copies: `Set.copyOf(scopes)`, `List.copyOf(items)`

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
```

## Comments

* Use JavaDoc for public APIs (see `pm-dev-java:javadoc` skill)
* See `plan-marshall:dev-general-code-quality` for general comment principles
