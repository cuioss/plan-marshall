# PLAN-TRUTH-051: the inbox emission must be the plan's terminal action

## ⛔⛔ SUPERSEDED 2026-08-03 — ABSORBED INTO `PLAN-TRUTH-050`. DO NOT EMIT.

**Operator decision: "no split".** The what/when/where of the plan's terminal report are one seam, and
splitting a seam is how this codebase produces half-fixes (#1080 closed write-before-merge and left
write-before-terminus; a renumber without a contract would re-accrete).

⇒ **All content below is retained as the evidence record and is live inside**
`PLAN-TRUTH-050-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see.md`
(**D4-D5, Phase 2**). ⚠ **Read 050, not this file, before implementing.**

---

epic: truthful-signals
workstream: WS-01

⭐⭐ **OPERATOR DIRECTIVE, 2026-08-03**: *"The last inbox post must be the last action of the plan.
Eventually we formalize this with a dedicated step that is only active if a plan is run in an
orchestrator context."* ⇒ **The design is decided. This plan implements it; it does not re-open it.**

## OBSERVED — the current order, read first-party from `_manifest_core.py`

`DEFAULT_PHASE_6_STEPS`, ascending, with the frontmatter `order` the composer and dispatcher both read:

| Step | `order` | What it produces that the landing cannot see |
|---|---:|---|
| `branch-cleanup` | **70** | the merge SHA, the merge outcome |
| **`lessons-capture`** | **991** | ← **the `kind: landing` emission happens HERE** |
| `record-metrics` | **998** | the run's token totals |
| `archive-plan` | **1000** | the archive path |

⇒ **The landing is written 3 steps and 2 producers before the run ends.** ⛔ Everything `PLAN-TRUTH-035`
found about totals follows mechanically: the landing physically cannot carry a figure that does not
exist yet.

⭐ **`archive-plan` (1000) is the hard boundary**, and the source says why in as many words: *"It runs
last because it moves the plan directory out from under every later reader."*

### ⛔⛔ AND THERE IS NO SLOT. Correcting a claim I made an hour ago.

I wrote that the terminal slot is *"between 998 and 1000"*. **A full sweep of every declared `order:`
refutes it: `999` is occupied by `finalize-step-print-phase-breakdown`.**

**The post-run band, complete:** `990, 991, 992, 995, 998, 999, 1000`. ⇒ **`998 → 999 → 1000` is
contiguous. At integer granularity the terminal region is SATURATED and the step cannot be inserted at
all.**

⛔ **I asserted a free slot from the four steps I had already read, without enumerating the space** —
the *a list produced by looking is a sample, not an enumeration* archetype, in the same drain where I
folded two fresh instances of it into `PLAN-TRUTH-012`. **Third instance of that class by me this
session.**

⇒ **D1 is BLOCKED on `PLAN-TRUTH-052`** (renumbering), or it must displace an existing step — which is
a decision, not an implementation detail. ⭐ **The operator's "we should adapt numbering, we are still
pre 1.0" is therefore not a nice-to-have: it is this plan's precondition.**

## ⛔⛔ MY OWN RETIREMENT OF `PLAN-TRUTH-037` WAS OVER-BROAD — owning it here

`PLAN-TRUTH-037` D1 said exactly this: *"the landing message becomes a terminal action, anchored on the
plan's terminal state, not on the merge."* **I retired it as `superseded` on 2026-08-03** because
`PLAN-CIS-028` (#1080) moved `lessons-capture` into a post-merge band at `order: 991`.

⛔ **That closed the WRITE-BEFORE-MERGE defect and left the WRITE-BEFORE-TERMINUS defect open.**
*Post-merge is not terminal.* 991 < 998 < 1000.

⭐⭐ **And I had the disproving fact in hand.** In the **same drain** I recorded, for `PLAN-TRUTH-035`,
that *"`plan-retrospective` = 995, `record-metrics` = 998 ⇒ 995 < 998"* — then failed to run the identical
comparison on the step whose retirement I was signing off. ⇒ **A retirement justified by a sibling's
evidence still needs the retiring epic's own arithmetic.**

⚠ **`PLAN-TRUTH-037` stays `superseded` — history is not rewritten.** Its live residue is **this plan**.
The retirement note in 037 already flags that the metrics half did not close; **this is that residue
promoted from a footnote to a deliverable, at the operator's direction.**

## Deliverables

1. **D0 — GATE: derive what a terminal emission can carry that today's cannot.** Enumerate every fact
   produced by steps at `order > 991`, and every field of the current landing envelope. ⛔ **Both
   directions**: facts the landing wants and cannot have, AND facts it currently asserts that it is not
   yet entitled to. ⭐ **The second direction is the one that bites** — a message emitted early does not
   merely omit, it **claims**. `PLAN-TRUTH-010`'s landing asserted a PR number that was never merged.
2. **D1 — a dedicated terminal step, ordered between `record-metrics` (998) and `archive-plan` (1000).**
   ⛔ **`archive-plan` must stay last** — it moves the plan directory, and every earlier reader depends
   on that. ⚠ **Do NOT relocate `lessons-capture`**: its *lesson* work is legitimately mid-band; it is
   the **emission** that must move. ⭐ **Separate the two concerns rather than moving one step later** —
   moving it wholesale is how the read-direction defect was created in the first place (a step relocated
   past the worktree it needed).
3. **D2 — the step exists ONLY under an orchestrator, and the detector already exists.**
   ⭐ **`orchestrator inbox detect --source-id` is the single sanctioned seam** — it classifies a plan's
   persisted `source_id` as orchestrated and returns `epic` + `plan_spec`. ⛔ **Do NOT add a second
   detector or a new persisted metadata field**; that skill's contract says so explicitly, and a second
   detector is how two producers over one field happen (see `PLAN-TRUTH-049`). A non-orchestrated plan
   composes the step **out**, and that must be an **observable compose-time decision**, not a silent
   no-op at runtime — a step that runs and does nothing is indistinguishable from a step that was
   skipped.
4. **D3 — the emission carries the terminal facts, machine-readable.** Consume `PLAN-TRUTH-031`'s
   (#1076) typed `facts` map rather than re-narrating it. ⛔ **This is the same deliverable
   `PLAN-TRUTH-050` D1 describes** — see Sequencing; **one of the two implements it and the other cites
   it.**
5. **D4 — a test that FAILS pre-fix.** Assert the emission's order is **greater than the order of every
   step whose facts the envelope carries**. ⭐ **This is `PLAN-TRUTH-037` D4 verbatim, and it was never
   built** — it must be verified to fail against the current 991 ordering, or the plan has re-shipped
   the same unenforced intention.
6. **D5 — reconcile the four restatements of the pipeline order.** `_manifest_core.py`'s tuple, each
   step doc's frontmatter `order`, `phase-6-finalize` SKILL.md's dispatch table, and
   `manage-config list-finalize-steps`. ⭐ The source already pins the first three in lock-step via
   `TestDefaultPhase6StepsMatchesDiscovery`; **a new step must land inside that pin, not beside it.**
   ⚠ **Low-risk but non-optional** — an unpinned addition is a fifth statement of the order.

⚠ Six deliverables, at the bloat threshold. Split evaluated: **D5 is the split point** (a pinning chore).
Kept because a new step that misses the lock-step pin is the failure mode D5 exists to prevent, and it is
cheapest to satisfy in the same change. ⭐ Rationale recorded **at staging**, per the standing correction.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, read from source)**: the four orders (70 / 991 / 998 /
  1000), the `DEFAULT_PHASE_6_STEPS` tuple, the stated reason `archive-plan` runs last, and the
  lock-step pin test. Re-derivable via `manage-config list-finalize-steps` — ⛔ **the source itself says
  resolve live values that way rather than sorting from memory; do it at D0.**
- **OBSERVED**: `PLAN-TRUTH-010`'s landing asserting the wrong PR; `PLAN-TRUTH-035`'s three-totals
  disagreement; the 995 < 998 finding — all this epic's own records.
- **OPERATOR DIRECTIVE (not a hypothesis to test)**: that the last inbox post is the plan's last action,
  and that the step is orchestrator-context-only.
- **HYPOTHESIS**: `inbox detect` is sufficient to gate composition. ⚠ It is documented as the single
  detection seam, but **it classifies a `source_id`, and whether that value is available at COMPOSE time
  (not just at runtime) is unverified.** ⛔ **Confirm at D0** — if it is only available later, D2's
  "compose the step out" shape changes to a runtime gate, and the observability requirement becomes
  harder, not easier.
- **HYPOTHESIS**: no producer runs after 998 other than `archive-plan`. ⚠ **An asserted absence, derived
  from the DEFAULT tuple** — composed manifests add steps. **Verify against a composed manifest**, not
  against the defaults.

## Expected Surface

- **OBSERVED**: `manage-execution-manifest/scripts/_manifest_core.py` — `DEFAULT_PHASE_6_STEPS`
- **OBSERVED**: `marshall-orchestrator/scripts/orchestrator.py` — `inbox detect`, `inbox write`
- **HYPOTHESIS**: `phase-6-finalize/` — the new step doc, its `order`/`post_run_review` frontmatter, the SKILL.md dispatch table
- **HYPOTHESIS**: `phase-6-finalize/workflow/lessons-capture.md` — where the emission is today
- **HYPOTHESIS**: `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — the lock-step pin

## Dependencies and Sequencing

- ⛔⛔ **STRONG OVERLAP with `PLAN-TRUTH-050`** (the operator report is an evidence surface the inbox
  cannot see). **They are the same fix from two ends**: 050 asks *what the landing should carry*, this
  asks *when it may be written*. ⭐ **050's D2 was a COMPROMISE** — carry a `total_at:` sampling marker
  because the final total was unavailable at 991. ⇒ **This plan removes the reason for that compromise.**
  ⛔ **Decide at outline: MERGE them, or 051 lands first and 050 narrows to the delta.** Do not implement
  both D3s.
- ⚠ **Cross-epic: `PLAN-CIS-034` owns the band contract** (whether a `mutates_source: true` step may be
  post-run). A new post-run step must satisfy it. **Notify before implementing; do not edit the band
  contract from this epic.**
- ⚠ `PLAN-TRUTH-035` is **RUNNING** and owns the totals' sampling point. **Surface-adjacent. SERIALIZE.**
- ⚠ `PLAN-TRUTH-032` (inbox protocol / quiescence) — ⭐ **a terminal emission step IS a termination
  signal by construction.** **Evaluate absorption at outline.**
- ⚠ `PLAN-TRUTH-038` (no amend/supersede verb) — **a terminal emission substantially reduces the need
  for one.** Re-evaluate 038's priority after this lands.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-051-the-inbox-emission-must-be-the-plans-terminal-action.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — ⭐ which
this plan is, by its own subject matter, the step that emits. Qualifiers are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
