---
name: junit-integration
description: Maven integration testing with Failsafe plugin, IT naming conventions, and profile configuration
user-invocable: false
mode: knowledge
---

# JUnit Integration Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Integration testing standards for Maven projects using the Failsafe plugin. This skill covers test separation, naming conventions, and profile configuration.

## Prerequisites

This skill applies to Maven projects:
- `maven-surefire-plugin` (unit tests)
- `maven-failsafe-plugin` (integration tests)

## Key Principles

### Test Separation

Integration tests should be completely separated from unit tests to ensure:

* Fast unit test execution during regular development builds
* Isolated integration test execution that can be run independently
* Clear distinction between test types for CI/CD pipelines
* Proper resource management for integration tests requiring external dependencies

### Maven Plugin Usage

* **Maven Surefire Plugin**: Handles unit tests during the `test` phase
* **Maven Failsafe Plugin**: Handles integration tests during the `integration-test` and `verify` phases

## Naming Conventions

Integration tests must follow Maven's standard naming conventions:

* `**/*IT.java` - Integration Test classes
* `**/*ITCase.java` - Alternative integration test naming

```java
// Preferred: Correct naming
public class TokenKeycloakIT extends KeycloakITBase {
    // Integration test implementation
}

// Avoid: Incorrect naming (would be treated as unit test)
public class TokenKeycloakITTest extends KeycloakITBase {
    // This follows unit test naming convention
}
```

## Maven Configuration

### Base Configuration

Configure surefire plugin to exclude integration tests from normal builds:

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <excludes>
            <exclude>**/*IT.java</exclude>
            <exclude>**/*ITCase.java</exclude>
        </excludes>
    </configuration>
</plugin>
```

### Integration Test Profile

Create a dedicated profile for integration tests:

```xml
<profile>
    <id>integration-tests</id>
    <build>
        <plugins>
            <!-- Skip Surefire Plugin (unit tests) when running integration tests -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <configuration>
                    <skipTests>true</skipTests>
                </configuration>
            </plugin>
            <!-- Maven Failsafe Plugin for Integration Tests -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-failsafe-plugin</artifactId>
                <configuration>
                    <includes>
                        <include>**/*IT.java</include>
                        <include>**/*ITCase.java</include>
                    </includes>
                </configuration>
                <executions>
                    <execution>
                        <id>integration-test</id>
                        <goals>
                            <goal>integration-test</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>verify</id>
                        <goals>
                            <goal>verify</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</profile>
```

## Critical Configuration Details

### Why Skip Unit Tests in Integration Profile

**Problem**: Without explicit unit test skipping, the integration-tests profile would run:
1. All unit tests (via surefire)
2. All integration tests (via failsafe)

**Solution**: Configure surefire to skip tests when the integration-tests profile is active.

### The Profile Skip Does Not Reach Upstream Modules

The `<skipTests>true</skipTests>` above skips the unit tests of the module that declares the profile — and of no other. In a multi-module build where the integration tests live in their own module, the usual invocation adds `-am` so the application module is built first:

```text
verify -Pintegration-tests -pl integration-tests -am
```

`-am` puts the application module into the reactor, and that module does not declare the profile's surefire skip. Its whole unit suite therefore runs a second time inside the integration-test lane, in addition to the lane that exists to run it. The duplication is invisible in the result — both runs are green — and shows up only as lane duration.

Split the lane into two invocations instead — the first builds and installs the upstream modules without running any test, the second runs the integration module alone against the installed artifacts:

```text
install -DskipTests -DskipITs -pl integration-tests -am
verify -Pintegration-tests -pl integration-tests
```

Check the result in the lane's log, not by its colour: it must show no surefire execution for the application module, and the failsafe test count must equal the count before the split.

`-DskipTests` stops surefire and nothing else. Every other check bound to a phase before `install` still runs in that first invocation — typically a frontend build's dependency install, lint, format check and JavaScript tests in a module that carries web resources. Where another lane gates those, switch them off in the install step with the plugin's own skip properties (for `frontend-maven-plugin`: `-Dskip.installnodenpm -Dskip.npm`), and confirm three things before relying on it:

* the log of the install step reports each of those executions as skipped;
* none of them produces a file the packaged artifact needs — a skipped bundling step yields an artifact without its web resources;
* the lane that gates them still runs them, unchanged.

### Failsafe Goals

Both goals are required for proper integration test execution:

* `integration-test`: Runs the integration tests
* `verify`: Checks the results and fails the build if tests failed

### An Include Pattern Can Match Nothing and Stay Green

Failsafe treats "no test matched" as success. An `<include>` that is narrower than the naming convention — a package-qualified pattern such as `**/integration/**/*IT.java` — can stop matching after a package move or a plugin update, and the lane then reports `Tests run: 0` with `BUILD SUCCESS`. A green lane that ran nothing is worse than a red one.

* Prefer the unqualified `**/*IT.java`; narrow by `<excludes>` or by tag, where a miss is visible as a test that ran when it should not have.
* Treat the failsafe test count as part of the lane's result: a lane that is expected to run integration tests and reports zero has failed.
* Let the build enforce that: `<failIfNoTests>true</failIfNoTests>` in the Failsafe configuration makes the `verify` goal fail when no integration test ran. Set it in the module that holds the integration tests, not in a parent POM, where it would fail every module that has none.

## Build Commands

Build commands are resolved via the architecture API — never hardcode build tool invocations.

- **Unit tests only**: `architecture resolve --command module-tests`
- **Full verify**: `architecture resolve --command verify`
- **Integration tests**: `architecture resolve --command integration-tests`

### Build Verification

Ensure both scenarios work correctly:

1. **Normal Build**: Should only run unit tests
2. **Integration Profile**: Should skip unit tests and only run integration tests

## JUnit 5 Nested Tests

Integration tests can use JUnit 5 nested test classes. The naming convention applies to the outer class:

```java
public class TokenKeycloakIT {

    @Nested
    class AccessTokenTests {
        @Test
        void shouldValidateAccessToken() {
            // Test implementation
        }
    }

    @Nested
    class IdTokenTests {
        @Test
        void shouldValidateIdToken() {
            // Test implementation
        }
    }
}
```

## Step 2: Load Additional Standards (As Needed)

**External Integration Testing** (load for Docker-based IT):
```text
Read: standards/external-integration-testing.md
```

Use when: Implementing external API integration tests with Docker containers, REST Assured over HTTPS, script-based lifecycle management, and management interface testing.

**Integration Test Lane Duration** (load when an integration-test lane is slow):
```text
Read: standards/integration-test-duration.md
```

Use when: Shortening an integration-test lane — running wall-clock-bound classes concurrently (a tagged Failsafe execution, or one JVM with classes opted in), sharing one wait between tests that observe the same event, or building fixture images outside the lane's critical path.

## Common Pitfalls

### FAIL Incorrect Naming Convention

```java
// Wrong - will be treated as unit test
public class TokenKeycloakITTest { }
```

### FAIL Missing Surefire Skip Configuration

Without `<skipTests>true</skipTests>` in the integration-tests profile, both unit and integration tests will run.

### FAIL Unit Suite Re-Run Through `-am`

The profile's surefire skip covers only the module that declares it. With `-am`, every upstream module runs its unit tests again inside the integration-test lane — see "The Profile Skip Does Not Reach Upstream Modules" above.

### FAIL Include Pattern That Matches Nothing

A package-qualified failsafe `<include>` that matches no class leaves the lane green with zero tests run — see "An Include Pattern Can Match Nothing and Stay Green" above.

### FAIL Wrong Maven Goal

Integration tests require the `verify` goal (runs failsafe). The `test` goal only runs surefire (unit tests) — it will not execute `*IT.java` files even with the integration-tests profile active.

### FAIL Missing Failsafe Executions

Without proper `<executions>` configuration, failsafe tests might not run or results might not be verified.

## Verify

- Normal build excludes integration tests
- Integration profile skips unit tests and only runs integration tests
- The integration-test lane's log shows no surefire execution for an upstream module
- The failsafe test count is the expected one, and never zero
- CI/CD workflow includes integration test execution
- Integration test naming follows Maven conventions (`*IT.java`)
- Both surefire exclusions and failsafe inclusions are properly configured

## Related Skills

- `pm-dev-java:junit-core` - JUnit 5 core patterns, including the surefire fork policy for the unit suite
- `pm-dev-java:java-cdi` - CDI patterns and container configuration

## Additional Resources

* [Maven Surefire Plugin Documentation](https://maven.apache.org/surefire/maven-surefire-plugin/)
* [Maven Failsafe Plugin Documentation](https://maven.apache.org/surefire/maven-failsafe-plugin/)
* [Maven Build Lifecycle](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html)
