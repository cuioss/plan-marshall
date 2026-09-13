---
name: pm-dev-java-javadoc
description: JavaDoc documentation standards including class, method, and code example patterns
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# JavaDoc Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

JavaDoc documentation standards for Java projects. This skill covers class documentation, method documentation, code examples, and error references.

## Prerequisites

This skill applies to all Java projects using standard JavaDoc.

## Workflow

### Step 1: Load Core Standards

Load this standard for any JavaDoc work.

```text
Call the `read` tool with `{ filePath: "standards/javadoc-core.md" }` before continuing.
```

This provides foundational rules for:
- Mandatory documentation requirements
- Clarity, completeness, and consistency principles
- Tag ordering standards

### Step 2: Load Specific Standards (As Needed)

**Class Documentation** (load for class-level docs):
```text
Call the `read` tool with `{ filePath: "standards/javadoc-class-documentation.md" }` before continuing.
```

Use when: Documenting classes, interfaces, enums, or annotations.

**Method Documentation** (load for method-level docs):
```text
Call the `read` tool with `{ filePath: "standards/javadoc-method-documentation.md" }` before continuing.
```

Use when: Documenting methods, including parameters, returns, and exceptions.

**Code Examples** (load for example snippets):
```text
Call the `read` tool with `{ filePath: "standards/javadoc-code-examples.md" }` before continuing.
```

Use when: Adding code examples to documentation using @snippet or @code.

**Error Reference** (load for troubleshooting):
```text
Call the `read` tool with `{ filePath: "standards/javadoc-error-reference.md" }` before continuing.
```

Use when: Fixing JavaDoc errors or warnings.

## Key Rules Summary

### Class Documentation
```java
/**
 * Validates JWT tokens against configured issuer and signing keys.
 *
 * <p>This validator supports both HMAC and RSA algorithms with
 * configurable clock skew tolerance for distributed systems.
 *
 * @since 1.0
 * @see TokenConfig
 */
@ApplicationScoped
public class TokenValidator { }
```

### Method Documentation
```java
/**
 * Validates the JWT token signature and expiration time.
 *
 * @param token the JWT token to validate, must not be null
 * @return validation result containing status and error messages
 * @throws IllegalArgumentException if token is null or empty
 */
public ValidationResult validate(String token) { }
```

### Code Examples
```java
/**
 * Parses JSON configuration from a file.
 *
 * <p>Example usage:
 * {@snippet :
 * Config config = ConfigParser.parse("config.json");
 * String value = config.get("key");
 * }
 */
public Config parse(String filename) { }
```

### Tag Order
```java
/**
 * Description.
 *
 * @param name description
 * @return description
 * @throws ExceptionType description
 * @since version
 * @see reference
 * @deprecated reason
 */
```

## Related Skills

- `plan-marshall:ref-code-quality` - Language-agnostic code quality and documentation principles
- `pm-dev-java:java-core` - Core Java patterns
- `pm-dev-java:java-null-safety` - Null annotations in docs

## Templates

**JavaDoc class and method** — reference templates for documentation structure:
```text
Call the `read` tool with `{ filePath: "templates/javadoc-class.java.tmpl" }` before continuing.
```

Contains both class-level and method-level JavaDoc patterns with all standard tags.

## Standards Reference

| Standard | Purpose |
|----------|---------|
| javadoc-core.md | Core principles and mandatory requirements |
| javadoc-class-documentation.md | Class-level documentation |
| javadoc-method-documentation.md | Method-level documentation |
| javadoc-code-examples.md | @snippet and @code patterns |
| javadoc-error-reference.md | Error troubleshooting |
