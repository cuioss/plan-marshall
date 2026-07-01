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
