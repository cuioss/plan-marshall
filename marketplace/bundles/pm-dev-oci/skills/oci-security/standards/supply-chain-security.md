# Supply Chain Security Quick Reference

Concise supply chain security checklist. For detailed threat descriptions, implementation examples, and CI/CD integration, see the OWASP Container Security reference (`standards/owasp-container-security.md`, controls D02, D08).

## Pipeline Workflow

```
Build image → Scan (fail on CRITICAL/HIGH) → Sign → Generate SBOM → Push to registry
```

## Tool Reference

| Tool | Type | Purpose |
|------|------|---------|
| Trivy | Open source | Vulnerability scanning |
| Grype | Open source | Vulnerability scanning |
| Snyk Container | Commercial | Vulnerability scanning |
| Docker Scout | Docker native | Vulnerability scanning |
| Cosign (Sigstore) | Open source | Image signing and verification |
| Syft | Open source | SBOM generation |

## Quick Commands

```bash
# Vulnerability scan with severity gate
trivy image --severity CRITICAL,HIGH --exit-code 1 myapp:v1.0

# Sign image (Cosign keyless via Fulcio/Rekor)
cosign sign registry.example.com/myapp:v1.0

# Verify before deployment
cosign verify registry.example.com/myapp:v1.0

# Generate and attach SBOM
syft registry.example.com/myapp:v1.0 -o spdx-json > sbom.json
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
