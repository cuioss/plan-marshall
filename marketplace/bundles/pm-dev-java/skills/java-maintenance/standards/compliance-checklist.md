# Standards Compliance Checklist

Verification checklist for Java code after maintenance or refactoring work. Each item references the authoritative standard — consult the linked skill for detailed rules.

**Verification levels**: [OK] Compliant | [WARNING] Needs work | [N/A] Not applicable

## Package Organization
**Standard**: `pm-dev-java:java-core` → `java-core-patterns.md`

- [ ] Feature-based packages (not layer-based)
- [ ] `package-info.java` present with `@NullMarked`
- [ ] Related classes grouped in same package

## Class Design
**Standard**: `pm-dev-java:java-core` → `java-core-patterns.md`

- [ ] Single Responsibility — one clear reason to change
- [ ] Appropriate access modifiers (public only for API)
- [ ] Reasonable size (< 500 lines, < 30 methods)
- [ ] Constructor injection, no circular dependencies

## Method Design
**Standard**: `plan-marshall:dev-general-code-quality`, `pm-dev-java:java-maintenance` → `refactoring-triggers.md`

- [ ] Methods < 50 lines (refactor at 60+)
- [ ] Parameters ≤ 3 (use parameter objects for 3+)
- [ ] Cyclomatic complexity < 15
- [ ] Cognitive complexity < 15 (SonarQube `java:S3776`)
- [ ] Nesting depth ≤ 3 (use guard clauses)
- [ ] Command-query separation respected

## Null Safety
**Standard**: `pm-dev-java:java-null-safety`

- [ ] `@NullMarked` in `package-info.java`
- [ ] No `@Nullable` on return types (use `Optional` instead)
- [ ] `Objects.requireNonNull()` at API boundaries
- [ ] Tests verify non-null contracts

## Exception Handling
**Standard**: `pm-dev-java:java-core` → `java-core-patterns.md`

- [ ] Specific exception types (no `catch(Exception)`, no `throw new RuntimeException()`)
- [ ] Exception causes preserved with chaining
- [ ] Meaningful messages with context

## Modern Java Features
**Standard**: `pm-dev-java:java-core` → `java-17-features.md`, `java-21-features.md`

- [ ] Records for immutable data carriers
- [ ] Switch expressions (not statements)
- [ ] Text blocks for multi-line strings
- [ ] `List.of()`, `Set.of()`, `Map.of()` for immutable collections

## Lombok Usage
**Standard**: `pm-dev-java:java-lombok`

- [ ] `@Builder` for types with 4+ parameters
- [ ] Records preferred over `@Value`
- [ ] `@Delegate` for composition over inheritance

## Documentation
**Standard**: `pm-dev-java:javadoc`

- [ ] All public classes and methods have JavaDoc
- [ ] `@param`, `@return`, `@throws` tags present
- [ ] Documentation matches current code behavior

## Unused Code

- [ ] No unused private fields or methods
- [ ] No commented-out code blocks
- [ ] No unreachable statements
- [ ] Framework-required "unused" code documented

## Build and Tests
**Standard**: `pm-dev-java:junit-core`

- [ ] Build passes (`verify`)
- [ ] All tests pass (`module-tests`)
- [ ] Coverage ≥ 80% line and branch (`coverage`)
- [ ] Static analysis passes (`quality-gate`)

## Deviation Documentation

When standards cannot be met, document the reason:

```java
@SuppressWarnings("unused") // Required by JPA specification
private Long id;
```
