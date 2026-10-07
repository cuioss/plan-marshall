# PLAN-CIS-031: Self-Review Re-Sweeps The Whole Surface Every Round At Flat Cost

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-03 from the PLAN-CIS-028 drain (inbox `…-011`), **first-party measurement of this
> epic's own run**. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and
> carries no brief.

## Objective

`pre-submission-self-review` re-runs a **full-surface sweep every round**, at a flat ~230K tokens
per round, regardless of how little moved since the previous round. On PLAN-CIS-028 that came to
**13 dispatches / 2,979,307 tokens = 56% of all 6-finalize tokens and 30% of the whole plan**, on a
26-file diff — while **nine of the 13 rounds followed an edit touching 1–3 files**.

Scope each re-run to the paths mutated since the previous round's recorded `head_at_completion`, and
reserve the full sweep for round 1 and the final confirmation round.

⛔ **This is a scoping change, NOT a reduction in review depth**, and the distinction is the whole
plan. See § "The loop is not wasteful; it is unscoped".

## Why this is ours, and why it is near the top of the queue

Operator directive 2026-08-02: **token reduction is Priority 1.** This is the single largest measured
consumer identified anywhere in the fleet so far — one step, 30% of a plan — with a mechanism that is
already understood and a remedy that is a bounded change to round mechanics. Routing test 2: it is
our own run's measurement, no PR/review-participation surface, so it is not `review-apparatus`'s.

⭐ **It does not wait on `PLAN-CIS-030`.** Its success test is structural and binary — *does round
N+1 sweep only the paths changed since round N's `head_at_completion`, yes or no?* Sizing the saving
needs L3; **doing it does not.** (Standing rule from the token-reduction directive: do not file every
lever behind the measurement plan.)

## The measurement (OBSERVED — first-party, PLAN-CIS-028 / PR #1080)

| Metric | Value |
|--------|------:|
| `pre-submission-self-review` dispatches | **13** (3 pre-loop-back-1, 5 post-loop-back-1, 4 post-loop-back-2) |
| Tokens attributable to those dispatches | **2,979,307** |
| Share of all 6-finalize tokens | **56%** |
| Share of the whole plan's tokens | **30%** |
| Findings filed | **19** |
| Tokens per finding | **~157,000** |
| Rounds that found nothing | **4 of 13** (~800K tokens spent proving termination) |
| Findings-per-round | `1,1,0 \| 3,3,1,1,0 \| 4,2,3,0` |

Whole-plan context: **10.4M tokens** for a **26-file** merged diff at `scope_estimate=single_module`
/ `change_type=bug_fix` — **7.7× the *error* anchor** for that row, and past the error anchor for
`complex+bug_fix` too. `6-finalize` (5.6M) **outspent** `5-execute`.

## ⭐ The loop is not wasteful; it is unscoped — the finding this plan must not be allowed to break

⛔ **Rounds 10–11 were worth the entire budget.** They caught two guards whose `clean: false` arm was
**structurally unreachable**, on a fully green test suite. Without them PR #1080 merges a fix that
can never fire, in a plan whose whole subject was steps running before their evidence exists.

⛔ **Rounds 5–7 were not.** ~690K tokens produced prose that was invalidated within two hours, and
the correction to the remediation *class* came from an **external reviewer**, not from the loop.

⇒ **The failure is not "too many rounds". It is that every round costs the same as round 1 no matter
how small the delta.** A plan that reduces round COUNT would delete rounds 10–11 along with 5–7. **Any
deliverable here must preserve late-round depth while removing repeated re-examination of unchanged
surface.** State this as an explicit anti-goal in the outline.

## The rework chain — 8 of 19 findings (42%)

1. Rounds 5–7 filed `1b2e2c` / `238d02` / `817d0f`, rewriting three doc sites to say the empty-tree
   guarantee rests on the `mutates_source` **declaration**, not a runtime check. **~690K tokens.**
2. CodeRabbit: *honesty is not the fix.* TASK-021 added the runtime guard those three sites had just
   finished asserting did not exist.
3. Round 9 filed `d5284d` / `ad17db`, stating it outright: *"the three sites were rewritten earlier
   this session and TASK-021 invalidated all of them."*
4. Round 10 filed `4f34d4` — TASK-021's guard bound to a worktree `branch-cleanup` deletes.
5. Round 11 filed `9c4eae` / `85aeb7` / `f34edf` — **three defects introduced by the fix for
   `4f34d4`**: a stale flag default, a stale anchor sentence, a stale ordinal cross-ref.

## Deliverables

1. **D1 — GATE: re-derive the per-round cost curve first-party (mutates nothing).** Confirm or refute
   the flat ~230K/round claim across the archived corpus, not just this one plan, and report the
   population size. ⛔ **Do not build round-scoping on a single plan's numbers** — that is exactly the
   sample-is-not-a-population error this epic keeps recording. If the curve is not flat, the remedy
   changes shape.
2. **D2 — scope the re-run to the delta.** Round N+1 examines only the paths mutated since round N's
   recorded `head_at_completion`; round 1 and the final confirmation round keep the full sweep.
   ~~⛔ `head_at_completion` is the enabling record and it is NOT reliably written … settle that the
   field is present before depending on it, or D2 silently degrades to a full sweep and the plan ships
   a no-op.~~

   ✅ **RE-GROUNDED 2026-08-08 AT EMIT TIME (the `next`-verb obligation under § Structural Findings F0).
   THE BLOCKING CONCERN IS NARROWER THAN THE LEDGER STATED, AND D2 IS NOT AT RISK OF SHIPPING A
   NO-OP.** Verified first-party:

   | Question | Answer | Evidence |
   |---|---|---|
   | Is the field written unconditionally? | **No — it is written only when the caller supplies the flag.** | `manage-status/scripts/_cmd_mark_step.py:330-331` — `if head_at_completion is not None: entry['head_at_completion'] = …`; `manage-status/SKILL.md:333` states the key is present only when the flag was supplied. |
   | Is supplying it mandatory for the step D2 depends on? | **YES.** | `phase-6-finalize/SKILL.md:545` — *every* head-dependent step MUST persist it on its terminal `--outcome done` call. |
   | Is `pre-submission-self-review` head-dependent? | **YES, and it carries its own explicit capture instruction.** | `phase-6-finalize/workflow/pre-submission-self-review.md:77` declares `head_dependent: true`; `:287-293` instructs capturing `git rev-parse HEAD` immediately before `mark-step-done` and forwarding it via `--head-at-completion {sha}`. |

   ⇒ ⛔ **The ledger's *"not reliably written"* caution came from a DIFFERENT step**: PLAN-CIS-028 paid a
   re-dispatch for a `lessons-housekeeping` record that omitted the flag. `lessons-housekeeping` is not
   `pre-submission-self-review`, and D2 depends only on the latter. **The caution was over-generalised
   from one step to the field.**

   ⭐ **What survives is a SHARPER risk, and D2 should own it rather than gate on it**: the field is
   **documented-mandatory but writer-optional** — the writer accepts an omission **silently**, so
   compliance rests on an LLM-driven step remembering a flag. ⇒ **D2's real deliverable is not "check
   the field exists" but "make its absence LOUD"**: a head-dependent step's terminal `done` record
   arriving without `head_at_completion` should fail rather than persist a record that reads complete.
   ⛔ **Do NOT let D2 degrade silently to a full sweep** — a silent degradation is precisely the
   confident-signal-hides-a-caveat archetype this epic exists to remove, reproduced inside its own fix.

   ⚠ **Boundary**: making the omission loud touches the `mark-step-done` handshake, which is
   `PLAN-CIS-011`'s D7 surface. **Coordinate — do not fix it twice**, and never pair the two plans.
3. **D3 — sweep the CLASS before closing a round.** When a round's findings share one discriminator,
   fix every member rather than one site per round. The item-5f porcelain claim was fixed **at one
   site per round for three rounds**. ⭐ The discriminators are **already machine-readable in the
   finding titles**, so this is a use of existing structure, not new metadata. This is the
   operational form of lesson `2026-08-03-06-002` applied to self-review's own output.
4. **D4 — report the detector mix per round.** A round whose findings are **all** doc-consistency is
   a signal about the **detector mix**, not about the code. On PLAN-CIS-028, **17 of 19** findings
   were prose/contract-consistency (`contract_drift`, `same_document_contradiction`,
   `description_body_drift`, `duplicate_prose`, `ordinal_reference_stale`) and only **2** structural
   (`unreachable_guard`) — **both appearing only after an external reviewer forced executable code
   into a 15-markdown-file changeset. Self-review filed ZERO of the two CodeRabbit Majors.** ⭐ A
   doc-heavy diff producing 17 prose findings and 0 structural ones **has not been reviewed for
   correctness; it has been proofread** — and *"214 candidates examined"* renders that as
   thoroughness. **Volume-read-as-coverage at the detector-mix level.**

⚠ **FIVE deliverables (D1 a gate), corrected 2026-08-08** — this line read *"Four deliverables"* while
D5 sat immediately below it, folded in on 2026-08-03 without the count being updated. Still below the
~6 split guard, so no split rationale is owed — but **a stale count in a spec is the same defect class
this epic files against everyone else**, and it is recorded rather than silently corrected.

## ⭐ D5 — the loop-back ceiling is a POST-HOC DETECTOR, not an admission gate (folded 2026-08-03, lesson `2026-08-03-14-001`)

**OBSERVED first-party on #1084**: the ceiling logged **`4 of max 3`** — *after* iteration 4 had
already spent **155K tokens**. ⇒ **It reports its own breach rather than preventing it.**

⭐ **This belongs here rather than in a new plan** because it is the same surface and the same
economics as D2: D2 makes each round cheaper, **this makes the round that should never have run not
run at all.** A ceiling that fires after the spend is a measurement, not a control.

**Deliverable**: the ceiling is evaluated at the **admission** boundary — before iteration N+1 is
dispatched — and a breach is refused, not recorded. ⛔ **This is NOT the anti-goal**: the ceiling
already exists and already declares the intended limit; enforcing a declared limit at its boundary is
not "examine less", it is making the existing declaration load-bearing. ⚠ If the outline finds the
ceiling's value is itself wrong, that is a separate operator question — **do not silently retune it
while making it enforceable.**

## ⭐⭐ D6 — THE BUILD GATE RE-RUNS IN FULL ON EVERY LOOP-BACK TOO (folded 2026-08-03, independent analysis of `plan-45`)

**The self-review dispatch is not the only thing this loop pays for, and the second consumer may be
the more expensive one in wall-clock.**

Measured on `plan-45-demo-client-doc-consolidation`: **six whole-tree Maven verifies — 5:11, 4:20,
5:16, 4:55, 6:23, 4:25 ≈ 30 minutes.** Six rather than one **because every loop-back re-ran the full
gate**: the self-review re-fire, two review rounds, and simplify.

⛔ **CORRECTED 2026-08-03, same day, by the filing agent — the first version of this fold said
SUPERLINEAR and named the wrong mechanism. Both are struck. Read the corrected version only.**

**It is LINEAR in loop-backs.** Mapped from `work.log`: **three gate executions × two Maven runs each,
≈10.5 min per execution** — one initial pre-push gate plus **two** loop-backs (a review-fix re-entry
at `HEAD=6d1654c`, and a self-review re-fire that caught `contract_drift`). ⇒ **Two loop-backs added
≈21 minutes.** Linear, not superlinear.

⭐ **And the constant factor of 2 is NOT waste** — it is the project's mandated two-command Pre-Commit
Process: one run under `-Ppre-commit` invoking `maven-javadoc-plugin` and building javadoc jars, one
plain `verify`. **Do not target it.**

### ⭐⭐ The real mechanism, and it is better than the one it replaces

⛔ **The resolver is NOT at fault and is not even involved.** `.plan/marshal.json`'s `build.map` is a
glob→build_class table (`*/src/main/*.java`→`compile`, `*/src/test/*.java`→`module-tests`,
`pom.xml`→`verify`) applied to the **actual diff** — so module selection **is** footprint-derived, and
the 1.5s/18.4s runs are evidence it **is wired and ran**, on the phase-5 per-deliverable path.
⇒ **The earlier "unestablished" flag is settled, in the direction that the machinery works.**

⭐⭐ **The six expensive runs never touched that machinery at all.** They are
`default:pre-push-quality-gate` — a **whole-tree** step building `[1/5]…[5/5]` every time, which
**does not consult the footprint** and **would have run identically on a pure `.adoc` change.** The
javadoc line and the `pom.xml` comment are **irrelevant to it.**

⇒ ⛔ **There are TWO build paths and the expensive one is the blind one.** The per-deliverable path is
footprint-aware and cheap; the pre-push gate is footprint-blind and whole-tree. **The earlier framing
— "which modules a one-line comment change selects" — was wrong: the gate selects nothing.**

**Deliverable, restated:**
1. **Let the whole-tree pre-push gate consult the same `build.map` classification the per-deliverable
   path already uses.** ⭐ The mechanism exists and is proven — this is wiring an existing classifier
   to a second consumer, **not** building scoping.
2. **Settle whether the gate must re-run in FULL after a loop-back whose diff is documentation-only.**

⛔ **Anti-goal unchanged**: *build less often* and *skip the gate on small diffs* are examination cuts
wearing this plan's clothes. **The target is re-running work already done on unchanged surface** —
and here, specifically, running a five-module build for a diff the project's own classifier would
score as needing none of it.

## Claim Labels

- **OBSERVED (first-party, PLAN-CIS-028 / #1080)**: every figure in the measurement table, the
  13-round sequence, the 8-of-19 rework chain, and the 17/2 detector split.
- **HYPOTHESIS**: that the ~230K flat per-round cost generalises beyond this plan. **D1 is this
  verification** (verify-at-outline).
- **HYPOTHESIS**: that `head_at_completion` is recorded reliably enough to key D2's delta on.
  ⛔ **Actively suspected FALSE** — one measured omission already forced a re-dispatch on this very
  run. Confirm/refute against the archived corpus (verify-at-outline).
- **OBSERVED (first-party)**: `scope_estimate=single_module` was **two bands low** on this plan, and
  it is a live input to the `scope_gated_finalize` pre-filter, which **attempted to drop
  `plan-marshall:plan-retrospective` from this plan's own manifest** — on the run that produced 19
  self-review findings and two near-miss vacuous guards. It survived **only on declared-lane
  immunity**. ⚠ Related to `PLAN-CIS-008`; **do not absorb it here** — record it and route it.

## Expected Surface

- **HYPOTHESIS**: `phase-6-finalize` `pre-submission-self-review` round mechanics (verify-at-outline)
- **HYPOTHESIS**: `pm-plugin-development:ext-self-review-plan-marshall` — the detector mix and the
  class-sweep behaviour (verify-at-outline). ⚠ **Different bundle** — confirm ownership via
  `architecture which-module` before scoping, and check whether it takes the work out of this repo's
  hands.
- **HYPOTHESIS**: the `head_at_completion` producer in `manage-status mark-step-done`
  (verify-at-outline) — shared with `PLAN-CIS-011` D7, **so never pair these two**.

## Dependencies and Sequencing

- **Depends on**: nothing. Wave-1 eligible.
- ⛔ **Never pair with `PLAN-CIS-011`** — both land on `mark-step-done` / `head_at_completion`.
- **Adjacent to `PLAN-CIS-030`**: CIS-031 is a lever, CIS-030 is the instrument. They are
  independent; do not sequence one behind the other. **CIS-031 must not claim a token saving** —
  that claim is CIS-030's to enable.
- **Adjacent to `PLAN-CIS-008`** (`scope_estimate` vocabulary) via the two-bands-low observation.

## Anti-goals

- ⛔ **Do not reduce round count as such.** See § "The loop is not wasteful; it is unscoped".
- ⛔ **Do not quantify a saving.** Report shares of measured spend, never projected reductions.
- ⛔ **Do not weaken the termination criterion.** The 4 zero-finding rounds are how the loop proves it
  converged; the target is their **cost**, not their existence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-031-self-review-resweeps-full-surface-every-round.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
