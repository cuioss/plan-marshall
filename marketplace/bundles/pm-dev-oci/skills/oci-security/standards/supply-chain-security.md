# Supply Chain Security

Vulnerability scanning, image signing, SBOMs, and provenance attestation for securing the container supply chain.

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

## Image Signing

Use Cosign or Docker Content Trust to sign images and verify signatures before deployment.

```bash
# Sign with Cosign
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Verify before pull
cosign verify --key cosign.pub registry.example.com/myapp:v1.0
```

## SBOMs

Create Software Bills of Materials for every image to track components and vulnerabilities.

```bash
# Generate SBOM with Syft
syft registry.example.com/myapp:v1.0 -o spdx-json > sbom.json

# Attach SBOM to image with Cosign
cosign attach sbom --sbom sbom.json registry.example.com/myapp:v1.0
```

## SLSA Provenance

Implement SLSA (Supply-chain Levels for Software Artifacts) provenance to attest build origin and integrity.
