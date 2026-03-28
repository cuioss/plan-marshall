# Supply Chain Security Quick Reference

Concise supply chain security checklist. For detailed threat descriptions, implementation examples, and CI/CD integration, see the OWASP Container Security reference (`standards/owasp-container-security.md`, controls D02, D08).

## Pipeline Workflow

```
Build image → Scan (fail on CRITICAL/HIGH) → Sign → Generate SBOM → Push to registry
```

## Vulnerability Scanning

| Tool | Type | Integration |
|------|------|-------------|
| Trivy | Open source | GitHub Actions, GitLab CI |
| Grype | Open source | CLI, CI/CD plugins |
| Snyk Container | Commercial | GitHub, GitLab, CLI |
| Docker Scout | Docker native | Docker Desktop, CI/CD |

```bash
# Trivy scan with severity gate
trivy image --severity CRITICAL,HIGH --exit-code 1 myapp:v1.0
```

## Image Signing (Cosign)

```bash
# Sign image
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Verify before deployment
cosign verify --key cosign.pub registry.example.com/myapp:v1.0
```

## SBOM Generation (Syft)

```bash
# Generate SBOM
syft registry.example.com/myapp:v1.0 -o spdx-json > sbom.json

# Attach SBOM to image
cosign attach sbom --sbom sbom.json registry.example.com/myapp:v1.0
```

## Checklist

| Control | Rule | OWASP |
|---------|------|-------|
| Vulnerability scan in CI/CD | Fail pipeline on CRITICAL/HIGH | D02 |
| Regular rebuilds | Weekly minimum, even without app changes | D02 |
| Image signing | Cosign or Docker Content Trust | D08 |
| Signature verification | Admission controller (Kyverno/OPA) in Kubernetes | D08 |
| SBOM generation | Attach SBOM to every released image | D08 |
| SLSA provenance | Attest build origin and integrity | D08 |
| Private registry | Access-controlled, no public pulls in production | D08 |
