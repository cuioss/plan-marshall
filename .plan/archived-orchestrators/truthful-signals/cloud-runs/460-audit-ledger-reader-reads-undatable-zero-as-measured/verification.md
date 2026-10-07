# Verification — 460-audit-ledger-reader-reads-undatable-zero-as-measured

**Verified against:** commit `705c2ac0`   **Landed as:** PR #1278, commit `d1c31533`   **Verdict:** fully-implemented

## Method

What was actually done, so an empty finding list is distinguishable from a check that examined nothing.

**Files opened and read in full or by symbol**

- `plan.md` and `report-01.md` (both in full).
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — `_parse_dispatch_boundary_totals`
  (`:7267-7392`), the `_BC_LEDGER_*` constants (`:7188-7226`), `_BC_BILLING_WEIGHTS` (`:7156`), and the
  single consumer inside `_collect_billing_composition_rows` (`:7490-7520`).
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` —
  `_parse_dispatch_boundary_file` (`:1030-1225`) and the lock-step mirror comment (`:978-996`), read to
  check the transplanted fingerprint rule cell-for-cell against the audit reader.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — § Per-Dispatch
  Context-Load Attribution, incl. *Provenance of a measured zero* (`:927-942`) and *Restating surfaces*
  (`:944`).
- `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md` — the two corrected
  passages.
- `test_audit_check_billing_composition_ledger_provenance.py` (whole file),
  `test_record_model_representability.py` (the changed regions and the two residual tests at `:455` /
  `:783`), `test_audit_check_billing_composition_reconstruction.py` (the changed docstring),
  `test_audit_check_inventory_consistency.py:79-111`.
- The new fixture
  `test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/undatable/work/metrics-dispatch-boundaries-5-execute.toon`.
- Third-party ledger readers, to test the plan's "exactly two readers" premise:
  `manage-metrics/scripts/_ledger_reconciliation.py` `load_boundary_rows` (`:214`) and
  `manage-metrics.py` `_read_dispatch_boundary_totals` (`:727`). **Verdict (added under adversarial
  review — the original Method listed the files but recorded no conclusion):** both read only columns
  0–2 (`timestamp`, `termination_cause`, `total_tokens`) and never touch the four context-load columns,
  so neither is exposed to the undatable-zero gate. The premise holds: `analyze-logs.py`
  `_parse_dispatch_boundary_file` and `audit.py` `_parse_dispatch_boundary_totals` are the only two
  readers of the gated columns.

**Landed diff.** `git show --name-status --find-renames d1c31533` — 9 paths, one of them the `git mv` of
the plan file into its directory. No `analyze-logs.py`, no writer, no archived corpus.

**Tests run (all from repo root, `UV_HTTP_TIMEOUT=600 uv run python -m pytest … -o addopts="" -q`)**

- `…/test_audit_check_billing_composition_ledger_provenance.py` + `…/test_record_model_representability.py`
  → **24 passed** in 1.18 s at HEAD.
- `--collect-only` on the new module → **7 tests collected** from 6 functions (the parametrized pair).
- Whole audit suite + representability → **657 collected** at HEAD, all green.

**Mutations applied** (byte-snapshot of `audit.py` taken to
`scratchpad/audit.py.orig` first; `git diff --quiet` returned 0 before each mutation and again after each
restore; restored by copying the snapshot back, never by `git checkout`/`restore`/`stash`):

| Mutant | Edit | Result |
|---|---|---|
| pre-fix (gate removed) | `if datable:` → `if True:` | **5 failed** — `test_fingerprint_free_all_zero_ledger_omits_the_context_columns`, both arms of `test_a_fingerprinted_row_does_not_date_its_neighbour`, `test_unrecognised_cell_is_not_a_fingerprint`, `test_undatable_zeros_are_not_measurements_in_either_reader` (failing at its **audit** half, line 940). The two negative controls stayed green. |
| over-correction | `if datable:` → `if False:` | **7 failed** — both negative controls, both per-row arms, the negative-value test, plus the two pre-existing tests the report names (`test_unmeasured_cells_are_omitted_while_measured_zeros_are_kept`, `test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader`). |
| file-level fingerprint | `datable` hoisted out of the row loop | **1 failed** — `…does_not_date_its_neighbour[dated-first]` only. Unique kill, exactly as reported. |
| positivity | `datable = True` → `datable = value > 0` on the nonzero branch | **1 failed** — `test_a_negative_context_load_value_dates_the_row` only. Unique kill. |

**Sweeps.** `grep` over the whole tree (excluding `doc/plans/`) for `three ways` / `three-way` /
`reads_three` / `four_ways`, for `context-load` co-occurring with "three", for
`metrics-dispatch-boundaries`, and for `dispatch_boundary` inside `audit.py`.

⚠ **Corrected under adversarial review.** The `three ways` / `three-way` sweep was stated as tree-wide but
its result was carried into the Residue table only for `test/plan-marshall/manage-metrics/`. Re-run
tree-wide, it also returns two stale statements about the SAME retrospective-reader cell read, at
`test/plan-marshall/plan-retrospective/test_analyze_logs.py:984` and
`test_analyze_logs_behavior.py:173`. Those are now recorded as **G5**. The remaining `three-way` hits in
the tree were checked and are about other subjects (the reconciliation comparator's larger/equal/smaller
annotation, the ARTIFACT-coverage floor, chat-provenance splitting, the transmit disposition, the
pre-commit freshness gate) — no further instance of this defect class survives.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | Consumer audit of `audit.py`'s own zero-handling | consumer set enumerated, each one's zero-handling stated in the report | Yes | Yes | Yes | Yes | Report §D0 lists C1–C4 off one call site. Re-derived: `_parse_dispatch_boundary_totals` is called exactly once, `audit.py:7498` — the identifier occurs only three times in the file (`def` at `:7267`, the call at `:7498`, a comment mention at `:7219`). The consumer's **four** ledger reads — `audit.py:7501` (`ledger.get("total_tokens", 0) >`), `:7505` (`ledger_value > 0`), `:7507` (`ledger_value > row_value`), `:7509` (`max(row_value, ledger_value)`) — all fetch through `.get(field, 0)`, so absent and measured-`0` are indistinguishable at every one and the "arithmetically inert" verdict holds by reading. |
| D1 | Provenance gate in `_parse_dispatch_boundary_totals` | fingerprint-free all-zero ledger → four fields **absent**; fingerprinted row's measured zeros still sum | Yes | Yes | Yes | Yes | `audit.py:7350-7395` — two-pass row loop, `datable` reset per row at `:7355`, deferred zeros applied at `:7393-7394` (`:7387-7392` is the explanatory comment). Both halves executed: `test_fingerprint_free_all_zero_ledger_omits_the_context_columns` and `test_nonzero_fingerprint_keeps_sibling_measured_zeros` pass; the pre-fix mutant turns the first RED. Fingerprint rule is cell-for-cell identical to `analyze-logs.py:1181-1221` (`unmeasured` token → datable; `int(cell) != 0` → datable; unrecognised and short-row → not datable). |
| D2 | Docstring cross-reference corrected in lock-step | docstring names the undatable-zero / provenance-gate behaviour | Yes | Yes | Yes | Yes | `audit.py:7280` now reads "each context-load cell reads FOUR ways"; `:7293-7317` is the `THE PROVENANCE GATE` paragraph, naming the fingerprint rule, the per-row scope, the sibling reader's `indeterminate` spelling, and the fact that this reader can express the state only as field absence. |
| D3 | Regression tests, negative controls in both directions | all three directions pass, each seen red first | Yes | Yes | Yes | Yes, with a disclosed and independently confirmed exception | New module `test_audit_check_billing_composition_ledger_provenance.py` (215 lines, `TestDispatchBoundaryZeroProvenance`, 7 collected from 6 functions), plus `test_undatable_fixture_carries_no_post_token_fingerprint` and `test_undatable_zeros_are_not_measurements_in_either_reader` in `test_record_model_representability.py:876-940` over the new shared `undatable/` fixture. The report's RED-pre-fix table reproduces exactly under the pre-fix mutant (see Method); the two negative controls are green pre-fix, which the report discloses rather than hiding, and they are non-vacuous under the over-correction mutant. |

No deliverable is other than a clean pass. Two notes that are not failures:

**D1 — the gate's scope is narrower than the sibling's, by pre-existing construction.** `audit.py` resolves
the four context columns **by name from the declared header** (`audit.py:7358` `if ledger_field not in
columns: continue`), while `analyze-logs.py` resolves them **positionally at index 5–8**
(`analyze-logs.py:1182-1183`). For a canonical nine-column header the two agree exactly, which is what all
the plan's fixtures and the archived corpus carry. For malformed headers they still diverge — that is
residue R1-L2, recorded by the run and re-confirmed open here (see Residue).

**D3 — "each seen red first" is met for four of six directions in the literal sense.** The two negative
controls cannot be red against pre-fix code by construction; the report says so in plain terms and
substitutes a stronger check. I reproduced that substitute: under `if False:` both controls fail, so they
demonstrably kill the over-correction they exist for.

## Report accuracy

**Contradicted by the tree — one figure.**

- §D3: *"The two modules now stand at 211 and 259 lines."* The new module is **215** lines, both at the
  landed commit (`git show d1c31533:…ledger_provenance.py | grep -c ""` → 215; `git show --stat` shows 215
  insertions for a new file) and at HEAD. The 259 for
  `test_audit_check_billing_composition_reconstruction.py` is correct. The rationale the figure supports —
  that appending the cluster would have exceeded the 400-line module budget — is unaffected (215 + 259 =
  474).

**Line references that no longer resolve, but are not contradictions.** The report cites `audit.py:6932-6943`
(the consumer) and `audit.py:6773` (`dict.fromkeys`). In the landed tree those are `:7498-7509` and `:7329`.
The branch was cut from `89edc991`, where `dict.fromkeys(_BC_LEDGER_FIELDS, 0)` sits at `:6739`; adding the
run's own ~34 lines above it lands on `:6773`. The references were accurate when written and drifted only
because the squash landed on a later `main`. Every symbol-level claim they carry re-derives correctly.

**Checked and found accurate.**

- D0's "exactly one site" — re-derived, `audit.py:7498` is the only call.
- D0's C1–C4 zero-handling table — each read opened; measured-`0` and absent are indistinguishable at all
  four.
- "7 collected cases from 6 test functions" — `--collect-only` → 7.
- The RED-pre-fix table — reproduced exactly (4 gate tests + the cross-reader test red; both negative
  controls green).
- "Under that mutant both controls fail — as do `…does_not_date_its_neighbour` and two PRE-EXISTING tests" —
  reproduced; the over-correction mutant fails exactly those, plus the negative-value test.
- "`dated-first` is the *unique* kill among all seven scenarios" under the file-level mutant — reproduced,
  1 failed / 656 passed.
- The positivity mutant's unique kill — reproduced.
- PR-1's rejection premise: `totals` is built with `dict.fromkeys(_BC_LEDGER_FIELDS, 0)` (`audit.py:7329`),
  not a `defaultdict`; the two controls do assert a datable zero is present as `0` and pass.
- S-3: `CHECK_ERA["billing-composition"]` is still `"#1086"` (`audit.py:489`), pinned at
  `test_audit_check_inventory_consistency.py:100`.
- R2-6: no surviving `.py`, skill-doc, or standard reference to the pre-rename test name — the only
  `reads_three_ways` hits left are the two **retrospective-reader** tests, which are different tests and are
  declared residue.
- R2-1: the refuted clause *"which this reader expresses as the field's absence"* survives nowhere in the
  tree except inside the findings row that records it as fixed.
- "The archived corpus was not touched. The diff contains no corpus file." — confirmed from
  `--name-status`.
- The fingerprint rule is behaviour-identical to `analyze-logs.py` — confirmed by reading both, including
  the short-row and unrecognised-cell cases, which set no fingerprint on either side.

**Not re-verified (see *What could NOT be verified*).** The `./pw verify` totals, the discarded differential
instrument, the wall-clock figures, the reviewer-participation bodies, and the branch commit SHAs.

## Out-of-scope compliance

Compliant. The landed diff is nine paths and contains no undeclared collateral change:

- **`analyze-logs.py`, the `manage-metrics` writer, the archived corpus** — all untouched, as the plan's
  ⛔ boundary requires.
- **`data-format.md`** — edited, one line. The plan permitted an edit **only if** D0/D1 made the standard's
  wording inaccurate. I checked both paragraphs. The *provenance wording* (`:938`) was **not** changed and
  did not become false: its first sentence is an existence claim about the retrospective reader, its second
  a general conditional about readers that do not recover provenance, and neither asserts audit.py's
  membership. The *Restating surfaces* list (`:944`) **was** changed, and its previous description of
  surface #4 ("the hand-copied `_BC_LEDGER_COLUMNS` tuple") had genuinely become an incomplete statement of
  what must move in lock-step. The edit is count-preserving — still "four surfaces" — which keeps the
  mirror at `analyze-logs.py:987` ("names FOUR surfaces") true without touching the out-of-scope file. The
  run's own reasoning here holds up on inspection.
- **`checks/billing-composition.md`** — inside the plan's Expected surface (the same skill as `audit.py`),
  and a genuine restating surface the diff would otherwise have left stale.
- **The plan's two further named residues** (the *when*-not-*what* denominator, the stale-closed partiality
  verdict) were not folded in.
- No status or bookkeeping write under `doc/plans/` outside this plan's own directory.

## Residue carried forward

| Residue declared in report-01.md | Still open at HEAD? | Evidence |
|---|---|---|
| The two readers still disagree about **datability itself** on malformed input — `audit.py` resolves context columns by header **name**, `analyze-logs.py` **positionally** at 5–8 | **Open** | `audit.py:7358` vs `analyze-logs.py:1182-1183`. A 5-column header with 9-cell rows makes `audit.py` measure nothing while `analyze-logs.py` measures all four and dates the row. A missing `rows[]{…}:` line leaves `audit.py` returning `{}` (`in_rows` never set, `:7346`) while `analyze-logs.py` parses the row (its skip list is prefix-based, `:1126`). |
| `checks/billing-composition.md` is a restating surface registered in **no** lock-step list | **Open** | It now carries the full gate text (`:34-71`), and neither `data-format.md:944` nor `analyze-logs.py:987-996` names it. |
| Two stale "three ways" test names describing the **retrospective** reader | **Open** | `test_record_model_representability.py:455` (`test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader`) and `:783` (`test_unmeasured_fixture_reads_three_ways_in_the_retrospective_reader`). A third instance is the comment at `:450` ("the third point of the three-way distinction"). The file is now internally asymmetric: its audit-side sibling was renamed, these were not. |
| Untested edges — whitespace-padded cells; a header omitting/reordering a context column | **Open, and the judgement holds** | Both readers strip (`audit.py:7347`, `analyze-logs.py:1189`), so whitespace has nothing to protect. The header case is the first residue item above. |
| Plan 420's own two residues (a denominator stating *when* not *what*; a partiality verdict blind to a stale-closed phase) | **Open, not this plan's** | Untouched by this diff. |
| Step-9 proposal: "red-against-pre-fix is not evidence that a test pins its stated invariant" — offered to the operator, explicitly not self-approved | **Open** | `.claude/skills/cloud-plan-lane/SKILL.md` § Step 6 carries no such obligation at HEAD. Deliberate, per the report. |

## What could NOT be verified

- **The branch's nine commits and their SHAs** (`2297407`, `2ccec2c`, `70d88ce`, `85848a8`, `7a2168e`,
  `a487035`). `git cat-file -t` reports every one absent — the PR was squash-merged, so the branch history
  is not in this clone. The per-commit `./pw quality-gate` claims and the `Co-Authored-By` trailer check
  rest on that history and are therefore unverifiable here.
- **The `./pw verify` figures** (`20472 passed, 14 skipped`, 498.37 s, and the superseded 417.56 s run).
  Not re-run — a full verify is a ~500 s six-dimension build, outside the cheap-check budget. The audit +
  representability subset (657 tests) is green at HEAD.
- **The D0 differential instrument.** The report states it was deliberately not committed and is gone; it
  is not in the diff and not in the tree, so its result cannot be re-executed. The *conclusion* it supports
  (arithmetic inertness) was independently re-derived here by reading all four consumer expressions.
- **Reviewer participation and the merge gate.** The three comment surfaces on PR #1278, the
  `sourcery-ai` rate-limit body, and the `mergeable_state` reading were not re-fetched; only the merge
  commit `d1c31533` is observable from the tree.
- **Wall-clock and token figures.** No artifact in the tree carries them.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Everything below was re-derived from the tree at `57731bb4`, not read off this document.

- **Every deliverable row** (all four were clean passes, so all four were re-checked behaviourally).
- **Both readers EXECUTED**, not read: a probe loaded `audit.py` and `analyze-logs.py` by file location
  and drove `_parse_dispatch_boundary_totals` / `_parse_dispatch_boundary_file` off eight purpose-built
  ledgers (fingerprint-free all-zero; nonzero-fingerprinted; `unmeasured`-token-fingerprinted; short
  header + long rows; malformed `total_tokens`; missing `rows[]{…}:` line; reordered header; empty
  header declaration). D1's two halves reproduce exactly — the fingerprint-free ledger omits all four
  context fields while `total_tokens` still sums, and both fingerprint kinds keep their sibling measured
  zeros as `0`.
- **Three of the four mutants re-applied** to `audit.py` (`git diff --quiet` returned 0 before each;
  restored from a byte snapshot taken to `$TMPDIR`, never by `git checkout`/`restore`/`stash`):
  `if datable:` → `if True:` → **5 failed**, the cross-reader test failing at its audit half, line 940 —
  exactly as reported; `→ if False:` → **7 failed**, both negative controls among them, confirming they
  are non-vacuous; `datable = True` → `datable = value > 0` → **1 failed**, the unique kill claimed.
- **Every stated figure re-derived.** New module = **215** lines (the document's own correction of the
  report's "211" is right); sibling = 259; `--collect-only` = **7** from 6 functions; the two modules =
  **24 passed**; whole audit suite + representability = **657 passed** at HEAD; `CHECK_ERA
  ["billing-composition"] == "#1086"` at `audit.py:489`, pinned at
  `test_audit_check_inventory_consistency.py:100`; the landed diff = **9 paths**, no `analyze-logs.py`,
  no writer, no corpus; the `data-format.md` edit is a **single line** and count-preserving.
- **Sweeps re-run BROADER than the originals**: `three ways|three-way|three_ways` across the whole test
  tree and all four relevant bundles (not only `test/plan-marshall/manage-metrics/`), and
  `metrics-dispatch-boundaries` across `marketplace/` + `.claude/` to re-test the "exactly two readers"
  premise.
- **Not re-checked:** the file-level-fingerprint mutant (`datable` hoisted out of the row loop) — three
  mutants were judged sufficient to establish the gate's tests bite; the `./pw verify` totals; the branch
  commit SHAs (still absent from this clone); PR #1278's review surfaces; and all wall-clock/token
  figures. These remain in *What could NOT be verified*.
- **Concurrency note.** Midway through this review another agent held a mutant
  (`provably_post_change = False` → `True`) in `analyze-logs.py`, which made
  `test_undatable_zeros_are_not_measurements_in_either_reader` fail at its *retrospective* half (line
  926). That file was left untouched and the failure vanished when the other agent restored it. The
  incident is worth recording as evidence rather than noise: the cross-reader test demonstrably kills a
  mutation on **either** reader, which is precisely the pinning property D3 was meant to buy.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| Verdict | `fully-implemented` | **upheld** | All four deliverable rows re-checked; D1 and D3 executed and mutation-tested; D0's absence claim re-derived by reading all four consumer expressions; D2's docstring read at `:7280` and `:7293-7316`. No row is other than a clean pass. |
| D0 | Consumer set enumerated; single call site; zero-handling arithmetically inert | **upheld, evidence corrected** | Single call site confirmed (`audit.py:7498`). Two corrections: the file's `metrics-dispatch-boundaries` hits are `:166`, `:7111`, `:7499` — the other four lines the row listed (`:7115`, `:7219`, `:7306`, `:7765`) are `dispatch_boundary` hits from a different grep, and the merged list omitted `:361`, `:373`, `:7187`, `:7268`, `:7712`. And the consumer makes **four** ledger reads, not three (`:7501`, `:7505`, `:7507`, `:7509`), matching the report's own C1/C2a/C2b/C2c. The inertness conclusion is unaffected: every read goes through `.get(field, 0)`. |
| D1 | Gate lands; both halves observable; rule cell-for-cell identical to `analyze-logs.py` | **upheld** | Executed both halves. Fingerprint-free all-zero ledger → `{'total_tokens': 9100}`; nonzero-fingerprinted → all four present, three of them `0`; `unmeasured`-token row → the three siblings present as `0`. Identity of the rule re-read at `audit.py:7357-7394` vs `analyze-logs.py:1182-1222`, including the short-row and unrecognised cases. Line range corrected to `:7350-7395`, apply at `:7393-7394`. |
| D2 | Docstring names the four-way read and the gate | **upheld** | `audit.py:7280` "reads FOUR ways"; `:7293-7316` is the gate paragraph, naming the fingerprint rule, the per-row scope, the sibling's `indeterminate` spelling, and this reader's absence-only expressibility. |
| D3 | Three directions pass, each seen red first (with a disclosed exception) | **upheld** | 7 collected from 6 functions; 24 passed with the representability module; the pre-fix mutant kills exactly the 5 reported; the over-correction mutant kills exactly the 7 reported, including both negative controls — so the disclosed "cannot be red pre-fix" exception really is compensated. |
| Report accuracy — "211 lines" | Contradicted; actual 215 | **upheld** | `wc -l` = 215 at HEAD; `git show --stat d1c31533` = 215 insertions for the new file. |
| "Swept, clean" — `three ways` / `three-way` | Only the two retrospective-reader test names survive | **refuted as stated** | The sweep is described as tree-wide but its result was carried only for `test/plan-marshall/manage-metrics/`. Tree-wide it also returns `test/plan-marshall/plan-retrospective/test_analyze_logs.py:984` and `test_analyze_logs_behavior.py:173`, both describing the same reader's cell read. Filed as **G5**. |
| "exactly two readers" premise | Third-party readers listed, no verdict recorded | **upheld, verdict now stated** | `_read_dispatch_boundary_totals` (`manage-metrics.py:727`) and `load_boundary_rows` (`_ledger_reconciliation.py:214`) both read only columns 0–2. Neither touches a gated column. |
| G1 | Mirror's surface-#4 description drifted from `data-format.md:944` | **upheld** | Both texts read side by side; mirror still says "the hand-copied `_BC_LEDGER_COLUMNS` / `_BC_LEDGER_UNMEASURED_TOKEN` pair", standard now adds the cell read and the gate. Both still say "four". `git show d1c31533` confirms the run's own one-line edit opened the gap. A cross-reference to G2 (same two paragraphs) was added so the two fixes are not landed as conflicting rewrites. |
| G2 | `checks/billing-composition.md` is an unregistered fifth restating surface | **upheld, line range corrected** | The gate text runs `:34-72`, not `:34-71`. Named in neither list — confirmed by reading `data-format.md:944` and `analyze-logs.py:987-996` in full. |
| G3 | Two readers diverge on column resolution; three divergence classes | **upheld, one sub-claim corrected and evidence upgraded from read to executed** | All three classes executed against both readers; a fourth (header reorder → transposed `input_tokens`/`output_tokens`) confirmed too, and the `rows[]{}:` empty-declaration case confirmed as the one malformed shape they agree on. Correction: in the short-header class `audit.py` does not "measure nothing" — it measures `total_tokens` and none of the four context columns. Severity `medium` upheld: the divergences need malformed input to reach, so this is latent, not a shipped false signal. |
| G4 | Three stale "three ways" sites in `test_record_model_representability.py` | **upheld** | `:450`, `:455`, `:783` all present at HEAD; `analyze-logs.py:1177-1225` confirms the reader is four-state. Severity `low` upheld — test names and a comment, no behaviour. |
| G5 | — | **added** | New. Two stale three-state statements in `test/plan-marshall/plan-retrospective/`, one of which (`test_analyze_logs.py:984`, "The three-way read is per COLUMN, not per row") is now false about the mechanism as well as the count, since the fourth state is decided per row. |

**Documents corrected.**

- `verification.md`: the D0 evidence cell (call-site enumeration and the three-vs-four consumer reads);
  the D1 line range and the deferred-zero apply line; the Sweeps paragraph, which now records that the
  tree-wide result was not carried into the Residue table and names what it missed; the third-party
  reader bullet, which now states the verdict it was collected for. The headline verdict is unchanged.
- `gaps.md`: **Open items** 4 → 5; G1 gained a cross-reference note to G2; G2's line range `:34-71` →
  `:34-72`; G3's "What is wrong" replaced with the executed per-class results (and its
  "measures nothing" overstatement corrected), its Fix and Done-when widened to the fourth class; G5
  added; a `## Refuted during adversarial review` section added recording that nothing was refuted and
  by what means each surviving gap was re-derived.

**Residual doubt — what a third reviewer should look at first.**

1. **The file-level-fingerprint mutant** is the one claimed unique kill I did not reproduce. If any
   mutant's reported result is wrong, it is the least-corroborated one.
2. **`_to_int`'s degrade-to-`0` on the legacy five columns** (`audit.py:955`, reached at `:7365`) is a
   *second* false measured zero in the same function — a malformed `total_tokens` is summed as `0` **and
   marked measured**, with no provenance gate. The docstring declares this deliberate ("their zeros are
   never gated") and the plan scoped the gate to the four context columns, so it is not a defect against
   this plan. But it is the same over-claim shape one column to the left, it is reachable from any
   malformed row, and G3(b) shows it produces a corpus entry the sibling reader discards entirely.
   Whether the legacy columns deserve their own absent-is-not-zero treatment is the question worth
   opening next.
3. **The archived corpus's actual composition.** Every claim here is about how the reader interprets
   bytes; nobody has re-derived how many archived plans actually carry fingerprint-free all-zero rows, so
   the practical magnitude of the corrected over-claim is still unmeasured — and `.plan/` is not in this
   clone, so it cannot be measured from here.
