envelope_version=1
sender_type=plan
sender_id=archived-plan-audit-26-08-08
epic=truthful-signals
kind=finding
created=2026-08-08T19:20:00Z

## Archived-plan retrospective audit — full analysis (58-plan corpus, 24 checks)

Emitted by an ad-hoc `/audit-archived-plan-retrospectives` run at coverage cell
`inherit/inherit` (behaviour-preserving: all 24 checks, full corpus). The corpus was
dormated to `.plan/temp/dormated-plans/` immediately after this audit, so the figures
below are the last reading of it.

---

### 1. Corpus shape and the confidence floor

- **58 archived plans** scanned. The eight **delivery-cost** checks run over the
  **53-plan shipping partition**; 5 plans are excluded on missing delivery evidence
  (no PR record, no real footprint) and every one is labelled `unrecorded` — none
  carried a reason string:
  `lessons-corpus-is-written-and-never-read`, `wrong-store-guard-refuses-project-local-lessons`,
  `compose-time-subtractions-drop-steps`, `correct-review-scores-as-maximally-wrong`,
  `org-empty-review-guard-too-broad`.
- `input-integrity`: **`data_confidence_blind: 0`, `partial: 0`, `fully-recorded: 58`,
  `blind_plan_ids` empty, `genuine_signal_count: 0`.**

**This is the load-bearing fact for reading everything else.** No plan is metrics-blind,
so no downstream row is a floor and the no-false-healthy rule gags no conclusion in this
report. That is a genuine change: the prior recorded run had `input-integrity_partial: 2`
and `genuine: 2`. One row carries `has_findings: false`
(`wrong-store-guard-refuses-project-local-lessons`) — an absent findings store, not a
blind metric; the check still classes it `fully-recorded`.

---

### 2. The three genuine signals that were filed as lessons

#### 2.1 Argparse / contract drift — the corpus's largest waste class

`2026-08-08-19-001` (`plan-marshall:tools-script-executor`, anti-pattern)

Three independent views of one class:

| View | Figure |
|------|--------|
| `quality-verification-report` unfiled signatures | **463**, across **48 of 58** plans |
| `global-log-analysis` errors | **178** (`ERROR=160`, `WARNING=71` over 74,712 lines) |
| `recurring-pattern-detector` argparse signature | **0** at threshold 3 |

The signature shapes are `Argparse rejection in {notation} call`,
`Invented flag drift in {notation} call`, `Missing required flag in {notation} call`,
`Invented subcommand drift in {notation}`, `Script-internal error in {notation}`.

Recurring source notations (≥3 plans): `manage-solution-outline` (~30 plans — the single
most persistent), `manage-findings`, `manage-status`, `manage-references`, `manage-files`,
`manage-logging`, `manage-architecture:architecture`, `manage-change-ledger`,
`manage-execution-manifest`, `tools-integration-ci:ci`, `workflow-integration-git:git-workflow`,
`workflow-integration-github:github_pr`, `phase-6-finalize:ci_verify`,
`automatic-review:review_completeness`.

**Filed as ONE source-keyed lesson**, per the `argparse_signature_cluster` caveat — not
one per facet and not one per consuming plan. A source-keyed record covers every later
plan that trips the same rejection; a plan-keyed one covers nothing.

Note the coupling itself did **not** fire (`argparse_signatures: 0`), because the
recurring-pattern detector saw no argparse signature at threshold — the 463 live entirely
in the quality-verification view. That divergence is itself worth the epic's attention:
**the detector and the report disagree about whether this class exists.**

`quality-verification-report_unfiled` moved **237 → 463** since the prior run.

#### 2.2 The cost-reducing lane levers are effectively unadopted

`2026-08-08-19-002` (`plan-marshall:phase-1-init`, improvement)

| Class | Target | Over |
|-------|--------|------|
| surgical | 1,200,000 | 1 / 1 |
| single_module | 1,500,000 | 34 / 34 |
| multi_module | 2,500,000 | 14 / 14 |

**49 of 53 `checkpoint_over`.** The four `informational` rows are the four `broad`-scope
plans, which are `unclassed` — no target exists to miss. **Not one classed plan came in
under target.**

Lever engagement over the same 53: `recipe_routed: 0`, `minimal_posture_chosen: 0`,
`light_lane_fires: 3`, `estimated_avoided_tokens: 0`, `posture_not_taken: 1`.

This is not 49 individually-overspending plans; it is one fact about the routing layer.
A lever that fires **zero** times in 53 plans is either unreachable or unarmed, and
neither is fixed by moving the number. The one plan that did take the light lane at
surgical scope (`manage-lessons-mixes-local-time-and-utc`) still came in at 2,198,948
against a 1,200,000 target, so lane selection alone does not close the gap.

Corroborated by `surgical_overpay` (fired): `orchestrator-inbox-pickup`
(4,262,740 tok / 8 files) and `post-merge-review-findings-untriaged-in-main`
(3,797,668 tok / 3 files) are simultaneously `checkpoint_over` and
`big_spend_tiny_footprint` — the clearest lane-lever misses in the corpus.

#### 2.3 In-task builds recur as runtime build churn

`2026-08-08-19-003` (`plan-marshall:phase-4-plan`, anti-pattern)

Both facets confirmed, as `redundant_build_churn` requires before filing:

- **Static** — `task-graph-redundancy` `in_task_build` on **46 of 58**. Worst:
  `lane-router-scale-blind-false-negative` (9), `mandatory-plan-id-build-results-ledger` (9),
  `post-run-steps-ordered-before-their-evidence` (9), `exploration-share-is-unmeasured` (6).
- **Runtime** — `sequence-and-build-minimality`: `corpus_builds: 2024`,
  `build_churn: 1712`, `heavy: 189` (>400 s), `corpus_build_seconds: 285,860` (≈79.4 h),
  `minimal: 1189`, `scoped: 646`. `build_churn` fires on **all 53** shipping plans;
  `phase_reentry(3-outline)` on 48.

The coupling names **43 plans** carrying both.

**Framed strictly as wall-clock, not tokens.** Per `churn_explains_walltime` (fired,
27 plans in the build-wall-clock upper half): builds are cheap in tokens by design —
a ~100-token TOON return while the LLM suspends on the synchronous call. The visible
token over-spend on those plans is generation volume (`long_session`) plus
execution-context fragmentation. **Do not read this lesson as a token-reduction lever.**

---

### 3. Billing composition — the number that reframes the roadmap

Every figure with its own population and label; **no figure is `floor`**, so none needs
"at least X" phrasing.

| Figure | Value | Population | Label |
|--------|-------|:----------:|-------|
| `billing_weighted_total_reconstructed` | 3,836,506,668 weighted tokens | 53 | measured |
| `cache_read` share | **76.2%** | 53 | measured |
| `cache_creation` share | **22.6%** | 53 | measured |
| `output` share | **1.1%** | 53 | measured |
| byte share exploration | **79.4%** | 33 | measured |
| byte share execute | 18.3% | 33 | measured |
| byte share orchestration | 1.6% | 33 | measured |
| byte share work | **0.7%** | 33 | measured |

Under-counts, kept **separately named** as the check requires:
`unabsorbed_loop_back_plans: 5`, `omitted_row_plans: 0`, `reconciled_plans: 23`,
`plans_excluded_no_counters: 0`.

**The consequence for the epic.** `lane-lever-effectiveness` scores plans on
`total_tokens = input + output`, and `token-economics` states the caveat explicitly
("excludes cache_read/cache_creation — a generation-volume proxy, not total traffic").
Those checkpoint targets therefore score the **1.1%** end of the bill. Retuning the
targets without changing what they measure cannot move cost. This is the single most
consequential finding in the audit.

The byte composition says the same thing from the other side: **79.4% of payload bytes
are exploration**, against 0.7% work.

---

### 4. Per-check adjudication — the remaining 21 checks

**Clean, with the verdict grounded:**

- `dispatch-topology` — 58/58 `leaf_dispatch: 0`, `genuine_signal_count: 0`. The
  leaf/dispatch-topology invariant **holds**; `dispatch_topology_reentry` correctly did
  not fire (`topo_violation_plans: 0` against `reentry_plans: 48`). Moved **24 → 0**
  since the prior run.
- `merge-window-accounting` — 0 rows, `plans_with_merge_events: 0`, `total_blocked: 0`.
  No merge contention in the corpus; `merge_window_ci_rerun` correctly did not fire.
- `pr-merge-velocity` — 53 rows, **0 flagged**. Max 8.0 h
  (`executor-version-split-resolvers`); 22 plans at 0.0 h.
- `input-integrity` — covered in §1.
- `retire-on-quiet` — 4 runs recorded, threshold 3, **0 proposals**. No check has gone
  quiet enough to warrant a removal review.

**Genuine rows adjudicated as one repeated fact, not N findings:**

- `execution-context-manifest` — `genuine_signal_count: 58` is **one** fact repeated 58
  times: `phase_6` built-in step `finalize-step-preference-emitter` resolves to no
  ownership class (orchestrator/leaf/hybrid) — roster drift from the canonical finalize
  steps. Underneath it sit **5 real rule drifts** (`expected=default, actual=tests_only`
  on `daemon-audit-logs-…`, `ceremony-prefilter-dropped-the-security-audit`,
  `exploration-share-is-unmeasured`, `post-merge-review-findings-untriaged-in-main`;
  `expected=default, actual=recipe` on `wrong-store-guard-refuses-project-local-lessons`).
  `name_drift_count: 0`. **The preference-emitter roster gap is the file-worthy residue
  here and is handed to the epic rather than filed as a lesson** — it is a roster
  definition, fixable in one place.
- `metrics` — 34 genuine, of which 30 are `6-finalize` share flags (47%–67%) and 4 are
  `5-execute` shares (46%–52%). `impossible_value` on **zero** plans; `incomplete_recording`
  on 4 (`3-outline` once, `1-init` three times). The finalize-heavy fact is the same one
  `token-economics` flags as `finalize_heavy`; adjudicated as covered, not re-filed.
- `token-economics` — 45 flagged. Corpus shares: `finalize 48.7%`, `execute 20.2%`,
  `outline 13.4%`, `refine 4.6%`. `exec_metrics_blind` on **zero** plans (consistent with
  `input-integrity`). Per the skill's own rule, these flags are **covered on a Gate-1
  dedup basis against the check's shipped taxonomy** and are not re-filed; the file-worthy
  thing would be a corpus *drift*, and the drift that exists (checkpoint non-adoption) is
  §2.2.
- `token-efficiency-trend` — **regression confirmed: tokens/phase rose 536,321 → 840,514
  (+57%)** across the 53-plan series. `trend_empty_untrustworthy` did **not** fire, and
  because `blind_execute_plans: 0` the regression is a **real measurement, not an
  artifact of unrecorded execute tokens**. This flipped `token-efficiency-trend_regression`
  from `False` → `True` since the prior run — the single clearest deterioration signal.
- `task-graph-redundancy` — 58/58 genuine: `multi_task_file` 41, `dup_substep` 37,
  `in_task_build` 46, `verif_task_fanout` 55, `deliverable_fanout` 20
  (threshold 4). Folded into §2.3 rather than filed twice.
- `sequence-and-build-minimality` — 53/53 genuine; figures in §2.3.
  `docs_only_build_plans: 0` (was 5). Read against the sub-doc's three structural
  caveats: finalize-fold conflation, verify-count-upper-bound vs heavy-duration-floor,
  and `consecutive_dup` over-count (`corpus_consecutive_dup: 29,879` is inflated by that
  known over-count and is **not** treated as 29,879 redundant calls).
- `quality-chain` — **all 1816 finding rows walked step-by-step, never sampled**, per the
  methodology constraint. Corpus matrix: build 362, self-review 1089, auto-review 56,
  human-review 256, other 53. The **629 `self-review/pending/assessments.jsonl` rows are
  the assessment-store artifact, not pending work** — they carry no title and no
  resolution by construction. Plan-level flags on **3** plans only:
  `auto_review_only` + `no_qgate6` on `build-tests-do-not-neutralize-daemon-routing` and
  `orchestrated-plan-detection-fails-silently`; `no_qgate6` on
  `manage-lessons-mixes-local-time-and-utc`. Shift-left: **tier1=7**, tier2=2, tier3=6,
  tier4=41 — i.e. only 7 auto-review findings sat inside the ext-self-review surfacer's
  remit. Improved from `tier1=20` / `plans_flagged=22` in the prior run.
- `finalize-flow-conformance` — 4 flagged. **`missing_ci_verify` on zero plans: the #849
  deterministic gate holds across the whole corpus.** The 4 are
  `ci_wait_timeout`/`ci_unresolved`: `build-timeout-learned-value-truthfulness` (timeout),
  `terminal-title-channel-reconciliation` (timeout),
  `post-merge-review-findings-untriaged-in-main` (**failure**),
  `plan-less-pr-can-be-opened-but-never-corrected` (timeout at success).
  `finalize_gate_gap_ci_rerun` fired on exactly one:
  `post-merge-review-findings-untriaged-in-main`.
- `scope-estimate-accuracy` — 12 mismatches. Two distinct kinds: **6 real band
  overruns** (`single_module` band [1,15] exceeded at 18–24 files; `surgical` band [1,3]
  at 5) and **5 rows that are a schema gap, not a plan error** — `declared=broad (no band
  mapping)`. `broad` has no band, so those rows can only ever report a mismatch.
  **Recommend the epic treat "broad has no band mapping" as a check defect.**
- `track-selection-accuracy` — 3 `UNDER-TRACKED`
  (`orchestrated-plan-detection-fails-silently`, `wrong-store-guard-refuses-project-local-lessons`,
  `plan-203-inbox-consumed-vs-missing`): all three chose the light lane where the
  counterfactual says deep, and all three shipped. Adjudicated as the counterfactual
  disagreeing with a successful outcome, **not** a defect. Moved 49 → 3.
- `task-count-efficiency` — 2 `over_decomposed`:
  `post-run-steps-ordered-before-their-evidence` (22 tasks / 5 deliverables, ratio 4.40)
  and `lesson-retirement-fails-open` (9 / 2, ratio 4.50). The first is also the corpus's
  single largest token spend (10.37M) — the coupling `scope_underestimate_cost` names it.
- `architecture-lookup-ratio` — 3 `build_dominated_lookup`
  (`retrospective-completeness-and-phase5-marker` 0.07,
  `one-coherent-automated-review-contract` 0.13,
  `mandatory-plan-id-build-results-ledger` 0.09). Corpus ratio 0.342
  (546 info / 1595 build lookups). Read as a **PROMPT, not a verdict** per the sub-doc —
  a low ratio may simply mean no navigation was needed. Moved 19 → 3.
- `exploration-share` — 14 flagged of 33 measured. Corpus byte share **80.7%**, turn share
  19.3%. `unclassified: 0` on every row. **20 plans are EXCLUDED for absent counters and
  are NOT zero exploration** — the instrumentation post-dates them. Flags are prompts, not
  verdicts. `many_cheap_probes` (the groping-around signature) on 4 plans:
  `lesson-retirement-fails-open`, `fail-closed-signal-integrity`,
  `post-run-steps-ordered-before-their-evidence`, `context-byte-attribution-instrumentation`.
- `global-log-analysis` — 224 genuine over 74,712 lines / 16,394 script-seconds.
  `impossible_count: 0`, `fixture_leak_count: 0`. Two recurring error families dominate
  and are **environmental, not plan defects**: a repeated
  `[EXTENSION] Failed to load extension from plan-marshall: cannot import name
  'PathAttributionBase' from 'extension_base'` (a cache/pin skew during the
  path-attribution-seam window, ~40 occurrences), and `title teardown not delivered …
  title_reset_failed`. One log line records the known pin trap directly:
  *"executor regenerated to 0.1.1293 while plugin registry pin remains 0.1.1288"*.
  5 slow calls, the worst being **549.6 s `ci checks`** and **306.8 s `ci pr`** — both CI
  waits, expected. `high_frequency_count: 41`, headed by
  `platform_runtime session 45,638×/8,998 s` and `claude_pretooluse_hook` at ~17,000 calls
  across duration buckets — **the hook is the corpus's single busiest caller and is worth
  the epic's attention on its own.**
- `recurring-pattern-detector` — 13 systemic signatures at threshold 3: `q-gate` (51),
  `contract_drift` (22), `keyword_drift` (15), `confidence justification` (13), `user` (10),
  `same_document_contradiction` (8), `ambiguous_wording` (5), `description drift` (5),
  `description_body_drift` (4), `scope realism` (3), `stale_count_prose` (3),
  `test failure in test_github_pr.py` (3), `unreachable_guard` (3). The first five are
  **disposition classes, routed to architecture hints at Step 4c rather than filed as
  lessons**. `contract_drift` at 22 plans and `unreachable_guard` at 3 are the two
  substantive code-quality residues.
- `preference-pattern-detector` — 7 candidates, all routed (§5).
- `cross-check-synthesis` — 10 couplings evaluated, **6 fired**, all resolved above by
  adjudicating their coupled rows together: `churn_explains_walltime` (§2.3),
  `qgate_gap_chain` (1 plan — `manage-lessons-mixes-local-time-and-utc`),
  `scope_underestimate_cost` (4 plans), `redundant_build_churn` (§2.3),
  `finalize_gate_gap_ci_rerun` (1 plan), `surgical_overpay` (§2.2). The 4 that did not
  fire — `trend_empty_untrustworthy`, `argparse_signature_cluster`,
  `dispatch_topology_reentry`, `merge_window_ci_rerun` — each did so for a **stated,
  checkable reason**, recorded above.

---

### 5. Preference routing to architecture hints (Step 4c)

All 7 threshold-cleared `(module, finding-class, disposition)` rows routed per
`disposition-to-hint-routing.md`. Generalized, never transcribed; no raw dispositions and
no finding titles written to `enriched.json`.

| Row | Occurrences | Outcome |
|-----|:-----------:|---------|
| `default` / q-gate / taken_into_account | 43 | **already covered** by `default.insights[2]` |
| `default` / confidence justification / taken_into_account | 13 | routed → new insight |
| `manage-tasks:qgate-mechanical-checks` / keyword_drift / taken_into_account | 10 | **already covered** by `plan-marshall.best_practices[1]` |
| `default` / user / taken_into_account | 9 | **already covered** by `default.insights[3]` |
| `default` / q-gate / accepted | 6 | **already covered** by `default.insights[4]` |
| `default` / description drift / taken_into_account | 3 | covered — same mechanical-checks drift family as keyword_drift |
| `default` / scope realism / taken_into_account | 3 | routed → new insight |

---

### 6. Defects and residue this audit is handing to the epic

1. **The detector and the report disagree about argparse drift.**
   `recurring-pattern-detector` reports `argparse_signatures: 0` while
   `quality-verification-report` reports 463 unfiled argparse signatures across 48 plans.
   One of the two is wrong. Because `argparse_signature_cluster` gates on the detector's
   count, **the coupling designed to catch this class is silently disarmed.**

2. **`scope-estimate-accuracy` has no band for `broad`.** Five rows report
   `declared=broad (no band mapping)`, which is a schema gap that can only ever produce a
   mismatch — including a nonsense row at `actual=0`
   (`retirement-verdict-cited-a-contradicting-example`).

3. **The checkpoint targets measure the wrong quantity.** `lane-lever-effectiveness`
   scores `input + output` (1.1% of billing weight) while `cache_read` carries 76.2%.
   Both facts are first-party outputs of this same audit run.

4. **`finalize-step-preference-emitter` resolves to no ownership class** in all 58 plans'
   `phase_6` roster — a single roster-drift definition, not 58 findings.

5. **I wrote two duplicate architecture hints.** `default.insights[12]` near-duplicates
   `[2]`, and `plan-marshall.best_practices[5]` near-duplicates `[1]`. I issued both
   `enrich` calls before reading the existing lists. `architecture enrich` exposes **no
   removal verb**, so I could not undo them; `enriched.json` needs a manual trim.

6. **One plan was dormated without ever being audited.** `--dormate-all` moved **59**
   directories against the 58 scanned:
   `2026-08-08-a-rule-that-is-green-because-it-examined-nothing` landed in
   `archived-plans/` between the scan and the move. A plan of that name is also live at
   `6-finalize/in_progress` in the `plans/` store, which is untouched — but the pairing
   should be checked before that plan resumes.

7. **The active lessons corpus was empty at audit time.** All 5 stored lessons were
   `superseded`, and the two records that superseded them
   (`2026-06-24-14-004`, `2026-06-29-23-002`) were themselves already retired. Every
   Gate-1 dedup check in this run therefore cleared against an empty set — which is the
   correct verdict, but also means **the corpus lost its supersession chain**: four
   lessons now point at records that no longer exist.

---

### 7. Actions taken

- Filed 3 lessons: `2026-08-08-19-001`, `-002`, `-003` (both gates verified against the
  empty lessons corpus and the 4 in-flight plans, none of which covers any filed signature).
- Routed 4 new architecture hints; verified 3 rows already covered.
- Dormated 59 plan directories → `.plan/temp/dormated-plans/`.
- Dormated 17 past-date global logs → `.plan/temp/dormated-plans/global-logs/`; today's
  `script-execution-2026-08-08.log` and `work-2026-08-08.log` correctly retained.

### 8. Granularity note

The envelope contract specifies one message per emitted item. This is emitted as **one**
`finding` — the item being the audit outcome itself — because the user requested a single
consolidated report. The individually file-worthy signals inside it were emitted through
the lessons corpus, not through this channel.
