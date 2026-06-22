# 04 — Preference learning via architecture hints/best-practices

**Independent. Highest reuse of existing machinery, smallest scope.**

## Problem

External workflows bias future generations from user *approvals* ("emerges, not
configured"). plan-marshall captures user gate dispositions (`manage-findings`
resolutions: `fixed` / `suppressed` / `accepted` / `taken_into_account`) but never
feeds them back — they are historical records only. This workstream realizes
preference learning through the PR #744 architecture-hints machinery rather than a
new store.

## Approach

Close the loop using the existing enrichment surface:

1. At finalize, extend the ACTIONABLE/KNOWLEDGE partition already in
   `phase-6-finalize/workflow/lessons-capture.md` (Branch B3) to also detect
   recurring user-disposition patterns — e.g. a finding class the user repeatedly
   `suppressed` / `accepted` in a module, or scope expansions repeatedly rejected.
2. Route the *generalized preference* to `architecture enrich best-practice`
   (module-specific) or `--module default` (cross-cutting) — the same verbs
   KNOWLEDGE signals already use. No new store.
3. The preference surfaces automatically: `get-module-context` →
   phase-3-outline `## Architecture Hints` (Step 10b-bis), biasing future outlines.

## Key design decisions

- **Reuse `enriched.json` `best_practices[]` / `insights[]`** — no new schema, no
  new reader. This is the whole point of routing through PR #744's machinery.
- **Generalize, do not log raw dispositions.** Store "module X: prefer Y over Z" as
  a best-practice, not "user clicked suppress on finding #123".
- **Threshold-gated** so one-off dispositions do not pollute hints — mirror the
  existing lessons-capture signal thresholds.

## Affected surface

- `phase-6-finalize/workflow/lessons-capture.md` — Branch B3 disposition-pattern
  detection.
- `manage-findings` — read dispositions; possibly a small "disposition summary"
  query.
- `manage-architecture enrich best-practice` / `enrich insight` (reuse).
- Docs: `phase-6-finalize/standards/lessons-integration.md`.

## Open decision

- **Detection locus:** per-plan at finalize (cheap, local) vs a periodic cross-plan
  sweep (richer patterns, more cost). **Recommendation:** per-plan finalize first,
  reusing the signal-threshold pattern already in lessons-capture.

## Documentation to update (deliverables of this plan)

- `doc/concepts/audit-trail.adoc` — how user dispositions become durable hints.
- `doc/concepts/planning-workflow.adoc` — the `## Architecture Hints` section now
  also reflecting learned preferences in the outline.
- `doc/user/configuration.adoc` — any threshold knob governing when a disposition
  pattern is promoted to a best-practice.

## On completion

Delete this document and remove the `04` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Small–medium. Highest reuse; independent of the other workstreams.
