> ⛔ **STAGED AT THE 2026-08-22 INGESTION — this plan closes REMEDIATION RESIDUE.**
>
> It exists because the gap-fix plans `500`/`510`/`520` ran **after** the epic audit closed, so every
> gap they filed, and every gap they left partially closed, is owned by no other staged plan. This was
> found by re-deriving ownership over the whole live gap set at ingestion: **218 gaps open, 38 unowned.**
>
> **Re-ground every gap below at HEAD before implementing it.** Its source is
> `cloud-runs/{NNN}-{slug}/gaps.md` in this ledger (git-ignored, ingested from `doc/plans/`), and a
> gap document is a snapshot. Line numbers in it are **leads, not addresses**; locate by quoted text.
> A gap that no longer reproduces is recorded as *already closed by `{sha}`* and **dropped, never
> re-fixed**.
>
> ⛔ **A run report is a dated record.** No deliverable here corrects one. Where a gap's `Where` names
> an archived `report-01.md`, the correction of record is the gap entry itself; only a live restatement
> is actionable, and it must be re-derived.

# The dispatch contract is enforced at one surface of three, and two gates were never opened

**Epic:** truthful-signals
**Branch prefix:** fix
**Source gaps:** `260/G1 G2 G3 G6 G7`, `280/G2 G4 G7`, `160/G4`, `230/G1 G4`, `440/G4` — the original-corpus gaps left unowned once `500`/`510`/`520` executed

## Objective

Enforce the dispatch contract where it is declared, carry the emission seam to every dispatch site, and
open the two measurement gates on a machine that can open them. The request narrative is § Problem
together with § Goal below, and they are not restated here. ⚠ Read the 2026-09-05 SPLIT-GUARD NOTICE at
the end of this spec before outlining. *(Section added at the 2026-09-11 `cleanup` as a pointer.)*

## Problem

Twelve gaps from the original corpus have **no owning plan**. They are not new: they are what remained
after the three gap-fix plans ran, either because a remediation closed a gap only partially or because
the plan that owned them was executed and its residue was never re-homed. Re-derived at the 2026-08-22
ingestion over the whole live set: **218 gaps open, 38 unowned**, of which these twelve are the
original-corpus share.

Two clusters and two orphans:

**The dispatch declaration surface (`260`).** D2 of plan `260` added a **third** declaration surface and
linked two of three. The input-table `Required: Yes` row that `ext-point-finalize-step.md` itself names
as the declaration surface **is read by nothing**, so the original defect still reproduces verbatim for
**24 of 26** steps.

**The dispatch audit rollout (`280`).** The emission seam is correct and per-firing, but only **6 of 22**
dispatch sites use it — and the same commit that left 11 hand-written `[DISPATCH]` blocks rewrote the
standard to call that shape forbidden, with `planning.md:275` still instructing it *and citing the
forbidding section as its authority*. `280/G2` is additionally unmet at `planning.md:233`, a
zero-emission site plan `510`'s Out-of-scope excludes **by name**.

**Two gates that could not be opened from a cloud clone** (`230/G4`, `440/G4`) need a local run with
`.plan/` state present. `160/G4` and `230/G1` are single live doc/behaviour defects with no owner.

## Goal

The dispatch contract is enforced where it is declared, the emission seam reaches every dispatch site,
and the two measurement gates are opened on a machine that can open them.

## Deliverables

**D0 — GATE: derive the dispatch-site population and the declaration surfaces.** Enumerate every
dispatch site and every surface on which a step-specific mandatory field can be declared. Publish
sites-total, sites-on-the-seam, and surfaces-read-by-a-guard. *(gates D1–D5.)*

**D1 — the declared surface is the read surface.** *(closes 260/G1, 260/G2)*
Bind the input-table `Required: Yes` row to the conformance guard, or retire it as a declaration
surface and say so. Prove with a matched control over a step that declares only there.

**D2 — retire the three fields that violate the mandatory-declaration rule.** *(closes 260/G3, 260/G7)*
`iteration`, `producer`, `session_id` already violate it; `caller_phase` is a documented contract field
the guard would flag as step-specific.

**D3 — complete the `[DISPATCH]` seam rollout and retire the forbidden shape.** *(closes 280/G2, 280/G7)*
9 hand-written blocks across 5 dispatch-site files remain, and the orchestrator lane's canonical
dispatch form emits on neither surface. ⛔ **`planning.md:275` instructs the forbidden shape while citing
the section that forbids it** — fix that first; it is actively teaching the defect.

**D4 — the two finalize doc-echoes describe a step that no longer exists.** *(closes 280/G4, 260/G6)*

**D5 — a degraded module-tests run gets a DEGRADED display detail.** *(closes 160/G4)*

**D6 — `push.md` stops naming `lessons-capture` as `mutates_source: true`.** *(closes 230/G1)*
False since #1080. ⚠ The re-stale discriminator has **two** conjuncts (`mutates_source: true` AND
`order >` the build producer) and no test derives that membership from frontmatter — derive it.

**D7 — LOCAL GATE: open the two measurement gates.** *(closes 230/G4, 440/G4)*
Both need `.plan/` state a cloud clone does not have: `230/D0`'s archived CI-manifest corpus, and
`440/D4`'s before/after re-fire measurement on a real finalize. **This plan must run locally.** If a
gate still cannot be opened, record *could not look* with the reason — never a zero.

**DA — a dispatch that skips its dispatcher-owned Step 1 is refused by the leaf, at full cost.** *(folded 2026-08-23 from PR #1330 / § 5 correction 4)*
`pre-submission-self-review` was dispatched WITHOUT running its dispatcher-owned Step 1, so the leaf
refused for a missing `candidates` field — **107,533 tokens on a dispatch that produced nothing**. The
leaf was RIGHT to refuse; the defect is that the dispatcher can omit a mandatory precondition and still
spend a full envelope discovering it.
⭐ Context that makes this worth fixing rather than filing as operator error: the same step in the same
run cost **478,113 tokens across three firings** and returned *"self-review clean: 7 candidates
examined, no check matched"* — zero findings on a six-file change. The 107,533-token refusal is 22 % of
that, spent before any work began.
**Remedy direction:** make the precondition checkable BEFORE the envelope is spent — either the
dispatcher validates the required field at compose time, or the prompt-body contract makes the missing
field a compose-time rejection rather than a leaf-time refusal.
⚠ Related but DISTINCT from the `(d)`/`(e)` envelope-shape work already in this spec: this is about a
mandatory field's ABSENCE being detected only after dispatch, not about the field's shape.

**DB — declare `verdict_inputs` on the head-dependent finalize steps that are SILENT — and do NOT
"fix" the two that already refused.** *(folded 2026-08-23 from PR #1332 / L1 — diagnosis CORROBORATED, remedy MATERIALLY CORRECTED first-party)*

**The diagnosis holds.** A head-dependent finalize step that declares no `verdict_inputs` surface is
invalidated on ANY HEAD advance, whether or not the advance touched anything its verdict depends on, so a
single loop-back re-runs the whole settle band. The source run recorded the classifier preserving
`era-stamp-fill` (`disjoint_from_verdict_inputs`) while invalidating seven others for
`verdict_inputs_undeclared` — *not because they were stale, but because they never said what would make
them stale.* Firing counts after two loop-backs: `pre-submission-self-review` 7, `pre-push-quality-gate` 5,
`plugin-doctor` 3, `lessons-housekeeping` / `finalize-step-simplify` / `ci-verify` / `automatic-review` 2,
`era-stamp-fill` **1**. Their cost figure — **~1,585,514 tokens, 44.9 % of finalize and 26.2 % of the whole
plan**, against `5-execute`'s 1,408,809 — is THEIR machine's ledger and was not reproduced here; carry it
as a lead, and re-derive before quoting it.

⛔⛔ **THE REPORT'S REMEDY SCOPE IS WRONG, AND NAIVELY APPLYING IT WOULD UNDO A RECORDED DECISION.** It
calls for declarations on "the 15 head-dependent finalize steps that lack it" and gives three concrete
starting points. **Enumerated first-party at HEAD, the population is 9, not 16:**

| `verdict_inputs` status | Steps |
|---|---|
| **DECLARES** (1) | `finalize-step-era-stamp-fill` |
| **REFUSED ON RECORD** (2) | `pre-push-quality-gate`, `finalize-step-plugin-doctor` |
| **SILENT — the real target set** (6) | `ci-verify`, `finalize-step-security-audit`, `finalize-step-simplify`, `branch-cleanup`, `finalize-step-review-retrospective`, `finalize-step-lessons-housekeeping` |

⛔ **Two of the report's three named starting points are in the REFUSED column, and both files anticipate
exactly the reasoning it uses:**
- `pre-push-quality-gate.md:326` — *"This gate declares **no** `verdict_inputs` … The absence is a
  **recorded refusal on evidence**, not an obligation left unwritten — and it is recorded here because the
  refusal is easy to mistake for an oversight **and easy to 'fix' wrongly**."*
- `finalize-step-plugin-doctor/SKILL.md:50` — *"…a **recorded refusal on evidence** … recorded because this
  step **looks like the obvious candidate** for a declaration — its `--paths` scope is derived from two
  skill roots, so `marketplace/*` plus `.claude/*` reads like the whole story. **It is not.**"*
  The report proposes precisely `marketplace/bundles/**` plus the doctor's rule set.

⇒ **D0 of this deliverable is to READ BOTH REFUSALS FIRST.** Either they still hold — in which case the
two are out of scope and the corrected target set is the **six silent steps** — or the refusal's stated
evidence has expired at HEAD, in which case **overturn it explicitly, in the file, naming what changed.**
⛔ Never silently add a declaration to a step carrying a recorded refusal. Only `ci-verify` of the
report's three suggestions is in the silent set; its proposed input ("the pushed HEAD only — an advance
that has not been pushed cannot change what CI saw") is sound and is the natural first declaration.
⭐ **The mechanism needs no new code** — `ext-point-finalize-step` already carries the declaration point,
the classifier already consumes it, and `era-stamp-fill` proves the path end to end.

**DC — a self-review round may FILE only on checked evidence but may DISMISS on any premise it likes.** *(folded 2026-08-23 from PR #1332 / L12)*
Round 7 independently detected the canonical-key collision a review bot also raised, then declined it on
the premise that the collapse was *"the module's existing identity model applied uniformly"* — i.e.
pre-existing. **The premise was false and one command refutes it:**
`git show {base}^:…/_list_providers.py` shows the pre-PR body building a **list**, where no key exists to
collide on. The plan's own triage reversed the reasoning and carried the defect as a residual.
⭐ **The asymmetry is the defect, and it is exactly backwards.**
`pre-submission-self-review.md` already binds two evidence obligations on **asserting** — the absence-claim
scope rule and the present-state grounding precondition — and a whole-document search for
`pre-existing` / `dismiss` returns **nothing**. A round may file only on confirmed present-state evidence
and dismiss on anything.
**Remedy: a provenance-grounding precondition on the DISMISSAL side.** When a round declines a candidate as
pre-existing, it MUST first read the same construct from the base ref (`git show {base_ref}:{path}`) and
confirm the behaviour is there; if the base-ref read does not show it, the candidate is a regression this
change introduced and the round MUST file it; and the dismissal ground is recorded in the round's output.
⭐ *"A dismissal that names no checkable premise is not a disposition, it is a silence."* The base ref is
already threaded through Step 1 (`--since-ref` / `head_at_completion`), so the input is in hand.
⚠ Failure class is invisible by construction — a dismissed candidate leaves no finding. Here a bot caught
it; on a run where the bot is quiet or its budget is spent, nothing does.

**DD — `plan-retrospective` runs BEFORE the `enrich` that would populate what it reports on.** *(folded 2026-08-23 from PR #1332 / L13 — CORROBORATED, with two corrections)*
`manage-metrics enrich` recovers the four raw `message.usage` fields and derives `billing_weighted_total`.
It **is** called at finalize by `default:record-metrics`. The defect is the ORDERING: the retrospective
runs first, so it reads a pre-enrichment ledger and reports the four-field view as empty on every plan.
Same run, both vantage points: retrospective observed `totals_billing_weighted_total: 0` /
`population_count: 0`; `record-metrics` then returned `enriched: true, message_count: 837,
subagent_calls_attributed: 37` and `generate` produced `total_billing_weighted: 133692078`.
⚠ **Correction 1 — the order number.** The report says the retrospective is `order: 990`. At HEAD it is
**`order: 995`** (`plan-retrospective/SKILL.md:12`); `record-metrics` is `998`. The relation the lesson
turns on is unchanged, but do not key a fix on `990`.
⛔ **Correction 2 — the ordering that produces the defect is DELIBERATE and LOAD-BEARING. Do not "fix" it
by moving `record-metrics` or the retrospective.** `record-metrics.md:37` states it **MUST be the LAST
token-accounting step**, running AFTER `plan-retrospective` and `lessons-housekeeping`, because *"This
ordering is what lets `end-phase` fold the token spend of every dispatched finalize step — including
retrospective and lessons-housekeeping — into the closed `6-finalize` phase row."* Moving either breaks the
accumulator fold.
⇒ **The report's shape 1 is compatible and is the right one:** add an EARLIER, cheap `enrich` before the
retrospective reads (its own Step 2.5 is the natural site), leaving `record-metrics`' `enrich` as an
idempotent refresh over the later steps' spend. Shape 2 (have the retrospective state that it runs
pre-enrichment, so an unenriched ledger is not reported as an absent capability) is the minimum honesty
requirement if shape 1 is rejected.
⚠ Still open and separate: the finalize dispatcher parses each returned `<usage>` envelope but calls
`record-dispatch-boundary` without the four context-load flags, so all per-dispatch rows carry the literal
`unmeasured`. Same family as PLAN-TRUTH-089 DB.

**DE — propagate the DELTA ANCHOR to the settle-band steps that re-fire without one.** *(2026-08-23, operator question: on a SECOND finalize after a review-driven fix, are `simplify` / `architecture-refresh` / `pre-submission-self-review` / `plugin-doctor` beneficial at all? Answered first-party per step.)*

⭐ **The answer is not "drop them". THREE INDEPENDENT MECHANISMS govern a re-fire and only ONE step
implements all of them.** Naming them apart is the whole of this deliverable:
1. **`verdict_inputs`** — *should this step re-fire at all?* (DB above; 1 of 9 declares)
2. **Delta anchor** — *when it does re-fire, over WHAT?* (this deliverable; **1 of 4 implements it**)
3. **Skip-clean / no-op** — *can it exit early?* (input-side or output-side, varies)

**Per-step verdict on a loop-back whose only delta is the fix commits, enumerated at HEAD:**

| Step | Scoped to | Verdict |
|---|---|---|
| `pre-submission-self-review` | **THE DELTA** — reads its own prior `head_at_completion` and passes `--since-ref`, narrowing the surfaced set to footprint ∩ paths changed since that SHA (10 `--since-ref` uses) | ✅ **KEEP — the highest-value step on a second finalize.** It is the ONLY check that examines the fix commits themselves. |
| `finalize-step-simplify` | **THE WHOLE PLAN CHANGESET** — `--since-ref` appears **0 times**. It records `head_at_completion` and re-fires on it, but uses it ONLY as a re-entry trigger, never as a scope narrower | ⚠ **Re-simplifies lines it already simplified.** Legitimate work exists (the fix IS new unsimplified code) but it is a fraction of what the step re-examines. |
| `finalize-step-plugin-doctor` | **THE PLAN FOOTPRINT** — `--paths` from `affected_files` skill dirs; whole-tree on the F1 rule-change trigger or an indeterminate read; **skip-clean exit when the plan touched no skill** | ⚠ **Cheap when the fix touches no skill, legitimate when it does** — but it re-lints every skill the PLAN touched, not the ones the FIX touched. |
| `architecture-refresh` | **NOTHING** — no delta scoping of any kind; its only early exit is the `3d. Non-empty status` branch, i.e. it re-runs the derivation and then declines to COMMIT | ⛔ **Weakest case of the four.** Its no-op is on the OUTPUT side, so the derivation cost is paid before it discovers there was nothing to do. |

⇒ **`pre-submission-self-review` IS THE MODEL AND ITS CONTRACT IS ALREADY WRITTEN** — including the part
that makes it enforceable: `mark-step-done` returns `error: missing_head_at_completion` and **writes
nothing** when a `head_dependent: true` step records `done` without the anchor, because *"an unanchored
record would leave the following round unable to define its delta, silently degrading it to a full
re-sweep."* Three steps record that same field and none of the other three narrows on it.

**Deliverable:**
1. **`finalize-step-simplify` adopts the anchor.** Read its own prior `head_at_completion`, pass a
   `--since-ref`-equivalent, and bound the simplification pass to the lines changed since that SHA rather
   than to the whole plan changeset. ⚠ Preserve the existing line-level `changeset` boundary — this NARROWS
   it, never widens it, and the `artifact` scope keeps today's behaviour.
2. **`finalize-step-plugin-doctor`: evaluate, do not assume.** Narrowing `--paths` to the skills the FIX
   touched is attractive but may be unsound — the step already documents that a scoped run *"structurally
   cannot evaluate plugin-doctor's cross-skill rules"* and emits a divergence WARNING for exactly that. ⛔
   Settle whether a delta-scoped run widens that existing blind spot BEFORE narrowing; if it does, the
   correct answer is to leave it footprint-scoped and say so.
3. **`architecture-refresh`: move the no-op to the INPUT side.** Decide from the delta whether any
   architecture-relevant path changed, and skip the derivation entirely when none did — instead of deriving
   and then declining to commit. ⚠ Coordinate with **PLAN-TRUTH-095 D6** (its order-10 push defect); same
   file, two defects, one edit window.
4. ⛔ **Do NOT drop `pre-submission-self-review` from the re-fire set.** §11.6 of the source report is
   first-party evidence for keeping it: on PR #1335 the FIRST fix commit — written to fix a bot-surfaced
   defect — **introduced a new falsehood**, and CI, CodeRabbit and PR Agent were all green on it. The
   second finalize is exactly where a fix's own defects surface.

⭐ **Expected effect, and why it beats collapsing the band:** DB decides WHICH steps re-fire; DE decides HOW
MUCH each re-examines when it does. Together they make a second finalize proportional to the fix rather
than to the plan — which preserves every gate's safety value. **Collapsing the band removes gates to buy
the same saving.**

**DF — make the loop-back re-fire a DECLARED, operator-overridable property — as a three-valued SCOPE,
not a boolean.** *(2026-08-23, operator proposal: "add a new property for the finalize API: `run-on-loop-back`, so it is a configuration aspect". Evaluated against the shipped frontmatter surface and ADOPTED with a corrected shape.)*

⛔ **A boolean `run-on-loop-back` would DUPLICATE `head_dependent` and create a second source that can
disagree with it.** `ext-point-finalize-step.md:43` already defines `head_dependent: true` as *"the step's
verdict is computed against a specific worktree HEAD"* and states that **"the dispatcher's re-entry check
re-fires the step when HEAD has advanced (a loop-back commit, a force-push, or a rebase)."* So *whether a
step runs on loop-back is already declared* — a parallel boolean would be a second producer of one fact,
this epic's most-recorded archetype.

⭐ **BUT THE PROPOSAL IS RIGHT THAT SOMETHING IS MISSING, AND IT NAMES THE RIGHT LAYER.** Two gaps the
existing pair genuinely does not express:
1. **`head_dependent` conflates a FACT with a POLICY.** Its discriminator — *"would this verdict change if
   HEAD changed?"* — is a **truth about the step**. The dispatcher then applies one fixed **policy**:
   re-fire. A step cannot say *"my verdict is head-dependent, and re-running me for THIS fix is still not
   worth it"* (the `architecture-refresh` case — derived state that a small fix rarely moves).
2. **Neither field expresses SCOPE.** `head_dependent` × `verdict_inputs` answer **whether** to re-fire.
   Nothing answers **over how much** — which is DE's finding: `pre-submission-self-review` narrows to its
   own `head_at_completion` delta and the other three re-examine the whole plan footprint.

⇒ **Adopt the proposal as ONE field carrying the scope, which subsumes the boolean:**

```yaml
loop_back_scope: full | delta | skip     # optional; absence ⇒ full (fail-closed, today's behaviour)
```

| Value | Meaning | Who is it today |
|---|---|---|
| `full` | re-fire over the whole footprint | every head-dependent step except self-review — the fail-closed default, so silence never buys a skip |
| `delta` | re-fire, scoped to changes since this step's own `head_at_completion` | `pre-submission-self-review` (DE's model); the target for `finalize-step-simplify` |
| `skip` | do not re-fire on loop-back despite being head-dependent | the operator's `run-on-loop-back: false`, now expressible **without** contradicting `head_dependent` |

**⭐ RESOLUTION PRECEDENCE — default declared at the SKILL, overridden in `marshal.json`, exactly as `lane`
resolves today** *(operator direction 2026-08-23)*. Mirror `_effective_lane_tier`'s three rungs verbatim
rather than inventing a second precedence order:

| Rung | Source | `lane`'s equivalent |
|:--:|---|---|
| 1 (wins) | per-element override — `plan.phase-6-finalize.steps.{id}.params` in `marshal.json`, or the plan-scoped `status.metadata.finalize_step_overrides` map, merged **plan-local over marshal** | the per-element `lane` override |
| 2 | the step's OWN frontmatter declaration — `loop_back_scope: delta` in the skill doc | declared `lane.tier` |
| 3 (default) | `full` — fail-closed, today's behaviour for every step | the `class` default tier |

⇒ **A step author states the sensible default for their step; an operator overrides it per project or per
plan without touching the skill.** That is the property the proposal asks for, and it costs no new
resolution machinery: rung 1 and rung 3 already exist for `lane`, and rung 2 is the frontmatter row DF-1
adds. ⛔ The immunity rule below applies at rung 1 ONLY — a step author declaring `skip` in their own
frontmatter is making a design statement about their own step, not weakening someone else's.

⭐ **The configuration channel already exists — no new plumbing.** `finalize-step-simplify.md:37` documents
the per-element override resolved from **either** the project-wide `plan.phase-6-finalize.steps` map in
`marshal.json` (`params.lane`) **or** the plan-scoped `status.metadata.finalize_step_overrides` map written
by `manage-config finalize-steps set-lane --plan-id …`, merged plan-local-over-marshal. `loop_back_scope`
rides that same map as a sibling key of `lane`. ⇒ The operator's *"so it is a configuration aspect"* is
satisfied by an existing seam.

⛔⛔ **THE SAFETY REQUIREMENT, AND IT IS NOT OPTIONAL: `skip` IS A WEAKENING AND MUST INHERIT THE `lane: off`
IMMUNITY MODEL.** `_manifest_lanes.py:37` defines `_IMMUNE_TO_OFF_CLASSES = ('core', 'derived-state')`, and
`_lane_keep_decision` ignores an `off` override on those classes, keeps the element, and emits *"override
'off' ignored for {cls} floor element — immune, cannot be weakened"*. **An operator-set
`loop_back_scope: skip` on a `core` step MUST be neutralised the same way, with the same warning.**
Without that, an operator could set `skip` on `pre-submission-self-review` and disable **the only check
that examines the fix commits themselves** — and § 11.6 of PR #1332 is first-party evidence of the cost:
a fix written for a bot-surfaced defect **introduced a new falsehood**, with CI, CodeRabbit and PR Agent
all green on it. ⚠ `delta` is a NARROWING, not a weakening, so it is not subject to the immunity — but its
correctness depends on the anchor, so a step declaring `delta` MUST also be `head_dependent: true` (whose
`missing_head_at_completion` refusal already guarantees the anchor exists).

**Deliverable:**
1. Add the `loop_back_scope` row to `ext-point-finalize-step.md`'s frontmatter table, with a verbatim
   discriminator in the style of its siblings and the fail-closed-absence rule stated explicitly.
2. Extend the per-element override resolution to carry it beside `lane`, and apply the immunity rule to
   `skip` with a matched control proving a `core` step's `skip` is neutralised **and** an `adversarial` /
   `prunable` step's `skip` takes effect. ⛔ Without both arms the guard is vacuous.
3. Declare it on the four steps DE analysed: `pre-submission-self-review: delta` (documenting shipped
   behaviour), `finalize-step-simplify: delta` (DE-1's change), `plugin-doctor` per DE-2's evaluation, and
   `architecture-refresh` per DE-3.
⚠ **Sequence after DB and DE** — this field is the declaration surface for what those two establish, and
declaring a scope before the delta machinery exists would ship an inert lever wearing the shape of a real
one, which `verdict_inputs`' own row already names as a disqualifying shape.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_gate_coverage.py`
- `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py`

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` *(added 2026-08-23, DB)*
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` *(added 2026-08-23, DC)*
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` *(added 2026-08-23, DD)*
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` *(added 2026-08-23, DD — READ-ONLY: its ordering rule is load-bearing, see DD correction 2)*

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` *(added 2026-08-23, DE-1)*
- `.claude/skills/finalize-step-plugin-doctor/SKILL.md` *(added 2026-08-23, DE-2 — evaluate-only; may end read-only)*
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` *(added 2026-08-23, DE-3 — ⚠ SHARED with PLAN-TRUTH-095 D6, coordinate)*

- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py` *(added 2026-08-23, DF-2 — ⚠ SHARED with PLAN-TRUTH-095, which is RUNNING; serialize)*
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_lanes.py` *(added 2026-08-23, DF-2)*

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` *(added 2026-09-03, drain fold of `deployment-and-refresh-gaps-006` — the `verdict_inputs` surface)*
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` *(added 2026-09-03, same fold)*
- `test/plan-marshall/phase-6-finalize/test_verdict_currency.py` *(added 2026-09-03, same fold)*

## Out of scope

- Correcting any archived `report-01.md` under `cloud-runs/` — a run report is a dated record; see the
  banner. Where the same false claim is restated on a live surface, that restatement is in scope and
  must be re-derived rather than inherited from the gap's `Where` line.
- Any gap owned by another staged plan. Ownership was derived at ingestion; if a re-derivation shows
  an overlap, **record it and serialize**, do not silently absorb the sibling's gap.
- Re-fixing a gap that no longer reproduces at HEAD.

## Claim Labels
- verdict: unverifiable | checked_at: 5f972ac15 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Prose-form claim section, section-scope address. The section itself declares every claim HYPOTHESIS until its own D0 gate re-derives, and states the 2026-08-22 re-check was per-gap and SAMPLED, not exhaustive. That is a self-declared unreached population, so unverifiable is the section's own stated state rather than an orchestrator judgement. Nothing here is refuted; settling it is the launched plan's D0 job.

Every claim in this plan is **HYPOTHESIS** unless the deliverable marks it otherwise. The gap entries
it derives from were OBSERVED at their verification commit and re-checked at the 2026-08-22 ingestion,
but that check was per-gap and sampled, not exhaustive. **Treat every asserted absence as unverified
until the D0 gate re-derives it.**

## Verification

- The D0 gate publishes the population it examined **and** the count that reproduced, as two separate
  numbers. A zero must state which zero it is: *examined N, none reproduced* is a result; *could not
  look* is not.
- Every guard added or widened here is proved by a **matched positive/negative control** — a case that
  goes RED against the defect the guard names, and a near-identical case that stays green. A guard
  whose population can be empty publishes its population size on a clean run.
- No deliverable is reported complete on a read alone where the claim is about behaviour: execute the
  symbol, or mutate it and observe the red.

## Notes

**Derived figures are re-derived AFTER the review cycle closes, not before.** Both `500` and `520` had
their diff silently widened by CodeRabbit after their counts were taken, and `510`'s own participation
figure used a floating `origin/main` endpoint three sections after its own § Build gate corrects that
exact defect. The review is a diff-widening event. Take every count last.

## Folded from PLAN-TRUTH-074's drain (2026-08-22)

Two first-party observations drained from PLAN-TRUTH-074's inbox. Both are instances of this plan's
own title — *the dispatch contract is enforced at one surface of three, and two gates were never
opened* — measured on a real 5.8M-token plan. **They are evidence for the existing deliverables, not
new ones**; outline decides whether either needs its own, and re-counts against the split guard if so.

### F1 — the shape-violation check has no left-hand side (from inbox `-005`)

`check-dispatch-audit` pairs two surfaces: **Surface B**, the `effort resolve-target` records in
`decision.log` (the resolve/intent side), against **Surface A**, the `[DISPATCH]` work-log lines (the
observable side). On PLAN-TRUTH-074 it returned:

```text
shape_violation:
  status: not_evaluated
  evaluated_population: 0
  reason: "no `effort resolve-target` records in decision.log — Surface B ... is empty,
           so the shape-violation check has no left-hand side to evaluate."
```

Surface A was healthy by contrast — 31 `[DISPATCH]` lines against 25 completions, ratio 1.24,
`confidence: nominal`, all 16 terminal finalize steps classified (7 dispatched, 9 inline, 0
no-evidence, 0 `missing_dispatch_emission`). The plan's `decision.log` holds **187** entries and not
one is an `effort resolve-target` record, so this is a specific absence, not a dead log.

⭐ **The check itself is exemplary and is NOT the defect.** It reports `not_evaluated` and spells out
that *"a bare 0 here would be a never-evaluated verdict wearing an evaluated-clean face."* That is
this epic's discipline working. The residual defect is one level up: **a check that is structurally
unevaluable is not a check.** Either the emission gets wired, or the arm is retired so the audit stops
carrying a permanently `not_evaluated` block once per plan.

Three outcomes are admissible, and the run must distinguish them: the emission does not exist; it
exists but is conditional and this plan took the other path; or it exists and is broken. If it is
deliberately conditional, `check-dispatch-audit` must publish **why** Surface B was empty in terms of
that condition — a reader cannot currently tell *"this plan took the other path"* from *"this
emission does not exist"*.

### F2 — the per-dispatch context-load columns are unfed, so billing composition is unavailable (from inbox `-004`)

`record-dispatch-boundary` accepts four context-load columns — `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`. Across PLAN-TRUTH-074's three dispatching
phases, **25 of 25 rows carry all four unpopulated** (`measured_rows: 0`; 4-plan 1 row, 5-execute 4,
6-finalize 20). The recorder is plainly being called — every row carries a correct
`termination_cause`, `total_tokens`, `tool_uses` and `duration_ms` — so **only the four appended
columns are unfed**, at the call sites.

⚠ **The sibling half of this finding has since MOVED — do not carry the message's version forward.**
The inbox message also stated that `manage-metrics generate` returns
`totals_billing_weighted_total: 0` with `population_count: 0` and renders `Billing (cost)` as `-` for
all six phases. That was true at emission because `record-metrics` had not yet run. It has now run:
`generate` returns **`totals_billing_weighted_total: 73955161`** with
**`population_count: 1`** (6-finalize). ⇒ The message's clause *"`enrich` evidently also did not run
or found nothing"* is **settled, not open**: `enrich` had not run because `record-metrics` had not.
The phase-level path works when `enrich` runs; **the per-dispatch path is the part still unfed**, and
it is the only source of the input/output split and the cache fields — the single-figure `<usage>`
tag carries neither.

⛔ **`position_multiple`** — the cache-read-per-tool-use figure that measures what re-reading resident
context costs as a dispatch grows — remains `unmeasured` for every phase. For a token-reduction
effort that is precisely the quantity needed and precisely the one not recorded.

⭐ **A defaulted `0` is indistinguishable from a measured `0`.** The recorder's argparse surface
defaults all four columns to `0`; that default is itself worth revisiting under this plan's own
never-report-an-absence-as-a-measurement rule.

---

## Findings drained from PLAN-TRUTH-075's inbox (2026-08-24, PR #1336 / `77c9dc70a`)

⛔ **SPLIT-GUARD NOTICE — READ BEFORE OUTLINE.** This plan already carries **14 deliverables**, above
the epic's raised guard of 12, and now carries **four** finding sections. F3 and F4 below are recorded
as EVIDENCE, not as new deliverables. ⚠ **Outline MUST re-count against the split guard and should
presume a split is required**, rather than absorbing F3/F4 into the existing set by default. A second
independent measurement arriving on an already-oversized plan is a signal to divide it, not to grow it.

### F2 — SECOND INDEPENDENT MEASUREMENT (from PLAN-TRUTH-075 inbox `-006`)

F2's evidence was n=1 (PLAN-TRUTH-074, 25 of 25 rows unfed). PLAN-TRUTH-075 makes it **n=2 on a
different plan**: `context_position_cost` reports `total_rows: 4`, `measured_rows: 0`,
`unmeasured_rows: 4`, `position_multiple: unmeasured` across all three dispatching phases. ⇒ **The
unfed-columns claim is corroborated and is not a property of one run.**

⭐ **But `-006` also carries a NEW claim F2 did not have, and it points the opposite way from -074's
evidence.** F2 argued *"the recorder is plainly being called"* from -074's 25 rows. On -075 there are
**4 rows total, 2 of them in `6-finalize` against 7 token-proven dispatches** — 238,455 tokens of
boundary rows against a phase accumulator of 1,233,654, i.e. **19.3% of the phase**. `metrics.md`
reports the coverage as *"undecidable — the phase carries no `subagent_samples` to compare against"*,
so the shortfall cannot even be attributed to the declared-excluded dispatch classes.

⇒ **There are TWO defects here and F2 currently names one.** (a) the four columns are unfed at every
call site; (b) **most finalize steps never call `record-dispatch-boundary` at all**, and the gap is
not merely unmeasured but *undecidable* for want of a comparison population. ⛔ Do not let (a)'s fix
close (b) — a fully-populated row set that covers a fifth of the phase is still a fifth of the phase.
⚠ **The largest phase in the plan is the least instrumented**, which is the worst possible place for
this gap given the epic's token-reduction priority.

### F3 — `check-dispatch-audit` grades its own channel confidence from a denominator the re-fires inflate (from inbox `-003`)

The audit emitted `channel_completeness: dispatch_line_count: 15, completion_count: 23,
dispatched_step_count: 7, ratio: 0.652, confidence: nominal`.

**At least 4 of those 23 completions are unpaired re-fire duplicates** (see F4). Excluding them moves
the ratio from `0.652` to roughly `0.79`.

⭐⭐ **The contamination is SELF-REFERENTIAL, which is what makes this F1's sibling rather than a
separate curiosity**: the component whose job is to report whether the dispatch channel is complete is
grading itself against an inflated denominator — **and it reported `nominal`.** F1 records an arm that
honestly says `not_evaluated`; F3 records an arm that confidently says `nominal` on a contaminated
population. Same component, opposite failure modes, and the second is the dangerous one.

⛔ **This is a population-derivation defect of the exact archetype the epic tracks**: a set-guarding
metric whose population is counted from a surface that can double-count. **The correct denominator was
already on disk** — `status.metadata.phase_steps` carries `firing_count` and `prior_firings[]` per
step. ⇒ Derive the population from the state store, not from log-line counts; if the log-line count is
kept, deduplicate by step name and **publish both the raw and the deduplicated figure** so the ratio's
population is legible.

### F4 — a re-fired finalize step emits `Completed` without `Executing`, so the `[STEP]` bracket is unbalanced (from inbox `-002`)

F3's producer-side cause. Four steps emitted a second
`[STEP] (plan-marshall:phase-6-finalize) Completed step: X` with no paired `Executing step: X`:

| Step | Executing | Completed | Second Completed | `firing_count` |
|---|---|---|---|---|
| `create-pr` | 19:18:03 | 19:22:15 | 19:22:52 | 2 |
| `pre-push-quality-gate` | (earlier) | 19:16:59 | 20:29:32 | **3** |
| `automatic-review` | 19:43:49 | 19:50:57 | 20:29:55 | 2 |
| `ci-verify` | 19:24:23 | 19:43:25 | 20:47:19 | 2 |

⭐ **The re-fires themselves are CORRECT and must not be "fixed"** — `pre-push-quality-gate` re-fired
per its head-dependent contract after HEAD advanced by four commits, and `status.json` models it
faithfully (`prior_firings[]`, `firing_count`). **The state store knows; only the work log does not.**
⇒ Emit `Executing step` on every firing, or emit a distinct `Re-firing step: X` marker so the bracket
is balanced and re-fires stay countable. ⚠ Whichever is chosen, F3's fix must not depend on it — the
state store is the authoritative denominator either way.

### F5 — gate-delta is structurally unmeasurable whenever a gate re-fires (from inbox `-008` item 5, finding `9134b6`)

**Direct evidence for DE.** The review-retrospective excluded its gate-delta share as
`gates_did_not_cover_reviewed_tree`. The *documented* cause is a gate SHA **older** than the reviewed
one; here it ran the **other way** — `pre-push-quality-gate` fired three times and the record keeps
only the terminal SHA, because **`prior_firings[]` carries outcomes WITHOUT SHAs.**

⇒ **Any plan whose head-dependent gate re-fires is unmeasurable for this delta**, independently of the
ordering hypothesis. Suggested fix: record per-firing head SHAs in `prior_firings[]` — which is
precisely the delta-anchor DE already owns, so this is DE's missing storage half rather than a new
deliverable.

⛔⛔ **AN EPISTEMIC WARNING THAT MUST SURVIVE INTO THE RUN:** *a run of `excluded` rows must NOT be read
as support for the ordering hypothesis.* The exclusions have **at least two causes** and the
provenance string names only one. Any measurement DE produces that counts exclusions has to
discriminate the two causes first, or it will confirm whichever hypothesis it started with.

### DD — addition from inbox `-001`: the billing column is unmeasured BY CONSTRUCTION

`-001` independently reproduces DD's ordering finding — `plan-marshall:plan-retrospective` at
`order: 995`, `default:record-metrics` at `order: 998`, and the retrospective's Step 2.5 reconcile
calls `manage-metrics generate` which folds the durable accumulators but does **not** compute the
billing view. ⇒ *"the epic whose top priority is token reduction has no billing composition in any of
its own retrospectives."*

⭐ **`-001` adds a third option DD did not carry, and it is the MINIMUM that must ship regardless of
which remedy is chosen:** have the plan-efficiency aspect declare billing
`unmeasured_by_construction`, **with the ordering as its stated reason**. Options (a) call `enrich`
early and (b) move the retrospective are what make the number *available*; option (c) is what stops
the empty column reading as a measured zero. ⛔ R18's constraint is unchanged and binds all three:
**do NOT move `record-metrics` or the retrospective** — `record-metrics.md:37` states its position is
load-bearing.

### ⛔⛔ F4 CORRECTION — the table above UNDER-COUNTS, and it under-counts by committing F3's own defect

**Verified first-party 2026-08-24 against the ARCHIVED plan's `status.json`**
(`.plan/local/archived-plans/2026-08-23-cloud-lane-build-gate-reads-one-field-short/status.json`,
`metadata.phase_steps["6-finalize"]`), after PLAN-TRUTH-075's operator report was checked against ground
truth.

**SIX steps re-fired, not four. Total firings 29 across 22 recorded steps.**

| Step | `firing_count` | `prior_firings[]` outcomes | Named in F4's original table? |
|---|:--:|---|:--:|
| `pre-push-quality-gate` | **3** | `done`, `done` | yes |
| `pre-submission-self-review` | 2 | **`failed`** | **NO** |
| `finalize-step-simplify` | 2 | `done` | **NO** |
| `create-pr` | 2 | `done` | yes |
| `ci-verify` | 2 | `done` | yes |
| `automatic-review` | 2 | `done` | yes |

⛔⛔ **HOW THIS HAPPENED, recorded because it is the epic's archetype committed by its own orchestrator
inside the very finding that names it.** F4's table was copied from the inbox message's enumeration of
**unpaired `[STEP]` log lines** — four of them. F3, written one section earlier, says explicitly that
the log-line count is an unreliable population and that **`status.metadata.phase_steps` carries
`firing_count` and `prior_firings[]` and is the authoritative record**. ⇒ **F4 derived its population
from the surface F3 had just condemned**, and consequently missed two re-fires. The log under-reports
re-fires as well as inflating completions, and the two errors are not symmetric.

⇒ **RULE, binding on this plan's run:** every count in F3/F4/F5 is derived from `phase_steps`, never
from `[STEP]` lines. The log is the SUBJECT of these findings, never their evidence.

### ⭐⭐ F6 — a step that FAILED and then passed renders as clean, with no trace of the failure

Discovered by the same first-party check; **in no inbox message.**

`pre-submission-self-review` carries `outcome: done`, `firing_count: 2`, and
`prior_firings: [{"outcome": "failed"}]`. The operator report renders it:

```text
[OK]  pre-submission-self-review        clean on full surface, 2 findings fixed
```

⛔ **A step whose first firing FAILED is reported `[OK] clean`, and the word "clean" is doing double
duty** — it describes the surface the *second* firing examined, and reads as a description of the step.
The failure is recorded in `prior_firings[]` and appears nowhere a reader of the report can reach.

⭐ **Two further shape facts, both first-party:**

1. **`prior_firings[]` entries carry ONLY `{"outcome": ...}`** — no SHA, no timestamp, no
   `display_detail`. ⇒ **This is direct confirmation of F5**, which asserted exactly that absence from
   the inbox message alone. F5's claim is now verified rather than reported.
2. **The report's denominator is 23; the store records 22.** The 23rd is `archive-plan`, which runs last
   and archives the file it would have to write itself into — so the store *structurally cannot* contain
   it. ⚠ Benign in cause, but it means **`23/23` is not verifiable against the state store at all**, and
   any consumer reconciling report against store will find an off-by-one with no recorded explanation.

⇒ **A per-step record that keeps only the terminal outcome cannot express "failed, then passed", and
the report has no vocabulary for it.** Whichever remedy DE/F5 chooses for per-firing SHAs must carry the
per-firing OUTCOME to the report surface too, or a failed-then-passed step stays indistinguishable from
one that passed first time.

### F7 — a MANDATORY dispatcher record was skipped, nothing checked, and the cost landed five steps later (2026-08-24, operator transcript)

**DA's archetype, observed live on a running plan.** DA reads *"a dispatch that skips its
dispatcher-owned Step 1 is refused by the leaf, at full cost."* This is the same shape at a different
seam, and it was verified first-party at HEAD `77c9dc70a`.

**What happened.** `finalize-step-simplify` (`mutates_source: true`, order 9) committed during
finalize. `phase-6-finalize/SKILL.md` Step 3 item **5f(d)** requires the dispatcher to emit a
**freshness reconciliation record** *immediately* after such a commit. **The dispatcher did not emit
it.** Five steps later the `push` barrier's freshness precondition refused with
`reason: worktree_mutated`, and the run paid a full rebuild.

⭐⭐ **The runner's response was CORRECT and must not be read as the defect.** It declined to author
the record retroactively:

> *"Writing it now — after the gate has told me it's blocking — would be authoring the evidence that
> unblocks me… A retroactive record and a genuine one are indistinguishable once written."*

✅ **Verified against the standard: `push.md:79` states *"Genuine drift never produces this record (no
finalize-internal commit authored it), so the fail-closed path is preserved."*** That property holds
**only** if the record cannot be authored on demand. A retroactive 5f(d) record would have converted a
fail-closed gate into an open one, silently. ⛔ The rebuild was the right call and the honest-stop
guard for it is `PLAN-TRUTH-107` D5.

**The defect is the missing emission and the absence of any check on it.**

| Property | 5f(d) reconciliation record | Comparable seam |
|---|---|---|
| Mandatory | **yes** — *"Emit a legible reconciliation record"* | `mark-step-done` |
| Post-condition check | **NONE** | `assert-step-recorded` (`manage-status/SKILL.md:516`, zero writes, *"called after every dispatched (Task-agent) step returns"*) |
| Failure surfaces | **five steps downstream**, as a gate refusal with no attribution to the omission | at the step boundary |

⇒ **`assert-step-recorded` is the shipped precedent and 5f(d) does not use it.** A mandatory emission
with no post-condition is a promise, not a contract. ⚠ Scope note: fixing 5f(d) alone would be a point
fix — **D0's population sweep should enumerate every MUST-emit record in the finalize dispatcher that
carries no post-condition check**, and F7 is one member found by one accident, not the population.

⛔ **Do NOT fix this by making the reconciliation record easier to write, later, or retroactively
tolerable.** The record's entire value is that it was written before the outcome was known. The correct
remedy is to make the *omission* detectable at the moment it happens.

## Folded from PLAN-TRUTH-095's drain (2026-08-24, PR #1339 / `b95d78437`)

⛔ **SPLIT-GUARD NOTICE STANDS AND HARDENS.** This plan already exceeded the guard at 14 deliverables
before this drain; it now carries a sixth finding section. **Outline must presume a split.**

### DD — THIRD data point, and the sharpest (from inbox `-002`)

`manage-metrics enrich` attributes the four-field `message.usage` view by a phase's recorded **time
window**, and a window needs an `end_time` — which `default:record-metrics` writes at order **998**.
`plan-retrospective` sits at **995**. ⇒ **On every plan, the phase that closes last is the phase that
can never be billed by the retrospective that reports on it.**

⭐ **On PLAN-TRUTH-095 this was the single largest item, not a rounding error:**

| Figure | Value |
|---|---|
| `6-finalize` dispatched | **2,635,188** — **48%** of the plan's 5,483,351, more than `5-execute` (1,210,592) + `4-plan` (535,462) combined |
| `6-finalize` Phase Details | **no** `Main-context-window usage`, **no** `Billing-weighted total`, none of the exploration / cache-residency bullets every other phase carries |
| Reported plan billing | **63,456,072** stamped `population_count: 5` of 6 |
| Actual, once closed | **145,500,000** — **2.3×** |

⭐⭐ **A concrete remedy the message supplies and DD should adopt rather than re-derive:** give `enrich`
an **open-window mode** — when a phase has a `start_time` and no `end_time`, attribute from
`start_time` to now and record with an explicit `window: open` / floor marker, **exactly as the
accumulator reconcile already does for `total_tokens` at the retrospective's Step 2.5**. The
authoritative close at 998 then overwrites the floor, as it already does for the token total. ⇒ **This
is a shape already shipped in the same skill for a sibling quantity**, which makes it the cheap
option. ⛔ R18's constraint is untouched: **do NOT move `record-metrics` or the retrospective** — its
lateness is load-bearing, it must fold in the retrospective's own spend. **Failing the open-window
mode, `generate` must render an unclosed phase's billing cell as `unbillable (window open)`, never `-`,
so the omission stops looking like a phase that cost nothing.**

### F2 — n=3, and a NEW failure mode BELOW the one F2 describes (from inbox `-004` and `-005`)

**`-005` corroborates F2 for the third time:** all **11** recorded dispatch rows carry `unmeasured` in
all four context-load columns; `position_multiple: unmeasured`. ⭐ The message is careful and correct
that *"the recorder behaved correctly and the reader reported honestly — the measurement simply never
happened"*: the flags are **deliberately defaultless** so an omitted flag writes the literal
`unmeasured`, keeping *"the caller passed no measurement"* distinguishable from *"the dispatch loaded
zero context"*. **That design is right and must survive the fix.**

⛔⛔ **`-004` is NOT a third corroboration — it is a worse, separate defect one level down.**
`5-execute` emits **no dispatch-boundary file at all**: the plan directory holds
`metrics-dispatch-boundaries-4-plan.toon` (1 row) and `-6-finalize.toon` (10 rows), and **no
`-5-execute.toon`** — while that phase demonstrably dispatched (3 inferred clusters, 15 tasks `done`,
1,210,592 tokens). ⇒ **F2 says the columns are unfed; this says the plan's IMPLEMENTING phase, its
second-largest token consumer, has no boundary rows to feed.**

⭐⭐ **And the consuming rule cannot see it.** `DISPATCH_TERMINATION_CAUSE` is precondition-guarded on
the file's existence — *"Plans without the artifact skip the rule entirely"* — a guard added so the
rule would not false-positive on plans predating the artifact. **A file-existence guard fails toward
silence for BOTH causes**: *this plan predates the artifact* and *this phase should have written it and
did not* are indistinguishable. ⇒ **Two fixes, and the second is the generalisable one:** (a) call
`record-dispatch-boundary --phase 5-execute` at every execute-dispatch termination, matching the
finalize dispatcher; (b) when a phase has dispatch evidence from **another** channel — inferred
clusters in the work log, or non-zero `subagent_samples` from `enrich` — but no boundary file, emit
`missing_boundary_file` rather than skipping. ⭐ **The retrospective already computes that corroborating
evidence, so the discriminator costs nothing**, and it mirrors the `missing_dispatch_emission`
treatment `check-dispatch-audit` already applies — *an instrumentation finding against the recorder,
not a discipline finding against the phase.*

⚠ `4-plan` is separately marked `PARTIAL: 1 of 4 dispatch(es) recorded`, so **even the phase that does
emit rows emits them for a quarter of its dispatches.** Fixing (a) for `5-execute` alone would leave
that intact.

## Folded from the PLAN-TRUTH-096 drain (2026-08-24)

Three inbox messages fold here. ⛔ **None of them adds a deliverable** — this spec is already over
the raised split guard (W-075-c), and every item below is EVIDENCE for a deliverable that already
exists. Do not let this section grow the set.

**F2 gains its first measurement, and a phase-level twin (inbox `-006`, `-008`).**

`-006` — the four per-dispatch context-load flags on `manage-metrics record-dispatch-boundary`
(`--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens`)
are honoured by the RECORDER and populated by **no call site**:

| Phase | Rows | Columns populated |
|---|---:|---|
| 4-plan | 1 | 0 of 4 |
| 5-execute | 3 | 0 of 4 |
| 6-finalize | 15 | 0 of 4 |

⇒ `context_position_cost` reports `total_rows: 19`, `measured_rows: 0`, `position_multiple:
unmeasured`, `cache_read_per_tool_use: unmeasured` for every phase. ⭐ The recorder writing the
literal `unmeasured` is the design WORKING — the gap is entirely on the write side.

`-008` — the **same defect one ordering band up**: `billing_weighted_total` is written per phase only
by `manage-metrics enrich`, and nothing in the retrospective workflow calls it. At
`plan-retrospective`'s `order: 995` the `Billing (cost)` column is empty **and cannot be anything
else**: `totals_billing_weighted_total: 0` with `population_count: 0`, `-` in all six phase rows and
the Total, and no phase row carrying the four token fields at all.

⛔ **Read with R18: the fix is an EARLIER `enrich`, not a move of `record-metrics` (order 995, not
990) or of the retrospective** — `record-metrics.md:37` states its position is load-bearing. The two
messages are one cause at two scopes: a reader scheduled before the producer that fills its input.

**DB gains the cost measurement that R22 asserted (inbox `-007`).** This plan is
`scope_estimate=single_module`, `change_type=bug_fix` — anchor warns at 800K, errors at 1.3M. It
consumed **6,443,862** dispatched tokens, ~**5× the error anchor**, and that is a **floor** (`1-init`
carries no token record; `6-finalize` was never closed by `end-phase`). Concentration is in finalize;
**self-review alone burned 7 firings, 6 of which failed.** ⇒ R22's *"the amplification, not the band
size, is the cost driver"* now has a second independent instance. DB lands first, unchanged.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24)

⛔ **Again: no new deliverable.** This spec is over the raised split guard and must be SPLIT before
it is emitted (W-075-c, W-096-d). Both items below attach to deliverables that already exist.

**F2 — the context-load gap is now a CONFIRMED RECURRENCE, not a single observation (inbox `-007`).**
The `-096` drain measured 19 of 19 dispatch-boundary rows carrying `unmeasured` in all four
context-load columns; this plan reports the same shape independently, and states the consequence in
one line: **the billing view stays unmeasurable until the fields are wired at the call sites.** ⭐ Two
plans, two runs, same zero ⇒ this is the steady state, not an artifact of one run. The recorder side
remains correct in both observations — the entire gap is on the write side.

⚠ **Read with `-088`'s own landing, which now carries `total_billing_weighted=94666978`.** A
plan-level billing total EXISTS; what does not exist is its **attribution to dispatches**. Do not let
the presence of the total be read as the gap closing — F2 is about per-dispatch attribution, and the
`-096` drain's message `-008` (billing unmeasured at retrospective `order: 995`) is a THIRD, distinct
scope. Three scopes, one cause, and only the plan-level one is now measured.

**DE/DF gain a concrete unvalidated-input defect (inbox `-011`): `mark-step-done` accepts a
`head_at_completion` SHA it never resolves.** The field is the anchor the whole delta-vs-full
mechanism rests on — `delta` scoping is defined against it, and `missing_head_at_completion` is the
guard that is supposed to make the anchor guaranteed. ⛔ **An accepted-but-unresolved SHA defeats that
guard without tripping it**: the field is present, so the missing-anchor check passes, while the
value may name no commit in the repository. ⇒ DF must not ship `delta` until the anchor is
**resolved** at record time, not merely non-empty. This is a prerequisite, not a companion.

## Folded from the PLAN-TRUTH-087 drain (2026-08-25) — inbox `-004` and `-011`, the head-dependence pair

Two candidate-lessons from PR #1340 that are **one defect seen from both ends**: finalize steps key
their re-fire decision on HEAD, and HEAD is the wrong key in both directions.

**`-004` — head-dependent gates RE-CERTIFY an unchanged tree because HEAD moved.** A gate declared
`head_dependent: true` re-runs whenever HEAD advances, even when nothing it examines changed. Cost
without signal, and it inflates the apparent verification count.

**`-011` — the mirror: a key finalize step SKIPS a changed tree because HEAD did not move in the way
the check expects.** Re-fire should key on a **content digest of the step's own inputs**, not on
`head_at_completion`.

⛔⛔ **This is not theoretical — it produced a FALSE `done` in this very run's landing payload, and
that payload is the epic's record of what shipped.** `finalize-step-sync-baseline` recorded `done`
against an **earlier base**, then a mid-finalize rebase was required (branch `mergeable: conflicting`
against a main that had advanced 7 commits; 24 commits replayed, **3 carrying conflicts across 7
files**, hand-resolved). The step was **skipped as not head-dependent** and never re-ran — so the
landing's machine-readable `steps` fact reads `finalize-step-sync-baseline:done` while the baseline
that `done` refers to no longer exists.

⭐ **Corroborated first-party at the drain**: the merged commit `b5ee8fac7` is a squash of a branch
that was rebased mid-finalize, and no step record anywhere states that a rebase happened. ⇒ **A
typed fact was emitted truthfully by a step whose precondition had silently expired.** That is this
epic's archetype reaching the one artifact the epic uses to reconcile — worth D-priority here, since
`-097` already owns the finalize dispatch/measurement surface.

⚠ **Adjacent, do not merge:** `-111` D3 holds `assert-step-recorded --require-terminal` accepting a
STALE record from a prior firing. Same root shape (a record outliving its precondition), different
verb. `-097` F5 (`prior_firings[]` carries outcomes without SHAs) is plausibly the **same** root
cause as both — D0 must check that before the three are fixed separately.

## Folded from the PLAN-TRUTH-086 drain (2026-08-26) — inbox `-003`

**`[DISPATCH]` rides the resolve seam, so re-firings are invisible and BOTH audit directions pass.**

The dispatch record is emitted by the `effort resolve-target` seam. A re-fired dispatch that does not
re-resolve therefore emits **no second `[DISPATCH]` line**, so the log under-counts firings.

⛔ **The reason this is worse than an under-count: both audit directions still pass.** Every logged
dispatch corresponds to a real firing (no false positives), and every *resolved* dispatch is logged
(no gap the resolve-side check can see) — so an auditor checking either direction gets a clean
answer while the true firing count is higher than the log. **A bidirectional check over the wrong
population is still vacuous**, which is this epic's archetype applied to its own dispatch trail.

⚠ Directly adjacent to this spec's existing F5 (`prior_firings[]` carries outcomes without SHAs) and
to `-111` D3 (`assert-step-recorded` accepting a prior firing's record). **All three are re-fire
accounting.** D0 must establish whether they share one root cause before any is fixed separately —
the same instruction already recorded for `-004`/`-011`, now with a third member.

## ⭐ FOLDED 2026-08-27 (landing #1359) — the four context-load columns never reach the recorder

From the `PLAN-TRUTH-098` landing drain (message `-008`).

**Directive: pass the four context-load columns from every dispatcher to
`record-dispatch-boundary`.** Today the recorder is called without them, so the dispatch-boundary
record cannot report context load at all.

⚠ **Cross-check against this plan's existing dispatch-measurement scope before scoping** — it may
already own the recorder's call surface, in which case this is one more caller to fix rather than a new
deliverable.

⭐ **The same run supplies the reason it matters:** resident context per tool-call climbed **209K →
771K** across finalize, and **nothing in the dispatch record would show that** — the figure came from
the metrics store by hand. ⛔ **The cost analysis itself belongs to `code-intelligence-substrate`**, not
here; what belongs here is that the measurement surface cannot carry the fact.

## ⭐ FOLDED 2026-08-27 (landing #1361) — 6-finalize is instrumented by nothing, and the enrich pass closed only half

From the `PLAN-TRUTH-114` landing drain (candidate-lesson `-003`).

**Three independent ledgers reported `6-finalize` as having done nothing:** `metrics.toon` carried only
a `start_time` with no accumulator, no dispatch-boundary file existed, and `execution.toon`'s
`execution_log` held **zero rows** for the phase.

⭐⭐ **The `enrich` pass closed the TOKEN half (6/6 phases, 14.6M tokens) and NOT the STEP half.** The
per-step execution log for `6-finalize` remains empty **because most finalize steps run INLINE in the
orchestrator rather than as dispatched agents** — and the execution log only records dispatches.

⇒ **This is the measurement surface's blind spot stated exactly**, and it bears directly on this plan's
dispatch-boundary scope: a phase that runs inline is invisible to every dispatch-derived measurement,
so *"6-finalize did nothing"* and *"6-finalize was not dispatched"* are the same row. ⚠ **Finalize is
also the most expensive phase** — the prior landing measured it at **52% of that run's billing** — so
the phase with the largest spend is the one the instrumentation cannot see.

⛔ **Do not fix this by dispatching finalize steps** to make them visible; that changes execution to
suit the instrument. The deliverable is that an inline step is RECORDED as an inline step.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-006.md`** (relayed from Token-Sheriff, plan `outbound-hostname-verification-core` PR #689) — *every HEAD advance during finalize paid a full ~10-minute reactor rebuild.*

  **The measured half (first-party in the sending run):** four long reactor builds inside phase-6-finalize alone — 13:11 `pre-push-quality-gate` ~600s, 13:56 post-`security-audit` re-gate ~530s, 16:06 post-review-fix re-gate ~600s, 17:46 post-triage re-gate ~650s — plus phase-5 boundary gates. **Roughly an hour of wall clock re-validating trees that differed from an already-green tree by a small, characterised delta.**

  ⚠ **The mechanism half is a HYPOTHESIS the sender explicitly refused to assert**: *“head-dependent finalize steps declare no `verdict_inputs` surface, so `verdict_currency` always returns `invalidated` on a HEAD advance”* — recorded by them as *“a mechanism hypothesis with a well-evidenced cost”*. ⭐ **This orchestrator DID locate the surface first-party** (`architecture search --content --pattern verdict_currency`, 8 hits over 4 files: `phase-6-finalize/SKILL.md`, `standards/verdict-currency.md`, `scripts/verdict_currency.py`, `test/.../test_verdict_currency.py`), so the component exists; **whether it lacks a `verdict_inputs` declaration is still unverified** and is now a verify-at-outline claim on this spec.

  ⛔ **One re-run in that set was CORRECT and must not be optimised away.** Decision `76e1c2` refused to file a freshness-reconciliation record because the security-audit commit had DELETED the root `<repositories>` block, changing dependency resolution for every module in the reactor. **A green gate computed against a different POM says nothing about that tree.** That case is also the discriminator the fold is really about: a commit touching dependency resolution invalidates the whole-reactor verdict; a commit touching only files already inside the previously-gated set, with no build-graph effect, does not. **A `verdict_inputs` declaration is exactly the surface that would let a step state which of the two it is, instead of every step defaulting to the expensive answer.**

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§5.3 — a fail-closed default over an UNDECLARED surface. ⭐ RECURRENCE and sharpening of the `deployment-and-refresh-gaps-006` fold recorded here 2026-09-03, and it converts that message's labelled HYPOTHESIS into a stated mechanism with a count.**

  The verdict-currency classifier invalidated **all 7** head-dependent finalize steps after a **docs-only** commit, **because none declares a `verdict_inputs` surface** and the fail-closed default assumes the commit could have invalidated the verdict. ⭐⭐ **The classification is CORRECT** — guessing *"unaffected"* would be the fail-open this design avoids. **It is also expensive: a full settle-band plus wait-region re-fire, twice, for prose-only deltas.**

  > ⛔⛔ **A fail-closed default is the right behaviour and the wrong steady state.** *"It is correct on every individual evaluation and wrong as a long-run condition, because it converts a missing declaration into a recurring cost paid silently, per run, forever."*

  ⭐ **The property that makes it silent is the one this spec must fix: the fail-closed branch is INDISTINGUISHABLE from a genuine invalidation.** Ask: report `invalidated_reason: no_verdict_inputs_declared` alongside `inputs_touched`, and surface **`head_dependent: true` with no `verdict_inputs` as a doctor-detectable under-declaration.** ⛔ *"Fixing only the 7 steps closes today's instance and leaves the mechanism intact."*

## ⛔⛔ SPLIT-GUARD NOTICE 2026-09-05 — OVER THE GUARD AT 16 DELIVERABLES. OUTLINE MUST PRESUME A SPLIT IS REQUIRED.

**Measured at cleanup: 16 deliverables, 883 lines, 4 folds.** The operator-raised split guard for this epic is
**12**, so this spec is over it by 4.

⛔ **This notice does NOT authorise absorbing the overage.** The default action is to split along
deliverable-group boundaries into sequential (or surface-disjoint parallel) plans. **Proceeding unsplit
requires a recorded rationale naming why the parts cannot ship independently** — a tightly-coupled
oversized plan is permitted, an unexamined one is not.

⚠ **Re-count before deciding.** This pass re-grounded every claim and re-scoped several; the
deliverable set may have moved underneath the number above. **Re-derive the count at outline rather than
inheriting it** — that is this epic's own promoted rule about restated figures, and it applies to this
notice too.

⭐ **Recorded rather than applied, by operator decision at the 2026-09-05 cleanup.** A5 redistribution is
the least-reversible class in the verb, and outline has more context about deliverable coupling than the
orchestrator does. **The orchestrator's job here was to make the overage impossible to miss, not to cut
the plan.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-148-the-finalize-step-contract-declared-surfaces-the-dispatch-seam-and-a-self-review-that-decides-its-own-close.md` (PLAN-TRUTH-148)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
