---
name: javadoc
description: JavaDoc documentation standards including class, method, and code example patterns, plus the documentation-accuracy review rules a code review cites
user-invocable: false
mode: knowledge
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
Read: standards/javadoc-core.md
```

This provides foundational rules for:
- Mandatory documentation requirements
- Clarity, completeness, and consistency principles
- Tag ordering standards

### Step 2: Load Specific Standards (As Needed)

**Class Documentation** (load for class-level docs):
```text
Read: standards/javadoc-class-documentation.md
```

Use when: Documenting classes, interfaces, enums, or annotations.

**Method Documentation** (load for method-level docs):
```text
Read: standards/javadoc-method-documentation.md
```

Use when: Documenting methods, including parameters, returns, and exceptions.

**Code Examples** (load for example snippets):
```text
Read: standards/javadoc-code-examples.md
```

Use when: Adding code examples to documentation using @snippet or @code.

**Error Reference** (load for troubleshooting):
```text
Read: standards/javadoc-error-reference.md
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
Read: templates/javadoc-class.java.tmpl
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

## Review Rules

The review rules of the java domain for documentation accuracy — what a code review looks for in changed JavaDoc. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../../../plan-marshall/skills/phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- A `@param` tag whose name no longer matches a parameter of the method, or a parameter the change added with no `@param`, so the documented contract describes an argument the method does not take.
- A `@throws` tag for an exception the method no longer throws, or a newly thrown checked or documented exception with no `@throws`, so a caller handles the wrong failure.
- A JavaDoc nullness or return claim ("never returns null", "returns an empty list when …") that the implementation contradicts, so a caller omits the check the actual return value needs.
- A `{@link}` or `@see` reference to a class or member the change renamed or removed, so the reference points nowhere and the JavaDoc build fails under doclint.
