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

Accumulated data cannot show a loss: a line that a change stopped covering still reads as covered, from a run that preceded the change. Delete the data file, or run a clean build, before any before/after coverage comparison — see `pm-dev-java:junit-core` → `standards/coverage-analysis-pattern.md`.

### When the Report Comes From `jacoco-maven-plugin`

A build can carry `quarkus-jacoco` and still take its coverage from `jacoco-maven-plugin`: `prepare-agent` puts the agent on the Surefire `argLine`, the agent writes the data file, and `jacoco:report` builds the report from it. In that build the extension's own report is a second path nobody reads, and it is not free. At JVM exit the extension waits for its own data file; when that file is never written, every `@QuarkusTest` JVM pays the wait — in the order of ten seconds each — and leaves a timeout message in `target/jacoco-report/error.txt`.

Switch the extension's report off and keep the dependency:

```properties
quarkus.jacoco.report=false
```

Confirm on clean coverage data that per-class coverage is unchanged, and that `target/jacoco-report/error.txt` is no longer written.

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

### One Boot Per Profile Needs One JVM

Quarkus keeps the application running between test classes of the same profile, and orders the classes by profile so each profile boots once. Both hold only inside one JVM. Under Surefire's `reuseForks=false` every `@QuarkusTest` class starts its own JVM and boots the application again, whatever its profile.

Give the `@QuarkusTest` classes a Surefire execution of their own with one reused fork, selected by a JUnit tag, and leave the classes that need a JVM to themselves in an isolated execution. In an extension's deployment module the classes that register a `QuarkusExtensionTest` boot an application too and belong to the same group; the guard test has to recognise both forms. The configuration, the criteria for isolation and the guard test that keeps the split correct are in `pm-dev-java:junit-core` → `standards/test-fork-policy.md`.

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

This test proves what the check answers. It does not prove that an application gets the check.

### A Health Check Shipped by an Extension

A health check that lives in an extension's runtime module is a bean in a jar. A consuming application discovers it only when that jar is a bean archive (it carries a Jandex index or a `beans.xml`) or when the extension's deployment processor registers the class. When neither holds, the application starts, `/q/health` answers `{"status":"UP","checks":[]}`, and nothing fails — an injected-bean test inside the extension's own module passes all the while, because there the class is part of the application under test.

Register the checks in the processor, unremovable, because nothing injects a health check:

```java
@BuildStep
AdditionalBeanBuildItem healthChecks() {
    return AdditionalBeanBuildItem.builder()
            .addBeanClasses(BackendReadinessCheck.class, ValidatorLivenessCheck.class)
            .setUnremovable()
            .build();
}
```

Then guard it at both ends:

* A test of the build step asserts that the produced item names each health-check class.
* A test against an application that only *depends on* the extension asserts each check by name in `/q/health/ready` and `/q/health/live` — not the overall status alone, which is `UP` for an empty list. See `pm-dev-java:junit-integration` → `standards/external-integration-testing.md`, "Health/Metrics Testing".

Registering checks that were missing changes what consumers observe: readiness can now be `DOWN`, with HTTP 503, where it was always `UP`. Say so in the change description, and check every script and test that polls readiness for 200 — a start script, an end-to-end environment — against the time the checks need to turn `UP`.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|---------|
| 0% coverage despite tests passing | JaCoCo agent not attached | Add `quarkus-jacoco` dependency; ensure `@{argLine}` in Surefire config |
| SonarQube shows no coverage | Report path mismatch | Set `sonar.coverage.jacoco.xmlReportPaths` to `${project.build.directory}/site/jacoco/jacoco.xml` |
| `@Inject` returns null in IT | Using `@QuarkusIntegrationTest` | No CDI injection — test via HTTP with REST Assured |
| Slow test suite | Too many distinct `@TestProfile` classes | Consolidate profiles; use plain JUnit for non-CDI tests |
| Slow test suite, one application boot per class | `reuseForks=false` starts a JVM per `@QuarkusTest` class | Run the `@QuarkusTest` classes in one reused fork — see "One Boot Per Profile Needs One JVM" |
| Each `@QuarkusTest` JVM takes about ten seconds to exit; `target/jacoco-report/error.txt` holds a timeout | The `quarkus-jacoco` report waits for a data file this build never writes | Set `quarkus.jacoco.report=false` — see "When the Report Comes From `jacoco-maven-plugin`" |
| Coverage did not drop after a test was removed | Coverage data accumulated across runs | Delete the data file before comparing |
| `/q/health` reports `UP` with an empty `checks` list | An extension's health checks are not registered in the consuming application | Register them in the deployment processor — see "A Health Check Shipped by an Extension" |

## References

* [Quarkus Testing Guide](https://quarkus.io/guides/getting-started-testing)
