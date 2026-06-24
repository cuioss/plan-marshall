---
name: javascript-security
description: "Use when reviewing or hardening JavaScript security — DOM trust boundaries, XSS sinks (innerHTML/outerHTML/insertAdjacentHTML), safe text rendering, sanitization (DOMPurify), and Trusted Types. The focused JavaScript security surface resolved via skills_by_profile.security."
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

```
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
| Cross-cutting OWASP / STRIDE / secure-coding principles | `Skill: plan-marshall:persona-security-expert` |

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity (OWASP Top Ten, STRIDE, secure-coding principles)
- `pm-dev-frontend:javascript` — Core JavaScript development standards (the DOM-trust/XSS content referenced above lives under its `standards/` directory)
- `pm-dev-frontend:jest-testing` — Testing security-relevant DOM rendering
