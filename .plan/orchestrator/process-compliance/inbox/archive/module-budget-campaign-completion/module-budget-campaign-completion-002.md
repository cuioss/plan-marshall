envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-22T20:43:16Z

# Refine-gate fired on ledger-owned paths — advance refused (module-budget-campaign-completion)

Phase-2-refine dispatched leaf returned `status: success` (confidence 99.5,
track complex, scope surgical, qgate_validation_required false) with a scoped
single-carve `clarified_request` for `test/test_shared_harness.py` (D2 slice 1).
Mailbox check-point: `inbox detect` → orchestrated (test-quality),
`inbox read` → `no_mailbox`, nothing waiting.

Post-dispatch contract assertion (`git -C . status --porcelain`) returned 12
non-empty lines, so per `plan-marshall:plan-marshall/workflow/planning.md` the
orchestrator emitted the `[CRITICAL]` refine-contract log, skipped the
`2-refine → 3-outline` metrics boundary, skipped the `2-refine` handshake
capture, and refused the `manage-status transition`. No phase advanced.

## Provenance analysis (why this looks like Issue 1/2, not a rogue leaf)

Every one of the 12 porcelain lines sits under `.plan/orchestrator/`:

- 7 tracked modifications/deletions: process-compliance `epic.md`,
  `plans/PLAN-10-entry-capture.md`, `status.json`, two inbox deletions, and
  test-quality `epic.md` + `status.json`. First-column `M`/`D` markers indicate
  staged index entries — an in-flight operator ledger reconciliation (drain /
  archive moves), not leaf output. The refine leaf's contract restricts it to
  `.plan/local/plans/module-budget-campaign-completion/**`; it cannot stage
  orchestrator files.
- 5 untracked (`??`) paths: the operator's archive/landing moves plus this
  plan's own two sanctioned inbox writes
  (`process-compliance/.../module-budget-campaign-completion-001.md`,
  `test-quality/.../module-budget-campaign-completion-001.md`).

Zero dirty paths fall under repository source (`marketplace/`, `test/`,
`.claude/`) or any other main-checkout tree. The refine return itself wrote
only `clarified_request` into `.plan/local` (untracked, invisible to porcelain).

## Standing-instruction conflict, resolved for compliance

Standing instruction: non-compliance is complete failure. The workflow's
violation branch mandates refusal, so the plan is parked at `2-refine`
(transition not taken) rather than advanced on a red gate. This second filing
extends the earlier Issue 2 (post-init assertion vs ledger dirt): the same
absolute-emptiness shape fires at every phase boundary while the operator's
ledger reconciliation stays in flight, so each boundary parks even when the
phase body provably wrote nothing to the main checkout.

## Suggested rule improvement

Scope the post-phase main-checkout assertion to non-ledger paths (exclude the
orchestrator-owned `.plan/orchestrator/**` tree, symmetric with the
`.plan/local/**` untracked exemption), or compare porcelain before/after the
dispatch and refuse only on newly-appeared non-ledger paths. The current shape
converts every in-flight ledger reconciliation into a full plan stop.

## Recovery needs operator disposition

Options: (a) operator reconciles/commits the staged ledger work, then this plan
resumes at the 2→3 boundary (re-run assertion, metrics fused call, handshake
capture, transition); (b) operator grants an explicit documented override to
advance with the ledger dirt named; (c) abort. No orchestrator file will be
reverted without that disposition — several entries look like staged,
uncommitted operator work that `git checkout --` would destroy irrecoverably.
