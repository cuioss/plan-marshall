# Gaps — 290-auditor-detector-integrity

All six deliverables plus the extra C4 fix are implemented at the sites the plan named, by the mechanisms it
asked for, and every one is covered by tests proved non-vacuous under mutation. What remains is seventeen
items: one documented-but-unimplemented precedence rule inside the new census (G1), one stale predicate
docstring (G2), one untested guard the code itself calls load-bearing (G3), two enumeration/scope statements
that are wrong on the tree (G4, G12), two declared-residue defects still open (G5, G7), the plan claim that
was never located (G6), four checks whose semantics this plan changed without bumping their era stamps
(G8-G11), and five stale or misattributed claims confined to the run report (G13-G17).

## G1 — Make `_examined_population` read `plans_in_corpus` first, as its docstring claims

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5488-5529`
  (`_PLANS_IN_CORPUS_RE`, `_examined_population`); emitters at `:5966`/`:5970` and `:8441`/`:8442`
- **Evidence:** the docstring states *"Precedence, strongest evidence first: 1. `plans_in_corpus` — the
  check's OWN statement of what it examined. Read first"*, but the implementation is one `re.search` over
  `^(?:plans_in_corpus|plans_in_series|plans_measured):\s*(\d+)$`, so the key appearing **first in the block
  text** wins. Both aliasing checks emit their alias first: `token-efficiency-trend` prints
  `plans_in_series` before `plans_in_corpus`, `lane-lever-effectiveness` prints `plans_measured` before it.
  Demonstrated in process — for a block carrying `plans_measured: 0` then `plans_in_corpus: 7`,
  `_examined_population(block, 12)` returns `0` and `_classify_zero` returns `starved`; with the two lines
  swapped it returns `7` and `disciplinary`.
- **Why it matters:** the census's whole job is refusing verdicts it cannot substantiate. Today the alias and
  the canonical key are numerically equal so nothing misreports, but the first check whose alias means
  something narrower or wider than `plans_in_corpus` silently flips its own zero class, and the docstring
  guarantees the opposite. The comment at `:8419` ("Published under the key the census reads") is already
  false for `lane-lever-effectiveness`, whose alias is what actually gets read.
- **Action:** iterate `_EXAMINED_POPULATION_KEYS` in order, searching a per-key pattern and returning the
  first key that matches, instead of a single alternation search. Keep the key set as-is.
- **Done when:** a test stages one block carrying two different `plans_*` population values in **both**
  orders and asserts `_examined_population` returns the `plans_in_corpus` value in both.
- **Effort:** S
- **Risk if fixed:** none behavioural today (the values coincide); the new test is the only new surface.

## G2 — Correct `check_input_integrity`'s docstring to the widened blind predicate

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:4419-4427`
  (`check_input_integrity` docstring), against the predicate at `:4482-4484`
- **Evidence:** the docstring says *"The bucket is `blind` exactly when the 5-execute phase recorded zero
  tokens — the load-bearing case"*. The shipped predicate is
  `execute_blind = (execute_absent or execute_recorded_zero) and not execute_marker_explained`, so it is
  wrong in both directions: an absent phase is blind too, and a marker-explained zero is not.
- **Why it matters:** this is the exact predicate whose vacuity the plan lists as a confirmed member (C4), and
  the docstring now restates the retired form directly above the corrected code. `checks/input-integrity.md`
  and the code comment at `:4471-4481` both carry the right rule, so a reader who consults the docstring gets
  the one wrong statement of three.
- **Action:** rewrite the sentence to name both routes into `blind` (recorded zero **or** absent section) and
  the `phases_missing_end_time` carve-out, matching `checks/input-integrity.md:67`.
- **Done when:** the docstring names the absent-phase route, and a grep for `"exactly when the 5-execute"`
  over the skill returns nothing.
- **Effort:** S
- **Risk if fixed:** none — comment-only.

## G3 — Pin `suspect_zero_census`'s unread-count guard with a test

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5613-5616`;
  `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_suspect_zero_census.py`
- **Evidence:** the code carries *"`.get(check)` — NOT `.get(check, 0)`. An unread count must reach
  `_classify_zero` as None so it is reported as such rather than classified as a measured zero."* Modelling
  precisely that defect in process (pre-filling every `CHECK_NAMES` key with `0` before the call) leaves all
  **33** census tests green. `_classify_zero`'s `None` contract is tested directly, and the real-sweep test
  asserts only that no check *is* `no_count` — an assertion the mutation preserves.
- **Why it matters:** this is the V3/W1 defect class (a false `disciplinary`, then a false `suspect`, both
  manufactured from a defaulted count) and the guard against its return has no regression test. A check that
  later stops publishing a readable count would be reported as a measured clean zero.
- **Action:** add a `suspect_zero_census` test that passes a `per_check_genuine` dict **missing** one registered
  check whose block carries no readable count, and assert that row's `zero_class == no_count` and
  `genuine_signal_count == ""`; add the mirror case where the dict carries `0` and assert `disciplinary`, so
  the two states are discriminated rather than one asserted alone.
- **Done when:** changing `per_check_genuine.get(check)` to `per_check_genuine.get(check, 0)` makes the new
  test fail.
- **Effort:** S
- **Risk if fixed:** none — test-only.

## G4 — Correct `_decision_line_shapes`'s scope clause about own-shape drop lines

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_decision_line_shapes.py:17-22`
- **Evidence:** the clause says gates rendering their own lines — naming `unresolved_ask_provider_drop`,
  `scope_gated_finalize`, `ceremony_finalize_selection` and the `*_inactive` pre-filter line — *"carry no
  `[STATUS]` tag and are matched individually by the reader's own per-mechanism patterns"*.
  `domain_seeded_step_unresolvable` (`manage-execution-manifest.py:2186-2190`) renders its own drop line
  **with** a `[STATUS]` tag and is matched by nothing; `canonical_verify_inactive` (`:2161-2165`) is a second
  unnamed own-shape drop line.
- **Why it matters:** the clause is the module's statement of its own boundary, which a future editor consults
  before adding a gate. It is a four-item enumeration of a set that is not four — the same defect shape this
  run corrected twice elsewhere (W8, Y7). Neither omission is harmful today, because both act on
  `phase_5.verification_steps`, which holds no `_PRUNABLE_PREDICATES` member — and that, not the tag, is the
  real reason they are outside scope.
- **Action:** restate the clause by property rather than by list: the module owns the `phase_6.steps`
  subtraction record; lines that drop from other lists, or that render their own shape, are matched
  individually. Name the live examples as examples, not as the set.
- **Done when:** the clause makes no claim about `[STATUS]` tags that `domain_seeded_step_unresolvable`
  falsifies, and does not present its examples as exhaustive.
- **Effort:** S
- **Risk if fixed:** none — comment-only.

## G5 — Make `frozen_manifest_stale` removals readable by the routing-decisions check

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** writer `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:3028-3034`;
  reader `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py:166-208`;
  documented at `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/routing-decision-verification.md:48`
- **Evidence:** the `reconcile` verb emits
  `(plan-marshall:manage-execution-manifest:reconcile) frozen_manifest_stale — dropped \`{step}\` from
  phase_6.steps: …` — no `[STATUS]` tag, and the step wrapped in backticks. The shared pattern requires the
  tag, and no per-mechanism pattern covers this line, so `resolve_removal_causes` returns no cause for the
  step. The run recorded this as W6 residue and fixed only the doc claim.
- **Why it matters:** a prunable step (`sonar-roundtrip`, `finalize-step-simplify`) removed by reconcile falls
  through to predicate re-evaluation and is reported as a `mis_prune` whenever the realized footprint touched
  production code — the precise false verdict D5 exists to end, reachable by a live path.
- **Action:** route the `frozen_manifest_stale` emission through `format_dropped_record` (dropping the
  backticks, since the reader's `\S+` capture and `_bare_step` expect a bare or prefixed step id), or add a
  per-mechanism pattern for the untagged reconcile shape. The formatter route is preferable — it closes the
  `frozen_manifest_backfill` sibling's shape drift too.
- **Done when:** a test stages a decision log containing the reconcile stale line and asserts
  `resolve_removal_causes` returns `{'sonar-roundtrip': 'frozen_manifest_stale'}`, and the counter-example
  paragraph in `routing-decision-verification.md:48` is retired.
- **Effort:** M
- **Risk if fixed:** changing the emitted line breaks any archived-log reader of the old shape; if the
  formatter route is taken, retain a legacy pattern for archived logs exactly as
  `posture_cutoff_legacy_aggregate` does.

## G6 — Settle C5: locate the warning that fires at every boundary, or refute it

- **Kind:** omission
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** the claim is `plan.md:76-78` and the claim-label row at `plan.md:171`; sites already cleared are
  `manage-execution-manifest.py:1603-1620` (`_lane_keep_decision` path) and `:1660-1694`
  (`_ceremony_prefilter_warnings`)
- **Evidence:** D1's *Done when* requires every claim to carry a verdict and a mode. C5 carries neither: the
  report records **NOT LOCATED**, and my independent re-derivation reached the same result — both composer
  warning families are conditional, so neither fires at 100%.
- **Why it matters:** the plan's premise is that a detector reporting a constant trains readers to ignore the
  channel it shares with real warnings. If the site exists it is still mis-training readers; if it does not,
  the claim should be struck so a later plan does not re-inherit it. An unsettled claim in a gate deliverable
  is the same "asserted, never checked" shape the plan exists to close.
- **Action:** retrieve the withheld proposal the plan says C5 was rescued from and take the site from it. If
  it cannot be retrieved, sweep every `WARNING`-level emission across `manage-execution-manifest`,
  `manage-metrics` and `plan-retrospective` for one whose guard is unconditional at a boundary, and record
  either the site or an explicit refutation.
- **Done when:** C5 carries a verdict (confirmed at a named `path:line`, or refuted with the sweep that
  covered it) and, if confirmed, a mode.
- **Effort:** M
- **Risk if fixed:** a warning removed or narrowed could hide a real signal — gate any change on a test that
  shows the warning still fires on the condition it names.

## G7 — Reconcile the `[LOCK]` timeline's log root, or teach dormation about it

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py:416-428`
  (`_resolve_lock_log_path`); `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5017-5040`
  (`dormate_global_logs`)
- **Evidence:** the lock timeline is written to `main_local_base.parent / 'logs'`, i.e. `.plan/logs/`, while
  every other global log lives in `.plan/local/logs/`. `dormate_global_logs` scans **only** `.plan/local/logs/`
  — `lock-2026-08-16.log` matches its `{prefix}-YYYY-MM-DD.log` grammar but is in the directory it never
  looks at.
- **Why it matters:** this is the residue the plan deliberately left to the lock skill, and it is wider than
  the report states. Beyond the audit scan (now fixed by scanning both roots), the lock timeline is never
  rotated out: it accumulates indefinitely, and every merge-window sweep re-reads the whole history.
- **Action:** in a `manage-locks` plan, either point `_resolve_lock_log_path` at `get_base_dir() / 'logs'` so
  the timeline joins the other global logs, or extend `dormate_global_logs` to scan both roots. Prefer the
  first: it collapses the split the auditor currently has to straddle.
- **Done when:** one root holds the `[LOCK]` timeline **and** dormation relocates past-date `lock-*.log`
  files, proved by a test that writes a past-date lock log through `log_lock_event` and asserts it moves.
- **Effort:** M
- **Risk if fixed:** moving the write path orphans lock logs already on developers' machines; the auditor's
  two-root scan must be kept until those age out.

## G8 — Bump `merge-window-accounting`'s era stamp to the boundary that changed it

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:454`
  (`"merge-window-accounting": "#877"`); contract at `:333-339`
- **Evidence:** `CHECK_ERA` is defined as *"the roadmap-era boundary as of which the check's computation is
  known accurate"* and rides every emitted block as `fixed_since`. Plan 290 (#1276) changed the check's scan
  roots and gave it an `unmeasured` state that withholds counts; the stamp still reads `#877`.
- **Why it matters:** a reader diffing `contended_plans` across runs sees one unchanged era spanning a
  scan-root change that turns structural zeroes into withheld counts. The file's own vocabulary shows #1260 —
  a non-roadmap PR — taking a bump for a smaller semantic change to `global-log-analysis`, so the convention
  is not roadmap-only in practice.
- **Action:** set the entry to `#1276` with the one-line rationale the neighbouring entries carry. If the
  convention is genuinely roadmap-only, say so at `:333-339` instead, so the next reader is not left to guess.
- **Done when:** the entry names a boundary at or after #1276, or the contract text scopes itself explicitly to
  roadmap plans.
- **Effort:** S
- **Risk if fixed:** `test_audit_check_era_model.py` reads `CHECK_ERA` for its expectations, so the bump is
  self-consistent; only tests pinning the literal `#877` would need updating.

## G9 — Bump `global-log-analysis`'s era stamp to the boundary that changed it

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:394`
  (`"global-log-analysis": "#1260"`)
- **Evidence:** rounds 3-5 of plan 290 gave this check the `unmeasured` contract, a `logs_readable` substrate
  probe (`:2928`) and a gated summary metric (`:9128-9132`). Its stamp still names #1260, the cost-rollup PR.
- **Why it matters:** the check's `genuine_signal_count` and `error_count` now have a state in which they are
  absent rather than zero; a cross-run diff under an unchanged stamp presents pre- and post-contract runs as
  commensurable.
- **Action:** bump to `#1276` with the one-line rationale, or scope the convention explicitly (see G8).
- **Done when:** the entry names a boundary at or after #1276, or the contract text is scoped.
- **Effort:** S
- **Risk if fixed:** as G8.

## G10 — Bump `quality-chain`'s era stamp to the boundary that changed it

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:428`
  (`"quality-chain": "plan-10"`)
- **Evidence:** D4 changed `_qc_finding_genuine` so structurally-pending rows no longer count as genuine, and
  added `pending_actionable` / `pending_structural` columns. The stamp still names `plan-10`.
- **Why it matters:** `finding_genuine_signal_count` is persisted as a `genuine__quality-chain` summary metric
  and feeds the retire-on-quiet streak and the census. Its meaning changed at #1276; a streak that spans the
  boundary mixes two definitions of "genuine".
- **Action:** bump to `#1276` with the one-line rationale, or scope the convention explicitly (see G8).
- **Done when:** the entry names a boundary at or after #1276, or the contract text is scoped.
- **Effort:** S
- **Risk if fixed:** as G8.

## G11 — Bump `input-integrity`'s era stamp to the boundary that changed it

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:414`
  (`"input-integrity": "#812"`)
- **Evidence:** the C4 fix widened `data_confidence: blind` to cover an absent `5-execute` section
  (`:4482-4484`), so `data_confidence_blind` and `blind_plan_ids` count a strictly larger population than
  before #1276. The stamp still names #812, the marker-model boundary.
- **Why it matters:** a rise in `data_confidence_blind` across the boundary reads as a corpus regression when
  it is a definition change — and this check's output is what other checks cite when dismissing a floored row.
- **Action:** bump to `#1276` with the one-line rationale, or scope the convention explicitly (see G8).
- **Done when:** the entry names a boundary at or after #1276, or the contract text is scoped.
- **Effort:** S
- **Risk if fixed:** as G8.

## G12 — State the `unmeasured` case on SKILL.md's global-log-analysis row

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/SKILL.md:163` (the `Global-log analysis` check
  table row), against `:173` (the merge-window row)
- **Evidence:** the merge-window row ends *"Reports `status: unmeasured` with NO counts — never a zero
  contention count — when no `[LOCK]` lifecycle log exists to read."* The global-log row, which received the
  identical contract in rounds 4-5 and whose own `checks/global-log-analysis.md:135-159` documents it in full,
  says nothing about it.
- **Why it matters:** the SKILL.md table is the index a reader consults to know what each check can report.
  One of the two checks carrying the new state advertises it and the other does not — the run's own
  "corrected at n−1 of n sites" pattern, landing in the shipped surface.
- **Action:** add the equivalent sentence to the `Global-log analysis` row, pointing at the `logs_readable`
  probe as the discriminator.
- **Done when:** both rows state the `unmeasured` state and its trigger.
- **Effort:** S
- **Risk if fixed:** none — doc-only.

## G13 — Correct the D4 test count in `report-01.md`

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/290-auditor-detector-integrity/report-01.md` § D4,
  *"**Verification** | 12 tests"*
- **Evidence:** `test_audit_check_quality_chain_structural_pending.py` holds **17** test functions at
  `2d5da71`; the report's own V1 disposition records "Five cases added", superseding the figure inside the
  same document.
- **Why it matters:** the report's § Build gate sets the standard explicitly — *"a figure that predates the
  commits it reports as landed is exactly the moving-figure defect this run kept finding elsewhere"* — and
  applies it to one figure only.
- **Action:** restate as 17, or as "12 at the deliverable commit, 17 after the verification rounds".
- **Done when:** the stated count matches the module at the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — Correct the D5 test count in `report-01.md`

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § D5, *"41 tests in that module"*
- **Evidence:** `test/plan-marshall/plan-retrospective/test_check_routing_decisions.py` collects **51** tests
  (46 `def test_` functions, some parametrised) at `2d5da71`; X4 and Y4 added to it after the deliverable
  commit.
- **Why it matters:** as G13.
- **Action:** restate the count, or attribute it to the deliverable commit explicitly.
- **Done when:** the stated count matches the module at the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G15 — Correct the D6 test count in `report-01.md`

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § D6, *"15 tests"*
- **Evidence:** `test_audit_suspect_zero_census.py` holds **33** test functions at `2d5da71`; the census
  absorbed additions in every verification round from V3 through R1.
- **Why it matters:** as G13, and most misleading here — the figure understates by more than half the
  coverage of the plan's cross-cutting deliverable.
- **Action:** restate the count, or attribute it to the deliverable commit explicitly.
- **Done when:** the stated count matches the module at the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G16 — Correct the changed-test-module count in `report-01.md` § Build gate

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § Build gate, *"(5 Python files: … plus 9 test modules)"*
- **Evidence:** `git show --name-only 7951ada -- '*.py'` lists 5 production modules and **10** test modules
  (`test_audit_check_cross_check_synthesis_couplings_d_f`, `…_era_model`, `…_global_log_analysis_emit`,
  `…_input_integrity_absent_execute`, `…_merge_window_accounting`, `…_quality_chain_structural_pending`,
  `…_recipe_provenance`, `…_registration_wiring`, `test_audit_suspect_zero_census`,
  `test_check_routing_decisions`).
- **Why it matters:** Z6 recorded a stale test-module count as fixed; the count in the merged report is still
  off by one, so the disposition is unsupported — the R1 shape (a record the artifacts contradict).
- **Action:** restate as 10.
- **Done when:** the figure matches `git show --name-only` on the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G17 — Correct the D4 partition-source attribution in `report-01.md`

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md` § D4, *"Mirrors the fixed actionable-vs-knowledge split already shipped at
  `plan-marshall/scripts/_invariants.py` — the blocking gate's own rule, and the 'proven pattern' the plan
  pointed to"*
- **Evidence:** the plan (`plan.md:112-114`) points at *"the same partition shape already shipped elsewhere in
  this codebase for **omitted-versus-dropped sections**"*, which is
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:511-616`
  (`sections_omitted` / `sections_dropped`). `_invariants.py` is a different artifact, and its real path is
  `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`.
- **Why it matters:** the delivered partition satisfies the deliverable either way, but the report asserts an
  identification it did not check — the failure mode this plan exists to close, in the report's own prose. It
  also leaves the pattern the plan actually cited unexamined, so nobody confirmed the two shapes agree.
- **Action:** name `compile-report.py`'s omitted/dropped partition as the pattern the plan pointed to, state
  that `_invariants.py` is the source of the **type set** (a separate, exact mirror), and give
  `_invariants.py`'s full path.
- **Done when:** the sentence distinguishes the shape source from the type-set source and both paths resolve.
- **Effort:** S
- **Risk if fixed:** none.
