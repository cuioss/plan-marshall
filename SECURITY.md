# Security Policy

## Reporting a Vulnerability

Please do **not** report security vulnerabilities through public GitHub issues.

Instead, use one of these private channels:

1. **GitHub private vulnerability reporting** (preferred): use the
   ["Report a vulnerability"](https://github.com/cuioss/plan-marshall/security/advisories/new)
   form on this repository's Security tab. The report is visible only to the
   maintainers until a fix is coordinated.
2. **Email**: contact the maintainers at `contact@cuioss.de` with a description
   of the issue, reproduction steps, and the affected component
   (bundle / skill / script path if known).

You should receive an acknowledgement within a few business days. Please allow
the maintainers a reasonable coordination window before any public disclosure.

## Scope

Plan Marshall ships development standards, workflow skills, and Python
automation scripts that run inside Claude Code sessions on developer machines.
Reports are especially valuable for:

- **Script execution paths** — anything that lets a crafted repository,
  configuration file, or script argument escape the documented execution
  contract of `.plan/execute-script.py` or the `manage-*` script family.
- **Credential handling** — leaks of provider credentials handled by the
  `workflow-integration-*` provider scripts (the design goal is that
  credentials never enter the LLM context; see
  `doc/concepts/tools-and-scripts.adoc`).
- **Untrusted-content containment** — bypasses of the `untrusted-ingestion`
  validation clamp or the read-only reader agent's containment described in
  `doc/adr/003-Reader_isolation_as_a_tool-surface_lever.adoc`.
- **Supply chain** — integrity of the generated `target/*` distributions and
  the `dist-*` release branches.

Findings in third-party dependencies are best reported upstream first; a note
here is still welcome when Plan Marshall's usage amplifies the impact.

## Security Model Documentation

The threat model and security architecture are documented in
[`doc/concepts/security.adoc`](doc/concepts/security.adoc).
