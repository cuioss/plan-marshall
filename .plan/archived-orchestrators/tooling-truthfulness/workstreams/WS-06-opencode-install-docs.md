# WS-06: OpenCode install documentation

## Charter

Document, in the repository root `README.md` and the user documentation, how a user installs and
updates Plan Marshall on the OpenCode assistant. The subject is the OpenCode **consumption path** —
how an OpenCode user pulls the marketplace in — as opposed to the developer inner loop
(`/sync-opencode`), which the `multiplattform` epic's PLAN-04 owns.

⛔ **This workstream is a deliberate, operator-directed duplicate of `multiplattform` PLAN-18
(opencode-user-documentation) and PLAN-17 (pin-opencode-install-path).** Those plans are PARKED in
`multiplattform` WS-05 because the OpenCode consumption path against the published refs
(`dist-opencode` / `opencode/v*`) has never been validated on a live install
(`doc/developer/distribution.adoc` § Multi-target architecture). The operator chose to stage the
task in this epic anyway rather than unpark `multiplattform`. The duplication is recorded and
accepted; the two epics' specs must cross-reference each other and whichever lands second must
re-read the other first.

## Why it sits here rather than in `multiplattform`

Operator direction on 2026-09-11: "We use plan-marshall commands now" surfaced a general desire to
get OpenCode install documentation written promptly. The `multiplattform` park is gated on running
the live-validation protocol, which has not happened. Staging here does NOT lift that gate: it
creates a sibling plan whose deliverables must state honestly which parts of the install path are
verified vs. documented-as-designed.

## Boundary

- In scope: repo-root `README.md` OpenCode install section; `doc/user/installation.adoc` OpenCode
  section; cross-references from `doc/developer/distribution.adoc` and the user guide index; and
  **PLAN-07's D0 — pinning the OpenCode consumption path against a live install** (which candidate
  route works against `dist-opencode` / `opencode/v*`), including a consumer-facing install script
  when the pinned path needs one.
- Out of scope: the `/sync-opencode` developer inner loop (multiplattform PLAN-04), the
  live-validation protocol itself (multiplattform PLAN-17), and any `marketplace/targets/opencode`
  generator change — a generator gap found by D0 is REPORTED and staged separately, never absorbed
  here. ⛔ `/sync-opencode` is additionally NOT a consumer path of any kind: it is a command that
  exists only in the plan-marshall repo, so the workstream's D0 treats its deploy *shape* (generated
  tree → config dir) as candidate (a) and the command itself as out of scope — operator direction
  2026-09-11.
- ⛔ Every statement about a working install path must be labelled OBSERVED (verified against a live
  OpenCode install or the deployed `~/.config/opencode/` state) or HYPOTHESIS (designed, not yet
  consumed end-to-end). No unlabelled claim ships — this workstream inherits the epic's
  verify-first contract and ADR-019 reflexively.