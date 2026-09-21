# WS-04: How plan-marshall talks — language, vocabulary, volume

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-how-plan-marshall-talks.md` and is tracked in the
> epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the three cross-cutting rules governing every word plan-marshall shows a user: **which
language** it speaks (the user's, consistently — German included), **which vocabulary** it
uses (the user's, not the system's internal nouns), and **how much** it says (what the next
decision needs, and no more). All three land in ONE new dedicated standards file,
`persona-plan-marshall-agent/standards/user-communication.md`, loaded UNCONDITIONALLY beside
`agent-behavior-rules.md`. That placement is a settled operator decision: it buys isolation
(one document to point at and evolve) without buying opt-in (a separate skill binds only when
something remembers to load it, and "throughout" is exactly what a load-when-remembered rule
cannot deliver). The workstream closes when the three rules exist there as binding standards
with a stated scope, so WS-05's sweep and every future component have something to conform to.

## Scope

- In scope: the NEW `persona-plan-marshall-agent/standards/user-communication.md` as the
  single home for all three rules, plus its unconditional load step in that skill's `SKILL.md`
  and a pointer to it from `agent-behavior-rules.md` (pointer only — no rule text is
  duplicated there); a user-language
  setting in `marshal.json` and its `manage-config` surface; the user-vocabulary rule and the
  glossary of internal terms it displaces (ledger, workstream, epic, q-gate, disjointness,
  multiSelect, lane, deliverable, footprint); the output-volume rule for main-context
  user-facing reporting, which today is bounded only on the subagent-return path
  (`citations-only-return.md`).
- Out of scope: applying any of the three at existing sites (WS-05); the prompt-structure
  standard (WS-03), which cites these rules; translating the marketplace's own developer-facing
  documentation, which is not user-facing output and stays in English.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-06-user-language-and-vocabulary | shipped — PR #1382 | User-language honouring + the user-vocabulary rule and its internal-term glossary |
| PLAN-07-output-volume-standard | shipped — PR #1387 | Bound main-context user-facing output volume, the surface `citations-only-return.md` does not reach |

Statuses above reconciled from `status.json` on 2026-09-05; the table had carried `staged` for
both after they landed.

## Sequencing and Surface Notes

- PLAN-06 and PLAN-07 both touch `standards/user-communication.md` — **overlapping, and the
  sequence is now structural rather than stylistic**: PLAN-06 CREATES the file PLAN-07 appends
  to. PLAN-07 halts if PLAN-06 has not landed, rather than creating a second home for the same
  concern.
- The placement decision NARROWED PLAN-07's surface: it no longer touches
  `agent-behavior-rules.md` or the persona `SKILL.md` at all, because the load step and the
  pointer are PLAN-06's deliverables.
- **This workstream is surface-disjoint from WS-01 and WS-02** (persona/standards vs
  `manage-config` scripts), which is what makes `parallelization_scope: 2` useful at all in
  this epic. It is the intended partner for the second slot.
- The user-language rule has **no existing surface to extend** — verified absent
  marketplace-wide at epic init. Expect PLAN-06 to define the concept, not adapt one.
- Distinguish two things the volume rule must not conflate: *verbosity of narration* (cut) and
  *completeness of a reported outcome* (keep). A rule that trims the second produces silent
  failures, which is a worse defect than the one being fixed.

