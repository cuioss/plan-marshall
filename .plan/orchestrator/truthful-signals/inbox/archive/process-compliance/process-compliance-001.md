envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=truthful-signals
kind=finding
created=2026-09-28T11:42:08Z

# Ledger regression: #1641 reverted this epic's state — restore from `88fcfc9ef`

**Sender:** `process-compliance` orchestrator, 2026-09-28. **Action required:** verify, then restore.

## What happened

PR #1641 (`945e59287`, "chore(orchestrator): land cross-epic ledger sync") was squash-merged onto main
**after** #1643 (`88fcfc9ef`), from a branch cut before #1643. Its body states it *held back* 20 deletions
"with no verifiable successor" — but the squash **deleted exactly those 20 files**, and additionally
reverted the PM-MCP-supersession edits #1643 had landed (spec banners, `epic.md` decision entries, anchor
blocks, queue statuses). Nobody flagged it at merge.

## What it changed in `.plan/orchestrator/truthful-signals/` (94 paths)

| Change | Path | Lines |
|---|---|---|
| `M` | `epic.md` | +524 / -65 |
| `D` | `inbox/archive/review-apparatus/review-apparatus-044.md` | +0 / -132 |
| `M` | `plans/PLAN-205-build-telemetry.md` | +0 / -6 |
| `M` | `plans/PLAN-206-verify-first-a.md` | +0 / -6 |
| `M` | `plans/PLAN-207-verify-first-b.md` | +0 / -6 |
| `M` | `plans/PLAN-208-review-yield-a.md` | +0 / -6 |
| `M` | `plans/PLAN-209-review-yield-b.md` | +0 / -6 |
| `M` | `plans/PLAN-211-baseline-reconcile.md` | +0 / -8 |
| `M` | `plans/PLAN-213-plan-execute-mechanics.md` | +0 / -6 |
| `M` | `plans/PLAN-214-gate-predicates.md` | +0 / -6 |
| `M` | `plans/PLAN-215-worktree-paths.md` | +0 / -6 |
| `M` | `plans/PLAN-216-self-review-detectors.md` | +0 / -6 |
| `M` | `plans/PLAN-217-chat-signal-halt.md` | +0 / -6 |
| `M` | `plans/PLAN-218-config-guards.md` | +0 / -6 |
| `M` | `plans/PLAN-219-finalize-self-review.md` | +0 / -6 |
| `M` | `plans/PLAN-220-cost-mergequeue.md` | +0 / -6 |
| `M` | `plans/PLAN-221-executor-target-fidelity.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-146-the-findings-ledger-one-vocabulary-and-an-experiment-told-from-a-regression.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-149-the-landing-payload-and-what-the-epic-learns-from-it.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-150-build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-151-early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-153-tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-154-operator-facing-authority-surfaces-that-answer-confidently-and-wrongly.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-155-agent-facing-documentation-surfaces-and-the-live-plan-defect-sweep.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-156-mark-step-done-must-derive-head-at-completion-never-accept-it.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-158-a-missing-freshness-reconciliation-record-is-reported-as-un-built-source-drift.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-159-a-documented-finalize-step-command-this-repos-own-hook-denies.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-160-the-billing-cost-column-undercounts-output-five-fold-in-a-report-of-ten-non-comparable-figures.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-162-argparse-rejections-recur-despite-documented-signatures-the-canonical-hint-is-not-uniform.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-163-two-deferred-dispatch-workflow-pin-test-defects-from-plan-truth-157.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-164-worktree-remove-leaves-use-worktree-and-worktree-path-stale.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-165-detect-suspicious-reports-a-clean-allow-list-while-the-harness-warns-on-every-startup.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-167-self-review-on-a-diff-no-resolvable-surfacer-applies-to-loops-to-the-ceiling-instead-of-reporting-not-covered.md` | +7 / -13 |
| `M` | `plans/PLAN-TRUTH-168-sync-defaults-reports-added-while-silently-reverting-a-deliberate-remove-step.md` | +5 / -18 |
| `M` | `plans/PLAN-TRUTH-169-a-timeout-verdict-describes-the-wait-not-the-work-and-time-budgets-are-undeclared.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-170-the-finalize-seam-records-less-than-it-does-and-enforces-less-than-it-documents.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-171-state-writers-that-fabricate-collide-or-fail-silently.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-172-the-lane-transition-lacks-the-arrival-path-and-the-artifacts-its-own-entry-gate-requires.md` | +4 / -9 |
| `M` | `plans/PLAN-TRUTH-173-the-in-run-self-review-instrument-detector-reach-a-bounded-terminus-and-six-vacuity-modes.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-174-plan-retrospective-measurement-integrity.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-175-dispatch-and-phase-boundary-measurement-integrity.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-176-preflight-invocation-validator.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-177-orchestration-detection-fails-open-without-source-id.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-178-scope-creep-guard-emits-a-finding-type-the-ledger-rejects.md` | +0 / -6 |
| `M` | `plans/PLAN-TRUTH-180-three-script-internal-error-recurrences-recovered-around-never-fixed.md` | +0 / -6 |
| `D` | `plans/PLAN-TRUTH-181-self-review-surfacing-foundation-shared-envelope-and-per-content-class-dispatch.md` | +0 / -101 |
| `D` | `plans/PLAN-TRUTH-182-ext-self-review-java-the-java-domain-self-review-surfacer.md` | +0 / -83 |
| `D` | `plans/PLAN-TRUTH-183-ext-self-review-python-the-python-domain-self-review-surfacer.md` | +0 / -81 |
| `D` | `plans/PLAN-TRUTH-184-ext-self-review-javascript-the-javascript-domain-self-review-surfacer.md` | +0 / -79 |
| `D` | `plans/PLAN-TRUTH-185-ext-self-review-documents-the-asciidoc-and-markdown-self-review-surfacer.md` | +0 / -83 |
| `M` | `queue-view.md` | +77 / -91 |
| `M` | `queue/PLAN-205.json` | +1 / -1 |
| `M` | `queue/PLAN-206.json` | +1 / -1 |
| `M` | `queue/PLAN-207.json` | +1 / -1 |
| `M` | `queue/PLAN-208.json` | +1 / -1 |
| `M` | `queue/PLAN-209.json` | +1 / -1 |
| `M` | `queue/PLAN-213.json` | +1 / -1 |
| `M` | `queue/PLAN-214.json` | +1 / -1 |
| `M` | `queue/PLAN-215.json` | +1 / -1 |
| `M` | `queue/PLAN-216.json` | +1 / -1 |
| `M` | `queue/PLAN-217.json` | +1 / -1 |
| `M` | `queue/PLAN-218.json` | +1 / -1 |
| `M` | `queue/PLAN-219.json` | +1 / -1 |
| `M` | `queue/PLAN-220.json` | +1 / -1 |
| `M` | `queue/PLAN-221.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-145.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-146.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-149.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-150.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-151.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-153.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-154.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-155.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-160.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-162.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-165.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-169.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-170.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-171.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-173.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-174.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-175.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-176.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-177.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-178.json` | +1 / -1 |
| `M` | `queue/PLAN-TRUTH-180.json` | +1 / -1 |
| `D` | `queue/PLAN-TRUTH-181.json` | +0 / -10 |
| `D` | `queue/PLAN-TRUTH-182.json` | +0 / -10 |
| `D` | `queue/PLAN-TRUTH-183.json` | +0 / -10 |
| `D` | `queue/PLAN-TRUTH-184.json` | +0 / -10 |
| `D` | `queue/PLAN-TRUTH-185.json` | +0 / -10 |
| `M` | `resume_anchor.md` | +1 / -5 |
| `M` | `settled.md` | +0 / -569 |

(`D` = deleted, `M` = modified, `R` = renamed/moved. Deletion-only `M` rows are typically a stripped banner
or a removed decision / anchor block.)

## How to verify and restore

- See the damage: `git diff 945e59287^ 945e59287 -- .plan/orchestrator/truthful-signals/`
- Restore source: `88fcfc9ef` (the last commit carrying the full state). Only restore paths whose content has
  NOT been legitimately changed on main since — compare `git diff 88fcfc9ef origin/main -- <path>` against the
  #1641 diff first; a later drain or directive in this epic may have superseded part of it.
- ⚠ `queue/*.json` status regressions are not visible as deletion-only rows; diff them explicitly.

The `process-compliance` epic restored its own tree the same way (operator decision: each epic restores its own).
