---
name: java-quarkus
description: Quarkus-specific CDI standards with testing, native image support, and GraalVM reflection configuration
user-invocable: false
---

# Java CDI Quarkus Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Quarkus-specific CDI standards extending core CDI patterns with Quarkus testing, native image support, and GraalVM reflection configuration.

## Prerequisites

This skill applies to Quarkus projects:
- `io.quarkus:quarkus-junit5` (Quarkus testing)
- `io.quarkus:quarkus-jacoco` (coverage)

## Workflow

### Step 1: Load Quarkus Testing Standards

Load this standard for any Quarkus testing work.

```
Read: standards/quarkus-testing.md
```

This provides foundational rules for:
- @QuarkusTest and @QuarkusIntegrationTest
- JaCoCo configuration for Quarkus
- REST Assured patterns

### Step 2: Load Additional Standards (As Needed)

**External Integration Testing** (load for Docker-based IT):

See `pm-dev-java:junit-integration` → `standards/external-integration-testing.md`. For Quarkus-specific paths, use `/q/health` and `/q/metrics` on the management interface.

**Native Image** (load for GraalVM work):
```
Read: standards/quarkus-native.md
```

Use when: Building native images or troubleshooting native compilation.

**Reflection Registration** (load for native issues):
```
Read: standards/quarkus-reflection.md
```

Use when: Resolving reflection issues in native builds.

**Container Standards** (load for Docker deployment):
```
Read: standards/container.md
```

Use when: Configuring container images, Docker Compose, health checks, or certificate management.

## Related Skills

- `pm-dev-java:java-cdi` - Core CDI patterns
- `pm-dev-java:junit-integration` - Maven integration testing
- `pm-dev-java:junit-core` - JUnit 5 core patterns

## Standards Reference

| Standard | Purpose |
|----------|---------|
| quarkus-testing.md | @QuarkusTest, JaCoCo, REST Assured |
| quarkus-native.md | GraalVM native image builds |
| quarkus-reflection.md | Reflection registration for native |
| container.md | Docker deployment, health checks, certificate management |
