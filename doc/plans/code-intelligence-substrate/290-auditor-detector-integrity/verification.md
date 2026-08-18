# Verification — 290-auditor-detector-integrity

**Audited:** `plan.md`, `report-01.md` (the plan directory holds no other file)
**Tree state:** `2d5da71` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

Every deliverable is implemented, at the site the plan named, by the mechanism the plan asked for, and
every one is covered by tests that were proved non-vacuous by mutation. The gaps are one unimplemented
documented precedence rule inside the census, one stale predicate docstring, one untested guard the code
itself flags as load-bearing, four un-bumped era stamps, two declared-residue items still open, and a
handful of stale counts in the run report.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Gate: verify each claim at its site, classify into a mode, settle the reporting contract, re-derive the other removal-cause patterns | 6 claims settled with verdict + mode; C5 "NOT LOCATED"; C3b re-derived, C3c newly surfaced; contract = `unmeasured`, never `0` | Every settled claim reproduces first-party (see per-claim evidence below). C5 carries no verdict and no mode. The contract is implemented in two checks and documented | **PARTIAL** |
| D2 | Read the field live data carries; correct the equivalence comment | `collect_inputs` reads `('plan_source', 'recipe_key')`, mirroring `_read_recipe_source`; comment replaced | `audit.py:1258` reads both in that precedence; `_manifest_decide.py:333` is byte-for-byte the same tuple; comment `audit.py:1233-1257` names both producers | **CONFIRMED** |
| D3 | Measure contention or say `unmeasured`; re-point the tests at the production emitter; decide the split | Scans both roots; `status: unmeasured` with no counts; tests drive `_locks_core.log_lock_event`; emission left to the lock skill | `audit.py:8115` scans both roots; `audit.py:8228-8252` withholds all counts; `test_audit_check_merge_window_accounting.py:23,50` drives the real emitter; `_locks_core.py` untouched by the diff | **CONFIRMED** |
| D4 | Exclude structural pendings; state what would make the count zero | `pending` splits into `pending_actionable` / `pending_structural`; both published; per-plan column | `audit.py:3441-3480`, `3768-3780`, `6326-6332`; containment holds by construction (the bucket is a parameter) | **CONFIRMED** |
| D5 | Branch on the recorded removal cause; shared formatter both sides import | New `_decision_line_shapes`; reader matches gate-agnostically | `_decision_line_shapes.py:44-86`; writer `manage-execution-manifest.py:505-535,565-590`; reader `check-routing-decisions.py:166,258-289`; round-trip verified in-process | **CONFIRMED** |
| D6 | Class guard: zero-positive detectors surfaced as suspect; structural vs disciplinary distinguished | New `suspect-zero-census` block, five zero classes, reporting only | `audit.py:5576-5686`; a live full sweep emits 24 rows, `suspect_count: 21`, classes `structural`/`starved`/`disciplinary`/`fired` | **CONFIRMED** |
| C4 | (extra) Absent `5-execute` is blind, not partial | Severity inversion corrected; marker carve-out preserved | `audit.py:4482-4484`; mutation-confirmed non-vacuous | **CONFIRMED** |

## Per-deliverable detail

### D1 — the verification gate

- **Required (plan):** *"each claim carries a verdict and a mode, and the reporting contract is decided"*,
  plus an explicit re-derivation of the OTHER removal-cause patterns against the live emitter.
- **Claimed (report):** C1/C3/C4/C6 confirmed, C2 confirmed as a defect but refuted as to cause, C3b
  re-derived clean, C3c newly surfaced, C5 **not located**.
- **Found — each claim re-derived first-party, not read out of the report:**
  - **C1** (`recipe_key` never read): the pre-fix state is no longer observable, but its *producer* premise is.
    `phase-1-init/SKILL.md:541-546` (auto-route) and `:569` (operator selection) persist
    `status.metadata.recipe_key` and write no `plan_source`; `:625` (Step 5c-lesson) writes both. So Row 2 was
    unreachable for the two legs the fix names. **Confirmed, mode A.**
  - **C2** (marker with zero production emitters): a literal sweep for `merge:acquired` across the tree returns
    `report-01.md` plus exactly three test files —
    `test_audit_check_merge_window_accounting.py`, `test_locks_core.py`, `test_manage_locks_merge_lock.py`.
    Production interpolates: `_locks_core.py:464` emits `f'[LOCK] ({lock}:{event}) {lock_id}'`, called from ten
    sites in `merge_lock.py` / `build_queue.py`. **The report's refutation of the cause is correct**, and the
    path mismatch is real: `_locks_core.py:427-428` writes `main_local_base.parent / 'logs'`, i.e. `.plan/logs/`.
  - **C3/C3b/C3c** (removal-cause patterns): verified by executing the writer and the reader together —
    `format_dropped_record` output for `lane_resolution`, `decision_matrix`, `commit_push_disabled` and
    `pre_push_quality_gate_inactive` all match `dropped_record_pattern()` and yield the gate as the cause.
    `decision_matrix` is emitted at `manage-execution-manifest.py:2495` and is recognised.
  - **C4** (guard whose precondition is its own subject): the corrected predicate is at `audit.py:4482-4484`,
    and the inversion it removes is described at `audit.py:4471-4481`.
  - **C6** (pending count that cannot reach zero): `add_finding` seeds `pending`, `_qc_resolution`
    (`audit.py:3545-3568`) buckets `none`/empty/unrecognised to `pending`; the split is now in place.
  - **C5** (a warning firing at every boundary): I re-derived independently and also failed to locate it. The
    composer's two warning families are conditional — `_lane_keep_decision` (`manage-execution-manifest.py:1616`)
    fires only on an `off` override hitting an immune floor class, and `_ceremony_prefilter_warnings`
    (`:1660-1694`) skips whenever the lane would have dropped the step anyway or the override is `off`.
    **UNVERIFIABLE — no site located; the claim carries no verdict and no mode.**
- **Checks run:** literal content sweeps; first-party read of `phase-1-init/SKILL.md`; an in-process
  writer→reader round trip of the shared line shape; reads of both composer warning sites.
- **Verdict:** **PARTIAL** — five of six plan claims plus the re-derivation are settled with a verdict and a
  mode, the reporting contract is settled and implemented, but C5 is left unsettled. Reporting it as unlocated
  rather than guessing is the right call and is exactly what the plan's own subject matter demands; it still
  leaves the gate incomplete against its literal *Done when*.

### D2 — read the field live data actually carries

- **Required (plan):** read the field live data carries so the routing row is reachable, **and** correct the
  comment asserting the equivalence.
- **Claimed (report):** both fields read in the composer's precedence; comment replaced; `_read_recipe_source`'s
  own docstring corrected in lock-step.
- **Found:** `audit.py:1258-1262` — `for provenance_field in ("plan_source", "recipe_key")`, first non-blank
  wins. `_manifest_decide.py:333` — `for field in ('plan_source', 'recipe_key')`. Identical set, identical
  order. The replacement comment (`audit.py:1233-1257`) names Step 5c-recipe-match's two legs as the gap and
  Step 5c-LESSON as the path that was always reachable; both statements check out against
  `phase-1-init/SKILL.md`. The resolver docstring (`_manifest_decide.py:305-311`) now says the audit reads the
  SAME two fields in the SAME precedence.
- **Checks run:** 7/7 tests green; mutation (`collect_inputs` reduced to a `plan_source`-only read) fails
  exactly 2 — `test_recipe_key_metadata_field_populates_recipe_key` and
  `test_row_2_recipe_fires_for_a_recipe_key_routed_plan` — with the five controls still green, matching the
  report's red-first claim exactly.
- **Verdict:** **CONFIRMED.**

### D3 — measure contention, or say it is unmeasured

- **Required (plan):** scan for a marker the logs actually contain **or** report `unmeasured` with a reason;
  the two states must be distinguishable in the output; the tests must be re-pointed at the production
  emitter; the emission half must be *decided*, not absorbed.
- **Claimed (report):** both roots scanned; `unmeasured` withholds counts; split decided in favour of leaving
  emission to the lock skill; distinguishability asserted by two named tests.
- **Found:** `audit.py:8115` — `_LOCK_LOG_ROOTS = ((".plan", "logs"), (".plan", "local", "logs"))`;
  `_merge_window_log_files` (`:8118-8140`) returns `(files, substrate_present)` where `substrate_present` is a
  `lock-*.log` probe, and `cross_merge_window_accounting` (`:8214-8217`) sets
  `measured = substrate_present or bool(rows)` — evidence beats the filename convention.
  `emit_merge_window_accounting_block` (`:8240-8252`) emits `status: unmeasured`, a reason, and the scanned
  roots, and **no counts at all**. The summary metric is gated (`audit.py:9126-9132`) and the synthesis
  coupling renders `contended_plans=unmeasured` (`audit.py:8833`). `_locks_core.py` is absent from the plan's
  diff, so the emission half really was left alone.
- **Checks run:** 12/12 tests green. Two mutations, both red: restricting `_LOCK_LOG_ROOTS` to
  `.plan/local/logs` fails `test_lock_log_present_with_no_merge_events_is_a_measured_zero` and
  `test_production_emitter_output_is_in_scan_range`; forcing `measured=True` fails
  `test_merge_window_no_logs_is_unmeasured_not_zero` and `test_unmeasured_block_withholds_counts_and_says_why`.
  The suite drives the real emitter (`import _locks_core`; `log_lock_event`; and
  `test_locks_core_module_is_the_production_one` pins the module path), so the "suite synthesises its own
  marker" shape is closed.
- **Verdict:** **CONFIRMED.**

### D4 — exclude structural pendings from the genuine count

- **Required (plan):** partition so pending-by-construction entries are excluded or reported in their own
  bucket; state explicitly what would make each count zero.
- **Claimed (report):** `pending_actionable` / `pending_structural`, both published, plus a per-plan column;
  the actionable half alone counts as genuine.
- **Found:** `_QC_STRUCTURAL_PENDING_TYPES` (`audit.py:3441`) = `{tip, insight, best-practice, improvement}`,
  which is exactly the knowledge set `_invariants.py:1215-1220` names as never counted by the blocking gate —
  the mirror claim holds, and the one-directional caveat (`audit.py:3427-3439`) is accurate.
  `_qc_structural_pending` (`:3451`) takes the computed bucket as a parameter and returns `False` unless
  `resolution == "pending"`, so `corpus_structural_pending <= corpus_pending` holds by construction
  (`:3768-3780`). `_qc_finding_genuine` (`:6249-6274`) excludes structural rows on the pending leg only and
  keeps the auto-review leg. The published note (`:6329-6332`) states the narrower, true claim (promotion or an
  explicit disposition, never defect-fixing work), matching `checks/quality-chain.md:66,75-79`.
- **Checks run:** 17/17 tests green. Mutation A (re-read `resolution` instead of taking the bucket — the V1
  defect) fails 3, including `test_actionable_pending_never_goes_negative`. Mutation B (genuine predicate
  ignores `structural_pending`) fails 2. Both red.
- **Verdict:** **CONFIRMED.** One attribution quibble, recorded under Report accuracy: the plan pointed at the
  *omitted-versus-dropped sections* partition (`compile-report.py:511-616`), not at `_invariants.py`.

### D5 — branch on the recorded removal cause

- **Required (plan):** re-evaluate a predicate only when the recorded removal was predicate-driven; report
  configuration-driven removals as intentional; preferred remedy is a shared formatter both sides import.
- **Claimed (report):** `_decision_line_shapes` renders and parses; gate-agnostic reader; four docs corrected.
- **Found:** `_decision_line_shapes.py:44-59` (`format_dropped_record`) and `:62-86`
  (`dropped_record_pattern`) build both directions from the same three segment constants. The writer routes
  `_log_dropped_records` (`manage-execution-manifest.py:534`), `_log_commit_push_omitted` (`:549`) and
  `_log_pre_push_quality_gate_omitted` (`:586`) through it; the reader imports it
  (`check-routing-decisions.py:58,166`) and `resolve_removal_causes` (`:279-282`) takes the captured gate name
  as the cause. Four individually-shaped mechanisms keep their own patterns (`:168-208`), including the
  deliberately-retained `posture_cutoff_legacy_aggregate` for archived logs.
- **Checks run:** 51/51 tests green. I executed writer→reader for four live gates (all match, correct gate and
  step captured). Three mutations, all red: substituting the retired `posture_cutoff` regex fails 9; deleting
  the legacy pattern fails 2 (including the list-repr coupling test); re-enumerating the gate set fails 4,
  including `test_unknown_future_gate_in_the_shared_shape_is_still_a_cause` and the `decision_matrix` case.
- **Verdict:** **CONFIRMED.**

### D6 — the class guard

- **Required (plan):** surface a detector with zero positives across a full corpus as *suspect*; distinguish a
  structural zero from a disciplinary one; reporting only, never blocking.
- **Claimed (report):** `suspect-zero-census` with `structural` / `starved` / `disciplinary` / `no_count` /
  `no_block` / `fired`; shares one streak derivation with `retire-on-quiet`; documented honest limit.
- **Found:** `suspect_zero_census` (`audit.py:5576-5643`) emits one row per `CHECK_NAMES` member including
  checks that emitted no block; `_classify_zero` (`:5531-5574`) ranks `fired` → `structural` → `no_count` →
  `starved` → `disciplinary`; the block (`:5645-5686`) carries per-class counts and a note, and proposes,
  removes and blocks nothing. `quiet_streaks` (`:5382`) is the single derivation both blocks read. SKILL.md
  `:211-253` documents every class, the honest limit, and the mode-E self-exclusion.
- **Checks run:** 33/33 tests green. A real end-to-end sweep (`run_checks` over a one-plan corpus in a temp
  root) emits `checks_registered: 24`, `suspect_count: 21`, `structural_count: 2` (the two `unmeasured`
  checks), `starved_count: 12`, `disciplinary_count: 7`, `no_count_count: 0` — so the block works outside its
  fixtures and the "no registered check is `no_count` today" claim reproduces. Two mutations red: blinding
  `_PLANS_IN_CORPUS_RE` fails 3 (including the whole-census property test); reordering `_classify_zero` so
  `no_count` outranks `structural` fails 3. One mutation **survived** — see Test adequacy, G3.
- **Verdict:** **CONFIRMED**, with the census's own blind spot (it is not in `CHECK_NAMES`) documented rather
  than closed, as the report says.

### C4 — the guard whose precondition is its own subject

- **Required:** not a numbered deliverable; the plan lists it among the confirmed members.
- **Found:** `audit.py:4482-4484` —
  `execute_blind = (execute_absent or execute_recorded_zero) and not execute_marker_explained`. The
  marker-explained carve-out is preserved (`:4514-4520`), and `checks/input-integrity.md:67,73-83` documents
  the widened rule and the ordering argument.
- **Checks run:** 5/5 green; mutation (absent phase downgraded to `partial`) fails 2, including
  `test_absence_never_grades_milder_than_a_recorded_zero`.
- **Verdict:** **CONFIRMED** — with a stale docstring on the enclosing function (G2).

## Correctness review

I read the shipped implementation of all six deliverables plus C4 end to end: `collect_inputs`, the
merge-window scan and its emitter, the quality-chain partition and its genuine predicate, the census and its
population reader, `check_input_integrity`, `_decision_line_shapes`, and the routing check's cause resolver.
Three defects and one latent hazard:

1. **The census's documented population precedence is not implemented.**
   `_examined_population` (`audit.py:5493-5529`) documents *"Precedence, strongest evidence first: 1.
   `plans_in_corpus` — the check's OWN statement … Read first"*, but the implementation is a single
   `re.search` over an alternation (`_PLANS_IN_CORPUS_RE`, `:5488-5490`), so the key that appears **first in
   the block text** wins, not the canonical one. Both live aliasing checks emit their alias first —
   `token-efficiency-trend` emits `plans_in_series` at `:5966` before `plans_in_corpus` at `:5970`, and
   `lane-lever-effectiveness` emits `plans_measured` at `:8441` before `plans_in_corpus` at `:8442`. Today the
   pairs are numerically identical, so nothing misreports; the moment one diverges the census silently reads
   the wrong denominator. Demonstrated: with `plans_measured: 0` before `plans_in_corpus: 7` the classifier
   returns `starved`; with the two lines swapped it returns `disciplinary`. Opposite verdicts from emission
   order alone, in the instrument built to stop unsubstantiated verdicts. → **G1**.
2. **`check_input_integrity`'s docstring states the retired predicate.** `audit.py:4425-4427` still says the
   bucket is *"`blind` exactly when the 5-execute phase recorded zero tokens"* — the exact predicate C4
   replaced, and the one whose vacuity the plan lists as a confirmed member. The code and
   `checks/input-integrity.md` both carry the corrected rule; this one site was missed. → **G2**.
3. **`_decision_line_shapes`'s scope clause is wrong.** `_decision_line_shapes.py:17-22` says the gates that
   render their own lines *"carry no `[STATUS]` tag"*. `domain_seeded_step_unresolvable`
   (`manage-execution-manifest.py:2186-2190`) renders its own drop line **with** a `[STATUS]` tag, and
   `canonical_verify_inactive` (`:2161-2165`) is another own-shape drop line the clause does not name. Neither
   is harmful today (both act on `phase_5.verification_steps`, which holds no `_PRUNABLE_PREDICATES` member),
   but the clause is what a future editor consults. → **G4**.
4. **`frozen_manifest_stale` removals are still invisible to the reader** (the run's own declared residue).
   `manage-execution-manifest.py:3028-3034` emits an untagged `reconcile` line with the step in backticks, so
   neither the shared shape nor any per-mechanism pattern matches it; a prunable step dropped that way still
   falls through to predicate re-evaluation and produces the false `mis_prune` D5 exists to end. → **G5**.

No fail-open branch, unguarded `None`, off-by-one or stale-surface read was found in the new code. Specific
things I checked and found sound: `measured = substrate_present or bool(rows)` (evidence outranks the filename
probe); `logs_readable = substrate_present and total_lines > 0` (`audit.py:2928` — a read probe, not an
existence probe); the `_qc_structural_pending` containment argument; `_classify_zero`'s `None`-vs-`0`
discipline; `genuine = per_check_genuine.get(check)` with no default; the `ceremony_finalize_selection`
pattern's refusal to read the `added … to` direction as a removal; and `_LOCK_WAITING_RE` against
`format_log_entry`'s `  key: value` field rendering (`plan_logging.py:138-140`).

## Test adequacy

| Deliverable | Test module | Count (re-derived) | Non-vacuity evidence |
|---|---|---|---|
| D2 | `test_audit_check_recipe_provenance.py` | 7 | `plan_source`-only read → 2 red, 5 controls green |
| D3 | `test_audit_check_merge_window_accounting.py` | 12 | scan-root narrowed → 2 red; `measured` forced true → 2 red |
| D4 | `test_audit_check_quality_chain_structural_pending.py` | 17 | bucket re-read → 3 red; genuine predicate widened → 2 red |
| D5 | `test_check_routing_decisions.py` | 51 collected | retired regex → 9 red; legacy pattern dropped → 2 red; gate list re-enumerated → 4 red |
| D6 | `test_audit_suspect_zero_census.py` | 33 | population regex blinded → 3 red; class precedence inverted → 3 red |
| C4 | `test_audit_check_input_integrity_absent_execute.py` | 5 | absent phase → `partial` → 2 red |

Whole-suite state at HEAD: `test/plan-marshall/audit-archived-plan-retrospectives/` → **640 passed**;
`test/plan-marshall/manage-execution-manifest/` + `test/plan-marshall/plan-retrospective/` → **1833 passed**.

**Mutation method.** Other audit agents were concurrently editing the same production files in this working
tree — I caught one such edit overwriting mine mid-run and discarded the byte snapshot I had taken, because
it had captured *their* mutation rather than the pristine file. Every mutation reported here was therefore
applied **in process**, by a pytest plugin that patches the loaded module after collection; no production file
was written at any point. `git status --porcelain` for `.claude/` is empty.

**One vacuous guard found.** `suspect_zero_census` carries a comment calling its dictionary lookup
load-bearing — *"`.get(check)` — NOT `.get(check, 0)`. An unread count must reach `_classify_zero` as None"*
(`audit.py:5613-5616`). Modelling exactly that defect (defaulting every unread count to `0` before the call)
leaves **all 33 census tests green**. `_classify_zero`'s own `None` contract is tested directly
(`test_an_unread_count_is_no_count_not_disciplinary`), and the real-sweep test asserts only the *absence* of
`no_count` — which the mutation preserves. So the census-level guard against the V3/W1 defect class is
unpinned. → **G3**.

## Report accuracy

The report is unusually accurate: every substantive mechanism claim I checked reproduces, including the two
that reverse the plan's own brief (the lock marker's producer exists; `decision_matrix` was unenumerated).
The following claims are stale or wrong against the tree now.

- *"plus 9 test modules"* (§ Build gate). The merged diff carries **10** test modules
  (`git show --name-only 7951ada -- '*.py'` → 5 production + 10 test). → **G16**.
- *"**Verification** | 12 tests"* (§ D4). The module holds **17** — the report's own V1 row records the five
  added cases, so the figure was superseded inside the same document. → **G13**.
- *"41 tests in that module"* (§ D5). `test_check_routing_decisions.py` collects **51** (46 `def test_`
  functions, some parametrised). → **G14**.
- *"15 tests"* (§ D6). `test_audit_suspect_zero_census.py` holds **33**. → **G15**.
- *"Mirrors the fixed actionable-vs-knowledge split already shipped at `plan-marshall/scripts/_invariants.py`
  … and the 'proven pattern' the plan pointed to"* (§ D4). The plan pointed at *"the same partition shape
  already shipped elsewhere in this codebase for **omitted-versus-dropped sections**"*, which is
  `plan-retrospective/scripts/compile-report.py:511-616` (`sections_omitted` / `sections_dropped`), a different
  artifact. The delivered partition is equivalent in kind, so the deliverable stands; the attribution does
  not. (The cited path is also abbreviated — the file is at
  `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`.) → **G17**.
- *"22 commits"* and the six per-deliverable commit SHAs (`f5761fb`, `751338a`, `cfbe68b`, `482fde1`,
  `f3f55fb`, `04b7b0f`) are **UNVERIFIABLE** from this clone: the PR squash-merged as `7951ada` and none of
  the branch commits is reachable (`git cat-file -t` fails for all six). Not recorded as a defect.
- The `./pw verify` figure (20,545 passed / 14 skipped / 392 s) is **UNVERIFIABLE** here and is now
  necessarily stale in any case: `d1c3153` (#1278) landed a further change to `audit.py` after this plan.

Claims I checked that held exactly: the `merge:acquired` sweep result (three test files, zero production
emitters); the production emitter's interpolated line shape; the `.plan/logs/` vs `.plan/local/logs/` path
split; `decision_matrix` dropping both prunable steps via `_ANALYSIS_MINIMUM` (`_manifest_decide.py:27`); the
`\w+`-safety of the four ceremony gate names (`manage-execution-manifest.py:1017-1020`); the `_invariants.py`
knowledge-set mirror; `resolve --resolution` being the real flag (`manage-findings.py:360`, `allow_abbrev=False`);
`DELIVERY_COST_CHECKS` holding nine members; 24 checks and 24 check docs; the era test pinning `status: \S+`
rather than `success`; and the V12 self-exclusion being documented in SKILL.md rather than silently left.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **F8 / C5** — the unlocated "warning that fires at every boundary" | **Open** | I re-derived independently: both composer warning families are conditional (`manage-execution-manifest.py:1616`, `:1660-1694`); no 100%-firing warning located. No verdict, no mode. → G6 |
| **F2's emission half** — `[LOCK]` timeline written to `.plan/logs/` while every other global log lives in `.plan/local/logs/` | **Open**, and wider than reported | `_locks_core.py:427-428` unchanged. Additionally `dormate_global_logs` (`audit.py:5017-5040`) scans **only** `.plan/local/logs/`, so `lock-*.log` files match the rotation grammar but are never dormated — the timeline grows without bound and the merge-window scan reads an ever-growing set. → G7 |
| **F16 — plan 310 had not run** | **Closed** | `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd/` is now an executed plan directory; its `report-01.md` records PR #1286, dated after #1276. The rebase-onto-changed-`audit.py` risk it named was absorbed by that run |
| **Merge-gate condition 2 — two comment surfaces returned HTTP 404; merge overridden** | **Closed, no work outstanding** | Both surfaces read cleanly now: `coderabbitai[bot]` posted *"Review failed — An error occurred during the review process"* (no findings) and `cuioss-review-bot[bot]` posted *"No major issues detected"*; `get_reviews` returns only sourcery's size-limit refusal. Nothing was left unhandled. The run's refusal to record these as `silent` was correct |
| **W6 — `frozen_manifest_stale` can still make a mechanism invisible** | **Open** | `manage-execution-manifest.py:3028-3034`; documented at `references/routing-decision-verification.md:48`. → G5 |
| **V12 — the census does not census itself** | **Open by design, documented** | `CHECK_NAMES` (`audit.py:231-259`) contains neither `suspect-zero-census` nor `retire-on-quiet`; SKILL.md:230-236 records it as mode E standing unresolved |

## Out-of-scope and collateral

All four exclusions were respected:

- **Working-directory resolution** — the merged diff of `audit.py` contains no `cwd` / report-path /
  walk-up hunk (`git show 7951ada -- …/audit.py | grep '^[+-].*cwd'` → empty).
- **Termination-cause vocabulary** — untouched.
- **Bookkeeping-prefix classification / manifest cross-check rule** — `_footprint_classification.py` and the
  manifest cross-check are absent from the diff.
- **Lock-marker EMISSION** — no `manage-locks` file appears in the diff; the split is stated in the code
  (`audit.py:8109-8113`) rather than only in the report.

Collateral the run declared and I confirmed present: `_manifest_decide.py` (docstring), `manage-execution-manifest.py`
(shared-formatter routing), five check docs, SKILL.md, and `references/routing-decision-verification.md`.
Nothing was changed outside what the report declares. Two obligations the run neither performed nor recorded:

- The `CHECK_ERA` boundary stamps of the four checks whose semantics it altered were not bumped
  (**G8-G11**) — `merge-window-accounting` still reads `#877`, `global-log-analysis` `#1260`,
  `quality-chain` `plan-10`, `input-integrity` `#812` (`audit.py:394,414,428,454`) — even though the same
  file's vocabulary shows a comparable non-roadmap PR (`#1260`) taking a bump for a smaller semantic change,
  and the stamp is defined as *"the boundary as of which the check's computation is known accurate"*
  (`audit.py:333-339`).
- SKILL.md's check table gained the `unmeasured` state on the merge-window row (`SKILL.md:173`) but not on the
  `Global-log analysis` row (`:163`), which received the identical contract in rounds 4-5 (**G12**) — the
  run's own "fix applied at n−1 of n sites" pattern, surviving into the shipped table.

## Method and coverage

- Read `plan.md` and all 368 lines of `report-01.md` first, then verified against the tree rather than
  against the report's own narrative.
- Located every symbol by name (the plan warned line numbers had already moved); all citations above are
  re-derived at `2d5da71`.
- Ran targeted suites with `uv run python -m pytest <file> -o addopts=""` and the two whole directories the
  diff touches. Did **not** run `./pw verify` (out of scope per the brief).
- Mutation-tested six production surfaces, in process, via a pytest plugin patching the loaded module after
  collection. This substitution for file-level mutation was forced by concurrent agents editing the same files;
  it is strictly safer and equally decisive, since the patched objects are the ones under test.
- Exercised the shipped code outside its fixtures twice: the writer→reader round trip for the shared decision
  line, and a full 24-check `run_checks` sweep over a temp corpus to read the census block as it really emits.
- Read the GitHub PR surfaces the run could not read at merge time, which is what let the merge-gate residue be
  closed rather than carried.
- **Not checked:** the `./pw verify` totals; the machine-local audit corpus (the plan forbids looking for it);
  the six branch commit SHAs (unreachable after squash-merge); C5's existence anywhere outside the composer and
  `audit.py`, which is an open-ended search the plan itself could not bound.
