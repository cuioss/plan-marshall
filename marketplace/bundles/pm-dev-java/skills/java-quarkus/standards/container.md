# Container Standards

## Purpose

Container standards for CUI Quarkus applications ensuring consistent, secure, and efficient containerized deployments.

## References

* [Quarkus Container Guide](https://quarkus.io/guides/container-image)
* [Distroless Images](https://gitingest.com/github.com/GoogleContainerTools/distroless)
* Generic OCI security: `Skill: pm-dev-oci:oci-security` (OWASP, runtime hardening, supply chain, image building)

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

# PEM certificate files with root ownership for security
COPY --chmod=0644 --chown=root:root certificates/tls.crt /app/certificates/tls.crt
COPY --chmod=0600 --chown=root:root certificates/tls.key /app/certificates/tls.key

EXPOSE 8443 9000

# Non-root execution
USER nonroot

ENTRYPOINT ["/app/application"]
```

## Docker Compose Standards

### Production-Grade Integration Testing

**Critical Principle**: Integration tests must use production-equivalent configuration to detect issues early.

```yaml
services:
  application:
    image: "my-app:distroless"
    build:
      context: ../my-app
      dockerfile: src/main/docker/Dockerfile.native
      cache_from:
        - quay.io/quarkus/quarkus-distroless-image:2.0

    ports:
      - "10443:8443"  # External test port
      - "19000:9000"  # Management interface (health/metrics, plain HTTP)

    environment:
      - QUARKUS_HTTP_SSL_CERTIFICATE_FILES=/app/certificates/localhost.crt
      - QUARKUS_HTTP_SSL_CERTIFICATE_KEY_FILES=/app/certificates/localhost.key
      # File logging for integration tests only (production uses console logging)
      - LOG_FILE_PATH=/logs/quarkus.log

    depends_on:
      - keycloak  # Service ordering for dependent infrastructure

    volumes:
      - ./src/main/docker/certificates:/app/certificates:ro
      # Writable log mount for integration tests (not for production)
      - ${LOG_TARGET_DIR:-./target}:/logs:rw

    # OWASP Security hardening (production-grade)
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m

    # Resource limitations (DoS protection)
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '4.0'
        reservations:
          memory: 256M
          cpus: '1.0'

    networks:
      - app-network
    restart: unless-stopped

  # Optional services via profiles
  monitoring:
    image: prom/prometheus:v3.6.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks:
      - app-network
    profiles:
      - monitoring

networks:
  app-network:
    driver: bridge
```

### Key Patterns

- **Image pinning**: Pin third-party images with SHA256 digest (e.g., `image@sha256:...`) when Dependabot cannot auto-update
- **`depends_on`**: Declare service startup ordering for infrastructure dependencies
- **Management port**: Expose Quarkus management interface (port 9000, plain HTTP) separately from application port
- **Console logging only**: Containers log to stdout/stderr — let the orchestrator handle log collection. File logging is only for local integration tests (mount `./target` as writable volume)
- **Profiles**: Use compose profiles for optional services (monitoring, benchmarks) — keeps default startup lean
- **No `platforms` in compose**: Multi-arch builds belong in CI with `docker buildx`, not in compose files

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

## Health Checks

**Do not embed `HEALTHCHECK` in Dockerfiles** for production. Orchestrators (Kubernetes, ECS) manage health probes externally. `HEALTHCHECK` is only useful for standalone Docker Compose testing.

For Quarkus native in distroless images, use the **management interface** (port 9000, plain HTTP) — shell-based scripts (`/dev/tcp`, `curl`) do not work in distroless.

```properties
# application.properties (build-time)
quarkus.management.enabled=true
```

For complete distroless health probe patterns and Docker Compose integration, see [distroless-health-probes.md](../../../pm-dev-oci/skills/oci-standards/standards/distroless-health-probes.md).

## Security Requirements

### OWASP Docker Top 10 Compliance

For the complete OWASP Docker Top 10 control mapping (D01-D10) with threats, mitigations, and implementation examples, see `Skill: pm-dev-oci:oci-security` → `standards/owasp-container-security.md`.

The Docker Compose example above demonstrates OWASP compliance for Quarkus native applications (non-root user, capability dropping, read-only filesystem, resource limits, network isolation).

### Runtime Security Configuration

For generic container runtime hardening (capabilities, seccomp, resource limits, daemon socket protection), see `Skill: pm-dev-oci:oci-security` → `standards/runtime-security.md`.

**Quarkus-specific runtime requirements**:
- Mount PEM certificates as read-only volumes
- Configure HTTPS-only via `quarkus.http.insecure-requests=disabled`
- Use distroless base image (`quay.io/quarkus/quarkus-distroless-image:2.0`)

## Certificate Management

For PEM certificate standards (generation, file permissions, PKCS12 conversion, container mounting), see `Skill: pm-dev-oci:oci-security` → `standards/certificate-management.md`.

### Quarkus SSL Configuration

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

