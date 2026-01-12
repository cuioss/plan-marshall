# JavaDoc Code Examples and Formatting Standards

## Overview

This document defines standards for formatting code examples, using inline code tags, and applying HTML formatting in JavaDoc documentation.

## Inline Code Formatting

### {@code} Tag

Use `{@code}` for inline code references that are not links:

```java
/**
 * Validates the token format. The token must follow the pattern
 * {@code header.payload.signature} where each part is Base64URL encoded.
 *
 * @param token the token string
 * @return true if format is valid
 */
public boolean validateFormat(String token) {
    // Implementation
}
```

**Use cases for {@code}**:
* Variable names: `{@code userId}`
* Method names without links: `{@code validate()}`
* Simple code expressions: `{@code x > 0}`
* Code fragments: `{@code if (x != null)}`
* Type names without links: `{@code List<String>}`

### {@literal} Tag

Use `{@literal}` for text with special HTML characters:

```java
/**
 * Parses HTML entities in the input string. Supports common entities like
 * {@literal &lt;}, {@literal &gt;}, {@literal &amp;}, and {@literal &quot;}.
 *
 * @param html the HTML string to parse
 * @return parsed string with entities decoded
 */
public String parseHtmlEntities(String html) {
    // Implementation
}
```

**Use cases for {@literal}**:
* HTML characters: `<`, `>`, `&`
* Generic type syntax: `{@literal List<Map<String, Integer>>}`
* Mathematical expressions with </>: `{@literal x < y && y > z}`

### {@link} and {@linkplain} Tags

Use for creating hyperlinks to other classes, methods, or fields:

```java
/**
 * Validates a token using the algorithm specified by {@link TokenType}.
 * See {@link #validate(String, TokenType)} for the full validation method.
 *
 * <p>For configuration details, refer to {@linkplain ValidatorConfig the validator configuration}.
 *
 * @param token the token to validate
 * @return validation result
 * @see TokenType
 * @see ValidatorConfig
 */
public ValidationResult validate(String token) {
    // Implementation
}
```

**{@link} vs {@linkplain}**:
* `{@link}`: Renders in monospace/code font
* `{@linkplain}`: Renders in plain text font

**Link formats**:
```java
{@link ClassName}                          // Link to class in same package
{@link package.ClassName}                  // Fully qualified class name
{@link ClassName#methodName}               // Method without parameters
{@link ClassName#methodName(String, int)}  // Method with parameters
{@link #methodName}                        // Method in current class
{@link #fieldName}                         // Field in current class
```

## Code Block Formatting

### Basic Code Blocks

Use `<pre><code>` tags for multi-line code examples:

```java
/**
 * Authenticates a user and returns a session token.
 *
 * <p>Example usage:
 * <pre><code>
 * TokenValidator validator = new JwtTokenValidator(config);
 * ValidationResult result = validator.validate(token);
 * if (result.isValid()) {
 *     System.out.println("Token is valid!");
 * }
 * </code></pre>
 *
 * @param token the authentication token
 * @return validation result
 */
public ValidationResult validate(String token) {
    // Implementation
}
```

### Complete, Compilable Examples

Provide complete examples that users can copy and run:

```java
/**
 * Builder for creating JWT token validators with custom configuration.
 *
 * <p>Example:
 * <pre><code>
 * // Create validator with default settings
 * JwtTokenValidator validator = JwtTokenValidator.builder()
 *     .issuer("https://auth.example.com")
 *     .publicKey(loadPublicKey())
 *     .clockSkewSeconds(30)
 *     .build();
 *
 * // Validate a token
 * ValidationResult result = validator.validate(jwtToken);
 * if (!result.isValid()) {
 *     log.error("Validation failed: {}", result.getErrors());
 * }
 * </code></pre>
 */
public static class Builder {
    // Implementation
}
```

### Code Examples with Error Handling

Show proper error handling in examples:

```java
/**
 * Loads configuration from the specified file.
 *
 * <p>Example with error handling:
 * <pre><code>
 * try {
 *     Configuration config = ConfigLoader.loadConfig(configPath);
 *     System.out.println("Loaded config: " + config);
 * } catch (FileNotFoundException e) {
 *     log.error("Config file not found: {}", configPath, e);
 *     // Use default configuration
 *     config = Configuration.defaultConfig();
 * } catch (ConfigurationException e) {
 *     log.error("Invalid configuration format", e);
 *     throw new IllegalStateException("Cannot start without valid config", e);
 * }
 * </code></pre>
 *
 * @param configPath the path to the configuration file
 * @return loaded configuration
 * @throws FileNotFoundException if config file doesn't exist
 * @throws ConfigurationException if config format is invalid
 */
public static Configuration loadConfig(Path configPath)
        throws FileNotFoundException, ConfigurationException {
    // Implementation
}
```

### Multi-Step Examples

For complex workflows, show complete step-by-step examples:

```java
/**
 * Token validation service providing comprehensive token validation and user extraction.
 *
 * <p>Complete usage example:
 * <pre><code>
 * // Step 1: Create and configure the validator
 * TokenValidator validator = TokenValidator.builder()
 *     .issuer("https://auth.example.com")
 *     .audience("my-api")
 *     .clockSkewSeconds(30)
 *     .build();
 *
 * // Step 2: Extract token from request header
 * String authHeader = request.getHeader("Authorization");
 * if (authHeader == null || !authHeader.startsWith("Bearer ")) {
 *     throw new AuthenticationException("Missing or invalid Authorization header");
 * }
 * String token = authHeader.substring(7);
 *
 * // Step 3: Validate token
 * ValidationResult result = validator.validate(token);
 * if (!result.isValid()) {
 *     log.warn("Token validation failed: {}", result.getErrors());
 *     response.sendError(HttpServletResponse.SC_UNAUTHORIZED);
 *     return;
 * }
 *
 * // Step 4: Extract user information
 * UserInfo user = validator.extractUserInfo(token);
 * request.setAttribute("currentUser", user);
 * </code></pre>
 */
public class TokenValidator {
    // Implementation
}
```

## HTML Formatting

### Paragraph Breaks

Use `<p>` tags for paragraph breaks:

```java
/**
 * Validates JWT tokens according to RFC 7519 specifications.
 *
 * <p>This validator performs the following checks:
 * <ul>
 *   <li>Signature verification</li>
 *   <li>Expiration time validation</li>
 *   <li>Issuer verification</li>
 *   <li>Audience validation</li>
 * </ul>
 *
 * <p>The validator uses a configurable clock skew to handle minor time
 * differences between servers.
 */
public class JwtTokenValidator {
    // Implementation
}
```

### Lists

Use `<ul>` and `<li>` for unordered lists, `<ol>` for ordered lists:

```java
/**
 * Token validation result containing status and error information.
 *
 * <p>Possible validation failures include:
 * <ul>
 *   <li>Invalid signature</li>
 *   <li>Expired token</li>
 *   <li>Invalid issuer</li>
 *   <li>Missing required claims</li>
 *   <li>Invalid audience</li>
 * </ul>
 *
 * <p>To handle validation failures:
 * <ol>
 *   <li>Check {@link #isValid()} to determine overall status</li>
 *   <li>Call {@link #getErrors()} to get detailed error messages</li>
 *   <li>Log errors for debugging</li>
 *   <li>Return appropriate HTTP status code</li>
 * </ol>
 */
public class ValidationResult {
    // Implementation
}
```

### Emphasis and Formatting

Use HTML tags sparingly for emphasis:

```java
/**
 * Validates tokens with strict security checks.
 *
 * <p><b>Security Note:</b> This validator enforces strict validation rules
 * and rejects tokens with any security concerns. Use
 * {@link LenientTokenValidator} only for testing environments.
 *
 * <p><i>Thread Safety:</i> This class is immutable and thread-safe.
 *
 * @see LenientTokenValidator
 */
public class StrictTokenValidator {
    // Implementation
}
```

### Tables

Use tables for structured information:

```java
/**
 * Token type enumeration with associated validators.
 *
 * <p>Supported token types:
 * <table border="1">
 *   <caption>Token Types and Their Validators</caption>
 *   <tr>
 *     <th>Token Type</th>
 *     <th>Validator Class</th>
 *     <th>RFC Reference</th>
 *   </tr>
 *   <tr>
 *     <td>JWT</td>
 *     <td>{@link JwtTokenValidator}</td>
 *     <td>RFC 7519</td>
 *   </tr>
 *   <tr>
 *     <td>OAuth2 Bearer</td>
 *     <td>{@link OAuth2TokenValidator}</td>
 *     <td>RFC 6750</td>
 *   </tr>
 * </table>
 */
public enum TokenType {
    // Implementation
}
```

### Headings

Use HTML headings to structure long documentation:

```java
/**
 * Comprehensive token validation service.
 *
 * <h2>Overview</h2>
 * <p>This service provides token validation for multiple token types
 * including JWT, OAuth2, and SAML tokens.
 *
 * <h2>Configuration</h2>
 * <p>Configure the validator using the builder pattern:
 * <pre><code>
 * TokenValidator validator = TokenValidator.builder()
 *     .issuer("https://auth.example.com")
 *     .build();
 * </code></pre>
 *
 * <h2>Usage</h2>
 * <p>Validate tokens by calling {@link #validate(String)}.
 *
 * <h2>Error Handling</h2>
 * <p>Validation errors are returned in {@link ValidationResult}.
 */
public class TokenValidator {
    // Implementation
}
```

## Code Example Best Practices

### 1. Complete Examples

Provide working code that users can copy:

```java
// ✅ Good - Complete and runnable
/**
 * <pre><code>
 * Configuration config = Configuration.builder()
 *     .issuer("https://auth.example.com")
 *     .audience("my-api")
 *     .build();
 * TokenValidator validator = new JwtTokenValidator(config);
 * </code></pre>
 */

// ❌ Bad - Incomplete
/**
 * <pre><code>
 * TokenValidator validator = new JwtTokenValidator(config);
 * // Where does config come from?
 * </code></pre>
 */
```

### 2. Show Common Use Cases

Focus on typical usage patterns:

```java
/**
 * Validates tokens and extracts user information.
 *
 * <p>Common use case - validating request tokens:
 * <pre><code>
 * String token = extractTokenFromHeader(request);
 * ValidationResult result = validator.validate(token);
 *
 * if (result.isValid()) {
 *     UserInfo user = validator.extractUserInfo(token);
 *     // Process authenticated request
 * } else {
 *     throw new AuthenticationException("Invalid token: " + result.getErrors());
 * }
 * </code></pre>
 */
```

### 3. Follow Project Standards

Examples should follow project coding standards:

```java
/**
 * <pre><code>
 * // ✅ Follows project standards
 * Optional&lt;User&gt; user = userRepository.findById(userId);
 * if (user.isPresent()) {
 *     log.info("Found user: {}", user.get().getName());
 * }
 *
 * // ❌ Doesn't follow standards (uses != null instead of Optional)
 * User user = userRepository.findByIdLegacy(userId);
 * if (user != null) {
 *     log.info("Found user: " + user.getName());
 * }
 * </code></pre>
 */
```

### 4. Include Error Handling

Show proper error handling:

```java
/**
 * <pre><code>
 * try {
 *     ValidationResult result = validator.validate(token);
 *     if (!result.isValid()) {
 *         log.warn("Validation failed: {}", result.getErrors());
 *         return Response.status(401).entity("Invalid token").build();
 *     }
 *     return Response.ok().build();
 * } catch (TokenException e) {
 *     log.error("Token validation error", e);
 *     return Response.status(500).entity("Validation error").build();
 * }
 * </code></pre>
 */
```

## Formatting Anti-Patterns

### 1. Mixing Code and Description

```java
// ❌ Bad - mixed inline
/**
 * Call validator.validate(token) to validate the token, then check
 * result.isValid() to see if it passed.
 */

// ✅ Good - clear separation
/**
 * Validates a token and checks the result.
 *
 * <p>Example:
 * <pre><code>
 * ValidationResult result = validator.validate(token);
 * if (result.isValid()) {
 *     // Token is valid
 * }
 * </code></pre>
 */
```

### 2. Incomplete HTML Tags

```java
// ❌ Bad - unclosed tags
/**
 * <p>First paragraph
 * <p>Second paragraph
 */

// ✅ Good - properly closed (or self-closing <p>)
/**
 * <p>First paragraph</p>
 * <p>Second paragraph</p>
 */
```

### 3. Overly Complex Examples

```java
// ❌ Bad - too complex
/**
 * <pre><code>
 * // 50 lines of complex setup code...
 * </code></pre>
 */

// ✅ Good - simplified
/**
 * <pre><code>
 * // Simplified example showing key concepts
 * TokenValidator validator = createValidator();
 * ValidationResult result = validator.validate(token);
 * </code></pre>
 *
 * <p>See {@link #createValidator()} for validator setup details.
 */
```

## External Links

For links to external resources, use standard HTML anchors:

```java
/**
 * Validates JWT tokens according to
 * <a href="https://tools.ietf.org/html/rfc7519">RFC 7519</a>.
 *
 * <p>For OAuth2 bearer tokens, see
 * <a href="https://tools.ietf.org/html/rfc6750">RFC 6750</a>.
 */
```

## Quality Checklist

For comprehensive JavaDoc quality checklist covering all API types, see [javadoc-core.md](javadoc-core.md) section "Quality Checklist".

**Code example-specific verification:**
- [ ] Inline code uses `{@code}` tag
- [ ] Code blocks use `<pre><code>` tags
- [ ] Examples are complete and compilable
- [ ] Examples show error handling
