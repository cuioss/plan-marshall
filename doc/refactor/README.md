# Multi-Target Marketplace Refactor — Overview

## Objective

Redesign the plan-marshall marketplace for multi-target distribution (Claude Code native + OpenCode + future) without changing the source-of-truth format or duplicating content.

## Core Insight

Multi-target portability without changing the source-of-truth format:
- **Keep Claude Code format as source of truth** — body text is emitted verbatim except for a small bounded set of mechanical line-level transforms (see [02 — Build System](02-build-system) "Body Transforms")
- **Abstract platform-specific behavior into scripts** — a `platform-runtime` layer
- **Generate target outputs at build time** — frontmatter, manifest, and the bounded body transforms documented in `marketplace/targets/opencode/transforms.md`

## Cluster Structure

This refactor is organized into 6 clusters plus cross-cutting principles:

| Cluster | Focus | Output |
|---------|-------|--------|
| [Principles](principles.md) | Rules that govern all clusters | Shared contract |
| [01 — Design Platform API](01-design-platform-api/plan.md) | Goal-based platform-runtime abstraction | API contract + router spec |
| [02 — Build System](02-build-system/plan.md) | Target generator, drift detection, OpenCode emitter | `marketplace/targets/` framework |
| [03 — Refactor for Portability](03-refactor-for-portability/plan.md) | Clean code of platform leakage | Updated skills + marshal.json |
| [04 — Validate and Document](04-validate-and-document/plan.md) | Know when we're done + document it | Test plan + architecture doc |
| [05 — Distribution](05-distribution/plan.md) | CI/CD, artifact hosting, end-user installation | Release pipeline + install docs |
| [06 — Developer Workflow](06-developer-workflow/plan.md) | Local deployment: edit → test → iterate | Dev inner loop for Claude + OpenCode |

## Dependency Graph

```
Principles (governs all)
    │
    ▼
01-design-platform-api ──────┐
    │                        │
    ▼                        │
02-build-system ──────────┐ │
    │                       │ │
    ▼                       │ │
03-refactor-for-portability ◄┘ │
    │                         │
    ├──────────┬──────────────┤
    ▼          ▼              ▼
04-validate  05-distribution 06-developer-workflow
             (can start      (can start
              design in       design in
              parallel)       parallel)
```

**01 must complete before 03** because the structural refactoring (03) depends on knowing the platform-runtime API surface (01).

**02 can proceed in parallel with 01** because the target engine's OpenCode emitter is a separate concern from the runtime API. However, 03's migration of the adapter into the target engine requires 02 to exist.

**04 runs last** because validation criteria depend on all implementation being in place.

**05 depends on 02** for the generator, but can be designed in parallel with 02 since both concern build artifacts. CI integration requires 02 to be complete.

**06 can be designed in parallel with 02** because the developer workflow depends on the build system for OpenCode generation, but not on 01 or 03. The Claude Code portion of 06 already exists and is documented.

## What We Are NOT Doing

- No universal templating syntax (`{{ }}`) — there is no cross-platform body language
- No open-ended body text transformations — body transforms are limited to the bounded set in `marketplace/targets/opencode/transforms.md`; adding a new transform is a deliberate spec change
- No excluding `marshall-steward` from OpenCode — it stays, but with platform-agnostic instructions
- No changing the 10-bundle structure or component model
- No adding version numbers, changelogs, or dated update sections to any document

## Terminology

| Term | Meaning |
|------|---------|
| **target** | An AI assistant platform we generate output for (Claude, OpenCode) |
| **platform-runtime** | The abstraction layer that routes platform-specific operations |
| **source of truth** | The Claude Code format in `marketplace/bundles/` |
| **drift** | When committed `.claude-plugin/` output differs from what the generator would produce |
| **no-op** | When a target cannot implement an operation, it returns a graceful fallback |

See [05 — Distribution](05-distribution) for the full `marketplace.json` structure and Claude Code plugin discovery details.
