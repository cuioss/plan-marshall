---
name: pm-dev-python-python-security
description: "Use when reviewing or hardening Python security — injection sinks (subprocess, eval/exec, unsafe deserialization, SQL), path-traversal prevention, and untrusted-input handling at stdlib boundaries. The focused Python security surface resolved via skills_by_profile.security; a thin pointer that delegates cross-cutting foundations upward to plan-marshall:persona-security-expert."
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Python Security

**REFERENCE MODE**: This skill provides reference material for Python security review and hardening. Load specific standards on-demand based on current task. Do not load all standards at once.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for Python security review and hardening tasks.

**Prohibited actions:**
- Do not pass untrusted input to `subprocess` with `shell=True`; use an argv list
- Do not `pickle.load`/`pickle.loads` untrusted bytes, nor `yaml.load` without a safe loader
- Do not `eval`/`exec`/`compile` externally-sourced strings; use `ast.literal_eval` for literals
- Do not interpolate user values into SQL query strings; use DB-API placeholders with a params tuple

**Constraints:**
- Every externally-sourced value (request data, file contents, environment, CLI args) is untrusted at stdlib boundaries
- User-supplied paths must be validated against a safe base to prevent traversal
- Reject untrusted input that fails a boundary check; never coerce it through

## When to Use This Skill

Activate when:
- **Running subprocesses** — building argv, avoiding `shell=True`, quoting when a shell is unavoidable
- **Deserializing external data** — choosing `yaml.safe_load`/`json` over `pickle`/`yaml.load`
- **Dynamic evaluation** — choosing `ast.literal_eval` over `eval`/`exec`
- **Building SQL** — DB-API placeholders over string interpolation
- **Handling user-supplied paths** — traversal prevention with `Path.resolve()` / `is_relative_to`

## Available Standards

Load progressively based on current task. **Never load all standards at once.**

### Injection Sinks and Path Security

```text
Read: ../python-core/standards/python-core.md
```

Load the **Security** (path traversal) and **Injection and Unsafe Deserialization** (subprocess / pickle / yaml / eval / SQL) sections. These cover the secure-by-default sink choices at each stdlib boundary:

| Sink | Insecure | Secure |
|------|----------|--------|
| Subprocess | `shell=True` with interpolation | argv list (no shell), or `shlex.quote` when shell is unavoidable |
| Deserialization | `pickle.loads`, `yaml.load` | `yaml.safe_load`, `json.loads` |
| Dynamic execution | `eval`/`exec`/`compile` | `ast.literal_eval` |
| SQL | f-string interpolation | DB-API placeholder + params tuple |
| Path handling | unchecked user path | `Path.resolve().is_relative_to(safe_base)` |

## Surface Boundaries

| Surface | Home |
|---------|------|
| Injection sinks + path-traversal prevention | `../python-core/standards/python-core.md` (Security / Injection sections) |
| Cross-cutting OWASP / STRIDE / trust-boundary / secure-design foundations | `Skill: plan-marshall:persona-security-expert` |

## Cross-Cutting Foundations (delegated upward)

This skill is a **thin pointer**: the Python sink mechanics above are genuinely language-specific (how to apply the secure choice at each stdlib boundary), but the conceptual *why* lives in the centralized `plan-marshall:persona-security-expert` sub-documents. Load the matching foundation, then return here for the Python mechanics — there is no content duplication:

| Python mechanic (here) | Centralized foundation (there) |
|------------------------|-------------------------------|
| Why every stdlib boundary value is untrusted; allow-list, canonicalize-before-validate, fail-closed (the general architecture behind every sink and path check) | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| The subprocess / SQL / eval sinks mapped to a recognized risk category (A03 Injection) | [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |
| Why deserializing untrusted bytes is dangerous before any value inspection (the `pickle`/`yaml.load` avoidance is the Python mechanic) | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) — Unsafe Deserialization sub-section |
| The principles behind secure-by-default sink choices (secure by default, fail securely, economy of mechanism) | [`secure-design-principles.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |

Note the deserialization sinks (`pickle`/`yaml.load`) also map to OWASP A08 Software and Data Integrity Failures — see [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md).

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity and authoritative home for OWASP Top 10, STRIDE, secrets, secure logging, trust boundaries, authn/authz, and secure-design principles
- `pm-dev-python:python-core` — Core Python development standards (the security/injection sections referenced above live under its `standards/` directory)
- `pm-dev-python:pytest-testing` — Property-based / adversarial testing of security-relevant code
