# JavaDoc Code Examples and Formatting Standards

Standards for code examples, inline code tags, and HTML formatting in JavaDoc.

## Inline Code Tags

| Tag | Use For | Example |
|-----|---------|---------|
| `{@code}` | Variable names, expressions, type names | `{@code userId}`, `{@code List<String>}` |
| `{@literal}` | Text with HTML special characters | `{@literal x < y && y > z}` |
| `{@link}` | Hyperlink to class/method (monospace) | `{@link TokenValidator#validate(String)}` |
| `{@linkplain}` | Hyperlink (plain text font) | `{@linkplain ValidatorConfig the config}` |

### Link Formats

```java
{@link ClassName}                          // Class in same package
{@link package.ClassName}                  // Fully qualified
{@link ClassName#methodName(String, int)}  // Method with parameters
{@link #methodName}                        // Method in current class
```

## Code Block Formatting

Use `<pre><code>` for multi-line examples. Examples should be complete and compilable:

```java
/**
 * Builder for JWT token validators.
 *
 * <p>Example:
 * <pre><code>
 * JwtTokenValidator validator = JwtTokenValidator.builder()
 *     .issuer("https://auth.example.com")
 *     .publicKey(loadPublicKey())
 *     .clockSkewSeconds(30)
 *     .build();
 *
 * ValidationResult result = validator.validate(jwtToken);
 * if (!result.isValid()) {
 *     log.error("Validation failed: {}", result.getErrors());
 * }
 * </code></pre>
 */
```

### Code Example Rules

- **Complete**: Include all setup so users can copy and run
- **Show error handling**: Include try/catch for methods that throw
- **Follow project standards**: Use Optional, parameterized logging, etc.
- **Keep concise**: Focus on key concepts, link to other methods for setup details

## HTML Formatting Reference

| Element | Usage |
|---------|-------|
| `<p>` | Paragraph breaks between sections |
| `<ul>/<li>` | Unordered lists |
| `<ol>/<li>` | Ordered/numbered lists |
| `<b>` | Bold emphasis (sparingly) — use for "Thread Safety:", "Security Note:" |
| `<h2>` | Section headings in long class docs |
| `<table>` | Structured reference data (include `<caption>`) |
| `<a href="...">` | External links (RFCs, specs) |

**Formatting rules**:
- Always close HTML tags properly (`<p>...</p>`)
- Use `{@code}` for inline code, not `<code>`
- Use `<pre><code>` for blocks, not `<pre>` alone

## External Links

```java
/**
 * Validates JWT tokens per
 * <a href="https://tools.ietf.org/html/rfc7519">RFC 7519</a>.
 */
```
