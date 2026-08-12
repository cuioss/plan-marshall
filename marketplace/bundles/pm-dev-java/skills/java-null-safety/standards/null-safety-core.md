# Null Safety Core Standards

Core annotations, package-level configuration, and API return type guidelines using JSpecify.

## Required Imports

```java
import org.jspecify.annotations.NullMarked;
import org.jspecify.annotations.Nullable;
import org.jspecify.annotations.NonNull;
```

## Core Annotations

* `@NullMarked` - Marks a package or class where all types are non-null by default
* `@Nullable` - Marks a type as nullable (exception to @NullMarked default)
* `@NonNull` - Explicitly marks a type as non-null (only needed without @NullMarked)

## Package-Level Configuration (PREFERRED)

Always prefer `@NullMarked` in `package-info.java` for consistent null-safety across the entire package.

### Correct package-info.java Structure

The `package-info.java` file has a **unique syntax** that differs from regular Java classes:

```java
// package-info.java
/*
 * Copyright headers and license...
 */

/**
 * Token validation and authentication services.
 *
 * <p>All types in this package are non-null by default due to {@code @NullMarked}.
 * Use {@code @Nullable} to explicitly mark nullable types.
 */
@NullMarked
package com.example.authentication;

import org.jspecify.annotations.NullMarked;
```

**CRITICAL: Unique package-info.java Syntax**

The structure is special and MUST follow this exact order:

1. **File header comment** (copyright, license)
2. **Package JavaDoc comment** (describes the package)
3. **Package annotations** (like `@NullMarked`)
4. **`package` declaration**
5. **`import` statements** (AFTER the package declaration)

**Why This Is Different:**

In regular Java classes, imports come BEFORE the class declaration:
```java
import java.util.List;  // Import first

public class MyClass {  // Then class
}
```

In `package-info.java`, imports come AFTER the package declaration:
```java
@NullMarked            // Annotation first
package com.example;   // Then package

import org.jspecify.annotations.NullMarked;  // Import last
```

This reverse ordering is the **Java Language Specification** requirement for package-info.java files. Placing imports before the package declaration will cause compilation errors.

**Benefits**:
* Consistent null-safety across entire package
* Less annotation noise (default is non-null)
* Clear contract for package APIs
* Easier to maintain

## API Return Type Guidelines

### Pattern 1: Guaranteed Non-Null Return (Default)

Methods return non-null by default with package-level `@NullMarked`:

```java
/**
 * Validates the JWT token and returns the result.
 *
 * @param token the token to validate, must not be null
 * @return validation result, never null
 */
public ValidationResult validate(String token) {
    // Implementation must ensure non-null return
    return new ValidationResult(token, checkSignature(token));
}
```

### Pattern 2: Optional Result

Use `Optional<T>` when the method may not have a result to return:

```java
/**
 * Finds a user by their unique identifier.
 *
 * @param userId the user identifier, must not be null
 * @return the user if found, or Optional.empty() if not found
 */
public Optional<User> findById(String userId) {
    User user = repository.get(userId);
    return Optional.ofNullable(user);
}
```

### CRITICAL RULE: Never Use @Nullable for Return Types

**NEVER** use `@Nullable` for return types. Either guarantee a non-null return or use Optional.

```java
// WRONG - Nullable returns are forbidden
public @Nullable ValidationResult validate(String token) {
    // Callers must null-check every time
}

// CORRECT - Guaranteed non-null
public ValidationResult validate(String token) {
    // Must return non-null
}

// CORRECT - Use Optional for "no result" scenarios
public Optional<ValidationResult> tryValidate(String token) {
    // Returns Optional.empty() when no result
}
```

## Null-Safety by Position

`Optional<T>` is a **return-type** idiom and nothing more; `@Nullable` marks every other position.
Applying the wrong one is the most common null-safety mistake: an author who has internalized "use
`Optional` for absence" and "never `@Nullable` for returns" — both correct in isolation — will reach
for `Optional<T>` as a field, a parameter, or a record component, where it is wrong.

| Position | Nullable case | Never |
|----------|---------------|-------|
| Return type | `Optional<T>` (absence), or a guaranteed non-null value | `@Nullable T` |
| Field | `@Nullable T` | `Optional<T>` |
| Parameter | `@Nullable T`, or a method overload (preferred) | `Optional<T>` |
| Record component | `@Nullable T` | `Optional<T>` |

The parameter and return rules are detailed above (§ "API Return Type Guidelines") and in
`standards/null-safety-patterns.md` (§ "Nullable Parameters"); the record-component rule is detailed
below (§ "Records and Null-Safety").

### Why `Optional` is a return type only

State the reasons — a rule without its reason gets re-litigated:

- **`Optional` is not `Serializable`.** A field or record component typed `Optional<T>` breaks
  serialization of its enclosing type; `@Nullable T` does not.
- **It costs an allocation and a dereference on every access.** A value held behind `Optional` is
  wrapped once and unwrapped on every read — overhead the `@Nullable` annotation, which is erased,
  never adds.
- **As a parameter it forces every caller to wrap.** A method taking `Optional<String>` makes each
  call site write `f(Optional.ofNullable(value))`; a `@Nullable` parameter — or, better, an overload —
  lets callers pass the value directly.

A return type is the one position where the caller *benefits* from the wrapper: it makes "no result"
explicit in the type and forces the caller to handle absence. Fields, parameters, and components get
none of that benefit — only the cost.

## Records and Null-Safety

A record component follows the field rule: a component that may be absent is `@Nullable T`, **never**
`Optional<T>`. The wrong turn here is `record Config(Optional<String> name)` — the exact anti-pattern
the positional rules above exist to prevent, and the shape a reader who knows only the return-type
rule will actually produce.

### The compact constructor

A record's compact constructor is the one place to **validate, normalize, and defensively copy**. Each
component is assigned **once**, from the (possibly adjusted) constructor parameter — do not reassign
after that:

```java
public record TokenConfig(String issuer, @Nullable Duration validity, Set<String> scopes) {
    public TokenConfig {
        // validate
        if (issuer == null || issuer.isBlank()) {
            throw new IllegalArgumentException("issuer is required");
        }
        // normalize / default (see below)
        validity = validity != null ? validity : Duration.ofHours(1);
        // defensively copy
        scopes = Set.copyOf(scopes);
    }
}
```

### Defaulting without a builder-default annotation

`@Builder.Default` does not work on record components (see `pm-dev-java:java-lombok`). Default a
component in the compact constructor instead: normalize the incoming value and let the implicit
assignment take the result, as `validity` does above. No builder-default annotation is involved.

### Legitimate normalization vs reassignment gymnastics

Reassigning a component parameter in the compact constructor is legitimate **only** when it validates,
normalizes, or defensively copies a value the component should carry. It is **not** legitimate when it
exists solely to unwrap an `Optional` the component should never have held:

```java
// WRONG - the component should never have been Optional; the constructor does unwrap gymnastics
public record Config(Optional<String> name) {
    public Config {
        name = name == null ? Optional.empty() : name;   // gymnastics to make a null-Optional safe
    }
    // ...and every reader must call name.orElse(...) forever
}

// CORRECT - @Nullable component; normalize directly, read directly
public record Config(@Nullable String name) {
    public Config {
        name = name != null ? name : "anonymous";        // legitimate defaulting
    }
}
```

If a compact constructor's only job for a component is to turn `null` into `Optional.empty()` or to
re-wrap a value, the component is typed wrong — make it `@Nullable T`.
