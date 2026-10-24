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

- **`Optional` is not `Serializable`.** Under default Java serialization, a field or record component
  typed `Optional<T>` makes its enclosing type fail to serialize; a `@Nullable T` field does not.
- **It adds a wrapper object.** The value is boxed in an `Optional` — a heap allocation the JIT is not
  guaranteed to elide — and unwrapped on read, overhead a `@Nullable` field (whose annotation is
  erased) never carries.
- **As a parameter it forces every caller to wrap.** A method taking `Optional<String>` makes each
  call site write `f(Optional.ofNullable(value))`; a `@Nullable` parameter — or, better, an overload —
  lets callers pass the value directly.

A return type is the one position where the caller *benefits* from the wrapper: it makes "no result"
explicit in the type and forces the caller to handle absence. Fields, parameters, and components get
none of that benefit — only the cost.

## Records and Null-Safety

A record component follows the field rule: a component that may be absent is `@Nullable T`, **never**
`Optional<T>`. `@Nullable` propagates to the generated accessor, so `@Nullable String name` yields a
`name()` that is honestly nullable — whereas `Optional<String> name` yields a component that is not
`Serializable`, a `name()` every caller must unwrap, and a canonical constructor every caller must
feed `Optional.ofNullable(...)`. The wrong turn is `record Config(Optional<String> name)` — the exact
anti-pattern the positional rules above exist to prevent, and the shape a reader who knows only the
return-type rule will produce.

### The compact constructor

A record's compact constructor is the one place to **validate, normalize, and defensively copy**. Each
component is assigned **once**, from the (possibly adjusted) parameter — do not reassign after that.
Normalization must **preserve the component's declared nullness**: trim, canonicalize, or copy, but do
not quietly turn a `@Nullable` component into an always-non-null one — that makes the accessor's
`@Nullable` a lie (see "Defaulting" below):

```java
public record TokenConfig(String issuer, Set<String> scopes, @Nullable Duration validity) {
    public TokenConfig {
        // validate (issuer is non-null under @NullMarked)
        if (issuer.isBlank()) {
            throw new IllegalArgumentException("issuer is required");
        }
        // defensively copy — non-null stays non-null
        scopes = Set.copyOf(scopes);
        // validity is left as-is: absent means null, and validity() honestly returns @Nullable
    }
}
```

### Defaulting without a builder-default annotation

`@Builder.Default` does not work on record components (see `pm-dev-java:java-lombok`), so a default is
applied in code. **A defaulted component is never absent** — it always holds a value after
construction — so declare it **non-null** and apply the default to a nullable *input*, in a static
factory (or secondary constructor). The canonical component, and its accessor, stay non-null and
honest:

```java
public record RetryPolicy(int maxAttempts, Duration backoff) {   // backoff is non-null
    public RetryPolicy {
        Objects.requireNonNull(backoff, "backoff");
    }

    // the default lives here; the nullable input never reaches the component as null
    public static RetryPolicy of(int maxAttempts, @Nullable Duration backoff) {
        return new RetryPolicy(maxAttempts, backoff != null ? backoff : Duration.ofSeconds(1));
    }
}
```

Defaulting a `@Nullable` component inside the compact constructor is the trap to avoid: the component
reads `@Nullable` while never actually being null, so its accessor advertises an absence that cannot
happen. A value is either genuinely absent (`@Nullable` component, no default) **or** it has a default
(non-null component, default at the factory) — never annotated one way and behaving the other.

### Legitimate normalization vs reassignment gymnastics

Reassigning a component parameter is legitimate only when it validates, canonicalizes, or defensively
copies a value the component should carry — **without changing its nullness**. It is **not** legitimate
when it exists solely to unwrap an `Optional` the component should never have held:

```java
// WRONG - Optional component: not Serializable, every caller wraps, every reader unwraps
public record Config(Optional<String> name) { }
//   construct:  new Config(Optional.ofNullable(rawName))   // caller forced to wrap
//   read:       config.name().orElse("anonymous")          // reader forced to unwrap, everywhere

// CORRECT - @Nullable component: construct and read directly, absence is null
public record Config(@Nullable String name) { }
//   construct:  new Config(rawName)                         // pass the value (or null) directly
//   read:       config.name()                               // @Nullable String — honestly nullable
```

If a component exists only so a constructor can turn `null` into `Optional.empty()` or a reader can
call `.orElse(...)`, the component is typed wrong — make it `@Nullable T`.
