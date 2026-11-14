# Code-to-Specification Linking Standards

Standards for linking from implementation code back to specification documents via API documentation comments. Examples cover Java (JavaDoc), Python (docstrings), and JavaScript/TypeScript (JSDoc) with equal depth.

## Language-Specific Templates

### Java (JavaDoc)

**Class-level reference**:
```java
/**
 * [Class purpose]
 * <p>
 * Implements requirement: {@code REQ-ID: Requirement Title}
 * <p>
 * For detailed specifications, see the
 * <a href="[relative-path]/doc/specification/[spec-file].adoc">Specification</a>.
 */
public class ClassName { }
```

### Python (Docstrings)

**Module/class-level reference**:
```python
class ClassName:
    """[Class purpose].

    Implements requirement: REQ-ID: Requirement Title

    For detailed specifications, see:
        doc/specification/[spec-file].adoc
    """
```

### JavaScript/TypeScript (JSDoc)

**Class/module-level reference**:
```javascript
/**
 * [Class purpose]
 *
 * Implements requirement: REQ-ID: Requirement Title
 *
 * @see {@link doc/specification/[spec-file].adoc} for detailed specifications.
 */
export class ClassName { }
```

## Path Calculation

Calculate relative paths from source code to documentation:

- **Formula**: Count directory levels from source file to project root, then append `doc/`
- **Example (Java)**: From `src/main/java/com/example/` → `../../../../../../../doc/`
- **Example (Python)**: From `src/validators/` → `../../doc/`
- **Example (JS/TS)**: From `src/components/` → `../../doc/`

## Linking Approaches

**Class/module-level references**:
- Link to overall specification in class or module documentation
- Use when entire class/module implements a specification component

**Method/function-level references**:
- Reference specific requirement IDs for individual methods or functions
- Use when methods implement specific requirements

**Multiple requirements**:
- List each requirement with its ID in the documentation comment
- Use the language's list/bullet syntax (HTML `<ul>` for JavaDoc, plain text for docstrings)

## Examples

**Single requirement (Java)**:
```java
/**
 * Validates JWT tokens according to security requirements.
 * <p>
 * Implements requirement: {@code SEC-101: Token Validation}
 * <p>
 * For detailed specifications, see the
 * <a href="../../../../../../../doc/specification/security.adoc">Security Specification</a>.
 */
```

**Single requirement (Python)**:
```python
def validate_token(token: str) -> ValidationResult:
    """Validate JWT tokens according to security requirements.

    Implements requirement: SEC-101: Token Validation

    See: doc/specification/security.adoc
    """
```

**Multiple requirements (Java)**:
```java
/**
 * User authentication service.
 * <p>
 * Implements requirements:
 * <ul>
 *   <li>{@code AUTH-201: User Login}</li>
 *   <li>{@code AUTH-202: Session Management}</li>
 *   <li>{@code SEC-105: Password Security}</li>
 * </ul>
 */
```

**Multiple requirements (Python)**:
```python
class AuthenticationService:
    """User authentication service.

    Implements requirements:
        - AUTH-201: User Login
        - AUTH-202: Session Management
        - SEC-105: Password Security

    See: doc/specification/authentication.adoc
    """
```

**Multiple requirements (JavaScript/TypeScript)**:
```javascript
/**
 * User authentication service.
 *
 * Implements requirements:
 * - AUTH-201: User Login
 * - AUTH-202: Session Management
 * - SEC-105: Password Security
 *
 * @see {@link doc/specification/authentication.adoc} for detailed specifications.
 */
export class AuthenticationService { }
```
