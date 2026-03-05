# OCI Container Standards

OCI container security standards and best practices for building and running secure container images.

## Purpose

This bundle provides comprehensive OCI container security expertise through reference skills covering image building, runtime hardening, secrets management, vulnerability scanning, supply chain security, and OWASP container security controls.

## Components Included

### Skills (2 skills)

1. **oci-security** - Container security best practices
   - Image building (minimal bases, multi-stage, pinned versions)
   - Runtime security (non-root, capabilities, read-only FS)
   - Secrets management and vulnerability scanning
   - Supply chain security (signing, SBOMs, provenance)
   - Progressive disclosure to OWASP sub-document

2. **plan-marshall-plugin** - Domain integration for plan-marshall workflows

## Architecture

```
pm-dev-oci/
└── skills/
    ├── oci-security/              # Security best practices (reference)
    │   ├── SKILL.md
    │   └── standards/
    │       └── owasp-container-security.md
    └── plan-marshall-plugin/      # Domain integration
        └── SKILL.md
```

## Bundle Statistics

- **Skills**: 2 (domain knowledge references)

## Dependencies

No external dependencies. Pure reference material.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-oci/
