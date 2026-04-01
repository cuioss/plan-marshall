---
name: java-lombok
description: Lombok patterns including @Delegate, @Builder, @UtilityClass for reducing boilerplate
user-invocable: false
---

# Java Lombok Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Lombok standards for reducing boilerplate code while maintaining code quality and testability.

## Prerequisites

This skill applies to Java projects using [Project Lombok](https://projectlombok.org/) for boilerplate reduction.

## Workflow

### Step 1: Load Core Annotations

**Important**: Load this standard for any Lombok work involving `@Delegate`, `@Builder`, `@Value`, `@Data`, or `@UtilityClass`.

```
Read: standards/lombok-core-annotations.md
```

This provides rules for:
- `@Delegate` for delegation over inheritance
- `@Builder` with records vs classes (including `@Builder.Default` limitations)
- `@Value` vs records decision guidance
- `@Data` for mutable objects
- `@UtilityClass` for static method classes

### Step 2: Load Canonical Methods (As Needed)

**Load for entity/bean work** involving `@EqualsAndHashCode`, `@ToString`, `@Getter`, `@Setter`:

```
Read: standards/lombok-canonical-methods.md
```

This provides rules for:
- `@EqualsAndHashCode` with business keys and inheritance
- `@ToString` with sensitive field exclusion
- `@Getter` / `@Setter` for mutable beans (JPA entities)
- Common pitfalls table

## Key Decision Guide

| Scenario | Recommendation |
|----------|---------------|
| Immutable data carrier | Java record (not `@Value`) |
| 4+ constructor parameters | `@Builder` |
| Need `@Builder.Default` or `toBuilder` | Class with `@Builder` |
| Delegation over inheritance | `@Delegate` |
| JPA entity with business key | `@Getter` + `@Setter` + `@EqualsAndHashCode(of = ...)` |
| Static utility methods | `@UtilityClass` |

## Related Skills

- `pm-dev-java:java-core` - Core Java patterns, records migration
- `pm-dev-java:java-null-safety` - Null safety with Lombok
