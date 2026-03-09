# Java Application Security Patterns

Security patterns for Java applications. These are language/framework-agnostic practices — applicable to any Java project.

## Secure Logging

### Never Log

- Authentication tokens (JWT, OAuth tokens, API keys)
- Passwords or password hashes
- Certificate contents (private keys, full certificates)
- Internal system paths or configuration details
- User personal information (PII)
- Session identifiers
- Encryption keys or secrets

### Safe to Log

- Security event types (authentication success/failure)
- Masked usernames (first 3 characters + `***`)
- Resource access attempts (without sensitive details)
- Security policy violations (without triggering data)
- Audit trail events (with proper masking)

### Masking Pattern

```java
public void logAuthenticationSuccess(String username) {
    log.info("Authentication successful for user: " + maskUsername(username));
}

private String maskUsername(String username) {
    if (username == null || username.length() <= 3) {
        return "***";
    }
    return username.substring(0, 3) + "***";
}
```

## Startup Configuration Validation

Validate security configuration at startup, not at runtime. Use `@PostConstruct` or constructor validation to fail fast:

```java
@PostConstruct
void validateSecurityConfig() {
    if (!jwtSecret.isResolvable()) {
        throw new SecurityException("JWT secret must be configured");
    }
    if (!isValidAlgorithm(encryptionAlgorithm)) {
        throw new SecurityException("Invalid encryption algorithm: " + encryptionAlgorithm);
    }
}

private boolean isValidAlgorithm(String algorithm) {
    return List.of("AES-256-GCM", "AES-128-GCM", "ChaCha20-Poly1305")
            .contains(algorithm);
}
```

## Anti-Patterns

### Hardcoded Secrets

```java
// BAD
private static final String JWT_SECRET = "my-super-secret-key";

// GOOD — external configuration
@ConfigProperty(name = "security.jwt.secret")
Instance<String> jwtSecret;
```

### Logging Sensitive Data

```java
// BAD
log.info("User login: " + username + " with password: " + password);

// GOOD
log.info("User login attempt for: " + maskUsername(username));
```

### Insecure Error Messages

```java
// BAD — reveals internal details
throw new RuntimeException("Database password incorrect: " + dbPassword);

// GOOD — generic message, details in log
log.error("Authentication failed", e);
throw new RuntimeException("Authentication failed");
```

### Missing Startup Validation

```java
// BAD — no validation
@PostConstruct
void init() {
    // Just use the configuration
}

// GOOD — fail-fast
@PostConstruct
void init() {
    validateEncryptionAlgorithm();
    validateKeyStrength();
}
```

## Security Principles

1. **Fail-Fast**: Validate all security configuration at startup
2. **Defense in Depth**: Multiple layers of security controls
3. **Least Privilege**: Minimal permissions and capabilities
4. **No Secrets in Code**: All secrets from external configuration
5. **Secure by Default**: Security enabled by default, not opt-in
6. **Log Events, Not Data**: Log security events without sensitive data
