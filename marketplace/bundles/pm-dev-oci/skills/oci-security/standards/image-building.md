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

```
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
