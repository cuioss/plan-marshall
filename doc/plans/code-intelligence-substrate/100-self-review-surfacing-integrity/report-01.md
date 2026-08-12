# Run report — 100-self-review-surfacing-integrity (run 01)

**Date (UTC):** 2026-08-12    **Branch:** claude/self-review-surfacing-integrity-jcwvqa (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (working contract — loaded first)
- `plan-marshall:ref-code-quality` (always) — read via bundle path
- `pm-plugin-development:plugin-script-architecture` (always) — read via bundle path
- `pm-dev-python:python-core` (Python production code) — read via bundle path
- `pm-dev-python:pytest-testing` (Python tests) — read via bundle path

Standards from these skills are loaded on-demand as the work requires.

## Deliverables

_Filled in as the run proceeds._

- **D1** — widen the stale-count detector's file set to match its sibling's, at the resolver; negative-control fixture. _pending_
- **D2** — tie registry membership to check coverage by a population-derived invariant; add the two missing consuming checks. _pending_
- **D3** — every residual/absence claim publishes searched scope + file count. _pending_
- **D4** — a message naming a running plan is reported undeliverable at write time. _pending_
- **D5** — termination criterion distinguishes converged from out-of-budget; self-seeding round reported as such. _pending_

## Build gate

_Filled in at Step 5._

## Findings

### Claim re-verification (Step: investigation)

Each plan claim label re-verified against the clone at HEAD `4a1936e`:

- **D1 asymmetry — CONFIRMED.** `_detect_count_prose` (`_self_review_detectors.py:1040`) opens only
  `skill_dir / 'SKILL.md'`, while its sibling `_collect_skill_contract_sources` (`:276`) returns
  "SKILL.md plus every standards/*.md". A stale count in a `standards/*.md` doc is surfaced by no
  candidate list. Fix at the resolver: `_detect_count_prose` will iterate
  `_collect_skill_contract_sources`.
- **D2 two uncovered counted entries — CONFIRMED and authoritatively recorded.**
  `ext-point-self-review-surfacing.md:219-222` explicitly records `duplicate_claimable_keys` and
  `discard_without_report` as the two `in_total: true` keys with "No consuming check", with a
  "Recorded coverage gap" paragraph. `keep_markers` (also `in_total: true`) IS covered (Check 4,
  per the contract's Consumed-By table). So exactly two entries need checks. Direction per plan: ADD
  the two checks (16, 17); do not drop `in_total`.
- **D3 asserted-absence REFUTED — D3 changes shape (as the plan anticipated).** The scope token
  (`surface_scope`) and file-count token (`files_in_scope`) DO now exist — emitted unconditionally
  by the surfacer (`self_review.py:330-331`), documented in the workflow doc (`:122`), the SKILL.md,
  and the ext-point schema. So the surfacer already publishes scope + count. The residual gap: the
  operator-facing VERDICT (`display_detail` clean strings) and the workflow's absence claims do not
  carry them, and no invariant pins that a clean claim must. D3 becomes: pin the always-emitted
  invariant, carry scope into the workflow's clean-verdict contract, and require every absence claim
  (this run's own included) to state its scope + file count.
- **D4 — CONFIRMED structural.** The inbox (`_orchestrator_inbox.py`, `inbox-envelope.md`) is the
  epic's plan→epic OUTBOX, drained by the orchestrator between plans; "the plan never reads the
  ledger to make a decision." There is no plan-as-recipient channel, so a message intended for a
  running plan is architecturally undeliverable. `cmd_inbox_write` currently always queues. Minimal
  honest form (D4): make the write verb report undeliverable at write time when a message targets a
  currently-running plan, without building a delivery channel.
- **D5 — CONFIRMED pattern.** The self-review step re-fires per round on HEAD-advance (loop-back);
  the loop closes only on a full-surface clean pass. There is no criterion distinguishing *converged*
  from *out of budget*, and no self-seeding classification. D5 adds both to the workflow doc,
  coordinating with D3 (published scope makes a self-seeded round identifiable).

### Verification sub-agent / CI / PR review

_Filled in from the verification sub-agent, CI, and PR review._

## Reviewer participation

_Filled in at Step 7/8._

## Cost

_Filled in at close._

## Contract check (Step 9)

_Filled in at close._

## What have we learned (Step 9)

_Filled in at close._

## Residue

_Filled in at close._
