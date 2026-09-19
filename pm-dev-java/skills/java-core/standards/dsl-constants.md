# DSL-Style Nested Constants Pattern

Design pattern for organizing related constants hierarchically using nested static classes. Provides IDE auto-completion, type safety, and self-documenting structure.

## Key Characteristics

* **Hierarchical Organization**: Constants organized in nested `@UtilityClass` classes
* **Discoverable API**: IDE auto-completion guides developers through the hierarchy
* **Type Safety**: Compile-time verification of constant usage
* **Immutable**: All elements are `public static final`

## Implementation

Use `@UtilityClass` for all levels. Keep hierarchy depth at 3–4 levels maximum.

```java
@UtilityClass
public final class ConfigKeys {

    @UtilityClass
    public static final class Authentication {

        @UtilityClass
        public static final class Jwt {
            public static final String ISSUER = "auth.jwt.issuer";
            public static final String SECRET_KEY = "auth.jwt.secret";
            public static final String VALIDITY = "auth.jwt.validity.seconds";
        }

        @UtilityClass
        public static final class OAuth2 {
            public static final String CLIENT_ID = "auth.oauth2.client.id";
            public static final String CLIENT_SECRET = "auth.oauth2.client.secret";
        }
    }

    @UtilityClass
    public static final class Database {
        public static final String URL = "db.url";
        public static final String POOL_SIZE = "db.pool.size";
    }
}

// Usage — clear context, discoverable
String issuer = config.get(ConfigKeys.Authentication.Jwt.ISSUER);
```

## Logging Messages Example

For logging systems, organize message templates by log level:

```java
@UtilityClass
public final class ModuleLogMessages {

    @UtilityClass
    public static final class INFO {
        public static final String USER_LOGIN = "User %s logged in successfully";
    }

    @UtilityClass
    public static final class ERROR {
        public static final String AUTH_FAILED = "Authentication failed for %s: %s";
    }
}
```

## Common Use Cases

* Configuration keys (by feature and subsystem)
* Error codes (by module and severity)
* Resource bundle keys (by domain and category)
* Log message templates (by level)

## Best Practices

### Use Static Imports at Category Level

```java
import static com.example.ModuleLogMessages.INFO;
import static com.example.ModuleLogMessages.ERROR;

LOGGER.info(INFO.USER_LOGIN, username);  // Clear context preserved
```

### Naming Conventions

Choose one convention per hierarchy and apply consistently:
- `PascalCase` for category classes (e.g., `Authentication.Jwt`)
- `UPPER_CASE` for leaf categories (e.g., `INFO`, `ERROR`)
- `UPPER_SNAKE_CASE` for constants (e.g., `ISSUER`, `CLIENT_ID`)

### Document Each Level

```java
/** Authentication module configuration keys. */
@UtilityClass
public static final class Authentication {
    /** JWT-specific settings. */
    @UtilityClass
    public static final class Jwt { }
}
```
