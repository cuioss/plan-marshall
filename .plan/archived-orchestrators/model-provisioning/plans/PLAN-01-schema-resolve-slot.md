# PLAN-01: Local-map schema and resolve-chain slot

epic: model-provisioning
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Decide and record the machine-local effort-to-model map schema (including the entry-kind discriminator distinguishing local models from provider-routed configs such as Zen/Go) and its settled slot in the effort resolve chain. Inherit-only stays as the fallback; the local map re-enables per-level provisioning on top. No behavior change lands here — the output is the settled decision plus the resolve-seam contract WS-02 builds on.

## Deliverables

1. Local-map schema decision (shape, entry-kind discriminator, machine-local storage home) recorded as an ADR or schema doc.
2. Resolve-chain slot contract: where the local map sits relative to per-sub-key override, phase default, phase string, plan.effort, and the inherit fallback — with narrow-but-never-escalate stated.
3. Fallback semantics: inherit-only preserved as workaround-turned-fallback, never removed.

## Claim Labels

- OBSERVED: Effort resolution walks per-sub-key override, phase default slot, phase plain-string effort, plan-wide effort, then implicit inherit fallback — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-variants.md` § `Resolution Order`
- OBSERVED: The level palette maps level-1 through level-7 plus inherit to model/effort primitives via aliases, with level-6/level-7 alias-capability-gated — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-levels.md` § `Level Table`
- OBSERVED: The resolver's role registry covers plan phases plus the orchestrator effort surfaces with default and max — read at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` § `KNOWN_ROLES`
- OBSERVED: OpenCode level variants are currently emitted model-less (no model/reasoningEffort frontmatter) so every dispatch inherits the session model — read at `marketplace/targets/opencode/variant_emitter.py` § `Inherit-only emission`
- OBSERVED: Commit 2ec552ba4 made OpenCode execution-context variants inherit-only as an adaptation, keeping the shared level palette and dispatch contract unchanged — read at git history § `2ec552ba4`
- HYPOTHESIS: A machine-local map with a local vs provider-routed entry-kind discriminator can slot into the resolve chain above the inherit fallback without changing the Claude-target binding — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` § `_resolve_orchestrator_level` (verify-at-outline)
  - verdict: corroborated | checked_at: fb8aadc9 | by: model-provisioning/analyze | rescoped: n/a | evidence: ADR-021 settles the local vs provider-routed discriminator and the post-resolve slot above the inherit fallback at this sha; _cmd_effort.py seam note is comment-only so the Claude-target binding is unchanged
- Verify-first clause: The consuming outline phase must settle the HYPOTHESIS against the resolver implementing source before scoping steward/emitter work — refutation loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` — resolver contract under decision
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-variants.md` — resolve-chain doc
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-levels.md` — level palette doc
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md` — config-schema home for the local map

## Dependencies and Sequencing

- Depends on: none (first in epic; entry precondition is the tooling-truthfulness effort-lever re-enable trigger firing first)
- Overlaps with: none
- Adjacent to: WS-02 steward/emitter surfaces (consumers of this contract, untouched here)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/model-provisioning/plans/PLAN-01-schema-resolve-slot.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
