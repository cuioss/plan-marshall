# JavaDoc Method and Field Documentation Standards

## Overview

This document defines standards for documenting methods, fields, constructors, and special method patterns in CUI Java projects.

## Method Documentation

### Public and Protected Methods

Every public and protected method must be documented:

```java
/**
 * Authenticates a user with the given credentials and returns a session token.
 *
 * <p>This method validates the username and password against the user database,
 * applies password hashing, and creates a new session if authentication succeeds.
 *
 * @param username the username to authenticate (3-20 characters, alphanumeric)
 * @param password the raw password to verify (minimum 8 characters)
 * @return authenticated session token with 24-hour validity
 * @throws AuthenticationException if credentials are invalid or user is locked
 * @throws IllegalArgumentException if username or password is null or empty
 * @see #logout(String)
 * @since 1.0.0
 */
public String authenticate(String username, String password)
        throws AuthenticationException {
    // Implementation
}
```

### Required Elements

* **Purpose**: What the method does and why
* **@param**: Each parameter with validation rules and constraints
* **@return**: What the return value represents and any guarantees
* **@throws**: All exceptions (checked and significant unchecked) with conditions
* **@see**: Related methods or classes
* **@since**: Version when introduced (for public APIs)

### Parameter Documentation

Document parameters with their purpose, constraints, and validation rules:

```java
/**
 * Creates a new user account with the specified details.
 *
 * @param username the unique username (3-20 characters, alphanumeric, case-insensitive)
 * @param email the user's email address (must be valid format, will be normalized)
 * @param age the user's age (must be 18 or older)
 * @param roles the roles to assign (must not be null or empty, duplicates removed)
 * @throws IllegalArgumentException if any parameter validation fails
 * @throws DuplicateUserException if username or email already exists
 */
public void createUser(String username, String email, int age, Set<Role> roles)
        throws DuplicateUserException {
    // Implementation
}
```

### Return Value Documentation

Document what the return value represents and any guarantees:

```java
/**
 * Retrieves all active users from the database.
 *
 * @return list of active users, never null but may be empty if no active users exist.
 *         Users are ordered by registration date (newest first).
 */
public List<User> getActiveUsers() {
    // Implementation
}

/**
 * Finds a user by their unique identifier.
 *
 * @param userId the user identifier
 * @return the user if found, or Optional.empty() if not found or user is deleted
 */
public Optional<User> findById(String userId) {
    // Implementation
}

/**
 * Checks if a user with the given email exists.
 *
 * @param email the email address to check
 * @return true if a user with this email exists and is active, false otherwise
 */
public boolean existsByEmail(String email) {
    // Implementation
}
```

### Exception Documentation

Document all checked exceptions and significant unchecked exceptions:

```java
/**
 * Loads and parses the configuration file.
 *
 * @param configPath the path to the configuration file
 * @return parsed configuration
 * @throws FileNotFoundException if the config file does not exist
 * @throws ConfigurationException if the file format is invalid or required fields are missing
 * @throws IllegalArgumentException if configPath is null
 * @throws SecurityException if the application lacks permission to read the file
 */
public Configuration loadConfig(Path configPath)
        throws FileNotFoundException, ConfigurationException {
    // Implementation
}
```

### Private Methods

Document private methods only when necessary:

```java
// ✅ Good - complex private method deserves documentation
/**
 * Applies rate limiting logic using token bucket algorithm.
 *
 * @implSpec This method is not thread-safe and must be called within a
 *           synchronized block.
 * @param userId the user identifier
 * @return true if request is allowed, false if rate limit exceeded
 */
private boolean checkRateLimit(String userId) {
    // Complex implementation
}

// ✅ Good - trivial private method, no documentation needed
private boolean isEmpty(String str) {
    return str == null || str.trim().isEmpty();
}
```

### Overridden Methods

Document overridden methods when they add behavior:

```java
/**
 * {@inheritDoc}
 *
 * <p>This implementation caches validation results for 5 minutes to improve
 * performance. Cached results are invalidated when the token expires or
 * configuration changes.
 */
@Override
public ValidationResult validate(String token) {
    // Implementation with caching
}
```

**For simple overrides without additional behavior**:
```java
@Override
public String toString() {
    return "User{id=" + id + ", name=" + name + "}";
}
// No documentation needed for straightforward toString/equals/hashCode
```

## Field Documentation

### Public Fields

Document all public fields (though prefer private fields with accessors):

```java
/**
 * Maximum number of login attempts before account lockout.
 * This value can be configured via system properties.
 */
public static final int MAX_LOGIN_ATTEMPTS = 3;

/**
 * Default session timeout in seconds (24 hours).
 */
public static final long DEFAULT_SESSION_TIMEOUT = 86400;
```

### Protected Fields

Document protected fields that subclasses may use:

```java
/**
 * The token validator used by this authenticator.
 * Subclasses can override {@link #createValidator()} to provide
 * custom validation logic.
 */
protected TokenValidator validator;
```

### Private Fields

Generally do not document private fields unless they have complex invariants:

```java
// ❌ Bad - obvious, don't document
/** The user's name */
private String name;

/** Logger for this class */
private static final Logger LOGGER = LoggerFactory.getLogger(MyClass.class);

// ✅ Good - complex invariant worth documenting
/**
 * Cache of active sessions, keyed by session ID.
 * Invariant: All sessions in this map must have expiration time > current time.
 * Cleanup is performed by background thread every 60 seconds.
 */
private final Map<String, Session> activeSessions = new ConcurrentHashMap<>();
```

### Fields That Should NOT Be Documented

* Standard logger fields
* serialVersionUID
* Trivial fields with obvious purposes
* Fields that are adequately explained by their type and name

## Constructor Documentation

### Public Constructors

```java
/**
 * Creates a new JWT token validator with the specified configuration.
 *
 * @param issuer the expected token issuer URL (must be valid URL format)
 * @param publicKey the RSA public key for signature verification (must not be null)
 * @param clockSkewSeconds allowed clock skew in seconds (must be non-negative, typically 30-300)
 * @throws IllegalArgumentException if issuer is invalid or publicKey is null
 * @throws KeyException if the public key format is invalid
 */
public JwtTokenValidator(String issuer, PublicKey publicKey, int clockSkewSeconds)
        throws KeyException {
    // Implementation
}
```

### Constructor Anti-Patterns

```java
// ❌ Bad - stating the obvious
/**
 * Constructor.
 *
 * @param name the name
 * @param age the age
 */
public User(String name, int age) {
    this.name = name;
    this.age = age;
}

// ✅ Better - document validation or business rules
/**
 * Creates a new user with the specified details.
 *
 * @param name the user's display name (minimum 2 characters, trimmed)
 * @param age the user's age (must be 18 or older)
 * @throws IllegalArgumentException if name is too short or age is under 18
 */
public User(String name, int age) {
    // Implementation with validation
}
```

## Special Method Patterns

### Builder Methods

Document builder pattern methods:

```java
/**
 * Sets the token issuer URL.
 *
 * @param issuer the issuer URL (must be valid HTTPS URL)
 * @return this builder for method chaining
 * @throws IllegalArgumentException if issuer is null or not a valid HTTPS URL
 */
public Builder issuer(String issuer) {
    // Validation and assignment
    return this;
}

/**
 * Builds and returns a configured JWT token validator.
 *
 * @return a new JwtTokenValidator instance with the configured settings
 * @throws IllegalStateException if required settings (issuer, publicKey) are not set
 */
public JwtTokenValidator build() {
    // Validation and construction
}
```

### Factory Methods

Document factory methods with emphasis on what's created:

```java
/**
 * Creates a new token validator for the specified token type.
 *
 * <p>This factory method instantiates the appropriate validator implementation
 * based on the token type (JWT, OAuth2, etc.).
 *
 * @param tokenType the type of tokens to validate
 * @param config the validator configuration
 * @return a new validator instance configured for the specified token type, never null
 * @throws UnsupportedTokenTypeException if the token type is not supported
 * @see TokenType
 */
public static TokenValidator create(TokenType tokenType, Config config)
        throws UnsupportedTokenTypeException {
    // Implementation
}
```

### Fluent API Methods

Document fluent API patterns clearly:

```java
/**
 * Adds a required claim to the validation rules.
 *
 * <p>The validator will reject tokens that do not contain this claim.
 * This method can be called multiple times to require multiple claims.
 *
 * @param claimName the name of the required claim
 * @return this validator for method chaining
 * @throws IllegalArgumentException if claimName is null or empty
 */
public JwtTokenValidator requireClaim(String claimName) {
    // Implementation
    return this;
}

/**
 * Executes the validation with the configured rules.
 *
 * <p>This is a terminal operation that completes the fluent API chain
 * and performs the actual validation.
 *
 * @return validation result containing status and any errors, never null
 */
public ValidationResult validate() {
    // Implementation
}
```

### Generic Methods

Document type parameters and constraints:

```java
/**
 * Converts a token string into a typed token object.
 *
 * @param <T> the type of token to parse, must extend {@link Token}
 * @param tokenString the token string to parse
 * @param tokenClass the class object representing T
 * @return parsed token instance of type T, never null
 * @throws ParseException if the token string cannot be parsed into type T
 * @throws IllegalArgumentException if tokenString or tokenClass is null
 */
public <T extends Token> T parse(String tokenString, Class<T> tokenClass)
        throws ParseException {
    // Implementation
}
```

### Varargs Methods

Document varargs parameters clearly:

```java
/**
 * Validates that the token contains at least one of the specified roles.
 *
 * @param requiredRoles the roles to check, at least one must be present.
 *                      Pass multiple roles to allow any of them (OR logic).
 *                      Must not be null or empty.
 * @return true if token contains at least one of the specified roles
 * @throws IllegalArgumentException if requiredRoles is null or empty
 */
public boolean hasAnyRole(String... requiredRoles) {
    // Implementation
}
```

## Method Documentation Anti-Patterns

For general JavaDoc anti-patterns including "stating the obvious" and redundant documentation, see the **Documentation Anti-Patterns** section in `javadoc-core.md`.

Method-specific anti-patterns to avoid:

### 1. Vague @param Descriptions

```java
// ❌ Bad - vague
/**
 * Validates a token.
 * @param token the token
 * @return the result
 */

// ✅ Good - specific
/**
 * Validates the JWT token signature and expiration.
 * @param token the JWT token string in compact serialization format
 * @return validation result indicating success or specific failure reasons
 */
```

### 2. Missing Exception Conditions

```java
// ❌ Bad - doesn't explain when exception is thrown
/**
 * Parses the token.
 * @param token the token string
 * @return parsed token
 * @throws TokenException if something goes wrong
 */

// ✅ Good - specific conditions
/**
 * Parses the token string into a structured token object.
 * @param token the token string
 * @return parsed token with validated claims
 * @throws TokenException if the token format is invalid, signature verification
 *         fails, or required claims are missing
 */
```

## Complex Method Documentation Example

```java
/**
 * Validates a JWT token and extracts user information from its claims.
 *
 * <p>This method performs the following validations:
 * <ul>
 *   <li>Signature verification using configured public key</li>
 *   <li>Expiration time check with clock skew tolerance</li>
 *   <li>Issuer verification against expected issuer</li>
 *   <li>Audience claim validation</li>
 * </ul>
 *
 * <p>If validation succeeds, the method extracts user information from
 * standard and custom claims according to the mapping configuration.
 *
 * <p><b>Thread Safety:</b> This method is thread-safe and can be called
 * concurrently from multiple threads.
 *
 * @param token the JWT token in compact serialization format (header.payload.signature),
 *              must not be null or empty
 * @param expectedAudience the expected audience claim value, or null to skip audience validation
 * @return user information extracted from token claims, never null
 * @throws TokenValidationException if any validation check fails
 * @throws IllegalArgumentException if token is null or empty
 * @throws IllegalStateException if the validator is not properly initialized
 * @see UserInfo
 * @see #configure(ValidatorConfig)
 * @since 1.2.0
 */
public UserInfo validateAndExtractUser(String token, @Nullable String expectedAudience)
        throws TokenValidationException {
    // Implementation
}
```

## Quality Checklist

For comprehensive JavaDoc quality checklist covering all API types, see [javadoc-core.md](javadoc-core.md) section "Quality Checklist".

**Method-specific verification:**
- [ ] All public/protected methods documented
- [ ] All parameters documented with constraints
- [ ] Return values documented with guarantees
- [ ] All exceptions documented with conditions
