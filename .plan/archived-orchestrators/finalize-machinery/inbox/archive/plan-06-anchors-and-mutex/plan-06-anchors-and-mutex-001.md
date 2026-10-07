envelope_version=1
sender_type=plan
sender_id=plan-06-anchors-and-mutex
epic=finalize-machinery
kind=landing
created=2026-09-18T07:29:57Z

# Landing: PLAN-06-anchors-and-mutex

plan_id: plan-06-anchors-and-mutex
spec: .plan/orchestrator/finalize-machinery/plans/PLAN-06-anchors-and-mutex.md
epic: finalize-machinery
workstream: WS-04
status: shipped
pr: 1525
pr_url: https://github.com/cuioss/plan-marshall/pull/1525
merge_commit: 1605831c5a8081f9b38b17d741fd910abb67717a
superseded_pr: 1523 (closed unmerged to re-trigger review tooling)

## Deliverables (4/4)

1. Unfabricable completion anchors: `mark-step-done` resolves
   `--head-at-completion` via `git rev-parse --verify {sha}^{commit}`,
   persists the canonical full-hex object ID, refuses unknown SHAs
   fail-closed (`unknown_head_at_completion`, nothing written).
2. Reclaimable merge budget: `merge_lock budget-reclaim --plan-id
   --hold-start --hold-budget-seconds` evicts only provably `stale` holders
   past budget via sidecar arbitration (+FIFO dequeue); `fresh`/`unknown`
   refuse; invalid inputs refused; audit fields on every branch. Wired into
   the branch-cleanup budget path.
3. Loud daemon supervision: routing resolutions name
   `serialization=daemon-scheduled|fallback-slot|unserialized|unknown`;
   fallback-streak escalation ERROR states the accurate failure model
   (fallback-slot serialization active, plan-less unserialized, OOM risk).
4. Sound handshake: `verify` blocking-findings drift carries the
   `blocking_findings_present` verdict key + counts (one vocabulary per tree
   state); non-zero `verify --strict` verdicts mirror to stderr with exit
   codes preserved; `cmd_verify` handles `PrTitleMissing` with the capture
   envelope.

## Verification

- `compile plan-marshall`: green (before + after rebase onto slice-040).
- `module-tests plan-marshall`: green, 22207 tests (6 new anchor, 6 new
  budget-reclaim, extended escalation/handshake suites; 8 legacy suites
  re-anchored from fabricated literals to live HEAD SHAs; forwarded onto the
  slice-040 cluster split for `test_ci_verify_reporting.py` /
  `test_loop_back_outcome_outcome.py`).
- `quality-gate plan-marshall`: green (ruff + mypy + plugin-doctor).
- Pre-merge `findings-check --phase 6-finalize`: clean (blocking_count 0).
- CI on PR #1525: overall success (11 checks, incl. Python Verify on the
  rebased HEAD).
- CodeRabbit: 8 actionable findings received, all addressed in 471455194,
  threads resolved with CodeRabbit's own "Addressed" markers. Requested
  re-review of the fix commit stayed quota-blocked (4x90min waits + explicit
  `@coderabbitai review`; bot: incremental system does not re-review
  already-reviewed commits via command).

## Re-grounded claim verdicts

- OBSERVED mark-step-done acceptance: CONFIRMED at HEAD (presence-only
  validation), closed by D1.
- OBSERVED merge-mutex no-reclaim: CONFIRMED at HEAD (no budget-aware verb),
  closed by D2 (holder-release happy path unchanged).
- OBSERVED down-daemon silent degradation: PARTLY REFINED at HEAD (fallback
  serializes via machine-global slot + streak escalation existed; residual
  gap was audibility/naming), closed by D3.
- OBSERVED handshake drift + silent verify: CONFIRMED at HEAD (capture=error
  vs verify=drift envelopes; empty stderr on non-zero exit), closed by D4.
- HYPOTHESIS (object-store resolution + liveness reclaim close both holes
  without changing holder-release): CONFIRMED — acquire auto-reclaim and
  holder-scoped release untouched; 22207 tests green.

## Notes for the ledger

- Rebase over upstream slice-040 test-cluster split mid-flight
  (test_ci_verify.py deleted, loop_back_outcome split); remediation
  forwarded, suite green on the combined tree.
- Closed PR #1523 unmerged (CodeRabbit quota); #1525 reviewed.
- Process-rule observations filed separately to the process-compliance inbox.
