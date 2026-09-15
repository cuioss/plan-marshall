# Integration Testing Patterns

Integration tests verify interaction between components, external services, or container-managed resources. They run separately from unit tests.

## Naming Conventions

Maven Failsafe recognizes these patterns — naming determines which plugin runs the test:

| Pattern | Example | Plugin |
|---------|---------|--------|
| `*IT.java` | `TokenKeycloakIT.java` | Failsafe (integration) |
| `*ITCase.java` | `AuthFlowITCase.java` | Failsafe (integration) |
| `*Test.java` | `TokenValidatorTest.java` | Surefire (unit) |

```java
// Correct — runs as integration test
public class TokenKeycloakIT { }

// Wrong — *ITTest.java matches Surefire, not Failsafe
public class TokenKeycloakITTest { }
```

## Test Separation

Unit and integration tests serve different purposes and run at different build phases:

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| Speed | Milliseconds | Seconds to minutes |
| Dependencies | Mocked/stubbed | Real or containerized |
| Execution | Every build (`test` phase) | On demand or CI (`verify` phase) |
| Naming | `*Test.java` | `*IT.java`, `*ITCase.java` |

For Maven Surefire/Failsafe configuration, see `pm-dev-java:junit-integration`.

## Structure and Organization

Integration tests follow the same JUnit 5 patterns as unit tests (AAA, `@DisplayName`, generators). Use `@Nested` for grouping:

```java
@DisplayName("Keycloak Token Integration")
class TokenKeycloakIT {

    @Nested
    @DisplayName("Access Token Flow")
    class AccessTokenTests {
        @Test
        void shouldObtainAccessTokenWithClientCredentials() { }

        @Test
        void shouldRefreshExpiredAccessToken() { }

        @Test
        void shouldRejectInvalidClientCredentials() { }
    }

    @Nested
    @DisplayName("Token Introspection")
    class IntrospectionTests {
        @Test
        void shouldIntrospectActiveToken() { }

        @Test
        void shouldDetectRevokedToken() { }

        @Test
        void shouldHandleIntrospectionTimeout() { }
    }
}
```

## Lifecycle Management

Integration tests often require setup/teardown of external resources:

```java
class DatabaseIT {

    @BeforeAll
    static void startContainer() {
        // Start test container or embedded database
    }

    @AfterAll
    static void stopContainer() {
        // Stop and cleanup
    }

    @BeforeEach
    void resetState() {
        // Clear tables or reset test data between tests
    }
}
```

Use Awaitility (see `standards/testing-async-patterns.md`) when waiting for external services to become ready — never `Thread.sleep`.

## Related Skills

- `pm-dev-java:junit-integration` - Maven Failsafe/Surefire plugin configuration and profiles
- `pm-dev-java:java-quarkus` - Quarkus-specific integration testing with DevServices
