# Gaps — 460-audit-ledger-reader-reads-undatable-zero-as-measured

**Source:** verification.md (same directory)   **Open items:** 4

None of the four is a defect in the deliverables D0–D3, which verify clean, including under four mutants.
All four are open items the run itself declared as residue or created as a side effect of a
deliberately-scoped edit; each is stated here with the concrete change that settles it.

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
- **Module/topic:** `plan-marshall:plan-retrospective` + `plan-marshall:manage-metrics` standards —
  dispatch-boundary schema lock-step list

## G2 — Register `checks/billing-composition.md` as a restating surface, moving both lists together

- **Kind:** omission
- **Severity:** medium
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md:34-71`;
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
  header entirely. Three observable divergences follow, each re-confirmed at HEAD: (a) a ledger whose header
  declares only the legacy five columns while its rows carry nine cells — `audit.py` measures nothing,
  `analyze-logs.py` measures all four **and dates the row**; (b) a malformed `total_tokens` beside a nonzero
  context cell — `analyze-logs.py` drops the whole row (`:1140-1148`), `audit.py` keeps it, degrades
  `total_tokens` to `0` via `_to_int`, sums the context cell and dates the row; (c) a missing `rows[]{…}:`
  header line — `audit.py` returns `{}` because `in_rows` is never set (`:7346`), `analyze-logs.py` parses
  the row because its skip list is prefix-based (`:1126`). A reordered header additionally transposes values
  between the two.
- **Why it matters:** the plan's stated goal is that "the two parallel readers of one ledger stop
  disagreeing about the same bytes". That now holds for the fingerprint gate and not for the surrounding
  parse, so the same on-disk file can still yield a dated row in one corpus and nothing in the other —
  including disagreement about **datability itself**, which is the property this plan restored.
- **Fix:** pick one resolution strategy for both readers and land it in a single change — header-name
  resolution with a positional fallback is the strictly more informative of the two, and `audit.py` already
  implements it. Then extend the shared-fixture cross-reader tests in
  `test/plan-marshall/manage-metrics/test_record_model_representability.py` with one fixture per divergence
  class (short header + long rows; malformed `total_tokens` beside a nonzero context cell; missing
  `rows[]{…}:` line), asserting the same verdict in each reader's own vocabulary. Requires touching
  `analyze-logs.py`, which plan 460 scoped out, so it needs its own plan.
- **Done when:** for each of the three divergence classes a single fixture drives both readers and both
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
