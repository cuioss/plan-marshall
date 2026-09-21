# PLAN-03: OpenCode emitter re-enable with inherit fallback

epic: model-provisioning
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Re-enable per-level model provisioning in the OpenCode target: level variants resolve each dispatch level to the user's configured model from the local map (local or provider-routed entry), while the inherit-only posture stays as the fallback when no pin exists. Reverses commit 2ec552ba4 deliberately per PLAN-01's contract, not by drift.

## Deliverables

1. Variant emission change: per-level variants carry the configured model pin instead of always omitting model/reasoningEffort, with pin-absent levels still emitting inherit-only.
2. Frontmatter transform handling for both entry kinds: alias-mapped models resolve via model_map, already-qualified provider/local strings pass through unchanged.
3. Lockstep and emitter tests updated: pinned variants asserted per kind, fallback variants asserted byte-identical to canonical.
4. Narrow-but-never-escalate enforcement at emit time: a pin never resolves above its configured level.

## Claim Labels

- OBSERVED: Every OpenCode level variant is emitted model-less with no model or reasoningEffort frontmatter, dispatching on the session model — read at `marketplace/targets/opencode/variant_emitter.py` § `Inherit-only emission`
- OBSERVED: The OpenCode frontmatter transform resolves a Claude model alias via model_map to a prefixed model id and passes unmapped (already-qualified or custom) values through unchanged — read at `marketplace/targets/opencode/frontmatter.py` § `_resolve_model`
- OBSERVED: The variant identity is carried by the filename with no name line emitted, and no variant is ever skipped on the OpenCode side — read at `marketplace/targets/opencode/variant_emitter.py` § `emit_agent_variants`
- OBSERVED: The level palette is shared single-source from the Claude target so level names cannot drift — read at `marketplace/targets/opencode/variant_emitter.py` § `Level palette`
- HYPOTHESIS: Per-variant pins can be threaded from the local map through render_variant_frontmatter without breaking the canonical target-neutral invariant — confirm/refute at `marketplace/targets/opencode/variant_emitter.py` § `render_variant_frontmatter` (verify-at-outline)
  - verdict: corroborated | checked_at: fb8aadc9 | by: model-provisioning/cleanup | rescoped: n/a | evidence: render_variant_frontmatter pops implements/levels and adds no model; validate_canonical keeps canonicals target-neutral; _resolve_model passes custom strings through — the pin-threading seam exists at this sha
- Verify-first clause: The consuming outline phase must settle the HYPOTHESIS against the emitter implementing source before scoping the change — refutation re-scopes the threading approach.

## Expected Surface

- OBSERVED: `marketplace/targets/opencode/variant_emitter.py` — variant emission under change
- OBSERVED: `marketplace/targets/opencode/frontmatter.py` — frontmatter transform under change
- OBSERVED: `marketplace/targets/opencode/mapping.json` — alias-to-id map consumed by the transform
- OBSERVED: `marketplace/targets/opencode/emitter.py` — bundle emit path

## Dependencies and Sequencing

- Depends on: PLAN-01-schema-resolve-slot (slot contract), PLAN-02-steward-pin-materialization (pin shape)
- Overlaps with: none (same workstream as PLAN-02 but sequenced after it — scope is 1)
- Adjacent to: steward skill surface (PLAN-02, untouched here), Claude variant_emitter level table (shared source, read-only)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/model-provisioning/plans/PLAN-03-emitter-reenable.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
