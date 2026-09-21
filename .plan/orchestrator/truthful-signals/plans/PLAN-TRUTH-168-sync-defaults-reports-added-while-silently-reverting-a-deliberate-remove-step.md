# PLAN-TRUTH-168: `sync-defaults` reports `added` while silently reverting a deliberate `remove-step`

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from inbox message `lessons-handling-26-09-04-01-064.md`, relayed from Token-Sheriff
PLAN-15 (PR cuioss/TokenSheriff#745, plan-marshall `0.1.1670`). The relaying orchestrator checked the
mechanism against source; this orchestrator re-read it at `7a028157e`. No staged or live spec in any epic
mentions `sync-defaults`, `_deep_merge_missing`, or `remove-step`.

## Objective

**An operator removes `default:verify:coverage` with the sanctioned `manage-config plan phase-5-execute
remove-step`; the next `manage-config sync-defaults` reports `added: …default:verify:coverage` and restores
`.plan/marshal.json` byte-for-byte to its pre-removal state.** `/marshall-steward upgrade` runs
`sync-defaults`, so routine maintenance undoes a deliberate decision, and the only trace is a
`marshal.json` diff inside a steward PR that reads as a benign default refresh.

The report is truthful about the mechanism (a key was added) and silent about the meaning (an operator
removal was reverted) — the epic's confident-signal-hides-a-caveat shape. The same shape applies to every
keyed step map with a seed (`phase-6-finalize` `steps`), and a second instance on a different field — the
steward upgrade discarding legacy `enabled_bots` because `sync-defaults` runs first — is already recorded.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive every keyed map `sync-defaults` deep-merges that an operator verb can remove from.**
Enumerate the seeded keyed maps and the verbs that remove entries from them; publish the population.

**D1 — A removal survives `sync-defaults`.** Either keyed step maps become atomic once present (seeded only
when the whole map is absent), or `remove-step` records an explicit opt-out that `_deep_merge_missing`
honours. D0 decides which; the choice must not strand an existing project that legitimately needs a
newly-shipped default step back-filled.

**D2 — `sync-defaults` distinguishes "new default" from "re-adding something removed"** in its report, so a
back-fill that crosses an operator decision can never read as a routine addition.

**D3 — Regression control:** `remove-step X` → `sync-defaults` → X still absent, plus the matched positive
control (a genuinely new default step IS back-filled), for both `verification_steps` and finalize `steps`.

## Claim Labels

- OBSERVED: `_deep_merge_missing` recurses into dicts and back-fills every key absent from live config; its
  docstring states an absent `steps` / `verification_steps` step id is back-filled —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` lines 255–294, read
  at `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_sync_defaults.py:254-297 _deep_merge_missing recurses into dicts and back-fills every key absent from live; its docstring states verbatim that an absent steps/verification_steps step id is back-filled (line range moved from 255-294).
- OBSERVED: `_seed_verify_steps()` exists as the verify-step seed —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` line 747, read at
  `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _seed_verify_steps exists in _config_defaults.py (3 references; line number has moved off 747, which now holds the BUILD_VERIFY_STEP_EXT_POINT comment block).
- OBSERVED: `remove-step` is a registered verb on keyed step phases —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` line 492, read at
  `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_quality_phases.py:577 dispatches elif args.verb == remove-step and phase_section in STEP_PHASES - a registered verb on keyed step phases (line moved from 492).
- HYPOTHESIS: `/marshall-steward upgrade` Stage 2 runs `sync-defaults` before any operator-intent
  preservation — confirm/refute at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py`
  § the Stage-2 `sub_steps` and `marshall-steward/standards/upgrade-flow.md` (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The claim's own confirm-at target is GONE: marshall-steward/standards/upgrade-flow.md does not exist (that standards dir holds only effort-menu.md and pin-provisioning.md), and upgrade.py carries no sync-defaults token at all. Not settled.
- HYPOTHESIS: the observed byte-for-byte revert (sender-observed on Token-Sheriff) reproduces at HEAD —
  confirm/refute with a D3 fixture against `_cmd_sync_defaults.py` § `_deep_merge_missing`
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Reproducing the byte-for-byte revert requires running the D3 fixture; not executed in a read-only pass.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` — the merge and its report (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` — `remove-step` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — the seeds (D0)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — the documented `sync-defaults` / `remove-step` contract (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-config/` — D3 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Shares `test/plan-marshall/manage-config/` with staged PLAN-TRUTH-147 — the disjointness gate sequences.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-168-sync-defaults-reports-added-while-silently-reverting-a-deliberate-remove-step.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
