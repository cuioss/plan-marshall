---
name: oci-standards
description: "Use when writing, reviewing, or debugging Dockerfiles and Containerfiles — covers base image selection, multi-stage builds, version pinning, .dockerignore (including excluding secrets from the build context), multi-platform builds, OCI labels, certificate management, secrets management (never embedding secrets in image layers, BuildKit build-time secrets, runtime secret injection), and Quarkus distroless health probes. Activate for any container image building or build-context hardening task. Carries the image-build review rules a code review cites."
user-invocable: false
mode: knowledge
---

# OCI Container Standards

**REFERENCE MODE**: This skill provides reference material for building OCI-compliant container images. Load specific references on-demand based on current task. Do not load all references at once.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for OCI container image building tasks.

**Prohibited actions:**
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- Standards in `image-building.md` define the authoritative rules for Dockerfiles
- Hadolint must pass without errors

## When to Use This Skill

Activate when:
- **Building container images** - Dockerfile best practices, base image selection, layer optimization
- **Multi-platform builds** - Building for amd64/arm64, manifest lists, buildx configuration
- **OCI image metadata** - Standard labels, annotations, image specification compliance
- **Health probes for distroless** - Quarkus management interface, Kubernetes probes, Prometheus scraping without TLS
- **Certificate management** - PEM format, generation, container integration, rotation
- **Reviewing Dockerfiles** - Linting, hygiene, .dockerignore, secrets handling

## Available References

Load references progressively based on current task. **Never load all references at once.**

### 1. Image Building Best Practices

**File**: `standards/image-building.md`

**Load When**:
- Writing or reviewing Dockerfiles/Containerfiles
- Choosing base images
- Configuring multi-stage or multi-platform builds
- Managing build-time secrets
- Linting with Hadolint
- Adding OCI-compliant image labels

**Contents**:
- Minimal base images (scratch, distroless, alpine, slim)
- Multi-stage builds
- Version pinning (tags and digests)
- COPY vs ADD
- .dockerignore
- Secrets management (BuildKit, runtime injection)
- Dockerfile hygiene (Hadolint, layer minimization, port exposure)
- OCI image labels and annotations
- Multi-platform build configuration
- Containerfile naming convention

**Load Command**:
```text
Read standards/image-building.md
```

### 2. Quarkus Distroless Health Probes

**File**: `standards/quarkus-distroless-health-probes.md`

**Load When**:
- Adding health checks to Quarkus distroless container images
- Configuring Quarkus management interface for health/metrics separation
- Setting up Prometheus scraping without TLS complexity
- Debugging missing health endpoints after Quarkus native image builds
- Writing Kubernetes liveness/readiness probes for Quarkus distroless containers

**Contents**:
- Why standard HEALTHCHECK fails in distroless (no shell, no curl)
- Quarkus management interface as the solution (port 9000, plain HTTP)
- Build-time vs runtime properties — critical native image pitfall
- Native build lifecycle requirements (`clean package` vs bare `quarkus:build`)
- Startup log verification for management interface
- Docker Compose, Prometheus, and Kubernetes probe configuration
- Decision matrix for health strategy by image type

**Load Command**:
```text
Read standards/quarkus-distroless-health-probes.md
```

### 3. Certificate Management

**File**: `standards/certificate-management.md`

**Load When**:
- Configuring TLS certificates for containers
- Choosing between PEM and PKCS12 formats
- Setting up certificate generation or rotation
- Mounting certificates securely in containers

**Contents**:
- PEM vs PKCS12 comparison
- Certificate generation script
- PKCS12 to PEM conversion
- Dockerfile and Compose integration patterns
- File permission and security requirements

**Load Command**:
```text
Read standards/certificate-management.md
```

## Quick Reference

### Dockerfile Rules

- Minimal base image (distroless, alpine, slim)
- Multi-stage build separating build and runtime
- Pinned image versions (no `latest`)
- Non-root USER instruction
- COPY instead of ADD
- .dockerignore excludes secrets and build artifacts
- No secrets in ENV, ARG, or COPY
- BuildKit secrets for build-time credentials
- OCI labels (`org.opencontainers.image.*`) present
- Hadolint passes without errors
- Quarkus health probe strategy for distroless (management interface or orchestrator-native probes)

## Review Rules

The review rules of the oci-containers domain for image builds — what a code review looks for in a changed Dockerfile, Containerfile or build context. Security rules for images belong to `pm-dev-oci:oci-security`. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../../../plan-marshall/skills/phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- A `COPY --from=<stage>` whose source path the named build stage no longer produces (a renamed artifact, a moved build output directory), so the image build fails or copies the wrong file into the runtime stage.
- An `ADD` used to copy a local file, so an archive is unpacked into the image instead of copied as the file the next instruction expects.
- An `apt-get update` (or the equivalent package-index refresh) in a different `RUN` layer than the install that depends on it, so a cached, stale index layer makes the install fail or pull outdated packages.
- A `HEALTHCHECK` that runs `curl`, `wget` or a shell in a distroless or scratch image, so the command does not exist and the container is reported unhealthy however the application behaves.
- A Quarkus management-interface property (`quarkus.management.*`) set only at runtime when it is fixed at build time, so the native image has no management endpoint and every health probe against it fails.
- A `.dockerignore` that does not exclude local build output (`target/`, `node_modules/`, `dist/`), so a stale local artifact is copied into the image in place of the freshly built one.
- A multi-platform build whose `RUN` step downloads or copies a binary for a single architecture, so the image for the other platform carries a binary it cannot execute.
