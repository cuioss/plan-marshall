envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:11:24Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-07-29
bundle=plan-marshall

# Emit the [STEP] Completed marker from mark-step-done, not from the caller

Fifteen finalize steps reached `outcome: done` in `status.metadata.phase_steps["6-finalize"]`.
The work log carries only **11** `[STEP] Executing step:` markers and **10**
`[STEP] Completed step:` markers.

| Step | `Executing` | `Completed` | `phase_steps` |
|------|:--:|:--:|:--:|
| `finalize-step-sync-baseline` | yes | **no** | done |
| `project:finalize-step-lessons-housekeeping` | yes | yes | done |
| `pre-push-quality-gate` | yes | yes | done |
| `project:finalize-step-plugin-doctor` | yes | yes | done |
| `pre-submission-self-review` | yes | yes | done |
| `architecture-refresh` | yes | yes | done |
| `push` | yes | yes | done |
| `create-pr` | **no** | yes | done |
| `project:finalize-step-era-stamp-fill` | yes | yes | done |
| `ci-verify` | yes | yes | done |
| `automatic-review` | yes | yes | done |
| `project:finalize-step-review-retrospective` | **no** | **no** | done |
| `lessons-capture` | **no** | **no** | done |
| `finalize-step-preference-emitter` | yes | **no** | done |
| `branch-cleanup` | yes | **no** | done |

The status ledger and the marker stream disagree by about a third, in both directions — three
steps opened and never closed, two ran with no markers at all, one closed without opening.

## Root cause

The markers are emitted by the caller as separate `manage-logging work` calls, adjacent to but
independent of the `mark-step-done` call that writes the authoritative record. Two independent
emissions of the same fact drift; the one that matters for control flow (`mark-step-done`) always
fires, the one that matters for observability does not.

## Solution

Fuse the emission to the record: have `manage-status mark-step-done` emit the
`[STEP] Completed step: {step}` work-log line itself, and the step-entry counterpart at the
dispatch branch that opens the step. Then the marker stream is a projection of the status ledger
by construction and cannot drift from it. This is the same fusion argument
`dispatch-inline-split.md` already makes for the `[DISPATCH]` emission being fused to the dispatch
branch in `SKILL.md` Step 3.

## Impact

Every retrospective aspect and audit check keyed on the markers under-counts finalize coverage
against a status ledger that reports everything done — the logging-gap aspect, the
finalize-flow-conformance audit check, and any operator reading the work log to see where a run
got to.

Worth recording plainly: **this plan SHIPPED `test_step_completion_emission.py`**, hardening
exactly this emission contract at the document level, in the same PR whose own run left a third of
the emissions unmade. The document-side invariant is now test-enforced while the runtime emitter
still skips. That gap between "the contract is tested" and "the contract is honoured at runtime"
is the epic theme in its purest form.

## Evidence

- `status.metadata.phase_steps["6-finalize"]` — 15 entries, all terminal.
- `logs/work.log` — 11 `[STEP] Executing step:` and 10 `[STEP] Completed step:` lines; the
  per-step table above is the pairing.
- The merged PR `d714a14e3` includes
  `test/plan-marshall/phase-6-finalize/test_step_completion_emission.py`.
