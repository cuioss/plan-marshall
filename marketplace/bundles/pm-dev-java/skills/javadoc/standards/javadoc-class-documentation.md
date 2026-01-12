# JavaDoc Class and Interface Documentation Standards

## Overview

This document defines standards for documenting packages, classes, interfaces, enums, and annotations in CUI Java projects.

## Package Documentation

### package-info.java Requirements

Every package MUST have a package-info.java file with comprehensive documentation.

**Structure**:
```java
/**
 * Provides token validation and authentication services for OAuth2 and JWT tokens.
 *
 * <h2>Key Components</h2>
 * <ul>
 *   <li>{@link de.cuioss.portal.authentication.TokenValidator} - Main token validation interface</li>
 *   <li>{@link de.cuioss.portal.authentication.JwtTokenParser} - JWT token parsing implementation</li>
 *   <li>{@link de.cuioss.portal.authentication.OAuth2TokenValidator} - OAuth2 token validation</li>
 * </ul>
 *
 * <h2>Best Practices</h2>
 * <p>Always validate tokens before accessing protected resources. Use the
 * {@link de.cuioss.portal.authentication.TokenValidator#validate(String)} method
 * which provides detailed validation results.</p>
 *
 * <h2>Usage Example</h2>
 * <pre><code>
 * TokenValidator validator = new JwtTokenValidator(issuerConfig);
 * ValidationResult result = validator.validate(bearerToken);
 * if (result.isValid()) {
 *     // Process authenticated request
 * }
 * </code></pre>
 *
 * @since 1.0.0
 * @author CUI Team
 */
package de.cuioss.portal.authentication;
```

### Required Sections

* **Overview**: Explain package purpose and scope
* **Key Components**: List main classes/interfaces with {@link} references
* **Best Practices**: Guidelines for using the package
* **Usage Example**: Complete example showing typical usage
* **Cross-references**: Links to related packages
* **Author and version**: @author and @since tags

## Class Documentation

### Public Classes

Every public class must be fully documented:

```java
/**
 * Validates JWT tokens according to RFC 7519 specifications, verifying
 * signature, expiration, and issuer claims.
 *
 * <p>This validator supports both symmetric (HS256) and asymmetric (RS256)
 * signature algorithms. It validates tokens against a configured issuer and
 * allows for clock skew tolerance during expiration checks.
 *
 * <p><b>Thread Safety:</b> This class is immutable and thread-safe. Instances
 * can be safely shared across multiple threads.
 *
 * <p><b>Usage Example:</b></p>
 * <pre><code>
 * JwtTokenValidator validator = JwtTokenValidator.builder()
 *     .issuer("https://auth.example.com")
 *     .clockSkewSeconds(30)
 *     .build();
 *
 * ValidationResult result = validator.validate(jwtToken);
 * if (!result.isValid()) {
 *     log.warn("Token validation failed: {}", result.getErrors());
 * }
 * </code></pre>
 *
 * @see TokenValidator
 * @see ValidationResult
 * @since 1.2.0
 */
public class JwtTokenValidator implements TokenValidator {
    // Implementation
}
```

### Required Elements

* **Purpose**: Clear statement of what the class does
* **Behavior**: Key behavioral characteristics
* **Thread Safety**: Explicit statement about thread-safety
* **Usage Example**: Complete, compilable example
* **@since**: Version when introduced
* **@see**: References to related classes

### Abstract Classes

Document abstract classes with focus on extension points:

```java
/**
 * Abstract base class for all token validators providing common validation logic.
 *
 * <p>Subclasses must implement {@link #validateSignature(String)} to provide
 * token-specific signature validation. This base class handles expiration
 * and issuer validation.
 *
 * <p><b>Extension Points:</b></p>
 * <ul>
 *   <li>{@link #validateSignature(String)} - Token-specific signature validation</li>
 *   <li>{@link #extractClaims(String)} - Token-specific claims extraction</li>
 * </ul>
 *
 * @since 1.0.0
 */
public abstract class AbstractTokenValidator implements TokenValidator {
    /**
     * Validates the token signature using implementation-specific logic.
     *
     * @param token the token to validate
     * @return true if signature is valid
     * @throws ValidationException if signature validation fails
     */
    protected abstract boolean validateSignature(String token)
            throws ValidationException;
}
```

## Interface Documentation

### Public Interfaces

Document interfaces as contracts:

```java
/**
 * Contract for validating authentication tokens.
 *
 * <p>Implementations of this interface validate tokens according to specific
 * protocols (JWT, OAuth2, SAML, etc.) and return detailed validation results.
 *
 * <p><b>Implementation Requirements:</b></p>
 * <ul>
 *   <li>Must be thread-safe for concurrent use</li>
 *   <li>Must not modify the input token</li>
 *   <li>Must return detailed error information in ValidationResult</li>
 *   <li>Must handle null tokens by throwing IllegalArgumentException</li>
 * </ul>
 *
 * <p><b>Known Implementations:</b></p>
 * <ul>
 *   <li>{@link JwtTokenValidator} - JWT token validation</li>
 *   <li>{@link OAuth2TokenValidator} - OAuth2 bearer token validation</li>
 * </ul>
 *
 * @see ValidationResult
 * @since 1.0.0
 */
public interface TokenValidator {
    /**
     * Validates the given authentication token.
     *
     * @param token the token to validate, must not be null
     * @return validation result containing status and any errors, never null
     * @throws IllegalArgumentException if token is null
     */
    ValidationResult validate(String token);
}
```

### Required Elements

* **Contract Description**: What the interface represents
* **Implementation Requirements**: Rules implementors must follow
* **Known Implementations**: List common implementations
* **@see**: References to related interfaces/classes

## Enum Documentation

### Enum Types

Document enum purpose and each constant:

```java
/**
 * Defines supported token types for authentication and authorization.
 *
 * <p>Each token type has specific validation rules and use cases. Use
 * {@link #getValidator()} to obtain the appropriate validator for each type.
 *
 * @since 1.0.0
 */
public enum TokenType {

    /**
     * JWT (JSON Web Token) for API authentication.
     * Supports both HS256 and RS256 signature algorithms.
     */
    JWT("application/jwt", JwtTokenValidator.class),

    /**
     * OAuth2 bearer token for delegated authorization.
     * Validated according to RFC 6750.
     */
    OAUTH2_BEARER("application/oauth2", OAuth2TokenValidator.class),

    /**
     * Legacy session token for backward compatibility.
     * @deprecated since 2.0.0, use {@link #JWT} instead
     */
    @Deprecated
    LEGACY_SESSION("application/session", LegacySessionValidator.class);

    private final String contentType;
    private final Class<? extends TokenValidator> validatorClass;

    /**
     * Creates a new token type with the specified content type and validator.
     *
     * @param contentType the MIME type for this token type
     * @param validatorClass the validator class for this token type
     */
    TokenType(String contentType, Class<? extends TokenValidator> validatorClass) {
        this.contentType = contentType;
        this.validatorClass = validatorClass;
    }

    /**
     * Returns the MIME content type for this token type.
     *
     * @return the content type, never null
     */
    public String getContentType() {
        return contentType;
    }
}
```

## Annotation Documentation

### Annotation Types

Document annotation purpose and all elements:

```java
/**
 * Marks a method as requiring token-based authentication.
 *
 * <p>Methods annotated with @RequiresAuthentication will have their
 * token validated before execution. If validation fails, a
 * {@link SecurityException} is thrown.
 *
 * <h2>Usage Example</h2>
 * <pre><code>
 * &#64;RequiresAuthentication(tokenType = TokenType.JWT)
 * public User getCurrentUser(@HeaderParam("Authorization") String token) {
 *     // Method implementation
 * }
 * </code></pre>
 *
 * <h2>Processing</h2>
 * <p>This annotation is processed by {@link AuthenticationInterceptor} at
 * runtime. The interceptor extracts the token from the configured header
 * and validates it using the appropriate validator.
 *
 * @see TokenValidator
 * @see AuthenticationInterceptor
 * @since 1.1.0
 */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.METHOD, ElementType.TYPE})
public @interface RequiresAuthentication {

    /**
     * The type of token required for authentication.
     * Defaults to JWT tokens.
     *
     * @return the required token type
     */
    TokenType tokenType() default TokenType.JWT;

    /**
     * The HTTP header containing the authentication token.
     * Defaults to the standard Authorization header.
     *
     * @return the header name
     */
    String headerName() default "Authorization";

    /**
     * Whether to allow expired tokens for read-only operations.
     * When true, expired tokens are accepted but a warning is logged.
     *
     * @return true if expired tokens are allowed, false otherwise
     */
    boolean allowExpired() default false;
}
```

### Required Elements

* **Purpose**: What the annotation does
* **Applicability**: Where it can be used
* **Element Documentation**: All elements with @return tags
* **Default Values**: Document all defaults
* **Usage Example**: Complete example
* **Processing**: How the annotation is processed

## Inheritance Documentation

### Documenting Inheritance

```java
/**
 * Specialized token validator for OpenID Connect ID tokens.
 *
 * <p>Extends {@link JwtTokenValidator} with additional validation for
 * OpenID Connect specific claims such as nonce, auth_time, and acr.
 *
 * <p><b>Additional Validations:</b></p>
 * <ul>
 *   <li>Nonce claim validation against expected value</li>
 *   <li>Auth_time claim validation for max age requirements</li>
 *   <li>ACR (Authentication Context Class Reference) validation</li>
 * </ul>
 *
 * @see JwtTokenValidator
 * @since 1.3.0
 */
public class OidcIdTokenValidator extends JwtTokenValidator {
    // Implementation
}
```

## Serialization Documentation

### Serializable Classes

Document serialization behavior:

```java
/**
 * Represents the result of token validation with detailed error information.
 *
 * <p>This class is serializable to support caching and distributed scenarios.
 * The serialized form includes validation status and all error messages.
 *
 * <p><b>Serialization Notes:</b></p>
 * <ul>
 *   <li>All fields are serializable</li>
 *   <li>No custom serialization logic required</li>
 *   <li>Compatible across versions (serialVersionUID maintained)</li>
 * </ul>
 *
 * @since 1.0.0
 */
public class ValidationResult implements Serializable {
    private static final long serialVersionUID = 1L;

    // Fields and methods
}
```

## Generic Type Documentation

### Generic Classes

Document type parameters:

```java
/**
 * Generic cache for storing validated tokens with configurable eviction policy.
 *
 * @param <K> the key type for cache lookups, must be immutable and implement
 *            equals/hashCode correctly
 * @param <V> the value type for cached tokens, must be thread-safe for
 *            concurrent access
 * @since 1.2.0
 */
public class TokenCache<K, V extends Token> {

    /**
     * Retrieves a token from the cache.
     *
     * @param key the cache key, must not be null
     * @return the cached token if present, or Optional.empty() if not found
     * @throws NullPointerException if key is null
     */
    public Optional<V> get(K key) {
        // Implementation
    }
}
```

## Quality Checklist

For comprehensive JavaDoc quality checklist covering all API types, see [javadoc-core.md](javadoc-core.md) section "Quality Checklist".

**Class-specific verification:**
- [ ] Package-info.java exists with complete documentation
- [ ] All public classes have clear purpose statements
- [ ] Abstract classes document extension points
- [ ] Interfaces document implementation requirements
