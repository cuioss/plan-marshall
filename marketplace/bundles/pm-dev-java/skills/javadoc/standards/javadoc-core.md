# JavaDoc Core Standards

## Purpose

This document defines core JavaDoc documentation standards for CUI projects, ensuring consistency, completeness, and maintainability across the codebase.

## Mandatory Documentation Requirements

### What Must Be Documented

* Every public and protected class/interface
* Every public and protected method
* All public and protected fields
* All enum constants and their purpose
* Package-level documentation in package-info.java
* Annotation types and their elements

### What Should NOT Be Documented

* Private methods (unless complex or non-obvious)
* Trivial fields (e.g., serialVersionUID, LOGGER)
* Obvious getters/setters without business logic
* Standard fields that follow common patterns
* Methods that simply delegate without logic

(See "Documentation Anti-Patterns" section below for examples of what NOT to document)

## Core JavaDoc Principles

### 1. Clarity and Purpose

* Start with a clear purpose statement
* Explain WHAT the code does and WHY it exists
* Avoid stating the obvious or repeating the method name
* Focus on behavior, not implementation details

**Good Example**:
```java
/**
 * Validates the JWT token signature and expiration time against the configured
 * issuer and clock skew tolerance.
 *
 * @param token the JWT token to validate
 * @return validation result containing status and any error messages
 * @throws IllegalArgumentException if token is null or empty
 */
public ValidationResult validate(String token) {
    // Implementation
}
```

**Bad Example (Stating the Obvious)**:
```java
/**
 * Validates a token.
 *
 * @param token the token
 * @return the result
 */
public ValidationResult validate(String token) {
    // Implementation
}
```

### 2. Completeness

* Document all parameters with meaningful descriptions
* Document return values with what they represent
* Document all checked exceptions and when they occur
* Document unchecked exceptions if they represent business rules
* Include @since tags for public APIs
* Add @deprecated with migration path for deprecated elements

### 3. Consistency

* Use consistent terminology across the codebase
* Follow standard tag order (see Tag Order section)
* Use consistent formatting and structure
* Apply consistent documentation style

### 4. Maintainability

* Keep documentation synchronized with code
* Update JavaDoc when changing method signatures or behavior
* Remove outdated or incorrect documentation
* Document assumptions and preconditions

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

## Documentation Maintenance

### When to Update JavaDoc

* When changing method signatures (parameters, return type)
* When modifying method behavior or semantics
* When adding new public APIs
* When deprecating existing APIs
* When fixing bugs that affect documented behavior
* During code reviews

### Keeping Documentation Synchronized

* Review JavaDoc during every code change
* Run JavaDoc generation to catch errors
* Include JavaDoc updates in the same commit as code changes
* Check for broken {@link} references

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

## Documentation Anti-Patterns

### 1. Stating the Obvious

```java
// ❌ Bad - obvious documentation
/**
 * Sets the name.
 * @param name the name to set
 */
public void setName(String name) {
    this.name = name;
}

// ✅ Good - document business rules if any
/**
 * Sets the user's display name. The name is trimmed and validated
 * to ensure it meets minimum length requirements.
 *
 * @param name the display name (minimum 2 characters after trimming)
 * @throws IllegalArgumentException if name is too short
 */
public void setName(String name) {
    // Implementation with validation
}
```

### 2. Outdated Documentation

```java
// ❌ Bad - documentation doesn't match implementation
/**
 * Validates the token format.
 *
 * @param token the token
 * @return true if valid
 */
public ValidationResult validate(String token) {
    // Method now returns ValidationResult, not boolean!
}
```

### 3. Vague Descriptions

```java
// ❌ Bad - vague, uninformative
/**
 * Processes the data.
 *
 * @param data the data
 * @return the result
 */
public Result process(Data data) {
    // What kind of processing? What result?
}

// ✅ Good - specific and informative
/**
 * Enriches user data by adding geolocation information based on IP address
 * and validating email deliverability.
 *
 * @param userData the user data to enrich
 * @return enriched user data with geolocation and email status
 * @throws EnrichmentException if external services are unavailable
 */
public EnrichedUserData enrich(UserData userData) throws EnrichmentException {
    // Implementation
}
```

### 4. Documenting Implementation Instead of Contract

```java
// ❌ Bad - exposes implementation details
/**
 * Uses a HashMap to store the users and iterates through the entrySet
 * to find the matching user by email.
 *
 * @param email the email
 * @return the user or null
 */
public User findByEmail(String email) {
    // Don't document HOW, document WHAT
}

// ✅ Good - documents the contract
/**
 * Retrieves the first user with the specified email address.
 *
 * @param email the email address to search for
 * @return the user if found, or Optional.empty() if not found
 */
public Optional<User> findByEmail(String email) {
    // Implementation can change without breaking documentation
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

## Quality Checklist

Before completing JavaDoc documentation:

- [ ] All public/protected APIs documented
- [ ] All parameters described with validation rules
- [ ] Return values documented with guarantees
- [ ] Exceptions documented with conditions
- [ ] No "stating the obvious" documentation
- [ ] No outdated documentation
- [ ] Proper tag order followed
- [ ] Thread-safety documented where relevant
- [ ] Null handling documented
- [ ] Migration paths provided for deprecated APIs
- [ ] JavaDoc HTML generation succeeds without warnings
