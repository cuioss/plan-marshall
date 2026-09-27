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
`.plan/orchestrator/post-run-quality/lessons/{id}.md`.

⛔ **Folded 2026-09-22 from inbox `lessons-handling-26-09-22-01-001.md`, shared-component pair
`2026-09-20-08-009` (primary) / `2026-09-21-13-002`.** The seventh and eighth members of the family the
Objective already predicted ("a seventh is likelier than not"): Step 2.5's metrics reconcile is inert when
no phase accumulator file exists — the exact case it exists to catch (a D1-shape precondition-keyed-on-its-
own-defect instance); and the chat-signal pre-pass reports Tier 1 over a transcript truncated to its first
line (a wrong-population-denominator instance, D3's shape). Adds no new file/module surface — both sites
fall inside the already-declared `plan-retrospective/scripts/` directory entry.

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

⛔⛔ **D2 IS NOW FULLY DISCHARGED (cleanup, `checked_at: 7d82d5d90`) — RETIRE OUTRIGHT, do not re-narrow.**
The `changed_files` producer now exists and is wired: `manage-tasks.py:548-596`
`cmd_finalize_step_record_changed_files` re-reads the task record after a terminal close and calls
`_tasks_core.record_changed_files`, registered as the `finalize-step` handler at `manage-tasks.py:611`,
first-close-wins with absent-baseline/present-empty handled correctly, pinned by
`test_manage_tasks_artifact_emission.py`. Landed in `#1545` (`afce081b1`), which post-dates this spec's
`1605831c5` narrowing check. The only remaining ask ("give it the producer, or retire it") is done —
nothing is left to build for D2. At outline, drop D2 from the deliverable count.

**D3 — A section that HAS something to report is dropped as if it had nothing, three ways.** ⛔⛔
**WIDENED 2026-09-21** (inbox `retrospective-aspects-publish-verdict-003.md` and `-004.md`, filed by
`PLAN-PRQ-02`'s own retrospective — folded here rather than staged separately, per the Scope-Bloat Split
Guard; this spec was already at 6 deliverables). The original member (a producerless `SECTION_SPEC` row
escalating instead of settling itself, lesson `2026-08-31-09-001`) is now one of three ways a
non-empty section fails to render:
(a) **No producer at all** — a `SECTION_SPEC` row with no producer renders clean as `sections_omitted`,
which reads as *"nothing to report"* rather than *"this section has no author"*. It is an operator
proposal, not an in-plan decision. (Lesson `2026-08-31-09-001`.)
(b) **A producer that ran and has findings, dropped for an honest non-success status.**
`compile-report.should_emit` refuses any conditional fragment whose `status` is not `success` or absent —
so an aspect that honestly reports `status: unmeasured` (e.g. an undeliverable population) has its findings
silently deleted from the report, including `error`-severity ones. A bespoke carve-out already exists for
ONE aspect (`chat-history-analysis`, placed BEFORE the status guard specifically to avoid this), which is
evidence the gap is general, not incidental — the same problem was solved once, for one aspect, by special
case rather than by fixing the guard. Fix the guard to render any fragment carrying a non-empty `findings`
list regardless of status (preferred), or document the `status`-vs-degradation-field idiom explicitly and
generalise the existing carve-out away.
(c) **A producer that ran and has data, looked up at the wrong nesting level.** `analyze-logs` emits its
`dispatch_boundaries` block NESTED inside its own `log-analysis` result
(`bundle['log-analysis']['dispatch_boundaries']`), but `compile-report`'s `should_emit` looks it up as a
TOP-LEVEL key (`fragments.get('dispatch_boundaries')`) and finds nothing — so `Phase Dispatch Boundaries`
renders as `sections_omitted` (the benign "nothing to lose" bucket) even when the underlying data (103
dispatch-boundary rows, every phase `present: true`) is real and lost. SKILL.md's own row for this key
states two jointly-unsatisfiable things ("injected, never dispatched" and "rendered from the bundle under
the same key") — pick one disposition (read the nested block explicitly, or register the key at top level)
and make the doc and the code agree.
All three share one root shape: the omitted/dropped classification is meant for *genuinely nothing to
report* and is silently absorbing *something to report that the pipeline couldn't reach*. D3's control
(added to D5's matched-controls set) must assert that a section with real underlying data renders, for
all three failure shapes — not just the original producerless case.

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
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: logging-gap-analysis.md:81-92 precondition still keyed on the artifact whose absence is the defect; cluster_dispatches at analyze-logs.py:1102-1115 (prior citation :866 now stale, cache-read-ratio code). D1's inversion unmade
- OBSERVED (lesson `2026-09-15-08-005`): tasks never persist `changed_files`, so `ARTIFACT_EMISSION` has
  been inert on every plan.
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: NEW SINCE PRIOR CHECK: producer now exists and is wired. manage-tasks.py:548-596 cmd_finalize_step_record_changed_files, registered handler at :611, pinned by test_manage_tasks_artifact_emission.py, landed #1545 (afce081b1, post-dates prior check sha). D2 fully discharged, not merely narrowed -- recommend retiring D2 outright
- OBSERVED (lesson `2026-08-31-09-001`): a producerless `SECTION_SPEC` row renders as `sections_omitted`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: compile-report.build_document (:735-858) still three-bucket; producerless row -> should_emit False -> omitted; no no-author escalation anywhere; test_compile_report_partition_producer_differential.py pins absent->omitted. D3(a) unbuilt
- OBSERVED (lesson `2026-09-03-23-004`): delete-intent and foreign-checkout paths enter a same-repo diff
  denominator.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: extract_modification_intent_files (:347) excludes READ only; 4-valued intent vocabulary confirmed, DELETE counted; foreign-checkout handling absent from check-artifact-consistency.py (0 hits). NEW: manage-solution-outline now carries foreign-deliverable handling upstream -- D4's fix has a real declared signal to read
- OBSERVED (lesson `2026-09-05-07-006`): a deliverable shipping 67% of a completeness-quantified surface
  is averaged away at plan level.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: extract_affected_files_per_deliverable (:310-319) returns a flat list despite its name; recall computed (:510-536) at PLAN level only, no per-deliverable ratio on any branch. _extract_bullet_entries admits on bare truthiness -- placeholder inflation confirmed unmade
- OBSERVED (lesson `2026-08-27-16-003`): a handed defect claim was restated as a finding without
  verification.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: governing lead-verification clause D5 would add does not exist at HEAD: content sweep for handed-claim/LEAD vocabulary returns 0/3097 files. Rule's absence, which D5 addresses, cleanly derived
- ⚠ HYPOTHESIS: these six are the whole population. ⛔ Asserted by nobody; D0 owns the derivation.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: D0's own 17-aspect classification sweep not performed in this read-only pass, whole-population hypothesis stays open by construction. Correction: D0's text already reads 17 and 17 IS correct at HEAD (SECTION_SPEC 19 rows, 2 underscore-prefixed, valid_aspect_keys returns 17) -- no further count correction needed
- OBSERVED, folded 2026-09-21 (inbox `retrospective-aspects-publish-verdict-003.md`, filed first-party by
  `PLAN-PRQ-02`'s own retrospective): `compile-report.should_emit` (lines 145-152) refuses any fragment
  whose `status` is not `success`/absent, dropping an `unmeasured`-status fragment's `error`-severity
  finding from the report entirely; a pre-existing bespoke carve-out for `chat-history-analysis` (placed
  before the guard) is direct evidence the gap is general. Grounds D3(b) above.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: chat-history-analysis carve-out at compile-report.py:145-148, status guard :149-152, exact at HEAD; test-pinned via test_compile_report_partition_producer_differential.py. Narrowing: loss now reported loudly under sections_dropped with warning status -- only the 'silent' half is superseded, findings still never reach the report body
- OBSERVED, folded 2026-09-21 (inbox `retrospective-aspects-publish-verdict-004.md`, same source):
  `analyze-logs` emits `dispatch_boundaries` nested under `bundle['log-analysis']['dispatch_boundaries']`;
  `compile-report`'s `should_emit` looks it up as a top-level key and finds nothing, so `Phase Dispatch
  Boundaries` renders `sections_omitted` despite 103 real rows across all three phases. Grounds D3(c)
  above.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: dispatch_boundaries present in analyze-logs bundle (:2203/:2110) but nothing registers the trigger key top-level (0 hits for --aspect dispatch registration). SKILL.md:202/:204 confirms this was a DELIBERATE disposition over a structural rename -- D3(c) must discharge a chosen position, not a slip
- OBSERVED, folded 2026-09-21 (inbox `retrospective-aspects-publish-verdict-007.md`, same source, action
  #3 of its `llm_to_script_opportunities` finding): proposes extending `check-artifact-consistency` to
  publish PER-DELIVERABLE recall beside its existing global recall, so D4's "hides a deliverable that
  shipped two thirds of a completeness-quantified surface" failure (lesson `2026-09-05-07-006`) is read
  from code rather than recomputed by hand each time, and the read-intent exclusion rule applies once.
  Confirming evidence for D4 above, not a new deliverable — D4 already stages "publish per-deliverable
  recall alongside the plan-level figure".
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: source inbox message consumed/archived at the 2026-09-21 fold; substance independently re-derived from code (global recall exists, no per-deliverable recall on any branch, single read-intent exclusion rule). Confirming evidence for D4, not a new deliverable

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — the aspect producers (D1–D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — `SECTION_SPEC` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — `should_emit`, D3(b)/(c) fix sites
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
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-09-retrospective-instruments-that-cannot-fire-and-recall-denominators-that-count-the-wrong-population.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
