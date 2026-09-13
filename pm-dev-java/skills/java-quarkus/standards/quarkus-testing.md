# Quarkus Testing Standards

Quarkus-specific testing patterns. For general JUnit 5 patterns, see `pm-dev-java:junit-core`. For Maven Surefire/Failsafe configuration, see `pm-dev-java:junit-integration`.

## Required Dependencies

```xml
<dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-junit5</artifactId>
    <scope>test</scope>
</dependency>

<!-- REST Assured for HTTP testing in @QuarkusTest -->
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <scope>test</scope>
</dependency>

<!-- Quarkus-aware JaCoCo (replaces standard jacoco-maven-plugin) -->
<dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-jacoco</artifactId>
    <scope>test</scope>
</dependency>
```

The `quarkus-jacoco` dependency handles JaCoCo agent attachment for Quarkus's classloading model. Set `quarkus.jacoco.reuse-data-file=true` in test `application.properties` to accumulate coverage across test runs.

## @QuarkusTest — CDI Integration Tests

Starts the full Quarkus container. Use for tests that need CDI injection, configuration, or the full application context:

```java
@QuarkusTest
class TokenValidatorProducerTest {

    @Inject
    TokenValidator tokenValidator;

    @Test
    @DisplayName("Should produce working TokenValidator")
    void shouldProduceWorkingTokenValidator() {
        assertNotNull(tokenValidator);
        assertThrows(TokenValidationException.class,
            () -> tokenValidator.createAccessToken("invalid-token"));
    }
}
```

**Characteristics**:
- Full CDI context — `@Inject` works
- Full application lifecycle (startup/shutdown per test class)
- Slower than plain JUnit — use only when CDI context is needed
- For pure logic without CDI dependencies, use plain `@Test` without `@QuarkusTest`

## @QuarkusIntegrationTest — Packaged Application Tests

Tests the packaged application (JAR or native binary) as a black box. No CDI injection — test via HTTP only:

```java
@QuarkusIntegrationTest
class ApplicationSmokeIT {

    @Test
    @DisplayName("Should start and serve health endpoint")
    void shouldStartAndServeHealth() {
        given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("status", equalTo("UP"));
    }
}
```

**Characteristics**:
- No `@Inject` — application runs in a separate process
- Tests the actual packaged artifact
- Use for native image smoke tests and end-to-end HTTP verification
- Name with `*IT.java` suffix (runs via Failsafe in `verify` phase)

## Test Profiles

Override configuration per test class using `QuarkusTestProfile`:

```java
public class MockAuthProfile implements QuarkusTestProfile {

    @Override
    public Map<String, String> getConfigOverrides() {
        return Map.of(
            "auth.provider.url", "https://mock-auth.example.com",
            "auth.validation.enabled", "false"
        );
    }

    @Override
    public String getConfigProfile() {
        return "test";
    }
}

@QuarkusTest
@TestProfile(MockAuthProfile.class)
class AuthDisabledTest {
    // Tests run with overridden configuration
}
```

**Note**: Each unique `@TestProfile` causes a Quarkus container restart. Minimize the number of distinct profiles to keep test suites fast.

## REST Assured Patterns

REST Assured is auto-configured in `@QuarkusTest` to point at the test instance:

```java
@QuarkusTest
class UserResourceTest {

    @Test
    void shouldReturnUsers() {
        given()
            .when().get("/api/users")
            .then()
            .statusCode(200)
            .body("$.size()", greaterThan(0));
    }

    @Test
    void shouldCreateUser() {
        given()
            .contentType(ContentType.JSON)
            .body(new UserRequest("alice", "alice@example.com"))
            .when().post("/api/users")
            .then()
            .statusCode(201)
            .header("Location", containsString("/api/users/"));
    }
}
```

## Testing Health Checks

```java
@QuarkusTest
class DatabaseHealthCheckTest {

    @Inject
    DatabaseHealthCheck healthCheck;

    @Test
    @DisplayName("Should return UP when database is reachable")
    void shouldReturnUp() {
        HealthCheckResponse response = healthCheck.call();
        assertEquals(HealthCheckResponse.Status.UP, response.getStatus());
    }
}
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|---------|
| 0% coverage despite tests passing | JaCoCo agent not attached | Add `quarkus-jacoco` dependency; ensure `@{argLine}` in Surefire config |
| SonarQube shows no coverage | Report path mismatch | Set `sonar.coverage.jacoco.xmlReportPaths` to `${project.build.directory}/site/jacoco/jacoco.xml` |
| `@Inject` returns null in IT | Using `@QuarkusIntegrationTest` | No CDI injection — test via HTTP with REST Assured |
| Slow test suite | Too many distinct `@TestProfile` classes | Consolidate profiles; use plain JUnit for non-CDI tests |

## References

* [Quarkus Testing Guide](https://quarkus.io/guides/getting-started-testing)
