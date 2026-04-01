# OCI Container Severity Guidelines

Decision criteria for handling OCI container findings based on severity, type, and context.

## Severity-to-Action Mapping

### Vulnerability Findings (Trivy, Grype, Snyk)

| Severity | Default Action | Override Conditions |
|----------|----------------|---------------------|
| **CRITICAL** | Fix (mandatory) | Suppress only if no fix exists AND mitigated by other controls |
| **HIGH** | Fix (mandatory) | Suppress only if no fix AND low exploitability |
| **MEDIUM** | Fix preferred | Suppress with justification in non-exposed services |
| **LOW** | Consider | Accept in internal-only images |
| **UNKNOWN** | Investigate | Classify manually, then apply appropriate action |

### Hadolint Findings

| Severity | Default Action | Override Conditions |
|----------|----------------|---------------------|
| **error** | Fix (mandatory) | None — indicates Dockerfile anti-pattern |
| **warning** | Fix preferred | Suppress with justification for legacy Dockerfiles |
| **info** | Consider | Accept or fix opportunistically |
| **style** | Accept | Fix if low effort |

## Decision by Finding Type

### Base Image Vulnerabilities

| Situation | Action |
|-----------|--------|
| Fix available in newer tag | Update base image tag |
| Fix available in different base | Evaluate migration effort |
| No fix available (0-day) | Suppress with tracking, set review date |
| Vulnerability in unused component | Document as false positive, suppress |

### Dockerfile Best Practices

| Finding | Action |
|---------|--------|
| Unpinned versions (DL3008/DL3018) | Fix if specific version available; suppress if floating with weekly rebuilds |
| Missing USER instruction | Fix (always — running as root is a security risk) |
| ADD instead of COPY | Fix (use COPY unless tar extraction is needed) |
| Missing HEALTHCHECK | Fix or accept if orchestrator handles health probes |
| Shell form CMD/ENTRYPOINT | Fix (use exec/JSON form) |

### Runtime Security Findings

| Finding | Action |
|---------|--------|
| Running as root | **Fix** (no exceptions in production) |
| Capabilities not dropped | **Fix** (`--cap-drop=ALL` with selective adds) |
| Writable filesystem | Fix (`--read-only` with tmpfs) or accept for dev images |
| No resource limits | Fix for production; accept for local dev |
| Docker socket mounted | **Fix** (no exceptions) |

## Context Modifiers

### Production vs Development Images

| Context | Guidance |
|---------|----------|
| **Production image** | Full severity rules apply, no CRITICAL/HIGH accepted |
| **Development/CI image** | More lenient on resource limits and health probes |
| **Test-only image** | Accept most non-security findings |
| **Base image (shared)** | Strictest rules — vulnerabilities propagate to all children |

### New vs Legacy Dockerfiles

| Context | Guidance |
|---------|----------|
| **New Dockerfile** | Fix all findings MEDIUM and above |
| **Legacy Dockerfile** | Suppress with migration plan for warnings |
| **Generated Dockerfile** | Fix template/generator, regenerate |

### Image Rebuild Frequency

| Frequency | Guidance for Unfixed CVEs |
|-----------|---------------------------|
| **Weekly rebuilds** | Accept MEDIUM with tracking (patches arrive via base image updates) |
| **Monthly or less** | Fix or suppress with explicit review date |
| **No scheduled rebuilds** | Fix all — no passive patching pathway |

## Acceptable to Accept

### Always Acceptable

| Finding Type | Reason |
|--------------|--------|
| CVE with no fix in any base image | Cannot be resolved, document and track |
| Hadolint style in generated Dockerfiles | Fix the generator instead |
| Scanner false positives (vendored/patched) | Tool limitation |
| Test-only images not deployed | No production risk |

### Conditionally Acceptable

| Finding Type | Condition |
|--------------|-----------|
| MEDIUM CVE | Mitigated by network isolation or WAF |
| Unpinned apt/apk versions | Weekly rebuild schedule with scan gate |
| Missing health probe | Orchestrator (Kubernetes) handles probes externally |

### Never Acceptable

| Finding Type | Reason |
|--------------|--------|
| CRITICAL CVE with available fix | Unacceptable security risk |
| Running as root in production | Container breakout grants host root |
| Docker socket mounted | Root-equivalent host access |
| Secrets in image layers | Extractable by anyone with image access |

## Iteration Limits

During finalize phase:

| Iteration | Focus |
|-----------|-------|
| 1 | Fix all CRITICAL CVEs and Hadolint errors |
| 2 | Fix HIGH CVEs and remaining Hadolint warnings |
| 3 | Review MEDIUM/LOW, suppress or accept with justification |
| MAX (5) | Accept remaining, document for future |

## Quick Decision Flowchart

```
Is it a CRITICAL CVE with a fix?
  -> Yes -> FIX (update base image or dependency)

Is it running as root or mounting docker.sock?
  -> Yes -> FIX (no exceptions)

Is it a Hadolint error?
  -> Yes -> FIX (Dockerfile anti-pattern)

Is it a HIGH CVE with a fix?
  -> Yes -> FIX

Is there no fix available?
  -> Yes -> SUPPRESS with tracking and review date

Is it in a test-only image?
  -> Yes -> ACCEPT

Is it low-effort to fix?
  -> Yes -> FIX

Else -> ACCEPT and document
```

## Related Standards

- [suppression.md](suppression.md) - How to suppress findings
- `pm-dev-oci:oci-standards` - OCI container standards
- `pm-dev-oci:oci-security` - Container security best practices
