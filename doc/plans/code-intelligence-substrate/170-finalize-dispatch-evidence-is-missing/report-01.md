# Run report — 170-finalize-dispatch-evidence-is-missing (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/finalize-dispatch-evidence-hgcl9s` (harness-assigned; kept as-is)    **PR:** [#1225](https://github.com/cuioss/plan-marshall/pull/1225)    **Outcome:** completed (conditions 1–3 met, 1-of-3 review shortfall disclosed, auto-merge armed; landing delegated to the merge queue)

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

### Verification sub-agent (Step 6)

An independent read-only sub-agent verified the diff against `plan.md`. **Verdict: all five
deliverables MET; no undeclared collateral change; the out-of-scope boundary respected
(`_cmd_effort.py` and the dispatch-line seam untouched — confirmed absent from `git diff
--name-only`).** It ran the full `test/plan-marshall/plan-retrospective/` suite (675 pass, 0 fail).

Findings, each with disposition:

- **Stale internal cross-reference — FIXED (`d38ce99`).** `execution-context-dispatch-audit.md`'s
  cross-reference footer still called the aspect an "LLM-driven retrospective aspect", contradicting
  the file's own rewritten opening. Genuinely stale (introduced by this change's rewrite). Reworded.
- **Three imprecise "LLM aspects" labels in sibling docs — FIXED (`d38ce99`).**
  `plan-marshall/standards/effort-roles.md`, `ref-workflow-architecture/standards/call-graph.md`
  (two sites) called the retrospective set "8 LLM aspects"; after this change one of the eight is a
  deterministic script, so the label is imprecise. Relabelled to "analytical aspects" (count
  unchanged). The sub-agent classed these as outside the plan's declared surface, but they are the
  misleading-signal defect the lane's beyond-diff sweep exists to catch, so they were fixed.
- **D2 mechanism deviation — ACCEPTED, not a gap.** The sub-agent confirmed the token-record
  mechanism (vs the plan's literal "roster qualifier") satisfies D2's "Done when" and is
  outcome-equivalent, honoring the programme's anti-"hand-maintained mirror" principle. Disclosed in
  Deliverables/D2.
- **D1 premise shift — ACCEPTED, disclosed.** The sub-agent independently confirmed the plan's
  "nothing writes Surface B" premise is false at HEAD (sibling PR #1200 wired the seam) and that the
  detector is correct regardless. Disclosed in Deliverables/D1.

No finding was rejected. All actionable findings fixed; the quality gate re-ran clean after the fixes.

### CI

`verify / gate`, `dependency-review`, `review / review`, `generate-check` concluded **success** on
the head SHA `9b4be92`; `verify / verify` (the heavy build carrying the required `verify /
conclusion`) was still **in_progress** at the merge gate. No self-wake is available in this session,
so — per the lane — auto-merge was armed while `verify` runs; the merge queue is the enforcer and
admits the PR only when the ruleset's required contexts pass. No CI failure observed.

### PR review

No actionable review comment. All three comment surfaces (`get_comments`, `get_reviews`,
`get_review_comments`) were read before the merge gate; inline review threads: none. `cuioss-review-bot`
posted a clean review (tests present, no security concerns, no major issues) — nothing to fix or reply
to. `coderabbitai` and `sourcery-ai` posted only rate-limit notices. Disposition: nothing actionable;
the shortfall is disclosed (Reviewer participation, below).

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:
**M = 3** — `coderabbitai` (coderabbit.md:27), `cuioss-review-bot` (pr-agent.md:55), `sourcery-ai`
(sourcery.md:25). Verdicts derived from the stored comment bodies (not check states):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a review summary over the diff — "PR Reviewer Guide: 🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected" (issue-comment 5286488438). Clean; no findings to handle. |
| `coderabbitai` | `rate-limited` | Published only a quota notice, no review: "Review limit reached … Next review available in: 107 minutes" (issue-comment 5286479074). |
| `sourcery-ai` | `rate-limited` | Published only a quota notice, no review: "you have reached your weekly rate limit of 500000 diff characters" (review 4931660348). Its `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** **Step-8 shortfall disclosure (fired — disclosure, not a block):** *Review
coverage: 1 of 3 — `cuioss-review-bot` reviewed (tests present, no security concerns, no major issues);
`coderabbitai` rate-limited (next window ~107 min); `sourcery-ai` rate-limited (weekly diff-character
quota).* Rate limits are routine and outside our control; per the lane this changes only what the run
says, not whether it merges. Auto-merge armed exactly as full coverage would be.

## Cost

- **Tokens:** not available to the agent as a reliable figure in this session.
- **Wall-clock:** single interactive Claude Code cloud session (see PR #1225 timestamps for the finalize
  window).
- **Population:** this one cloud session's usage as the harness counts it. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total (which counts the orchestrator-plus-agent dispatch tree under a
  per-task billing boundary this single interactive session does not share). No comparable number is
  presented.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; each step checked against what happened and its on-disk artifact:

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — `cloud-plan-lane`, `ref-code-quality`, `plugin-script-architecture`, `python-core`, `pytest-testing`, loaded by bundle path (plugin absent, as the lane anticipates). |
| 2 Branch on `origin` | **done** — harness-assigned `claude/finalize-dispatch-evidence-hgcl9s`, pushed before any work; kept as-is. |
| 3 Plan directory | **done** — `…/170-…/plan.md` exists and opens with the first-instruction block (present on receipt; no repair needed). |
| 4 Implement | **done** — commits `251c96d`,`c52b795`,`77611b2`,`d38ce99`,`9b4be92` + this final report commit; each carries the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | **done** — every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`total_issues: 0` across ruff/mypy/SPDX/plugin-doctor). |
| 4 Pushed | **done** — this final report commit is the last; no unpushed commit remains. |
| 5 Build gate | **done** — Python changed → `./pw verify` SUCCESS (19621 passed, 0 failed). Later doc-only commits took the no-build path, validated by `./pw quality-gate`. |
| 6 Verification sub-agent | **done** — dispatched read-only; all five deliverables MET; four stale-claim findings fixed (`d38ce99`), D2/D1 disclosures accepted. Findings + dispositions above. |
| 7 PR cycle | **done** — PR #1225 (no `skip-bot-review`: the diff is code — `*.py` + skills/bundles). Every comment dispositioned; all three comment surfaces read. |
| 8 Merge gate | conditions 1–3 met (required `verify` deferred to the queue via auto-merge; no open comments; report finalized as the last pre-merge commit), 1-of-3 shortfall disclosed, auto-merge armed (SQUASH). Landing delegated to the merge queue (no self-wake in this session — arm-and-hand-off is a completed outcome per the lane). |
| 8 Bridge | **done** — no status/bookkeeping write under `doc/plans/` outside this plan's own directory; no shared lane doc touched. The report carries the PR number and per-deliverable outcome for the orchestrator's collect. |
| 9 This check | **done** — recorded here. |
| 9 What have we learned | **done** — below. |

GitHub access path used: **GitHub MCP server**. Branch form: **harness-assigned**. No `/sync-plugin-cache`
is owed (machine-local build step, not a debt a cloud run records).

## What have we learned (Step 9)

**No `cloud-plan-lane` contract change proposed.** The contract executed cleanly end to end: skill-by-path
loading, the harness-assigned branch pushed before any work, the conditional build gate (Python → full
`verify`; docs-only → quality-gate), the pre-PR verification sub-agent (whose beyond-diff stale-claim
sweep earned its keep — it caught four real stale docs the diff-scoped checks missed), the three-surface
comment read, and the disclose-not-block shortfall rule all behaved as written. No step was ambiguous in
practice and no step's artifact failed to produce as written. The one environmental friction —
`UV_HTTP_TIMEOUT` needed raising and `python3 -m pytest` is not on the bare PATH (use `uv run pytest`) —
is already documented in the lane. A speculative edit is not a proposal, so none is made.

**Observation for the operator (plan-authoring, not a lane-contract change).** Plan 170's central premise
— "the shape-violation check's second surface has *no producer at all*" — was **false at HEAD**: the
sibling `truthful-signals/280` (PR #1200) landed first and wired Surface-B emission into the resolve
seam. The plan anticipated exactly this risk (it labelled the audit-file location a HYPOTHESIS and told
the run to *settle the prior question in the clone*), so the run settled it from source and reported the
shift rather than papering over it. Two consequences worth the operator's eye: (a) the "detector" the
plan assumed existed was **LLM-only prose**, so the plan's deliverables (a fail-able, testable detector)
required **building one from scratch** — larger than "fix the detector"; and (b) the plan's D2 named a
*roster qualifier* mechanism, but the token-record mechanism the run used is what the plan's own claim
table cites as ground truth and better honors the programme's anti-"hand-maintained mirror" rule. Both
are recorded as disclosed, justified decisions; neither is a lane-contract gap.

## Residue

- **Finalize resolves still don't pass `--workflow`.** Surface B stays empty for every finalize dispatch,
  so finalize's `shape_violation` reports `not_evaluated` (honestly). Migrating those resolves to the
  seam is the **sibling emission plan's** job (out of this plan's scope); when it lands, D1's
  `shape_violation` becomes evaluable and D3's channel-completeness will *show* the emission fix working
  (its stated purpose).
- **Per-task ARTIFACT emission cannot be made deterministically complete** — it is LLM-hand-emitted and
  empty-diff-suppressed by design, so D4 took the population-statement route (the plan's second option).
  A future emitter that drives `[ARTIFACT]` from the shared task-close path (analogous to the dispatch
  seam) would let the population reach N == M reliably; not owned here.
- **Three sibling docs** (`effort-roles.md`, `call-graph.md` ×2) carried "LLM aspects" labels the
  relabel made imprecise; fixed in this run (`d38ce99`). No further known stale sites.
