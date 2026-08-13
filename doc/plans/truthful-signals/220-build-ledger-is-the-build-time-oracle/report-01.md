# Run report — 220-build-ledger-is-the-build-time-oracle (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/build-time-oracle-ledger-hxatuk (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (working contract — first action).
- `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-script-architecture` (always).
- `pm-dev-python:python-core`, `pm-dev-python:pytest-testing` (Python production + tests).

Loaded by `Read` on the bundle path (plugin notation not required).

## STOP CONDITION — SATISFIED

The plan's stop condition (checked first): *does the ledger carry a structured
duration for every build system, plus a mandatory plan identifier on ledger rows?*

**Yes.** Verified in code, not just docs:
`marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py`
`build_record(...)` (line 135) constructs a `kind=build` row carrying:

- `duration_seconds: float | None` — the wrapper's measured build duration (the structured field).
- `plan_id: str` — **required, never null**; a plan-less build is stamped `NO_PLAN`
  (docstring line 167, module docstring line 21). This is the mandatory plan identifier.
- `status: str` over `BUILD_STATUSES` = `{success, error, timeout, killed, unknown}` (line 62/74/81).
- `command: str | None` — the **wrapper-resolved** command (`./pw verify`, and by construction any
  build tool's resolved command), which is what distinguishes build systems.

The `kind=build` writer fires at the executor dispatch boundary for **any** `build-*` skill's
`run` verb (SKILL.md "Build-class-ness is a conjunction: the notation must sit under a `build-*`
skill AND the dispatched subcommand must be the build-executing verb (`run`)"), not just
`build-pyproject`. So the ledger already spans every build system. Producer work has landed;
this consumer plan may proceed.

## D0 — GATE findings (mutates nothing)

### Existing facet inventory (the derivation to RE-BASE, not duplicate)

`sequence-and-build-minimality` (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
`_sequence_build_minimality_plan` line 3514) derives build facts from
`logs/script-execution.log`'s `(N.NNs)` fragments. **Population: `build-pyproject:pyproject_build run`
calls ONLY** — `_sbm_is_build(notation, sub)` (line 3461) `return notation.endswith(
"build-pyproject:pyproject_build") and sub == "run"`. It computes: per-build duration-band
classification (`minimal` <120s / `scoped` 120–400s / `heavy` >400s, `_sbm_classify_build`),
`total_build_seconds`, `max_build_seconds`, per-phase `b=` build counts, and the `build_churn` /
`non_minimal_build` / `docs_only_build` flags.

Per D0's mandate ("**Do not add a check that duplicates a facet already computed — fold instead**"),
the re-base and both new facets **fold into this existing check** — no new check is added, so the
skill's stated check count stays **twenty-four** (D4 reconciliation is a verification, not an edit).

### The two blindnesses in the current derivation (named, to be closed)

1. **Single build system.** `_sbm_is_build` matches only `build-pyproject`; Maven / Gradle / npm
   builds are invisible. (Closed by reading `kind=build` ledger rows, which span every build system.)
2. **Early-phase builds never reach the plan-scoped log**, so they are invisible regardless of tool.
   (Closed by the ledger, which is written at the dispatch boundary for every phase.)

⇒ Today's build totals are undercounts of unknown size. D1 quantifies the delta.

### The wall-clock denominator (D2a)

Plan wall-clock = **sum of per-phase `duration_seconds`** from `work/metrics.toon`
(`PhaseMetrics.duration_seconds`, `parse_metrics_toon` line 877).

**Denominator reliability — the hole it inherits.** `metrics.toon` has an **absent-file branch**:
`parse_metrics_toon` returns `[]` when absent, and `check_metrics` reports `incomplete_recording:
true` (line 1646). A ratio built on it inherits that hole. **Resolution: when plan wall-clock is
absent or zero, the build-share facet is WITHHELD (rendered `n/a`), never computed as a false
number.** This is the same best-effort-degrade posture the metrics check already documents.

### Impossible-values precedent (for D2's invariant)

`check_metrics` already flags `agent_duration_seconds > duration_seconds + 1.0` per phase (worked >
wall, line 1699). D2's invariant — *build time cannot exceed plan wall-clock* — follows this exact
shape: `total_build_seconds > plan_wall_clock + tolerance` is a **recording defect** flag.

### Suspect-zero rule (the 411s / `duration_seconds = 0` defect)

A ledger build with `duration_seconds` of `0` or `None` is **SUSPECT**, never data. It is counted
in a separate `suspect`/`unknown` bucket and is **NOT summed into `total_build_seconds` and NOT
averaged in**. `_sbm_classify_build(0)` already returns `unknown`; the re-base extends that so a
zero/None duration contributes to no summed total or share. Demonstrated by a fixture feeding a zero
alongside a real duration (D4).

### Ledger access + plan-id attribution design

The audit reads the **single** ledger at `repo_root/.plan/work/change-ledger.jsonl` **once** (in
`run_checks`, which holds `repo_root`), and indexes `kind=build` rows by **bare** `plan_id`.
Archived plan dirs are named `{YYYY-MM-DD}-{plan_id}` (`manage-status/_cmd_lifecycle.py:490`
`archive_name = f'{date_prefix}-{args.plan_id}'`), while ledger rows carry the bare `{plan_id}`
(executor `_ledger_plan_id`). Attribution therefore strips a leading `^\d{4}-\d{2}-\d{2}-` from the
archived dir name; `--include-active` plans have no date prefix and match as-is. A plan with no
ledger rows degrades to zero/withheld (best-effort), exactly as the log-derived path degrades on
absent logs.

### Shipping-predicate exclusion (HYPOTHESIS resolved)

`sequence-and-build-minimality` is a `DELIVERY_COST_CHECKS` member — it runs over the SHIPPING
partition. The new facets fold into the **same** check, so they inherit the same partition. This is
correct, not silent inheritance: build time and pass/fail ratio are cost-per-delivery facets, so
they belong on the shipping partition just as the existing build-minimality signal does.

### D3 surface — D0 DECISION

D0 (this run is the authority — its verdict normally lives under git-ignored `.plan/`, absent here)
names the D3 surface: the **plan-retrospective report** (`quality-verification-report.md`),
specifically its **`plan_efficiency` aspect** — computed in
`marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` and rendered
per `references/plan-efficiency.md` + `references/report-structure.md` (Section 7 "Plan Efficiency",
whose `totals` block already carries `duration_seconds` and a per-phase breakdown).

Decisive evidence (a focused research sub-agent gathered the corpus; the decision is D0's):

1. The plan's **Expected surface** names **only** `plan-retrospective/**` for D3 ("only if D0 names
   it"). `manage-metrics` / `metrics.md` / any finalize artifact appears **nowhere** in the plan —
   if the author meant the always-on finalize metrics report, they would have listed it.
2. The retrospective's own reference docs repeatedly call `quality-verification-report.md` "**the
   final report**" (e.g. `references/log-analysis.md`, `references/artifact-consistency.md`); the
   operator's phrase "final report" maps here, not to the "final **metrics** report".
3. `plan-retrospective` is the **per-plan mirror** of the cross-plan
   `audit-archived-plan-retrospectives` this plan re-bases — same family, consistent home for the
   build-time facet.

The claim-label hypothesis ("The 'final report' surface is the retrospective report **rather than**
a distinct finalize artifact") therefore resolves to **the retrospective report**. Runner-up
(`metrics.md` via `manage-metrics`) is rejected: not in the Expected surface, and "final report" ≠
"final metrics report".

**Consequence:** D3 is a marketplace-bundle change (`analyze-logs.py` is `.py` → build gate fires;
bundle change → reviewed as code; a local `/sync-plugin-cache` is owed but a cloud run neither
performs nor owes it — recorded here). `analyze-logs.py` runs via the executor, so it imports
`_ledger_core` (unlike standalone `audit.py`); the two consumer reads are necessarily separate.

## Deliverables

_(updated as the run proceeds)_

- **D0** — **done** (the sections above). Facet inventory + wall-clock denominator + suspect-zero
  rule + ledger-access design + D3-surface decision recorded; nothing mutated.
- **D1** — **done.** `_sequence_build_minimality_plan` re-based onto the change-ledger
  (`_load_build_ledger_index`): build count, per-build duration, duration-band class, and the
  per-phase build attribution now come from the ledger's `duration_seconds` for **every build system
  and every phase**. Both blindnesses named in the check doc (§ "Build time comes from the
  change-ledger") and quantified: the block reports `corpus_build_seconds` (ledger) vs
  `corpus_build_seconds_log_derived` (old log baseline) and their `corpus_build_seconds_delta`, over
  the ledger-bearing population, with `plans_without_ledger` naming plans whose build time is
  unavailable (absent is not zero). Commit: audit re-base.
- **D2** — **done.** (a) `build_share` = ledger build time / wall-clock (sum of per-phase
  `metrics.toon` durations), **withheld (`n/a`) when metrics absent**. (b) pass/error/timeout/killed
  status ratio from the ledger `status` field, with **`killed` visibly separate** in both the per-row
  `killed` column and the `corpus_build_killed` line. Invariant `build_exceeds_wallclock` fires on a
  violating fixture; suspect-zero rule counts a zero/absent duration in `build_unknown` +
  `suspect_build_duration` and never sums it. Commit: audit re-base.
- **D3** — **done.** `analyze-logs.py` gains `summarize_build_ledger`, which reads the change-ledger
  (`_ledger_core.read_entries`), filters `kind=build` by the plan's bare `plan_id` (date-prefix
  stripped for archived mode), and emits a `build_time` block — `total_build_seconds` (valid `> 0`
  durations only, suspect-zero applied), `build_count`, `suspect_count`, and the
  pass/error/timeout/`killed`-separate ratio — for **every build system and every phase**. The
  `plan_efficiency` aspect (`references/plan-efficiency.md`) now carries `total_build_seconds` in its
  `totals`, **read** from that block (not re-derived), with the suspect-zero-floor and killed-separate
  rules documented; `log-analysis.md` documents the block; `report-structure.md` §7 names it. So a
  plan's total build time appears on **its own reporting surface** (the retrospective report), the
  surface D0 named — not only the cross-plan audit. Tests: `TestBuildTimeFromLedger` in
  `test_analyze_logs.py` (sum, suspect-zero, killed-separate, non-pyproject, absent-is-not-zero,
  cross-plan non-attribution). Commit: D3 plan-retrospective. **A local `/sync-plugin-cache` is owed
  for this bundle change but a cloud run neither performs nor owes it** (§ cloud-plan-lane).
- **D4 (audit side)** — **done.** New tests in `test_audit_checks.py`
  (`TestSequenceBuildMinimalityLedgerFacets`): (a) all-four-status ratio with killed separate; (b)
  build-exceeds-wall-clock flagged (+ negative control); (c) a non-pyproject (Maven) build in the
  totals; (d) the wall-clock denominator derivation asserted non-empty; plus suspect-zero,
  withheld-share, delta, and date-prefixed attribution. Existing sbm tests migrated to the ledger.
  Each new test's red-pre-fix state demonstrated against HEAD (see Findings). Check docs +
  SKILL.md Surfaces cell reconciled; the stated check count stays **twenty-four** (folded, not
  added — verified `len(CHECK_NAMES) == 24`). `CHECK_ERA["sequence-and-build-minimality"]` bumped to
  the `PR-PENDING` sentinel (test mirror in `test_audit.py` updated in lock-step). ⚠ **The
  `project:finalize-step-era-stamp-fill` step does NOT fire in the standalone `doc/plans/` lane**, so
  the sentinel is resolved by running `era_stamp_fill.py` **manually** after create-pr (rewrites both
  `audit.py` and `test_audit.py` in lock-step), committed and pushed **before** the merge gate so it
  rides this PR and never lands on `main` as `PR-PENDING`. D4 doc reconciliation for D3's surface
  lands with D3.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (audit.py, analyze-logs.py, tests),
so the gate takes its full path.

- Per-commit `./pw quality-gate` (both commits): **clean** — mypy "Success: no issues found in 398
  source files", ruff "All checks passed!", "SPDX-header check passed", plugin-doctor marketplace-wide
  COMPLETE.
- Step 5 full `./pw verify plan-marshall`: **SUCCESS** — all three sub-steps green: quality-gate
  (mypy production 278, ruff, SPDX), **test-compile (mypy over the whole `test/plan-marshall` tree,
  588 files — no issues)**, module-tests **`16457 passed, 1 skipped in 362s`**. `=== verify: SUCCESS ===`.

## Findings

- **Red-pre-fix demonstration (D4 "seen red first").** Because the implementation was already in
  place, each new D4 test's pre-fix red state was demonstrated by loading the committed-at-HEAD
  `audit.py` and showing the symbols and row fields the tests depend on are absent:
  `_load_build_ledger_index` / `_ledger_plan_key` / `_sbm_ledger_duration` do not exist pre-fix;
  the pre-fix `_sequence_build_minimality_plan(inputs)` takes ONE positional arg (the tests pass a
  ledger index → `TypeError`); and the pre-fix row dict carries none of `has_ledger`,
  `build_success`/`error`/`timeout`/`killed`/`unknown`, `wall_clock_seconds`, `build_share`,
  `log_build_seconds` (→ `KeyError`). So every D4 assertion fails against pre-fix code.
- **Own-code mypy finding, fixed.** The quality gate caught a type collision: the ledger loop's
  duration variable reused the name `dur` already bound as `float` by the earlier call-timeline loop,
  so assigning `float | None` was rejected. Renamed to `ledger_dur`. Gate then clean.

### Pre-PR verification sub-agent (Step 6) — findings + dispositions

The independent sub-agent returned **PASS** (it executed both consumer sites against synthetic ledger
rows — 10 audit scenarios + 3 retrospective scenarios green — cross-checked the producer schema, and
swept both skills for stale references). Every claim label and every D0–D4 requirement was confirmed
met in code, not merely claimed; out-of-scope respected (no producer touched).

- **Finding 1 (minor, dead field + inaccurate doc) — FIXED.** `build_status_unknown` was computed
  per-plan but emitted nowhere, and the check doc falsely called it "a corpus-only tally", so when
  unknown-status builds existed `pass+error+timeout+killed < builds` with no accounting — itself a
  small truthfulness gap. Fixed by actually emitting it: `corpus` gains `status_unknown`, the block
  gains a `corpus_build_status_unknown` line, the doc now states `pass+error+timeout+killed+
  status_unknown == corpus_builds`, and a new test
  (`test_status_unknown_reconciles_corpus_build_count`) locks the reconciliation in.
- **Observation (red-first not diff-re-verifiable) — accepted, no action.** The new tests are
  structurally red pre-fix (signature/row-key/`build_time`-block absence); demonstrated against HEAD
  (see above). A sound structural red.
- **Observation (PR-PENDING won't auto-resolve in the lane) — accepted, report corrected.** The
  finalize step does not fire here; the sentinel is resolved by running `era_stamp_fill.py` manually
  after create-pr (see D4 above). Report wording corrected from "automatic".
- **Observation (`plan-retrospective/SKILL.md:131` narrow) — rejected with reason.** Line 131 is
  Step 2.5's token-accumulator-reconciliation concern, accurately scoped to per-phase *token totals*
  from `metrics.md`. Build time flows through a different data path — the `log_analysis` fragment's
  `build_time` block — documented in `plan-efficiency.md`'s Inputs. Adding build_time to line 131
  would be off-topic, not more accurate.

## Out-of-scope items recorded (not fixed — per plan)

- **Wrapper internal-ceiling disagreement** (a `module-tests` build killed at 411s against a promised
  441s envelope): a build-wrapper-surface defect, explicitly out of scope. This plan's obligation was
  to stop *trusting* the resulting duration — met by the suspect-zero rule (a `duration_seconds = 0`
  is flagged, never averaged in) and the `build_exceeds_wallclock` invariant.
- **Notify the sibling epic** that measures our own runs — the audit corpus is what they read — when
  this lands. Recorded here for the operator/orchestrator; a cloud run has no channel to another epic.

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
