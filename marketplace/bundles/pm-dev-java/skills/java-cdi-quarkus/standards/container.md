# Container Standards

## Purpose

Container standards for CUI Quarkus applications ensuring consistent, secure, and efficient containerized deployments.

## References

* [OWASP Docker Top 10](https://owasp.org/www-project-docker-top-10/)
* [NIST Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)
* [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
* [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
* [Quarkus Container Guide](https://quarkus.io/guides/container-image)
* [Distroless Images](https://gitingest.com/github.com/GoogleContainerTools/distroless)

## Base Image Standards

### Production (Required)
**Base Image**: `quay.io/quarkus/quarkus-distroless-image:2.0`

**Benefits**:
* **Security**: Minimal attack surface, no shell/package manager
* **Size**: 91.9MB compact footprint
* **Performance**: <0.5s startup, <150MB memory
* **Compliance**: OWASP Docker Top 10 aligned

### Development (Debugging Only)
**Base Image**: `registry.access.redhat.com/ubi9/ubi-minimal:9.4`

**Use Cases**:
* **Local debugging**: When you need to `docker exec` into a running container and use commands like `ps`, `netstat`, `ls`, or `cat` to inspect the runtime environment
* **Troubleshooting production issues**: Temporarily recreating a container with shell tools to diagnose file permissions, network connectivity, or process issues
* **Initial development**: Building and testing locally before production hardening

**When to Use Which**:
* ✅ **Use distroless** for: CI/CD pipelines, integration tests, pre-production environments, production deployments
* ✅ **Use UBI minimal** for: Interactive debugging sessions where you need `docker exec -it <container> /bin/sh` to investigate issues
* ❌ **Never use UBI minimal** in: Production deployments, automated CI/CD pipelines, or any environment where shell access is not actively needed

**Important**: Use distroless for all automated testing (CI/CD, integration tests). Only use UBI minimal when you specifically need shell access for debugging. Never use in production.

## Production Dockerfile Template

```dockerfile
FROM quay.io/quarkus/quarkus-distroless-image:2.0

# Security metadata for compliance tracking
LABEL security.scan.required="true"
LABEL security.distroless="true"
LABEL org.opencontainers.image.vendor="CUI"

WORKDIR /app

# Secure file operations with root ownership to prevent modification
COPY --chmod=0755 --chown=root:root target/*-runner /app/application
COPY --chmod=0755 --chown=root:root health-check.sh /app/health-check.sh

# PEM certificate files with root ownership for security
COPY --chmod=0644 --chown=root:root certificates/tls.crt /app/certificates/tls.crt
COPY --chmod=0600 --chown=root:root certificates/tls.key /app/certificates/tls.key

EXPOSE 8443

# Internal health check optimized for native startup performance
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
  CMD ["/app/health-check.sh"]

# Non-root execution
USER nonroot

ENTRYPOINT ["/app/application"]
```

## Docker Compose Standards

### Production-Grade Integration Testing

**Critical Principle**: Integration tests must use production-equivalent configuration to detect issues early.

```yaml
# Production-Grade Integration Testing Configuration
services:
  application-integration-tests:
    build:
      context: .
      dockerfile: src/main/docker/Dockerfile.native
      cache_from:
        - quay.io/quarkus/quarkus-distroless-image:2.0
      platforms:
        - linux/amd64
        - linux/arm64

    ports:
      - "10443:8443"  # External test port

    volumes:
      # PEM certificate mount (production pattern)
      - ./src/main/docker/certificates:/app/certificates:ro

    environment:
      - QUARKUS_LOG_LEVEL=INFO

    # OWASP Security hardening (production-grade)
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
      - /app/tmp:rw,noexec,nosuid,size=50m

    # Resource limitations (DoS protection)
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 128M
          cpus: '0.5'

# Health check optimized for native Quarkus startup performance
    healthcheck:
      test: ["CMD", "/app/health-check.sh"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

    # Network isolation
    networks:
      - integration-test

    restart: unless-stopped

networks:
  integration-test:
    driver: bridge
    internal: false
```

For detailed explanation of OWASP security options (`no-new-privileges`, `cap_drop`, `read_only`), see [security.md](security.md) section "OWASP-Compliant Deployment".

### Environment Configuration (.env)

**Minimal Configuration Approach**:
```properties
# Docker Compose build optimization
COMPOSE_BAKE=true
```

**Configuration Principles**:
* **Minimal .env**: Only COMPOSE_BAKE needed, other variables handled in docker-compose.yml
* **No Password Variables**: PEM approach eliminates certificate password management
* **Simplified Configuration**: Direct property assignment preferred over complex YAML anchors

## Health Check Standards

### Internal Health Check Implementation

**Core Principle**: Use internal health check scripts with built-in system tools only - avoid external dependencies like `curl`, `wget`.

#### Why Avoid External Dependencies?
* **Image Bloat**: `curl` adds ~2.5MB and increases attack surface
* **Portability Issues**: Cross-platform compatibility problems
* **Security Concerns**: External diagnostic endpoints need to be private
* **Dependency Risk**: Tool availability varies across base images

#### Production Health Check Script

```bash
#!/bin/bash
# Internal health check script - no external dependencies

# Port connectivity test using /dev/tcp (Docker best practice)
if ! echo -n '' > /dev/tcp/127.0.0.1/8443 2>/dev/null; then
    echo "Application not listening on port 8443"
    exit 1
fi

# PEM Certificate validation (match actual file paths)
if [ ! -f "/app/certificates/tls.crt" ] || [ ! -f "/app/certificates/tls.key" ]; then
    echo "PEM certificate files missing"
    exit 1
fi

# Application executable check
if [ ! -x "/app/application" ]; then
    echo "Application executable missing"
    exit 1
fi

echo "Health check passed"
exit 0
```

#### Health Check Benefits
* **No External Dependencies**: Works in distroless and minimal base images
* **Security**: Reduced attack surface, no exposed diagnostic endpoints
* **Performance**: Faster execution than HTTP-based checks
* **Reliability**: Tests actual application functionality

#### Health Check Timing Guidelines

**Native Quarkus Optimization**: Health check timings must be optimized for native application startup characteristics.

**Recommended Timings**:
* **start_period**: `10s` (native apps start in 1-2 seconds)
* **interval**: `15s` (responsive monitoring for integration tests)
* **timeout**: `5s` (sufficient for internal checks)
* **retries**: `3` (standard reliability)

**Anti-Pattern**: The original `start_period: 40s` was excessive for containers that start in milliseconds.

**Performance Impact**:
* Faster container readiness detection
* More responsive health monitoring
* Reduced integration test execution time
* Better feedback during development

## Security Requirements

### OWASP Docker Top 10 Compliance

**Production Mandatory Requirements**:
- [x] **D01 - Secure User Mapping**: Non-root user execution (`USER nonroot`)
- [x] **D02 - Patch Management**: Regular base image updates in CI/CD
- [x] **D03 - Network Hardening**: HTTPS-only endpoints, network isolation
- [x] **D04 - Security Defaults**: Read-only filesystem, no-new-privileges, capability dropping
- [x] **D05 - Maintain Security Contexts**: Proper file permissions and ownership
- [x] **D06 - Resource Protection**: Memory/CPU limits, DoS prevention
- [x] **D07 - Data Protection**: Secure certificate management, no embedded secrets
- [x] **D08 - Container Monitoring**: Health checks without external dependencies
- [x] **D09 - Version Pinning**: Specific base image versions (never `latest`)
- [x] **D10 - Secrets Management**: External secret stores, not embedded in images

### Runtime Security Configuration

For complete OWASP-compliant Docker deployment configuration with security options explained, see [security.md](security.md) section "OWASP-Compliant Deployment".

**Key Security Requirements for Container Runtime**:
- Use `--security-opt=no-new-privileges` to prevent privilege escalation
- Drop all capabilities with `--cap-drop ALL` (principle of least privilege)
- Enable read-only filesystem with `--read-only` and writable tmpfs mounts
- Set resource limits (`--memory`, `--cpus`) to prevent DoS attacks
- Mount certificates as read-only volumes

## Certificate Management

### PEM Certificates (Primary Approach)

#### Security Benefits of PEM
* **No Password Storage**: Eliminates password management and exposure risks
* **File System Security**: Relies on proper file permissions (600 for keys, 644 for certificates)
* **Separation of Concerns**: Private keys and certificates stored separately
* **Cloud Native**: Better integration with container orchestration
* **Rotation Friendly**: Easier certificate rotation without password coordination

#### Certificate Generation Script

```bash
#!/bin/bash
# Secure certificate generation script

CERT_DIR="./src/main/docker/certificates"
VALIDITY_DAYS=${1:-1}  # Default 1 day for testing, 365+ for production

# Create certificate directory
mkdir -p "$CERT_DIR"

# Generate private key (no password required)
openssl genrsa -out "$CERT_DIR/tls.key" 2048

# Generate self-signed certificate
openssl req -new -x509 -key "$CERT_DIR/tls.key" \
    -out "$CERT_DIR/tls.crt" \
    -days "$VALIDITY_DAYS" \
    -subj "/CN=localhost/O=CUI/C=US" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Set secure file permissions
chmod 600 "$CERT_DIR/tls.key"   # Private key - restricted
chmod 644 "$CERT_DIR/tls.crt"   # Certificate - public

echo "Certificates generated in $CERT_DIR with $VALIDITY_DAYS day validity"
```

#### Quarkus PEM Configuration

```properties
# PEM-based SSL configuration
quarkus.http.ssl.certificate.files=/app/certificates/tls.crt
quarkus.http.ssl.certificate.key-files=/app/certificates/tls.key

# SSL enforcement
quarkus.http.ssl-port=8443
quarkus.http.insecure-requests=disabled

# Enhanced TLS Security Settings
quarkus.http.ssl.cipher-suites=TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_AES_128_GCM_SHA256
quarkus.http.ssl.protocols=TLSv1.3,TLSv1.2
```

### PKCS12 Certificates (Alternative)

**Alternative format** for environments requiring PKCS12. PEM is recommended for new implementations.

**PKCS12 to PEM Conversion**:
```bash
# Extract private key from PKCS12
openssl pkcs12 -in keystore.p12 -nocerts -out tls.key -nodes

# Extract certificate from PKCS12
openssl pkcs12 -in keystore.p12 -clcerts -nokeys -out tls.crt

# Set proper permissions
chmod 600 tls.key
chmod 644 tls.crt
```

## Performance Targets

**Performance Requirements**:
* **Startup Time**: <0.5s
* **Memory Usage**: <150MB runtime
* **Image Size**: <100MB
* **Build Time**: <2 minutes native

**Implementation Results**:
* **Unit Testing**: Comprehensive coverage
* **Integration Testing**: Full deployment validation
* **Native Compilation**: GraalVM support
* **Multi-Platform**: linux/amd64 and linux/arm64 support
* **Certificate Integration**: PEM and PKCS12 support

## Multi-Platform Build Support

### Platform Requirements
* **linux/amd64**: Standard CI/CD environments, Intel/AMD servers
* **linux/arm64**: Apple Silicon, ARM-based cloud instances, edge devices

### Build Commands
```bash
# Multi-platform build (requires buildx)
docker compose build

# Platform-specific build
docker compose build --platform linux/amd64

# Create multi-platform builder (one-time setup)
docker buildx create --name multiarch --use --driver docker-container
```

## Logging Standards

**Required**: Console logging only (no file logging)

```properties
quarkus.log.console.enable=true
quarkus.log.console.format=%d{HH:mm:ss} %-5p [%c{2.}] (%t) %s%e%n
quarkus.log.level=INFO
```

## DevUI Component Standards

### JavaScript API Integration

**Critical**: DevUI JavaScript components must use correct case-sensitive API calls.

**Correct API Pattern**:
```javascript
// CORRECT: Case-sensitive API calls
const result = await devui.jsonRPC.CuiJwtDevUI.getConfiguration();
const health = await devui.jsonRPC.CuiJwtDevUI.getHealthInfo();
const status = await devui.jsonRPC.CuiJwtDevUI.getValidationStatus();
const jwks = await devui.jsonRPC.CuiJwtDevUI.getJwksStatus();
const validation = await devui.jsonRPC.CuiJwtDevUI.validateToken(token);
```

**Anti-Pattern** (Common Error):
```javascript
// INCORRECT: Wrong case - will cause runtime failures
const result = await devui.jsonrpc.CuiJwtDevUI.getConfiguration();
```

**Error Prevention**:
* **IDE Configuration**: Configure linters to catch case sensitivity errors
* **Code Review**: Mandatory review of all DevUI API calls
* **Testing**: Comprehensive integration tests for API interactions
* **Documentation**: Clear API documentation with correct casing

## Certificate Security Requirements

**Security Implementation**:
* **Validity**: 2 years production, 1 day testing (script configurable)
* **Algorithm**: RSA 2048-bit minimum
* **Security**: External volume mounts only, no embedded certificates
* **File Permissions**: 600 for private keys, 644 for certificates
* **Container Security**: Non-root execution with capability dropping
* **Password-Free**: No password storage required with PEM format

**Security Features**:
* **Certificate Generation**: Automated script with proper permissions
* **Container Mounting**: Read-only volume mounts
* **TLS Configuration**: Enhanced cipher suites and protocols
* **Health Checks**: Certificate validation integrated
* **Build Integration**: Full Maven lifecycle compatibility
