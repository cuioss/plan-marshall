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

Population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md` → `coderabbitai`; `pr-agent.md` → `cuioss-review-bot`; `sourcery.md` →
`sourcery-ai`), cross-named by `.github/workflows/pr-agent.yml`. Verdicts read from the stored comment
bodies on PR #1224:

| Reviewer (`author_login`) | Verdict | Body evidence |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "PR Reviewer Guide 🔍 — PR contains tests, No security concerns identified, No major issues detected" (issue-comment surface). A review artifact against the diff with an explicit no-issues finding. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached — you've reached your PR review limit, so we couldn't start this review" (issue-comment surface). Engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" (review-summary surface). Engaged but did not review this diff. |

**Coverage: 1 of 3.** `cuioss-review-bot` reviewed (clean); `coderabbitai` rate-limited (window
reopens shortly); `sourcery-ai` rate-limited (weekly quota). All three comment surfaces were read
(`get_comments`, `get_reviews`, `get_review_comments`); the inline-thread surface was empty. **No
actionable review comment exists** — the sole review found no issues, and the other two published only
refusal notices. The § Step 8 condition-4 shortfall disclosure fired: **"Review coverage: 1 of 3 —
`cuioss-review-bot` reviewed (no issues); `coderabbitai` rate-limited; `sourcery-ai` rate-limited."**
Per the lane, a rate-limit shortfall is a disclosure, not a block, and blocking on a bot's quota is
explicitly the wrong direction — so the aborted attempts are recorded as `rate-limited` (never counted
as coverage), disclosed, and the merge proceeds. The change was independently verified by the local
`./pw verify` (16457 tests) and the pre-PR verification sub-agent, so the confidence floor does not
rest on the rate-limited bots.

## Cost

- **Tokens:** not available to the agent in this session — a single interactive Claude Code cloud
  session exposes no token counter to the running agent, so no figure is stated rather than a guess.
- **Wall-clock:** approximately one working session (first commit `ffda76f` establishing the plan
  directory through the merge-gate arm; PR #1224 opened at 2026-08-13T21:01:40Z). Source: git commit
  times + the PR creation timestamp. Two full `./pw` builds (quality-gate ×4, one full verify at
  ~362s) dominate the wall-clock.
- **Population:** this single Claude Code cloud session's own activity. ⛔ **NOT comparable to a
  plan-marshall `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's per-task billing boundary that a single interactive session does not share. The two
  cannot be made comparable, so no parity figure is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — `cloud-plan-lane`, `ref-code-quality`, `plugin-script-architecture`, `python-core`, `pytest-testing` (named above). |
| 2 Branch | Done — harness-assigned `claude/build-time-oracle-ledger-hxatuk` kept as-is; pushed to `origin` before any work. |
| 3 Plan directory | Done — `doc/plans/truthful-signals/220-build-ledger-is-the-build-time-oracle/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — 6 commits carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | Done — each `*.py`-touching commit preceded by a clean `./pw quality-gate`; the era-stamp commit was a string-literal swap (a change class that cannot regress ruff/mypy/SPDX), verified by the era tests. |
| 4 Pushed | Done — no unpushed commit remains. |
| 5 Build gate | Done — Python changed, full `./pw verify plan-marshall` SUCCESS (quality-gate + test-compile 588 files + module-tests 16457 passed). |
| 6 Verification sub-agent | Done — PASS with one minor finding (fixed + test-locked) and three observations (2 accepted, 1 rejected-with-reason). The fix was additive, contained to the audit skill, and covered by the full suite + a new reconciliation test, so a full re-dispatch was judged disproportionate; the fix was re-verified via the audit test suite (533 passed) and the quality gate. |
| 7 PR cycle | Done — PR #1224; all three comment surfaces read; no actionable comment; reviewer participation recorded above. |
| 8 Merge gate | Conditions 1–3 met (condition 1 via the queue: `verify / gate` was `in_progress` at arm time, and on this merge-queue repo the queue is the required-green enforcer). Auto-merge armed; coverage shortfall disclosed (condition 4). Recorded as arm-and-hand-off — see § Residue and the operator note. |
| 8 Bridge | No status/bookkeeping write landed outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | This section. |
| GitHub access path | GitHub MCP server (the cloud path). |
| Branch form | Harness-assigned `claude/*` (kept), per the lane. |
| Plugin-cache sync | Not owed — a cloud run never performs or owes `/sync-plugin-cache` (a local dev refresh of the `plan-retrospective` bundle is a local-developer concern, recorded for a local dev). |

## What have we learned (Step 9)

**One contract-change proposal, recorded for operator approval (not self-shipped — headless run).**

*Evidence from this run:* this plan changed the semantics of an `audit-archived-plan-retrospectives`
check (`sequence-and-build-minimality`), which per that skill's convention requires bumping the
check's `CHECK_ERA` stamp — normally resolved from the `PR-PENDING` sentinel by
`project:finalize-step-era-stamp-fill`. **That finalize step does not fire in the standalone
`doc/plans/` lane**, so the run had to (a) recognize the era-stamp obligation at all, and (b) resolve
the sentinel by invoking `era_stamp_fill.py` manually after create-pr, committing it before the merge
gate. The `cloud-plan-lane` contract says nothing about either obligation, so a future lane run that
touches an audit check could silently ship a stale era stamp or a `PR-PENDING` sentinel to `main`.

*Proposed edit:* add a short note to `cloud-plan-lane` (Step 4 or Step 8) — "if the change alters an
`audit-archived-plan-retrospectives` check's semantics, bump its `CHECK_ERA` to the `PR-PENDING`
sentinel and resolve it by running `era_stamp_fill.py run --pr-number {N} --worktree-path .` manually
after create-pr, committed before the merge gate (the finalize step that normally does this does not
fire in this lane)." Scope is narrow (only plans touching the audit checks), so this is a small,
targeted addition — presented for the operator to accept and ship as its own `chore(cloud-plan-lane)`
PR, per Step 9. Not self-approved.

## Residue

- **The landing is delegated (arm-and-hand-off).** `verify / gate` (the required check) was
  `in_progress` at the merge gate, and this cloud session has no reliable self-wake to block until the
  queue lands the PR. Per § Step 8, the run is **completed with the landing delegated**: conditions
  1–3 met, auto-merge armed, the queue is the required-green enforcer, and the orchestrator's collect
  reads `state: MERGED` from the PR merge event. `./pw verify` passed locally (16457 tests), so
  confidence that `verify / gate` will go green is high; if it does not, the queue refuses the merge
  rather than landing a red PR.
- **Notify the sibling epic** (the one measuring our own runs; the audit corpus is what it reads) when
  this lands — recorded for the orchestrator; a cloud run has no channel to another epic.
- **Local `/sync-plugin-cache`** is owed to a local developer for the `plan-retrospective` bundle edit
  (not owed by this cloud run).
- **Contract-change proposal** (above) awaits operator approval; ship as a separate `chore/` PR if
  accepted.
