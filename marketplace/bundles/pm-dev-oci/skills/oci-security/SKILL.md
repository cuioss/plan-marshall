---
name: oci-security
description: OCI container security best practices covering image building, runtime hardening, secrets management, and supply chain security
user-invocable: false
---

# OCI Container Security

**REFERENCE MODE**: This skill provides reference material for building and running secure OCI containers. Load specific references on-demand based on current task. Do not load all references at once.

## When to Use This Skill

Activate when:
- **Building container images** - Dockerfile best practices, base image selection, layer optimization
- **Hardening runtime** - Non-root users, capabilities, read-only filesystems, resource limits
- **Managing secrets** - BuildKit secrets, runtime injection, avoiding embedded credentials
- **Scanning vulnerabilities** - CI/CD integration, tool selection, remediation workflows
- **Securing supply chain** - Image signing, SBOMs, provenance attestation
- **Reviewing Dockerfiles** - Linting, security audit, compliance checks

## Available References

Load references progressively based on current task. **Never load all references at once.**

### 1. Image Building Best Practices

**File**: `standards/image-building.md`

**Load When**:
- Writing or reviewing Dockerfiles
- Choosing base images
- Configuring multi-stage builds
- Managing build-time secrets
- Linting with Hadolint

**Contents**:
- Minimal base images (scratch, distroless, alpine, slim)
- Multi-stage builds
- Version pinning (tags and digests)
- COPY vs ADD
- .dockerignore
- Secrets management (BuildKit, runtime injection)
- Dockerfile hygiene (Hadolint, layer minimization, port exposure)

**Load Command**:
```
Read standards/image-building.md
```

### 2. Runtime Security

**File**: `standards/runtime-security.md`

**Load When**:
- Configuring container runtime security
- Hardening docker-compose or Kubernetes deployments
- Setting resource limits and capabilities
- Reviewing CIS Docker Benchmark compliance

**Contents**:
- Non-root user mapping
- Capability dropping and selective adds
- Read-only filesystems with tmpfs
- CPU/memory/PID resource limits
- Docker daemon socket protection
- Network segmentation
- Immutable/ephemeral container patterns
- CIS Docker Benchmark overview

**Load Command**:
```
Read standards/runtime-security.md
```

### 3. Supply Chain Security

**File**: `standards/supply-chain-security.md`

**Load When**:
- Setting up vulnerability scanning in CI/CD
- Implementing image signing workflows
- Generating SBOMs for compliance
- Configuring SLSA provenance

**Contents**:
- Vulnerability scanning tools (Trivy, Grype, Snyk, Docker Scout)
- CI/CD scan workflow
- Regular rebuild schedules
- Image signing with Cosign
- SBOM generation with Syft
- SLSA provenance attestation

**Load Command**:
```
Read standards/supply-chain-security.md
```

### 4. OWASP Container Security

**File**: `standards/owasp-container-security.md`

**Load When**:
- Mapping security controls to OWASP Docker Top 10
- Compliance audits requiring OWASP alignment
- Detailed threat modeling for container deployments
- Understanding specific OWASP control implementations

**Contents**:
- OWASP Docker Top 10 (D01-D10) with threats, mitigations, examples
- Container Security Verification Standard recommendations
- Pre-deployment verification checklist

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
