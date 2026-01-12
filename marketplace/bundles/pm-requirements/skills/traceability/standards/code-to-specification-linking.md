# Code-to-Specification Linking Standards

Standards for linking from implementation code (JavaDoc) back to specification documents.

## JavaDoc Specification Reference Template

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

**Method-level reference**:
```java
/**
 * [Method purpose]
 * <p>
 * Implements requirement: {@code REQ-ID: Requirement Title}
 * @param [param] [description]
 * @return [description]
 */
public ReturnType methodName(ParamType param) { }
```

## Path Calculation

Calculate relative paths from source code to documentation:

- **From `src/main/java/com/example/`**: `../../../../../../../doc/`
- **From `src/test/java/com/example/`**: `../../../../../../../doc/`
- **Formula**: Count directory levels from `src/` to file, then use that many `../` to reach project root, then add `doc/`

## Linking Approaches

**Class-level references**:
- Link to overall specification in class JavaDoc
- Use when entire class implements a specification component

**Method-level references**:
- Reference specific requirement IDs for methods
- Use when methods implement specific requirements
- See Method-Level Requirement Reference Template above

**Multiple requirements**:
- Use bulleted list in JavaDoc
- For classes implementing multiple requirements
- List each requirement with its ID

## Examples

**Single requirement**:
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

**Multiple requirements**:
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
 * <p>
 * For detailed specifications, see the
 * <a href="../../../../../../../doc/specification/authentication.adoc">Authentication Specification</a>.
 */
```
