---
name: java-null-safety
description: JSpecify null safety annotations with @NullMarked, @Nullable, and package-level configuration
user-invocable: false
---

# Java Null Safety Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Null safety standards using JSpecify annotations for consistent, compiler-verifiable null contracts.

## Prerequisites

This skill requires JSpecify annotations:
- `org.jspecify:jspecify` (NullMarked, Nullable, NonNull)

## Maven Dependency

```xml
<dependency>
    <groupId>org.jspecify</groupId>
    <artifactId>jspecify</artifactId>
</dependency>
```

## Workflow

### Step 1: Load Core Null Safety Standards

**Important**: Load this standard for any null safety work — package configuration, annotations, API return types.

```
Read: standards/null-safety-core.md
```

This provides rules for:
- `@NullMarked` package-level configuration with `package-info.java` syntax
- Core annotations (`@NullMarked`, `@Nullable`, `@NonNull`)
- API return type guidelines (non-null default, Optional, never `@Nullable` returns)
- Required imports

### Step 2: Load Implementation Patterns (As Needed)

**Load for implementation work** — writing null-safe code, collections, testing, migration:

```
Read: standards/null-safety-patterns.md
```

This provides rules for:
- Null-safe implementation patterns with and without `@NullMarked`
- Nullable parameter handling and overload alternatives
- Collections and generics null safety
- Unit testing null contracts
- Migration strategy for new and existing code

## Key Rules Summary

| Rule | Guidance |
|------|----------|
| Package default | Always add `@NullMarked` to `package-info.java` |
| Return types | Never use `@Nullable` — use `Optional<T>` instead |
| Parameters | Use `@Nullable` sparingly; prefer method overloads |
| API boundaries | `Objects.requireNonNull()` for defensive checks |
| Collections | `List<@Nullable String>` for nullable elements |

## Templates

**package-info.java** — starting point for new packages with `@NullMarked`:
```
Read: templates/package-info.java.tmpl
```

Replace `${YEAR}`, `${PACKAGE}`, and `${PACKAGE_DESCRIPTION}` with actual values. The import-after-package ordering is critical — see `standards/null-safety-core.md` for why.

## Quality Rules

- Package has `@NullMarked` in `package-info.java`
- No `@Nullable` used for return types (use `Optional` instead)
- Nullable parameters documented and justified
- Defensive null checks at API boundaries
- Unit tests verify non-null contracts (see `pm-dev-java:junit-core` skill)
- Static analysis configured and passing
- JavaDoc documents null-safety contract
- Collections specify element nullability if needed

## Related Skills

- `pm-dev-java:java-core` - Core Java patterns
- `pm-dev-java:java-lombok` - Lombok patterns (interop with null safety)
