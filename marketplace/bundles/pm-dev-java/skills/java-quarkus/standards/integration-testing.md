# Quarkus External Integration Testing Standards

## Purpose

Standards for implementing **external API integration tests** in Quarkus applications that test the complete application stack through published API interfaces using production-like configurations with Docker containers.

**Prerequisites**: For basic Maven Failsafe configuration and naming conventions, see `pm-dev-java:junit-integration`.

## Core Principles

### API-Only Testing

External integration tests **MUST** test only through published APIs, never through internal CDI injection:

* **No CDI Injection**: Tests must not use `@Inject` for services
* **External Client Perspective**: Tests simulate real client interactions
* **Protocol Compliance**: Use actual HTTP/HTTPS protocols
* **Container Isolation**: Application runs in separate process/container

### Production Equivalence

External integration tests **MUST** use production-equivalent configurations:

* **HTTPS Required**: All API tests use TLS with proper certificates
* **Management Interface**: Health/metrics via plain HTTP on separate port (9000)
* **Real Networking**: Actual TCP/IP communication, not in-memory
* **Container Runtime**: Application runs in Docker container
* **Resource Constraints**: Same memory/CPU limits as production

## Test Structure

### Directory Organization

```
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

The integration test module does **not** build the application — it only builds Docker images and runs tests. The native build happens in the main application module.

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
                        <include>**/integration/**/*IT.java</include>
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
- No `quarkus-maven-plugin` — the integration module doesn't build the app
- Explicit Failsafe `<include>` pattern for test discovery
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

Health and metrics endpoints use the management interface (plain HTTP, port 19000):

```java
@Test
void shouldProvideOverallHealthStatus() {
    given()
            .baseUri(managementBaseUri())
            .when()
            .get("/q/health")
            .then()
            .statusCode(200)
            .contentType("application/json")
            .body("status", equalTo("UP"));
}

@Test
void shouldExposePrometheusMetrics() {
    given()
            .baseUri(managementBaseUri())
            .when()
            .get("/q/metrics")
            .then()
            .statusCode(200)
            .contentType(containsString("text"))
            .body(containsString("# HELP"));
}
```

## Application Configuration

### Port Mapping Strategy

| Port | Protocol | Purpose |
|------|----------|---------|
| `10443:8443` | HTTPS | API endpoints (external test port) |
| `19000:9000` | HTTP | Management interface (health, metrics) |

For complete Docker Compose configuration, see [container.md](container.md).

## Script-Based Lifecycle Management

### Start Script Pattern

The start script must wait for **all dependent services** before proceeding:

```bash
#!/bin/bash
# scripts/start-integration-container.sh
set -e

cd "${PROJECT_DIR}"

docker compose up -d

# 1. Wait for dependent services first (e.g., Keycloak)
echo "Waiting for Keycloak..."
for i in {1..60}; do
    if curl -s http://localhost:1090/health/ready > /dev/null 2>&1; then
        echo "Keycloak is ready"
        break
    fi
    [ $i -eq 60 ] && { echo "Keycloak failed to start"; exit 1; }
    sleep 1
done

# 2. Then wait for the application (via management interface)
echo "Waiting for application..."
START_TIME=$(date +%s)
for i in {1..30}; do
    if curl -s http://localhost:19000/q/health/live > /dev/null 2>&1; then
        TOTAL_TIME=$(( $(date +%s) - START_TIME ))
        echo "Application ready in ${TOTAL_TIME}s"
        break
    fi
    [ $i -eq 30 ] && { echo "Application failed to start"; docker compose logs; exit 1; }
    sleep 1
done
```

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

docker compose logs keycloak > "${TARGET_DIR}/keycloak.log" 2>&1 || true
docker compose logs application > "${TARGET_DIR}/application.log" 2>&1 || true

echo "Service logs saved to ${TARGET_DIR}"
```

## Test Execution Phases

### Maven Lifecycle Integration

```
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

## Anti-Patterns

* **CDI Injection in Tests**: Never use `@Inject` — tests are external clients
* **@QuarkusTest**: Use for unit tests only, not external integration tests
* **HTTP for API tests**: All API integration tests must use HTTPS
* **Health checks on HTTPS port**: Use management interface (port 9000) for health/metrics
* **Hardcoded Ports**: Always use configurable system properties
* **Quarkus plugin in IT module**: The integration module doesn't build the app
* **Missing log dump**: Always dump service logs before stopping containers

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
curl -s http://localhost:19000/q/health

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

* [Quarkus Testing Guide](https://quarkus.io/guides/getting-started-testing)
* [REST Assured Documentation](https://rest-assured.io/)
* [Maven Failsafe Plugin](https://maven.apache.org/surefire/maven-failsafe-plugin/)
