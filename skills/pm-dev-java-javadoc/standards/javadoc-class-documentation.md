# JavaDoc Class and Interface Documentation Standards

Standards for documenting packages, classes, interfaces, enums, and annotations.

## Package Documentation

Every package MUST have a `package-info.java` with:
- Overview explaining package purpose and scope
- Key components listed with `{@link}` references
- Usage example
- `@since` tag

```java
/**
 * Provides token validation and authentication services.
 *
 * <h2>Key Components</h2>
 * <ul>
 *   <li>{@link com.example.authentication.TokenValidator} - Main validation interface</li>
 *   <li>{@link com.example.authentication.JwtTokenParser} - JWT parsing</li>
 * </ul>
 *
 * @since 1.0.0
 */
package com.example.authentication;
```

## Class Documentation

Every public class must document: purpose, key behavior, thread safety, and `@since`.

```java
/**
 * Validates JWT tokens according to RFC 7519, verifying signature,
 * expiration, and issuer claims.
 *
 * <p>Supports both HS256 and RS256 signature algorithms with
 * configurable clock skew tolerance.
 *
 * <p><b>Thread Safety:</b> Immutable and thread-safe.
 *
 * @see TokenValidator
 * @since 1.2.0
 */
public class JwtTokenValidator implements TokenValidator { }
```

### Abstract Classes

Focus on extension points:

```java
/**
 * Base class for token validators providing common validation logic.
 *
 * <p>Subclasses must implement {@link #validateSignature(String)}.
 * This base class handles expiration and issuer validation.
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

Document as contracts — include implementation requirements and known implementations:

```java
/**
 * Contract for validating authentication tokens.
 *
 * <p><b>Implementation Requirements:</b>
 * <ul>
 *   <li>Must be thread-safe for concurrent use</li>
 *   <li>Must not modify the input token</li>
 *   <li>Must handle null tokens by throwing IllegalArgumentException</li>
 * </ul>
 *
 * @see JwtTokenValidator
 * @see OAuth2TokenValidator
 * @since 1.0.0
 */
public interface TokenValidator {
    ValidationResult validate(String token);
}
```

## Enum Documentation

Document enum purpose and each constant:

```java
/**
 * Supported token types for authentication.
 *
 * @since 1.0.0
 */
public enum TokenType {
    /** JWT for API authentication. Supports HS256 and RS256. */
    JWT,

    /** OAuth2 bearer token per RFC 6750. */
    OAUTH2_BEARER,

    /** @deprecated since 2.0.0, use {@link #JWT} instead */
    @Deprecated
    LEGACY_SESSION;
}
```

## Annotation Documentation

Document purpose, applicability, all elements with defaults, and processing:

```java
/**
 * Marks a method as requiring token-based authentication.
 *
 * <p>Processed by {@link AuthenticationInterceptor} at runtime.
 *
 * @see TokenValidator
 * @since 1.1.0
 */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.METHOD, ElementType.TYPE})
public @interface RequiresAuthentication {
    /** The required token type. Defaults to JWT. */
    TokenType tokenType() default TokenType.JWT;

    /** The HTTP header containing the token. Defaults to Authorization. */
    String headerName() default "Authorization";
}
```

## Generic Type Documentation

Document type parameters with constraints:

```java
/**
 * Cache for validated tokens with configurable eviction.
 *
 * @param <K> the key type, must implement equals/hashCode correctly
 * @param <V> the cached token type
 * @since 1.2.0
 */
public class TokenCache<K, V extends Token> { }
```
