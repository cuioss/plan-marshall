---
name: ext-triage-oci
description: Triage extension for OCI container findings during plan-finalize phase
user-invocable: false
---

# OCI Container Triage Extension

Provides decision-making knowledge for triaging OCI container and Dockerfile findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing OCI container-related findings. It provides domain-specific knowledge for deciding whether to fix, suppress, or accept findings.

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain oci-containers --type triage` during finalize phase when:

1. Hadolint reports Dockerfile violations
2. Trivy or other scanners report image vulnerabilities
3. Docker build failures occur
4. Container runtime security issues are flagged
5. PR review comments reference Dockerfile or container configuration

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | Dockerfile and scanner suppression syntax (hadolint ignore, trivyignore) |
| [severity.md](standards/severity.md) | OCI-specific severity guidelines and decision criteria |

## Extension Registration

Registered via the `plan-marshall-plugin/extension.py` in this bundle. The `provides_triage()` method returns `pm-dev-oci:ext-triage-oci`, which the plan-marshall workflow discovers at runtime for the `oci-containers` domain.

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| Hadolint rule | `# hadolint ignore=DL3008` (inline) |
| Hadolint global | `.hadolint.yaml` with `ignored` list |
| Trivy CVE | `.trivyignore` file with CVE IDs |
| Trivy inline | `# trivy:ignore:CVE-2024-XXXX` |
| Docker Scout | `.docker/scout-policy.yaml` exceptions |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| CRITICAL (CVE) | **Fix** (mandatory, update base image or dependency) |
| HIGH (CVE) | **Fix** (mandatory for production images) |
| DL3xxx error | Fix (Hadolint best practice violation) |
| DL3xxx warning | Fix or suppress with justification |
| DL3xxx info | Accept or fix opportunistically |

### Acceptable to Accept

- Base image CVEs with no available patch (document and track)
- Hadolint style warnings in legacy Dockerfiles with migration plan
- Scanner false positives for vendored or patched dependencies
- Test-only images not deployed to production

## Related Documents

- `plan-marshall:extension-api` - Triage extension contract
- `pm-dev-oci:oci-standards` - OCI container standards
- `pm-dev-oci:oci-security` - Container security best practices
