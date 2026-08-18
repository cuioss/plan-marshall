# Verification — 420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make

**Verified against:** commit `85432346056d96741b8b27090becf41fca51aa49`   **Landed as:** PR #1255, commit `d5b2c4e30b44ab63129aa93f49df761f44efb1f7`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and `report-01.md` in full. Located the landing with
`git log --oneline --all --grep '#1255'` → `d5b2c4e3`; read its full diff
(`git show --stat -M`, `git show -- <path>` for each of the five source files) and its rename record
(`git show --raw -M`).

Opened against HEAD:

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`
  — `_parse_dispatch_boundary_file` (lines 1030–1226) in full, plus `summarize_context_position_cost`
  (lines 526–706) and `read_dispatch_boundaries_per_phase` (line 1346).
- `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py`
  — `UNMEASURED_COLUMN_TOKEN` comment (line ~118–137), `cmd_record_dispatch_boundary` write/return path
  (lines 3196–3250), the `record-dispatch-boundary` argparse `help=` strings (lines 3840–3890).
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
  — § Per-Dispatch Context-Load Attribution in full (lines 862–950), including the Format example block.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` line 448.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py`
  — `render_dispatch_boundaries_body` (lines 336–383) and `_dispatch_boundaries_has_present_phase`.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — `SECTION_SPEC`.
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
  — `_parse_dispatch_boundary_totals` and its `_BC_LEDGER_*` constants (lines 7187–7330).
- `test/plan-marshall/plan-retrospective/test_analyze_logs.py`
  — `TestDispatchBoundaryContextLoadColumns` in full (lines 710–980).
- `test/plan-marshall/manage-metrics/test_record_model_representability.py` (lines 440–500, 775–830).

Executed (not read):

- `uv run python -m pytest test/plan-marshall/plan-retrospective/test_analyze_logs.py -o addopts="" -q`
  → **110 passed**; `-k DispatchBoundary` → **14 passed**.
- `uv run python -m pytest test/plan-marshall/manage-metrics/test_record_model_representability.py -o addopts="" -q`
  → **17 passed**.
- A standalone driver that imports `analyze-logs.py` and calls `_parse_dispatch_boundary_file` on ten
  synthetic artifacts, printing the full row dict for each. Results below under D2.

**Mutation checks** (three, one file, `analyze-logs.py`; `git diff --quiet` returned 0 before each,
byte snapshot taken with `cp`, restored with `cp` back — never `git checkout`/`restore`/`stash`;
`git diff --quiet` returned 0 after every restore):

1. `provably_post_change = False` → `True` (re-creates the pre-fix defect) →
   `test_all_zero_no_fingerprint_row_reads_indeterminate` and
   `test_indeterminate_zero_coexists_with_unrecognised_cell` **FAILED**.
2. Removed the `provably_post_change = True` set on a nonzero cell (marks every zero indeterminate) →
   `test_nonzero_fingerprint_keeps_measured_zeros_measured` **FAILED**.
3. Made `row['indeterminate_columns']` conditional on non-emptiness (the empty-collapses-to-absent
   conflation) → `test_nonzero_fingerprint_keeps_measured_zeros_measured`,
   `test_unmeasured_token_fingerprint_keeps_measured_zeros_measured` and
   `test_indeterminate_columns_present_empty_on_legacy_row` **FAILED**.

None of the plan's guards is vacuous.

Supersession checks: `git log --oneline d5b2c4e3..HEAD -- <each touched path>` (six later commits),
`git log --oneline -S '<string>'` for `indeterminate cells alike`,
`def summarize_context_position_cost`, `or a column the row does not have`,
`were byte-identical on columns`, `test_measured_zero_context_load_stays_zero`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: establish the discriminator, or prove there is none | answer recorded, population published | Yes | Yes | Yes | Partial (population is non-numeric, unavoidably) | `report-01.md` § D0 verdict "there is NONE", re-derived by source read: `manage-metrics.py:3209-3215` writes a header with no schema/version field; `cmd_record_dispatch_boundary` writes `int(measured)` or the literal token only. No corpus reachable: `find .plan -name 'metrics-dispatch-boundaries-*.toon'` → **0 files** in this checkout too |
| D1 | If a discriminator exists: read provenance-dated | pre-change rows no longer read as measured zeros | N/A — precondition refuted by D0 | — | — | — | Correctly declared N/A; and ⛔ "never rewrite the corpus" honoured — the landed diff touches no `.plan/` path (`git show --stat -M d5b2c4e3`: 7 files, none under `.plan/`) |
| D2 | Fourth state `indeterminate`, emitted per row | fourth state exists and is emitted | Yes | Yes | Yes (3 mutations red) | Yes | `analyze-logs.py:1177-1225` `_parse_dispatch_boundary_file` — two-pass gate, `provably_post_change`, `zero_columns`, `row['indeterminate_columns']` always assigned. Executed: `…,0,0,0,0` → four indeterminate, no value keys; `…,9100,0,0,0` → `input_tokens=9100` + three measured `0`s; `…,unmeasured,0,0,0` → `unmeasured_columns=['input_tokens']` + three measured `0`s; `…,0,not-an-int,0,0` → three indeterminate + `unrecognised_columns=['output_tokens']`; legacy 5-col → four `unmeasured_columns`, `indeterminate_columns == []` |
| D3 | Consumer audit, derived not sampled | consumer set derived, each one's handling stated | Yes | Yes | Yes | Yes, for the landing-time tree | Consumer set re-derived by `grep -rn "dispatch_boundaries\|metrics-dispatch-boundaries"` over `marketplace/`, `.claude/`, `test/`. At `d5b2c4e3` exactly three: `compile-report.py:336` `render_dispatch_boundaries_body` (counts rows, sums `total_tokens`-family fields, then `json.dumps(fragment)` — reads **no** context-load column), `retro_sections.py:40` (registry row only), `.claude/.../audit.py` `_parse_dispatch_boundary_totals` (parallel re-reader, out of surface, recorded as residue) |
| D4 | Regression tests, red-first, both directions | both directions pass, each seen red first | Yes | Yes | Yes — non-vacuous | Yes | `test_analyze_logs.py:761` (direction 1 fix), `:806` and `:842` (direction-1 negative controls), `:872` (direction 2, present-but-empty), `:907` (mixed edge case). `-k DispatchBoundary` → 14 passed. Red-first re-established here by the three mutations above rather than taken on the report's word |

### D0 — population is published as a non-count, and that is the only available answer

`plan.md` requires "how many archived rows, how many datable, how many not". `report-01.md` publishes
"not countable from this clone" plus a *structural* population statement (datable-among-affected =
zero by construction). I confirmed the underlying fact rather than assuming it: `.plan/` exists in
this checkout but holds no dispatch-boundary ledger at all (`find /home/user/plan-marshall/.plan -name
'metrics-dispatch-boundaries-*.toon'` → 0). The numeric population is therefore not derivable from
git-tracked state by any run, and the plan's own Notes forbid going after `.plan/`. Recorded as an
honest non-count, not as a skipped obligation.

### D2 — the gate is sound, with one deliberate and stated conservatism

`provably_post_change` is set by an `unmeasured` token (`analyze-logs.py:1192`) or a nonzero
context-load cell (`:1205`). Ordering cannot bias the verdict: every literal `0` is deferred into
`zero_columns` and resolved only after the whole row has been scanned (`:1218-1222`). The
absent-column branch (`:1183-1187`) deliberately does **not** set the fingerprint, which is right — a
legacy short row proves nothing about the writer.

Two edge behaviours I executed and record as by-design rather than as defects: a genuine post-token
row whose four cells are *all* measured zeros carries no fingerprint and reads indeterminate (the
stated conservative direction — the standard says so in § *Provenance of a measured zero*); and a
negative integer counts as a nonzero fingerprint (`…,-5,0,0,0` → `input_tokens = -5`, siblings
measured). Neither is reachable from a well-formed writer.

### D3 — the claim still holds against today's tree, which has a consumer the audit could not have seen

`summarize_context_position_cost` (`analyze-logs.py:526`) *is* a consumer of
`cache_read_input_tokens` today, but it did not exist at landing:
`git log --oneline -S 'def summarize_context_position_cost'` → `89edc991` (#1260), later. Checked it
anyway: `:624` skips a row whose key is absent and counts it as a writer-side gap, never as a zero, so
the parser fix is not undone by it either. D3's absence-claim — the plan's flagged higher-risk half —
holds both at landing and now.

## Report accuracy

Re-derived every figure and symbol name the report states. **No contradiction found**, having checked:

- The D0 mechanism claims against `manage-metrics.py` (`cmd_record_dispatch_boundary`,
  `_DISPATCH_CONTEXT_LOAD_COLUMNS`, `UNMEASURED_COLUMN_TOKEN`) and `analyze-logs.py`
  (`_parse_dispatch_boundary_file`, `len(parts) < 5` floor at `:1139`) — all present and as described.
- The five-case parser trace in § Findings — reproduced exactly by executing the parser (see D2 row).
- The D3 consumer table — the three named consumers are the complete set at `d5b2c4e3`; each one's
  stated handling matches its code.
- F1/F2/F3 "fixed" — `SKILL.md:448` reads "four-way (measured / unmeasured / unrecognised /
  indeterminate)"; `data-format.md`'s subsection header reads "The unmeasured token, and the cell
  read"; `manage-metrics.py:136` names the reader's fourth state. All three still stand at HEAD.
- F4 "deferred → residue" — accurate at the time; now closed, see § Residue.
- PR number, branch name, and the "auto-merge armed / landing delegated" outcome — `d5b2c4e3` is a
  squash-merge of `#1255` with the `Co-authored-by: Claude` trailer.

Two figures are **imprecise rather than contradicted**, and are listed under *What could NOT be
verified*: the module-verify total (`16475 passed, 1 skipped`) and the local "120 passed" for "the
full reader + representability suites" — the file set has changed six commits since, and the two
suites carried 78 + 15 test defs at `d5b2c4e3` versus 109 + 17 today.

One claim is **accurate but narrower than a reader would take it**: the run says its verification
sub-agent's "beyond-diff sweep surfaced stale lock-step 'three-way' claims" and lists four. Re-running
that sweep at HEAD finds three further live sites the run did not touch — see G1. The report never
says the sweep was exhaustive, so this is an incomplete sweep, not a false statement.

## Out-of-scope compliance

Clean. The landed diff (`git show --stat -M d5b2c4e3`) is exactly seven paths:

| Path | Declared? |
|---|---|
| `doc/plans/…/420-….md` → `doc/plans/…/420-…/plan.md` (R100, 0 content change) | plan-directory lifecycle, contract Step 3 |
| `doc/plans/…/420-…/report-01.md` (new) | contract Step 9 |
| `…/plan-retrospective/scripts/analyze-logs.py` | Expected surface |
| `…/manage-metrics/standards/data-format.md` | Expected surface |
| `test/plan-marshall/plan-retrospective/test_analyze_logs.py` | Expected surface |
| `…/manage-metrics/scripts/manage-metrics.py` (comment only, no behaviour change) | lock-step restating surface named in `data-format.md` § Restating surfaces |
| `…/manage-metrics/SKILL.md` (one sentence) | same |

⛔ **"NOT the archived corpus"** — honoured; no `.plan/` path appears in the diff, and the writer change
is a comment. No undeclared collateral change.

## Residue carried forward

| Report residue item | Status in today's tree |
|---|---|
| `audit.py` `_parse_dispatch_boundary_totals` reads a fingerprint-free literal `0` as a measured zero (+ F4's "reads three ways" docstring cross-reference) | **CLOSED — superseded.** `d1c31533` (#1278, "gate an undatable ledger zero out of the measured totals") ported the same row-level provenance gate. `audit.py:7268` docstring now reads "each context-load cell reads FOUR ways" and documents THE PROVENANCE GATE; `_BC_LEDGER_UNMEASURABLE_FIELDS` scopes it to columns 6–9 |
| Adjacent: a denominator that states WHEN it was sampled but not WHAT it counted | **Still open**, and independently confirmed as live work: `85abeeb9` (#1293, "a token figure carries its population or it is not named 'actual'") addresses the same family on the metrics surface but is a different plan; no verdict offered here |
| Adjacent: a partiality verdict that cannot see a *stale-closed* phase | **Not verified** — no symbol named in the report to check against; recorded as declared-not-addressed |

One item the report does **not** list as residue but which it created: renaming
`test_measured_zero_context_load_stays_zero` left a dangling docstring cross-reference to it inside the
same test file (`git show d5b2c4e3 -- test/…/test_analyze_logs.py` deletes the def at old line 119
while `test_unmeasured_token_reads_as_absent_not_zero`'s docstring kept pointing at it). **Now closed**
— `88894aef` (#1258) re-pointed it at `test_nonzero_fingerprint_keeps_measured_zeros_measured`
(`test_analyze_logs.py:946`). Not an open gap, recorded because the run's own sweep missed it.

## What could NOT be verified

1. **The archived corpus and every claim resting on it.** No dispatch-boundary ledger exists in this
   checkout (`.plan/` present, `find … -name 'metrics-dispatch-boundaries-*.toon'` → 0). So: the plan's
   HYPOTHESIS "the four columns were zero on every pre-change row", D0's numeric population, and the
   blast-radius-is-total conclusion are all **not checkable from the tree** — neither confirmed nor
   refuted here.
2. **The empirical pre-fix confirmation** the plan itself flagged as reported-not-re-run. I confirmed
   the *mechanism* by source read and by mutation, which is the same route the run took; the original
   empirical observation against merged main remains unre-run.
3. **The build figures.** `./pw verify plan-marshall` → "16475 passed, 1 skipped" was not re-run —
   six later commits have moved the suite, so the number is not reproducible and its absence of
   reproduction is not evidence against it.
4. **The "120 passed locally" red-first figure.** The scope of "the full reader + representability
   suites" is not stated precisely enough to re-derive; today the two named files collect 110 + 17.
   Red-first was instead re-established directly, by the three mutations above.
5. **CI and reviewer-participation claims** (check-run states, `coderabbitai` rate-limit,
   "no actionable comments"). These live on the GitHub PR, not in the tree; not fetched.
