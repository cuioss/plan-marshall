# PLAN-CIS-011: Finalize Step & Dispatch Emission (a step that ran and left no trace)

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-07-25 (lessons-triage). ⛔⛔ **SPLIT 2026-08-08 — THIS SPEC HAS BEEN NARROWED. Scope from
> the split table below, NOT from the deliverable numbering, which now has gaps.**
>
> The spec had accreted from four deliverables to **ELEVEN** (D1–D11) through seven separate folds —
> the worst split-guard breach in the queue, and far past the point where it could land or be analyzed
> as one unit. ⭐ **The tell was not the count**: it was that D8/D10/D11 had begun citing each other as
> candidate explanations while D3/D4 touched an entirely different surface. **Three surfaces were
> wearing one plan's name.**
>
> | Arm | Went to | Former deliverables |
> |-----|---------|---------------------|
> | **Step & dispatch EMISSION** — a step that ran and left no trace | **THIS PLAN** | D1, D2, D5, D6, D7, D9 |
> | **Boundary-LEDGER arithmetic** — a coverage figure over an undeclared population | **`PLAN-CIS-037`** | D8, D10, D11 |
> | **Frozen MANIFEST vs live config** + finalize prompt/log residue | **`PLAN-CIS-038`** | D3, D4 |
>
> ⭐⭐ **THE SPLIT UNBLOCKED A SIBLING, which is its most valuable consequence.** The epic's standing
> note read *"CIS-011 must land first; `PLAN-CIS-035`'s D1 shares need a denominator that is not
> `17 of 9`"* — but that denominator is **D8**, which now lives in `PLAN-CIS-037`. ⇒ **CIS-035 is
> blocked on CIS-037 ONLY**, and this plan may now land in any order relative to it. **Do not re-derive
> the old dependency.**
>
> **What remains here is one coherent question**: does a finalize step's execution leave a reliable
> trace? Six deliverables — at the guard, but genuinely one surface (`[DISPATCH]` / `[STEP]` emission
> and the `mark-step-done` handshake), so proceeding unsplit is deliberate and recorded.

## Objective

Finalize-phase machinery repeatedly loses or contradicts its own observability: a dispatched step
reaches `done` with no `[DISPATCH]` emission, the manifest emits two contradictory decision lines for
one selection, the frozen `execution.toon` diverges from the live candidate set, and the simplify
prompt lacks a line-level scope boundary. Make the finalize/manifest signals truthful and complete.

## Deliverables

### D1 — GATE: map the observability seams + fixes (mutates nothing)
Confirm each open defect at HEAD; pair each signal with the write seam that must co-emit it.

### D2 — dispatch & selection observability
- `2026-06-24-10-001`: a dispatched finalize step must emit `[DISPATCH]` at the same seam it writes the metrics dispatch-boundary record (6× recurrence: build-decision #985, modernize-python #987).
- `2026-07-22-00-002`: the manifest must not emit two contradictory adjacent decision-log lines for one step selection (`_log_pre_push_quality_gate_omitted` vs `_log_ceremony_finalize_selection 'added'`).

### ~~D3 — frozen-vs-live reconciliation~~ ⛔ MOVED 2026-08-08 → `PLAN-CIS-038`

*Text retained below as the moved record. **Do not scope it here.***

### D3 (moved) — frozen-vs-live reconciliation
- `2026-06-21-01-001`: reconcile the outline-composed `execution.toon` against the live `marshal.json` candidate set at finalize-entry (a self-modifying plan's frozen toon references a deleted/added step — diff/backfill, not a hard `validate-loadable` fail).
- `2026-07-10-23-002`: `finalize-step-sync-baseline` regenerates the phase-5-generated per-tree executor after a non-noop rebase (script set changed; clean-env dispatch fails notation resolution otherwise).

### ~~D4 — simplify scope + title-log noise + promote + retire~~ ⛔ MOVED 2026-08-08 → `PLAN-CIS-038`

*Text retained below as the moved record. **Do not scope it here.***

### D4 (moved) — simplify scope + title-log noise + promote + retire
- `2026-06-25-08-003`: the finalize-step-simplify dispatched prompt gets a line-level "pre-existing lines OUT OF SCOPE" clause under changeset scope (today only a file-level boundary).
- `2026-07-22-12-001`: suppress the repeated `[MANAGE-STATUS] Title token` INFO line on an unchanged token value.
- Promote `2026-06-28-13-001`'s residue (bypass/guard branch placed BEFORE the dispatch it guards). Tests pin each; finalize retires the carried lessons.

### D5 — the dispatcher does not forward `--iteration` to `plan-retrospective` (folded 2026-08-02)

From `truthful-signals-026` item 7. `plan-retrospective`'s mode detection is *"`--iteration` present
⇒ finalize-step mode"*, and **only** finalize-step mode emits the `mark-step-done` tail. The dispatch
prompt body carried no `iteration`. ⇒ **Following the documented heuristic literally selects
user-invocable mode**, skips `mark-step-done`, and leaves
`phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` **unwritten** — a step that ran with
no record that it ran, which is exactly the observability class D2 owns.

⚠ **Re-ground against #1076 before scoping**: it added `mark-step-done --fact` and rewired three
steps, so **the tail this item says is skipped now carries more payload than when the item was
filed.** Confirm the current shape rather than the filed one.

### D6 — `[STEP]` logging covers 9 of 16 completed steps (folded 2026-08-02)

From `truthful-signals-026` item 8 — ⭐ **the widest blast radius of the delegated set, and
corroborated three ways.** Seven steps completed with **no** `[STEP]` evidence; four more carry
`Completed` with no paired `Executing`. Emission is **per-handler rather than driven by the step
loop**, and the Executing/Completed pairing is convention, not contract.

Corroboration: `truthful-signals`' own 39-plan corpus found **33× `sync-baseline` markers vs 1×
`sonar-roundtrip`**; #1076's msg-010 independently confirmed markers are absent for
`lessons-capture` and for head-advance re-fires.

⛔ **Standing consequence, and it binds this plan's own measurements**: any count any of the three
epics derives from `[STEP]` markers is an **undercount of unknown size** — a FLOOR, not a count.
**Marker absence does not mean the step did not run.** Drive emission from the step loop so the
population is structural, and until then label every marker-derived figure as a floor.

### D7 — fuse the `[STEP]` emission to the `mark-step-done` handshake (folded 2026-08-03, CIS-028 drain `…-014`)

⭐ **D6's remedy, now named concretely and backed by a fresh first-party instance.** On PLAN-CIS-028
`default:finalize-step-preference-emitter` recorded a full terminal outcome
(`outcome: done`, `display_detail: "1 pattern promoted, owed hint to epic inbox"`) and
**demonstrably did its work** — inbox message `…-008.md` was written at `21:57:41`. Yet `work.log`
contains **neither** `[STEP] Executing step: …` **nor** `[STEP] Completed step: …` for it; the two
adjacent lines are consecutive:

```text
21:56:27  [STEP] Completed step: default:lessons-capture
21:57:58  [STEP] Executing step: default:branch-cleanup
```

⚠ **The absent `[DISPATCH]` line is CORRECT** — `dispatch-inline-split.md` classifies this step as
inline, so it is owed none. **The absent `[STEP]` pair is not**: every other inline step in that run
(`push`, `ci-verify`, `architecture-refresh`, `branch-cleanup`,
`project:finalize-step-era-stamp-fill`) emitted both. Do not let the inline classification be read as
an exemption at outline.

⛔ **The structural point, which is why this is a deliverable and not another data point for D6**:
`phase_steps_complete` is satisfied by the `mark-step-done` handshake **alone**, while the `[STEP]`
emission is a **separate instruction living in workflow prose**. ⇒ A step can be **fully compliant
with the invariant while leaving no trace in the operational log** — and those two records are
precisely the pair a retrospective, an audit, or a debugging operator cross-checks against each
other. The `execution-context-dispatch-audit` aspect's inverse-coverage half depends on that
cross-check; here it had to fall back on `status.json` to establish the step ran at all.

**Deliverable**: `mark-step-done` already receives `--step`, `--phase` and `--outcome` — it has
everything the line needs. **Emit `[STEP] Completed step: {step}` from the script itself.** A prose
instruction to log, sitting beside a script call that already knows the payload, is a duplication
that can only ever drift **toward silence**, because nothing reads the log back to confirm the
emission. The omission is discoverable only by someone counting steps in two places.

⭐ **Generalise to the peer pair in the same pass**: an outcome record that omits
`head_at_completion` is likewise unverifiable on re-entry. PLAN-CIS-028 paid a **full re-dispatch**
of `project:finalize-step-lessons-housekeeping` for exactly that (*"Prior verdict UNVERIFIED — done
record carried no `head_at_completion`"*). Same shape: **a terminal record well-formed enough to
pass and thin enough to be useless.**

### ⛔ D8, D10 and D11 MOVED 2026-08-08 → `PLAN-CIS-037`

**The boundary-ledger arithmetic arm.** ⛔ **`PLAN-CIS-035`'s blocker moved with them** — it is now
`PLAN-CIS-037`, not this plan. *Text retained below as the moved record; **do not scope it here**.*

⚠ **D9 stayed here** (it is `[STEP]` path-dependence, an emission defect) but it hands CIS-037's D2 a
candidate explanation to rule in or out: a resumed run may contribute to numerator and denominator
inconsistently. **Cross-reference, not shared ownership.**

### D8 (moved) — the completeness ratio has a denominator smaller than its numerator, and it is stamped `complete` (folded 2026-08-03, PLAN-CIS-001 / #1084)

**OBSERVED first-party**: that run's `6-finalize` row rendered

```text
17 of 9 dispatch(es) recorded — complete
```

⛔ **`17 of 9` is not a ratio**, and the verdict attached to it is **`complete`** — so the surface
that exists to report coverage emitted an arithmetically impossible figure and certified it.

⭐ **This is D6's marker-floor problem seen from the other end, and the pair is what makes it
tractable.** D6 says a marker-derived count is a **floor** (9 of 16 steps carry `[STEP]` evidence);
here the numerator is drawn from one population and the denominator from a narrower one, and nothing
asserts they are commensurable. ⇒ **The two figures are not the same measurement and are printed as
if they were.**

**Deliverable**: the numerator and denominator of any recorded-vs-expected ratio must be **derived
from one declared population**, and a ratio whose numerator exceeds its denominator must be a **loud
failure**, never a `complete`. ⛔ **Do not fix this by clamping the display** — a clamped `9 of 9`
would be the same defect with the evidence removed.

⚠ **Blocking for a sibling**: `PLAN-CIS-035` computes shares of dispatch spend against this
denominator. **CIS-011 should land before CIS-035's D1 asserts any share.**

### D9 — an operator resume after a loop-back halt emits NO step instrumentation at all (folded 2026-08-03, lesson `2026-08-03-14-006`)

**OBSERVED first-party on #1084.** ⭐ **This is the sharpest case for D7's fuse-the-emission remedy**,
because it is not a step that forgot to log — it is an entire **entry path** that logs nothing.

⇒ ⛔ **The `[STEP]` population is not merely incomplete (D6's 9-of-16 floor), it is
PATH-DEPENDENT**: whether a step is observable depends on **how the run re-entered**, which is
exactly the dimension no marker-derived count can see. A resumed run is indistinguishable from a run
that skipped those steps.

**Binding on this plan's own measurements**: any coverage figure must state whether the runs in its
population included a resume. ⛔ **And it compounds with D8** — a resumed run contributes to the
numerator or denominator of `recorded-vs-expected` inconsistently, which is one available explanation
for `17 of 9` that D8 must rule in or out rather than assume.

### D10 — whole classes of dispatch record NO boundary at all (folded 2026-08-03 from `…-004`, PR #1086)

**`2-refine` and the `q-gate-validation` spawns record no dispatch boundary whatsoever.**

⇒ ⛔ **This is a harder problem than D6/D9 and it changes what a "floor" means here.** D6 says a
`[STEP]`-marker count is a floor; D9 says the marker population is path-dependent. **D10 says an
entire dispatch CLASS is missing from the ledger** — so the denominator itself is drawn from a
population that structurally excludes some dispatches.

⭐ **And it compounds directly with D8's `17 of 9`**: if some dispatch classes never register, a
numerator counted one way and a denominator counted another **cannot** agree, and `17 of 9` becomes
an expected outcome rather than an anomaly. **D8 must test this as a candidate explanation before
treating the ratio as a separate defect.**

**Deliverable**: every dispatch records a boundary, or the ledger declares which classes it excludes.
⛔ **Silent exclusion is the defect** — a ledger that omits a class without saying so is
indistinguishable from a class that did not run.

### D11 — the dispatch-boundary comparator is wrong on EQUALITY, and D10 is confirmed on an independent plan (folded 2026-08-03)

From an operator-supplied `metrics.md` for `plan-45-demo-client-doc-consolidation` — **a plan neither
epic ran**, which is what makes it independent corroboration rather than a second look at our own run.

**(a) The comparator mislabels the equal case.** `6-finalize` reports
`Dispatch-boundary total: 2,468,507` beside `Total tokens: 2,468,507` — **identical** — annotated
*"recorded; not preferred — smaller than total_tokens under same-population max"*. ⛔ **Equal is not
smaller.** The max-selection is arithmetically fine; **the message asserts a strict inequality that
does not hold**, so a reader is told the boundary ledger under-counted when it agreed exactly.
⭐ **Worth more than a wording fix**: an exact agreement between two independent producers is the
single most valuable signal this surface can emit — **and it is currently rendered as a discrepancy.**

**(b) D10 confirmed off our own corpus.** That plan carries **no `Dispatch-boundary total` for
`2-refine` or `3-outline` at all**, while 4-plan / 5-execute / 6-finalize have one. ⇒ **The missing
dispatch classes are not an artifact of our runs** — same two phases, different plan, different epic.
**D10 may be scoped as a general defect rather than requiring a population sweep to establish that it
exists** (the sweep is still owed to establish its SIZE).

## Lessons Carried (bound 2026-07-25 · lessons-triage)
- `2026-06-24-10-001` — **OPEN** — dispatched step reaches done with no `[DISPATCH]` (D2).
- `2026-07-22-00-002` — **OPEN** — manifest contradictory adjacent decision lines (D2).
- `2026-06-21-01-001` — **OPEN** — frozen execution.toon diverges from live marshal.json (D3).
- `2026-07-10-23-002` — **OPEN** — worktree executor not regenerated after sync-baseline rebase (D3).
- `2026-06-25-08-003` — **OPEN** — simplify prompt omits line-level changeset scope (D4).
- `2026-07-22-12-001` — **OPEN** — title-token INFO line logs unconditionally (D4).
- `2026-06-28-13-001` — bypass/guard branch must precede the dispatch it guards — landed #786, promote.

## Expected Surface
- `phase-6-finalize` (dispatch emission, sync-baseline executor regen, simplify prompt)
- `manage-execution-manifest` (contradictory log lines, frozen-vs-live reconcile)
- `manage-status` title-token log; tests under `test/plan-marshall/**`

**Disjointness:** phase-6-finalize + manage-execution-manifest + manage-status. Adjacency: PLAN-52 /
PLAN-60 also touch `phase-6-finalize` (different files) — coordinate at outline.

## Second concern in the same row — the audit verdict carries no depth

A finalize/audit verdict is recorded without the depth at which it was reached, so a shallow pass and
a thorough one are indistinguishable in the record. That is this epic's flagship archetype pointed at
the same `execution_log[]` row this plan already owns — one structure, so one plan.

**Deliverables for this half:**
- **GATE (mutates nothing)** — establish what actually differed between a shallow and a thorough
  pass, then decide what a verdict must carry to make them distinguishable.
- **The verdict carries its depth** in the recorded row.
- **The depth is chosen, not defaulted-into** — a verdict must not inherit a depth nobody selected.
- **Tests.**

⚠ **Boundary:** if recording depth requires touching **effort resolution**, stop and coordinate with
**PLAN-CIS-014** (aggregate cost) and **PLAN-99** (shared reporting shape) rather than editing that seam
from inside this plan.

⚠ **Split guard:** if the combined deliverable set runs past the guard, split the depth-recording arm
out and say so rather than absorbing silently.

## `finalize-step-simplify` is classified DISPATCHED but needs a second dispatch

Observed on PR #1034 (message-supplied; HYPOTHESIS until re-verified at outline). The step is
classified **DISPATCHED**, but its own Step 3 requires a **second `Task:` dispatch that a leaf cannot
make**. The leaf returned `blocked / leaf_cannot_dispatch`, and the inner review was run from main
context instead — so the step's declared topology and its actual execution disagree.

This is the **leaf/dispatch-topology invariant** (`ref-workflow-architecture/standards/agents.md`)
violated by a step this plan already observes, which is why it lands here rather than as its own plan.

⛔ **The observability angle is the point:** the step still reported a normal result. A topology
violation that degrades into "the orchestrator did it instead" and reports success is exactly the
confident-signal-hides-a-caveat shape — **the manifest should be able to say a dispatched step did
not actually dispatch.** Fix the classification or the step, and make the divergence visible.

## Two more manifest/dispatch observability items

Message-supplied, HYPOTHESIS until re-verified at outline.

**(a) Two prune predicates in one compose run disagreed about whether the plan has a footprint.** Two
independent answers to the same question inside a single compose — so at least one is wrong, and
nothing reconciles or reports the disagreement. **A composer that silently proceeds on contradictory
predicates is the same shape PLAN-75 (#1032) closed for the declared step contract.** Make the
disagreement fail or surface; do not pick a winner silently.

**(c) CONFIRMED LIVE, and the document-level mechanism is now known (cross-epic handover from
`test-suite-quality`, verified in-tree at `6d51ae704`).** `phase-6-finalize/standards/dispatch-inline-split.md`
**declares itself "the single source of truth"** for which steps dispatch and which run inline, and
carries a closure invariant at `:9` — *"Every step carries **exactly one** classification: … never
both and never neither."* **`default:architecture-refresh` carries TWO classifications, and the
runtime obeys the NON-authoritative one.**

⛔ **This is the epic's flagship archetype in its purest documentary form:** a document that declares
itself authoritative is the confident signal; that the runtime ignores it is the suppressed caveat.
**The closure invariant is violated by the very document that states it** — so the invariant is not
merely unenforced, it is false on its own page.

**And its closure test is vacuous.** The test **opens the file
but never asserts classification**, so it passes regardless of what the file says. ⛔ **A test that
cannot fail is worse than no test**: it converts an open question into a documented-as-closed one.
This is the vacuous-guard archetype inside the coverage for the very divergence (b) describes — fix
the assertion first, and **verify it FAILS against the divergent state** before changing anything else.

**(b) `architecture-refresh`'s Tier-0-only zero-dispatch path is undocumented**, while `ci-verify`'s
equivalent path **is** documented. A step that legitimately dispatches nothing looks identical to a
step that failed to dispatch — which is precisely the ambiguity this plan exists to remove. Document
it the way `ci-verify`'s is documented, so a zero-dispatch run is *declared* rather than inferred.

⚠ Both fold in here rather than standing alone because this plan already owns the composed-manifest
and dispatch-emission surface — same serialization class.

## Three more dispatch/observability gaps

Message-supplied, HYPOTHESIS until re-verified at outline. All three are this plan's own surface.

**(f) `finalize-step-simplify` can introduce NEW untested production code with no test-coverage
gate.** A step whose purpose is simplification can add production code that no test exercises, and
nothing stops it. ⚠ Note the interaction with (a): simplify is already implicated in a topology
violation, and #1038 also records that it was **not re-swept after a loop-back commit**. Treat the
step as a whole rather than patching one symptom.

**(i) Finalize-step mode resolution keys on `--iteration`, so a real finalize dispatch degrades**
(#1039). A mode decision keyed on the wrong signal means a genuine dispatch is treated as something
else — same family as (a)/(g): the step's declared shape and its executed shape diverge, and nothing
reports it.

**(j) `SKILL.md`'s dispatch table omits an inline Step-1 precondition, inviting a missing-field
dispatch** (#1039). The table that documents dispatch shape is itself incomplete, so a conforming
reader builds a non-conforming call.

**(g) THIRD DISTINCT SITE (#1039) — `automatic-review` and the unified triage ran INLINE where the
roster requires DISPATCH**, leaving no `[DISPATCH]` row for either. ⭐ **With `architecture-refresh`
(two sites) and `finalize-step-simplify`, the divergence is no longer per-step — the roster and the
runtime disagree BROADLY.** D1 must scope for a systematic reconciliation, not three patches:
**derive the divergent set population-wise from the roster** rather than fixing the sites this spec
happens to name. ⚠ Recall the roster document *declares itself the single source of truth* and states
a closure invariant it violates — so the roster cannot be trusted as the baseline either; both sides
need establishing.

## ⭐ (k) A measured ZERO where "unmeasured" is the truth — folded 2026-07-28 from the PLAN-94 landing (#1040), inbox message 007

**OBSERVED, first-party in PLAN-94's decision log.** `manage-execution-manifest record-step` wrote
**nine** entries of the form:

```text
Recorded ci-verify phase=6-finalize outcome=executed — total_tokens=0, tool_uses=0, duration_ms=0
```

Every one of those steps did real, expensive work: `pre-push-quality-gate` (three build invocations),
`architecture-refresh`, `push`, `ci-verify` ×2 (`ci_complete_precondition` recorded at **591 s** and
**562 s**), `branch-cleanup` (~16 min including the merge-queue wait and the merge itself),
`era-stamp-fill`, `preference-emitter`. All recorded as `0`.

The cause is mechanical and legitimate — these steps ran **inline** in the orchestrator context, so
there is no dispatched-agent `<usage>` envelope to read. ⛔ **The defect is not the missing
measurement. It is writing `0` where the honest value is ABSENT.**

The consequence compounds: `6-finalize` never closed its metrics row at all, so `metrics.md` renders
the **most expensive phase of the entire run** as empty, with the total marked `n=4/6`. That
partiality marker is the one honest signal in the table — **but the nine `0`s upstream of it are not
marked partial anywhere and are indistinguishable from a step that genuinely consumed nothing.**

⇒ **Rule this deliverable carries:** a cost field with no measurement serializes as **absent/null**,
never as `0`. `0` is a legitimate measured value (a no-op step really can cost nothing) and must stay
available to mean exactly that.

1. `record-step` accepts and persists a **null/omitted** cost triple distinctly from a zero triple,
   and renders inline steps that way.
2. The decision-log line says so: `total_tokens=unmeasured (inline step)`, not `total_tokens=0`.
3. Close the `6-finalize` metrics row on the terminal path so the phase is *recorded* even when its
   cost is unmeasured. ⚠ **This is a call-site omission, not a missing capability** — the `end-phase`
   contract already treats a timestamps-only closed row as fully recorded (the sanctioned inline-phase
   recording mode).

Aggregation then has what it needs: sum the measured, count the unmeasured, report both — instead of
silently summing structural zeros into a total that looks complete.

⚠ **Related but DISTINCT from the recorded floor-not-truth work on `generate`'s `partial` /
`unrecorded_phases`** — that made *phase-level* incompleteness first-class. This is the *step-level*
hole underneath it and is **not** covered by the same marker. It also corrupts this epic's own
instrumentation: any cross-plan token-economics or lane-lever-effectiveness analysis reading these
fields systematically under-attributes cost to finalize — the phase where most of the wall-clock and
a large share of the tokens actually go.

⛔ **SPLIT EXECUTED — the EVIDENCE seam (the vacuous `shape_violation` audit, missing `[DISPATCH]`
rows, partial `[ARTIFACT]` emission) is now PLAN-CIS-010.** This plan keeps the STEP-CONTRACT seam.
**Same bundle — sequence, never pair; run PLAN-CIS-010 FIRST**, because this plan cannot measure its own
divergence while that audit is vacuous.

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-002` and `-003`)

⚠ **Leads, not facts** — re-verify before scoping.

| Source | Origin | Claim |
|---|---|---|
| `one-coherent-automated-review-contract-017` | PLAN-92 / #1041 | `record-step` for `archive-plan` is **structurally unsatisfiable** |
| `runnable-slice-keys-...-018` | PLAN-89 / #1044 | A step's **structural caveat stayed in the work log and never reached its outcome** |
| `one-coherent-automated-review-contract-008` | PLAN-92 / #1041 | Phase-4 **froze the step-param key** the plan retired, silently breaking its own finalize |

⛔ **017 IS A CONTRACT COLLISION, NOT A PATCH — it forces a D-level decision.** Two documented
constraints are jointly unsatisfiable:
- dispatcher item 5e: *"this row is recorded for EVERY finalize step — dispatched OR inline"*, after the step completes;
- `archive-plan` ordering: it **MUST be last**, and it **moves the plan directory** — including `execution.toon`, the row's own target.

Observed: `status: error, file_not_found, execution.toon not found`. ⇒ Neither rule is buggy; **the
pair cannot both hold.** One must yield, and which one is a **design decision**, not a fix.

⭐ **`one-coherent-008` folds onto D3 (frozen-vs-live reconciliation).** It is the purest instance the
programme has produced: PLAN-92's own subject was single-sourcing the bot contract, and it shipped
past a gate its own change had emptied.

## Second Evidence Fold (2026-07-29 — `truthful-signals-009` and `-010`)

⭐ **`post-merge-review-...-012` IS THE STRUCTURAL REMEDY: consolidate `record-step` and
`record-dispatch-boundary` into ONE accounting ledger.** They are two ledgers over one population, and
they demonstrably disagree — `metrics.md` carries lines like *"Dispatch-boundary total: … (recorded;
not preferred — smaller than total_tokens under same-population max)"*.
⇒ **Those reconciliation notes are the system compensating at READ time for a defect at WRITE time.**
A same-population max is a heuristic that hides *which* ledger was wrong. One ledger removes the
heuristic and removes the recurring question "which of these two numbers do I trust".

**`post-merge-review-...-011` — re-open the phase metrics window on loop-back re-entry.** PLAN-102
measured a **~40% token under-report** because the loop-back never re-opened the window.
⚠ **Very likely the same defect family as PLAN-10's replace-not-accumulate** (73% overwrite). ⛔ **Do
NOT fix twice — and do NOT assume identical.** One describes a *window that never re-opens*, the other
a *write that replaces*. **Establish whether closing the window correctly also fixes the overwrite, or
whether both halves need changing.** That determination belongs in D1, not in the fix.

⭐ **API-Sheriff #6 — NEW, and it is a SELECTION defect, not a coverage one.** Phase-5 ran
`verify -pl integration-tests -am`; CI runs `verify -Pintegration-tests` for the same module. **Only
the second builds the GraalVM native executable.** A `static final SecureRandom` without runtime-init
registration failed native-image (*"Detected an instance of Random/SplittableRandom class in the image
heap"*) **while the local gate was green**. The manifest picked a command *sharing a module name with
the CI gate but not its build depth* — **which reads as coverage while providing none.**
⇒ **Proposed rule**: when the footprint touches code a **profile-gated build compiles differently**
(native image, AOT, shaded/relocated artifact, alternate runtime), select the **profile-gated**
command. *"Do not treat 'the module is covered' as sufficient."*

## ⭐ Cross-Epic Ownership Settled — 2026-07-29, answering `truthful-signals-011`

`truthful-signals` asked, blocking their PLAN-TRUTH-001 D5 scoping, whether PLAN-CIS-010 or PLAN-CIS-011 already
owns **the derived cross-document classification detector**. The orchestrator read both specs and
answered **YES — this plan (PLAN-CIS-011) owns it**, on the strength of two sections already here:

- **§ "(c)"** already carries the `default:architecture-refresh` dual-classification defect *and* the
  finding that its closure test is **vacuous** ("opens the file but never asserts classification"),
  with the standing instruction to fix the assertion and **verify it FAILS against the divergent
  state** before changing anything else.
- **§ "(g)"** already requires the divergent set be **derived population-wise from the roster** rather
  than patching the sites the spec happens to name.

⇒ **D5b (derive the full contradicting-step population) and D5c (close the detector blind spot with a
cross-document consistency assertion) are THIS plan's work.** `truthful-signals` keeps **D5a** (correct
`dispatch-inline-split.md:23` to inline, deleting the faulty rationale) and **D5d** (reconcile the five
`SKILL.md` enumeration sites) — the doc-correction half, which is theirs under the routing rule.

**Two constraints carried in from their finding, both of which sharpen this plan's scope:**

1. ⛔ **The roster document cannot be trusted as the baseline.** `dispatch-inline-split.md:3` declares
   itself the single source of truth and `:9` states a closure invariant — *"every step carries exactly
   one classification"* — that the document **violates on its own page**. Worse, the designated SSOT is
   **substantively wrong on the merits**: `architecture-refresh.md:26` carries the binding mechanism
   (Tier-1 `prompt` mode needs `AskUserQuestion`, which a dispatched leaf cannot fire), so classifying
   the step dispatched makes its documented mode unreachable. The `:23` rationale conflates *a
   sub-dispatch an inline step MAKES* with *the step BEING dispatched* — under that rule every inline
   step that spawns anything reclassifies.
2. ⛔ **Do NOT close the detector gap with a second hand-written pin.** The existing test already
   carries a hand-written pin for `finalize-step-simplify` and none for `architecture-refresh`; a
   hand-maintained mirror of a derived set is the recurring archetype (n=5+). ⭐ **Their detector
   analysis is the reusable insight**: every assertion in the current test is a **completeness**
   property (coverage, disjointness, no step-count claim) and **none is a correctness** property — it
   can prove each step has exactly one classification and never that the classification is *right*,
   because it never reads the step's own standards doc.

⚠ **`architecture-refresh` is a KNOWN mismatch, not THE mismatch.** The population is unknown and an
asserted absence of further mismatches needs the same derivation as an asserted presence — treat the
one confirmed instance as a sample.

⛔ **Cross-epic surface warning**: `truthful-signals` PLAN-112 is LAUNCHED into `phase-6-finalize`
right now, and PLAN-TRUTH-001 will touch `dispatch-inline-split.md` for D5a/D5d. Cross-epic disjointness is
NOT computed automatically. Sequence against both before emitting this plan.

⚠ **Duplicate signal, folded not re-filed**: `end-phase-replace-not-accumulate-004` independently
reported the same `architecture-refresh` dual classification from a second run. Recurrence recorded
here; it did not become a second item.

## ⛔ Sequencing + Trap Warning — 2026-07-29, `truthful-signals-013` + `-015`

**Their PLAN-TRUTH-001 D5b/D5c removal is CONFIRMED ACCEPTED** — this plan owns the derived cross-document
classification detector, and they keep D5a (correct the roster) + D5d (reconcile the five `SKILL.md`
sites). Recorded on both sides.

⛔⛔ **HARD SEQUENCING CONSTRAINT: `truthful-signals` PLAN-TRUTH-001 MUST LAND BEFORE THIS PLAN'S DETECTOR
WORK.** Both touch `dispatch-inline-split.md` — PLAN-TRUTH-001 *corrects the classification*, this plan
*builds the detector over it*. Building first means writing the test against the divergent state. This
plan's § (c) already says to verify the assertion FAILS against the divergent state first; that
ordering is what makes both work. ⚠ **STATUS as of 2026-07-30: PLAN-TRUTH-001 (their ex-`PLAN-113`,
re-issued in their own code-slug rename) is BLOCKED and cannot yet be emitted on their side** — their
RUNNING `PLAN-202` (`compose-time-subtractions-drop-steps-nobody-authorised`) is file-level disjoint
from it but concerns the same question of *which finalize steps run*, and PLAN-202's spec says to
sequence if either is in flight. So the blocker on this plan is real but is **not** a case of them
withholding: they cannot emit it. Re-check by NAMING their PR rather than by memory.

⭐ **THE TRAP, and it is the reason this warning is here rather than in the ledger.** The
`architecture-refresh` contradiction has now been shown to have a **RUNTIME consequence, not merely a
documentary one**: a retrospective independently logged it as a live **`dispatch_coverage_violation`** —
the plan ran the step inline (a leaf structurally *cannot* fire its `AskUserQuestion`) while the roster
classifies it dispatched, **so the audit recorded a violation for CORRECT behaviour.**

⛔ **A reader who "fixes" the audit to agree with the roster would be hard-coding the wrong answer.
THE ROSTER IS THE SIDE THAT IS WRONG.** Inline is correct on the merits — the binding mechanism is in
`architecture-refresh.md:26`, and classifying the step dispatched makes its documented Tier-1 prompt
mode unreachable.

**Corroboration count on the dual classification is now FOUR independent sightings** (this spec's
original, `end-phase-...-004`, their PLAN-110/#1061 in passing, and this runtime violation). ⚠ Four
sightings of **one** instance is still **not** a derived population — the D5b-equivalent obligation to
derive the full contradicting-step set stands unchanged.

⚠ **Cross-epic surface: PARTIALLY cleared, then re-occupied.** Their PLAN-112 did land (PR #1055,
`ad683c574`), which cleared *that* occupant. But as of 2026-07-30 their **PLAN-202 is RUNNING** and
concerns which finalize steps run, so the `phase-6-finalize` class is occupied on their side again —
and it is what blocks PLAN-TRUTH-001, which in turn blocks this plan's detector work. **PLAN-TRUTH-001
is the cross-epic occupant this plan sequences behind**, and the constraint above governs it.

⛔ **Do not read the earlier "CLEARED" as still true.** A cross-epic clearance is a snapshot, not a
state: the class was clear between PLAN-112 landing and PLAN-202 starting. Re-derive it from both
queues at emit time rather than trusting this paragraph.

## ⭐⭐ `[DISPATCH]` UNDERCOUNTS A LOOPING STEP 6:1 — folded 2026-08-09 from inbox `self-review-resweeps-full-surface-every-round-002`

**OBSERVED first-party on PR #1126**: `pre-submission-self-review` spawned **six** times and
emitted **one** `[DISPATCH]` work-log line (`00:37:14Z`); `project:finalize-step-plugin-doctor`
spawned **twice** and emitted **one**. Every spawn after the first is invisible in the canonical
dispatch trail.

The spawns are not in doubt — **two independent ledgers record them**: six
`[STATUS] (plan-marshall:execution-context.pre-submission-self-review) Complete` lines
(`00:47:36`, `01:07:11`, `01:18:36`, `01:29:11`, `01:44:39`, `01:56:26`), and six rows in
`work/metrics-dispatch-boundaries-6-finalize.toon` totalling **1,528,196 tokens**.

**Root cause**: the emission is wired to *first entry into a step*, not to the re-fire from the
resumable re-entry check. Every step that ran once is correctly instrumented; every step that
looped back is instrumented once regardless of how many times it actually spawned.

**Deliverable**: move the emission to the spawn site (or add one at the loop-back re-fire path)
so the `[DISPATCH]` count equals the spawn count. ⭐ `dispatch-logging.md` already specifies the
line shape — **only the placement is wrong**, so this is placement work, not contract work.

⛔ **Why this outranks bookkeeping**: `dispatch-logging.md` names `[DISPATCH]` lines as the
audit's primary evidence, and the execution-context dispatch audit's `shape_violation` check is
built on them. On #1126 the trail undercut the **single most expensive step 6:1** — a reader of
`work.log` alone sees one round at ~250K where the truth is six rounds at 1.53M.
⭐⭐ **The gap was detectable only because a SECOND ledger existed to contradict the first; on a
step with no dispatch-boundary rows it would be undetectable.** That is the standing
`[STEP]`-marker-count-is-a-FLOOR rule, now measured on the dispatch trail as well.

⚠ **Coordinate with `PLAN-CIS-037`**, which owns the `17 of 9` boundary-ledger arithmetic — this
undercount is a candidate contributing mechanism and CIS-037's D2 should rule it in or out.

### ⛔ SECOND SIGHTING, 2026-08-09 — the ratio varies, so a single plan's figure is not the defect's size

From PR #1127 (inbox `executor-rejects-invalid-invocations-before-spawn-002`): **4 of 13 dispatches
un-logged — 31%**, against #1126's **6:1 on a single step**. ⇒ ⭐ **Two independent plans, same
mechanism, materially different magnitudes.** The deliverable is unchanged; what changes is how it
must be reported: ⛔ **do NOT quote either ratio as "the" undercount** — the loss depends on how
many steps looped back and how often, which varies per run. **State the mechanism and publish the
per-plan population, never a single headline multiple.**

## Write-Boundary
Repository source + tests only; NO `.plan/local/orchestrator/` writes. See orchestration-model.md § Ledger Write-Boundary.
