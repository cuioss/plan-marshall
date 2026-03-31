# Health Probes for Distroless Containers

Strategies for implementing health checks in distroless container images that have no shell, no package manager, and no utilities like `curl` or `wget`.

## The Distroless Challenge

Distroless images (e.g., `quay.io/quarkus/quarkus-distroless-image`, Google's `gcr.io/distroless`) contain only the application runtime — no shell, no coreutils. Standard Docker `HEALTHCHECK` instructions that rely on `curl`, `wget`, or shell built-ins (`/dev/tcp`) cannot work.

### What Does NOT Work in Distroless

```dockerfile
# ALL of these fail — no shell, no curl, no wget
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1
HEALTHCHECK CMD wget -q -O- http://localhost:8080/health || exit 1
HEALTHCHECK CMD echo -n '' > /dev/tcp/127.0.0.1/8080 2>/dev/null || exit 1
```

## Solution: Quarkus Management Interface

For Quarkus native applications in distroless images, enable the **management interface** to expose health/metrics on a separate plain HTTP port (default 9000). This allows orchestrators and compose health checks to probe without TLS complexity.

### Configuration

```properties
# application.properties — build-time property (cannot be overridden at runtime)
quarkus.management.enabled=true
```

Quarkus defaults: port 9000, host 0.0.0.0, no TLS — correct for internal health probes.

**CRITICAL**: `quarkus.management.enabled` is a **build-time fixed** property in Quarkus. It is baked into the native executable during augmentation. Setting `QUARKUS_MANAGEMENT_ENABLED=true` as a runtime environment variable has **no effect** on native images. The property must be in `application.properties` before the native build.

### Native Build Requirement

The native image must be built with the full Maven lifecycle to ensure build-time augmentation picks up the property:

```bash
# Correct — full lifecycle ensures resources + augmentation
./mvnw clean package -Pnative -pl <module> -DskipTests

# WRONG — quarkus:build alone may skip resource processing
./mvnw -Pnative quarkus:build -pl <module>
```

### Startup Log Verification

When management is properly enabled, the startup log shows the management port:

```
INFO  api-sheriff started in 0.147s. Listening on: http://0.0.0.0:8080 and https://0.0.0.0:8443. Management interface listening on http://0.0.0.0:9000.
```

If the log only shows `Listening on: http://... and https://...` without the management interface line, the property was not picked up during the native build.

### Required Extensions

No additional Maven dependency is needed. The management interface is built into Quarkus and activates automatically when extensions that use it are present:

- `quarkus-smallrye-health` (health endpoints)
- `quarkus-micrometer` / `quarkus-micrometer-registry-prometheus` (metrics)

### Dockerfile

Expose both the application and management ports:

```dockerfile
EXPOSE 8443 9000
```

### Docker Compose

Map the management port and probe it for health:

```yaml
services:
  app:
    ports:
      - "10443:8443"  # Application (HTTPS)
      - "19000:9000"  # Management (HTTP — health/metrics)
```

### Health Probe (Script-Based)

```bash
# Plain HTTP, no -k (insecure TLS skip) needed
curl -sf http://localhost:19000/q/health/live
```

### Prometheus Scraping

Scrape metrics from the management port over plain HTTP — no `insecure_skip_verify` required:

```yaml
scrape_configs:
  - job_name: 'quarkus'
    static_configs:
      - targets: ['app:9000']
    metrics_path: '/q/metrics'
    scheme: http
```

## Alternative: UBI Micro with Shell

When a shell IS available (e.g., `quay.io/quarkus/ubi9-quarkus-micro-image`), a TCP port probe works without any HTTP client:

```dockerfile
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD echo -n '' > /dev/tcp/127.0.0.1/8443 2>/dev/null || exit 1
```

This checks that the port is listening but does not validate HTTP response codes. Use only when distroless is not feasible (e.g., JFR profiling images that need shell access).

## Kubernetes Probes

Kubernetes natively supports HTTP probes without requiring any binaries in the container:

```yaml
livenessProbe:
  httpGet:
    path: /q/health/live
    port: 9000      # Management port
    scheme: HTTP
readinessProbe:
  httpGet:
    path: /q/health/ready
    port: 9000
    scheme: HTTP
startupProbe:
  httpGet:
    path: /q/health/started
    port: 9000
    scheme: HTTP
  failureThreshold: 30
  periodSeconds: 2
```

With the management interface, Kubernetes probes use plain HTTP on port 9000 — no TLS configuration, no certificates in the probe spec.

## Decision Matrix

| Scenario | Image Type | Health Strategy |
|----------|-----------|-----------------|
| Production (Quarkus native) | Distroless | Management interface (port 9000) |
| Profiling / debugging | UBI micro | `/dev/tcp` port probe or management interface |
| Kubernetes deployment | Any | Native HTTP probes on management port |
| Docker Compose | Any | `curl -sf http://host:9000/q/health/live` from host |
| Prometheus scraping | Any | Scrape `http://app:9000/q/metrics` (no TLS) |
