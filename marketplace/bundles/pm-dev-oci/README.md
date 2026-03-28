# OCI Container Standards

OCI container standards and security best practices for building and running secure container images.

## Purpose

This bundle provides comprehensive OCI container expertise through reference skills covering image building, multi-platform builds, distroless health probes, runtime hardening, vulnerability scanning, supply chain security, and OWASP container security controls.

## Components Included

### Skills (4 skills)

1. **oci-standards** - General OCI container practices
   - Image building (minimal bases, multi-stage, pinned versions)
   - OCI image labels and annotations
   - Multi-platform builds (amd64/arm64)
   - Containerfile naming convention
   - Distroless health probes

2. **oci-security** - Container security best practices
   - OWASP Docker Top 10 controls (primary reference)
   - Runtime security quick reference (checklist + hardened template)
   - Supply chain security quick reference (scanning, signing, SBOMs)
   - Certificate management (PEM, generation, container integration)

3. **ext-triage-oci** - Triage extension for finalize phase
   - Hadolint finding suppression and severity
   - Trivy/scanner CVE suppression and severity
   - Runtime security finding triage

4. **plan-marshall-plugin** - Domain integration for plan-marshall workflows

## Architecture

```
pm-dev-oci/
└── skills/
    ├── oci-standards/             # General OCI practices (reference)
    │   ├── SKILL.md
    │   └── standards/
    │       ├── image-building.md
    │       └── distroless-health-probes.md
    ├── oci-security/              # Security best practices (reference)
    │   ├── SKILL.md
    │   └── standards/
    │       ├── owasp-container-security.md   # Primary reference (D01-D10)
    │       ├── runtime-security.md           # Quick reference checklist
    │       ├── supply-chain-security.md      # Quick reference checklist
    │       └── certificate-management.md
    ├── ext-triage-oci/            # Triage extension
    │   ├── SKILL.md
    │   └── standards/
    │       ├── suppression.md
    │       └── severity.md
    └── plan-marshall-plugin/      # Domain integration
        ├── SKILL.md
        └── extension.py
```

## Dependencies

No external dependencies. Pure reference material.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-oci/
