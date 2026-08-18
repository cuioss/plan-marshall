# Gaps — 420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make

**Source:** verification.md (same directory)   **Open items:** 3

All five deliverables are implemented, correct and non-vacuous — three mutation checks against
`_parse_dispatch_boundary_file` each turned the plan's own tests red. No gap below is a behaviour
defect in the fix. All three are stale statements on the reader contract: one an incomplete sweep by
this run, two pre-existing contradictions inside the exact section this run rewrote and did not carry
across.

Explicitly **not** filed as gaps, having been checked: the `audit.py` residue (closed by #1278, which
ported the same provenance gate and moved its docstring to "reads FOUR ways"); the dangling
`test_measured_zero_context_load_stays_zero` cross-reference this run left behind (closed by #1258);
the fourth state's conservative direction — a genuine all-four-measured-zero post-token row reads
indeterminate — which is a documented and deliberate choice, stated in `data-format.md`
§ *Provenance of a measured zero*.

## G1 — Finish the "three-way → four-way" sweep in the manage-metrics representability tests

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/plan-marshall/manage-metrics/test_record_model_representability.py:450` (comment),
  `:455` (`test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader`),
  `:783` (`test_unmeasured_fixture_reads_three_ways_in_the_retrospective_reader`)
- **What is wrong:** the run corrected three named "three-way" restating surfaces (F1–F3) and its
  verification sub-agent ran a beyond-diff sweep for the phrase, but three live sites remain — two of
  them **test function names that assert the retrospective reader's contract by name**, pinning it at
  "reads three ways" against a reader that has read four ways since `d5b2c4e3`. All three predate the
  landing (`git show d5b2c4e3:test/plan-marshall/manage-metrics/test_record_model_representability.py`
  carries them at old lines 482/487/815) and none was touched. The sibling audit-ledger test at `:815`
  *was* renamed and re-documented by #1278 to name the fourth state, which leaves the two remaining
  "three_ways" names visibly out of step with their own neighbour.
- **Why it matters:** a reader locating the reader contract by test name lands on a name asserting the
  retired two-plus-one model. `test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader`
  is the producer/consumer pinning test — the one a future writer change is expected to break — so its
  name is the most-read summary of the contract outside the standard itself.
- **Fix:** rename `test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader` and
  `test_unmeasured_fixture_reads_three_ways_in_the_retrospective_reader` to say four ways (e.g.
  `…_reads_four_ways_in_the_retrospective_reader`), and reword the `:450` comment "the third point of
  the three-way distinction" to name the four states. While renaming, add to at least the composed
  round-trip test an assertion on `indeterminate_columns` (currently only `unmeasured_columns` and
  `unrecognised_columns` are asserted there), so the fourth state is actually pinned by the test whose
  name will claim it. Every row of both fixtures carries an `unmeasured` token or a nonzero, so all
  existing expectations stay green.
- **Done when:** `grep -n "three.way\|three ways" test/plan-marshall/manage-metrics/test_record_model_representability.py`
  returns only line 690 (the unrelated `metrics.toon` schema three-state comparison), and
  `test/plan-marshall/manage-metrics/test_record_model_representability.py` passes.
- **Module/topic:** `manage-metrics` / dispatch-boundary reader contract (tests)

## G2 — Reconcile the cell-read table's "a column the row does not have" row with the code

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:923`
  — § Per-Dispatch Context-Load Attribution cell-read table; mirrored at
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1052`
  — `_parse_dispatch_boundary_file` docstring
- **What is wrong:** the table's fourth row says `anything else (non-int, non-token, **or a column the
  row does not have**) → **unrecognised**`. Both readers do the opposite, and the standard itself
  contradicts it eleven lines later. `analyze-logs.py:1183-1187` puts an absent column into
  `unmeasured_columns`; `audit.py`'s `_parse_dispatch_boundary_totals` docstring states "the
  `unmeasured` literal, **or a column the row is too short to have** — UNMEASURED"; and
  `data-format.md`'s own **Positional backward compatibility** paragraph says a legacy row's "four
  **missing** columns read as **unmeasured** (absent), never as a measured `0`". Executed to confirm:
  a seven-column row yields `unmeasured_columns == ['cache_read_input_tokens',
  'cache_creation_input_tokens']` and `unrecognised_columns == []`. The `analyze-logs.py` docstring
  carries the same wrong clause immediately above its own correct "A LEGACY five-column row … reports
  all four as **unmeasured**" sentence. Both predate this plan (`git log -S 'or a column the row does
  not have'` → `2586ef00`/#1129), but this run rewrote that exact table and that exact docstring and
  did not carry the correction across.
- **Why it matters:** the standard is declared the single source of truth for every restating reader,
  and a new reader implemented from the table would report a legacy short row's four columns as
  *unrecognised* — "the writer wrote something I could not parse" — instead of *unmeasured*. That is
  the same over-claim family the whole section exists to prevent, and it would diverge silently from
  the two shipped readers.
- **Fix:** in `data-format.md:923`, drop `or a column the row does not have` from the fourth table
  row, and add a fifth row: `| a column the row is too short to have | **unmeasured** | Carry the
  column as ABSENT — a row written before the columns existed recorded no measurement at all |`. In
  `analyze-logs.py:1052`, change `anything else, and a column a short row does not have —
  UNRECOGNISED` to `anything else — UNRECOGNISED`, leaving the existing legacy-row sentence below it
  to own the short-row case.
- **Done when:** the cell-read table and both reader docstrings agree with the code that an absent
  column reads *unmeasured*, and no sentence in § Per-Dispatch Context-Load Attribution assigns the
  short-row case to *unrecognised*.
- **Module/topic:** `manage-metrics` / `standards/data-format.md` § Per-Dispatch Context-Load
  Attribution (+ the `plan-retrospective` reader docstring that restates it)

## G3 — Correct the byte-identity sentence under the format example

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:890`
- **What is wrong:** "Before the `unmeasured` token existed, rows 2 and 3 were byte-identical on
  columns 6–9." Read against the example block directly above it (lines 884–886), row 2 is
  `…,51044,17,238110,unmeasured,unmeasured,unmeasured,unmeasured` and row 3 is
  `…,12903,4,61220,9100,0,0,0`. Pre-token those would have been `0,0,0,0` and `9100,0,0,0` — not
  byte-identical. The true statement is the one this plan added at line 936: an *all-zero* pre-token
  row is byte-identical to an all-measured-zero row. The sentence predates the plan
  (`git log -S 'were byte-identical on columns'` → `2586ef00`/#1129) but sits four lines above the
  section this plan rewrote and states the plan's own subject incorrectly.
- **Why it matters:** it is the first explanation of the collapse a reader of this standard meets, and
  it points at the wrong pair of rows — which makes the fourth state look like it addresses the
  unmeasured-token case rather than the undatable-zero case.
- **Fix:** replace with a sentence naming the real pair, e.g. "Before the `unmeasured` token existed,
  row 2 was written `0,0,0,0` — byte-identical to a row whose caller genuinely measured zero on all
  four columns. That collapse is what the token prevents going forward and what
  § *Provenance of a measured zero* below handles for rows already on disk."
- **Done when:** the sentence names a pair of representations that are in fact byte-identical, and
  cross-references § *Provenance of a measured zero*.
- **Module/topic:** `manage-metrics` / `standards/data-format.md` § Dispatch-boundary artifact format
