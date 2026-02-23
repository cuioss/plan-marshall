# Quarkus Testing Standards

## Required Imports

```java
// Quarkus Testing
import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.QuarkusIntegrationTest;
import io.quarkus.test.junit.QuarkusTestProfile;
import io.quarkus.test.junit.TestProfile;

// REST Assured (for HTTP/REST testing)
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

// MicroProfile Health (for health check testing)
import org.eclipse.microprofile.health.HealthCheckResponse;
```

## Purpose
Defines comprehensive testing standards for Quarkus applications, including test coverage configuration, test annotations, and integration with SonarQube for coverage reporting.

## References
* [Quarkus Testing Guide](https://quarkus.io/guides/getting-started-testing)
* [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
* [JaCoCo Documentation](https://www.jacoco.org/jacoco/trunk/doc/)
* [SonarQube Java Test Coverage](https://docs.sonarqube.org/latest/analyzing-source-code/test-coverage/java-test-coverage/)

## Quarkus Test Dependencies

### Required Test Dependencies
All Quarkus test modules must include these dependencies in `pom.xml`:

```xml
<dependencies>
    <!-- Core Quarkus testing -->
    <dependency>
        <groupId>io.quarkus</groupId>
        <artifactId>quarkus-junit5</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- JUnit Jupiter -->
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- REST Assured for HTTP testing -->
    <dependency>
        <groupId>io.rest-assured</groupId>
        <artifactId>rest-assured</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- JaCoCo for coverage reporting (REQUIRED for SonarQube) -->
    <dependency>
        <groupId>io.quarkus</groupId>
        <artifactId>quarkus-jacoco</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

## Test Coverage Configuration

### JaCoCo Configuration for Quarkus
Quarkus applications require special JaCoCo configuration to properly collect test coverage from `@QuarkusTest` and `@QuarkusIntegrationTest` annotated tests.

#### Required JaCoCo Plugin Configuration
```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <executions>
        <execution>
            <id>prepare-agent</id>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
            <configuration>
                <!-- Configure JaCoCo to work with Quarkus tests -->
                <includes>
                    <include>de/cuioss/jwt/quarkus/**</include>
                </includes>
                <!-- Ensure JaCoCo agent is properly attached to Quarkus tests -->
                <append>true</append>
                <!-- Ensure destination file is set -->
                <destFile>${project.build.directory}/jacoco.exec</destFile>
            </configuration>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
            <configuration>
                <outputDirectory>${project.build.directory}/site/jacoco</outputDirectory>
                <formats>
                    <format>XML</format>
                    <format>HTML</format>
                </formats>
            </configuration>
        </execution>
    </executions>
</plugin>
```

#### Required Surefire Configuration
The Maven Surefire plugin must be configured to properly include the JaCoCo agent for Quarkus tests:

```xml
<plugin>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <systemPropertyVariables>
            <java.util.logging.manager>org.jboss.logmanager.LogManager</java.util.logging.manager>
            <java.util.logging.config.file>${project.build.testOutputDirectory}/logging.properties</java.util.logging.config.file>
            <maven.home>${maven.home}</maven.home>
        </systemPropertyVariables>
        <useModulePath>false</useModulePath>
        <useFile>false</useFile>
        <trimStackTrace>false</trimStackTrace>
        <enableAssertions>true</enableAssertions>
        <!-- CRITICAL: Include JaCoCo agent with @{argLine} placeholder -->
        <argLine>@{argLine} -XX:+IgnoreUnrecognizedVMOptions -Djava.awt.headless=true</argLine>
    </configuration>
</plugin>
```

#### SonarQube Integration
Configure SonarQube to read the JaCoCo XML reports:

```xml
<properties>
    <!-- Configure SonarQube to find JaCoCo coverage reports -->
    <sonar.coverage.jacoco.xmlReportPaths>${project.build.directory}/site/jacoco/jacoco.xml</sonar.coverage.jacoco.xmlReportPaths>
</properties>
```

## Quarkus Test Types

### Unit Tests with @QuarkusTest
Use `@QuarkusTest` for tests that require the full CDI context and Quarkus application lifecycle:

```java
@QuarkusTest
@TestProfile(JwtTestProfile.class)
class JwtValidationConfigTest {

    @Inject
    JwtValidationConfig jwtConfig;

    @Test
    @DisplayName("Should load configuration with default values")
    void shouldLoadConfigWithDefaults() {
        // Assert
        assertNotNull(jwtConfig);
        assertNotNull(jwtConfig.issuers());
        assertTrue(jwtConfig.issuers().containsKey("default"));
    }
}
```

#### @QuarkusTest Requirements
* **CDI Injection**: Full CDI context is available, `@Inject` annotations work
* **Application Lifecycle**: Complete Quarkus application startup and shutdown
* **Test Profiles**: Use `@TestProfile` to configure test-specific settings
* **Coverage Collection**: Automatically collected by JaCoCo when properly configured

### Integration Tests with @QuarkusIntegrationTest
Use `@QuarkusIntegrationTest` for tests that verify the packaged application works correctly:

```java
@QuarkusIntegrationTest
@TestProfile(JwtTestProfile.class)
class NativeTokenValidatorProducerIT {

    @Test
    @DisplayName("Should start application successfully in native mode")
    void shouldStartApplicationInNativeMode() {
        // Given: The Quarkus application is running in native mode
        // When: The application has started successfully (no startup exceptions)
        // Then: This test passes, indicating all JWT components are properly configured

        // Basic smoke test - successful startup indicates proper CDI configuration
        assert true : "Application started successfully in native mode";
    }
}
```

#### @QuarkusIntegrationTest Limitations
* **No CDI Injection**: `@Inject` annotations are NOT supported
* **HTTP Testing**: Use RestAssured to test through HTTP endpoints
* **Application Packaging**: Requires build packaging
* **Native Mode**: Primarily for testing native builds and packaged applications

### Test Profiles
Create test profiles to configure different test scenarios:

```java
public class JwtTestProfile implements QuarkusTestProfile {

    @Override
    public Map<String, String> getConfigOverrides() {
        return Map.of(
            "cui.jwt.issuers.default.jwks-url", "https://example.com/.well-known/jwks.json",
            "cui.jwt.health.enabled", "true"
        );
    }

    @Override
    public String getConfigProfile() {
        return "test";
    }
}
```

## Test Configuration

### Test Resource Configuration
All Quarkus test modules must include properly configured test resources to ensure consistent test behavior and coverage collection.

#### Required Test Properties Configuration
Create `src/test/resources/application.properties` with essential Quarkus and JaCoCo settings:

```properties
# Test configuration for Quarkus tests
quarkus.log.level=INFO
quarkus.log.category."de.cuioss.jwt".level=DEBUG
quarkus.log.category."org.jboss.logmanager".level=WARN
quarkus.jacoco.reuse-data-file=true
quarkus.log.console.enable=true
quarkus.log.console.format=%d{yyyy-MM-dd HH:mm:ss,SSS} %-5p [%c] (%t) %s%e%n

# Default issuer configuration - base configuration that can be overridden by test profiles
cui.jwt.issuers.default.url=https://test-auth.example.com
cui.jwt.issuers.default.enabled=true
cui.jwt.issuers.default.public-key-location=classpath:keys/test_public_key.pem

# Configure a test issuer
cui.jwt.issuers.test-issuer.url=https://test-issuer.example.com
cui.jwt.issuers.test-issuer.jwks.url=https://test-issuer.example.com/.well-known/jwks.json
cui.jwt.issuers.test-issuer.jwks.refresh-interval-seconds=300
cui.jwt.issuers.test-issuer.jwks.read-timeout-ms=5000
cui.jwt.issuers.test-issuer.enabled=true

# Global parser configuration
cui.jwt.parser.max-token-size-bytes=8192
cui.jwt.parser.audience=test-audience
cui.jwt.parser.leeway-seconds=30
cui.jwt.parser.validate-not-before=true
cui.jwt.parser.validate-expiration=true
cui.jwt.parser.validate-issued-at=false
cui.jwt.parser.allowed-algorithms=RS256,RS384,RS512,ES256,ES384,ES512

# Health check configuration
cui.jwt.health.enabled=true
cui.jwt.health.jwks.cache-seconds=30
cui.jwt.health.jwks.timeout-seconds=5
```

#### Alternative YAML Configuration
For projects using YAML configuration, create `src/test/resources/application.yaml`:

```yaml
# Test configuration for Quarkus tests
quarkus:
  log:
    level: INFO
    console:
      enable: true
      format: "%d{yyyy-MM-dd HH:mm:ss,SSS} %-5p [%c] (%t) %s%e%n"
    category:
      "de.cuioss.jwt":
        level: DEBUG
      "org.jboss.logmanager":
        level: WARN
  jacoco:
    reuse-data-file: true

# JWT configuration for testing
cui:
  jwt:
    issuers:
      default:
        url: https://test-auth.example.com
        enabled: true
        public-key-location: classpath:keys/test_public_key.pem
      test-issuer:
        url: https://test-issuer.example.com
        enabled: true
        jwks:
          url: https://test-issuer.example.com/.well-known/jwks.json
          refresh-interval-seconds: 300
          read-timeout-ms: 5000
    parser:
      max-token-size-bytes: 8192
      audience: test-audience
      leeway-seconds: 30
      validate-not-before: true
      validate-expiration: true
      validate-issued-at: false
      allowed-algorithms: RS256,RS384,RS512,ES256,ES384,ES512
    health:
      enabled: true
      jwks:
        cache-seconds: 30
        timeout-seconds: 5
```

#### Critical Configuration Elements
* **`quarkus.jacoco.reuse-data-file=true`**: Enables proper JaCoCo coverage collection across test runs
* **Logging Configuration**: Essential for debugging test issues and coverage analysis
* **Test-Specific Endpoints**: Use `test-` prefixed URLs to avoid production conflicts
* **Appropriate Timeouts**: Configured for test environment performance
* **Consistent Test Data**: Use standardized test audiences, algorithms, and issuer names

## Testing Best Practices

### Test Organization
* **Unit Tests**: Place in `src/test/java` with `*Test.java` naming
* **Integration Tests**: Place in `src/test/java` with `*IT.java` naming
* **Test Resources**: Use `src/test/resources` for test configurations
* **Configuration Consistency**: All test modules must use consistent base configuration from the standards above

### Coverage Requirements

**What Constitutes "Business Logic"**:
* ✅ **Include in coverage**: Services, validators, processors, domain logic, business rules, data transformation, calculation logic
* ❌ **Exclude from coverage**: Generated code (Lombok, MapStruct), simple DTOs without logic, configuration POJOs, framework adapters with only delegation

**Minimum Coverage Targets**:
* **Business Logic**: 80% line coverage minimum
  - Services implementing business rules
  - Validators with business validation logic
  - Processors transforming data
  - Domain model methods with behavior
* **CDI Components**: 100% coverage for producers, observers, and interceptors (critical infrastructure)
* **Configuration Classes**: All configuration classes must have tests validating correct bean production
* **Health Checks**: All health check implementations must be tested

### Quarkus-Specific Testing Patterns

#### Testing CDI Producers
```java
@QuarkusTest
class TokenValidatorProducerTest {

    @Inject
    TokenValidator tokenValidator;

    @Test
    @DisplayName("Should produce working TokenValidator")
    void shouldProduceWorkingTokenValidator() {
        // Assert that the producer created a functional bean
        assertNotNull(tokenValidator);

        // Test the produced bean's functionality
        assertThrows(TokenValidationException.class,
            () -> tokenValidator.createAccessToken("invalid-token"));
    }
}
```

#### Testing Health Checks
```java
@QuarkusTest
class JwksEndpointHealthCheckTest {

    @Inject
    JwksEndpointHealthCheck healthCheck;

    @Test
    @DisplayName("Should return UP when JWKS endpoints are accessible")
    void shouldReturnUpWhenJwksEndpointsAccessible() {
        // When
        HealthCheckResponse response = healthCheck.call();

        // Then
        assertEquals(HealthCheckResponse.Status.UP, response.getStatus());
    }
}
```

#### Testing Configuration
```java
@QuarkusTest
@TestProfile(JwtTestProfile.class)
class JwtValidationConfigTest {

    @Inject
    JwtValidationConfig config;

    @Test
    @DisplayName("Should load issuer configuration")
    void shouldLoadIssuerConfiguration() {
        // Assert configuration is properly loaded
        assertNotNull(config.issuers());
        assertTrue(config.issuers().containsKey("default"));

        var defaultIssuer = config.issuers().get("default");
        assertNotNull(defaultIssuer.jwksUrl());
    }
}
```

## Troubleshooting Coverage Issues

### Common Problems and Solutions

#### Coverage Not Collected
**Problem**: JaCoCo shows 0% coverage despite tests running
**Solution**: Ensure `@{argLine}` is included in Surefire configuration:
```xml
<argLine>@{argLine} -XX:+IgnoreUnrecognizedVMOptions -Djava.awt.headless=true</argLine>
```

#### SonarQube Not Finding Coverage
**Problem**: SonarQube reports no coverage data
**Solution**:
1. Verify `quarkus-jacoco` dependency is included
2. Check XML report path in `sonar.coverage.jacoco.xmlReportPaths`
3. Ensure XML format is enabled in JaCoCo report configuration

#### @QuarkusIntegrationTest Failures
**Problem**: Integration tests fail with injection errors
**Solution**: Remove `@Inject` annotations and use HTTP testing instead:
```java
// Not supported - @Inject not available
@Inject TokenValidator tokenValidator;

// Correct - Use HTTP endpoints
RestAssured.when().get("/q/health").then().statusCode(200);
```

### Build Phase Requirements
* **Unit Tests**: Run during `test` phase
* **Integration Tests**: Run during `integration-test` phase
* **Coverage Reports**: Generated during `test` and `verify` phases
* **Package Required**: Integration tests require `package` phase completion

## Quality Gates

### Mandatory Requirements
* All `@QuarkusTest` classes must have coverage data collected
* All CDI producers must be tested with actual injection
* All configuration classes must be tested with test profiles
* Coverage reports must be generated in XML format for SonarQube
* Build must fail if coverage falls below project thresholds
