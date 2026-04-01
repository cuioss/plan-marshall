# JavaDoc Core Standards

For general documentation principles (what/when/how to document, clarity, completeness, anti-patterns), see `plan-marshall:dev-general-code-quality`. This document covers JavaDoc-specific tag syntax, formatting, and Java-specific patterns.

## Java-Specific Documentation Requirements

In addition to general requirements in `plan-marshall:dev-general-code-quality`:

* Package-level documentation in `package-info.java`
* Annotation types and their elements
* All enum constants and their purpose

## Basic Tag Usage

### @param Tag

Document each parameter with its purpose and any validation rules:

```java
/**
 * Creates a new user account with the specified credentials.
 *
 * @param username the unique username (3-20 characters, alphanumeric)
 * @param email the user's email address (must be valid email format)
 * @param password the raw password (min 8 characters, will be hashed)
 */
public void createUser(String username, String email, String password) {
    // Implementation
}
```

### @return Tag

Document what the return value represents and any guarantees:

```java
/**
 * Retrieves the user by their unique identifier.
 *
 * @param userId the unique user identifier
 * @return the user if found, or Optional.empty() if not found
 */
public Optional<User> findById(String userId) {
    // Implementation
}
```

### @throws Tag

Document both checked and significant unchecked exceptions:

```java
/**
 * Parses the configuration file and loads application settings.
 *
 * @param configFile the configuration file path
 * @return loaded configuration settings
 * @throws FileNotFoundException if the config file does not exist
 * @throws ConfigurationException if the file format is invalid
 * @throws IllegalArgumentException if configFile is null or empty
 */
public Configuration loadConfig(Path configFile)
        throws FileNotFoundException, ConfigurationException {
    // Implementation
}
```

### @since Tag

Document when the API was introduced:

```java
/**
 * Validates OAuth2 bearer tokens according to RFC 6750.
 *
 * @param token the bearer token to validate
 * @return validation result
 * @since 1.2.0
 */
public ValidationResult validateBearerToken(String token) {
    // Implementation
}
```

### @deprecated Tag

Provide clear migration path when deprecating:

```java
/**
 * Validates a token using legacy validation rules.
 *
 * @param token the token to validate
 * @return true if valid, false otherwise
 * @deprecated since 2.0.0, use {@link #validate(String)} instead which
 *             returns detailed validation results and supports modern
 *             token formats. This method will be removed in 3.0.0.
 */
@Deprecated
public boolean validateLegacy(String token) {
    // Implementation
}
```

## Tag Order

Always use this standard tag order:

1. `@param` (in parameter order)
2. `@return`
3. `@throws` (in alphabetical order by exception name)
4. `@see`
5. `@since`
6. `@deprecated`
7. `@author` (if applicable, usually package-level only)
8. `@version` (if applicable, usually package-level only)

**Example**:
```java
/**
 * Authenticates a user with the given credentials.
 *
 * @param username the username to authenticate
 * @param password the password to verify
 * @return authenticated user session
 * @throws AuthenticationException if credentials are invalid
 * @throws IllegalArgumentException if username or password is null
 * @see #logout(Session)
 * @since 1.0.0
 */
public Session authenticate(String username, String password)
        throws AuthenticationException {
    // Implementation
}
```

## Thread-Safety Documentation

For classes/methods with thread-safety implications:

```java
/**
 * Thread-safe cache for user sessions. All methods are synchronized
 * and safe for concurrent access from multiple threads.
 *
 * @since 1.0.0
 */
public class SessionCache {
    // Implementation
}

/**
 * Returns the current session count. This method is thread-safe but the
 * returned value may be stale if other threads are concurrently adding
 * or removing sessions.
 *
 * @return approximate number of active sessions
 */
public int getSessionCount() {
    // Implementation
}
```

## Null Handling Documentation

Document null behavior clearly:

```java
/**
 * Finds a user by their unique identifier.
 *
 * @param userId the user identifier, must not be null
 * @return the user if found, never null (use Optional.empty() for not found)
 * @throws NullPointerException if userId is null (via Objects.requireNonNull)
 */
public Optional<User> findUser(String userId) {
    Objects.requireNonNull(userId, "userId must not be null");
    // Implementation
}
```

## Java-Specific Quality Rules

Beyond general documentation requirements (see `plan-marshall:dev-general-code-quality`):

- Proper tag order followed (see Tag Order section above)
- Thread-safety documented where relevant
- Null handling documented with `@NonNull`/`@Nullable` annotations
- Migration paths provided for all `@deprecated` APIs
- JavaDoc HTML generation succeeds without warnings
