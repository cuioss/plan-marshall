# Verification and Validation Linking

Standards for linking specifications to test code and documenting test coverage.

> **Format note**: Specification-side examples use AsciiDoc syntax. For AsciiDoc link syntax, see `pm-documents:ref-asciidoc`. The linking concepts apply regardless of document format.

## Test References in Specifications

Include test verification sections in specifications to show how requirements are validated.

**Test Reference Format**:
```asciidoc
=== Verification
* link:../path/to/TokenValidatorTest[TokenValidatorTest] - Unit tests for token validation
* link:../path/to/AuthenticationIT[AuthenticationIT] - Integration tests for authentication flow
```

**Language-specific path examples**:
- Java: `link:../src/test/java/com/example/TokenValidatorTest.java[TokenValidatorTest]`
- Python: `link:../tests/test_token_validator.py[test_token_validator]`
- JS/TS: `link:../src/__tests__/TokenValidator.test.ts[TokenValidator.test]`

**What to Include**:
- List unit tests with brief descriptions
- List integration tests for end-to-end flows
- Document test coverage metrics when available
- Reference detailed testing specifications when they exist

## Coverage Documentation

**Coverage Section in AsciiDoc**:
```asciidoc
=== Coverage

Test coverage metrics:

* Line coverage: 92%
* Branch coverage: 88%
* Security-critical paths: 100%
```

**When to Include**:
- For IMPLEMENTED components
- When coverage data is available
- For security-critical components (always show 100% requirement)

## Test File API Documentation

Reference specifications from test files to complete bidirectional traceability.

### Java (JavaDoc)

```java
/**
 * Unit tests for {@link TokenValidator}.
 * <p>
 * Verifies the implementation against the requirements specified in
 * <a href="../../../../../../../doc/specification/token-validation.adoc">Token Validation Specification</a>.
 * <p>
 * Tests cover:
 * <ul>
 *   <li>Valid token validation</li>
 *   <li>Expired token handling</li>
 *   <li>Invalid signature detection</li>
 * </ul>
 */
public class TokenValidatorTest { }
```

### Python (Docstrings)

```python
class TestTokenValidator:
    """Unit tests for TokenValidator.

    Verifies the implementation against the requirements specified in
    doc/specification/token-validation.adoc.

    Tests cover:
        - Valid token validation
        - Expired token handling
        - Invalid signature detection
    """
```

### JavaScript/TypeScript (JSDoc)

```javascript
/**
 * Unit tests for TokenValidator.
 *
 * Verifies the implementation against the requirements specified in
 * doc/specification/token-validation.adoc.
 *
 * Tests cover:
 * - Valid token validation
 * - Expired token handling
 * - Invalid signature detection
 */
describe('TokenValidator', () => { });
```

## Integration Test Documentation

Integration tests should additionally list the requirement IDs they validate:

### Java Example

```java
/**
 * Integration tests for the complete authentication flow.
 * <p>
 * Validates end-to-end behavior specified in
 * <a href="path/to/doc/specification/authentication.adoc">Authentication Specification</a>.
 * <p>
 * Requirements validated:
 * <ul>
 *   <li>{@code AUTH-201: User Login}</li>
 *   <li>{@code AUTH-202: Session Management}</li>
 * </ul>
 */
```

### Python Example

```python
class TestAuthenticationFlow:
    """Integration tests for the complete authentication flow.

    Validates end-to-end behavior specified in
    doc/specification/authentication.adoc.

    Requirements validated:
        - AUTH-201: User Login
        - AUTH-202: Session Management
    """
```

### JavaScript/TypeScript Example

```javascript
/**
 * Integration tests for the complete authentication flow.
 *
 * Validates end-to-end behavior specified in
 * doc/specification/authentication.adoc.
 *
 * Requirements validated:
 * - AUTH-201: User Login
 * - AUTH-202: Session Management
 */
describe('Authentication Flow', () => {
  it('should complete user login', () => { });
  it('should manage sessions', () => { });
});
```

## Best Practices

**Complete Traceability**:
- Every specification should reference its tests
- Every test should reference its specification
- Test coverage should be documented

**Meaningful Descriptions**:
- Describe what tests validate, not how they work
- List requirement IDs being verified
- Note special validation for security/performance

**Keep Current**:
- Update test references when tests change
- Update coverage metrics regularly
- Remove references to deleted tests
