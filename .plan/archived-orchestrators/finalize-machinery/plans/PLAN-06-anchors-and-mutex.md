# PLAN-06: Make finalize anchors unfabricable and the mutex reclaimable

epic: finalize-machinery
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-anchors-and-mutex.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Harden the mechanisms finalize trusts: mark-step-done must refuse a
--head-at-completion resolving to no commit instead of persisting a fabricated anchor,
the merge-mutex budget must reclaim from a dead holder via plan liveness instead of
stranding waiters past expiry, a down build daemon must fail loudly instead of
silently removing cross-plan serialization, and phase_handshake must speak with one
verdict and audible errors. Ship anchors the mechanism cannot fabricate or strand.

## Deliverables

1. Unfabricable completion anchors: mark-step-done resolves --head-at-completion
   against the object store and refuses unknown SHAs fail-closed (lesson
   2026-09-05-16-003).
2. Reclaimable merge budget: merge_hold_budget_seconds gains a reclaim path consulting
   manage-locks plan liveness so a dead holder releases (lesson 2026-09-05-16-004).
3. Loud daemon supervision: a down marshalld fails the build lane loudly instead of
   silently dropping serialization into OOM kills (lesson 2026-09-05-16-002).
4. Sound handshake: phase_handshake single verdict per tree (lesson 2026-09-03-16-005)
   with verify errors audible on stderr and non-zero exit preserved (lesson
   2026-09-03-19-006).

## Claim Labels

- OBSERVED: mark-step-done accepts a --head-at-completion resolving to no commit, persisting a fabricated anchor — read at corpus lesson `2026-09-05-16-003` § `fabricated anchor`
  - verdict: corroborated | checked_at: 1605831 | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1525 D1: mark-step-done resolves via git rev-parse --verify, persists canonical full-hex, refuses unknown SHAs
- OBSERVED: the merge mutex survived 18min past a 3600s budget with a waiter queued and no reclaim path; only the holder can release — read at corpus lesson `2026-09-05-16-004` § `dead holder`
  - verdict: corroborated | checked_at: 1605831 | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1525 D2: budget-reclaim evicts only provably stale holders past budget; holder-release path unchanged
- OBSERVED: a down daemon silently removes cross-plan build serialization so concurrent suites OOM — read at corpus lesson `2026-09-05-16-002` § `silent degradation`
  - verdict: corroborated | checked_at: 1605831 | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1525 D3: routing names serialization state; fallback-streak escalation ERROR states the OOM failure model
- OBSERVED: phase_handshake drifts on pending_findings_blocking_count (bidirectional) and verify exits non-zero with empty stderr — read at corpus lessons `2026-09-03-16-005` § `drift` and `2026-09-03-19-006` § `silent failure`
  - verdict: corroborated | checked_at: 1605831 | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1525 D4: drift carries blocking_findings_present key; non-zero verify verdicts mirror to stderr with exits preserved
- HYPOTHESIS: object-store resolution at the mark site plus liveness-consulting reclaim at the mutex site closes both holes without changing the holder-release happy path — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` § `reclaim` (verify-at-outline)
  - verdict: corroborated | checked_at: 1605831 | by: finalize-machinery/analyze | rescoped: n/a | evidence: PR #1525: acquire auto-reclaim and holder-scoped release untouched; 22207 tests green; holder-release happy path unchanged
- Verify-first clause: the consuming phase confirms the anchor, mutex, daemon, and handshake mechanisms against the implementing sources at HEAD before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` — lock core and liveness
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — merge-mutex budget
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py` — daemon supervision
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — daemon lifecycle
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` — mark-step-done anchor
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/phase_handshake.py` — handshake verbs

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-05 touches ledger/retrospective — no shared files, may parallelize
- Adjacent to: finalize-step-lessons-housekeeping retrospective cost (17 fragments in 17 calls) stays a watch until the anchor work lands; not in this plan's surface

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-06-anchors-and-mutex.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
