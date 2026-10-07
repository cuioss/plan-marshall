# Gaps — 270-aggregate-cost-invisible-to-per-call-ceiling

The observability deliverable (D2) landed and works; what remains is a precision defect in the
cross-plan roll-up's *published denominator* (G1), an unguarded input path that feeds the per-plan
roll-up calls that never happened (G14), a duration-grammar asymmetry that makes the two roll-ups
disagree about the same log line (G4), a silent exclusion class in the folded-global reader (G5),
the reconcilability claim the docs and code comments make and the code does not keep (G2), the
missing precision pin that let G1 ship (G3), the schema-doc key-order drift the last round of fixes
reintroduced (G6, G7), three stale numeric claims in the run report (G8–G10), and the four residue
items the run itself declared open, of which one has since been closed elsewhere (G11–G13).
Fourteen entries, one per instance.

## G1 — Publish `total_script_seconds` at the precision its shares are computed against

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2931`
  (`"total_script_seconds": round(total_seconds, 1)`), against `audit.py:2887`
  (`rollup_total = round(total_seconds, 3)`) and `audit.py:2907-2909` (`share_pct`)
- **Evidence:** Loading `audit.py` and running `cross_global_log_analysis` over a one-line corpus
  `pm:a:a run (0.04s)` emits a block containing `total_script_seconds: 0.0` and
  `sub_precision_call_count: 0` beside the row
  `dominant-cost-caller,1x 0.040s 100.0% pm:a:a run,,informational`. A second corpus
  (`pm:a:a run (0.24s)`, `pm:b:b run (0.20s)`) publishes `total_script_seconds: 0.4` with shares
  `54.5 %` / `45.5 %`; recomputing those from the printed columns gives `60.0 %` / `50.0 %`, which
  sum to 110 %. Both cases re-reproduced independently on adversarial review, byte-for-byte,
  including the emitted line `dominant-cost-caller,1x 0.040s 100.0% pm:a:a run,,informational`.
- **Why it matters:** the block publishes a corpus total of `0.0 s` while naming a caller that owns
  100 % of it — a measured non-zero rendered as zero, in the instrument built to stop exactly that.
  It is the same arithmetic class as report finding #54 (rated Major by the PR reviewer), fixed for
  the row and left in the denominator the row is a share of.
- **Why high, not medium** (severity re-rated on adversarial review): this trips two of the high
  band's triggers at once, not the medium band's. **(1) A measurement misreports** — the emitted
  block is the measurement as far as any orchestrator reading it is concerned, and it publishes
  `total_script_seconds: 0.0` for a corpus that carries measured work, with no counter flagging the
  shortfall (`sub_precision_call_count: 0`, because a `0.04 s` call is *above* the writer's floor and
  so is not sub-precision — nothing in the block marks the total as unreliable). **(2) A documented
  contract is unimplemented** — `checks/global-log-analysis.md:94` promises each row's `share_pct` is
  a share *"of the published `total_script_seconds`"*, and `audit.py:2871-2873` promises *"a reader
  recomputing it from the printed columns gets the printed value back"*; neither holds below ~1 s.
  The medium band covers *"a false claim in shipped documentation"* — that is G2, the doc half. The
  code half is shipped behaviour that is wrong. The precedent settles it: the run's own reviewer
  rated the identical rounding-before-dividing defect **Major** one column over (finding #54), the
  run accepted that rating and fixed the row, and the report calls it *"the most consequential of the
  run … it made the roll-up misreport the very class of script the plan was written about"*. Rating
  the residue of that same defect medium is inconsistent with the precedent this entry itself cites.
  The misreporting regime — sub-second per-call durations — is precisely the many-fast-calls regime
  the plan exists to surface.
- **Action:** change `round(total_seconds, 1)` to `round(total_seconds, 3)` at `audit.py:2931` so the
  published denominator matches `rollup_total`.
- **Done when:** `cross_global_log_analysis` over a single `(0.04s)` call publishes
  `total_script_seconds: 0.04`, and for every roll-up row
  `round(row['cumulative_seconds'] / result['total_script_seconds'] * 100, 1) == row['share_pct']`.
- **Effort:** S
- **Risk if fixed:** the emitted `total_script_seconds` line gains decimals, which any consumer
  parsing it as text sees. Applying this exact change and running the whole audit test tree
  (`test/plan-marshall/audit-archived-plan-retrospectives/`) gave **640 passed**, so no in-tree test
  pins the old precision.

## G2 — Correct the reconcilability claim in the check doc

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/checks/global-log-analysis.md:94` and
  `:247`
- **Evidence:** line 94 — *"with each row's `share_pct` of the published `total_script_seconds`"*;
  line 247 — *"ranked by seconds owned with each row's share of `total_script_seconds`"*. The share is
  computed against a 3-decimal total; the published one is 1-decimal (see G1). The same claim appears
  in-code at `audit.py:2871-2873` and `:2884-2886`.
- **Why it matters:** this doc is what the orchestrator reads to adjudicate rows. It instructs a
  reader to reconcile a figure against a denominator that does not reconcile, and the discrepancy is
  worst precisely in the many-tiny-calls regime the check exists to surface.
- **Action:** land G1 first; the claim then becomes true and needs no edit. If G1 is rejected, amend
  both doc lines and the two `audit.py` comment blocks to state that `share_pct` is computed at
  millisecond precision while `total_script_seconds` is published at decisecond precision, so the two
  do not reconcile exactly below ~1 s.
- **Done when:** either `total_script_seconds` is published at the precision the shares use, or every
  site that claims recomputability states the precision difference.
- **Effort:** S
- **Risk if fixed:** none beyond doc churn.

## G3 — Pin the share/denominator reconciliation below the rounding granularity

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_global_log_analysis_cost_rollup.py:71`
  (`test_share_is_a_share_of_the_published_denominator`)
- **Evidence:** the test uses `30.0 s` and `10.0 s`, which round cleanly at one decimal, so it passes
  either way. Mutating `audit.py:2931` from `round(total_seconds, 1)` to `round(total_seconds, 3)`
  left the entire audit tree green (`640 passed`) — nothing pins the published denominator at all.
  The sibling tests `test_two_short_calls_do_not_both_report_the_whole_share` and
  `test_a_single_short_call_is_not_rendered_as_zero_seconds` deliberately work in the sub-decisecond
  regime but assert only on the roll-up rows, never on `total_script_seconds`.
- **Why it matters:** the run's own Proposal 4 says a new metric must be tested at the boundaries of
  its own precision. The rounding fix from finding #54 was tested at those boundaries for the row and
  not for the denominator, which is why G1 shipped.
- **Action:** extend `test_a_single_short_call_is_not_rendered_as_zero_seconds` to assert
  `result['total_script_seconds'] == pytest.approx(0.04)`, and add a case asserting that every row's
  `share_pct` equals the value recomputed from `cumulative_seconds / total_script_seconds` on a
  corpus whose total does not round cleanly (e.g. `0.24 s` + `0.20 s`).
- **Done when:** reverting G1's change makes at least one test in that module fail.
- **Effort:** S
- **Risk if fixed:** none; test-only.

## G4 — Make the per-plan duration grammar as strict as the global one

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:88`
  (`_DURATION_RE = re.compile(r'\((\d+\.?\d*)s\)')`), against `analyze-logs.py:112`
  (`_GLOBAL_LOG_DUR_RE = re.compile(r'\((\d+(?:\.\d+)?)s\)\s*$')`)
- **Evidence:** loading the module through `test/conftest.py` and feeding both readers the same line
  bodies:

  ```
  per-plan extract_script_durations -> [('pm:x:x', 5000.0), ('pm:y:y', 1500.0), ('pm:z:z', 1500.0)]
  global: pm:x:x run (5.s)                  -> None
  global: pm:y:y run (1.5s) failed          -> None
  global: pm:z:z run (1.5s) retried (2.00s) -> 2.00
  ```

  ⚠ **Reachability, added on adversarial review.** All three line bodies above are *synthetic*. The
  only writer of these logs is `plan_logging.py:344`
  (`message = f'{notation} {subcommand} ({duration:.2f}s)'`), and `format_log_entry`
  (`plan_logging.py:112-142`) puts every extra field on its own indented continuation line, so a
  real entry's **header** line always ends in a well-formed `(N.NNs)`. No current writer emits
  `(5.s)`, and none emits a second parenthesised duration on a header line. This entry is therefore
  a **latent asymmetry and a documentation mismatch**, not a defect that today's corpus trips — which
  is why it stays at medium while the sibling G14, whose writer path is real, is high. Fix them
  together: they are the same file, the same function and the same principle (make the per-plan
  reader as strict as the global one).

  ⚠ The `except ValueError` at `analyze-logs.py:394` is **unreachable**: `\d+\.?\d*` can only capture
  `5`, `5.` or `5.5`, all of which `float()` accepts, and `(1.2.3s)` does not match the pattern at all
  (verified first-party — `extract_script_durations(['pm:q:q run (1.2.3s)'])` returns `[]`). Keeping
  it is harmless, but it must not be described as a live guard.

- **Why it matters:** `_DURATION_RE` feeds `script_cost_rollup`, the deliverable this plan shipped. A
  malformed `(5.s)` enters that roll-up as a measured **5 s**; a line with two parenthesised
  durations enters as the **first** while the global roll-up takes the **last**, so the two
  instruments the plan added publish different cumulative totals for the same physical line while
  `references/log-analysis.md:109-110` tells the reader they are the *"Same shape … different
  population"*. Report finding #42 established the principle ("refuse the match rather than invent a
  zero") and applied it to one of the two readers, which is the exact
  guard-on-one-half-of-a-pair shape the run's own Proposal 3 names.
- **Action:** anchor and tighten `_DURATION_RE` to `r'\((\d+(?:\.\d+)?)s\)\s*$'`, or replace both
  uses with the single strict pattern; the `except ValueError` in `extract_script_durations` may
  stay, but comment it as unreachable rather than as an active guard.
- **Done when:** `extract_script_durations` returns `[]` for `pm:x:x run (5.s)` and for
  `pm:y:y run (1.5s) failed`, and returns `2000.0` (not `1500.0`) for
  `pm:z:z run (1.5s) retried (2.00s)`; a test asserts each of the three.
- **Effort:** S
- **Risk if fixed:** `_DURATION_RE` also feeds `script_duration_p50/p95/max_ms` and
  `slowest_scripts`, so tightening it can move those pre-existing per-plan figures for any log line
  whose duration is not terminal. Verify the plan-retrospective test tree and re-read the archived
  fixtures before landing.

## G5 — Count the duration-bearing lines the global grammar refuses

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1462-1477`
  (`analyze_folded_global_logs`)
- **Evidence:** when `_GLOBAL_LOG_DUR_RE.search(rest)` returns `None` the line contributes to
  `total_lines` and to nothing else — not `slow_call_count`, not `cost_rollup`, and not
  `unattributable_calls` (which is incremented only inside the `if dur_match:` branch, at
  `analyze-logs.py:1477`). Verified against `pm:y:y run (1.5s) failed`, which the global reader
  refuses entirely.
- **Why it matters:** the fragment's whole design claim is that every exclusion is published so a
  total is legible as a floor rather than a measurement. One exclusion class — a call the grammar
  could not parse — is silent. The cross-plan tier does not have this hole: an untimed
  notation-headed line still lands in `untimed_call_keys` (`audit.py:2950`).
- **Action:** add an `unparsed_duration_calls` counter (a **separately named** field — do not fold it
  into `unattributable_calls`, whose population is disjoint from it: `unattributable_calls` counts
  lines that *did* parse a duration and carried **no** notation, `analyze-logs.py:1477`) incremented
  when a line carries a parenthesised `…s)` body the strict pattern refuses; publish it beside
  `unattributable_calls` and document it in `references/log-analysis.md`. Publish alongside it the
  classification the reconciliation needs, because the two existing counters do not partition
  anything on their own: state, in `references/log-analysis.md`, that every line matched by
  `_GLOBAL_LOG_LINE_RE` — i.e. counted in `total_lines` — falls into exactly one of four classes:
  1. **measured and attributed** — duration parsed *and* a notation found (`folded_durations`);
  2. **unattributable** — duration parsed, no notation (`unattributable_calls`);
  3. **refused** — a parenthesised `…s)` body the strict pattern would not parse
     (`unparsed_duration_calls`, new);
  4. **no duration claimed** — the line carries no duration body at all (a residual; publish it as
     `untimed_lines` if the reconciliation is to be checkable at all).
- **Done when:** `analyze_folded_global_logs` over a log containing one well-formed call and one
  refused-duration call publishes a nonzero `unparsed_duration_calls`; and a test asserts the
  partition holds over a fixture carrying at least one line of each class —
  `len(folded_durations) + unattributable_calls + unparsed_duration_calls + untimed_lines ==
  total_lines`, with `total_lines` (the matched-log-entry population) as the denominator. ⚠ Do **not**
  write the check as `measured + refused + unattributable` against a notation-headed line count: the
  unattributable class is by construction *not* notation-headed, so that equation cannot balance.
- **Effort:** M
- **Risk if fixed:** a new fragment key; `references/log-analysis.md` and any consumer asserting the
  fragment's key set must be updated in lock-step.

## G6 — Align the documented `ranked[*]{}` header with the emitted one

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md:61`
- **Evidence:** the doc states
  `ranked[*]{notation,calls,cumulative_ms,share_pct,max_ms,sub_precision_calls}`. The dict is built at
  `analyze-logs.py:481-496` in the order `notation, calls, cumulative_ms, sub_precision_calls,
  share_pct, max_ms`, and `serialize_toon` (`marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py:552`)
  iterates `data.items()` while `_is_uniform_array` (`:520-527`) builds the header from
  first-occurrence key order — so the emitted header is the dict order, not the documented one.
- **Why it matters:** report finding #22 recorded exactly this class ("`log-analysis.md` key order did
  not match emission order") as a defect and fixed it; the later `sub_precision_calls` addition
  (finding #55) reintroduced it. A schema doc whose header does not match the artifact is what a
  downstream parser is written against.
- **Action:** move `sub_precision_calls` to the fourth position in the documented header at
  `log-analysis.md:61`.
- **Done when:** the documented header string is byte-identical to the header
  `serialize_toon` emits for a non-empty `ranked` list.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Align the documented `script_cost_rollup` key order with the emitted one

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md:50-61`
- **Evidence:** the doc orders the block `population, ceiling_seconds, calls_at_or_over_ceiling,
  total_calls, total_duration_ms, distinct_scripts, ranked_count, sub_precision_calls, ranked`. The
  return dict at `analyze-logs.py:498-508` orders it `population, ceiling_seconds,
  calls_at_or_over_ceiling, total_calls, total_duration_ms, sub_precision_calls, distinct_scripts,
  ranked_count, ranked` — `sub_precision_calls` sits two keys earlier than documented.
- **Why it matters:** same reason as G6; this is the second instance of the same drift, introduced by
  the same commit.
- **Action:** move `sub_precision_calls` (and its explanatory comment) to sit between
  `total_duration_ms` and `distinct_scripts` in `log-analysis.md`.
- **Done when:** the documented key sequence matches the emitted TOON key sequence line for line.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Correct the run report's test-count table

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/270-aggregate-cost-invisible-to-per-call-ceiling/report-01.md:130-136`
- **Evidence:** the report says *"**37 test functions added**, 0 removed"*, with `test_analyze_logs.py`
  *"27 (78 → 105)"* and the new cross-plan module *"9 (new module)"*, labelled *"Re-derived by AST at
  the moment of this claim"*. AST diff of `89edc99` against `89edc99^` gives **43 added**:
  `test_analyze_logs.py` 30 (78 → 108), the new module 12, `test_audit.py` 1 (81 → 82). The 6-test
  delta is exactly the tests added by the post-report CodeRabbit fixes (#54, #55, #58, #59).
- **Why it matters:** the report's own Proposal 2 is that a claim about the tree must be re-derived at
  finalize. This is a claim about the diff, which the report says is *"already re-derived"* — and it
  was not.
- **Action:** re-derive the table by AST against the merged commit and correct the three figures, or
  state the commit the count was taken at.
- **Done when:** each figure in the table matches an AST count taken against `89edc99`.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Correct the run report's pre-fix failure figures

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:115`
- **Evidence:** the report records
  `test_analyze_logs.py -k "ScriptCostRollup or ContextPositionCost or PerCallCeilingPreserved"` →
  *"23 failed, 1 passed"* against `origin/main`. Running that same selection against the `89edc99^`
  sources gives **29 failed, 1 passed** (30 selected). The neighbouring
  `test_audit_checks.py (whole file) → 10 failed, 445 passed` row cannot be re-derived at all — that
  module was decomposed by #1258 and no longer exists.
- **Why it matters:** the plan's Verification section makes recording the pre-fix failure a named
  obligation. The record as written no longer describes the shipped test set, and half of it points
  at a file that is gone.
- **Action:** re-run the selection against the merge-base sources and restate both rows, replacing
  the `test_audit_checks.py` row with the module that survived
  (`test_audit_check_global_log_analysis_cost_rollup.py` → 11 failed, 1 passed).
- **Done when:** both figures reproduce from the stated selection against the stated base.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Scope the run report's "zero hits" sweep claim

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:36`
- **Evidence:** *"A content sweep for `cumulative` / `total_duration` / `share_of_total` / `total_ms`
  across `plan-retrospective` returned **zero** hits."* Re-derived at `89edc99^`: zero hits under
  `…/plan-retrospective/scripts/`, but one hit across the skill directory —
  `…/plan-retrospective/SKILL.md:157` ("assign-cumulative"). The PR body scoped the claim to
  `plan-retrospective/scripts`; the report dropped the scope.
- **Why it matters:** the report's own finding #34 is *"Report's 'zero hits' sweep claim not scoped —
  Fixed in the report"*. It was fixed in the PR body and not in the sentence the report shipped, so
  the disposition overstates.
- **Action:** restore the `scripts` scope to the sentence.
- **Done when:** the sweep the sentence describes reproduces zero hits verbatim.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Widen the archived-plan fragment fixture to the current section-4 contract

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-log-analysis.toon`
- **Evidence:** the fixture ends at `top_error_tags[0]:` and carries none of `script_cost_rollup`,
  `context_position_cost`, `global_log_signals`, `build_time`, `dispatch_boundaries`, `findings` or
  `artifact_emission`, while
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/report-structure.md:16` now
  names `script_cost_rollup` and `context_position_cost` in the section-4 contract.
- **Why it matters:** the run declared this open and argued nothing breaks (`retro_sections.py`
  renders the fragment generically), which I confirmed — `retro_sections.py` references
  `script_cost_rollup` only inside a comment (`:122`). The consequence is that no test exercises the
  render path for the new keys, so a rendering regression on them is invisible.
- **Action:** extend the fixture with a representative `script_cost_rollup`, `context_position_cost`
  and `global_log_signals` block, and assert the rendered section-4 output names them.
- **Done when:** a section-4 render test fails if `script_cost_rollup` or `context_position_cost` is
  dropped from the rendered output.
- **Effort:** M
- **Risk if fixed:** the fixture is shared; widening it can move assertions in other
  plan-retrospective render tests.

## G12 — Discharge D1's numeric half, D3 and D4(b) when a corpus is reachable

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** the plan's D1(b), D3 and D4(b); the instrument to use is
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2887-2912` (`cost_rollup`)
- **Evidence:** `report-01.md:23` records `.plan/local/archived-plans/` and `.plan/local/plans/` as
  absent from the clone; that is still true here, so the call counts, cumulative durations and
  share-of-total for the two named hot paths remain unmeasured, D3 was never scoped, and the
  title/session-contract assertion D4(b) requires has no subject. No successor plan in
  `doc/plans/code-intelligence-substrate/` picks this up.
- **Why it matters:** the plan's Goal has two halves and only the observability half shipped. The
  reduction half is not cancelled — it is deferred behind a measurement that now exists but has never
  been run against a real corpus.
- **Action:** on a machine with an archived-plan corpus, run `global-log-analysis` and read
  `cost_rollup` / `sub_precision_call_count`; decide D1(b) from the ranking; then scope D3 and write
  the D4(b) delivery assertion against whichever path it names.
- **Done when:** the two hot paths' call counts, cumulative seconds and shares are stated
  first-party, and either a reduction lands with a delivery-asserting title/session test or a
  recorded reason replaces it.
- **Effort:** L
- **Risk if fixed:** D3 touches the terminal-title / session-binding contract, which the plan makes a
  hard invariant; a reduction there risks the title-delivery fix and the wait-mechanism stamp.

## G13 — Widen the log writer's duration precision, or the floor caps the instrument

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/plan_logging.py:344` —
  `message = f'{notation} {subcommand} ({duration:.2f}s)'`
- **Evidence:** the writer still formats at two decimals, so any call under 5 ms is recorded as
  `0.00s` and contributes nothing to either roll-up. `sub_precision_calls` (`analyze-logs.py:487, 504`;
  `audit.py:2906, 2955`) makes the shortfall legible but does not remove it.
- **Why it matters:** a script whose calls are all under 5 ms — plausibly the pre-tool-use hook this
  plan was written about — reports a cumulative total of `0.0 s` however many times it runs. If G12's
  corpus work shows the hot paths sit below that floor, widening the format is the prerequisite for
  measuring them at all.
- **Action:** widen the format (e.g. `%.4f`) in `plan_logging.py` and relax the two duration patterns
  that read it if needed; keep `sub_precision_calls` as the residual counter.
- **Done when:** a 1 ms call is recorded with a nonzero duration and contributes to both roll-ups,
  and `sub_precision_calls` counts only calls below the new floor.
- **Effort:** M
- **Risk if fixed:** every historical log line stays at the old precision, so any cross-era total
  mixes two floors; the change is a `manage-logging` boundary and would want its own `CHECK_ERA`
  treatment.

## G14 — Gate the per-plan duration reader on the log-line shape

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:378-397`
  (`extract_script_durations`), against `analyze-logs.py:1455-1462` (`analyze_folded_global_logs`)
- **Evidence:** `extract_script_durations` applies `_DURATION_RE` and `_NOTATION_RE` to **every line
  handed to it**, with no check that the line is a log *entry header*. Its sibling
  `analyze_folded_global_logs` gates on `_GLOBAL_LOG_LINE_RE.match(raw)` first and `continue`s
  otherwise. The writer produces the lines this exploits: on a non-zero exit,
  `log_script_execution` (`manage-logging/scripts/plan_logging.py:346-360`) passes `exit_code`,
  `args`, `stdout` and `stderr` to `format_log_entry`, which emits each as an indented
  **continuation line** (`plan_logging.py:138-142`) inside the same entry. Fed one real writer-produced
  entry:

  ```
  [2026-08-19T07:41:58Z] [ERROR] [0ee8a3] pm:b:build run (1.20s)
    exit_code: 1
    args: pm:b:build run --command-args verify
    stdout: tests finished pm:t:t run (9.99s) ok

  per-plan extract_script_durations -> [('pm:b:build', 1200.0), ('pm:t:t', 9990.0)]
  global reader                     -> 1.20   (three continuation lines SKIPPED, no header)
  ```

  The per-plan reader invented a `pm:t:t` call of 9.99 s that never ran, from text a failing script
  printed to stdout. The global reader, correctly, saw only the header's 1.20 s.
- **Why it matters:** `extract_script_durations` is the sole input to `summarize_script_cost`
  (`analyze-logs.py:1521`), i.e. to `script_cost_rollup` — **the deliverable this plan shipped** — and
  also to `total_duration_ms`, every `share_pct`, `script_duration_p50/p95/max_ms` and
  `slowest_scripts`. A captured-output line can therefore add a call that never happened, attribute
  wall-clock to a script that did not spend it, and outrank a genuinely dominant script. The function
  predates this plan, but before this plan it only fed percentiles; the plan promoted it to the input
  of a published cumulative cost roll-up, which is what makes the missing guard consequential now.
  Unlike G4, the writer path is real: every non-zero-exit script call writes `args`/`stdout`/`stderr`
  continuation lines, and the `args` line always carries a notation. Whether a specific corpus is
  inflated depends on whether a captured body also carries a parenthesised `(N.Ns)`; the guard's
  absence does not.
- **Action:** in `extract_script_durations`, match each line against the entry-header grammar before
  parsing it — reuse `_GLOBAL_LOG_LINE_RE` and search only within its `rest` group, mirroring
  `analyze_folded_global_logs:1455-1462` — so continuation lines are skipped.
- **Done when:** `extract_script_durations` over the four-line entry above returns exactly
  `[('pm:b:build', 1200.0)]`, and a test in
  `test/plan-marshall/plan-retrospective/test_analyze_logs.py` asserts that a `stdout:` continuation
  line carrying a notation and a `(N.Ns)` body contributes nothing to `script_cost_rollup`.
- **Effort:** S
- **Risk if fixed:** `script_duration_p50/p95/max_ms` and `slowest_scripts` are pre-existing figures
  computed from the same list, so gating the input can move them for any plan whose script log
  contains ERROR entries — a correction, but one that changes previously published per-plan numbers.
  Land it with G4, which touches the same function, and re-read the archived-plan fixtures.
