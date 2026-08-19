# Gaps — 460-audit-ledger-reader-reads-undatable-zero-as-measured

**Source:** verification.md (same directory)   **Open items:** 5

None of the five is a defect in the deliverables D0–D3, which verify clean — re-confirmed under
adversarial review by executing both readers on purpose-built ledgers and by re-applying three of the
four mutants. Four are open items the run itself declared as residue or created as a side effect of a
deliberately-scoped edit; the fifth (G5) was found during adversarial review, at a site the run's own
stated tree-wide sweep did not carry through to its residue list. Each is stated here with the
concrete change that settles it.

## G1 — Reconcile the lock-step mirror in `analyze-logs.py` with the surface-#4 description it mirrors

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:986-996`
  — the `LOCK-STEP OBLIGATION` comment block above `_LEGACY_COLUMN_COUNT`
- **What is wrong:** R2-3 widened `data-format.md:944`'s description of restating surface #4 to name
  `_parse_dispatch_boundary_totals`'s cell read and the row-level provenance gate alongside the constants.
  The hand-written mirror of that same list in `analyze-logs.py` still describes surface #4 as "the
  hand-copied `_BC_LEDGER_COLUMNS` / `_BC_LEDGER_UNMEASURED_TOKEN` pair in
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`". The **count** (four) still agrees,
  which is what the run checked; the **description** no longer does. The run's R2-3 disposition reasoned
  about count-preservation only and did not record the descriptive asymmetry it introduced, so this appears
  in no residue list.
- **Why it matters:** the mirror exists precisely because `audit.py` lives outside the crawled inventory and
  a content sweep will not find it. An editor changing the schema who reads the mirror rather than the
  standard is told to update two constants and is never told the provenance gate moves too — leaving the
  audit reader's gate stale against a changed contract. That is the defect class this epic removes,
  reproduced one level up.
- **Fix:** in the `LOCK-STEP OBLIGATION` comment, extend the surface-#4 clause to match `data-format.md:944`
  — name `_parse_dispatch_boundary_totals`'s cell read and the row-level provenance gate beside the two
  constants, and keep the stated count at four. Text only; no code change, no count change.
- **Done when:** `analyze-logs.py:986-996` and `data-format.md:944` describe the same set of audit-side
  symbols for surface #4, and both still say "four surfaces".
- **Note:** G2 edits the same two paragraphs. They are separate defects (a wrong *description* of surface
  #4 here; a *missing* surface there), but must not land as two conflicting rewrites of one paragraph —
  settle them in one change, or land G1 first and let G2 build on the corrected text.
- **Module/topic:** `plan-marshall:plan-retrospective` + `plan-marshall:manage-metrics` standards —
  dispatch-boundary schema lock-step list

## G2 — Register `checks/billing-composition.md` as a restating surface, moving both lists together

- **Kind:** omission
- **Severity:** medium
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md:34-72`;
  the lists that omit it are
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:944` and
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:987-996`
- **What is wrong:** this plan added the full four-way cell read and the whole provenance-gate rule to the
  check doc, making it a fifth surface that restates the `data-format.md` contract. It is named in neither
  lock-step list. The run declared this as residue and stated the blocker: adding a fifth *file* would
  falsify the "four surfaces" count that `analyze-logs.py:987` mirrors, and this plan may not touch that
  file. Nothing tests the list structurally — only the `termination_cause` enum has an equality guard.
- **Why it matters:** the check doc is the interpretation guide a human auditor reads when dispositioning a
  `billing-composition` finding. A schema change that updates the four registered surfaces and not this one
  leaves the auditor reading a description of a reader that no longer behaves that way — a false signal
  about a check whose whole purpose is truthful signals.
- **Fix:** in one change, raise the count to **five** in both `data-format.md:944` and the mirror comment at
  `analyze-logs.py:987-996`, and add `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md`
  as surface #5 in each, noting (as surface #4 already does) that it lives outside the crawled inventory.
  Both edits must land in the same commit or the mirror is false in between.
- **Done when:** both lists say five surfaces and both name the check doc; a grep for "four surfaces" in the
  two files returns nothing.
- **Module/topic:** `audit-archived-plan-retrospectives` checks + `plan-marshall:manage-metrics` standards

## G3 — Reconcile the two readers' column-resolution strategies, or pin the divergence

- **Kind:** bug (latent, pre-existing; not introduced by this plan)
- **Severity:** medium
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:7356-7360`
  (`_parse_dispatch_boundary_totals`, `if ledger_field not in columns` / `columns.index(ledger_field)`)
  vs `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1182-1183`
  (`index = _LEGACY_COLUMN_COUNT + offset`)
- **What is wrong:** `audit.py` resolves the four context-load columns **by name from the declared
  `rows[]{…}:` header**; `analyze-logs.py` resolves them **positionally at indices 5–8** and ignores the
  header entirely. Three observable divergences follow, each **executed** at HEAD against a purpose-built
  ledger, both readers driven off the same file (row
  `2026-01-01T00:00:00Z,clean_exit_queue_empty,9100,10,500,11,22,33,44` unless stated):

  - **(a) short header, long rows** — the header declares only the legacy five columns while the rows carry
    nine cells. `audit.py` → `{'total_tokens': 9100}`: it measures **none of the four context columns**
    (`total_tokens` still sums, so "measures nothing" would overstate it). `analyze-logs.py` → all four
    measured (`input_tokens=11 … cache_creation_input_tokens=44`), `indeterminate_columns == []` — it
    measures all four **and dates the row**.
  - **(b) malformed `total_tokens` beside a nonzero context cell** (cell 3 = `NaN`) — `analyze-logs.py`
    drops the whole row (`:1140-1148`), returning `rows == []`. `audit.py` keeps it, degrades
    `total_tokens` to `0` via `_to_int` (`audit.py:955`) **and marks it measured**, then sums all four
    context cells and dates the row → `{'total_tokens': 0, 'input_tokens': 11, 'output_tokens': 22,
    'cache_read_input_tokens': 33, 'cache_creation_input_tokens': 44}`. The corpus therefore gains a
    `total_tokens` measurement of `0` that no dispatch reported, from a row the sibling reader discarded.
  - **(c) missing `rows[]{…}:` header line** — `audit.py` returns `{}` because `in_rows` is never set
    (`:7345-7346`); `analyze-logs.py` parses the row in full because its skip list is prefix-based
    (`:1126`).

  A **reordered** header additionally transposes values: with `output_tokens` and `input_tokens` swapped in
  the declared header, `audit.py` → `input_tokens=22, output_tokens=11` while `analyze-logs.py` → the
  positional `input_tokens=11, output_tokens=22`. (An `rows[]{}:` header declaring *no* columns is the one
  malformed case the two agree on — `audit.py` falls back to `_BC_LEDGER_COLUMNS`, so both read all four.)
- **Why it matters:** the plan's stated goal is that "the two parallel readers of one ledger stop
  disagreeing about the same bytes". That now holds for the fingerprint gate and not for the surrounding
  parse, so the same on-disk file can still yield a dated row in one corpus and nothing in the other —
  including disagreement about **datability itself**, which is the property this plan restored.
- **Fix:** pick one resolution strategy for both readers and land it in a single change — header-name
  resolution with a positional fallback is the strictly more informative of the two, and `audit.py` already
  implements it. Then extend the shared-fixture cross-reader tests in
  `test/plan-marshall/manage-metrics/test_record_model_representability.py` with one fixture per divergence
  class (short header + long rows; malformed `total_tokens` beside a nonzero context cell; missing
  `rows[]{…}:` line; a header that reorders two context columns), asserting the same verdict in each
  reader's own vocabulary. Requires touching
  `analyze-logs.py`, which plan 460 scoped out, so it needs its own plan.
- **Done when:** for each of the four divergence classes a single fixture drives both readers and both
  report the same measured set and the same datability verdict.
- **Module/topic:** `plan-marshall:plan-retrospective` + `audit-archived-plan-retrospectives` —
  dispatch-boundary ledger parse

## G4 — Rename the two stale "three ways" retrospective-reader tests

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/plan-marshall/manage-metrics/test_record_model_representability.py:455`
  (`test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader`), `:783`
  (`test_unmeasured_fixture_reads_three_ways_in_the_retrospective_reader`), and the comment at `:450`
  ("the third point of the three-way distinction")
- **What is wrong:** the retrospective reader's context-load cell has read **four** ways since plan 420
  (`analyze-logs.py:1046-1065`, and `data-format.md:927` § *Provenance of a measured zero*). These three
  sites still say three. Plan 460 renamed the audit-side sibling
  (`test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader` →
  `…_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader`) and deliberately deferred these,
  which leaves the module internally asymmetric: a reader cannot tell whether the asymmetry is meaningful.
- **Why it matters:** these are the two tests a maintainer opens to learn what the retrospective reader's
  cell read is. Their names assert a state count the reader has not had since #1255, and the neighbouring
  correctly-named test makes the mismatch look intentional.
- **Fix:** rename `:455` to name the invariant it pins (the writer/reader round-trip over one artifact, e.g.
  `test_composed_boundary_file_round_trips_through_the_retrospective_reader`) and `:783` likewise (e.g.
  `test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_retrospective_reader`, mirroring
  its audit-side sibling). Reword the `:450` comment to say what the row demonstrates — a fully measured
  dispatch declaring nothing unmeasured — rather than counting the states. No assertion changes.
- **Done when:** `grep -rn "three_ways\|three-way distinction" test/plan-marshall/manage-metrics/` returns
  nothing, and the module's audit-side and retrospective-side tests follow one naming convention.
- **Module/topic:** `plan-marshall:manage-metrics` tests — dispatch-boundary representability suite

## G5 — Two stale "three-way" statements about the retrospective reader in the `plan-retrospective` suite

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/plan-marshall/plan-retrospective/test_analyze_logs.py:984` — the docstring of
  `TestDispatchBoundaryContextLoadColumns::test_per_column_mix_of_measured_and_unmeasured`
  ("The three-way read is per COLUMN, not per row."); and
  `test/plan-marshall/plan-retrospective/test_analyze_logs_behavior.py:173` — the docstring of
  `TestParseDispatchBoundaryFile::test_malformed_appended_cell_is_unrecognised_not_unmeasured`
  ("The three-way distinction at its sharpest: a legacy row (nothing there), an ``unmeasured`` token
  (deliberately not measured) and a corrupt cell (a shape the reader failed to parse) must not collapse
  into one bucket.")
- **What is wrong:** the retrospective reader's context-load cell has read **four** ways since plan 420
  (`analyze-logs.py:1177-1225`; `data-format.md:927-936` § *Provenance of a measured zero*). Both
  docstrings still describe a three-state taxonomy, and the first one's headline claim is not merely an
  outdated count — it is now **false about the mechanism**: `indeterminate`, the fourth state, is decided
  by the row-level provenance gate (`analyze-logs.py:1181`, `:1218-1222`), so the read is precisely *not*
  per column any more. This is the same defect class as G4, one directory over, and it is what the
  verification's own stated tree-wide `three-way` sweep should have surfaced — its residue list carried
  only the `test/plan-marshall/manage-metrics/` hits.
- **Why it matters:** these are the two modules a maintainer opens to learn what the retrospective
  reader's cell read is (`test_analyze_logs.py` is the reader's own unit suite). A docstring asserting
  the read is per column and three-valued teaches the exact pre-420 model this epic removed — and it sits
  in the same file as the tests that pin the four-state behaviour, so the contradiction reads as an
  intentional distinction rather than as drift.
- **Fix:** in `test_analyze_logs.py:984`, replace "The three-way read is per COLUMN, not per row." with a
  statement of what the test actually pins — that the *measured / unmeasured / unrecognised* verdicts are
  reached per column, one cell's verdict never propagating to its neighbours — and add that the fourth
  state, `indeterminate`, is the one verdict decided per row by the provenance gate. In
  `test_analyze_logs_behavior.py:173`, change "The three-way distinction at its sharpest" to name the
  three states it is contrasting without claiming they are the whole taxonomy (e.g. "Three of the four
  states at their sharpest"). Docstrings only; no assertion or test-name changes, so no behaviour moves.
- **Done when:** `grep -rn --include="*.py" "three-way\|three ways\|three_ways"
  test/plan-marshall/plan-retrospective/`
  returns exactly one hit — `test_chat_provenance.py:270`, which is about chat-provenance splitting and
  not about the dispatch-boundary cell — and neither `test_analyze_logs.py` nor
  `test_analyze_logs_behavior.py` appears.
- **Module/topic:** `plan-marshall:plan-retrospective` tests — dispatch-boundary context-load read

## Refuted during adversarial review

**None.** All four originally-filed gaps (G1–G4) survived adversarial re-derivation, and each was
re-checked at its named symbol rather than accepted from the text:

- **G1** — read `analyze-logs.py:986-996` and `data-format.md:944` side by side. The mirror does still
  describe surface #4 as "the hand-copied `_BC_LEDGER_COLUMNS` / `_BC_LEDGER_UNMEASURED_TOKEN` pair" with
  no mention of the gate, while the standard now names `_parse_dispatch_boundary_totals`'s cell read and
  the row-level provenance gate. Both still say "four". The causal attribution to R2-3 also holds:
  `git show d1c31533 -- …/data-format.md` is a single-line change and the pre-change wording was "the
  hand-copied `_BC_LEDGER_COLUMNS` tuple", i.e. the run widened the standard past its own mirror.
- **G2** — read `checks/billing-composition.md:34-72`; it carries the whole four-way cell read and the
  whole gate rule. Neither `data-format.md:944` nor `analyze-logs.py:987-996` names the file. Upheld;
  only the cited line range was off by one (`:34-71` → `:34-72`).
- **G3** — not accepted by reading. Both readers were **executed** on purpose-built ledgers (see the
  per-class results now inlined in the gap). All three divergence classes reproduce, plus the
  header-reorder transposition. One sub-claim was overstated and has been corrected: in class (a)
  `audit.py` does not "measure nothing" — it measures `total_tokens` and none of the four context columns.
- **G4** — all three sites confirmed present at HEAD
  (`test_record_model_representability.py:450`, `:455`, `:783`), and `analyze-logs.py:1177-1225` confirms
  the retrospective reader is four-state, so the names are genuinely stale.
