# PLAN-TRUTH-179: OpenCode target detection landed; three gaps it exposed still stand

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-22 from a paste-mode landing report on unorchestrated PR #1595 (`a41de18`,
opencode target auto-detection via `OPENCODE`/`OPENCODE_PID`, merged). The four owed follow-ups
arrived with it; each mechanism below was re-grounded against this repo's code at HEAD before
staging — corroborated, corrected, or (one) recorded healed. The report's runtime instances
(residual counts, hang observations, the descriptor deletion) are provenance, not ledger facts.

## Objective

**Detection shipped; the consumers were never told.** Three defects, one shape: a new target the
detector now resolves, and downstream code that still assumes the old world — alphabetical path
emission that lets stale user-global copies shadow live tree code, an enrichment skip keyed off
the declared target instead of the detected one, and a wait clamp that disables itself exactly
when the target is new.

## Deliverables

Three deliverables. Each owns its proof at outline; the corroboration below names where to look,
not what the answer is.

**D0 — Executor path order must not let stale copies shadow live code (ship-blocking).** With
correct opencode detection, generated executors embed user-global roots (`~/.config/opencode/…`)
ahead of tree dirs by alphabetical emission, so stale cache copies shadow live code
(`manage-config` crashed at import on the reporter's machine). Order tree dirs first and exclude
(or deprioritise) user-global roots in the generated `sys.path`/resolver emission. Control: a
regen on an OpenCode machine resolves every notation to tree code with a stale cache present.

**D1 — The metrics enrich skip must follow the detected target, not the declared one.** The
transcript-less skip exists (`_TRANSCRIPT_LESS_TARGETS`, skip branch with gap flag) but keys off
`runtime.target` as declared in `.plan/marshal.json`; on any machine where auto-detection newly
resolves `opencode` while the file still declares `claude`, enrichment errors `missing_session_id`
instead of skipping. Close the declared-vs-detected skew either way (read the detected target, or
document the declaration as authoritative and say so). Control: enrich on a detected-opencode run
with a `claude`-declaring marshal file takes the skip branch with its gap flag.

**D2 — The CI-wait clamp must hold for targets with no declared harness ceiling.** The clamp
disables itself when the target imposes no ceiling — the exact state of a brand-new target — so the
wait hangs past every ceiling it was supposed to honour (twice observed, silent past the Bash
ceiling). Give the opencode target a ceiling or a bounded fallback, and make the disabled-clamp
state loud rather than silent. Control: a still-running CI resolves to `deadline_exceeded`
re-poll inside the clamp, never a silent hang past it.

**Healed, no work — worktree discover descriptor deletion.** The report attests the 2/12-modules
discover that deleted 10 descriptors mid-finalize was healed by the landed PR's own cached-root
fix, the tree was restored, and the retry went clean. Recorded here so the item is dispositioned,
not dropped; reopen only on recurrence.

**Recurrences 2026-09-24 (PLAN-TRUTH-147 landing):** metrics landed unenriched on a transcript-less
opencode target with no session identity (~25h wall, 0 measured tokens) — second live instance of
D1's declared-vs-detected skew; and an executor-poisoning incident recovered via the steward
bootstrap path — second live instance of D0's stale-shadow shape. Both strengthen the deliverables
without changing them; no surface change.

## Claim Labels

- OBSERVED: alphabetical emission sites order generated executor paths — `generate_executor.py:1492`
  (`sorted(...)` PYTHONPATH assembly) with user-global roots in the population; dot-dirs sort ahead
  of tree dirs — re-verify at outline and prove the shadowing live (verify-at-outline).
  - Corroborated-mechanism 2026-09-22 at HEAD by the staging session; live proof is D0's.
- OBSERVED: the enrich skip keys off the declared target (`_resolve_runtime_target` reads
  `.plan/marshal.json`, defaults `claude`) while detection resolves independently — re-verify at
  outline and prove the skew live (verify-at-outline).
  - Corroborated-mechanism 2026-09-22 at HEAD by the staging session; live proof is D1's.
- OBSERVED: the wait clamp disables itself when the target imposes no ceiling
  (`ci_complete_precondition.py:175` region; `_clamp_wait_ceiling` + runtime-seam ceiling read) —
  re-verify at outline and prove the hang-or-bound live (verify-at-outline).
  - Corroborated-mechanism 2026-09-22 at HEAD by the staging session; live proof is D2's.
- ⚠ HYPOTHESIS: these three are independent rather than one detection-rollout cause — ⛔ D0 decides
  only its own member; no collapse is asserted (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — path emission order (D0)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — enrich skip branch and target resolution (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py` — clamp and ceiling read (D2)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/`, `test/plan-marshall/manage-metrics/`, `test/plan-marshall/phase-6-finalize/` — D0/D1/D2 controls (verify-at-outline)
- HYPOTHESIS: the platform-runtime harness-ceiling seam consumed by the clamp (D2) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Shares `phase-6-finalize/**` and `manage-metrics/**` with staged PLAN-TRUTH-147/169/175/205 and
  `tools-script-executor/**` with PLAN-TRUTH-154/176/215/221 — sequence, never pair (N=1 makes this
  automatic, recorded so a future scope change keeps it).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-179-opencode-target-detection-landed-three-gaps-it-exposed-still-stand.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
