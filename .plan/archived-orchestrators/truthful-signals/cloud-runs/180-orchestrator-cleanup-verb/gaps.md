# Gaps — 180-orchestrator-cleanup-verb

**Source:** verification.md (same directory)   **Open items:** 7

The plan's core mechanism landed and holds under mutation: breaking the closed-epic guard and breaking
the between-markers write boundary each turned the plan's own tests RED (14 of 32 failing, re-run
independently), so neither the refusal nor the "a retraction survives verbatim" property is vacuous.
The seven open items below are a dead assertion, two doc-contract divergences of the exact archetype
this epic exists to close, one un-migrated lossy path, one un-migrated inert path, one shipped false
signal in the report the plan calls its safety deliverable, and one duplicated reconciliation.

⚠ **G5 was refuted during adversarial review and moved to the end of this file.** It is retained with
its refuting evidence rather than dropped.

## G1 — Replace the tautological assertion in the narrative-survival test

- **Kind:** vacuous-test
- **Severity:** medium
- **Where:** `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py:369` —
  `TestNarrativeSurvivesVerbatim::test_every_hand_authored_section_survives_verbatim`
- **What is wrong:** the closing line is
  `assert after == text or after == _epic_text(plan_context)`. `after` was assigned from
  `_epic_text(plan_context)` at line 364 and nothing writes the file between that read and line 369,
  so the second disjunct re-reads the same unchanged bytes and is a tautology. Replacing the line with
  `assert after == text` alone makes the test fail (re-verified independently under adversarial review:
  `1 failed, 31 passed`, the diff showing `+ **Inbox (derived)**: …` — the regenerated resume-summary
  body), proving the first disjunct is False in this fixture and the assertion is carrying no weight. The comment above it, "A second pass changes nothing at all", describes a second
  `_run()` the test never performs, and the comment on line 362 (`# after regeneration`) mislabels a
  read taken *before* `_run()`.
- **Why it matters:** a reader counts this test as covering idempotence-of-narrative; it does not. If
  `TestIdempotence` were ever weakened or deleted, the loss would be invisible here.
- **Fix:** perform the second pass the comment claims — call `_run()` again, re-read, and assert the
  bytes are identical to the post-first-pass read; or delete the disjunctive line and fix the two
  misleading comments, leaving the four `assert fragment in after` checks as the test's real content.
- **Done when:** the test contains no assertion whose truth is independent of the code under test, and
  every comment in it describes an operation the test actually performs.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` tests

## G2 — Give an already-hand-annotated generated block a migration path, or name the loss in the report

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2018`
  — `_replace_block`; `.../workflow/cleanup.md:78-97` § Step 8 (Phase B);
  `.../persona-plan-orchestrator/standards/orchestration-model.md:249` (annotation-zone contract)
- **What is wrong:** the plan's D2 is explicit that a live block was found hand-annotated *between* the
  markers and that "pasting the verbatim output as-is would destroy information the annotations carry".
  The landed answer — an annotation zone outside the markers — solves this only for content written
  after the landing. For a ledger that already carries in-marker annotations, the first `compact` run
  overwrites them: `_replace_block` computes `before = lines[begin_idx + 1 : end_idx]` and then
  discards it, returning only `len(before)` and `len(new_lines)`. `cmd_compact` never surfaces the
  discarded text. § Ledger-Compaction Stage `:249` does state the *intent* — "the annotations move to
  the zone" — but states it as the abstract resolution of the tension, not as an instruction: neither
  `cleanup.md` § Step 8 nor `:249` carries a step performed BEFORE the script call, and nothing gates
  the first compaction on the migration having happened. The script does the overwrite regardless.
- **Why it matters:** the plan's own safety property is "a silent compaction is indistinguishable from
  a lossy one". A first pass on a real, hand-annotated epic is exactly a lossy compaction whose only
  trace in the report is a line-count delta — the failure mode this epic exists to close, reproduced
  inside the verb built to close it.
- **Fix:** either (a) add a `discarded[]` (or `replaced_body`) field to `cmd_compact`'s payload
  carrying the pre-write between-marker text for every block whose `outcome` is `regenerated`, so the
  operator can rescue an annotation from the report; or (b) add a step to `cleanup.md` § Step 8 that
  runs before the script call, instructing the orchestrator to move any hand-written line found between
  the markers into the adjacent `### Annotations` / `### Queue annotations` zone, and state the
  one-time migration in § Ledger-Compaction Stage. Option (a) also wants a test asserting the field is
  populated when a block changes.
- **Done when:** running `compact` on an epic whose generated block contains a hand-written line either
  preserves that line, or names its content (not merely its line count) in the emitted report — and a
  test in `test_orchestrator_compact.py` pins the behaviour.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — compact stage + cleanup workflow

## G3 — Declare `settled.md` in the orchestrator tree-layout contract and the carve-out enumeration

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:**
  `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md:24-35`
  (the epic tree-layout entries, inside the code fence at `:23-36`) and `:85` (§ Carve-outs, the
  ledger-document enumeration)
- **What is wrong:** the same standard mandates `settled.md` at `:253` ("a live-epic sibling of
  `history.md`") and `cleanup.md:82` links to `#carve-outs` when instructing the orchestrator to create
  it — but the tree-layout contract lists nine entries (`epic.md`, `status.json`, `history.md`,
  `references.json`, `workstreams/`, `plans/`, `landings/`, `inbox/`, `logs/`) and does not include
  `settled.md`, and `:85`'s parenthetical enumeration of "the orchestrator's ledger documents"
  (`epic.md`, workstream charters, plan specs, landing records, `history.md`, `references.json`) does
  not name it either. Re-derived under adversarial review by grepping `settled.md` across
  `marketplace/` and `test/` (excluding `__pycache__`): **21 matching lines / 22 occurrences** — 2 in
  the standard (`:59`, `:253`), 9 in `orchestrator.py`, 4 in `cleanup.md`, 6 in
  `test_orchestrator_compact.py` — none of them the layout block or the carve-out list. (The
  verification's figure of "17 sites" does not re-derive; 21/22 is the current value.)
- **Why it matters:** the layout block is the binding statement of what an epic tree contains, and
  `:48` asserts the templates "mirror this layout contract one-to-one". A file the standard orders
  written but does not admit exists is a doc-contract divergence — the archetype this epic files
  against everyone else — and a future audit of tree contents would flag `settled.md` as an
  unrecognised artifact.
- **Fix:** add a `settled.md` row to the layout code block between `history.md` and `references.json`,
  commented as "Relocated settled narrative (written mid-life by the compact stage; pointers in
  epic.md resolve here)", and add `settled.md` to the ledger-document parenthetical at `:85`.
- **Done when:** `settled.md` appears in the tree-layout code block and in the § Carve-outs
  ledger-document list in `orchestration-model.md`.
- **Module/topic:** `plan-marshall` / `persona-plan-orchestrator` standards

## G4 — Carry the compaction stage's report fields into the `cleanup` verb's Output contract

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md:97`
  (the instruction) versus `:154-173` (the `## Output` TOON block)
- **What is wrong:** line 97 says "fold the stage's `regenerated[]`, `invariants[]`, and `abstained[]`
  into this report". The canonical Output block declares `ledger_compaction: compacted` and no key for
  any of the three; it declares `regrounded[]`, `applied[]`, and `declined[]` only. An implementer
  working from the Output block — which is where a verb's emission contract is normally read — emits a
  compaction line naming no mutation and no abstention. No test covers this: `test_cleanup_contract.py`
  checks router closure, verb-enumeration agreement, canonical-invocation coverage, apply-idempotence,
  and verdict-field single-definition, but not the Output block's field set.
- **Why it matters:** the plan's Verification section states D4's requirement as "a report that lists
  only what changed cannot distinguish 'nothing needed touching' from 'the verb could not see it'". The
  script satisfies that; the verb that wraps it does not, so the operator-facing report — the one a
  human actually reads — can legally omit both.
- **Fix:** add the three keys to the `## Output` block with the same shapes the script emits
  (`compaction_regenerated[R]{surface,outcome,lines_before,lines_after}`,
  `compaction_invariants[I]{invariant,verdict,evidence,population}`,
  `compaction_abstained[A]{section,treatment}`), and state that each is required-never-omitted, as
  `declined[]` already is at `:177`.
- **Done when:** `cleanup.md`'s `## Output` block declares a key for each of `regenerated[]`,
  `invariants[]`, and `abstained[]`, and line 97's instruction names those keys.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — cleanup workflow doc


## G6 — `abstained[]` reports a derivable section the stage COULD NOT touch as one it CHOSE to preserve

- **Kind:** false-signal
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2192`
  — `_abstained_sections`; consumed at `:2290` and emitted as `abstained[]` / `abstained_count` by
  `cmd_compact` (`:2301-2302`). Contract statements at
  `plan-orchestrator/SKILL.md:140` and
  `persona-plan-orchestrator/standards/orchestration-model.md:257`
- **What is wrong:** `_abstained_sections` classifies a `##` section as abstained-from "unless it
  CONTAINS a GENERATED marker". A section that IS a derivable surface but whose markers are absent —
  the case `_replace_block` reports as `markers_absent` — therefore lands in `abstained[]` with
  `treatment: preserved_verbatim`, the same value used for a genuine narrative section. Executed
  under adversarial review against an `epic.md` in the PRE-change template shape (a `## Ordered
  Queue` table with no marker pair):

  ```text
  {'section': 'Vision',        'treatment': 'preserved_verbatim'}
  {'section': 'Ordered Queue', 'treatment': 'preserved_verbatim'}   <-- derivable, NOT preserved by choice
  {'section': 'Decisions',     'treatment': 'preserved_verbatim'}
  ```

  `abstained_count` is inflated by the same row. The function's own docstring claims the opposite
  property — "This is what lets a reader tell 'nothing needed touching' from 'the stage could not see
  it'" — so the code asserts in prose exactly what it fails to deliver.
- **Why it matters:** this is the plan's D4 requirement stated back to it verbatim. The plan's
  Verification section: "A report that lists only what changed cannot distinguish 'nothing needed
  touching' from 'the verb could not see it'." The report the plan calls "the deliverable that makes
  the verb safe to run unattended" tells an operator that the Ordered Queue — the single surface D2
  exists to bring under the marker contract — was deliberately preserved as narrative. The
  `regenerated[]` row (`ordered-queue / markers_absent`) is the only counter-signal, and the two rows
  contradict each other; neither the SKILL.md nor the standard's report contract discloses the
  interaction. On every epic scaffolded before this landing (see G7) this is the DEFAULT output, not
  an edge case.
- **Fix:** in `_abstained_sections`, take the per-block outcomes `cmd_compact` already computed and
  emit a distinct treatment for a section that carries a derivable surface the stage could not reach —
  e.g. `treatment: markers_absent_not_regenerated` — instead of `preserved_verbatim`; exclude it from
  `abstained_count`, or add a separate `unreachable_count`. Pass the `regenerated` rows (or the set of
  block names whose outcome was `markers_absent`, keyed to their owning heading) into the function
  rather than re-deriving from text alone. Add a test in `test_orchestrator_compact.py`
  (`TestMarkersAbsent`) asserting that with `include_queue_markers=False` the `Ordered Queue` row's
  treatment is NOT `preserved_verbatim`.
- **Done when:** running `compact` on an `epic.md` whose `## Ordered Queue` carries no marker pair
  emits an `abstained[]` row for that section whose `treatment` distinguishes it from a narrative
  section, and a test pins that value.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — compact stage report

## G7 — No migration inserting the new `ordered-queue` markers into an already-live `epic.md`

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/epic.md:50-54`
  (the marker pair this plan added); the refusal to insert at
  `persona-plan-orchestrator/standards/orchestration-model.md:247`; no counterpart step in
  `plan-orchestrator/workflow/cleanup.md` § Step 8 or in any other workflow doc
- **What is wrong:** the `ordered-queue` marker pair is NEW in this landing — re-derived from
  `git show 91a1c771^:.../templates/epic.md`, whose Ordered Queue table sits at lines 44-46 with no
  markers at all. Every `epic.md` scaffolded from the pre-change template therefore has no
  `ordered-queue` markers, and the standard at `:247` positively forbids the stage from inserting
  them ("never fabricated, because inserting markers into a hand-authored document is a structural
  edit the stage has no mandate to make"). No doc instructs anyone to insert them either: sweeping
  `marker` across `plan-orchestrator/workflow/` and `doc/concepts/orchestration.adoc` returns only
  paste-between-existing-markers instructions (`resume.md:48`, `close.md:36`, `analyze.md:140`,
  `orchestrate.md:128`, `decompose.md:72`, `lessons-handling.md:86`), never an insertion or migration
  step. The result: on every pre-existing epic, D2's central deliverable is inert — `compact` reports
  `ordered-queue / markers_absent` forever and the queue is never regenerated.
- **Why it matters:** the plan's motivating evidence is a LIVE epic whose "ordered queue drifted to
  phantom rows and live-shown shipped plans". Those are exactly the epics that predate the marker.
  A verb built for mid-flight epics that only takes effect on epics created after it shipped is a
  capability the operator cannot reach from where they are.
- **Fix:** add a one-time migration step to `cleanup.md` § Step 8, before the script call: when
  `epic.md` has a `## Ordered Queue` section and no `<!-- BEGIN GENERATED: ordered-queue -->` marker,
  the orchestrator inserts the marker pair around the existing table and moves any `Notes` column
  content into the `### Queue annotations` zone (the pre-change table's sixth column, dropped by this
  landing's template) — writing via the direct-file-write carve-out, not via the script. State the
  migration as a one-time obligation in `orchestration-model.md` § Ledger-Compaction Stage next to
  the `markers_absent` rule at `:247`, so the refusal and its remedy are read together.
- **Done when:** `cleanup.md` § Step 8 carries a marker-insertion step conditioned on
  `markers_absent`, and § Ledger-Compaction Stage names the one-time migration alongside the
  never-fabricate rule.
- **Note on observability:** the affected population (live `epic.md` files) is under the git-ignored
  `.plan/`, so the number of affected epics cannot be counted from this clone. The contract gap
  itself is fully observable and is what this row records.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — cleanup workflow + standard

## G8 — `_invariant_queue_spec` duplicates `_corpus_signal` branch for branch

- **Kind:** duplication
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2051-2086`
  (`_invariant_queue_spec`, added by this landing) versus `:1805-1841` (`_corpus_signal`,
  pre-existing)
- **What is wrong:** the two functions call the same `cmd_corpus_enumerate`, build the same
  population string (`f'{rows_total} queue row(s) and {specs_total} spec file(s)'`), and branch
  identically on `status != 'success'` → `unreadable_count` → `rows_without_spec_count or
  specs_without_row_count` → clean, with the same evidence strings ("queue and specs reconcile both
  ways", "N row(s) without a spec and M spec(s) without a row"). They differ only in the emitted
  vocabulary — `_signal`/`READINESS_INDETERMINATE`/`NOT_READY`/`READY` versus
  `_invariant`/`indeterminate`/`violated`/`ok` — and in the row name.
- **Why it matters:** two copies of one reconciliation rule can drift, and when they do the
  restart-readiness verdict and the compact invariant will disagree about the same fact while both
  claim to have checked it. That is a smaller instance of the divergence archetype this epic files
  against everyone else, introduced by the landing rather than inherited.
- **Fix:** extract the shared body into one helper returning a
  `(state, evidence, population)` triple with a neutral three-value state
  (`clean` / `mismatched` / `unobservable`), and have `_corpus_signal` and `_invariant_queue_spec`
  each map that triple into their own vocabulary. Keep both public shapes unchanged so
  `test_orchestrator.py` and `test_orchestrator_compact.py` pass without edit.
- **Done when:** exactly one function in `orchestrator.py` branches on
  `unreadable_count` / `rows_without_spec_count` / `specs_without_row_count`, and both callers derive
  their verdicts from it.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — orchestrator script

## Refuted during adversarial review

A dismissed finding is still evidence. The row below was filed as open, re-checked, and refuted; it
is kept here so the next reader knows it was considered.

### G5 (REFUTED) — Isolate the machine-global fallback-streak store in the `script-shared` build-factory test

**Original claim.** `test_a_real_plan_id_still_writes_the_work_log`
(`test/plan-marshall/script-shared/test_build_execute_factory.py:934`) monkeypatches only
`factory.log_entry`, so `_record_resolution(..., 'socket_absent', ..., 'a-real-plan')` reaches
`_update_fallback_streak` and read/writes the machine-global
`home_root()/'marshalld'/'fallback-streak.json'`; after `_FALLBACK_WARN_STREAK` (3) consecutive
in-session runs, `suppress_repeat` flips True and `assert len(written) == 1` fails. Filed `medium`,
inherited from `report-01.md` § Residue, and asserted in verification.md as "still open … nothing
monkeypatches `home_root` or `_fallback_state_path`".

**Why it is refuted.** The module carries an **autouse** fixture that isolates the home root, added
AFTER this plan landed:

- `test/plan-marshall/script-shared/test_build_execute_factory.py:433-451` — `_isolated_home_root`,
  `@pytest.fixture(autouse=True)`, `monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path /
  'plan-marshall-home'))`. Its docstring names this exact defect ("that write lands in the
  developer's REAL `~/.plan-marshall` and ACCUMULATES across pytest runs … fails on any machine that
  has run the suite more than `_FALLBACK_WARN_STREAK` times").
- `git log -S "_isolated_home_root" -- test/plan-marshall/script-shared/test_build_execute_factory.py`
  → **`d4ae2e81`** ("fix(build): a timeout is not a red test, and a harness kill is not a timeout",
  **#1193**) — later than this plan's `91a1c771` (#1183). The residue `report-01.md` disclosed was
  fixed by a subsequent plan.
- **Executed, not read:** the target test class was run **five consecutive times in one session**
  (`pytest … -k TestRecordResolutionSentinelSuppressesWorkLog`) — `4 passed` on every run, and
  `~/.plan-marshall/marshalld/fallback-streak.json` was byte-identical before and after
  (md5 `f21dab0824076fb6a8f558ce1f80b1c0` both ways, and no `a-real-plan` key ever appeared).

The verification's search was for the symbol names `home_root` / `_fallback_state_path`; the
isolation is applied through the `PLAN_MARSHALL_HOME` environment variable, which that search could
not see. The claim was reached by reading the callee rather than by running the test.
