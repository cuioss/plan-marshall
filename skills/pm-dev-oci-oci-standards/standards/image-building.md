# Image Building Best Practices

Secure Dockerfile practices for building minimal, reproducible, and vulnerability-free container images.

## Use Minimal Base Images

Start from the smallest image that satisfies your requirements. Fewer packages means fewer vulnerabilities.

| Base Image | Use Case |
|------------|----------|
| `scratch` | Static binaries (Go, Rust) |
| `distroless` | Runtime-only (Java, Python, Node.js) |
| `alpine` | When a shell is needed for debugging |
| `slim` variants | When specific OS packages are required |

Avoid `latest` tags and full OS images (`ubuntu`, `debian`) in production.

## Multi-Stage Builds

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

### Test-Fixture Images

The multi-stage form above is for an image that has to be reproducible from its sources alone. An image that exists only as a fixture of a test lane — an echo service, a stub backend — and whose sources are a module of the same build is a different case. A build stage inside its Dockerfile runs a full build tool on every lane run: it resolves dependencies outside the host's cache and compiles a module the surrounding build has already compiled or could compile in the same reactor.

Build the fixture's artifact in the surrounding build and reduce the Dockerfile to a single stage that copies it:

```dockerfile
FROM eclipse-temurin:21.0.2_13-jre-alpine
COPY target/quarkus-app/ /app/
USER 1001
ENTRYPOINT ["java", "-jar", "/app/quarkus-run.jar"]
```

Three consequences have to be handled, or the change trades a slow lane for a wrong one:

* **The artifact must exist before the image build.** Every lane that builds the image — including one no CI workflow runs, such as an on-demand comparison or benchmark lane — needs the packaging step in front of it. A lane that built from sources before and is not updated now fails on a missing directory, or copies a stale one.
* **A stale local image is reused silently.** With the build stage gone, nothing in the Dockerfile changes when the fixture's sources change, and a compose stack that finds an image under the expected name starts it. Force the rebuild where the lane starts the stack (`docker compose build`, or `up --build`), and treat "the test ran against an old fixture" as the first suspect when a fixture change shows no effect locally.
* **The build context must contain the artifact.** A `.dockerignore` that excludes `target/` or `build/` — as recommended below for ordinary images — hides exactly the directory this Dockerfile copies. Give the fixture its own context or its own ignore file.

This applies to fixtures only. A deliverable image keeps the form that makes it reproducible.

## Pin Image Versions

Always pin to a specific digest or version tag. Never use `latest` in production.

```dockerfile
# Good - pinned version
FROM eclipse-temurin:21.0.2_13-jre-alpine

# Better - pinned digest
FROM eclipse-temurin@sha256:abc123...

# Bad - mutable tag
FROM eclipse-temurin:latest
```

## COPY Over ADD

Use `COPY` for local files. `ADD` has implicit behaviors (URL fetching, tar extraction) that can introduce unexpected content.

```dockerfile
# Good
COPY requirements.txt .

# Avoid unless tar extraction is intentional
ADD archive.tar.gz /app/
```

## Use .dockerignore

Exclude build artifacts, secrets, and unnecessary files from the build context.

```text
.git
.env
*.secret
node_modules
target/
build/
```

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

# WRONG - false fix: rm in a subsequent RUN does not erase the secret from the prior layer.
# Even if combined in a single RUN, the secret is still leaked in the image history/metadata.
RUN echo "$NPM_TOKEN" > ~/.npmrc && npm install && rm ~/.npmrc
```

A `rm` in a subsequent instruction cannot erase content already frozen into a prior layer; the file remains fully recoverable from that layer's filesystem. While executing the write and `rm` within a single `RUN` instruction does prevent the file from persisting in the layer's filesystem snapshot, the secret is still leaked in the image's metadata and history (visible via `docker history`) — for example through the recorded build command or build arguments.

### Verify Layers Carry No Secrets

`docker history <image>` only surfaces secrets passed via `ENV`/`ARG`/build instructions — it misses secrets written to files during `RUN` steps. Audit the extracted layer contents instead:

```bash
# Catches secrets written to files inside any layer, not just build args
docker save img:tag | strings | grep -iE "token|secret|password"
```

Use Trivy `--scanners secret` as the tool-grade equivalent in CI (see `supply-chain-security.md` for the full Trivy workflow):

```bash
trivy image --scanners secret img:tag
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

The `# syntax=docker/dockerfile:1` directive assumes BuildKit is the active builder. On Docker <23 (where BuildKit is not the default), enable it explicitly or `--mount=type=secret` is silently ignored:

```bash
DOCKER_BUILDKIT=1 docker build --secret id=npmrc,src=.npmrc .
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

## OCI Image Labels

Use standardized OCI annotations for image metadata. These labels enable registry tooling, vulnerability scanners, and orchestrators to identify and manage images.

```dockerfile
LABEL org.opencontainers.image.title="myapp"
LABEL org.opencontainers.image.description="Application description"
LABEL org.opencontainers.image.version="1.2.3"
LABEL org.opencontainers.image.vendor="Organization"
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="Apache-2.0"
```

Set dynamic labels at build time via `--build-arg`:

```dockerfile
ARG GIT_SHA
ARG BUILD_DATE
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
```

```bash
docker build \
  --build-arg GIT_SHA=$(git rev-parse HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) .
```

## Multi-Platform Builds

Build images for multiple architectures using Docker Buildx.

### Setup

```bash
# Create multi-platform builder (one-time)
docker buildx create --name multiarch --use --driver docker-container

# Verify available platforms
docker buildx inspect --bootstrap
```

### Build and Push

```bash
# Build for amd64 and arm64, push to registry
docker buildx build --platform linux/amd64,linux/arm64 \
  -t registry.example.com/myapp:1.0 --push .
```

### CI/CD Integration

In GitHub Actions:

```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: registry.example.com/myapp:${{ github.sha }}
```

### Architecture-Specific Considerations

- Test on all target platforms — behavior can differ (e.g., musl vs glibc on alpine)
- Pin base images that support multi-arch (most official images do)
- Use `--platform=$BUILDPLATFORM` in build stages for faster cross-compilation

## Containerfile Naming

The OCI-standard filename is `Containerfile` (used by Podman and Buildah). Docker uses `Dockerfile`. Both are functionally identical.

- Use `Containerfile` for OCI-first projects or Podman/Buildah-based workflows
- Use `Dockerfile` when Docker is the primary build tool
- Both `docker build` and `podman build` accept either name via `-f` flag
- Buildah provides fine-grained image building without a daemon: `buildah bud -f Containerfile -t myapp .`
