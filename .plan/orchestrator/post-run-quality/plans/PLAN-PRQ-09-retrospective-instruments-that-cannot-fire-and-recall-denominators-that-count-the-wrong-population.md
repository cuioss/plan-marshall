# PLAN-PRQ-09: Retrospective instruments that cannot fire, and recall denominators that count the wrong population

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-17 from a full classification sweep of the 194-lesson corpus (49 candidate files read in
full; 23 classified as post-run-quality by subject). Every member below is a lesson filed first-party by a
plan that hit it, and all are preserved verbatim in this epic at
`.plan/local/orchestrator/post-run-quality/lessons/{id}.md`.

⛔ These lessons were **recorded and never actioned** — the oldest is 2026-08-27, the newest 2026-09-15.
That the corpus held six independent reports of the same instrument family for three weeks without one
reaching a plan is itself the `PLAN-PRQ-05` contract-reach metric, measured on this epic's own subject.

## Objective

**Six retrospective instruments produce a clean reading they did not earn** — three because the check
cannot fire at all, three because the number they publish is computed over the wrong population. Unlike
`PLAN-PRQ-02`, which fixes producers that read a population they never saw, every member here reads a
population that IS available and counts the wrong thing in it, or is structurally unable to fire.

## Deliverables

Six deliverables. D0 is a gate.

**D0 — GATE: classify every registered aspect's guard and denominator.** For each of the 17 aspects
(⛔ **RE-GROUNDED 2026-09-18, cleanup: `retro_sections.SECTION_SPEC`/`valid_aspect_keys()` returns 17
registerable keys at HEAD, not 16 — same correction as `PLAN-PRQ-02` D0, same population**), state (a)
whether any precondition it carries can be falsified by the very condition it audits, and (b) what
population each published ratio is computed over. ⛔ Publish both, with sizes. The six members below were
found by six separate plans over three weeks; a seventh is likelier than not.

**D1 — A precondition may not key on the artifact whose absence is the defect.** `RE_ENTRY_COVERAGE`'s
guard is the re-entry marker it exists to audit, so **total absence skips silently** while partial absence
reports. Invert it: the guard fires on the population, and absence is the finding.
(Lesson `2026-09-08-22-007`.)

**D2 — A detector whose producer never writes: give it the producer, or retire it.** `ARTIFACT_EMISSION`
reads a per-task `changed_files` that tasks never persist, so it is inert on every plan ever run — the same
shape as `scope_creep_check`'s missing `plan_creation_sha` writer. ⛔ **NARROWED 2026-09-18 (cleanup,
`checked_at: 1605831c5`): the "renders as a pass" half is ALREADY FIXED.**
`references/logging-gap-analysis.md:127-152` now requires `change_attribution: measured|unavailable` be
read FIRST, and on `unavailable` the three dependent keys are ABSENT rather than a false zero — implemented
at `analyze-logs.py:1034-1076,:1824`, with the mixed-corpus partial-recording case handled at `:133-142`.
D2 is therefore a pure binary now, with no honesty-of-degradation work left: give `ARTIFACT_EMISSION` the
`changed_files` producer, or retire the detector. Note the older non-`changed_files` branch (zero
`[ARTIFACT]` lines against a non-empty footprint) still fires as `error`, so the aspect is not wholly
inert. (Lesson `2026-09-15-08-005`.)

**D3 — A producerless section row escalates instead of settling itself.** A `SECTION_SPEC` row with no
producer renders clean as `sections_omitted`, which reads as *"nothing to report"* rather than *"this
section has no author"*. It is an operator proposal, not an in-plan decision. (Lesson `2026-08-31-09-001`.)

**D4 — The recall denominators count the population the claim is about.** Three independent errors, one
deliverable because all three are the denominator of the same `_extract_bullet_entries` /
`affected_files_recall` pipeline: `affected_files_recall` counts **delete-intent and foreign-checkout
paths** into a same-repo diff denominator (lesson `2026-09-03-23-004`), the plan-level average **hides a
deliverable that shipped two thirds of a completeness-quantified surface** (lesson `2026-09-05-07-006`),
and ⛔ **FOLDED 2026-09-19** (inbox `prq-06-a-lane-override-that-cannot-take-effect-is-006.md`) —
`_extract_bullet_entries`'s admission test is bare truthiness (`if path: entries.append(...)`), so the
solution-outline's literal `(none)` placeholder is admitted as a declared path, inflating the denominator
by one per placeholder (confirmed: `PLAN-PRQ-06` recomputed `27 declared / 24 found / 88.9%` against the
reported `28 / 24 / 85.7%`). Publish per-deliverable recall alongside the plan-level figure, exclude from
the denominator what the diff cannot contain, AND reject non-path placeholder tokens at admission —
`(none)` is the confirmed instance; the admission test should recognise a placeholder vocabulary, not only
truthiness.

**D5 — An aspect verifies a claim handed to it before filing it as a finding, and the controls.** A defect
claim arriving in the dispatch context is a LEAD; restating it as a retrospective finding launders an
unverified assertion into the report (lesson `2026-08-27-16-003`). Plus the matched controls: a guard that
can fire still fires, a detector with a live producer still reports, and each corrected denominator is
pinned by a case where the old and new figures differ.

## Claim Labels

Every claim below is OBSERVED by the plan that filed the cited lesson, and each lesson is preserved in this
epic at `lessons/{id}.md`. ⛔ They are first-party reports, not this orchestrator's derivations — re-ground
each against the named instrument at HEAD before scoping (verify-at-outline for all six).

⛔ **FOUR OF THE SIX CITED LESSONS ARE ALREADY RETIRED FROM THE LIVE CORPUS** — `2026-08-27-16-003`,
`2026-08-31-09-001`, `2026-09-03-23-004`, `2026-09-05-07-006` were removed on 2026-09-17 by a concurrent
orchestrator session, with `completely_covered` tombstones. Two consequences bind this plan:

1. **Read them from `lessons/{id}.md`, never from the corpus** — `manage-lessons get` will return
   `not_found` for all four, and that `not_found` is correct.
2. ⛔ **This plan MUST NOT call `manage-lessons remove` on any id it cites.** They are already retired, and
   `remove` on an absent id is the documented path that destroys a DIFFERENT lesson when retried. There is
   no lesson-retirement work in this plan at all — retirement was completed by the sweep that staged it.

⚠ The `completely_covered` verdict on those four asserts their rule now lives in a named clause. It does
not yet: it lives in THIS spec, which is staged. Landing these deliverables is what makes those tombstones
true retroactively, which is a reason to land them rather than a defect in them.

- OBSERVED (lesson `2026-09-08-22-007`): `RE_ENTRY_COVERAGE`'s precondition is the re-entry marker whose
  absence is the defect, so a run with no markers at all skips the rule silently.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: logging-gap-analysis.md:81-92 verbatim: precondition is at least one Re-entering-execute-phase work.log line, closing 'Plans without any Re-entering line skip this rule entirely.' Still keyed on the artifact whose absence is the defect. Impl site analyze-logs.py:866. D1's inversion is unmade.
- OBSERVED (lesson `2026-09-15-08-005`): tasks never persist `changed_files`, so `ARTIFACT_EMISSION` has
  been inert on every plan.
  - verdict: contradicted | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: yes | evidence: Producer half holds (zero hits for changed_files in manage-tasks/**), but the 'renders as a pass' half is ALREADY FIXED: logging-gap-analysis.md:127-152 now requires change_attribution:measured|unavailable be read FIRST, with the three keys ABSENT (not zero) on unavailable -- implemented at analyze-logs.py:1034-1076,:1824, mixed-corpus case handled at :133-142. D2 is narrowed to only 'give it the producer or retire it'.
- OBSERVED (lesson `2026-08-31-09-001`): a producerless `SECTION_SPEC` row renders as `sections_omitted`.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: compile-report.py still terminates in a two-bucket classification (:744 returns content/sections_written/sections_omitted/sections_dropped, emitted :1115). Recent hardening (:640-687) separates lost payload from omitted but does NOT distinguish no-payload from no-author. A producerless row still lands in sections_omitted. D3's escalation is unbuilt. Note: this lesson's own tombstone (completely_covered) is not yet accurate, per its own recorded caveat.
- OBSERVED (lesson `2026-09-03-23-004`): delete-intent and foreign-checkout paths enter a same-repo diff
  denominator.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Denominator filter excludes read intent only: check-artifact-consistency.py:345 filters entry['intent'] != _READ_INTENT. Four-valued vocabulary at constants.py:301-310 includes STEP_INTENT_DELETE='delete' -- a delete-intent path IS counted. Foreign-checkout handling absent entirely (0 matches for 'foreign' in the 937-line file). details publishes read_intent_excluded but no delete/foreign counters.
- OBSERVED (lesson `2026-09-05-07-006`): a deliverable shipping 67% of a completeness-quantified surface
  is averaged away at plan level.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Per-deliverable machinery exists but publishes declaration state only, never recall: extract_affected_files_per_deliverable (:308) and _declaration_state_per_deliverable (:348) feed check_affected_files_recall (:382), which consumes them solely to detect unparseable deliverables (:437-465). No per-deliverable recall ratio on any branch. D4's ask is unbuilt.
- OBSERVED (lesson `2026-08-27-16-003`): a handed defect claim was restated as a finding without
  verification.
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Historical event not re-derivable (plan artifacts gone), but the governing clause D5 would add does NOT exist at HEAD: regex sweep for a handed-claim/lead-verification rule returns 0 over 2993 files scanned; no such rule in plan-retrospective/references/ (15 files) or standards/. Lesson text preserved at lessons/2026-08-27-16-003.md. D5's rule is unwritten.
- ⚠ HYPOTHESIS: these six are the whole population. ⛔ Asserted by nobody; D0 owns the derivation.
  - verdict: unverifiable | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: D0's own 17-aspect classification sweep was not performed in this corroboration pass. But the COUNT in D0's own instruction is already known wrong: 17 registerable aspects exist at HEAD (retro_sections.SECTION_SPEC, valid_aspect_keys()==17), not 16 -- same finding as PLAN-PRQ-02 claim 0.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — the aspect producers (D1–D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — `SECTION_SPEC` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/` — the logging-gap rules and the recall definitions (D1, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/**` — the `changed_files` producer D2 needs, if D2 chooses the writer over retirement (verify-at-outline)
- OBSERVED: `test/plan-marshall/plan-retrospective/` — the controls (D5)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Shares `plan-retrospective/scripts/` with `PLAN-PRQ-01`, `PLAN-PRQ-02` and `PLAN-PRQ-08` — at
  `parallelization_scope: 1` the gate serializes them; do not raise the knob without re-reading this set.
- D2's writer half touches `manage-tasks/**`, which `truthful-signals` PLAN-TRUTH-153 also declares.
  **Cross-epic and invisible to both gates.**
- ⛔ **Split-guard note, 2026-09-19.** Two further inbox findings (`script-failure-analysis`
  misclassifying executor-guard firings as product bugs; `script_cost_rollup` collapsing a correct wait
  and a stalled poll into one undifferentiated cost figure) share this spec's THEME — "reads an available
  population and counts the wrong thing in it" — but are a DIFFERENT sub-tier (spend/diagnostic aspects,
  not recall/coverage aspects) and would have pushed this spec from 6 to 8 deliverables. Staged separately
  as `PLAN-PRQ-11` rather than folded here, per the Scope-Bloat Split Guard.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-09-retrospective-instruments-that-cannot-fire-and-recall-denominators-that-count-the-wrong-population.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
