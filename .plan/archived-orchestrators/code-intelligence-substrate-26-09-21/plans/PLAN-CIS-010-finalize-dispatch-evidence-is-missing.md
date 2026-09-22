# PLAN-CIS-010: Finalize dispatch leaves no evidence, and the audit that would catch it is vacuous

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec. Split out of PLAN-CIS-011, which had absorbed ten items across two seams.
> This plan owns the **EVIDENCE** seam; PLAN-CIS-011 keeps the **STEP-CONTRACT** seam.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and hand-off
> contract.

## ⛔⛔ RECONCILED 2026-08-09 — OWNERSHIP SPLIT CORRECTED AND STALE GATES STRUCK. READ FIRST.

**This spec contradicted itself about who owns the `[DISPATCH]` emission fix.** Its § Deliverables
boundary note says *"PLAN-CIS-011 owns `[DISPATCH]` / `[STEP]` emission for finalize STEPS; this owns
`[ARTIFACT]` emission for TASKS"* — while its Third Evidence Fold **adopts "emit `[DISPATCH]` from
the single dispatch seam" into "this spec's scope"**. Both cannot be true, and shipping both plans
against it would have produced **two writers for one emitter**, which is the F0b archetype.

✅ **SETTLED: `PLAN-CIS-011` owns the `[DISPATCH]` EMISSION fix.** It now carries the defect from
**two independent first-party sightings** (#1126 at 6:1 on one step, #1127 at 4-of-13 / 31%) as its
D11. ⛔ **This plan MUST NOT ship an emission change.**

⭐ **What stays here is the half CIS-011 cannot do, and it is the more valuable half**: the
**detector** cannot be trusted regardless of how good the emission gets, and the channel-completeness
idea below generalises past this aspect. Concretely, this plan keeps:

- **D1** — the vacuous `shape_violation` detector (Surface B has no producer at all).
- **D3** — `[ARTIFACT]` emission for phase-5 **tasks** (a different emitter, unambiguously this plan's).
- ⭐ **The channel-completeness report** (`dispatch_lines / envelope_completions` **downgrades the
  audit's own confidence**) — ⭐⭐ **the single most reusable idea in this spec**, and it is a
  *consumer-side* change that works whether or not CIS-011 has landed. **Do it first; it is cheap,
  it needs no new instrumentation** (`[STATUS] … Complete` is already emitted), **and it makes
  CIS-011's fix measurable when it arrives.**
- **D2 is RE-SCOPED** from *"make dispatch evidence unambiguous"* (an emission change) to
  *"make the CONSUMER distinguish the three states"* — dispatched / ran-inline / no evidence —
  including the `missing_dispatch_emission` vs `dispatch_coverage_violation` distinction this spec
  already derives, which is a **detector** change and stays here.

## ⛔ Sequencing — CORRECTED 2026-08-09

Both edit `phase-6-finalize` and are the same serialization class: **sequence, never pair.**
**Run this plan FIRST** — while the audit is vacuous, any measurement of CIS-011's divergence reads
clean, so CIS-011 cannot verify its own fix until this lands. ⭐ **That ordering is now doubly
motivated**: this plan's completeness ratio is the instrument that will *show* CIS-011's emission fix
working.

⛔ **STRUCK 2026-08-09 — every blocker below referenced the RETIRED `plan-optimization` epic and all
of them shipped long ago.** ~~Blocked while PLAN-92 is in flight (its D8 put `phase-6-finalize` in an
in-flight surface)~~; ~~overlaps with PLAN-100, PLAN-52, PLAN-60~~. **None of these plans exists in
this epic's queue and none is in flight.** ⚠ **The same stale-reference class is present throughout
the older half of this queue** — see `epic.md` § Queue Reconciliation 2026-08-09, finding R1. **Do
not re-derive a blocker from a `PLAN-NN` id with no `CIS` segment; those are all historical.**

## Objective

A finalize step can reach a terminal outcome with **no record that it dispatched**, and the audit
built to detect exactly that **cannot fire**. Make dispatch evidence real, then make the audit able
to report its absence.

## The defects

All observed on PRs #1037–#1039; each is message-supplied and **HYPOTHESIS until re-verified at
outline**.

**1. The dispatch audit's `shape_violation` check is VACUOUS — its intent surface never fires.**
⛔ **Fix this first.** While it is vacuous, every measurement of dispatch divergence reads clean, and
any count of divergent sites is **unmeasured, not low**. Nothing downstream can be trusted until the
detector can fail.

**2. Dispatched finalize steps reach terminal outcomes with NO `[DISPATCH]` log evidence.** A
dispatched step, an inline fallback, and a step that never ran are **indistinguishable after the
fact**. Confirmed live on #1039, where `automatic-review` and the unified triage ran inline against a
roster requiring dispatch and left no row either way.

**3. Per-task `[ARTIFACT]` log emission is missing for most completed tasks.** Emission exists but
fires for a minority, so any consumer counting artifacts under-reports **by construction** — and
reads the result as "few artifacts produced" rather than "emission is broken".

## Deliverables

1. **D1 — make the audit able to fail.** Establish why `shape_violation`'s intent surface never fires
   and fix it. ⚠ **Verify the corrected detector FAILS against a known-divergent site** before
   trusting any clean run — a detector that has never failed is not evidence.
2. **D2 — dispatch evidence becomes unambiguous.** A terminal step records whether it dispatched,
   ran inline, or did neither. **Absence of evidence must be distinguishable from evidence of
   inline execution.**
3. **D3 — `[ARTIFACT]` emission fires for every completed task**, or its scope limit is declared in
   the output so consumers cannot read a partial count as a total.
   - ⭐ **CONSOLIDATED 2026-08-08 — D3 is now the SOLE owner.** `PLAN-CIS-015`'s D4 carried the same
     defect (lesson `2026-07-21-17-005`) in a different workstream; it has been **struck** there.
   - ⛔ **Carried across from it, and it sharpens the deliverable**: the detection
     `artifact_entries > 0` **cannot see the collapse** — because emission fires for *some* tasks, the
     check that exists to notice the gap is satisfied by the very partiality it should report. ⇒ **A
     count-based detector cannot guard a per-item emission defect.** D3's declared scope limit must be
     a *population* statement ("N of M completed tasks emitted"), never a non-zero assertion.
   - ⚠ **Boundary against `PLAN-CIS-011`**: that plan owns `[DISPATCH]` / `[STEP]` emission for finalize
     *steps*; this owns `[ARTIFACT]` emission for *tasks*. Same archetype, different emitters — do not
     merge, and do not let either fix silently cover the other's surface.
4. **D4 — tests, each verified to FAIL pre-fix**, including one asserting the audit reports a
   deliberately-divergent step.

Four deliverables.

## Claim Labels

- OBSERVED (orchestrator-verified): `automatic-review` and unified triage ran inline on #1039 against
  a roster requiring dispatch — self-reported in that plan's finalize report and recorded in its
  `decision.log`.
- ⭐ **OBSERVED, first-party to PR #1079 — D1's vacuity is now MEASURED, not hypothesised** (folded
  2026-08-02 from inbox `plan-cis-027-…-009`, independently corroborated by `truthful-signals-026`
  item 5 on a different plan). `shape_violation` pairs Surface A (`[DISPATCH]` work.log lines)
  against Surface B (`effort resolve-target` decision.log entries). On #1079: **20 Surface-A lines,
  ZERO Surface-B entries across all 95 decision entries.** `truthful-signals` measured **18 and
  ZERO across 80** on a different plan. ⛔ **Nothing writes Surface B at all** — the aspect's spec and
  the dispatcher's instrumentation were never reconciled, so the check is structurally incapable of
  firing. **Vacuity is PROVABLE within a single plan**: `pre-submission-self-review` demonstrably ran
  three envelopes against one `[DISPATCH]` line — precisely what `shape_violation` exists to catch —
  **and it was not caught.**
- ⭐ **OBSERVED — the durable half of D1 is a REPORTING change, not only a detector fix.** Direction 1
  of the same aspect (envelope conformance) is *genuinely* clean over a populated set of 20, and
  renders as the identical `0`. **A reader cannot tell which zero is which.** ⇒ Every check that can
  return `0` from an empty population MUST publish the evaluated-population size next to the count.
  That is what makes the next vacuous guard self-announcing, and it generalises past this aspect.
  ⚠ **This is the vacuous-guard archetype at n≥5, and one prior instance was introduced BY A FIX for
  it** — apply the standing counter-measure: every set-guarding detector must be **population-derived,
  not literal** (reference implementation `test/_shared/_dispatch_roster.py`).
- OBSERVED (folded 2026-08-02 from `truthful-signals-026` item 4, **second sighting**): **a re-fired
  finalize step emits no `[DISPATCH]` line.** `pre-submission-self-review` ran three envelopes and
  emitted one `[DISPATCH]`; after `outcome=error` the re-fire path re-enters the envelope without
  passing the emission point. ⇒ **The contract is satisfied once per STEP rather than once per
  ENVELOPE.** ⭐ Read together with the item above: **this is what CREATES the unmatched pairs
  `shape_violation` cannot see.** Neither is complete alone — D1 and D2 must land together.
- ⛔ **OBSERVED — D2 also has a FALSE-POSITIVE direction** (folded 2026-08-02 from inbox
  `plan-cis-027-…-010`): `dispatch-inline-split.md` forces exactly one classification per step, and
  `default:architecture-refresh`'s is **conditional** — its dispatching Tier 1 is gated on
  `change_type`. On #1079 it reached `outcome=done` with zero `[DISPATCH]` evidence because
  `Tier 1 skipped — change_type = bug_fix`, and the coverage check emitted a
  `dispatch_coverage_violation`. **`bug_fix` is one of the most common change types here, so this
  fires on essentially every bug_fix plan.** The fix is a `dispatched-when` qualifier on the roster
  row (`change_type not in {bug_fix}`) that the coverage check evaluates — the closure invariant
  survives, since a conditional row is still exactly one row. ⭐ **The token attribution independently
  confirms no dispatch occurred** (`architecture-refresh` recorded `0/0/0`, the inline signature,
  while every other dispatched-roster step recorded non-zero) — so this is a roster-expressiveness
  gap, **not** a lost emission. ⚠ A recurring false positive in a hard-rule check is worse than a
  missing check: it trains readers to discount the category.
- ⛔ **Verify-first clause (folded 2026-08-02):** `truthful-signals` reports finalize `[STEP]` logging
  covers only **9 of 16** completed steps, with four more carrying `Completed` and no paired
  `Executing`. **Marker absence does NOT mean the step did not run**, and any count derived from
  those markers is a **FLOOR, not a count**. Settle how to enumerate step execution before asserting
  any coverage claim in D3 — including this plan's own.
- HYPOTHESIS: the `shape_violation` vacuity, the missing `[DISPATCH]` rows, and the partial
  `[ARTIFACT]` emission — each confirm/refute at its own site (verify-at-outline).
- Verify-first clause: re-read the audit at HEAD before scoping. **If PLAN-CIS-011 landed first and
  altered the roster or the step contract, re-baseline** rather than proceeding against this spec.

## Expected Surface

- HYPOTHESIS: the dispatch-audit implementation and its `shape_violation` check — exact file resolved
  at outline (verify-at-outline).
- HYPOTHESIS: the `[DISPATCH]` / `[ARTIFACT]` emission sites in `phase-6-finalize` (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/phase-6-finalize/**`.

**Disjointness:** `phase-6-finalize`. ⛔ Same bundle as PLAN-CIS-011 and PLAN-100, and as PLAN-92's D8 —
sequence, never pair.

## Dependencies and Sequencing

- Depends on: **PLAN-92 landing** (surface conflict).
- **Run BEFORE PLAN-CIS-011** — it cannot measure its own divergence while this audit is vacuous.
- Overlaps with: PLAN-CIS-011, PLAN-100, PLAN-52, PLAN-60 (same bundle).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-010-finalize-dispatch-evidence-is-missing.md"
```

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-002`)

⚠ **Leads, not facts** — re-verify before scoping.

| Source | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-010` | PLAN-99 / #1043 | The dispatch-boundary audit trail is **unpopulated, unvalidated AND uncounted** — three failures that all read as success |
| `self-review-cannot-see-an-unreachable-guard-007` | PLAN-81 / #1042 | Per-task `[ARTIFACT]` emission **stops after the first per-deliverable commit batch** |

⭐ **SCOPE CORRECTION TO D1 — this widens the plan.** The three failure modes in message 010 are
**INDEPENDENT**: *unpopulated*, *unvalidated*, *uncounted*. Fixing emission alone still leaves a
trail that nothing validates and nothing counts. **D1 must scope all three**, not the emission gap
this plan was originally staged from.

## Second Evidence Fold (2026-07-29 — `truthful-signals-008` and `-009`)

**Remedies, now stated as fix shapes rather than diagnoses:**
- `wrong-store-...-009` — emit `[DISPATCH]` lines for phase-6-finalize dispatched steps.
- `wrong-store-...-010` — emit `[ARTIFACT]` lines after phase-5-execute task completion.
- `post-merge-review-...-014` — ⭐ **emit the `[STEP] Completed` marker from `mark-step-done`, NOT
  from the caller.** This is the right structural answer *precisely because it removes the caller's
  discretion*.

⛔ **PROVENANCE CAVEAT THAT CHANGES WHAT D1 MAY CONCLUDE — read before scoping.** Both source runs
**self-reported execution deviations**, and the missing emissions are consequences of them: PLAN-103
drove **inline rather than through the normal dispatch path** (so it skipped `[DISPATCH]` for most
finalize dispatches and `[ARTIFACT]` after phase-5 tasks), and PLAN-102 **left roughly one third of
`[STEP]` emissions unmade while economising on context** — in the very run that shipped that
contract's hardening.

⇒ **These describe emissions skipped BY THOSE RUNS' OWN BYPASSING, which is NOT proof the emitter is
broken.** D1 MUST distinguish *"the step never emits"* from *"this run bypassed the emitting path"*.
**That is the difference between a code fix and a workflow-conformance fix**, and scoping the wrong
one produces a change that fixes nothing.

## Evidence Fold — 2026-07-29, from the PLAN-01 landing (#1056), `inventory-blind-spot-011`

⚠ **Leads, not facts** — re-verify at outline. **First-party observation from a completed run**, which
makes this the strongest evidence the spec carries for defect 2.

Cross-referencing `status.metadata.phase_steps["6-finalize"]` (17 steps, all `outcome: done`) against
`logs/work.log` on #1056:

- **Two done-marked steps are silent.** `push` and `ci-verify` appear **nowhere** in `work.log` —
  neither `[STEP]` nor `[DISPATCH]`. Their recorded outcomes are consequential (`pushed
  feature/inventory-blind-spot`, `ci-verify: all checks green`). The only trace is a `record-step`
  line in `decision.log`. ⛔ **The work log — the surface a retrospective reads first — cannot confirm
  the branch was pushed or that CI was green.**
- **A dispatch with no `[DISPATCH]` row.** `lessons-capture` has no `[DISPATCH]` line, yet `work.log`
  carries `[STATUS] (plan-marshall:execution-context.lessons-capture) Complete` — a line only an
  `execution-context` envelope emits. The dispatch demonstrably happened.
- **Dispatch/completion pairs cannot be matched mechanically.** The dispatch at 15:40:51 names
  `workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md`; its completion at 15:43:20
  reads `(plan-marshall:execution-context.wait-region-unified-triage) Complete`.

⭐ **This sharpens D1/D2 into a structural remedy and away from site-patching.** Emission is an
obligation on each individual **call site** rather than a property of the shared dispatch/step path,
so any site that forgets it produces a dispatch with no evidence. ⛔ **The audit that exists to catch
this reads `[DISPATCH]` lines — so a dispatch that omits its line is invisible to the very check
designed to police it. A detector that consumes voluntarily-emitted evidence can only ever report a
lower bound**, which is why D1's "make the audit able to fail" is necessary but NOT sufficient on its
own. Emit from the shared path; failing that, add a finalize-exit assertion that every `phase_steps`
entry marked `done` has at least one matching work-log line.

⚠ **Provenance caveat still applies and is NOT weakened by this fold**: the earlier sources
self-reported execution deviations. This one did not — #1056 ran the normal path — so it is the first
instance where "the step never emits" is the better-supported reading. Still confirm at the emitter.

## Second Evidence Fold — 2026-07-29, from the PLAN-10 landing (#1059)

⚠ **Leads, not facts** — re-verify at outline. Four messages fold here. ⛔ **READ THE SPLIT GUARD AT
THE END OF THIS SECTION BEFORE SCOPING** — this plan is already at four deliverables.

**(a) `end-phase-...-008` — D1 IS NOW OBSERVED, AND THE DETECTOR IS WRONG IN BOTH DIRECTIONS IN ONE
RUN.** `default:lessons-capture` is on the dispatched roster, reached `outcome=done`, and its envelope
demonstrably ran: `work.log:272` carries `[STATUS] (plan-marshall:execution-context.lessons-capture)
Complete`, `execution_log` carries `lessons-capture,6-finalize,executed,115423,24,166674`, and it
produced four real inbox messages **verified on disk by this orchestrator**. **No `[DISPATCH]` line was
ever emitted** — 17 `[DISPATCH]` lines in the run, none with `role=post-run-review`.

⛔ **The consequence is worse than a missing log line.** `dispatch_coverage_violation` keys *solely* on
`[DISPATCH]` presence and its canonical message asserts *"the step ran inline where dispatch was
required"*. For `lessons-capture` that conclusion is **false** — the step WAS dispatched. **The detector
converts an instrumentation gap into a fabricated discipline violation.** In the same run it also
produced the mirror-image false positive on `architecture-refresh` (rostered dispatched, genuinely and
correctly inline, Tier-1 skipped on `change_type = bug_fix`). ⇒ **One plan, two firings, wrong about the
nature of the violation in opposite directions.**

⭐ **The remedy this yields, and it is a scope sharpener for D2**: a step with envelope evidence but no
`[DISPATCH]` line must be reported as `missing_dispatch_emission` — an instrumentation finding against
the **dispatcher** — NOT as `dispatch_coverage_violation`, a discipline finding against the **step**.
That requires the check to consult a second, independent evidence source (the `[STATUS] …Complete` line
and/or a non-zero token record) before concluding "ran inline".

**(b) `end-phase-...-014` — D1's vacuity is now CONFIRMED WITH ITS MECHANISM.** `shape_violation` is
defined as a resolve-without-dispatch pairing: a `decision.log` `(plan-marshall:manage-config)`
`effort resolve-target` entry with no subsequent `[DISPATCH]` for the same role. This run's
`decision.log` contains **zero** `effort resolve-target` entries across **17** dispatches. ⇒ **Surface B
is empty, so the pairing has no left-hand side and the check cannot produce a finding under any
circumstances.** Its `shape_violation: 0` means *never evaluated*, not *evaluated clean*. ⛔ **D1 must
decide the prior question the spec does not currently ask: is the resolver expected to log and does
not, or is the audit built on an evidence surface no producer writes?** Until that is settled, the
check must report `not_evaluated` with its empty-population reason rather than `0`.

Same message, same shape, two more producerless surfaces: **`dispatch_boundaries` is a valid registry
key that NO aspect row produces** (the data is emitted nested inside `analyze-logs`' fragment), so the
"Phase Dispatch Boundaries" section is omitted on **every run, forever**, and the omission is classified
BENIGN. Executive Summary likewise has no producer. ⇒ **Distinguish "no producer exists" from "producer
ran and found nothing" in `sections_omitted` — only the latter is benign.** ⚠ The aspect-naming defect
in the same message (one aspect, three names: "Invariant outcomes" / `invariant-check-summary.md` /
`invariant-summary`, where the documented label is rejected by the registry) is **`plan-retrospective`'s
surface, not this plan's** — cross-noted, not folded here.

**(c) `end-phase-...-007` AXIS 2 ONLY — the context-load columns are producerless.** Every row of every
boundary file carries `0` for all four per-dispatch context-load columns (`input_tokens`,
`output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) — 10 rows across 3 phases.
The flags exist and default to `0`; **no call site anywhere passes them.** A column that defaults to `0`
with no producer is indistinguishable at read time from a measured zero.

⛔⛔ **AXIS 1 OF THAT MESSAGE IS RETRACTED AND MUST NOT BE SCOPED.** The message reported three missing
`record-dispatch-boundary` rows (a 433,411-token arithmetic gap) as a tool defect. **The plan itself
subsequently identified this as its OWN omission** — three item-5c calls skipped to conserve context —
and repaired the trail (9 rows now reconcile). ⭐ **This is exactly the provenance caveat this spec
already carries**: *"these describe emissions skipped BY THOSE RUNS' OWN BYPASSING, which is NOT proof
the emitter is broken."* The caveat has now been vindicated once in each direction — (a) is a genuine
emitter gap, axis 1 was a run-conformance gap. **D1's obligation to distinguish the two is not
theoretical; it has already produced one false positive.**

**(d) `end-phase-...-013` — the same shape OUTSIDE finalize, which widens the surface.** The **first**
entry into 5-execute logs `Re-entering execute phase`: 0 `Starting` markers, 2 `Re-entering` markers,
2 dispatch clusters. `RE_ENTRY_COVERAGE` computes `expected = clusters − 1 = 1`, observes 2, and
reports a mismatch **against a plan whose dispatch behaviour was entirely correct** (one genuine first
entry, one genuine re-entry). ⛔ The rule's precondition is satisfied by *the presence* of the line, not
by the line being *correct* — so the guard certifies a differentiation that is absent. Likely cause: the
entry path keys on something true on first entry too (`worktree_path already populated` was logged on
that same first entry). ⇒ Two fixes: key the marker on a genuine first-entry discriminator, and make
the rule report `indeterminate` rather than `mismatch` when `starting_markers == 0`.

### ⛔ Split guard — MANDATORY read before scoping

This plan had four deliverables and this fold adds material to all of them plus a new surface
(`phase-5-execute`). **Do NOT absorb silently.** Recommended shape:

- **Keep here**: the vacuous/producerless-detector arm (b) and the emission-vs-discipline arm (a)+(c) —
  they are one seam, `phase-6-finalize` + the dispatch audit, and (b) is already D1.
- **SPLIT OUT** (d) if the deliverable set passes six: it is `phase-5-execute` marker emission plus one
  `plan-retrospective` rule precondition — a different bundle and independently landable.
- **Derive, do not enumerate**: every arm here names *observed instances*. The population of
  emission-gap sites and of producerless columns/sections is **unmeasured**, and this spec's own
  standing rule ("a reported instance is a sample") applies to all four.

## ⭐ Third Evidence Fold — 2026-07-29, `truthful-signals-016`: THE CHANNEL IS 64% POPULATED, AND NOW IT HAS A NUMBER

⚠ **Lead, not fact** — first-party from PLAN-109's retrospective (PR #1058), not independently re-read.
⭐ **This is the same defect this spec already owns, with a measurement attached — which converts D1
from "establish whether the emitter is broken" into "measure the channel and report its completeness".**

On that plan:

- `[DISPATCH]` lines emitted: **9**
- `execution-context.{name} Complete` envelope completions observed: **14**

⇒ **Five envelopes ran with no dispatch record at all**, including
`project:finalize-step-review-retrospective` (72,510 tokens / 13 tool uses) and `lessons-capture`
(89,398 tokens / 24 tool uses) — **both with manifest-recorded spend proving they ran**.
**161,908 tokens, roughly 30 % of finalize spend, left no dispatch evidence.**

⭐ **The mechanism of the gap is now identified and it is NOT random forgetfulness: only the FIRST
dispatch of a step emits a line, so every loop-back or re-review re-entry is invisible.**
(`automatic-review` fired three times and produced one line.) ⛔ This is a **re-fire** defect, which
means the population of missing rows scales with loop-backs — the very runs most likely to be audited.

**Why this undercuts the detector, stated more sharply than this spec had it:** the audit's
inverse-coverage half flags "step marked done with zero matching `[DISPATCH]`" as
*inline-where-dispatch-was-required*. ⛔ **On a channel this sparse the check cannot fire truthfully in
EITHER direction** — a genuinely-inline step and a dispatched-but-unlogged step are indistinguishable.
**The detector is population-derived from a population it does not control, and nothing measures the
channel's own completeness.**

**Two remedies, both adopted into this spec's scope:**

1. **Emit `[DISPATCH]` from the single dispatch seam**, not from each step's prose, so **re-fires
   cannot bypass it.** This is the same structural answer already recorded here (emit from the shared
   path) — now with the re-fire case as the proof that per-site emission cannot be patched into
   correctness.
2. ⭐ **Have the audit report channel completeness (`dispatch_lines / envelope_completions`) alongside
   its findings, so a sparse channel DOWNGRADES THE AUDIT'S OWN CONFIDENCE** instead of silently
   weakening its verdicts. ⛔ **This is the single most reusable idea in the fold** — it generalises
   past this detector to every check in the programme that consumes voluntarily-emitted evidence, and
   it is the concrete form of "a detector that consumes voluntary evidence can only report a lower
   bound", which this spec already asserts but does not currently make *measurable*.

⇒ **D3 sharpener**: `envelope_completions` is an independent, already-emitted second source
(`[STATUS] … Complete`). It is the denominator that makes completeness computable **today**, with no
new instrumentation — which is what makes remedy 2 cheap enough to do first.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
