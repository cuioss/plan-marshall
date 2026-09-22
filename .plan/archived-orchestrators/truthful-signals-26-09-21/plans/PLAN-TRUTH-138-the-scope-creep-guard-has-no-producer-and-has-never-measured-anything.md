# PLAN-TRUTH-138: The scope-creep guard has no producer and has never measured anything

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-05 after a **fourth** independent report, from TokenSheriff. The defect has been an
Open Defect in this epic since 2026-09-03 and stayed UNOWNED through three findings; the fourth
carried the thing the first three lacked — **a named miss.**

| Corpus | Plans with `references.json` | Carrying `plan_creation_sha` | Reported |
|---|:-:|:-:|---|
| this checkout | 31 | 1 | 2026-09-03, first-party |
| first reporting project | 12 | 1 | 2026-09-03 |
| second reporting machine | — | — | 2026-09-04, filed `2026-09-04-12-003` |
| TokenSheriff | — | 0 (10 tasks, all `could_not_look`) | 2026-09-05 |

⛔ **The fourth report is the one that changes the priority:** the guard *"is the guard that would have
flagged this plan's one genuine out-of-footprint edit."* Every prior report established the guard's
SILENCE; this one names a real defect the silence let through.

## Objective

**`scope_creep_check` diffs a plan's live footprint against `references.json`'s `plan_creation_sha`.
No producer for that field exists anywhere in the marketplace, and the field is not in the schema of
the file it is read from. The guard therefore returns `could_not_look` / `no_baseline_sha` on every
plan and has never measured scope creep for anyone.**

⭐⭐ **The guard itself is EXEMPLARY and MUST NOT be "simplified" by this plan.** It refuses to publish
a zero it did not measure — it omits `residual_count` entirely rather than printing `0` — and its own
SKILL states why: *a 0 published by a run that never compared anything is indistinguishable from
"compared, found none", and a reason field alone does not fix that because it is advisory and trivially
dropped.* ⛔ **The defect is entirely UPSTREAM of the guard. A fix that touches the consumer's
reporting discipline has fixed the wrong end.**

⚠ **This is a SCHEMA gap, not merely a missing writer.** `_references_core.py:25` defines
`ReferencesData` — `branch`, `base_branch`, `issue_url`, `build_system`, `domains`, `affected_files`,
`external_docs`, `realized_footprint`, `merge_commit_sha`. **`plan_creation_sha` is not among them.**
The consumer reads a key the schema of the file it reads does not declare.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: re-ground the population and the writer question at HEAD before building anything.**
Re-derive the carrier set and publish it with its population and its coverage. ⛔ **Two facts must be
separated and both published:** (a) that no producer exists in the inventoried bundle source, and
(b) that a small number of `references.json` files in the wild DO carry the field, so *something* wrote
it. Fact (b) is not evidence of a producer this plan can reuse — `ReferencesData` is a `total=False`
TypedDict (typing, not enforcement) and `references.json` is plain JSON, so any writer with file access
could have. ⛔ **Do NOT chase a shared producer for the co-occurring keys.** `realized_footprint` and
`merge_commit_sha` are BOTH in the schema with documented producers (`manage-references
capture-footprint`, and `branch-cleanup` on the synchronous merge path only), so their co-occurrence is
fully explained by a sync-merge landing and is NOT evidence of a third writer. The unexplained write is
`plan_creation_sha` **alone**, and D0 may legitimately conclude it is not determinable from the corpus —
**that is a result, published as one, not a shortfall.**

**D1 — declare the field in the schema.** Add `plan_creation_sha` to `ReferencesData` so the next
reader is not reading an undeclared key. ⛔ **The schema entry is a deliverable in its own right and
does not become optional if D2 lands** — an undeclared key that happens to be written is the same
latent defect one step later.

**D2 — build the PRODUCER.** Stamp HEAD into `references.json` at plan creation. ⚠ **The site is a D0
question, not a premise of this spec**: `phase-1-init` and `manage-references` are both candidates and
the choice has consequences (a phase-1 stamp binds the baseline to plan creation; a `manage-references`
verb makes it callable for recovery on the ~30 existing plans that have none). ⛔ **Whichever site
wins, the value must be the sha at PLAN CREATION, not at first read** — a lazily-stamped baseline
would silently define scope creep as "since the first time anyone looked", which is a different and
useless measurement that would still report `success`.

**D3 — matched controls, including the one that has never been exercised.** A plan with a baseline sha
must produce a real `residual_count`; a plan without one must STILL report `could_not_look` and still
omit `residual_count`. ⛔ **The negative control is load-bearing and must be kept**: the recovery path
for the ~30 pre-existing plans cannot be "invent a baseline", so `could_not_look` remains a reachable,
correct state after this plan lands and its honesty must be pinned by a test. ⭐ **The positive control
is the one that has never run anywhere** — no test in the tree exercises the guard's measuring path
against a real baseline, because no environment has ever had one.

## Claim Labels

- OBSERVED: `scope_creep_check` reads `references.json`'s `plan_creation_sha` and returns `could_not_look` / `no_baseline_sha` with `residual_count` omitted when it is absent. First-party, this checkout.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: scope_creep_check.py:205-214 returns could_not_look/no_baseline_sha with residual_count omitted when the field is absent
- OBSERVED: no producer for `plan_creation_sha` exists in the inventoried marketplace source. Re-derived at `c3a1aacbc` via `architecture search --content` over a clean sweep (`files_scanned: 5340`, `unreadable[0]`, `truncated: false`): 5 files — 2 consumers (`phase-5-execute/SKILL.md`, `phase-5-execute/scripts/scope_creep_check.py`) and 3 tests. `manage-references` appears nowhere.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Independent sweep of 2408 files found exactly the same 5 files, 2 consumers 3 tests, manage-references absent
- OBSERVED: `plan_creation_sha` is absent from the `ReferencesData` TypedDict at `manage-references/scripts/_references_core.py:25`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _references_core.py ReferencesData TypedDict L26-45 has no plan_creation_sha field
- OBSERVED: four independent reports, three of them foreign corpora, agree the guard measures nothing. The fourth names a genuine out-of-footprint edit it would have caught.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Four-independent-reports provenance spans foreign and historical channels not reachable here
- ⚠ HYPOTHESIS: the `count: 0` for a producer is complete. ⛔ `architecture search --content` is **inventory-scoped**, so `.plan/` (git-ignored) and non-allowlisted dotfile trees are NOT swept. The zero is a trustworthy *"no producer in any inventoried bundle file"* and is **not** a statement about the whole tree. Confirm/refute by re-running the sweep with `Glob`/`Grep` scoped to the excluded paths (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: DISCHARGES the spec own coverage caveat: a direct sweep of the git-ignored .plan tree (20647 py files) outside the inventory found zero additional producers
- ⚠ HYPOTHESIS: the two in-the-wild carriers were written by a path that no longer exists. ⛔ NOT corroborated — D0 owns it and may return `indeterminate`. Confirm/refute at `manage-references/scripts/_references_core.py` and the `branch-cleanup` write sites (verify-at-outline).
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED as stated: git log --all -S plan_creation_sha over marketplace/ and .claude/ returns only #458 and #1343, neither a producer -- the field was never written by tracked source. Re-scoped.
- ⚠ HYPOTHESIS: the out-of-footprint edits the reporting projects name would in fact have been caught by a working guard. ⛔ **Foreign-corpus evidence, NOT corroborated here.** Their instances are theirs; what this epic established first-party is the guard's SILENCE, not the catch rate. Confirm/refute only if a reporting project supplies the diff (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Foreign-corpus catch-rate claim explicitly not corroborated by this orchestrator per the spec own text

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — the `ReferencesData` schema (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py` — a producer verb, if D0 sites it here (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` — the canonical block for any new verb (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — the plan-creation stamp site, if D0 sites it here (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — read-mostly; the consumer is CORRECT and is expected to change little or not at all (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — the guard's documented contract (D3) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-references/**` — the D1/D2 controls (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/**` — the D3 controls (verify-at-outline)

## Dependencies and Sequencing

- ⚠ **Overlaps `PLAN-TRUTH-098` (SHIPPED, #1359)** — *plan footprint is unknowable to its own graders* — which landed the `realized_footprint` capture. **Re-ground against the post-`-098` tree**: the realized side already exists, and this spec supplies only the missing BASELINE side. ⛔ Do not re-derive footprint capture.
- ⚠ **Adjacent to `PLAN-TRUTH-104`** (*a clear verdict over an empty population is reported as a checked negative*). ⛔ **Keep separate.** `-104`'s subject is a consumer that DISCARDS a published population; this guard's consumer publishes its population correctly and is starved of input. **Same archetype, opposite end of the pipe** — naming the archetype in both shipped docs is right; sharing code is not.
- ⚠ **Adjacent to `PLAN-TRUTH-111`** (*observed defects from the live-plan sweep*). This member was considered for a fold there and **deliberately kept out**: `-111` is a dated grab-bag whose D0 re-grounds a 2026-08-24 snapshot, and its own spec instructs outline to split it if members diverge. This one diverges.
- ⛔ **Re-derive `corpus cross-check` before emitting.** The sibling-epic constraint has moved twice in two days and this spec's declared surface has never been machine-checked against it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-138-the-scope-creep-guard-has-no-producer-and-has-never-measured-anything.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐⭐⭐ FOLDED 2026-09-05 (c) — PLAN-TRUTH-089 drain (1 message). A SECOND GUARD, STARVED BY A SECOND NEVER-WRITTEN FIELD.

- **`planning-lane-...-008`** — *no completed task record persists `changed_files`, so `ARTIFACT_EMISSION`
  can never run.*

  ⭐⭐ **The same shape as this spec's subject, at a different guard, with a different missing field — which
  is what turns a single instance into a CLASS.** `ARTIFACT_EMISSION` is specified in detail: a population
  rule (`N of M change-qualified completed tasks emitted >= 1 [ARTIFACT] line`), `M` restricted to
  completed tasks whose **own** diff is non-empty, two findings partitioning the incomplete range, and an
  explicit prohibition on substituting the unqualified completed-task count for `M`. **The qualification
  needs each task's own realized change set, and no task record carries a `changed_files` list.**

  ⭐⭐⭐ **AND THE GUARD BEHAVED PERFECTLY — this is the positive control this spec needs.** The extractor
  reported `completed_tasks: 25`, `tasks_with_artifacts: 8`, `change_attribution: unavailable` with a
  stated reason, and **`eligible_tasks` / `eligible_tasks_with_artifacts` / `eligible_tasks_without_artifacts`
  ABSENT from the payload rather than reported as zero.** No emission finding was made.

  ⛔ **So D0's population is NOT "guards that report a clean zero" — it is "guards whose producer was never
  built", and the two guards found so far BOTH decline to publish the zero.** That inverts the spec's
  framing in a way outline must absorb: **the consumers in this class are the well-behaved part, and a
  sweep that hunts for dishonest zeros will find neither of them.** Search for unwritten producers of
  documented inputs instead.

  ⚠ **Expected Surface widened in this same act**:
  `marketplace/bundles/plan-marshall/skills/manage-tasks/**` — the completed-task record and its
  `changed_files` field — and
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md`
  — the `ARTIFACT_EMISSION` invariant (HYPOTHESIS, verify-at-outline).

## ⭐ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (1 claim contradicted, 1 CAVEAT DISCHARGED)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 5 | the two in-the-wild carriers were written by a path that no longer exists | **REFUTED as stated** — `git log --all -S plan_creation_sha` over `marketplace/` and `.claude/` returns only **#458 and #1343**, and **neither is a producer**. The field was never written by tracked source at all. |

⭐⭐⭐ **AND THE SPEC'S OWN COVERAGE CAVEAT IS DISCHARGED — claim 4 is now CORROBORATED by a direct
sweep, not left as a hypothesis.** The spec warned that `architecture search --content` is
inventory-scoped, so its zero could not speak for the git-ignored `.plan/` tree. **That tree was swept
directly this pass — 20 647 Python files outside the inventory — and it holds ZERO additional
producers.**

⇒ **The absence claim is now established over BOTH populations, and D0's first deliverable shrinks
accordingly**: it no longer needs to establish that no producer exists, only to decide **where the
producer should go**. ⛔ **Keep the two populations named separately in the shipped doc** — inventoried
bundle source and the git-ignored tree are different sweeps with different instruments, and collapsing
them into one "we checked everywhere" is the completeness assertion this epic exists to prevent.

## ⭐⭐ FOLDED 2026-09-06 — `review-apparatus-033` drain (1 item). SECOND INDEPENDENT REPORT OF MEMBER 2.

### Item 5 (`-003`) — record `changed_files` on completed task records so `ARTIFACT_EMISSION` can measure

⛔ **This is not a new member — it is a SECOND, INDEPENDENT report of the member folded here on
2026-09-05** (`planning-lane-...-008`), arriving from a different plan, a different epic's drain, and a
different run.

⭐⭐ **The recurrence is the information.** One report of a never-written field is a gap; two
independent reports naming **the same field, the same consumer, and the same starved invariant** make it
a standing property of the task record rather than an artefact of one plan's instrumentation. ⇒ **D0's
population claim strengthens without a new sweep.**

⭐ **And it re-confirms the inversion this spec already absorbed**: the reporting side keeps behaving
correctly — `ARTIFACT_EMISSION` still declines to publish a zero it cannot qualify. **Both reports
describe a starved consumer, neither describes a dishonest one.** The class remains *guards whose
PRODUCER was never built.*

## ⭐⭐ FOLDED 2026-09-06 (b) — a FIFTH independent corpus, from a Java repo

> *"Scope-creep checking never ran either, and it's worse than plan-local: `plan_creation_sha` has no
> writer anywhere in the bundle, only a reader. That guard resolves `no_baseline_sha` on **every plan in
> this project**. I verified the committed file set **by hand** against the deliverables; that's my
> check, not the guard's."*

⇒ **n = 5 independent corpora** — this checkout, the first reporting project, the 2026-09-04 machine,
TokenSheriff, and now a Java project. ⭐ **And this reporter reached the SAME diagnosis independently:
"no writer anywhere in the bundle, only a reader."** That is D0's conclusion, derived a fifth time by
someone who did not read this spec.

⭐⭐⭐ **THE NEW INFORMATION IS THE SUBSTITUTE, NOT THE ABSENCE.** *"I verified the committed file set by
hand against the deliverables; that's my check, not the guard's."* ⇒ **Where the guard is starved, the
work does not stop — it moves to a human, silently, and the finalize record shows a guard that ran.**
⛔ **That is the cost this spec has been unable to price**: not undetected creep, but **undetectable
substitution.** A hand check leaves no artifact the ledger can read, so a plan whose scope was verified
by hand and one whose scope was never verified at all are **indistinguishable downstream.**

⚠ **Keep this distinct from the catch-rate claim, which stays `unverifiable`.** This does not establish
how often creep occurs; it establishes that **the guard's silence is being absorbed by people rather
than surfaced** — which is a stronger argument for D2 than any incidence figure.

## ⭐⭐ FOLDED 2026-09-07 (b) — a SIXTH independent corpus

`lessons-handling-26-09-04-01-015` (`plan-marshall:manage-references`) reports it again, in the same
words the other five reached independently: **the scope-creep guard never ran on ANY task, because
`references.json` carries no `plan_creation_sha`.**

⇒ **n = 6.** ⛔ **Six independent reporters, one diagnosis, zero disagreement — and the producer still
does not exist.** ⚠ **The count is now the least interesting thing about this spec.** Six corroborations
add no information the first three did not; **what they measure is the DELAY**, not the defect.

⭐ **Record that plainly in the shipped doc**: this is a defect whose evidence was complete after report
one and which accumulated five more while unowned. **A corroboration count is not a priority signal, and
treating it as one is how a fully-diagnosed defect stays unowned for a week.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-145-declarations-that-cannot-learn-and-cannot-go-stale.md` (PLAN-TRUTH-145)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
