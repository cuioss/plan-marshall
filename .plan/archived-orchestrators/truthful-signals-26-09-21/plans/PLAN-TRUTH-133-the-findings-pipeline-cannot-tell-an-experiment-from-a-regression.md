# PLAN-TRUTH-133: The findings pipeline cannot tell an experiment from a regression

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from inbox drain messages `deployment-and-refresh-gaps-013.md` and `-019.md`,
> both relayed from the **Token-Sheriff** repo (epic `deployment-and-refresh-gaps`, plans
> `refresh-path-gate-and-invariant-gaps` PR #687 and `outbound-hostname-verification-quarkus`
> PR #694) after `manage-lessons add` refused them there with `wrong_store`.

## Objective

**Findings capture is keyed on the OBSERVABLE — a non-zero build exit, parsed error/failure lines —
with no channel for the INTENT of the invocation, and the blocking count it produces is disclosed
exactly once, at the merge barrier, hours after the context that would let anyone dispose of it.**

Two members, observed in two different plans, and they compound: the first fills the store with
findings that are evidence of correctness, and the second guarantees nobody sees them until the gate.

### Member 1 — a deliberate negative control's red build is captured as blocking findings

To prove the JaCoCo coverage gate actually binds, a run deliberately misspelled an `include` pattern —
a textbook negative control: break the input, confirm the guard goes red, restore. **The gate did go
red, which is the result that proves the guard works.**

The findings pipeline captured that red build as **9 `build-error` findings and 7 `test-failure`
findings**. Both are blocking types. Had they not been noticed and resolved by hand, they would have
held the finalize boundary open against the `pending_findings_blocking_count` invariant.

⛔ **The evidence that a guard WORKS was recorded, verbatim, as evidence that the code is broken. The
polarity was inverted at the capture layer.** A negative control and a genuine regression are
byte-identical at that layer — they differ only in whether the operator expected red — and because
nothing carries that expectation, capture defaults every red to *regression*: the safe default for an
unannotated build and the wrong one here.

⭐⭐ **The standing tension this creates is the actionable part.** Matched positive/negative controls are
**prescribed** by `persona-module-tester` as the way to prove a fixture-level guard binds. That
prescription and the findings pipeline are in direct tension: **following the testing standard damages
the finalize gate.** The only remedies available today are *"do not run negative controls"* or
*"clean up by hand afterwards"*, and both are bad.

### Member 2 — the count first surfaces as an opaque merge-barrier refusal

The maven build wrapper auto-files a finding per failed build. Over one run's build failures and
deliberate control experiments (a clean-`main` timing control, a two-step test-jar workaround
discovery), **19 actionable findings accumulated — 13 `build-error`, 6 `test-failure`**. (For scale,
that plan's findings store held **46** `build-error` records total, 36 after filtering — most
auto-resolved by a later green build.)

**Nothing in the pipeline surfaced them between phase-5 and the pre-merge barrier.** The operator's
first contact was the barrier refusing with a blocking count: an opaque number, at merge time, over
findings filed hours earlier for causes by then already resolved or deliberately induced.

⛔ **A finding filed at build-failure time is actionable THEN, while the operator holds the context.**
Deferring all of them to one aggregate count at the gate strips that context and converts N specific,
individually-cheap dispositions into one expensive, undifferentiated blocker.

## Deliverables

1. **D0 — GATE: derive the population and settle whether the two members share a remedy.** Measure,
   over recent plans, how many auto-filed `build-error` / `test-failure` findings reach the barrier
   still pending, and how many of those were auto-resolved by a later green build. ⛔ **Publish the
   swept population, its size, and the plans it spans.** ⚠ **Do NOT assume one fix serves both** — an
   intent channel (member 1) and a disclosure cadence (member 2) are different remedies, and this
   epic's own record shows the shape-grouping inference failing before. D0 may split this plan.
2. **D1 — the build invocation can declare an expected-red intent, and capture honours it.** A build
   marked as a control/experiment routes its parsed errors and failures to a non-blocking record class
   (`insight` / `tip`) — or suppresses capture — instead of `build-error` / `test-failure`. ⛔ **The
   record must still EXIST**: an experiment's red is real evidence and suppressing it entirely would
   substitute one blind spot for another. It must simply not count against the barrier.
   ⭐ The sending message ranks this above the documented-cleanup alternative for a stated reason:
   **cleanup depends on the operator remembering, which is the class of guarantee this lesson exists
   to remove.** Record the rejected arm.
3. **D2 — surface the pending actionable-findings count at each phase boundary** (end of phase-5, and
   at each finalize step that already reports), so the number never arrives cold.
4. **D3 — the barrier's refusal enumerates findings by cause and age**, not a bare count. ⛔ A blocking
   count with no denominator and no membership is the epic's own *underived-completeness* archetype
   sitting on the merge path.
5. **D4 — matched controls, and they are the point of the plan.** A genuine regression must still file
   blocking findings and still hold the barrier; a declared control must not. ⛔ **A fix that lets any
   build opt out of blocking findings has built a bypass, not a discriminator** — the control must
   demonstrate that the opt-out cannot be reached by an ordinary failing build.

## Claim Labels

- OBSERVED: a deliberate `include`-pattern negative control produced 9 `build-error` + 7 `test-failure` findings, both blocking types — first-party from the sending run.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _build_shared.py always-on _store_build_findings stores every parsed issue as build-error/test-failure with no intent or control param
- OBSERVED: 19 actionable findings (13 `build-error`, 6 `test-failure`) accumulated across one run and first surfaced at the merge barrier as a blocking count.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The specific 19-finding Token-Sheriff figure is a foreign-repo run, not reproducible from this checkout
- OBSERVED: that plan's findings store held 46 `build-error` records total, 36 after filtering, most auto-resolved by a later green build.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The specific 46/36 figure is a foreign-repo run, not reproducible from this checkout
- OBSERVED: `persona-module-tester` prescribes matched positive/negative controls for proving a fixture-level guard binds — this is a local, corroborable claim.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: persona-module-tester/SKILL.md and standards/testing-methodology.md both name positive and negative control
- HYPOTHESIS: the capture layer has no intent channel at all, as opposed to one no caller uses. Confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py` § the finding-emission path and `manage-findings` § the `add` surface (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: cmd_run_common and _store_build_findings carry no intent/control/expected-red parameter anywhere in the capture path
- HYPOTHESIS: the barrier is the FIRST disclosure of the pending blocking count, i.e. no earlier phase surface reports it. ⛔ NOT checked here (verify-at-outline).
- HYPOTHESIS: the two members share one remedy. ⛔ **This orchestrator's grouping by adjacency, not a claim either message makes.** D0 settles it; splitting is a legitimate outcome (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Whether the two members share one remedy is an unsettled analytical question the spec assigns to D0
- Verify-first clause: before D1, establish whether an auto-resolve-on-next-green path already exists. The 46→36 figure suggests one does; if it does, member 2's remedy is a disclosure change only and D1's scope narrows to the control case.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _reconcile_pending_build_findings in _build_shared.py auto-resolves clearable finding types on a subsequent green build

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/**` — the build wrapper's finding emission (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md`, `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — the record class and the blocking predicate (D1, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier` surfaces — the refusal payload (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — the phase-boundary disclosure (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-findings/**`, `test/plan-marshall/script-shared/**` — the D4 controls (verify-at-outline)

## Dependencies and Sequencing

- ⛔⛔ **Overlaps with `PLAN-TRUTH-124` (STAGED, queue head) on `manage-findings/SKILL.md`,
  `manage-findings/scripts/_findings_core.py` and `test/plan-marshall/manage-findings/`.** `-124` is
  the unified-ledger-vocabulary clean slate and is first in the emit order. **SERIALIZE behind `-124`
  — do not pair.** ⭐ An expected-red record class IS a vocabulary question, so `-124` may legitimately
  absorb part of D1; re-ground this spec against `-124`'s landed model before emitting.
- ⚠ Also overlaps `PLAN-TRUTH-105` (build execution verdicts that mislead on the healthy path) on
  `script-shared/scripts/build/`. Serialize or re-scope at emit.
- Adjacent to: `PLAN-TRUTH-123` (the quality chain has no score) — that plan SCORES what the gates
  caught; this one fixes what the gates FILE. `-123` is itself blocked behind `-124`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-133-the-findings-pipeline-cannot-tell-an-experiment-from-a-regression.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐⭐⭐ FOLDED 2026-09-05 — lessons-handling drain (1 message). THE SPEC'S TITLE, OBSERVED IN THE WILD.

- **`lessons-handling-26-09-04-01-006`** — *a deliberate negative control files real-looking failure
  records that later block the merge gate.* Relayed from Token-Sheriff PLAN-01
  (`pre-commit-gate-truthfulness`, PR #713 / `29d9f6c5`).

  **This is not an adjacent case — it is this spec's exact subject with a measured instance.** TASK-10
  ran a proof-of-discrimination (deleting a `families.remove` call so a new test would fail, proving the
  test discriminates rather than passing vacuously). ⭐ **That is correct practice — a negative control
  is the only evidence a gate is not lying.** The control filed **12 build-error / test-failure
  findings**, and **they SURVIVED the control's revert**. At the pre-merge barrier they were
  indistinguishable from genuine failures and **BLOCKED it.**

  ⛔⛔ **The remedy the sender names is the one this spec must adopt: provenance is stamped WHEN THE
  RECORD IS CREATED, never recovered at triage time.** Once the control is reverted, the only
  distinguishing signal left is a timestamp — and *a timestamp is correlation, not attribution*. Two
  concrete shapes: a flag on the emitting call, or a scoped **control window** opened and closed around
  the deliberate breakage. Either lets triage partition by reading a FIELD, and lets the barrier exclude
  control records **without an operator override that would also waive genuine failures** — which is the
  part that makes the cheap workaround unacceptable.

  ⭐⭐ **The irony is load-bearing and belongs in the shipped doc**: the originating plan existed to prove
  one gate honest, and the mechanism it used to prove it made a *different* gate dishonest about what had
  actually failed. ⇒ **An experiment is a first-class record class, not noise to be filtered later.**

  ⚠ **Interim workflow rule, valid until this ships**: a task running a negative control must record, in
  the same step, which findings the control produced.

  ⚠ **Expected Surface widened in this same act**: `marketplace/bundles/plan-marshall/skills/manage-findings/**`
  — the emitting call's provenance field and the control-window verbs — and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — the pre-merge barrier's exclusion
  predicate (HYPOTHESIS, verify-at-outline).

## ⛔⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (1 claim contradicted, and D2 MAY ALREADY BE HALF-SHIPPED)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 5 | the pre-merge barrier is where a blocking findings count is FIRST computed | **REFUTED** — `phase-handshake.md:226` already records `pending_findings_blocking_count` **at every phase boundary**. The barrier is the first place that count BLOCKS, not the first place it is COMPUTED. |

⭐⭐⭐ **This materially re-scopes D2 and the epic should not discover it at outline.** The count this
spec proposed to introduce **already exists and is already captured at every boundary.** ⇒ **What
remains open is narrower than D2 as written: (a) surfacing it to the operator, and (b) blocking
earlier.** ⛔ **Do NOT build a second counter.** A second blocking-count producer beside an existing one
is the two-vocabularies defect `PLAN-TRUTH-124` exists to end, committed while fixing a different
truthfulness gap.

⭐ **The spec's core thesis is untouched and strengthened by what DID corroborate**: `_store_build_findings`
is always-on and stores every parsed issue as `build-error` / `test-failure` **with no intent or control
parameter anywhere in the capture path** (claims 0 and 4), and `_reconcile_pending_build_findings`
auto-resolves clearable types on a later green build (claim 7). ⇒ **The provenance gap is real and is at
the CAPTURE site, exactly where the spec places it.**

⚠ **Claims 1-2 are `unverifiable` foreign-repo figures.** The Token-Sheriff instance counts are theirs;
what this epic establishes first-party is the missing capture-time parameter, **not the incidence rate.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-146-the-findings-ledger-one-vocabulary-and-an-experiment-told-from-a-regression.md` (PLAN-TRUTH-146)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
