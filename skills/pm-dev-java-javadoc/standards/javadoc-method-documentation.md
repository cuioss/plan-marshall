# JavaDoc Method and Field Documentation Standards

Standards for documenting methods, fields, and constructors.

## Method Documentation

Every public and protected method must document: purpose, `@param`, `@return`, `@throws`, and `@since` (for public APIs).

```java
/**
 * Authenticates a user and returns a session token.
 *
 * @param username the username (3-20 characters, alphanumeric)
 * @param password the raw password (min 8 characters, will be hashed)
 * @return authenticated session token with 24-hour validity
 * @throws AuthenticationException if credentials are invalid or user is locked
 * @throws IllegalArgumentException if username or password is null or empty
 * @see #logout(String)
 * @since 1.0.0
 */
public String authenticate(String username, String password)
        throws AuthenticationException { }
```

### Parameter Documentation

Include purpose, constraints, and validation rules:

```java
/**
 * @param username the unique username (3-20 chars, alphanumeric, case-insensitive)
 * @param roles the roles to assign (must not be null or empty, duplicates removed)
 */
```

### Return Value Documentation

State what the value represents and guarantees (nullability, ordering, emptiness):

```java
/**
 * @return list of active users ordered by registration date (newest first),
 *         never null but may be empty
 */
public List<User> getActiveUsers() { }

/**
 * @return the user if found, or Optional.empty() if not found
 */
public Optional<User> findById(String userId) { }
```

### Exception Documentation

Document both checked and significant unchecked exceptions with triggering conditions:

```java
/**
 * @throws FileNotFoundException if the config file does not exist
 * @throws ConfigurationException if the file format is invalid or required fields missing
 * @throws IllegalArgumentException if configPath is null
 */
```

## Overridden Methods

Document only when adding behavior beyond the contract:

```java
/**
 * {@inheritDoc}
 *
 * <p>This implementation caches results for 5 minutes.
 */
@Override
public ValidationResult validate(String token) { }
```

For simple overrides (`toString`, `equals`, `hashCode`), no documentation needed.

## Private Methods

Document only complex private methods:

```java
/**
 * Applies rate limiting using token bucket algorithm.
 *
 * @implSpec Not thread-safe — must be called within a synchronized block.
 */
private boolean checkRateLimit(String userId) { }
```

## Constructor Documentation

Document validation rules and business constraints, not obvious assignments:

```java
/**
 * Creates a new JWT validator with the specified configuration.
 *
 * @param issuer the expected issuer URL (must be valid URL format)
 * @param publicKey the RSA public key for signature verification
 * @param clockSkewSeconds allowed clock skew (non-negative, typically 30-300)
 * @throws KeyException if the public key format is invalid
 */
public JwtTokenValidator(String issuer, PublicKey publicKey, int clockSkewSeconds)
        throws KeyException { }
```

## Special Method Patterns

### Builder and Factory Methods

```java
/**
 * Sets the token issuer URL.
 *
 * @param issuer the issuer URL (must be valid HTTPS URL)
 * @return this builder for method chaining
 */
public Builder issuer(String issuer) { }

/**
 * Builds a configured JWT token validator.
 *
 * @return a new JwtTokenValidator instance, never null
 * @throws IllegalStateException if required settings are not set
 */
public JwtTokenValidator build() { }
```

### Generic Methods

Document type parameters and constraints:

```java
/**
 * Converts a token string into a typed token object.
 *
 * @param <T> the token type, must extend {@link Token}
 * @param tokenString the token string to parse
 * @param tokenClass the class representing T
 * @return parsed token instance, never null
 * @throws ParseException if the string cannot be parsed into type T
 */
public <T extends Token> T parse(String tokenString, Class<T> tokenClass)
        throws ParseException { }
```

## Field Documentation

- **Public/protected fields**: Always document
- **Private fields**: Only when they have complex invariants
- **Skip**: Logger fields, `serialVersionUID`, fields with obvious purpose from name and type

```java
/** Maximum login attempts before account lockout. */
public static final int MAX_LOGIN_ATTEMPTS = 3;

/**
 * Cache of active sessions. Invariant: all sessions have expiry > now.
 * Cleanup by background thread every 60 seconds.
 */
private final Map<String, Session> activeSessions = new ConcurrentHashMap<>();
```
