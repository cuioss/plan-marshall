# External Integration Testing Standards

## Purpose

Standards for implementing **external API integration tests** that test the complete application stack through published API interfaces using production-like configurations with Docker containers.

**Prerequisites**: For basic Maven Failsafe configuration and naming conventions, see `pm-dev-java:junit-integration` SKILL.md.

## Core Principles

### API-Only Testing

External integration tests **MUST** test only through published APIs, never through internal injection:

* **No Internal Injection**: Tests must not use framework-specific injection (`@Inject`, `@Autowired`)
* **External Client Perspective**: Tests simulate real client interactions
* **Protocol Compliance**: Use actual HTTP/HTTPS protocols
* **Container Isolation**: Application runs in separate process/container

### Production Equivalence

External integration tests **MUST** use production-equivalent configurations:

* **HTTPS Required**: All API tests use TLS with proper certificates
* **Management Interface**: Health/metrics via plain HTTP on separate port
* **Real Networking**: Actual TCP/IP communication, not in-memory
* **Container Runtime**: Application runs in Docker container
* **Resource Constraints**: Same memory/CPU limits as production

## Test Structure

### Directory Organization

```text
integration-tests/
├── pom.xml
├── docker-compose.yml
├── scripts/
│   ├── start-integration-container.sh
│   ├── stop-integration-container.sh
│   └── dump-service-logs.sh
└── src/test/java/
    └── integration/
        ├── BaseIntegrationTest.java
        └── *IT.java
```

## Maven Configuration

The integration test module does **not** build the application — it only builds Docker images and runs tests. The application build happens in the main application module.

### Module Properties

```xml
<properties>
    <skipITs>true</skipITs>           <!-- Disabled by default -->
    <test.https.port>10443</test.https.port>
    <test.management.port>19000</test.management.port>
    <sonar.skip>true</sonar.skip>     <!-- Exclude from Sonar analysis -->
</properties>
```

### Integration Test Profile

```xml
<profile>
    <id>integration-tests</id>
    <properties>
        <skipITs>false</skipITs>
    </properties>

    <build>
        <plugins>
            <!-- Docker lifecycle via scripts -->
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <executions>
                    <execution>
                        <id>start-integration-app</id>
                        <phase>pre-integration-test</phase>
                        <goals><goal>exec</goal></goals>
                        <configuration>
                            <executable>./scripts/start-integration-container.sh</executable>
                        </configuration>
                    </execution>
                    <execution>
                        <id>dump-service-logs</id>
                        <phase>post-integration-test</phase>
                        <goals><goal>exec</goal></goals>
                        <configuration>
                            <executable>./scripts/dump-service-logs.sh</executable>
                            <arguments>
                                <argument>${project.build.directory}</argument>
                            </arguments>
                        </configuration>
                    </execution>
                    <execution>
                        <id>stop-integration-app</id>
                        <phase>post-integration-test</phase>
                        <goals><goal>exec</goal></goals>
                        <configuration>
                            <executable>./scripts/stop-integration-container.sh</executable>
                        </configuration>
                    </execution>
                </executions>
            </plugin>

            <!-- Failsafe for integration tests -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-failsafe-plugin</artifactId>
                <configuration>
                    <includes>
                        <include>**/*IT.java</include>
                    </includes>
                    <systemPropertyVariables>
                        <test.https.port>${test.https.port}</test.https.port>
                        <test.management.port>${test.management.port}</test.management.port>
                    </systemPropertyVariables>
                </configuration>
            </plugin>
        </plugins>
    </build>
</profile>
```

**Key differences from the application module**:
- No framework build plugin (e.g., no `quarkus-maven-plugin`) — the integration module doesn't build the app
- Explicit Failsafe `<include>` pattern for test discovery — the unqualified `**/*IT.java`, never a package-qualified one: a pattern that matches no class leaves the lane green with zero tests run (see SKILL.md, "An Include Pattern Can Match Nothing and Stay Green")
- System properties pass port configuration to tests
- Post-integration-test dumps service logs before stopping containers

## Base Test Class Pattern

```java
public abstract class BaseIntegrationTest {

    private static final String DEFAULT_TEST_PORT = "10443";
    private static final String DEFAULT_MANAGEMENT_PORT = "19000";

    @BeforeAll
    static void setUpBaseIntegrationTest() {
        // Configure HTTPS with relaxed validation for self-signed certificates
        RestAssured.useRelaxedHTTPSValidation();
        RestAssured.baseURI = "https://localhost";

        // Use external port from docker-compose (10443:8443)
        String testPort = System.getProperty("test.https.port", DEFAULT_TEST_PORT);
        RestAssured.port = Integer.parseInt(testPort);
    }

    /**
     * Base URI for management interface endpoints (health, metrics).
     * Management runs on plain HTTP on a separate port.
     */
    protected static String managementBaseUri() {
        String port = System.getProperty("test.management.port", DEFAULT_MANAGEMENT_PORT);
        return "http://localhost:" + port;
    }
}
```

## Testing Patterns

### API Endpoint Testing (HTTPS port)

API tests use the default RestAssured config (HTTPS, port 10443):

```java
class ApiIntegrationIT extends BaseIntegrationTest {

    @Test
    void shouldHandleValidRequest() {
        given()
                .contentType("application/json")
                .body("""
                    {
                        "field": "value"
                    }
                    """)
                .when()
                .post("/api/endpoint")
                .then()
                .statusCode(201)
                .body("id", notNullValue())
                .body("status", equalTo("created"));
    }
}
```

### Health/Metrics Testing (management port)

Health and metrics endpoints use the management interface (plain HTTP, separate port):

```java
@Test
void shouldProvideOverallHealthStatus() {
    given()
            .baseUri(managementBaseUri())
            .when()
            .get("/health")
            .then()
            .statusCode(200)
            .contentType("application/json")
            .body("status", equalTo("UP"));
}

@Test
void shouldExposeMetrics() {
    given()
            .baseUri(managementBaseUri())
            .when()
            .get("/metrics")
            .then()
            .statusCode(200);
}
```

**Note**: The health/metrics endpoint paths vary by framework (e.g., `/q/health` for Quarkus, `/actuator/health` for Spring Boot). Adjust paths accordingly.

**An overall `UP` is not evidence that a check ran.** An aggregate endpoint reports `UP` when every registered check is up — and also when no check is registered at all. A test that asserts only the status passes against an application whose health checks were never wired in. Assert the checks the application is expected to contribute, by name:

```java
@Test
void shouldReportTheExpectedReadinessChecks() {
    given()
            .baseUri(managementBaseUri())
            .when()
            .get("/health/ready")
            .then()
            .statusCode(200)
            .body("status", equalTo("UP"))
            .body("checks.name", hasItem("backend-connection"));
}
```

A readiness endpoint answers with a non-2xx status while a check is down, and still carries the JSON body. A test that inspects the body of a `DOWN` answer sets no status expectation, or expects the 503.

### Port Mapping Strategy

| Port | Protocol | Purpose |
|------|----------|---------|
| `10443:8443` | HTTPS | API endpoints (external test port) |
| `19000:9000` | HTTP | Management interface (health, metrics) |

## Script-Based Lifecycle Management

### Start Script Pattern

The start script must wait for **all dependent services** before proceeding:

```bash
#!/bin/bash
# scripts/start-integration-container.sh
set -e

cd "${PROJECT_DIR}"

docker compose up -d

# 1. Wait for dependent services first (e.g., identity provider)
echo "Waiting for identity provider..."
for i in {1..60}; do
    if curl -sf http://localhost:1090/health/ready > /dev/null 2>&1; then
        echo "Identity provider is ready"
        break
    fi
    [ $i -eq 60 ] && { echo "Identity provider failed to start"; exit 1; }
    sleep 1
done

# 2. Then wait for the application (via management interface)
echo "Waiting for application..."
START_TIME=$(date +%s)
for i in {1..30}; do
    if curl -sf http://localhost:19000/health/live > /dev/null 2>&1; then
        TOTAL_TIME=$(( $(date +%s) - START_TIME ))
        echo "Application ready in ${TOTAL_TIME}s"
        break
    fi
    [ $i -eq 30 ] && { echo "Application failed to start"; docker compose logs; exit 1; }
    sleep 1
done
```

**`curl` needs `-f` in a readiness wait.** Without it `curl` exits 0 for any HTTP answer, including the 503 a readiness endpoint gives while the service is not ready, so the loop reports "ready" on the first response instead of the first successful one. Keep the call as the condition of the `if`: under `set -e` a failing `curl` there does not end the script, and the loop goes on polling until its own limit.

The wait for a dependent service has to cover that service's whole start. Where the stack is started in steps — dependencies first, the application once a setup step has finished — `docker compose up` no longer waits on the dependency's own health check, and the loop's limit is the only bound there is.

### Stop Script Pattern

```bash
#!/bin/bash
# scripts/stop-integration-container.sh
set -e

cd "${PROJECT_DIR}"

docker compose down

if docker compose ps | grep -q "Up"; then
    echo "Warning: Some containers still running"
    docker compose ps
fi
```

### Log Dump Script Pattern

Dump service logs in `post-integration-test` **before** stopping containers — essential for debugging failures:

```bash
#!/bin/bash
# scripts/dump-service-logs.sh
TARGET_DIR="${1:-.}"

docker compose logs identity-provider > "${TARGET_DIR}/identity-provider.log" 2>&1 || true
docker compose logs application > "${TARGET_DIR}/application.log" 2>&1 || true

echo "Service logs saved to ${TARGET_DIR}"
```

Dump every container a test reads from, not only the application under test. A container added for one test — a second instance of the application with a different configuration, a stub — is the one whose log is needed when that test fails, and it is the one a script written earlier does not know. Write each dump under a name the CI workflow's artifact upload already matches, and print nothing for a container that does not exist in the current profile.

### A New Integration Test Runs First in CI

A test that needs the full stack — a built image, the compose services, an identity provider — is often written and compiled without ever being run, because the stack is too slow or too heavy to start locally. Its first execution is then the CI run of the pull request, and its first failure has to be diagnosed from the CI log alone. Write it for that:

* **Put the evidence into the failure message.** An assertion on a response carries the HTTP status and the body in its message. "expected: not null" tells nothing; the body tells which part of the expectation was wrong.
* **Make the logs it depends on reach the CI artifacts** — see above — before the first run, not after the first failure.
* **Say in the pull request that the test has not run.** A reviewer reads a compiled-only test differently from a passing one.
* **Read a first failure as information about the system as well as about the test.** A new test that probes a part of the application no test looked at before can fail because that part never worked. Reproduce against the running application before changing the test's expectation.

## Test Execution Phases

### Maven Lifecycle Integration

```text
1. compile               → Compile integration test code
2. test                  → SKIP (unit tests disabled in IT module)
3. pre-integration-test  → Start containers, wait for readiness
4. integration-test      → Run *IT.java files via Failsafe
5. post-integration-test → Dump logs, stop containers
6. verify                → Check test results
```

### Build Commands

```bash
# Run integration tests
./mvnw verify -Pintegration-tests -pl integration-tests

# Skip integration tests (default — skipITs=true)
./mvnw verify -pl integration-tests
```

The first line assumes the application module's artifact is already installed. When it is not, build it with a separate `install -DskipTests -DskipITs -pl integration-tests -am` first — do not add `-am` to the `verify` line, which would run the upstream modules' unit suites inside this lane (see SKILL.md, "The Profile Skip Does Not Reach Upstream Modules").

## Anti-Patterns

* **Internal Injection in Tests**: Never use `@Inject`/`@Autowired` — tests are external clients
* **HTTP for API tests**: All API integration tests must use HTTPS
* **Health checks on HTTPS port**: Use management interface for health/metrics
* **Hardcoded Ports**: Always use configurable system properties
* **Framework build plugin in IT module**: The integration module doesn't build the app
* **Missing log dump**: Always dump service logs before stopping containers
* **Package-qualified Failsafe include**: A pattern that matches nothing reports success with zero tests
* **`-am` on the `verify` line**: Re-runs the upstream modules' unit suites inside the integration-test lane
* **Status-only health assertion**: `status: UP` also holds with no check registered; assert the expected checks by name
* **`curl` without `-f` in a readiness wait**: Exits 0 on a 503, so the wait ends on the first answer, not the first ready one
* **Failure message without the response**: A first run in CI that fails with "expected: not null" cannot be diagnosed from the log

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker compose logs

# Verify certificates exist
ls -la src/main/docker/certificates/

# Test certificate validity
openssl x509 -in src/main/docker/certificates/localhost.crt -text -noout
```

### Connection Refused

```bash
# Check port mapping from host
docker compose ps

# Probe management interface from host
curl -s http://localhost:19000/health

# Probe HTTPS endpoint from host
curl -k https://localhost:10443/api/health
```

### SSL Certificate Errors

```bash
# Regenerate certificates
cd src/main/docker/certificates
./generate-certificates.sh

# Verify certificate
openssl verify -CAfile localhost.crt localhost.crt
```

## References

* [REST Assured Documentation](https://rest-assured.io/)
* [Maven Failsafe Plugin](https://maven.apache.org/surefire/maven-failsafe-plugin/)
* For container configuration and Docker Compose patterns, see `pm-dev-java:java-quarkus` (Quarkus) or your framework's container standard
* For certificate management, see `pm-dev-oci:oci-security`
