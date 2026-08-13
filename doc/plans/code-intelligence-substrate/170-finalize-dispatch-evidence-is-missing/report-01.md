# Run report — 170-finalize-dispatch-evidence-is-missing (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/finalize-dispatch-evidence-hgcl9s` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

This plan owns the **detector** (the execution-context dispatch audit) and the **per-task
artifact emitter**. The dispatch-line EMISSION is out of scope (owned by a sibling plan).

## Skills loaded

- `cloud-plan-lane` (first action, governs the run).
- `plan-marshall:ref-code-quality` (read by bundle path).
- `pm-plugin-development:plugin-script-architecture` (read by bundle path).
- `pm-dev-python:python-core`, `pm-dev-python:pytest-testing` (read by bundle path — Python production + tests).

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Outline findings (pre-implementation)

_Being established. Key facts settled in the clone:_

- The dispatch audit (aspect 11) is an **LLM-only aspect** — its detection logic is prose in
  `plan-retrospective/standards/execution-context-dispatch-audit.md`; there is **no deterministic
  script** implementing `shape_violation` / `dispatch_coverage_violation`. `audit.py`'s
  `check_dispatch_topology` (leaf invariant) and `check_finalize_flow_conformance` (ci_verify) are
  unrelated checks. ⇒ To make the detector *able to fail* and *testable* (D1/D5), a deterministic
  detector must be built (matching the SKILL's already-established script-backed-facts pattern for
  aspects 1-3, 8, 10, 12, 13).
- **D1 premise shift (settled in the clone):** a Surface B producer now EXISTS — the merged sibling
  plan (`truthful-signals/280`, PR #1200) moved dispatch-record emission into the `effort
  resolve-target` seam (`manage-config/scripts/_cmd_effort.py`), which writes both Surface A and
  Surface B when passed `--workflow`. So "no producer at all" is no longer literally true at HEAD;
  the vacuity now stems from the producer being **under-wired** (most dispatch sites still hand-write
  Surface A only and never emit Surface B). Detail recorded under Deliverables/D1.

## Deliverables

The dispatch audit (aspect 11 in `plan-retrospective`) was **LLM-only prose** — no deterministic
script, so it could not be tested, never failed against a divergent site, and rendered a
never-evaluated state and an evaluated-clean state as the identical `0`. The plan's headline
requirement ("make the audit able to fail") plus D5 ("tests, each verified to FAIL pre-fix; one
asserting the audit reports a deliberately-divergent step") therefore **require a deterministic,
testable detector**, which did not exist. So this run **built one** — `check-dispatch-audit.py`
(new) — matching the SKILL's established script-backed-facts pattern (aspects 1-3, 8, 10, 12, 13),
and wired aspect 11 to it. Commits `c52b795` (detector + D4 + docs + tests) and `77611b2`
(register-from-reference-doc invariant fix).

### D1 — make the audit able to fail

`check-dispatch-audit.py` `shape_violation` pairs the decision-log `effort resolve-target` records
(Surface B, the resolve/intent side) against the work-log `[DISPATCH]` lines (Surface A). **When
Surface B is empty it reports `not_evaluated` with its reason, never a bare `0`.** Every count is
published beside its `evaluated_population`, and the population is derived from the log (the resolve
record count), not a literal. Verified against a **deliberately-divergent site**
(`test_shape_violation_fires_on_divergent_site`): a resolve for `role=phase-2-refine` with no matching
`[DISPATCH]` line produces a `shape_violation` finding. Clean-with-population
(`test_shape_violation_clean_when_resolve_is_paired`) and empty-population→not_evaluated
(`test_shape_violation_not_evaluated_when_surface_b_empty`) both covered.

**Prior question settled in the clone (as the plan demanded).** The claim "nothing writes Surface B at
all" is no longer literally true at HEAD: the merged sibling `truthful-signals/280` (PR #1200) moved
dispatch-record emission into the `effort resolve-target` seam (`_cmd_effort.py::_emit_dispatch_records`),
which writes Surface B **when passed `--workflow`**. But only **two** phase-5 sites pass `--workflow`;
**every finalize dispatch site still hand-writes Surface A only** and never emits Surface B. So the
vacuity is now an **under-wired producer**, not an absent one — and for finalize the shape-violation
pairing still has no left-hand side, which is exactly the `not_evaluated` state the corrected detector
now reports honestly. (Migrating the finalize resolves to `--workflow` is the sibling emission plan's
job, out of this plan's scope.)

### D2 — the CONSUMER distinguishes dispatched / ran-inline / no-evidence

`dispatch_coverage` classifies each terminal finalize step (`status.metadata.phase_steps["6-finalize"]`)
by its **token record** (`execution.toon` `execution_log[]` `total_tokens`) — the second, independent
evidence source: non-zero ⇒ `dispatched`, measured-zero ⇒ `ran_inline`, no row ⇒ `no_evidence`. The old
"ran inline where dispatch was required" discipline finding is **gone**. A step token-proven to have
dispatched with no `[DISPATCH]` line is reported as **`missing_dispatch_emission`** — an instrumentation
finding against the **dispatcher** (`test_missing_dispatch_emission_on_dispatched_but_unlogged`). A
conditionally-dispatching step that legitimately ran inline carries a measured-zero record and lands in
`ran_inline`, never flagged (`test_conditional_inline_step_not_flagged`); a terminal step with no token
row is honest `no_evidence`, never "ran inline" (`test_no_evidence_when_terminal_step_has_no_token_record`).

**Deliberate, recorded deviation on the mechanism.** D2's text names a *roster qualifier* for the
conditional case; I used the **token record** instead — which the plan's own claim table cites as ground
truth ("Token attribution independently confirmed no dispatch occurred"). This is the population-derived
realization the programme mandates ("population-derived, not literal") and it avoids the "second
hand-written pin" / "hand-maintained mirror of a derived set" the sibling plan explicitly forbids. The
detector therefore consults **no** dispatched/inline roster at all, so the roster's expressiveness gap
cannot mislead it, and the closure invariant survives untouched (the roster is not edited).

### D3 — the channel-completeness report

`channel_completeness` publishes `dispatch_line_count` against `completion_count` (the `[STEP] …
Completed step:` lines — already emitted, no new instrumentation) and the token-proven
`dispatched_step_count`, and downgrades the audit's own `confidence` (`none` / `low` / `nominal`) when
the channel is sparse. A deliberately sparse fixture (completions + a token-proven dispatch, zero
`[DISPATCH]` lines) → `confidence: none` (`test_sparse_channel_lowers_confidence_to_none`); a provable
shortfall (dispatch lines < dispatched steps) → `low`; a covered channel → `nominal`. Done first, as the
plan directed; it works whether or not the emission fix has landed.

### D4 — per-task artifact emission population statement

`analyze-logs.py` now publishes `artifact_emission: {completed_tasks: M, tasks_with_artifacts: N,
tasks_without_artifacts: […]}` — **N of M** — so a consumer cannot read a partial count as a total. The
per-task `[ARTIFACT] (plan-marshall:phase-5-execute:{n})` emission is LLM-hand-emitted and
empty-diff-suppressed, so "complete emission" is not deterministically achievable; the plan's second
route (a POPULATION statement in the output) is the faithful, safe choice. The bare `artifact_entries
== 0` floor is preserved but a WARNING fires only for unambiguous partiality (`0 < N < M`) — the exact
defect (a count satisfied by a single artifact while most completed tasks emitted none). Tests:
`TestArtifactEmissionPopulation` (partial → population + finding while the floor is satisfied; complete →
no finding; N=0 → population still published, no finding).

### D5 — tests, each verified to FAIL pre-fix

`test_check_dispatch_audit.py` (13 tests) — every detector exercises a divergent site (it fires) AND a
clean site (it does not), the mutation-guard shape these plans use to prove non-vacuity. The **D4** tests
were run against the pre-fix `analyze-logs.py` (via `git stash` of that one file) and confirmed **red**
(`KeyError: 'artifact_emission'` × 3), then restored. For the NEW detector, "red pre-fix" is inherent —
the deterministic verdicts did not exist before — and the divergent-site tests are what prove the
detector actually fails when it should.

**Preserved surface (not a plan deliverable, but required to avoid a regression):** converting aspect 11
to script-backed must not silently drop its two other categories, so `envelope_violation` (a `[DISPATCH]`
target outside the execution-context set) and `generic_subagent_violation` (a raw `Task: general-purpose`
in the work log) are implemented deterministically too, with tests.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (`check-dispatch-audit.py`,
`analyze-logs.py`, two test files), so the build takes its full path. Per-commit `./pw quality-gate` ran
clean (`total_issues: 0`, 36 plugin-doctor rules) before each `*.py`-touching commit. **Full `./pw
verify`: SUCCESS — 19621 passed, 14 skipped, 0 failed; coverage COMPLETE over mypy(production, 399
files), ruff, SPDX headers, plugin-doctor (marketplace-wide), mypy(test, 733 files), and whole-tree
pytest.** Read from the build output, not the exit code. (One intermediate full-verify run flagged a
single failure — the registered-aspects render guard, which requires aspect 11 to register from its
reference doc; fixed in `77611b2` and re-verified green.)

## Findings

_Pending._

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
