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

- **D1 — widen the count-prose detector at the resolver (commit `53d49f3`).** `_detect_count_prose`
  now iterates `_collect_skill_contract_sources` (SKILL.md + `standards/*.md`) instead of opening only
  `SKILL.md`, so both detectors resolve the one conceptual input through one resolver. **Verified:** a
  negative-control test plants a count in a `standards/*.md` doc and asserts it is surfaced — it FAILS
  against the pre-fix resolver (confirmed by stashing the detector change and re-running: both new
  tests failed) and passes after; an agreement test pins the detector's scanned file set to the shared
  resolver's output. Docs (SKILL.md rule 14, ext-point `count_prose` row) updated.
- **D2 — population-derived registry↔check coverage + two new checks (commit `5ae9848`).** Added
  cognitive checks 16 (`duplicate_claimable_key`) and 17 (`discard_without_report`) to the workflow
  doc — the two `in_total` registry entries the ext-point recorded as having "No consuming check".
  `keep_markers`'s consumption by check 4 is now explicit in the doc too. **Verified:** a
  population-derived test enumerates the `in_total` registry entries, publishes the population size
  (guarding against a vacuous pass over an empty population), and fails if any counted entry lacks a
  backtick-quoted reference in the Step-3 checks region; a synthetic negative control proves the
  predicate fails when a check is missing. **Dispatch-gate magnitude unchanged by construction:** no
  `in_total` flag changed, asserted by `test_new_checks_do_not_change_total_magnitude`. Coverage-gap
  paragraph in the ext-point marked closed; "fifteen"→"seventeen" reconciled across the workflow doc,
  the ext-point contract, and the implementor SKILL.md.
- **D3 — publish and require the searched-scope statement (commit `cb577b2`).** ⚠ **Claim shape
  changed** (as the plan anticipated): the scope token (`surface_scope`) and file-count token
  (`files_in_scope`) already existed. Added `scope_statement` (derived from them) emitted
  UNCONDITIONALLY by the surfacer — pinned present on full, delta, and empty (zero-file) surfaces, so
  the surface never presents an absence without the scope it was drawn against. Added the workflow rule
  "Absence claims state the scope they were drawn against": a finding rationale asserting an absence
  MUST quote the round's `scope_statement` and never phrase the claim wider than `files_in_scope`.
  Docs updated. **This run's own absence claims carry their scope** — see the § Findings note below.
- **D4 — undeliverable-to-running-plan report at write time (commit `89ddcbf`).** Added optional
  `--target-plan` to `inbox write`; when it names a plan the epic `status.json` positively reads as
  `running`, the write is refused (`undeliverable_to_running_plan`) rather than silently queued. Not a
  mid-run delivery channel — the flag is a plan id, never reaches the write path. `RUNNING_STATUS`
  moved to `_orchestrator_inbox` and imported back into `orchestrator.py` (single source, avoiding the
  source-of-truth drift this surface exists to catch). **Verified:** 4 end-to-end tests (running →
  refused + not queued; non-running → queued; untargeted → unaffected; malformed id → rejected). The
  `--help` write-boundary test's `--target` substring guard tightened to `--target ` (its own `--file `
  convention) so it still forbids a bare output-target arg while admitting the identifier flag. Docs:
  inbox-envelope.md § Write-side deliverability + orchestrator SKILL.md canonical invocation.
- **D5 — cap the round loop on convergence, not budget (commit `0c69f8b`).** Doc-only change to the
  self-review workflow: added a "Round-loop termination" section defining a SELF-SEEDING round (all
  findings are doc-claim findings inside the delta scope — the prose this plan's own prior rounds
  authored, identified via D3's published scope), reporting it as such rather than as an ordinary
  non-clean round; prescribing resolution by DELETION not correction; and distinguishing a CONVERGED
  close (full-surface clean pass) from an OUT-OF-BUDGET close (warning deviation, doc-claim half
  non-converged). NOT a round-count reduction. Verification is a cold read (Step 6 sub-agent).

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

### Scope-bearing absence claims (D3 self-binding)

D3 binds this plan against itself: its own residual/absence claims must publish the scope searched and
the file count, from the first round. This run's absence claims, each with its scope:

- **"Exactly two `in_total` registry entries lacked a consuming check."** Searched scope: the
  `CANDIDATE_LISTS` registry in `_self_review_patterns.py` (1 file, 23 entries, 17 `in_total`)
  cross-referenced against the "Consumed By" table in `ext-point-self-review-surfacing.md` (1 file) and
  the Step-3 checks region of `pre-submission-self-review.md` (1 file). Result: `duplicate_claimable_keys`
  and `discard_without_report` — the two the ext-point itself already recorded — and no others
  (`keep_markers` is consumed by check 4).
- **"The scope token and file-count token already exist"** (D3 premise refutation). Searched scope:
  `self_review.py` and `pre-submission-self-review.md` (2 files). Result: `surface_scope` +
  `files_in_scope` present in both (self_review.py:330-331; workflow doc line 122), plus the SKILL.md
  and ext-point schema — the plan's asserted absence is refuted.
- **"No `fifteen` check-count reference remains outside the three reconciled docs."** Searched scope:
  `architecture`-equivalent content sweep via `Grep` for `fifteen` across `marketplace/bundles`
  (crawled tree). Result: after reconciliation, the only remaining `fifteen` matches are two unrelated
  literals — the number-word regex in `_self_review_patterns.py:167` and a number-word map in
  `_analyze_literal_count.py:195` — neither a check-count. Coverage note: this `Grep` sweep covers the
  `marketplace/bundles` tree only; `doc/`, `.claude/`, and `.github/` were not swept, so the claim is
  scoped to `marketplace/bundles`.

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
