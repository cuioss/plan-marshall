---
name: java-core
description: Core Java development standards for patterns, modern features, and performance optimization
user-invokable: true
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

## Related Skills

- `pm-dev-java:java-null-safety` - JSpecify null annotations
- `pm-dev-java:java-lombok` - Lombok patterns
- `pm-dev-java:junit-core` - JUnit 5 testing patterns
- `pm-dev-java:javadoc` - JavaDoc documentation standards
