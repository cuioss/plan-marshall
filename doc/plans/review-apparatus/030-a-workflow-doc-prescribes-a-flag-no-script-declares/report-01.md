# Run report — 030-a-workflow-doc-prescribes-a-flag-no-script-declares (run 01)

**Date (UTC):** 2026-08-11T08:13Z    **Branch:** claude/workflow-flag-script-mismatch-q42lik (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action)
- `plan-marshall:ref-code-quality` (+ `standards/error-handling.md` — the § "Fail-Closed Classification" rules (b)/(c)/(e) that this plan's D0/D1 implement) — read from bundle path
- `pm-plugin-development:plugin-script-architecture` (+ `standards/output-contract.md` — exit-code convention: exit 2 = argparse rejection) — read from bundle path

Conditional surfaces this plan touches (Python production code, Python tests, workflow docs, SKILL/bundle structure) are being worked from the re-grounded code directly; the domain standards above cover the fail-closed discipline that governs the fix.

## Re-grounding against merged main (findings so far)

Line references in the plan were treated as stale and re-read. Established directly from source:

- `review_completeness.py` — `parse_participation` (bot_kind:evidence_kind pairs) **silently drops** a bare/colonless token at its `continue`; the bot then falls through `classify_bot` to `STATE_ABSENT`, a **blocking** member. `--participated-bots` uses pair-form `parse_participation`; `--stale-participation-bots` (and the other `--*-bots` flags) use bare-form `_split_bots`. This is the D1 flag-set inconsistency.
- `github_pr.py` `fetch_findings` declares only `--pr-number/--plan-id/--required-bots/--optional-bots` — **no `--enabled-bots`** (confirms OBSERVED claim 1). The producer emits `{bot_kind, evidence_kind}` **pairs for BOTH** `participated_bots` and `stale_participation_bots` (lines ~1180-1191) (confirms OBSERVED claim 4). The `stale_participation_bots` pair shape is heavily asserted in `test_github_pr.py`, so D2 must reconcile the *documented invocation* (forward the bare `bot_kind` column) rather than change the producer output.
- `input_validation.parse_args_with_toon_errors` swallows **known identifier-validator** failures to exit 0 + `status: error`, but an **unrecognized flag** (`--enabled-bots`) falls through to argparse's real **exit 2**. So the `--enabled-bots` rejection genuinely exits 2 — the swallow is downstream (barrier/step interpretation), i.e. error-handling.md rule (e): exit 0 is necessary not sufficient; the `status` field must be read.
- Prior shipped remedy (`#1063`) exists: `test_bot_participation_contract.py::TestCrashedGateNeverRecordsAPass` plus a `nargs='?'` parser relaxation and **prose** UNKNOWN-verdict branches in `automatic-review/SKILL.md` and `phase-6-finalize/standards/branch-cleanup.md`. `_scan_invocation_sites()` there already derives documented invocations from the tree (the D3 model), and `_CONFIRMED_SITES` names four call sites. Whether this prose guard covers the full finalize merge-and-review population (D0) is under active mapping.

## Deliverables

_In progress — see below as each lands._

## Build gate

_Pending._

## Findings

_Pending (verification sub-agent + CI + review)._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
