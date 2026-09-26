# PLAN-TRUTH-168: `sync-defaults` reports `added` while silently reverting a deliberate `remove-step`

> ✅ **RE-OPENED BY OPERATOR (2026-09-26; row status `staged`).** Parked earlier the same day as PM-MCP-superseded,
> then explicitly un-parked by the operator: `/marshall-steward upgrade` blindly overwrites operator adaptations
> (e.g. re-adding a removed `default:verify:coverage`, TokenSheriff#745) in every consumer repo TODAY, and PM-MCP's
> ConfigReconciler currently reproduces the defect (contradiction 2 in
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`), so the fix is needed on both sides.
> **Scope amendment:** the operator names the steward UPGRADE path, not only `manage-config sync-defaults`. The
> outline MUST settle the (still `unverifiable`) upgrade-path claim below against the live `marshall-steward`
> upgrade flow and widen `## Expected Surface` to it if upgrade reaches the back-fill by another route.

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

**Second independent repro, 2026-09-22 (operator dogfood, `7d82d5d90`), broadens the trigger surface.**
Running `marshall-steward` against an existing repo whose `marshal.json` already carried a deliberately
narrow `verification_steps` (`{default:verify:quality-gate, default:verify:module-tests}` — `coverage`
never selected, no `remove-step` ever run against it) silently back-filled `default:verify:coverage` on a
routine run. Ground-truth re-verified independently: `_deep_merge_missing` (`_cmd_sync_defaults.py:288-294`)
back-fills ANY key present in the seed and absent from live, unconditionally, regardless of whether the gap
is a fresh project's never-populated map or an operator's deliberately curated one; `_seed_verify_steps()`
(`_config_defaults.py:794`, `{step_id: {} for step_id in _verify_step_ids()}`) seeds every discovered
built-in step with no `default_on`/applicability filter; `marshall-steward/SKILL.md:648` already
self-labels the path "silent, unconditional." So the defect's trigger is broader than "reverting a
`remove-step`" — it fires on ANY pre-existing pruned/curated `verification_steps` selection, removal or
not. This sharpens D1: the remedy MUST cover the no-removal case too, and the operator's own framing of the
fix is two-fold — (a) an existing `verification_steps`/`steps` map is never expanded without consent, and
(b) adding a not-yet-selected step is something the operator is ASKED about, not merely reported on after
the fact. D1's note below is amended accordingly.

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

**D1 — A removal survives `sync-defaults`, AND a pre-existing curated map is never silently expanded.**
Either keyed step maps become atomic once present (seeded only when the whole map is absent), or
`remove-step` records an explicit opt-out that `_deep_merge_missing` honours. D0 decides which; the choice
must not strand an existing project that legitimately needs a newly-shipped default step back-filled — but
"stranding" is resolved by ASKING (`AskUserQuestion`, once per newly-discovered not-yet-selected step),
never by auto-adding. This covers both triggers the corpus now has evidence for: reverting an explicit
`remove-step` (2026-09-15 report), and expanding a map that simply never included the step in the first
place (2026-09-22 repro, no `remove-step` involved) — the mechanism and the fix are the same for both.

**D2 — `sync-defaults` distinguishes "new default" from "re-adding something removed"** in its report, so a
back-fill that crosses an operator decision can never read as a routine addition.

**D3 — Regression control:** `remove-step X` → `sync-defaults` → X still absent, plus the matched positive
control (a genuinely new default step IS back-filled), for both `verification_steps` and finalize `steps`.

## Claim Labels

- OBSERVED: `_deep_merge_missing` recurses into dicts and back-fills every key absent from live config; its
  docstring states an absent `steps` / `verification_steps` step id is back-filled —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` lines 255–294, read
  at `7a028157e`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_sync_defaults.py:254-297 _deep_merge_missing copies every key absent from live (:292-294) and recurses into dicts; docstring :271-275 states absent steps/verification_steps ids are back-filled.
- OBSERVED: `_seed_verify_steps()` exists as the verify-step seed —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` line 747, read at
  `7a028157e`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _config_defaults.py:782-794 _seed_verify_steps returns {step_id: {} for every built-in verify step} (:775-779), no default_on/applicability filter.
- OBSERVED: `remove-step` is a registered verb on keyed step phases —
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` line 492, read at
  `7a028157e`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_quality_phases.py:577-590 remove-step deletes the key (:584) and records no opt-out; no opt_out/excluded/removed_steps token in manage-config scripts.
- HYPOTHESIS: `/marshall-steward upgrade` Stage 2 runs `sync-defaults` before any operator-intent
  preservation — confirm/refute at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py`
  § the Stage-2 `sub_steps` and `marshall-steward/standards/upgrade-flow.md` (verify-at-outline).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: upgrade.py:146-158 Stage 2 first sub_step reconcile-marshal-json; upgrade-flow.md:338-343 runs sync-defaults first; no operator-intent step before it. Second route: marshall-steward/SKILL.md:638-648 re-run remediation.
- HYPOTHESIS: the observed byte-for-byte revert (sender-observed on Token-Sheriff) reproduces at HEAD —
  confirm/refute with a D3 fixture against `_cmd_sync_defaults.py` § `_deep_merge_missing`
  (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Needs the D3 fixture run; static read supports the revert (remove-step deletes :584, sync-defaults re-adds :292-294); byte-for-byte equality open (docstring says None, seed value is {}).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` — the merge and its report (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` — `remove-step` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — the seeds (D0)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — the documented `sync-defaults` / `remove-step` contract (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-config/` — D3 controls (verify-at-outline)
- OBSERVED (2026-09-26 sweep): `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` — the upgrade flow invokes `manage-config sync-defaults` at line 339–342 (`sync-defaults` then `steps-sort` then `normalize-keys`); the upgrade report wording and any operator-intent step live here
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — the upgrade verb's documented contract (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — `_STAGE_SPECS` (:146-158) changes if the ask-before-add becomes its own Stage-2 sub-step (cleanup 2026-09-26, understated) (verify-at-outline)
- OBSERVED: `test/plan-marshall/marshall-steward/` — `test_upgrade_flow_stage2.py` pins Stage-2 order sync-defaults -> steps-sort -> normalize-keys; any operator-intent step breaks it (cleanup 2026-09-26, understated)

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
