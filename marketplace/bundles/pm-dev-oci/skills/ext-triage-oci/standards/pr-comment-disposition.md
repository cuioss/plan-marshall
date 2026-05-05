# OCI Container PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, Hadolint-bot, Trivy-bot, Docker Scout, Sonar, etc.) on Dockerfiles, Containerfiles, and container build configuration. Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Image change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of OCI container standards (see `pm-dev-oci:oci-standards`, `pm-dev-oci:oci-security`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Base image not pinned | `FROM alpine:latest`, `FROM ubuntu` (no tag), missing digest on production image | `oci-standards` (Version Pinning) |
| Package manager pin missing | `apt install foo` without `=version`, `apk add` without `--no-cache` | `oci-standards` |
| Layer cache misuse | `COPY . .` before dependency install, `RUN apt update` separated from `apt install` | `oci-standards` |
| Multi-stage missing | Build deps shipped in runtime image (compilers, JDKs, npm cache) | `oci-standards` (Multi-Stage Builds) |
| Root user in runtime | No `USER` directive, runtime stage runs as root | `oci-security` (Capabilities) |
| Privilege escalation | `--privileged`, `cap_add: ALL`, `securityContext.privileged: true` | `oci-security` |
| Capabilities not dropped | Missing `--cap-drop=ALL` baseline, broad `cap_add` list | `oci-security` (Capability Dropping) |
| Filesystem not read-only | Runtime container without `read-only: true` and explicit tmpfs mounts | `oci-security` (Read-Only Filesystem) |
| Missing OCI labels | No `org.opencontainers.image.source`, `image.revision`, `image.licenses` | `oci-standards` (OCI Labels) |
| Missing `.dockerignore` | Build context includes `.git`, `node_modules`, `target/` for non-build stage | `oci-standards` (.dockerignore) |
| HEALTHCHECK absent | Long-running service image without `HEALTHCHECK` (or k8s probe equivalent) | `oci-standards` (Quarkus distroless probes section) |
| Hadolint `error` (DL3xxx) | DL3008 unpinned apt, DL3009 missing `--no-install-recommends`, DL3015 `--no-install-recommends` missing | `oci-standards` |
| CVE — CRITICAL/HIGH with patch available | Trivy reports CVE-YYYY-NNNN with `Fixed Version` field populated | `oci-security`, `severity.md` |
| Secret in image | Hardcoded password/token in `ENV`, `ARG` leaked via `--build-arg`, `.env` copied into image | `oci-security` (Secret Management) |
| Image not signed | Missing Cosign signature in supply-chain pipeline | `oci-security` (Image Signing) |
| SBOM missing | Production image without Syft-generated SBOM in CI | `oci-security` (SBOM) |
| Multi-platform omission | Image declared for `linux/amd64,linux/arm64` only builds `amd64` | `oci-standards` (Multi-Platform Builds) |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Trivy flags CVE with no fixed version available | `False positive (no fix): CVE `{id}` has no patched version upstream; tracked in `.trivyignore` with rationale per suppression.md.` |
| Hadolint flags `apt-get update` without install — but it's a builder stage that intentionally caches the index | `False positive: builder stage caches index for downstream RUN layer; flagged DL3009 does not apply when followed by `apt install` in next layer.` |
| Bot flags root user in distroless image (which has no shell to switch to) | `False positive: distroless base provides only nonroot UID 65532; the suggested `USER nonroot` is implicit (see oci-standards Quarkus distroless section).` |
| Bot flags missing HEALTHCHECK on a job-style container (CronJob, init container) | `False positive: container is short-lived ({type}); HEALTHCHECK is not applicable per oci-standards (long-running service criterion).` |
| Trivy flags base image CVE on a build-stage image not shipped to runtime | `False positive: CVE is in builder-stage image; runtime image is `{runtime_base}` and is not vulnerable. Multi-stage discards the builder layer.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion reintroduces a deprecated base image the plan is removing | `Suggestion contradicts plan intent: this PR migrates base image from `{old}` to `{new}` per `{plan_id}/{lesson_id}`. Reverting restores the deprecated base.` |
| Suggestion adds backward-compat shim on a `breaking` plan | `Plan compatibility strategy is `breaking` (see phase-2-refine compatibility field). Backward-compat shim is intentionally out of scope.` |
| Bot suggests reintroducing `latest` tag for "ease of upgrade" on a plan enforcing digest pinning | `Plan enforces digest pinning per oci-standards. `latest` tag reintroduces non-reproducible builds — the explicit anti-pattern this PR removes.` |
| Bot suggests dropping multi-stage to "simplify" Dockerfile on a plan reducing image size | `Plan migrates to multi-stage to remove build deps from runtime image. Single-stage would reintroduce the bloat the plan eliminates.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes refactor of a Dockerfile untouched by this PR | `Out of scope: `{path}` is not modified in this PR. Refactor request belongs in a dedicated container hardening plan.` |
| Bot proposes adopting a new base image family (Alpine → Wolfi, Ubuntu → distroless) | `Out of scope: base image family change requires an ADR and migration plan; not in this PR's stated scope.` |
| Bot proposes adopting BuildKit / Buildah / Kaniko for the project | `Out of scope: build tool change requires CI infrastructure work; not in this PR's stated scope.` |
| Bot flags runtime orchestration concerns (k8s manifests, helm charts) on a Dockerfile thread | `Out of scope for this thread (Dockerfile review). Orchestration findings belong on the manifest PR.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags a `.dockerignore` rule with a Dockerfile rule code | `Out of domain: `.dockerignore` syntax differs from Dockerfile; rule `{id}` does not apply.` |
| Bot suggests language-runtime tuning (JVM heap, Node `--max-old-space-size`) inside a Dockerfile review thread | `Out of domain for this thread (image build review). Runtime tuning is configured at deploy time (k8s, compose), not in the image.` |
| Bot suggests Dockerfile syntax for Containerfile / Buildah-specific feature | `Out of domain: file is OCI Containerfile; the suggested Docker BuildKit-only syntax is not portable across builders.` |
| Bot complains about `CMD` vs `ENTRYPOINT` style on a base image where convention is fixed | `Out of domain: base image `{base}` documents `{convention}` as the required pattern (see upstream image guidance).` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes the base image major version (Alpine 3.18 → 3.20, Ubuntu 22.04 → 24.04) without a tested migration | Base image major bumps require maintainer-driven validation across CI matrix |
| Suggestion conflicts between two automated scanners (Trivy says fix to version A, Grype says version B) | Cannot satisfy both; user must pick the authoritative scanner |
| Trivy reports a CRITICAL CVE with no fixed version and the bot suggests image switch | Image switch is a base-image decision, not a CVE patch; needs maintainer call |
| Suggestion proposes capability changes (`SYS_ADMIN`, `NET_ADMIN`) for "convenience" | Security capability grants require explicit go/no-go; default is drop-all |
| Suggestion proposes mounting host filesystems (`/var/run/docker.sock`, `/proc`) | Host mounts have severe security implications; never accept inline |
| Suggestion contradicts a project-specific lesson (Quarkus distroless probes, Maven Jib usage) but the lesson is not referenced in the plan | Verify the lesson still applies before accepting or rejecting |
| Bot proposes signing/SBOM tooling change (Cosign → Notation, Syft → Grype) | Supply-chain tool swap affects CI and verification workflow; needs maintainer sign-off |
| Bot proposes loosening read-only filesystem to "fix" a write attempt | Writable runtime filesystem is a security regression; trace the write target instead |

## Disposition Flow

```
Bot comment received
  ↓
Plan-intent check (dev-general-practices PR review rule)
  Contradicts plan? → REPLY-AND-RESOLVE (Plan-Intent Contradiction)
  ↓
Match FIX category from table above?
  Yes → FIX (apply change, reply with commit link)
  ↓
Match REPLY-AND-RESOLVE category?
  Yes → reply with template, mark resolved
  ↓
Match Escalation Trigger?
  Yes → AskUserQuestion, record decision in lessons
  ↓
Default → ESCALATE (do not silently fix or resolve unknown categories)
```

## Reply Quality Rules

| Rule | Rationale |
|------|-----------|
| Always cite the Hadolint rule code (DL3xxx), CVE id, or OWASP Docker Top 10 reference that justifies the disposition | Reviewers and security audits can verify rationale without context-switching |
| Never accept "won't fix" on a CRITICAL CVE without explicit user confirmation and `.trivyignore` justification | Security exceptions require traceable approval |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — CVE severity-to-action mapping
- [suppression.md](suppression.md) — Hadolint inline ignore, `.trivyignore`, scout-policy syntax
- `pm-dev-oci:oci-standards` — Container build standards
- `pm-dev-oci:oci-security` — Runtime security and supply chain
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
