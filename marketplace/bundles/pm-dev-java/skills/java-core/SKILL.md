---
name: java-core
description: Core Java development standards for patterns, modern features, and performance optimization
user-invocable: true
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Java Core Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Core Java development standards for general Java projects. This skill covers fundamental patterns, modern Java features, and performance optimization.

## Prerequisites

This skill applies to Java 21+ projects with no CUI-specific dependencies.

## Workflow

### Step 1: Load Core Patterns

Load this standard for any Java implementation work.

```
Read: standards/java-core-patterns.md
```

This provides foundational rules for:
- Package and class structure
- Method design and command-query separation
- Parameter objects and method complexity
- Code organization principles

### Step 2: Load Additional Standards (As Needed)

**Java 17 Features** (load for new code):
```
Read: standards/java-17-features.md
```

Use when: Writing new code or modernizing existing code. Covers records, switch expressions, pattern matching for instanceof, sealed classes, text blocks, streams, and Optional usage.

**Java 21 Features** (load for Java 21+ code):
```
Read: standards/java-21-features.md
```

Use when: Using Java 21 features — pattern matching in switch, record patterns, sequenced collections, and virtual threads.

**Performance Patterns** (load for optimization work):
```
Read: standards/java-performance-patterns.md
```

Use when: Optimizing code or designing high-performance components. Covers string handling, autoboxing, collection sizing, thread safety, exception handling, and logging performance.

## Key Rules Summary

### Package Structure
```java
// CORRECT - Feature-based organization
de.example.portal.authentication     // Authentication feature
de.example.portal.configuration      // Configuration feature
de.example.portal.user.management    // User management feature
```

### Command-Query Separation
```java
// Query - returns value, no side effects
public boolean isValid() {
    return status == Status.VALID;
}

// Command - modifies state, returns void
public void markAsInvalid() {
    this.status = Status.INVALID;
}
```

### Parameter Objects (3+ parameters)
```java
// CORRECT - Multiple related parameters grouped
public record ValidationRequest(
    String tokenId,
    Set<String> expectedScopes,
    Duration maxAge,
    String issuer
) {}

public boolean validate(ValidationRequest request) {
    // Clear, organized parameters
}
```

## Related Skills

- `pm-dev-java:java-null-safety` - JSpecify null annotations
- `pm-dev-java:java-lombok` - Lombok patterns
- `pm-dev-java:junit-core` - JUnit 5 testing patterns
- `pm-dev-java:javadoc` - JavaDoc documentation standards

## Standards Reference

| Standard | Purpose |
|----------|---------|
| java-core-patterns.md | Code organization and design principles |
| java-17-features.md | Records, switch expressions, sealed classes, streams, Optional |
| java-21-features.md | Pattern matching in switch, record patterns, sequenced collections, virtual threads |
| java-performance-patterns.md | String handling, autoboxing, collections, thread safety, exceptions, logging |
