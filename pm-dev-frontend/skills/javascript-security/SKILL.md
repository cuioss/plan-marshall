---
name: javascript-security
description: "Use when reviewing or hardening JavaScript security — DOM trust boundaries, XSS sinks (innerHTML/outerHTML/insertAdjacentHTML), safe text rendering, sanitization (DOMPurify), and Trusted Types. The focused JavaScript security surface resolved via skills_by_profile.security; a thin pointer that delegates cross-cutting foundations upward to plan-marshall:persona-security-expert."
user-invocable: false
mode: knowledge
---

# JavaScript Security

**REFERENCE MODE**: This skill provides reference material for JavaScript security review and hardening. Load specific standards on-demand based on current task. Do not load all standards at once.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for JavaScript security review and hardening tasks.

**Prohibited actions:**
- Do not assign untrusted data to `innerHTML`, `outerHTML`, or `insertAdjacentHTML` — these parse and execute injected markup
- Do not hand-roll HTML sanitization with regex; use a vetted allow-list sanitizer
- Do not render untrusted data into the DOM without choosing a text-treating sink or sanitizing first

**Constraints:**
- Untrusted data rendered into the DOM is an XSS trust boundary; the safe default is a text-treating sink (`textContent`, `createElement` + `textContent`)
- When rendering untrusted HTML is a genuine requirement, sanitize with a vetted library (DOMPurify) and prefer Trusted Types where the platform supports it
- DOMPurify is a third-party dependency — adding it is a user-approval step

## When to Use This Skill

Activate when:
- **Rendering untrusted data into the DOM** — choosing `textContent` over `innerHTML`
- **Reviewing XSS sinks** — auditing `innerHTML`/`outerHTML`/`insertAdjacentHTML` usage
- **Sanitizing HTML output** — DOMPurify allow-list sanitization when HTML rendering is unavoidable
- **Hardening with Trusted Types** — enforcing `require-trusted-types-for 'script'` via CSP

## Available Standards

Load progressively based on current task. **Never load all standards at once.**

### DOM Trust Boundaries / XSS

```text
Read: ../javascript/standards/modern-patterns.md
```

Load the **DOM Trust Boundaries / XSS** section. The hazard is API-specific — properties that parse their argument as HTML execute embedded markup, while properties that treat their argument as text do not:

| API | Treatment | Safety |
|-----|-----------|--------|
| `textContent` | text | safe |
| `createElement` + `textContent` | text | safe (use when building structure) |
| `innerHTML` / `outerHTML` | HTML-parsing | XSS sink |
| `insertAdjacentHTML` | HTML-parsing | XSS sink |
| `DOMPurify.sanitize(html)` | allow-list sanitizer | safe when HTML output is unavoidable |

Trusted Types (`require-trusted-types-for 'script'` via Content-Security-Policy) turn the boundary into a runtime guarantee where the platform supports it.

## Surface Boundaries

| Surface | Home |
|---------|------|
| DOM trust boundaries, XSS sinks, sanitization, Trusted Types | `../javascript/standards/modern-patterns.md` (DOM Trust Boundaries / XSS section) |
| Cross-cutting OWASP / STRIDE / trust-boundary / secure-design foundations | `Skill: plan-marshall:persona-security-expert` |

## Cross-Cutting Foundations (delegated upward)

This skill is a **thin pointer**: the DOM-sink taxonomy above is genuinely runtime-specific (which browser APIs parse their argument as HTML), but the conceptual *why* lives in the centralized `plan-marshall:persona-security-expert` sub-documents. Load the matching foundation, then return here for the DOM mechanics — there is no content duplication:

| JS/DOM mechanic (here) | Centralized foundation (there) |
|------------------------|-------------------------------|
| The DOM as a trust boundary; the safe-default text sink; why allow-list sanitization beats deny-list filtering | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| The XSS sinks mapped to a recognized risk category (A03 Injection / XSS) | [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |
| Why the text-treating sink is the secure default and Trusted Types/CSP harden by default | [`secure-design-principles.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |
| The Content-Security-Policy directives and `require-trusted-types-for 'script'` header that back the DOM Trusted Types mechanic | [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) — Security Headers and Content Security Policy |

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity and authoritative home for OWASP Top 10, STRIDE, secrets, secure logging, trust boundaries, authn/authz, and secure-design principles
- `pm-dev-frontend:javascript` — Core JavaScript development standards (the DOM-trust/XSS content referenced above lives under its `standards/` directory)
- `pm-dev-frontend:jest-testing` — Testing security-relevant DOM rendering
