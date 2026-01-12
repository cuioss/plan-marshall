# DSL-Style Nested Constants Pattern

## Purpose

This document defines a design pattern for organizing related constants in a hierarchical, discoverable manner using nested static classes. This pattern is particularly useful when dealing with a large number of related constants that can be logically grouped by multiple dimensions.

## Key Characteristics

* **Hierarchical Organization**: Constants are organized in nested static classes, each representing a dimension or category
* **Type Safety**: Each level in the hierarchy is a proper type, enabling IDE support and compile-time checks
* **Discoverable API**: The structure guides users through available options via IDE auto-completion
* **Immutable**: All elements are final and preferably immutable
* **Self-Documenting**: The hierarchy itself documents the relationship between constants

## Implementation Guidelines

* Use `@UtilityClass` for all levels to prevent instantiation
* Make all classes and constants `public static final`
* Use meaningful names for each level that represent the dimension they categorize
* Consider using interfaces to define common behavior across similar categories
* Keep hierarchy depth reasonable (3-4 levels maximum)
* Use consistent naming conventions across all levels
* Document the purpose of each category level
* Consider using enums for the lowest level when appropriate
* Maintain consistent ordering within each level

## Basic Example Structure

```java
@UtilityClass
public final class ModuleConstants {

    @UtilityClass
    public static final class CATEGORY_A {

        @UtilityClass
        public static final class TYPE_1 {
            public static final Item CONSTANT_1 = ...;
            public static final Item CONSTANT_2 = ...;
        }

        @UtilityClass
        public static final class TYPE_2 {
            public static final Item CONSTANT_3 = ...;
        }
    }

    @UtilityClass
    public static final class CATEGORY_B {
        // Similar structure
    }
}
```

## Usage Pattern

```java
// Instead of flat structure:
ModuleConstants.CONSTANT_1  // Hard to discover, no context

// Use hierarchical structure:
ModuleConstants.CATEGORY_A.TYPE_1.CONSTANT_1  // Clear context, discoverable
```

## Logging System Example

For logging systems, the recommended structure organizes messages by log level. For complete logging implementation details and best practices, see [logging-standards.md](logging-standards.md).

### Minimal Structure Example

```java
@UtilityClass
public final class ModuleLogMessages {
    public static final String PREFIX = "MODULE";

    @UtilityClass
    public static final class INFO {
        public static final LogRecord USER_LOGIN = LogRecordModel.builder()
            .template("User %s logged in successfully")
            .prefix(PREFIX)
            .identifier(1)
            .build();
        // Additional INFO messages...
    }

    @UtilityClass
    public static final class WARN {
        // Warning messages (identifiers 100-199)
    }

    @UtilityClass
    public static final class ERROR {
        // Error messages (identifiers 200-299)
    }
}
```

**For complete LogMessages implementation**, including:
- Full identifier range allocation
- All log level nested classes
- Usage examples with CuiLogger
- Static import patterns
- Testing strategies

See [logging-standards.md](logging-standards.md)

## Configuration System Example

Organizing configuration keys by feature and environment:

```java
@UtilityClass
public final class ConfigKeys {

    @UtilityClass
    public static final class AUTHENTICATION {

        @UtilityClass
        public static final class JWT {
            public static final String ISSUER = "auth.jwt.issuer";
            public static final String SECRET_KEY = "auth.jwt.secret";
            public static final String VALIDITY = "auth.jwt.validity.seconds";
        }

        @UtilityClass
        public static final class OAUTH2 {
            public static final String CLIENT_ID = "auth.oauth2.client.id";
            public static final String CLIENT_SECRET = "auth.oauth2.client.secret";
            public static final String REDIRECT_URI = "auth.oauth2.redirect.uri";
        }
    }

    @UtilityClass
    public static final class DATABASE {
        public static final String URL = "db.url";
        public static final String USERNAME = "db.username";
        public static final String PASSWORD = "db.password";
        public static final String POOL_SIZE = "db.pool.size";
    }
}

// Usage
String issuer = config.get(ConfigKeys.AUTHENTICATION.JWT.ISSUER);
String dbUrl = config.get(ConfigKeys.DATABASE.URL);
```

## Error Code System Example

Organizing error codes by module, severity, and subsystem:

```java
@UtilityClass
public final class ErrorCodes {

    @UtilityClass
    public static final class AUTHENTICATION {

        @UtilityClass
        public static final class CRITICAL {
            public static final String INVALID_CREDENTIALS = "AUTH-C-001";
            public static final String ACCOUNT_LOCKED = "AUTH-C-002";
            public static final String TOKEN_EXPIRED = "AUTH-C-003";
        }

        @UtilityClass
        public static final class WARNING {
            public static final String WEAK_PASSWORD = "AUTH-W-001";
            public static final String APPROACHING_LIMIT = "AUTH-W-002";
        }
    }

    @UtilityClass
    public static final class PAYMENT {

        @UtilityClass
        public static final class CRITICAL {
            public static final String PAYMENT_FAILED = "PAY-C-001";
            public static final String INSUFFICIENT_FUNDS = "PAY-C-002";
        }
    }
}

// Usage
throw new AuthenticationException(ErrorCodes.AUTHENTICATION.CRITICAL.INVALID_CREDENTIALS);
```

## Resource Bundle Example

Organizing localized message keys:

```java
@UtilityClass
public final class MessageKeys {

    @UtilityClass
    public static final class VALIDATION {

        @UtilityClass
        public static final class USER {
            public static final String USERNAME_REQUIRED = "validation.user.username.required";
            public static final String EMAIL_INVALID = "validation.user.email.invalid";
            public static final String AGE_MIN = "validation.user.age.min";
        }

        @UtilityClass
        public static final class TOKEN {
            public static final String EXPIRED = "validation.token.expired";
            public static final String INVALID = "validation.token.invalid";
        }
    }

    @UtilityClass
    public static final class MESSAGES {

        @UtilityClass
        public static final class SUCCESS {
            public static final String LOGIN = "messages.success.login";
            public static final String LOGOUT = "messages.success.logout";
        }

        @UtilityClass
        public static final class ERROR {
            public static final String GENERAL = "messages.error.general";
            public static final String NOT_FOUND = "messages.error.not.found";
        }
    }
}

// Usage
String message = bundle.getString(MessageKeys.VALIDATION.USER.EMAIL_INVALID);
```

## Common Use Cases

* **Logging Systems**: Organizing messages by module, level, and component
* **Configuration**: Grouping settings by feature, environment, and type
* **Error Codes**: Categorizing by module, severity, and subsystem
* **Resource Bundles**: Organizing by language, region, and resource type
* **API Endpoints**: Grouping by version, resource, and operation
* **Permissions**: Categorizing by module, role, and action

## Benefits

* **Improved Code Organization**: Clear structure for related constants
* **Better Maintainability**: Easy to add new categories without changing existing code
* **Enhanced Developer Experience**: IDE auto-completion guides developers through hierarchy
* **Type Safety**: Compile-time verification of constant usage
* **Documentation**: Structure itself documents relationships
* **Refactoring Support**: IDEs can safely rename categories and constants
* **Consistency**: Enforces consistent naming and organization

## Best Practices

### 1. Use Consistent Naming

```java
// ✅ Good - consistent UPPER_CASE for all levels
ModuleLogMessages.INFO.USER_LOGIN
ModuleLogMessages.ERROR.DATABASE_ERROR

// ❌ Bad - inconsistent naming
ModuleLogMessages.Info.userLogin  // Mixed case
```

### 2. Keep Hierarchy Shallow

```java
// ✅ Good - 3 levels
ConfigKeys.AUTHENTICATION.JWT.ISSUER

// ❌ Bad - too deep
ConfigKeys.PRODUCTION.EUROPE.GERMANY.BERLIN.DATACENTER_1.AUTH.JWT.ISSUER
```

### 3. Document Each Level

```java
/**
 * Authentication module log messages.
 */
@UtilityClass
public static final class AUTHENTICATION {

    /**
     * Informational messages about successful operations.
     */
    @UtilityClass
    public static final class INFO {
        // Messages
    }
}
```

### 4. Use Static Imports Wisely

```java
// ✅ Good - import category level
import static com.example.ModuleLogMessages.INFO;
import static com.example.ModuleLogMessages.ERROR;

LOGGER.info(INFO.USER_LOGIN, username);
LOGGER.error(ERROR.DATABASE_ERROR, message);

// ❌ Bad - importing individual constants loses context
import static com.example.ModuleLogMessages.INFO.USER_LOGIN;
import static com.example.ModuleLogMessages.ERROR.DATABASE_ERROR;

LOGGER.info(USER_LOGIN, username);  // Less clear without INFO context
```

### 5. Group Related Constants

```java
// ✅ Good - related constants grouped
@UtilityClass
public static final class TIMEOUTS {
    public static final Duration CONNECT = Duration.ofSeconds(5);
    public static final Duration READ = Duration.ofSeconds(30);
    public static final Duration WRITE = Duration.ofSeconds(30);
}

// ❌ Bad - scattered constants
public static final Duration TIMEOUT_1 = Duration.ofSeconds(5);
public static final Duration SOME_OTHER_CONFIG = ...;
public static final Duration TIMEOUT_2 = Duration.ofSeconds(30);
```

## Quality Checklist

- [ ] @UtilityClass used for all levels
- [ ] All classes and constants are public static final
- [ ] Hierarchy depth is reasonable (≤ 4 levels)
- [ ] Consistent naming conventions used
- [ ] Each category level is documented
- [ ] Related constants are grouped together
- [ ] Static imports used at category level
- [ ] Type-safe constants used where possible
- [ ] Clear, self-documenting structure
- [ ] IDE auto-completion works effectively
