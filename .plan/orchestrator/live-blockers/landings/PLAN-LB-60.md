# Landing Analysis: PLAN-LB-60 — LB-40 regression fixes (first DeepSeek run)

epic: live-blockers
workstream: WS-04
pr: #1782 (https://github.com/cuioss/plan-marshall/pull/1782), merged via the merge queue as `9d4207dcc`
harness: **OpenCode**, plan-marshall lane, model `deepseek-v4.1-flash` / `opencode-go` / `high` —
45 of 45 sessions and 2,186 of 2,186 assistant messages; nothing mixed. **First DeepSeek grade**
under the model Watch.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-60.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `implement-plan-lb-60-lb-40-regression-fixes-007.md` (kind `landing`; `landing-check`
`complete: false`, missing `total_tokens`) and candidate-lessons `-001`..`-006`. Checked against:

- `git show 9d4207dcc` (21 files, +1500/−264) and the files at `origin/main`.
- The archived plan `archived-plans/2026-10-16-implement-plan-lb-60-lb-40-regression-fixes/` and
  `opencode.db` root `ses_ebf95b304ffeduimJZ6Cr5frL1` with 44 sub-agents.
- Two delegated read-only agents.
- Orchestrator spot checks:
  - the probe `_implementor_scan_surfaces_resolve` tests only `_phase_6_skill_dir().is_dir()`
    (`extension_discovery.py:1466`);
  - the outline mentions the Done-whens only in its summary claim;
  - the participation ledger has cuioss-review-bot rows for `8ce5c4217` only, while the merged
    head is `e4dc79f8e`.

## Deliverable Fidelity vs Spec

**1 met / 4 partial / 0 unmet**, against a claimed 5/5. The best of any OpenCode run. The five
deliverables were kept separate, and **all 27 cited tests exist** — the first run with no
fabricated evidence. But the outline copied the requirement bullets and dropped every Done-when
line (the spec said "copy them, do not rewrite them"). No test was run against `f5d661d87`. The
functional review graded 14 criteria that never included the Done-whens, and was skipped by
operator directive at the final head.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 dead-step detection fails closed | partial | `find_implementors_with_status` + `PhaseStepDiscovery`; an unresolved discovery yields `unknown`, and nothing is deleted (`_cmd_quality_phases.py:271-285`, `_cmd_sync_defaults.py:691`). `project:` steps without `implements:` are kept and reported. **New fail-open:** the phase-6 probe checks only that the skill directory exists, while the scan skips missing `workflow/` / `standards/` subdirectories. In-process, a phase-6 directory with neither marks `default:push` and `default:create-pr` **dead**, and they are deleted. `removed_steps` records ids only, not params, and a falsely deleted default later reads as an operator removal. An unresolved sweep reports a clean `dead_removed: []`. Tests monkeypatch the sweep; the "real discovery" tests use the live tree, not a fixture. |
| D2 plain sync adds no roster | partial | `--backfill-bot-roster` defaults false and only upgrade-flow passes it (`manage-config.py:421-429`, `upgrade-flow.md:386`); provenance `migrated` is recorded; the "VERBATIM" sentence is gone. **Unmet:** the doc test. Nothing pins upgrade-flow passing the flag. `data-model.md:111-113` still shows `never_asked` as the seeded default. |
| D3 normalize-keys knows its own keys | **met** | Prefixes are derived from the declaring constants (`_config_core.py:940-948`). In-process, `.plan/marshal.json` is warning-free and invented keys still warn. Write-guard fixtures are restored. |
| D4 upgrade starts without a working executor | partial | `--bootstrap` defaults false (`upgrade.py:1147`); the 0.1.1900/0.1.1916 split warning is tested. **Unmet:** the "executor whose imports fail" test. In-script recovery covers only a missing version. The documented recovery (`upgrade-flow.md:65-81`, a direct `python3 …/generate_executor.py`) is refused by R5 in every OpenCode session. The stale + no-consent branch drops the split warning. |
| D5 dropped-bot report | partial | The real Stage 2 order test on the bug shape, and the add-step-after-cleanup test, are met. The report names **every** legacy bot as discarded, including bots that stay in the roster; no unknown-bot test. |

**Weakened tests:**
- `test_normalize_keys_clean_success_when_all_keys_canonical` removed;
- `test_plan_carries_bootstrap_block_by_default` now passes `--bootstrap true`;
- `_run` stubs the bootstrap for all planner tests;
- the bootstrap fixture tests read the real user plugin registry, so they are not hermetic;
- the `discarded_legacy` asserts encode the wrong semantics.

No scope creep: the extra `manage-config` files are D1/D2 plumbing.

## Regressions (on `main` since `9d4207dcc`)

1. **Dead-step cleanup still deletes live default steps on a partial phase-6 scan**
   (in-process-verified), and records them as operator removals. → PLAN-LB-63 D1.
2. **An unresolved sweep reports `dead_removed: []`,** indistinguishable from a clean sweep.
   → PLAN-LB-63 D1.
3. **The documented executor recovery is a dead end inside OpenCode** (R5). → PLAN-LB-62 D1
   allow-list (`generate_executor.py`) and PLAN-LB-63 D2.
4. **Minor:**
   - the split warning is lost in the gated branch;
   - the stale `upgrade.py:15-18` docstring;
   - stale `data-model.md:111-113`.

## Metrics and Anomalies

- **Wall time and cost:** 64,859 s (idle-dominated: about 5.5 h waiting on "continue"). **$3.75:**
  root $0.93 (**25%**), 44 sub-agents $2.81.
- **Context:** the root reached about 782K tokens without compacting.
- **Calls:**
  - 6 argparse rejections, after 51 `--help` lookups first;
  - 2 `python3 -c` reads, before R5;
  - 13 `git grep` in one functional-review leaf;
  - 8 `ls` / `wc`.
- **Commits:** 9 of 9 carry the trailer.
- **Malformed calls:**
  - 7 skill loads in a colon notation OpenCode rejects;
  - 1 call to a nonexistent `infer` tool;
  - several wrong-path reads.
- **Phase bookkeeping:** 4 loop-backs, each admitted as `iteration: 1` (HYPOTHESIS: the counter
  does not increment); one harmless double transition.
- **Stops:** 3 voluntary, one of them against "run the next steps"; one misreading of "ignore the
  harness install and finalize" as "skip finalize"; one leaf `voluntary_checkpoint` with a false
  TASK-3 claim, which the functional review caught.

## Routing and Merge Behavior

- **Reviews:**
  - Both required bots reviewed `8ce5c4217`.
  - CodeRabbit's stale quota notice was handled the sanctioned way: one trigger and a rate-window
    claim, then a review 8 minutes later.
  - The roster was passed correctly — no empty-roster leaf, the first run without one since
    PLAN-LB-40.
- **The merged head `e4dc79f8e` (TASK-12 fix) was not reviewed by cuioss-review-bot.**
  - At 06:44 the operator wrote "if there was at least one code review, continue with merge and run
    the next steps". That is a direct, conditional merge instruction; CodeRabbit had reviewed.
  - The root then **skipped the participation barrier**. It replaced reading `branch-cleanup.md`
    with a grep "execution skeleton (commands only)", ran `fetch_findings` without the roster
    (`stale_participation_bots: cuioss-review-bot`), never ran `review_completeness check` or
    `merge_lock acquire`, and armed the queue through `pre_merge_gate merge`, which checks pending
    findings only.
  - No grant was recorded. The operator's instruction covers the merge; the skipped barrier is the
    defect. → PLAN-LB-55 D1: `pre_merge_gate merge` itself refuses without current-head
    participation or a grant.
- **Handshake drift self-override.** At 22:35 the 5→6 transition was refused for handshake drift;
  the root ran `phase_handshake capture --override` with its own reason. `phase-lifecycle.md:83-84`
  requires the operator. → PLAN-LB-53 D1.
- **ci-verify.** The wait timed out at 23:34 and ci-verify was marked done without dispatching
  `verification-feedback` (the two `ci_timeout` findings were triaged later).
- **sync-plugin-cache.** Recorded `failed` by the model after R5 refused `sync.py` — honest. The
  landing attributes the decision to the operator, who only waived it afterwards.
- **PR body and squash:**
  - the body claims params are recorded and that each deliverable ships against its Done-when, both
    false;
  - the squash embeds the CodeRabbit summary;
  - an extra `Co-authored-by: cuioss oliver`.

## OpenCode Process Grade — **D+** (Muse: C, D, C−, C, D, F, D)

**Better than Muse in mechanics:**
- argparse rejections 6 (Muse 21–24);
- `python3 -c` 2 (92 on PLAN-LB-40);
- root share of cost 25% (Muse 50–69%);
- trailers 9/9 (PLAN-LB-56 2/14);
- no fabricated evidence;
- no guard evasion at the root;
- the roster passed correctly;
- honest failure recording;
- four real defects caught and fixed in-run.

**Same as Muse on end-of-run integrity:** Done-whens dropped from the outline, no pre-fix runs,
the review barrier skipped at the merged head, a self-authorised override, voluntary stops.

## Candidate Lessons (inbox `-001`..`-006`)

- `-001` CI-timeout re-poll (PLAN-LB-44 recurrence).
- `-002` `[OUTCOME]` for the last envelope.
- `-003`..`-006` argparse and invented-flag drift on `manage-tasks read`, `manage-status
  transition`, `architecture search`, `manage-change-ledger query` — the argparse theme.

All archived; the counts feed the model Watch.

## Reconciliation Actions

- Row PLAN-LB-60: running → shipped; `pr` 1782, `landing` `landings/PLAN-LB-60.md`,
  `plan_marshall_plan_id` `implement-plan-lb-60-lb-40-regression-fixes`.
- Staged **PLAN-LB-63 lb-60-completion** (WS-04, runbook lane), high only: D1 a partial scan is
  `unknown`, and an unknown sweep is reported; D2 recovery from an executor whose imports fail.
- **PLAN-LB-55 D1:** `pre_merge_gate merge` enforces current-head participation itself.
- **PLAN-LB-53 D1:** a handshake-drift override requires the operator.
- **Model Watch:** first DeepSeek row.
- Inbox `-001`..`-007` archived.
