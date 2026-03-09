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
   - Distroless health probes

2. **oci-security** - Container security best practices
   - Runtime security (non-root, capabilities, read-only FS)
   - Supply chain security (signing, SBOMs, provenance)
   - OWASP Docker Top 10 controls

3. **plan-marshall-plugin** - Domain integration for plan-marshall workflows

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
    │       ├── runtime-security.md
    │       ├── supply-chain-security.md
    │       └── owasp-container-security.md
    └── plan-marshall-plugin/      # Domain integration
        └── SKILL.md
```

## Dependencies

No external dependencies. Pure reference material.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-oci/
