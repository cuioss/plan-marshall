# 02 — Auditor: preference learning via architecture hints

**Depends on [01](01-personas.md) for `persona-auditor` — this is its first
consumer. Reuses the retrospective auditor's corpus sweep + dormation.**

## Problem

User approvals are signal: the dispositions a user repeatedly makes at gates
express durable preferences that should bias future work without being configured
explicitly. plan-marshall captures user gate dispositions (`manage-findings`
resolutions: `fixed` / `suppressed` / `accepted` / `taken_into_account`) but never
feeds them back — they are historical records only. This workstream realizes
preference learning through the PR #744 architecture-hints machinery rather than a
new store.

## Approach

Detection lives in a **specialized cross-plan command**, modeled on (and likely
extending) `.claude/skills/audit-archived-plan-retrospectives` — the project-local
auditor that already sweeps the archived-plan corpus with a deterministic
`scripts/audit.py` (script computes, LLM orchestrates), runs a
`recurring-pattern-detector` check, and **dormates** reviewed plans to
`.plan/temp/dormated-plans/`. That dormation IS the "implicit archiving" the
learning sweep wants.

1. A **preference-pattern detector** (a new deterministic check in `audit.py`)
   computes recurring user-disposition patterns across the archived corpus — e.g.
   a finding class the user repeatedly `suppressed` / `accepted` in a module, or
   scope expansions repeatedly rejected — emitting candidate preferences as TOON.
2. The LLM half generalizes each surfaced pattern and routes it to
   `architecture enrich best-practice` (module-specific) or `--module default`
   (cross-cutting) — the same verbs KNOWLEDGE signals already use. No new store.
3. The same sweep **implicitly archives** (dormates) the plans it has processed,
   so learning and archiving are one pass — exactly the auditor's
   learn-then-dormate shape, retargeted from lessons to architecture hints.
4. The preference surfaces automatically: `get-module-context` →
   phase-3-outline `## Architecture Hints` (Step 10b-bis), biasing future outlines.

## Key design decisions

- **Reuse `enriched.json` `best_practices[]` / `insights[]`** — no new schema, no
  new reader. This is the whole point of routing through PR #744's machinery.
- **Generalize, do not log raw dispositions.** Store "module X: prefer Y over Z" as
  a best-practice, not "user clicked suppress on finding #123".
- **Threshold-gated** so one-off dispositions do not pollute hints — mirror the
  existing lessons-capture signal thresholds.
- **First `persona-auditor` consumer.** This workstream wires `persona-auditor`
  ([01](01-personas.md)) — the meta-persona that composes the tester / reviewer /
  security-expert lenses — over the retrospective command, making the audit a named,
  multi-persona evaluation. It is the first real exercise of the persona composition
  model, which is why it lands right after 01. Because 02 lands **before**
  [05](05-security-finalize-step.md), the `persona-security-expert` lens is still a
  *shell* at this point (its security content + `security` profile arrive with 05);
  the auditor functions via its other lenses (tester, reviewer) until then.

## Affected surface

- `.claude/skills/audit-archived-plan-retrospectives/` — new
  `checks/preference-pattern-detector.md` + the corresponding compute in
  `scripts/audit.py`; an LLM-orchestration step that routes generalized preferences
  to `architecture enrich`. (Or a sibling command if the auditor is the wrong home —
  see open decision.)
- `manage-findings` — read dispositions across the corpus; possibly a small
  "disposition summary" query.
- `manage-architecture enrich best-practice` / `enrich insight` (reuse).

## Open decisions

- **New check vs sibling command.** Add the preference detector as a check inside
  `audit-archived-plan-retrospectives` (reuses its corpus sweep + hybrid model +
  dormation) vs a standalone sibling command. **Recommendation:** a check in the
  existing auditor — the corpus sweep and dormation are already there; duplicating
  them in a sibling is the worse option.
- **Portability.** The auditor is **project-local** (operates on
  `.plan/local/archived-plans/`, which only exists in this meta-project). If
  preference learning should also work in consumer projects, a lightweight
  per-plan emitter at finalize (consumer-available) can feed the same
  `architecture enrich` verbs; the cross-plan command stays the richer, meta-only
  path. Resolve at the outline gate.

## Documentation to update (deliverables of this plan)

- `doc/concepts/audit-trail.adoc` — how user dispositions become durable hints.
- `doc/concepts/planning-workflow.adoc` — the `## Architecture Hints` section now
  also reflecting learned preferences in the outline.
- `doc/user/configuration.adoc` — any threshold knob governing when a disposition
  pattern is promoted to a best-practice.

## On completion

Delete this document and remove the `02` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Small–medium — a new check + compute in the existing auditor, routing to the
existing `architecture enrich` verbs. Depends on [01](01-personas.md)
(`persona-auditor`); otherwise independent.
