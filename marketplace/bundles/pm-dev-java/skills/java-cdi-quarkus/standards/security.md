# CDI Security Standards

## Purpose

Application-level security standards for CDI and Quarkus applications, focusing on secure dependency injection, configuration validation, security testing, and runtime security monitoring.

## CDI Security Patterns

### Secure Dependency Injection

**Critical**: Constructor injection ensures dependencies are validated at startup.

```java
@ApplicationScoped
public class SecurityService {
    private final EncryptionService encryption;
    private final AuditLogger auditLogger;

    // Constructor injection ensures dependencies are validated at startup
    public SecurityService(EncryptionService encryption, AuditLogger auditLogger) {
        this.encryption = Objects.requireNonNull(encryption, "EncryptionService required");
        this.auditLogger = Objects.requireNonNull(auditLogger, "AuditLogger required");
    }
}
```

**Benefits**:
* **Fail-Fast**: Missing security dependencies cause immediate startup failure
* **No Runtime Surprises**: Security components verified at build/startup time
* **Clear Dependencies**: All security requirements visible in constructor

### Secure Configuration Injection

**Pattern**: Validate security configuration at startup, not at runtime.

```java
@ApplicationScoped
public class JwtSecurityConfig {

    @ConfigProperty(name = "security.jwt.secret")
    Instance<String> jwtSecret;

    @ConfigProperty(name = "security.encryption.algorithm", defaultValue = "AES-256-GCM")
    String encryptionAlgorithm;

    // Validate security configuration at startup
    @PostConstruct
    void validateSecurityConfig() {
        if (!jwtSecret.isResolvable()) {
            throw new SecurityException("JWT secret must be configured");
        }

        if (!isValidAlgorithm(encryptionAlgorithm)) {
            throw new SecurityException("Invalid encryption algorithm: " + encryptionAlgorithm);
        }

        // Additional security validations
        validateKeyStrength();
        validateCipherConfiguration();
    }

    private boolean isValidAlgorithm(String algorithm) {
        return List.of("AES-256-GCM", "AES-128-GCM", "ChaCha20-Poly1305")
                .contains(algorithm);
    }

    private void validateKeyStrength() {
        // Validate key meets minimum security requirements
    }

    private void validateCipherConfiguration() {
        // Validate cipher suite configuration
    }
}
```

**Benefits**:
* **Early Detection**: Configuration errors detected at startup
* **Security Enforcement**: Invalid security configs rejected immediately
* **Clear Requirements**: Security constraints documented in code

## Secure Logging Standards

### Security-Compliant Logging Configuration

```properties
# Console logging only (security requirement)
quarkus.log.console.enable=true
quarkus.log.console.format=%d{HH:mm:ss} %-5p [%c{2.}] (%t) %s%e%n
quarkus.log.level=INFO

# Application-specific debug (development only)
quarkus.log.category."de.cuioss.jwt".level=DEBUG

# SECURITY: Never log sensitive data
# - No authentication tokens
# - No certificate contents
# - No internal system information
# - No user credentials
```

### Secure Logging Requirements

**CRITICAL**: Never log sensitive information.

```java
@ApplicationScoped
public class SecureLogger {

    private static final Logger log = Logger.getLogger(SecureLogger.class);

    // ✅ CORRECT: Log security events without sensitive data
    public void logAuthenticationSuccess(String username) {
        log.info("Authentication successful for user: " + maskUsername(username));
    }

    // ❌ WRONG: Logging sensitive data
    public void logAuthenticationAttempt(String username, String password) {
        log.info("Login attempt: " + username + " / " + password); // NEVER DO THIS!
    }

    // ✅ CORRECT: Log security events with context
    public void logAccessDenied(String resource, String reason) {
        log.warn("Access denied to resource: " + resource + ", reason: " + reason);
    }

    private String maskUsername(String username) {
        if (username == null || username.length() <= 3) {
            return "***";
        }
        return username.substring(0, 3) + "***";
    }
}
```

**Never Log**:
* Authentication tokens (JWT, OAuth tokens, API keys)
* Passwords or password hashes
* Certificate contents (private keys, full certificates)
* Internal system paths or configuration details
* User personal information (PII)
* Session identifiers
* Encryption keys or secrets

**Safe to Log**:
* Security event types (authentication success/failure)
* Masked usernames (first 3 characters + ***)
* Resource access attempts (without sensitive details)
* Security policy violations (without data that triggered violation)
* Audit trail events (with proper masking)

## Security Testing Standards

### Security Unit Tests

```java
@QuarkusTest
class SecurityConfigTest {

    @Inject
    SecurityConfig securityConfig;

    @Test
    @DisplayName("Should enforce secure configuration")
    void shouldEnforceSecureConfiguration() {
        // Verify security configuration is properly loaded
        assertNotNull(securityConfig.getEncryptionAlgorithm());
        assertTrue(securityConfig.getEncryptionAlgorithm().startsWith("AES"));

        // Verify required security settings
        assertTrue(securityConfig.isHttpsOnly());
        assertFalse(securityConfig.isDebugMode());
    }

    @Test
    @DisplayName("Should reject weak encryption algorithms")
    void shouldRejectWeakEncryptionAlgorithms() {
        // Verify weak algorithms are rejected
        assertThrows(SecurityException.class,
            () -> securityConfig.setEncryptionAlgorithm("DES"));
    }

    @Test
    @DisplayName("Should validate minimum key strength")
    void shouldValidateMinimumKeyStrength() {
        // Verify minimum key strength requirements
        assertTrue(securityConfig.getMinimumKeyBits() >= 256);
    }
}
```

### Security Integration Tests

**IMPORTANT**: Security integration tests must use HTTPS and production-equivalent security.

```java
class SecurityIntegrationTest extends BaseIntegrationTest {

    @Test
    @DisplayName("Should enforce HTTPS-only access")
    void shouldEnforceHttpsOnlyAccess() {
        // HTTP should be rejected or redirected
        RestAssured.given()
            .when().get("http://localhost:8080/q/health")
            .then()
            .statusCode(anyOf(is(301), is(302), is(400)));

        // HTTPS should work
        RestAssured.given()
            .relaxedHTTPSValidation()
            .when().get("https://localhost:8443/q/health")
            .then()
            .statusCode(200);
    }

    @Test
    @DisplayName("Should reject requests with invalid certificates")
    void shouldRejectInvalidCertificates() {
        // Test certificate validation
        // Implementation depends on certificate setup
    }

    @Test
    @DisplayName("Should enforce TLS 1.2 minimum")
    void shouldEnforceTlsMinimum() {
        // Verify TLS 1.0 and 1.1 are rejected
        // Verify TLS 1.2 and 1.3 are accepted
    }
}
```

### Security Testing Requirements

**Coverage Requirements**:
* All security configuration classes: 100% coverage
* Authentication/authorization logic: 100% coverage
* Encryption/decryption operations: 100% coverage
* Security validation logic: 100% coverage
* Security exception handling: 100% coverage

**Test Scenarios**:
* Valid security configurations
* Invalid security configurations (should fail fast)
* Weak encryption algorithms (should be rejected)
* Missing security dependencies (should fail at startup)
* Certificate validation
* TLS configuration enforcement

## Runtime Security Configuration

### OWASP-Compliant Deployment

```bash
# OWASP-compliant production deployment
docker run -d \
  --name secure-application \
  --security-opt=no-new-privileges:true \
  --cap-drop ALL \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /app/tmp:rw,noexec,nosuid,size=50m \
  --memory="256m" \
  --cpus="1.0" \
  --restart=unless-stopped \
  --network=secure-app-network \
  -v "./certificates:/app/certificates:ro" \
  -e QUARKUS_LOG_LEVEL=INFO \
  application:latest
```

### Security Options Explained

* **`--security-opt=no-new-privileges`**: Prevents privilege escalation via setuid/setgid binaries
* **`--cap-drop ALL`**: Removes all Linux capabilities (principle of least privilege)
* **`--read-only`**: Makes root filesystem read-only (immutable infrastructure)
* **`--tmpfs`**: Provides temporary writable space without persistence
* **`--memory/--cpus`**: Resource limits prevent DoS attacks
* **`--restart=unless-stopped`**: Production resilience without security risks
* **`--network`**: Network isolation for controlled communication

## Security Monitoring and Compliance

### Continuous Security Monitoring

#### Required Security Metrics

Monitor these security-related metrics continuously:

* **Authentication Failures**: Track failed authentication attempts
* **Authorization Denials**: Monitor access control violations
* **Certificate Expiration**: Alert before certificates expire
* **Security Configuration Changes**: Audit all security config modifications
* **Resource Usage Anomalies**: Detect potential DoS attacks
* **Error Rates**: Monitor security-related errors

### Security Scanning Requirements

**Pre-Deployment Scanning**:
* **Image Vulnerability Scanning**: Integrate Trivy, Snyk, or similar tools in CI/CD
* **Dependency Scanning**: Check for known vulnerabilities in dependencies
* **Static Code Analysis**: Use SonarQube security rules
* **Secret Detection**: Scan for accidentally committed secrets

**Runtime Security Monitoring**:
* **Privilege Escalation Detection**: Monitor for privilege escalation attempts
* **Network Traffic Analysis**: Ensure only HTTPS traffic is allowed
* **Resource Usage Monitoring**: Detect potential DoS attacks
* **Compliance Verification**: Regular OWASP Top 10 compliance checks

### Security Validation Procedures

#### Container Security Validation

```bash
# Verify container security configuration
docker inspect container --format='User: {{.Config.User}}'
docker inspect container --format='SecurityOpt: {{.HostConfig.SecurityOpt}}'
docker inspect container --format='ReadOnly: {{.HostConfig.ReadonlyRootfs}}'
docker inspect container --format='CapDrop: {{.HostConfig.CapDrop}}'

# Test application security endpoints
curl -k https://localhost:8443/q/health/live   # Should return 200
curl -k https://localhost:8443/q/health/ready  # Should return 200

# Verify TLS configuration
openssl s_client -connect localhost:8443 -servername localhost

# Performance verification with security
docker logs container | grep "started in"
docker stats container --no-stream
```

## Security Performance Metrics

**Security Overhead Targets**:
* **Image Size**: <100MB compact footprint
* **Startup Time**: <0.5s with security hardening
* **Memory Usage**: <150MB within security resource limits
* **Attack Surface**: Minimal distroless + no shell access
* **Privilege Level**: Non-root execution only
* **Compliance**: OWASP Docker Top 10 aligned

## Enterprise Security Standards

### Security Governance

#### Production Security Requirements

* **Security Reviews**: All container configurations must pass security review
* **Change Control**: Security configuration changes require approval
* **Incident Response**: Defined procedures for security incidents
* **Compliance Auditing**: Regular OWASP and industry standard compliance verification
* **Security Training**: Team training on container security best practices

#### Security Documentation Requirements

* **Security Configuration**: Maintain security configuration documentation
* **Incident Runbooks**: Security incident response procedures
* **Compliance Reports**: Regular security posture reporting
* **Risk Assessments**: Quarterly security risk assessments
* **Security Metrics**: Continuous security metrics collection and reporting

### Certificate Security Management

#### Certificate Security Standards

* **External Mounting**: Use read-only certificate mounts (`-v ./certs:/app/certificates:ro`)
* **Validity Periods**: 2 years maximum for production, 1 day for testing
* **File Permissions**: 600 for private keys, 644 for certificates
* **Zero Embedding**: Never include certificates in container images
* **Automated Validation**: Health checks verify certificate availability and readability
* **Rotation Policy**: Automated certificate rotation with zero-downtime deployment

#### Certificate Monitoring

```bash
# Certificate expiration monitoring
openssl x509 -in /app/certificates/tls.crt -noout -dates

# Certificate validation in health checks
test -r "/app/certificates/tls.crt" && test -r "/app/certificates/tls.key"

# TLS endpoint validation
openssl s_client -connect localhost:8443 -verify_return_error
```

## Security Validation Checklist

### Pre-Deployment Security Validation

- [ ] Container runs as non-root user
- [ ] Read-only filesystem enabled
- [ ] All capabilities dropped
- [ ] Resource limits configured
- [ ] Certificates externally mounted
- [ ] No sensitive data in environment variables
- [ ] HTTPS-only endpoints configured
- [ ] Security scanning completed
- [ ] Vulnerability assessment passed
- [ ] Penetration testing completed (production)

### Runtime Security Validation

- [ ] Authentication mechanisms working correctly
- [ ] Authorization policies enforced
- [ ] Encryption working for sensitive data
- [ ] Audit logging operational
- [ ] Security monitoring active
- [ ] Certificate rotation tested
- [ ] Incident response procedures documented
- [ ] Security metrics collected and analyzed

## Security Anti-Patterns

### Common Security Mistakes

#### Anti-Pattern 1: Hardcoded Secrets

```java
// ❌ WRONG: Hardcoded secrets
@ApplicationScoped
public class BadSecurityConfig {
    private static final String JWT_SECRET = "my-super-secret-key";  // NEVER DO THIS!
}

// ✅ CORRECT: External configuration
@ApplicationScoped
public class GoodSecurityConfig {
    @ConfigProperty(name = "security.jwt.secret")
    Instance<String> jwtSecret;
}
```

#### Anti-Pattern 2: Logging Sensitive Data

```java
// ❌ WRONG: Logging passwords
log.info("User login: " + username + " with password: " + password);

// ✅ CORRECT: Log events without sensitive data
log.info("User login attempt for: " + maskUsername(username));
```

#### Anti-Pattern 3: Insecure Error Messages

```java
// ❌ WRONG: Revealing internal details
catch (SecurityException e) {
    throw new RuntimeException("Database password incorrect: " + dbPassword);
}

// ✅ CORRECT: Generic error messages
catch (SecurityException e) {
    log.error("Authentication failed", e);
    throw new RuntimeException("Authentication failed");
}
```

#### Anti-Pattern 4: Weak Validation

```java
// ❌ WRONG: No validation
@PostConstruct
void init() {
    // Just use the configuration without validation
}

// ✅ CORRECT: Strict validation
@PostConstruct
void init() {
    validateEncryptionAlgorithm();
    validateKeyStrength();
    validateCertificateConfiguration();
}
```

## Security Best Practices Summary

### Key Security Principles

1. **Fail-Fast**: Validate all security configuration at startup
2. **Defense in Depth**: Multiple layers of security controls
3. **Least Privilege**: Minimal permissions and capabilities
4. **No Secrets in Code**: All secrets from external configuration
5. **Secure by Default**: Security enabled by default, not opt-in
6. **Comprehensive Logging**: Log security events without sensitive data
7. **Regular Updates**: Keep dependencies and base images updated
8. **Continuous Monitoring**: Active security monitoring and alerting

### Security Testing Requirements

* Unit tests for all security configuration
* Integration tests with HTTPS and certificates
* Security-specific test scenarios (invalid configs, weak algorithms)
* 100% coverage for security-critical code
* Regular security scanning and vulnerability assessment

## References

* [OWASP Top 10](https://owasp.org/www-project-top-ten/)
* [OWASP Docker Top 10](https://owasp.org/www-project-docker-top-10/)
* [NIST Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
* [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
* [Quarkus Security Guide](https://quarkus.io/guides/security)
