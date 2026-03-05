---
name: oci-security
description: OCI container security best practices covering image building, runtime hardening, secrets management, and supply chain security
user-invocable: false
---

# OCI Container Security

**REFERENCE MODE**: This skill provides reference material for building and running secure OCI containers. Load the OWASP sub-document on-demand when detailed control mappings are needed.

## When to Use This Skill

Activate when:
- **Building container images** - Dockerfile best practices, base image selection, layer optimization
- **Hardening runtime** - Non-root users, capabilities, read-only filesystems, resource limits
- **Managing secrets** - BuildKit secrets, runtime injection, avoiding embedded credentials
- **Scanning vulnerabilities** - CI/CD integration, tool selection, remediation workflows
- **Securing supply chain** - Image signing, SBOMs, provenance attestation
- **Reviewing Dockerfiles** - Linting, security audit, compliance checks

## Image Building

### Use Minimal Base Images

Start from the smallest image that satisfies your requirements. Fewer packages means fewer vulnerabilities.

| Base Image | Use Case |
|------------|----------|
| `scratch` | Static binaries (Go, Rust) |
| `distroless` | Runtime-only (Java, Python, Node.js) |
| `alpine` | When a shell is needed for debugging |
| `slim` variants | When specific OS packages are required |

Avoid `latest` tags and full OS images (`ubuntu`, `debian`) in production.

### Multi-Stage Builds

Separate build-time dependencies from runtime. The final image contains only what is needed to run.

```dockerfile
# Build stage
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests

# Runtime stage
FROM eclipse-temurin:21-jre-alpine
COPY --from=builder /app/target/*.jar /app/app.jar
USER 1001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Pin Image Versions

Always pin to a specific digest or version tag. Never use `latest` in production.

```dockerfile
# Good - pinned version
FROM eclipse-temurin:21.0.2_13-jre-alpine

# Better - pinned digest
FROM eclipse-temurin@sha256:abc123...

# Bad - mutable tag
FROM eclipse-temurin:latest
```

### COPY Over ADD

Use `COPY` for local files. `ADD` has implicit behaviors (URL fetching, tar extraction) that can introduce unexpected content.

```dockerfile
# Good
COPY requirements.txt .

# Avoid unless tar extraction is intentional
ADD archive.tar.gz /app/
```

### Use .dockerignore

Exclude build artifacts, secrets, and unnecessary files from the build context.

```
.git
.env
*.secret
node_modules
target/
build/
```

## Runtime Security

### Run as Non-Root

Never run containers as root. Create a dedicated user or use a numeric UID.

```dockerfile
# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Or use numeric UID (no user creation needed)
USER 1001
```

Verify at runtime: `docker run --user 1001:1001`

### Drop Capabilities

Remove all Linux capabilities and add back only what is needed.

```yaml
# docker-compose.yml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if binding to ports < 1024
```

```bash
# docker run
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE --security-opt=no-new-privileges myapp
```

### Read-Only Filesystem

Mount the container filesystem as read-only. Use tmpfs for directories that need writes.

```bash
docker run --read-only --tmpfs /tmp --tmpfs /var/cache myapp
```

```yaml
# docker-compose.yml
read_only: true
tmpfs:
  - /tmp
  - /var/cache
```

### Resource Limits

Set CPU and memory limits to prevent resource exhaustion attacks.

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Protect the Docker Daemon Socket

Never mount `/var/run/docker.sock` into containers. This grants root-equivalent access to the host.

## Secrets Management

### Never Embed Secrets in Images

Secrets in `ENV`, `COPY`, or `ARG` instructions persist in image layers and are extractable.

```dockerfile
# WRONG - secret persists in layer
ENV DATABASE_PASSWORD=mysecret
COPY .env /app/

# WRONG - visible in image history
ARG SECRET_KEY
RUN curl -H "Authorization: $SECRET_KEY" https://api.example.com
```

### Use BuildKit Secrets

For build-time secrets (private registries, API keys during build):

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm install
```

```bash
docker build --secret id=npmrc,src=.npmrc .
```

### Runtime Secret Injection

Inject secrets at runtime via environment variables or mounted volumes:

```bash
# Environment variable (acceptable for non-sensitive config)
docker run -e DATABASE_URL=postgres://... myapp

# Mounted secret file (preferred for sensitive data)
docker run -v /run/secrets/db_password:/run/secrets/db_password:ro myapp
```

Use orchestrator-native secret management (Kubernetes Secrets, Docker Swarm secrets, Vault) in production.

## Vulnerability Scanning

### Scan in CI/CD Pipeline

Integrate image scanning into every build. Fail the pipeline on critical/high vulnerabilities.

| Tool | Type | Integration |
|------|------|-------------|
| Trivy | Open source | GitHub Actions, GitLab CI |
| Grype | Open source | CLI, CI/CD plugins |
| Snyk Container | Commercial | GitHub, GitLab, CLI |
| Docker Scout | Docker native | Docker Desktop, CI/CD |

### Scan Workflow

```
Build image → Scan → Fail on CRITICAL/HIGH → Push to registry (if clean)
```

### Rebuild Regularly

Base images receive security patches. Rebuild images on a regular schedule (weekly minimum) even without application changes.

## Supply Chain Security

### Sign Images

Use Cosign or Docker Content Trust to sign images and verify signatures before deployment.

```bash
# Sign with Cosign
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Verify before pull
cosign verify --key cosign.pub registry.example.com/myapp:v1.0
```

### Generate SBOMs

Create Software Bills of Materials for every image to track components and vulnerabilities.

```bash
# Generate SBOM with Syft
syft registry.example.com/myapp:v1.0 -o spdx-json > sbom.json

# Attach SBOM to image with Cosign
cosign attach sbom --sbom sbom.json registry.example.com/myapp:v1.0
```

### SLSA Provenance

Implement SLSA (Supply-chain Levels for Software Artifacts) provenance to attest build origin and integrity.

## Dockerfile Hygiene

### Lint with Hadolint

Use Hadolint to catch Dockerfile issues before build.

```bash
hadolint Dockerfile
```

Key rules:
- `DL3006` - Always tag the version of an image explicitly
- `DL3007` - Using latest is always a bad practice
- `DL3008` - Pin versions in apt-get install
- `DL3018` - Pin versions in apk add
- `DL3025` - Use JSON form for CMD/ENTRYPOINT

### Minimize Layers

Combine related `RUN` instructions to reduce layers and image size.

```dockerfile
# Good - single layer for package installation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl && \
    rm -rf /var/lib/apt/lists/*
```

### Expose Only Required Ports

Declare only the ports your application needs. Do not expose debug or management ports in production images.

```dockerfile
# Explicit single port
EXPOSE 8080
```

## Container Orchestration Security

### Network Segmentation

Isolate containers on separate networks. Frontend containers should not directly access database containers.

### Ephemeral Containers

Treat containers as immutable and ephemeral. Do not patch running containers - rebuild and redeploy.

### CIS Docker Benchmark

Follow the CIS Docker Benchmark for host and daemon hardening. Key areas:
- Host configuration and auditing
- Docker daemon configuration
- Container runtime restrictions
- Security operations

## Available References

### OWASP Container Security

**File**: `standards/owasp-container-security.md`

**Load When**:
- Mapping security controls to OWASP Docker Top 10
- Compliance audits requiring OWASP alignment
- Detailed threat modeling for container deployments
- Understanding specific OWASP control implementations

**Contents**:
- OWASP Docker Top 10 (D01-D10) with threats, mitigations, examples
- Container Security Verification Standard recommendations

**Load Command**:
```
Read standards/owasp-container-security.md
```

## Quick Reference

### Dockerfile Security Checklist

- [ ] Minimal base image (distroless, alpine, slim)
- [ ] Multi-stage build separating build and runtime
- [ ] Pinned image versions (no `latest`)
- [ ] Non-root USER instruction
- [ ] COPY instead of ADD
- [ ] .dockerignore excludes secrets and build artifacts
- [ ] No secrets in ENV, ARG, or COPY
- [ ] BuildKit secrets for build-time credentials
- [ ] Hadolint passes without errors
- [ ] Vulnerability scan passes (no CRITICAL/HIGH)

### Runtime Security Checklist

- [ ] `--cap-drop=ALL` with selective `--cap-add`
- [ ] `--security-opt=no-new-privileges`
- [ ] `--read-only` with tmpfs for write directories
- [ ] Memory and CPU limits set
- [ ] Docker socket NOT mounted
- [ ] Network segmented per service role
- [ ] Images signed and verified
- [ ] SBOM generated and attached
