---
name: pm-plugin-development-plugin-security
description: "Use when reviewing or hardening the security of marketplace meta-project components — the Python script surface (subprocess, path traversal, environment trust, unvalidated config-key handling) and the markdown trust surface (new external-content ingestion that bypasses the untrusted-ingestion boundary, trust-boundary erosion, prompt-injection-susceptible prose). The plan-marshall-plugin-dev security surface resolved via skills_by_profile.security; owns the two marketplace-specific surfaces and delegates cross-cutting foundations upward to plan-marshall:persona-security-expert."
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Plugin Security

**REFERENCE MODE**: This skill provides reference material for reviewing and hardening the security of marketplace meta-project components. Load a specific standard on-demand based on the surface being reviewed. Do not load both standards at once.

This skill is the `plan-marshall-plugin-dev` domain's security surface. Unlike the per-language security skills (`pm-dev-python:python-security`, `pm-dev-java:java-security`), which are thin pointers over a single stdlib, this skill is a **deep, meta-project-focused** security home: the marketplace's own attack surface is not "a Python app" or "a Java app" but a two-headed substrate — the **Python script surface** that every `manage-*` / build / extension script presents, and the **markdown trust surface** that every skill, command, and ingestion doc presents to the model that loads it. Both are owned here. The cross-cutting *why* (OWASP categories, STRIDE, trust-boundary architecture, secrets, secure logging, secure-design principles) is NOT restated here — it is delegated upward to `plan-marshall:persona-security-expert`, the single authoritative home.

## Enforcement

**Execution mode**: Reference library; load a standard on-demand for the marketplace surface under review. No execution logic in this SKILL.md.

**Prohibited actions:**
- Never read an environment variable (`os.environ.get(...)`) and construct a filesystem `Path`, a subprocess argv element, or a network target from it without validating it against a safe base or allow-list first. Environment is an untrusted boundary in a tool a consumer project drives.
- Never pass a value sourced from an extension's `get_skill_domains()` (a `domain` key, a profile name, a skill notation) into a downstream filesystem, subprocess, or import call without confirming it against the declared allow-list of known domains/profiles. Extension data is bundle-author-controlled, not core-controlled.
- Never add a new external-content ingestion surface (web page, GitHub issue/PR/comment body, Sonar message, or any other attacker-influenceable text) that consumes raw bytes in a write-capable or skill-loading context without routing the candidate struct through the deterministic `plan-marshall:untrusted-ingestion:validate_struct` gate.
- Never author skill/command/agent prose that interpolates untrusted external text into instructions the model will execute, nor that can be read as an instruction-injection vector.

**Constraints:**
- Strictly comply with all rules from `plan-marshall:persona-plan-marshall-agent`, especially tool usage and workflow step discipline.
- Every externally-sourced value (environment, CLI args, file contents read from a consumer project, extension-provided data, external web/issue/Sonar text) is untrusted at the boundary where the marketplace script or doc first consumes it.
- Reject untrusted input that fails a boundary check; never coerce it through. Fail closed.

## When to Use This Skill

Activate when:
- **Authoring or reviewing a marketplace script** — a `manage-*`, build, extension, or workflow-helper script that reads environment, CLI args, a consumer project's files, or extension-provided data, and routes any of it into a subprocess, a `Path`, an import, or a network call. Load `standards/python-script-surface.md`.
- **Adding or reviewing a content-ingestion surface** — any new place where the marketplace reads attacker-influenceable external text (web, GitHub, Sonar, or a new provider) and the model later consumes the result. Load `standards/markdown-trust-surface.md`.
- **Reviewing skill/command/agent prose for instruction-injection risk** — checking that a doc's prose cannot be coerced into executing attacker-supplied instructions, and that trust boundaries between read-only and write-capable contexts are not eroded. Load `standards/markdown-trust-surface.md`.

## The Two Marketplace Security Surfaces

```text
  marketplace meta-project security substrate
  ────────────────────────────────────────────
  Python script surface              markdown trust surface
  (standards/python-script-surface)  (standards/markdown-trust-surface)
    subprocess argv vs shell           untrusted-ingestion boundary
    path traversal at fs boundary      reader/orchestrator/writer isolation
    PLUGIN_CACHE_PATH env-trust        trust-boundary erosion
    unvalidated get_skill_domains()    prompt-injection-susceptible prose
              │                                    │
              └──────────────┬─────────────────────┘
                             ▼
       cross-cutting foundations (delegated upward)
       plan-marshall:persona-security-expert
       OWASP · STRIDE · trust boundaries · secrets · secure logging · secure design
```

## Available Standards

Load progressively based on the surface under review. **Never load both standards at once.**

| Standard | File | Load When |
|----------|------|-----------|
| Python script surface | `standards/python-script-surface.md` | Reviewing a marketplace script's injection sinks — subprocess invocation, path traversal, environment trust (`PLUGIN_CACHE_PATH`), and unvalidated extension config-key handling (`get_skill_domains()`) |
| Markdown trust surface | `standards/markdown-trust-surface.md` | Reviewing a content-ingestion surface that may bypass the `plan-marshall:untrusted-ingestion` boundary, trust-boundary erosion between read-only and write-capable contexts, or prompt-injection-susceptible prose |

## Cross-Cutting Foundations (delegated upward)

The two standards above own the **marketplace-specific mechanics**. The conceptual foundation behind each mechanic lives in the centralized `plan-marshall:persona-security-expert` sub-documents — load the matching foundation, then return here for the marketplace mechanics. There is no content duplication:

| Marketplace mechanic (here) | Centralized foundation (there) |
|-----------------------------|--------------------------------|
| Why every environment/CLI/extension/external value is untrusted at the boundary; allow-list, canonicalize-before-validate, fail-closed | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| The subprocess / path-traversal sinks mapped to a recognized risk category (A03 Injection) | [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |
| Drawing the reader/orchestrator/writer data-flow and placing the ingestion trust boundary (the STRIDE decomposition behind the untrusted-ingestion contract) | [`threat-modeling-stride.md`](../../../plan-marshall/skills/persona-security-expert/standards/threat-modeling-stride.md) |
| The principles behind fail-closed validation and least-privilege reader contexts (secure by default, fail securely, complete mediation, economy of mechanism) | [`secure-design-principles.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity and authoritative home for OWASP Top 10, STRIDE, secrets, secure logging, trust boundaries, authn/authz, and secure-design principles
- `plan-marshall:untrusted-ingestion` — The shared contract every untrusted-external-content ingestion surface loads (reader/orchestrator/writer isolation + the deterministic `validate_struct` boundary); the markdown trust surface frames new ingestion against it
- `pm-dev-python:python-security` — The general Python stdlib injection-sink surface; the marketplace Python script surface applies the same sink discipline to the meta-project's own scripts
- `pm-plugin-development:plugin-script-architecture` — Script implementation standards (stdlib-only, executor integration, TOON output) the Python script surface review complements
