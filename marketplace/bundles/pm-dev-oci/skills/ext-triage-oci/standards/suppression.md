# OCI Container Suppression Syntax

How to suppress various types of findings in Dockerfiles and container scanning.

## Hadolint Suppressions

Hadolint is the standard Dockerfile linter. Suppressions can be applied at three levels.

### Inline Suppression

```dockerfile
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y curl

# Multiple rules
# hadolint ignore=DL3008,DL3015
RUN apt-get update && apt-get install -y curl wget
```

### Global Configuration (.hadolint.yaml)

```yaml
ignored:
  - DL3008  # Pin versions in apt-get
  - DL3018  # Pin versions in apk add

trustedRegistries:
  - docker.io
  - gcr.io
  - quay.io
```

### Common Hadolint Rules

| Rule | Description | When to Suppress |
|------|-------------|------------------|
| DL3006 | Always tag image version | Never (pin versions) |
| DL3007 | Using `latest` tag | Never (pin versions) |
| DL3008 | Pin apt-get versions | When exact version not available in base image |
| DL3018 | Pin apk add versions | When exact version not available in base image |
| DL3025 | Use JSON form for CMD | When shell features are needed |
| DL3059 | Multiple consecutive RUN | When layer caching is intentional |
| SC2086 | Double-quote variables | When word splitting is intentional |

### Best Practices

```dockerfile
# Good - explains why suppression is appropriate
# hadolint ignore=DL3008 -- versions float with base image, rebuilt weekly
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates

# Bad - no justification
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y curl
```

## Trivy Suppressions

### .trivyignore File

Place in the repository root or specify with `--ignorefile`.

```
# CVE with no available fix, tracked in JIRA-789
CVE-2024-12345

# False positive - vendored and patched
CVE-2023-67890

# Expires after fix is available
CVE-2024-11111  # Until: 2025-06-01
```

### Inline Annotation (Trivy 0.50+)

```dockerfile
# trivy:ignore:CVE-2024-12345
RUN apt-get install -y vulnerable-but-needed-package
```

### Trivy Policy (.trivy.yaml)

```yaml
severity:
  - CRITICAL
  - HIGH
ignore-unfixed: true
```

## Docker Scout Suppressions

### Exceptions via Policy

```yaml
# .docker/scout-policy.yaml
exceptions:
  - cve: CVE-2024-12345
    reason: "No fix available, mitigated by network policy"
    expires: "2025-06-01"
```

## When NOT to Suppress

- CRITICAL CVEs with available fixes (update the dependency)
- Hadolint DL3006/DL3007 (`latest` tag usage — always pin)
- Security-relevant rules (secrets in layers, root user)
- Issues that can be fixed with minimal effort
- Issues in new Dockerfiles (only suppress in legacy)
