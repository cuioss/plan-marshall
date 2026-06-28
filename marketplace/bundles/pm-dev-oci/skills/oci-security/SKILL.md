---
name: oci-security
description: "Use when hardening container runtime configuration, scanning for vulnerabilities, securing the image supply chain, or auditing against OWASP Docker Top 10. Covers capability dropping, read-only filesystems, image signing, SBOMs, and Trivy/Cosign/Syft workflows. Cross-references the cross-cutting foundations in plan-marshall:persona-security-expert."
user-invocable: false
mode: knowledge
---

# OCI Container Security

**REFERENCE MODE**: This skill provides reference material for securing OCI containers at runtime and across the supply chain. Load specific references on-demand based on current task. Do not load all references at once.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for container security hardening tasks.

**Prohibited actions:**
- Do not run containers as root; always use non-root USER instruction
- Do not mount Docker daemon socket into containers
- Do not skip vulnerability scanning in CI/CD pipelines
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- All containers must drop all capabilities (`--cap-drop=ALL`) and selectively add required ones
- Read-only filesystems required with tmpfs for write directories
- Images must be signed and verified before deployment
- SBOM must be generated and attached to images

For general image building practices (Dockerfiles, base images, multi-platform builds), see `Skill: pm-dev-oci:oci-standards`.

## When to Use This Skill

Activate when:
- **Hardening runtime** - Non-root users, capabilities, read-only filesystems, resource limits
- **Scanning vulnerabilities** - CI/CD integration, tool selection, remediation workflows
- **Securing supply chain** - Image signing, SBOMs, provenance attestation
- **OWASP compliance** - Docker Top 10 controls, threat modeling, compliance audits

## Available References

Load references progressively based on current task. **Never load all references at once.**

### 1. OWASP Container Security (Primary Reference)

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

### 2. Runtime Security (Quick Reference)

**File**: `standards/runtime-security.md`

**Load When**:
- Need a quick hardening checklist without full OWASP detail
- Copy-pasteable docker-compose hardened template
- Capability reference table

Cross-references OWASP controls D01, D03, D04, D05, D07, D09, D10.

**Load Command**:
```
Read standards/runtime-security.md
```

### 3. Supply Chain Security (Quick Reference)

**File**: `standards/supply-chain-security.md`

**Load When**:
- Need a quick pipeline workflow and tool reference
- Copy-pasteable Trivy, Cosign, Syft commands

Cross-references OWASP controls D02, D08.

**Load Command**:
```
Read standards/supply-chain-security.md
```

## Cross-Cutting Foundations (delegated upward)

This skill retains the container-specific mechanics (capability dropping, read-only filesystems, image signing, SBOMs, Trivy/Cosign/Syft) in its `standards/`. The cross-cutting conceptual foundations behind those mechanics live in the centralized `plan-marshall:persona-security-expert` sub-documents — load the matching foundation, then return here for the container realization. No content duplication:

| Container mechanic (here) | Centralized foundation (there) |
|---------------------------|-------------------------------|
| Container threat modeling (the Docker Top 10 lens applied per deployment) | [`threat-modeling-stride.md`](../../../plan-marshall/skills/persona-security-expert/standards/threat-modeling-stride.md) — the general STRIDE method behind it |
| Capability dropping (`--cap-drop=ALL`), `no-new-privileges`, non-root user; minimal hardened base images | [`secure-design-principles.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) — least privilege, secure by default, fail securely |
| Container secret injection (avoid `ENV`/`ARG`, use mounted volumes / sidecars) | [`secrets-handling.md`](../../../plan-marshall/skills/persona-security-expert/standards/secrets-handling.md) — the environment-variable pitfall and secret-manager integration |
| Image signing, SBOMs, provenance attestation (Trivy/Cosign/Syft are the container mechanics) | [`dependency-supply-chain.md`](../../../plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md) — the cross-cutting SBOM, provenance/SLSA, and artifact-signing authority; maps to OWASP A03 / A08 in [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |

> **Docker Top 10 ≠ web Application Top 10.** The OWASP **Docker** Top 10 (D01–D10) covered by this skill's `standards/owasp-container-security.md` is container-specific and stays local. The general OWASP web **Application** Top 10 (A01–A10) lives in the centralized [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md). Cross-reference them; do not merge them.

## Quick Reference

### Runtime Security Rules

- `--cap-drop=ALL` with selective `--cap-add`
- `--security-opt=no-new-privileges`
- `--read-only` with tmpfs for write directories
- Memory and CPU limits set
- Docker socket NOT mounted
- Network segmented per service role
- Images signed and verified
- SBOM generated and attached
- Vulnerability scan passes (no CRITICAL/HIGH)
