# PLAN-CIS-044: The One Blocking Gate Arms On A Call That Must Happen, Not A State That Must Hold

epic: code-intelligence-substrate
workstream: WS-05

> Staged 2026-08-09 from the PLAN-CIS-031 drain (inbox `-006`), **re-grounded first-party at
> HEAD** before staging per § Structural Findings F0. Self-sufficient spec.

## Objective

PR #1126 merged with **19 Q-Gate findings still at `resolution: pending`** — every finding its
six `pre-submission-self-review` rounds filed. The gate that exists to prevent exactly that
never evaluated them.

Read at HEAD from `plan-marshall/scripts/_invariants.py`:

- `_ACTIONABLE_FINDING_TYPES` (`:1045`) **includes `qgate`**, aggregated at `--resolution pending`.
- `_BLOCKING_BOUNDARIES` (`:1030`) is **exactly `frozenset({'6-finalize'})`**.
- The raise (`:1248`) fires only `if total > 0 and phase in _BLOCKING_BOUNDARIES` — i.e. only
  when a `capture` call arrives **carrying `phase='6-finalize'`**.
- #1126's `handshakes.toon` carries rows for `1-init` … `5-execute` and **none for `6-finalize`**.

⇒ ⛔⛔ **No `capture --phase 6-finalize` was persisted, so the one boundary where a pending
`qgate` finding blocks was never reached.** The class docstring claims the intra-finalize
boundaries are *"guarded by the `phase-6-finalize` orchestrator re-issuing `phase_handshake
capture --phase 6-finalize`"*; that run's handshake store does not corroborate it.

**The defect is the arming condition, not the predicate.** The predicate is correct. The gate is
armed by *a call that must happen*, and **a missing call is indistinguishable from a passing
gate**: both leave no row and raise nothing.

## ⭐ Why this is worth a plan even though nothing shipped broken

**No real defect reached main** — the 19 findings were genuinely fixed; only their records stayed
`pending`. ⭐ **That is precisely what makes it worth filing: the gate's inertness was invisible
because the outcome was fine.** On a run where the fixes had NOT landed, the same silence would
have shipped them, and the same green report would have been produced.

⇒ `pending_findings_blocking_count` is **not a trustworthy merge signal on this path**, and
anything reading it as one — including a retrospective audit counting *"plans that merged
clean"* — is reading a number nobody computed. This is the epic's confident-signal-hides-a-caveat
theme in its purest form: **a gate that never ran, presenting as a gate that passed.**

## Deliverables

1. **D1 — GATE: establish the population, mutates nothing.** Across the archived-plan corpus,
   how many plans carry **no `6-finalize` handshake row**, and how many of those merged with
   pending actionable findings? ⛔ **Derive the population — do not sample.** ⚠ If the missing
   row is universal rather than incidental, the remedy is a workflow defect and not a guard
   defect, and D2 changes shape. **This gate decides which.**
2. **D2 — the absence of a `6-finalize` handshake row is itself a blocking condition at the
   merge boundary.** *"The gate never ran"* must not be able to present as *"the gate passed"*.
   ⛔ **Convert the arming condition from a call to a state**: the merge boundary asserts the row
   exists, rather than the row's writer asserting the findings are clean.
   ⚠ **This must not become a vacuous guard** — the epic's most-recorded archetype, *"repeatedly
   introduced BY A FIX for them"* (n≥6). **Ship a negative-control fixture**: a plan with no
   `6-finalize` row and pending actionable findings MUST be refused, and the fixture must fail
   against the pre-fix code.
3. **D3 — the self-review loop-back path resolves the Q-Gate findings whose fixes it lands.**
   The store accumulated 19 permanent `pending` rows on a green plan. ⭐ **Both D2 and D3 are
   needed and neither substitutes for the other**: D2 closes the gate, D3 stops the gate from
   having to be closed against a store that is wrong anyway. ⚠ **Do not let D3 auto-resolve a
   finding whose fix cannot be evidenced** — a finding marked `fixed` without a landed change is
   strictly worse than one left `pending`.

Three deliverables, D1 a gate — well below the split guard.

## Claim Labels

- **OBSERVED (first-party at HEAD, 2026-08-09)**: `_invariants.py:1030` defines
  `_BLOCKING_BOUNDARIES` as `frozenset({'6-finalize'})`; `:1248` guards the raise on
  `phase in _BLOCKING_BOUNDARIES`; `:1045` includes `qgate` in `_ACTIONABLE_FINDING_TYPES`.
- **OBSERVED (#1126's own artifacts)**: 19 `qgate` findings at `resolution: pending` at merge;
  `handshakes.toon` carries `1-init`…`5-execute` and no `6-finalize` row.
- **HYPOTHESIS**: that the missing `6-finalize` row is not unique to #1126. **D1 is this
  verification.** ⚠ **Actively suspected TRUE and that changes the remedy** — if every
  orchestrated finalize omits it, the gate has been inert fleet-wide and D2 is a correctness fix
  rather than a hardening.
- **HYPOTHESIS**: that `_cmd_lifecycle.py`'s use of `_BLOCKING_BOUNDARIES` (3 matches) is a
  second consumer with the same arming assumption. **Read it at outline** — a fix to one
  consumer that leaves the other is this epic's second-site archetype (`PLAN-CIS-019`'s
  `_BOOKKEEPING_PREFIXES` correction is the standing instance).

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the second consumer
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` and `workflow/execution.md` — the contract docs
- **HYPOTHESIS**: `phase-6-finalize` — where the missing `capture` should originate, and the
  merge-boundary assertion's home (verify-at-outline)
- **HYPOTHESIS**: `phase-6-finalize/workflow/pre-submission-self-review.md` — D3's resolution
  path (verify-at-outline)
- **OBSERVED**: `test/plan-marshall/manage-status/test_manage_status_transition.py` — existing coverage

## Dependencies and Sequencing

- **Depends on**: nothing.
- ⛔ **Never pair with `PLAN-CIS-010` or `PLAN-CIS-011`** — shared `phase-6-finalize` surface.
- ⛔ **Never pair with `PLAN-CIS-043`** — D3 touches `pre-submission-self-review.md`, which is
  CIS-043's D2/D3 surface.
- ⚠ **`PLAN-CIS-018`** (phase-handshake capture / `main_sha`) touches the same handshake record.
  **Coordinate; re-check at emit.**

## Anti-goals

- ⛔ **Do not weaken the predicate.** It is correct; the arming is not.
- ⛔ **Do not ship a guard without a negative control.** The vacuous-guard archetype has been
  introduced by a fix for itself at least six times in this project.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-044-blocking-boundary-arms-on-a-call-not-a-state.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
