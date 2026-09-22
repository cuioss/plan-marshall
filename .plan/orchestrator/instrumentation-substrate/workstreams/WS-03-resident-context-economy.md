# WS-03: Resident-context economy

epic: instrumentation-substrate

> Charter document for one workstream. Lives at `workstreams/WS-03-resident-context-economy.md` and is
> tracked in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Roughly 99% of this project's billing weight is resident context rather than generation, and cost is
`resident_context × turns` at an average byte re-read of 44.6×. A component's frontmatter
`description` is resident on **every turn of every session** whether or not the component is ever
loaded, which makes it the most expensive byte in the corpus per unit of information it carries. This
workstream measures that surface, decides whether a shape rule for it is worth having, and — only if
the first measurement justifies it — recovers the same effect for the state that compaction destroys.

It closes when the price of the always-resident surface is a published number and a decision has been
recorded either way.

## Scope

- In scope: measuring the always-resident description surface; deciding and, if justified, enforcing a
  trigger-shaped description rule through `plugin-doctor`; the post-compaction re-injection of a
  *pointer* to live plan state through the existing `SessionStart` seam.
- Out of scope: ⛔ **injecting instruction bodies into the session.** Injection is resident context by
  definition, and a body would spend the very budget this workstream exists to recover. Also out of
  scope: rewriting any `description` for reasons other than shape, and any change to what a component
  *does*.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-description-surface-economy | staged | Derive the resident description cost, then decide whether a trigger-shaped rule earns its keep. "Close it unfixed" is a documented outcome. |
| PLAN-06-compaction-anchor-pointer | staged | Re-inject a pointer to live plan state at `SessionStart`/`compact`. Gated behind PLAN-05. |

## Sequencing and Surface Notes

- PLAN-06 is deliberately staged **behind** PLAN-05, and the gate is evidentiary rather than
  technical: PLAN-05 establishes whether this workstream's premise — that always-resident bytes are
  worth chasing — survives contact with a measurement. ⚠ PLAN-06's own saving has never been
  independently sized; if PLAN-05 closes unfixed, re-read PLAN-06's premise before launching it.
- PLAN-05 touches component frontmatter and `plugin-doctor`; PLAN-06 touches `platform-runtime`. The
  two surfaces are disjoint, so the sequencing here is an evidence dependency and not a collision.
- ⚠ A description rule has a fleet dimension: descriptions are how every runtime locates a skill, and
  the generator emits them byte-identical to all of them. A shape change tuned to one model's
  retrieval behaviour is the same defect WS-02 exists to prevent, at a smaller scale. PLAN-05 must
  state which runtimes its rule was reasoned about and which it was not.
