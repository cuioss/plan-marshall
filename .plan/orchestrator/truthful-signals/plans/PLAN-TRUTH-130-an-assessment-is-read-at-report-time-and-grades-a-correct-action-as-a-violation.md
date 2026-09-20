# PLAN-TRUTH-130: An assessment is read at report time and grades a correct action as a violation

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from inbox drain messages `dual-homed-hook-install-renders-identically-005.md`,
> `-007.md` and `-012.md` — three first-party observations from PLAN-TRUTH-102's own run (PR #1384,
> merged `19453cb1b`), all three naming the same mechanism from different surfaces.

## Objective

**A point-in-time judgement is stored without an effective-from instant, and every reporting surface
that consumes it compares an action against the judgement's CURRENT value rather than the value in
force when the action was taken.** The result is a confident RED over a correctly-answered question —
this epic's archetype inverted, and the more corrosive direction, because a report that manufactures
false defects spends the reader's scarce attention on non-problems and trains them to discount the
whole instrument.

⛔ **In the clearest instance the overriding authority was the OPERATOR.** The report grades the run
for obeying an explicit operator instruction, which is precisely the input that should be unappealable.

**Three members, one mechanism:**

1. **Assessments are never re-derived when the outline is widened.** `check-outline-vs-shipped`
   reported `exclude_violated: count 1, denominator 6, population certain_exclude_assessed_paths`
   naming `platform-runtime/SKILL.md`, and labelled it in its own finding text *"the one unambiguously
   bad outcome"*. It is not a bad outcome — it is a stale assessment, and the timeline shows it:
   - `15:34:32Z` — the assessment gate writes 12 assessments (6 `CERTAIN_INCLUDE`, 6
     `CERTAIN_EXCLUDE`, 0 `UNCERTAIN`); that path is assessed `CERTAIN_EXCLUDE`.
   - `15:50:17Z` — the Q-Gate **fails** deliverable 2, naming the same path (L62, L179) as still
     asserting the two-value domain the plan widens ⇒ the deliverable's success criterion is
     unsatisfiable with the declared file list.
   - `16:00:16Z / 16:00:22Z` — the outline is revised, D2 widened from 3 files to 5, and the path
     becomes a declared `write-replace` file.
   - The assessment is **never rewritten**.

   ⭐ The review-gate re-entry path rewrites a deliverable's declared file set **without re-running or
   invalidating the assessments that scored those files**, and nothing in the store records that an
   assessment predates the widening.

2. **An operator-approved mid-run scope addition never returns to the outline.** During finalize the
   pre-push module-tests gate came back red on exactly one test (a `manage-architecture` subprocess
   timeout, 30s budget against a 24-57s verb, 19,525 others passing). The operator answered *"Fix the
   test budget in this plan"*. The fix landed and shipped. **The file entered `references.json` and
   never entered `solution_outline.md`**, so two first-party checks report the approved change as a
   defect signature: `check-artifact-consistency` → `affected_files_exact_match: warn` with the path
   in `references_only`; `check-outline-vs-shipped` → `touched_but_unassessed: 2 of 9`, same path a
   member. ⭐ **There are two write paths into a plan's declared surface — the outline (authored,
   assessed, Q-Gated) and the operator answer applied in-flight (recorded in `references.json` only)
   — and the second has no return path to the first.**

3. **The general form: two reporting surfaces independently produced a wrong verdict from a correct
   run.** The common cause is that both compare an action against a stored value **with no notion of
   when the value held**. ⛔ The error can land in EITHER direction — an action taken under the
   previous value looks like a violation, and an action taken under the new value looks compliant even
   if it preceded the revision. This run happened to catch the false-positive direction; nothing makes
   that the likely one.

## Deliverables

1. **D0 — GATE: enumerate every reporting surface that grades a recorded action against a mutable
   stored judgement.** ⛔ **Publish the swept population and its size.** The retrospective named two
   surfaces; **that is the sample it happened to traverse, not an enumeration**, and the sending
   message says so in its own words. D0 may legitimately find the population is exactly those two, but
   it must DERIVE that rather than inherit it.
2. **D1 — an assessment carries an effective-from instant, and the report joins on it.** Test each
   action against the assessment in force **at that action's timestamp**, not against the current one.
   ⭐ Both ledgers already carry timestamps — `manage-metrics reconcile-ledgers` demonstrates the
   pattern in-tree — so this is a join, not new instrumentation.
3. **D2 — supersession is recorded, not overwritten.** When an assessment is overridden, keep the
   prior value with its window. ⭐ Two in-tree precedents for *"stays resolvable, stops presenting as
   live"* already exist and one of them should be reused rather than a third invented: the
   `manage-lessons` tombstone model and the `inbox supersede` envelope.
4. **D3 — an operator override is distinguishable from drift, at the report.** The report must be able
   to say *"acted under the assessment then in force, superseded by operator at T"* — never
   `exclude_violated`. ⛔ **`exclude_violated` must partition** into *violated a live exclusion* and
   *contradicted by a later approved widening*; the second is not a violation and must not be reported
   as one.
5. **D4 — close the outline write-back gap (member 2).** Either append an operator-approved path to
   the owning deliverable's declared file list with explicit provenance
   (`(operator-approved, {phase}, {timestamp})`), or have `check-artifact-consistency` and
   `check-outline-vs-shipped` read a provenance marker on the `references.json` entry. ⭐ **The second
   is the cheaper arm and the messages say so**; D4 must cost both and record the rejected one.
6. **D5 — matched controls.** A genuine exclusion violation must still report as one, and a genuine
   undeclared drift must still report as `references_only`. ⛔ **The negative control is load-bearing
   here beyond the usual**: a fix that silences `exclude_violated` wherever an override exists would
   convert a false-positive instrument into a blind one, which is strictly worse.

## Claim Labels

- OBSERVED: the four-event timeline of member 1, quoted from this plan's own `decision.log` at 15:34:32Z, 15:50:17Z, 16:00:16Z and 16:00:22Z.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-102 decision.log and plan dir no longer exist under .plan/local/plans (only NO_PLAN remains)
- OBSERVED: `check-outline-vs-shipped` reported `exclude_violated` 1 of 6 naming `platform-runtime/SKILL.md`, and `manage-solution-outline list-deliverables` shows D2 declaring that path with `intent: write-replace`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The specific check-outline-vs-shipped / list-deliverables reading is from a removed plan dir; not reproducible at HEAD
- OBSERVED: member 2's operator turn, the landed test-budget fix, and both check outputs (`affected_files_exact_match: warn`; `touched_but_unassessed: 2 of 9`).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Member 2 operator turn and check outputs are from a removed plan dir; not reproducible at HEAD
- OBSERVED: the assessment gate wrote 12 assessments with 0 `UNCERTAIN` and none was rewritten after the widening.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 12-assessment write count is from a removed plan dir; not reproducible at HEAD
- HYPOTHESIS: the two named reporting surfaces are the whole affected population. ⛔ **Explicitly refused by the sending message** — *"that is the sample it happened to traverse, not an enumeration"*. D0 settles it (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D0 population sweep not independently completed; the assessments.jsonl consumer search found only check-outline-vs-shipped.py
- HYPOTHESIS: assessments are stored with no effective-from field at all, rather than with one no reader consults. Confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § the component-assessment record (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: add_assessment in _findings_core.py carries hash_id/timestamp/file_path/certainty/confidence/agent/detail/evidence only -- no effective-from field
- HYPOTHESIS: the review-gate re-entry path (`phase-3-outline` Step 3c) is the only writer that widens a declared file set without touching assessments. ⛔ NOT checked (verify-at-outline).
- Verify-first clause: before D1, settle whether the assessment store's existing timestamps are WRITE times or EFFECTIVE times. If they are write times only, D1 is a schema addition rather than a join and re-scopes accordingly.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _findings_core.add_assessment stamps timestamp() at write time only; no separate effective-from field exists in the record

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/**` — the assessment record and its lifecycle (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/**` — `check-outline-vs-shipped` and `check-artifact-consistency` (D3, D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-3-outline/**` — the Step 3c review-gate re-entry path (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/**` — the provenance marker on an in-flight footprint addition (D4) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-findings/**`, `test/plan-marshall/plan-retrospective/**` — the D5 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Overlaps with `PLAN-TRUTH-110`** (*a plan decides what the epic learns and nothing audits that decision*), which claims `plan-retrospective/**` and `manage-findings/**` in full. ⛔ **SERIALIZE — do not pair.** Both rewrite retrospective checks; a half-landed pair leaves one check reading a partitioned `exclude_violated` and the other not.
- Adjacent to: `PLAN-TRUTH-104` (a clear verdict over an empty population) — that is a verdict with nothing behind it; this is a verdict with something *stale* behind it. Different remedies, keep separate.
- Adjacent to: `PLAN-TRUTH-117` (restated counts and underived completeness claims) — D0's population obligation is the same discipline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-130-an-assessment-is-read-at-report-time-and-grades-a-correct-action-as-a-violation.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-008`** — *a file assessed `CERTAIN_EXCLUDE` and declared read-only was written to anyway.* `manage-tasks/standards/task-contract.md` carried **two independent scope declarations, both saying it would not be modified** — outline assessment `CERTAIN_EXCLUDE` (1 of only **3** `certain_exclude_assessed_paths` on the whole plan) **and** deliverable 1’s `Files to survey:` with `intent: read`. **It appears in the realized footprint**, and `check-outline-vs-shipped` reports it as `exclude_violated: 1 of 3`, in that aspect’s own words *“the one unambiguously bad outcome.”*

  ⭐⭐⭐ **The root cause is the sharpest statement of this spec’s subject yet recorded, and it is NOT that a check was missing.** Neither declaration is enforced at write time — **and the THIRD check, the one that does run, PASSES.** Scope creep is measured against the full declared surface **including read-intent entries**, so **a file declared read-only is BY CONSTRUCTION never scope creep.** The declared-surface check therefore reports the file as in-scope and expected, while the intent annotation and the assessment both say it should not have been touched. ⛔ *“The failure is not that a check was absent; it is that the check that fired answers a DIFFERENT QUESTION from the two that were violated, and its green result is the one a reader sees first.”*

  ⚠ **Note the direction: this is the mirror of the instance this spec was staged on.** `dual-homed-...-005` recorded a correct action graded as `exclude_violated` (a false RED over a stale assessment); this records a genuine violation absorbed by a green sibling check (a false GREEN over a live one). **Both come from comparing an action against a declaration with no shared notion of what the declaration meant.** D3’s partition must therefore serve both directions, not just the false-positive one.

  **Ask:** when a path carries a `read` intent or a `CERTAIN_EXCLUDE` assessment **and appears in the realized footprint**, surface it as a distinct outcome class rather than letting the declared-surface pass absorb it. ⭐ *“`check-outline-vs-shipped` already computes `exclude_violated` correctly; the gap is that no gate consumes it and the sibling scope-creep verdict reads clean over the same file.”*

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§6.3 — an operator-confirmed decision is NOT review-proof, and this is the highest-stakes member of this spec's family.** A redirect-policy change carried **the strongest authorization the pipeline can produce** — explicit operator confirmation at refine time. A later review found the change **opened an SSRF-shaped egress hole.**

  ⭐⭐ **The mechanism is precisely this spec's subject — a stored judgement read at the wrong moment:** *"the operator confirmed a BEHAVIOUR at a point where the SECURITY CONSEQUENCE had not been analysed, and by the time it arrived the decision carried a sign-off — and the natural pull is to treat that as settling the question."*

  > ⛔⛔ **An operator decision authorizes the change that was DESCRIBED to the operator, not every consequence discovered later.** Confirm the finding against the code first; then treat it as **new information invalidating the premise the operator confirmed under**, and reopen. **Reverting plus deferring to a follow-up plan is legitimate; shipping the hole with the sign-off cited as cover is not.**

  ⚠ **Note how this cuts against `dual-homed-...-012`, already folded into this spec.** That message argued an operator override is *"precisely the input that should be unappealable"* and that grading a run for obeying it is wrong. **§6.3 argues an operator sign-off must NOT immunise a consequence the operator was never shown.** ⛔ **Both are correct and they bound D3 from opposite sides:** the report must not grade a run for obeying an override, **and** an override must not be citable as cover for an unanalysed consequence. **D3's partition has to express authority-scope, not just authority-presence** — *what was authorized*, not merely *that something was*.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (1 claim contradicted)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 6 | the outline phase has no path that revises deliverables without touching assessments | **REFUTED** — `phase-3-outline`'s own Lessons Consult step (`light-lane.md:155`) revises deliverables via `manage-solution-outline update` **and touches no assessment** |

⭐⭐ **The refutation supplies the plan's missing mechanism rather than removing it.** The spec argued
that a correct action gets graded as a violation because the assessment is read at report time; claim 6
assumed no legitimate revision path existed. **One does, and it is on the mainline outline lane.** ⇒ That
path is the **worked example** of a correct action the grader will mis-score, and D0 should key its
population on it instead of hunting for the class abstractly.

⚠ **Claims 0-4 are all `unverifiable` because their source plan directory no longer exists.** ⛔ That is
NOT a refutation and must not be read as one — the evidence is gone, not contradicted. **D0 must
re-derive the instance set from a LIVE plan** rather than citing `PLAN-TRUTH-102`, whose artifacts have
been reclaimed. ⭐ Claims 5 and 7 both corroborate independently at `_findings_core.add_assessment`
(no effective-from field; timestamp stamped at write time), so **the mechanism half stands on current
source and does not depend on the lost evidence.**

## ⭐ FOLDED 2026-09-06 — `review-apparatus-033` drain (1 item)

### Item 4 (`-001`) — split `include_unrealised` by declared intent in `check-outline-vs-shipped`

⭐⭐ **This lands squarely on the consumer this spec's own re-grounding already isolated.** The
cleanup's `assessments.jsonl` consumer search found **exactly one** reader — `check-outline-vs-shipped.py`
— and this item is a defect in that same reader: `include_unrealised` lumps together deliverables that
were **declared read-only** with those that were **declared for modification and never touched.**

⛔ **Those two are not the same finding and do not share a remedy**: an unrealised read-only entry is
**correct behaviour**, an unrealised modify entry is a **shortfall**. Collapsing them makes the grader
report a correct action as a violation — **which is this spec's title.** ⇒ **Fold, do not stage: it is
the same defect at the same reader, arriving with a second instance.**

⚠ **Expected Surface unchanged: adds no file surface** — `plan-retrospective/scripts/check-outline-vs-shipped.py`
is already in this spec's declared set.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-152-the-retrospective-quality-chain-and-assessments-graded-at-report-time.md` (PLAN-TRUTH-152)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
