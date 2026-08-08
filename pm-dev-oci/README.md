# OCI Container Standards

OCI container standards and security best practices for building and running secure container images.

## Purpose

This bundle provides comprehensive OCI container expertise through reference skills covering image building, multi-platform builds, distroless health probes, runtime hardening, vulnerability scanning, supply chain security, and OWASP container security controls.

## Components Included

### Skills (3 skills)

1. **oci-standards** - General OCI container practices
   - Image building (minimal bases, multi-stage, pinned versions)
   - OCI image labels and annotations
   - Multi-platform builds (amd64/arm64)
   - Containerfile naming convention
   - Quarkus distroless health probes
   - Certificate management (PEM, generation, container integration)

2. **oci-security** - Container security best practices
   - OWASP Docker Top 10 controls (primary reference)
   - Runtime security quick reference (checklist + hardened template)
   - Supply chain security quick reference (scanning, signing, SBOMs)

3. **ext-triage-oci** - Triage extension for finalize phase
   - Hadolint finding suppression and severity
   - Trivy/scanner CVE suppression and severity
   - Runtime security finding triage

### Infrastructure

- **plan-marshall-plugin** - Domain extension for plan-marshall workflow integration (not registered in plugin.json)

## Architecture

```
pm-dev-oci/
└── skills/
    ├── oci-standards/             # General OCI practices (reference)
    │   ├── SKILL.md
    │   └── standards/
    │       ├── image-building.md
    │       ├── quarkus-distroless-health-probes.md
    │       └── certificate-management.md
    ├── oci-security/              # Security best practices (reference)
    │   ├── SKILL.md
    │   └── standards/
    │       ├── owasp-container-security.md   # Primary reference (D01-D10)
    │       ├── runtime-security.md           # Quick reference checklist
    │       └── supply-chain-security.md      # Quick reference checklist
    ├── ext-triage-oci/            # Triage extension
    │   ├── SKILL.md
    │   └── standards/
    │       ├── suppression.md
    │       └── severity.md
    └── plan-marshall-plugin/      # Domain extension (not registered)
        ├── SKILL.md
        └── extension.py
```

## Dependencies

No external dependencies. Pure reference material.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-oci/
