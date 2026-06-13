# 05 — OpenCode user + developer documentation

## Objective

Document OpenCode support for end users and contributors, **after** the runtime is
validated. Write present-tense AsciiDoc that extends the existing `doc/` structure — do
not resurrect the retired plan's flat-`doc/*.md` porting table.

## Current state

The build and distribution architecture is already documented canonically:

- `doc/developer/marketplace-build.adoc` — generator pipeline, variant emission, the
  `--target opencode` adapter invocation, plugin-cache sync.
- `doc/developer/distribution.adoc` — dist-branch + dist-tag model, the multi-target
  matrix, unified versioning.
- `doc/concepts/execution-context.adoc` — the dispatcher architecture.

These describe Claude as the validated target and OpenCode as "best-effort / not yet
validated." This workstream upgrades that once [02](02-validate-opencode-runtime.md) lands.

## Tasks

Write only what the validated reality supports. Do not document an install path or a
behaviour that [02](02-validate-opencode-runtime.md) or
[03](03-distribution-opencode-target.md) has not confirmed.

1. **User: OpenCode installation** — add the verified OpenCode install/update path to
   `doc/user/installation.adoc` (which install mechanism actually works is decided in
   [03](03-distribution-opencode-target.md), not assumed here).

2. **Developer: OpenCode inner loop** — add a section (or sibling doc under
   `doc/developer/`) covering generate → `sync-opencode` → test, the three deploy options,
   and the singular→plural rename. Cross-reference `marketplace-build.adoc`.

3. **Reference: platform-runtime + no-op surface** — document the 15-operation
   `platform-runtime` API and, per operation, the OpenCode behaviour (real vs `no-op`
   with its `reason`/`alternative`). The authoritative contract is the runtime's own
   `standards/` docs; the `doc/` entry orients and cross-references rather than
   duplicating.

4. **Limitations** — record the confirmed OpenCode limitations from
   [02](02-validate-opencode-runtime.md): no platform-driven terminal-title/status-line
   hook, no automatic token capture (manual `--total-tokens`), weaker instruction
   following (Opus recommended), and any `inline_only` step kinds discovered during
   validation.

5. **Update the "Multi-Assistant Support" framing** in the repo-root `README.md` /
   `CLAUDE.md` so it reflects validated OpenCode support instead of "generated but not
   validated."

## Acceptance

- OpenCode install, inner loop, API/no-op surface, and limitations are documented in the
  existing `doc/` structure, present-tense, cross-referenced (no duplication).
- Every documented behaviour traces to something confirmed in
  [02](02-validate-opencode-runtime.md) / [03](03-distribution-opencode-target.md).
- The repo-root "Multi-Assistant Support" framing matches reality.

## Dependencies

- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) and
  [03 — Distribution](03-distribution-opencode-target.md) — documentation follows
  validated behaviour.
