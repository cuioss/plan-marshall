# Landing Analysis: PLAN-LB-81 — The runtime stamp carries the measured variant, refreshes at landing, leaves no stale stamp, and the reader is hardened

epic: live-blockers
workstream: WS-04
pr: #1832 (merge commit `d7e351419f17cc2bba4922561024bc577e1de32f`, 2026-10-21T11:11:02Z, branch `fix/lb-81-lb-45-completion`; supersedes #1831, closed unmerged under the quota policy)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying the landing message
> against ground truth: the merged diff and tree at `d7e351419`, both PRs through the `ci` abstraction (state,
> 10 and 11 reviews, 23 and 34 comments, 5 and 9 threads), the run's commits and trailers, the guard log, and the
> OpenCode session store read-only (475 messages in the main session, 25 shell calls in the self-review
> sub-agent). One read-only `execution-context-level-5` agent corroborated the code and the tests; the
> orchestrator re-read DF1-DF3 (`orchestrator.py` L6855-6975, `emit-landing.md` L205-244) itself. The run was
> started within three minutes of PLAN-LB-48 and PLAN-LB-49 (all three OpenCode sessions opened between
> 19:04Z and 19:05Z on 2026-10-20) and ran beside them for sixteen hours.

## Verdict

**Grade C+.** The process is the cleanest of the OpenCode runs so far: one shell file operation (the last call
before the landing), no `git add -A`, no `sed -i`, 74 in-process builds and none through the daemon, the lane
re-read after the restart, trailers on every commit including the merge, a guard log that matches the
transcript exactly, an honest "not met as written" for the Done-when the spec got wrong, every refusal time
verified, and a sub-agent that loaded the reviewer persona. The grade is held down by the product: the plan's
own Objective ("loud about what it could not read") is only half delivered. The provenance the refresh records
never reaches the landing (DF1), the refresh measures the landing process's session and replaces the stamp
wholesale (DF2), on a non-OpenCode harness an environment model overwrites the model the run reported (DF3), the
new root-manifest read stamps a placeholder bundle version on Antigravity (DF4), and 15 of the 24 audited test
rows are weak, misnamed or vacuous at the base, two of them because the orchestrator's own spec labelled a
clause "fails at" that already held.

Lane text loaded: the PLAN-LB-72 text (`cf28a05db`, still the newest on `main`; the two loaded copies are
byte-identical to the LB-48 run's), read at 2026-10-20T19:05:11Z and **re-read at 2026-10-21T07:01:26Z**, 28
seconds after the work resumed from the idle gaps (5.70 h before the operator's `retry` at 05:04:33Z, 1.29 h
before the resume at 07:00:58Z).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the landing carries the measured variant; effort is measured where the harness measures it | shipped-as-specified (third clause was a spec error) | `orchestrator.py:6391-6405` adds `variant`, `provider`, `model_origin`, `model_omission_reason`; `runtime_info.py:491-492` makes the measured variant win over `--effort` with `effort_source: measured`; `emit-landing.md:232-234` and `landing-payload-spec.md:101` specify `{model}/{variant}`. The third clause (a `mixed` tree writes distinct labels, labelled "fails at `137986c61`") already held at the base (`emit-landing.md:214`, `orchestrator.py:6392`, `runtime_info.py:376`): the run's "not met as written" is right and the spec was wrong. |
| D2 — the stamp is refreshed at landing time | shipped-modified | `refresh-runtime-stamp` exists (`orchestrator.py:6818-6977`) and `emit-landing.md:213-216` calls it first. **Not met:** the second Done-when asks that "the landing marks it as start-time"; `measured_at_start` is written to `status.json` only and the landing copies bare values (DF1). The first clause is tested at `status.json`, not at the landing. The refresh also measures the landing process's session, not the plan's (DF2). |
| D3 — a failed preflight leaves no stale stamp, a failed stamp is visible | shipped-as-specified | The clear precedes the collector (`orchestrator.py:6740` before `:6752`), exactly as the spec's L71-72 asked; step 8a.6 branches on `metadata_stamped: false` (`phase-1-init/SKILL.md:860`); OpenCode with no session id returns `model_omission_reason: no_session_id` (`runtime_info.py:467`). The clear's result is discarded (DF6); the doc-contract test is keyword-only. |
| D4 — the reader is robust, the guarding tests can fail | shipped-modified | `Path.as_uri()` with `mode=ro`, a parameterised recursive CTE, `XDG_DATA_HOME` honoured: all corroborated. The replaced preflight-argv test is not replaced (the canned-argv test remains); the flat-layout fixture is unrealistic and the new root-manifest read stamps `0.1.0` on Antigravity (DF4). |
| Added-unplanned | — | 13 files against a declaration the parser read as 8: 5 beyond it. Four are necessary and disclosed (`plan-orchestrator/SKILL.md`, `workflow/preflight.md`, `runtime-info.md`, `test_phase_1_init.py`). The fifth, `test_landing_completeness.py`, **was declared**: the spec wrote "`test_preflight_client_toon.py` and `test_landing_completeness.py`" in one bullet and the parser resolved the second bare filename as a filename glob that claims no path. The landing is right not to list it; the orchestrator's spec was wrong (PLAN-LB-69 D4 gains the rule). |

### Tests

24 rows audited: **9 sound** (two with a stated gap), **2 vacuous at the base**, **13 weak or misnamed**.

- Sound: `test_preflight_stamps_variant_and_measured_effort`, `test_opencode_effort_is_the_measured_variant`, `test_refresh_stamps_a_mixed_tree_after_a_model_switch`, `test_refresh_keeps_the_start_value_when_the_database_is_unreachable` (asserts `status.json` only), `test_failed_collector_clears_a_previous_runtime_stamp` (its `_failed` fallback calls the function it replaced and would recurse on any other `subprocess.run`), `test_opencode_without_a_session_reports_the_omission_reason`, `test_database_path_with_uri_metacharacters_is_read`, `test_default_opencode_db_path_follows_xdg_data_home`, `test_unreadable_executor_yields_no_executor_version` (its tautological `!= '0.1'` became a real equality).
- Vacuous at the base: `test_preflight_stamps_the_mixed_model_labels` (unchanged, a canned payload through a monkeypatched `subprocess.run`) and `TestEmitLandingRuntimeStamp::test_emit_landing_writes_the_mixed_list` (asserts a sentence `emit-landing.md:214` already carried at `137986c61`). Both exist because the spec's clause was wrong; they were kept "as the regression control".
- Keyword-only doc tests: `test_emit_landing_writes_the_variant_form`, `test_emit_landing_refreshes_the_stamp_first`, both `TestPhase1InitRuntimeStampBranch` tests (`test_warning_names_the_reason` searches the rest of the file after the split, not the 8a.6 section).
- Weak or constant-pinning: `test_refresh_over_an_unchanged_tree_keeps_the_value` (a no-op refresh also passes), `test_the_executor_version_stays_optional`, `test_a_block_carrying_all_four_is_complete` (docstring only), `test_measurement_is_bounded_to_the_session_tree` (the pre-image was already result-bounded and the test cannot observe a scan), `test_bundle_cache_tree_reads_the_deployed_manifest` (passes at the base), `test_flat_deployed_tree_reads_its_root_manifest` (a fixture no emitter writes), `test_no_marketplace_build_version_is_reported` (passes an explicit root, so the auto-locate path is never exercised).
- Misnamed: the landing and the progress file cite `TestPhase1InitRuntimeStampBranch::test_unstamped_metadata_without_degradation_is_reported`; that class holds `test_step_branches_on_an_unstamped_metadata` and `test_warning_names_the_reason`. The named test is a module-level duplicate in `test_preflight_client_toon.py:429` that passes at the base.

### Order labels

The landing's rows are consistent with the code and with the build timeline: every `test-first` row's behaviour is
absent at `d7e351419^1` (the audit read the pre-image for each), and the six `mutation-after` logs are
listed by name. Not opened one by one: the `python-2026-10-20-…log` files, so the red runs themselves are the
landing's account.

## Code defects (PLAN-LB-84)

Confirmed by the corroboration; DF1-DF3 re-read by the orchestrator.

- **DF1** (medium): the provenance the refresh records never reaches the landing. `measured_at_start` is written to `status.json` (`orchestrator.py:6920-6927`); `emit-landing.md:227-228` copies `metadata.model` / `effort` only and `landing-payload-spec.md:117-121` has no field for it, so a start-time or carried-over value lands indistinguishable from a landing-time one. Trigger: database unreachable at landing. The spec's second D2 Done-when asks for exactly this.
- **DF2** (medium): the refresh runs `runtime-info` with the LANDING process's environment (`orchestrator.py:6866-6873`) and overwrites the model fields wholesale (`:6941-6950`), with no union with the stamped models. Trigger: plan starts in root session A on model X and finalizes in a new root B on model Y; it lands as Y, not `mixed`.
- **DF3** (medium): the refresh passes no `--model` / `--effort` (`:6866-6871`), so on a harness that does not measure, an environment model replaces the model the run reported and is tagged `measured`, inverting preflight's precedence (flag beats env). Trigger: Claude with `ANTHROPIC_MODEL` set to another model.
- **DF4** (medium): the new root `plugin.json` read (`runtime_info.py:511`) picks up Antigravity's hard-coded aggregate manifest version `0.1.0` (`marketplace/targets/antigravity/emitter.py:393`), so Antigravity installs now stamp a placeholder `bundle_version` where they previously stamped nothing (landing `unknown`). OpenCode installs write no root `plugin.json` (`install.sh:462` is Antigravity-only), so the new docstring's claim and the flat-layout fixture are wrong.
- **DF5** (minor): the session-tree guard applies only when the landing harness is OpenCode and `model_origin` is never cleared (`:6906-6910`, `:6941-6944`): a plan started under OpenCode and landed under Claude with an env model keeps a stale `model_origin: session_tree`.
- **DF6** (minor): `cmd_preflight` discards `_clear_runtime_metadata`'s result (`:6740`); a failed clear followed by a failed collector leaves the old stamp and the degraded result carries no signal of it.
- **DF7** (minor, plausible): the refresh reads the status document with `read_status` at `:6890` and writes the whole document at `:6965`; the write goes through the guarded seam (protected keys carried), but a concurrent non-protected write between the two is clobbered. The existing stamper has the same pattern.
- **DF8** (minor, plausible): the downward recursive query joins on `s.parent_id` (`runtime_info.py:327-335`); "never scans every project's sessions" holds for the result set, not for I/O unless `parent_id` is indexed.
- **DF9** (minor): the "exactly one refresh rule" partition assert (`orchestrator.py:6435`) checks set equality only, not disjointness, and is stripped under `python -O`.
- **DF10** (minor): when an env model is read but rejected by the session-tree guard the returned reason is `model_unknown`, which is misleading.
- **DF11** (minor, plausible, outside this plan): the runbook lane never calls `refresh-runtime-stamp` and has no `status.json`, so the landing-time guarantee covers `/plan-marshall` lifecycle plans only. This is PLAN-LB-78 D3's scope, and the reason this very landing arrives `effort=unknown`, `plugin_version=unknown`.

## Metrics and Anomalies

- Tokens (from `session_v2`, the landing says `unknown`): main session (`build`, "PLAN-LB-81 Completion Runbook Plan") input 2,912,004 / output 103,490 / reasoning 78,054 / cache-read 145,392,384, cost $0.982; self-review sub-agent (`general`) input 175,980 / output 13,349 / reasoning 38,648 / cache-read 6,709,632, cost $0.078. Total input 3,087,984, output 116,839, reasoning 116,702, cache-read 152,102,016; **$1.060**. Every message is `deepseek-v4.1-flash` variant `high`, provider opencode-go; OpenCode 2.1.1.
- Duration: 16 h 27 m (2026-10-20T19:05:07Z to 2026-10-21T11:32:10Z). Operator question 31 m 24 s; idle gaps of 5.70 h, 1.29 h and 1.53 h.
- Tool use in the main session: 242 shell, 120 edits, 65 reads, 33 greps, 28 writes, 11 globs, 9 skill loads, 3 sub-agent dispatches, 1 question; 74 builds, all in-process. The sub-agent: 25 shell calls (all `git`), no build.
- $1.06 against LB-48's $1.30 and LB-77's $0.81, for 4 deliverables over 13 files.
- Merge time: 2026-10-21T11:11:02Z; the landing was written 11:31:50Z.

## Routing and Merge Behavior

- **#1831 (closed unmerged)**: CodeRabbit auto-summary 22:09:09Z, then triggers at 22:10:50Z, 05:42:50Z, 07:14:57Z, 07:36:10Z (`@coderabbitai full review`, the escalated trigger) and 09:29:40Z, each answered with a rate-limit refusal (all five verified). **No formal CodeRabbit review exists on #1831.** Sourcery reviewed it at 22:13:37Z (6 issues) and 22:16:55Z (1 security, 2 other); a second manual trigger at 22:55:11Z was refused on its own review budget (the landing's "hard quota since 10:01Z" is the #1832 refusal; the first refusal was 22:55:16Z). All nine threads are resolved.
- **90-minute floor**: held at 22:10 -> 05:42 (7 h 31 m), 05:42:59 -> 07:14:57 (91 m 58 s), and 07:36:18 -> 09:29:40 (113 m). **Broken at 07:36:10Z**: the escalated trigger came 21 m 06 s after the 07:15:04Z refusal, 68 m 54 s short; the lane (§ 6 step 5) says to re-trigger no sooner than 90 minutes "even when the reviewer's own notice names a shorter wait" and lets the escalated trigger be posted once, not early. The run then closed the PR after five triggers (the lane allows up to ten); the operator's recovery policy allows close-and-reopen when no review exists, which was true.
- **#1832**: opened ~10:01Z; Sourcery refused on its review budget at 10:01:07Z and reviewed anyway at 10:12:20Z (one security-only inline comment, a false positive, answered and resolved); CodeRabbit formal review at **10:05:25Z** (4 actionable, head `25c5571b7`), four minutes after the new PR, which is the same shape as LB-77's close-and-reopen. The four findings were fixed in `1715a7f13` (10:10:53Z) and CodeRabbit confirmed them in-thread at 10:12:57Z, 10:13:50Z and 10:14:48Z; triggers 10:15:52Z and 10:42:51Z were refused. All five threads are resolved.
- **Standing authorization at `9a62ed1c4`** (lane § 7): a qualifying review exists (10:05:25Z); every finding from it and later ones is fixed or answered and resolved; a re-trigger after the last push (10:42:23Z push, 10:42:51Z trigger) was refused. `9a62ed1c4` is a merge of `main` into the branch (`148558aa1`, PLAN-LB-48), pushed 28 minutes before the merge; the fix in `1715a7f13` was confirmed in-thread before it. No operator question about the merge was asked and none was needed: the branch was cut from `8a449ca83`, which already carries #1829, so cuioss-review-bot was not on the required list and there was no reviewer gap.
- CI: not re-read per head. The merge-group run `39590088052` completed `success`; `queue-state` reads `merged` with the merge SHA on `origin/main`.
- Commit trailers: all eight commits on the branch, **including the merge commit `9a62ed1c4`**, carry exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>` (read with `%(trailers)`). The lane text gives no merge-trailer instruction, so the run supplied it on its own; PLAN-LB-73 D1 makes it a rule.

## Operator questions (rebuilt from the transcript)

Exactly one, completed; no aborted question; one free-text message (`retry`, 05:04:33Z).

1. 19:05:43Z, header "LB-81 is blocked", options Land the ledger then rerun (Recommended) / Run against the ledger copy / Stop the run. **Answered with free text, "ledge ris landed", at 19:37:07Z**; no option was selected, and the landing says so. The question's premise was true: the spec was an uncommitted file in the ledger worktree until the land (`8a449ca83`). The run verified the land before continuing. This is the third face of the "spec reaches a runbook run only through a ledger land" watch (LB-59, LB-74, LB-76, now LB-81).

## Process findings

- **Concurrency**: LB-48, LB-49 (plan lifecycle) and LB-81 were launched together from one emitted block and ran in parallel for sixteen hours, beside other sessions of another repository (`pm-mcp-core`) on the same machine. One CodeRabbit quota served all of them: #1831 got no review in 11 hours and 5 triggers, LB-48 got its windows at 22:15, 05:17, 06:44, 08:53. The livelock that the close-and-reopen cured here is the same shape as LB-68's and LB-77's.
- **Skills and personas**: the main session loaded the runbook lane, `persona-implementer`, `python-core`, `pytest-testing`, `plugin-script-architecture`, `ref-code-quality`, `persona-module-tester` and `plugin-architecture` (the spec's six skills and the implementer persona, loaded once at 19:37:55Z after the land). It never loaded `persona-code-reviewer`; the sub-agent loaded it at 21:10:10Z. The landing says "Every self-review round and every PR-comment triage: `persona-code-reviewer`": PR-comment triage ran in the main session without it.
- **Rule check**: the guard log has exactly the three lines the landing lists (R1 19:39:39Z, R2 21:01:02Z for `cp -a .pyprojectx`, R1 sub-agent 21:10:18Z) and matches the transcript's guard-blocked calls. The sub-agent also had two `tail` calls denied by OpenCode's own permission layer ("Permission denied: shell", 21:39:54Z and 21:39:55Z), which the landing does not list. The only shell file operation in the main session is the `wc` at 11:31:07Z.
- **Self-review**: three rounds in one sub-agent session (21:10Z-22:07Z); rounds 1 and 2 had blocking findings that were fixed, round 3 clear at `8681fcd30`. **Three heads after it were never self-reviewed**: `25c5571b7` (a semantic fix from Sourcery's findings), `1715a7f13` and the merge `9a62ed1c4`.
- **Sub-agent builds**: none. Main-session builds: 74 in-process, none through the daemon.

### `test-compile` at every pushed head

The landing lists eight heads; the branch has exactly those eight. Local `verify` (which includes `test-compile`) succeeded against the content of five of them.

| Head | Local evidence |
|------|----------------|
| `3bfbffe90`, `1ecb1049e`, `ad340c414` | `quality-gate` only; CI per head not read |
| `3397327b1` | local `verify` success at 21:01Z |
| `8681fcd30` | local `verify` success at 21:53Z |
| `25c5571b7` | local `verify` success at 09:51Z |
| `1715a7f13` | local `verify` success at 10:16Z |
| `9a62ed1c4` | local `verify` success at 10:35Z |

## Landing-message accuracy

Correct: the PR numbers and the merge state; #1831 closed unmerged under the quota policy; the eight pushed heads; every deliverable's commit attribution; the refusal times of both bots on both PRs; the nine and five thread counts and their resolution; the three guard lines; the one question and its free-text answer; the "not met as written" D1 clause; `deliverables_done=3` of 4 as the run counts it; the residue list (CodeRabbit never reviewed the merge head, Sourcery's red check, the unknown keys); trailers.

False or misleading:

1. D2 second Done-when "met": the landing does not mark a start-time value (DF1); the first clause is evidenced at `status.json`, not at the landing.
2. §2 "every PR-comment triage: `persona-code-reviewer`": the main session never loaded it.
3. §4 `TestPhase1InitRuntimeStampBranch::test_unstamped_metadata_without_degradation_is_reported`: no such method; the cited test is a module-level duplicate that passes at the base.
4. §4 "replaced" preflight-argv test: `test_preflight_forwards_the_self_report_and_stamps_metadata` still uses the canned argv; `--model` is never router-parsed.
5. Sourcery "hard-quota refusal since 10:01Z": the first refusal was 22:55:16Z on #1831.
6. Rule check omits the sub-agent's two denied `tail` calls.
7. Facts block: `total_tokens=unknown` (3.09M input, $1.06 measured); `effort=unknown`, `plugin_version=unknown` (it says why: the lane's resolve supplies neither); `model` without the variant; `self-review: clear` for five of eight heads.
8. The 07:36:10Z escalated trigger 21 minutes after a refusal is not mentioned among the refusal history; the history lists the time, not the interval.
9. `landing-check`: `complete: false`, `missing_keys` = `total_tokens`, `effort`, `plugin_version` — **recurrence 3** of the PLAN-LB-78 D3 defect, not a new one. The irony stands: this plan's landing arrives without the stamp it shipped.

## Reconciliation Actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-LB-81 --status shipped`
- [x] row `pr` stamped — `1832`
- [x] row `landing` stamped — `landings/PLAN-LB-81.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-81-lb-45-completion` (from the sender `rb-lb-81-lb-45-completion`)
- [x] `epic.md`: grade and watch entries, the incomplete-landing defect recurrence 3, the PLAN-LB-81 defects and the retirement of the PLAN-LB-45 stamp defect, the Queue annotations
- [x] PLAN-LB-84 staged (`lb-81-completion`, medium, WS-04, runbook lane) and its Expected Surface verified with `corpus surfaces`
- [x] PLAN-LB-69 gains the third spec-authoring clause (bare filename after "and") and the LB-48 / LB-81 datapoints (no surface change)
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- PLAN-LB-84 owns DF1-DF10 and the test repairs; DF11 is PLAN-LB-78 D3.
- PLAN-LB-69 D4 (spec authoring): full repo-relative paths in Expected Surface bullets; D3 (audit): the persona claim, the interval behind a refusal-history list.
- Rulings for the operator: whether the escalated CodeRabbit trigger may be posted before the 90-minute floor (the lane says no); whether three plans should run in parallel against one CodeRabbit quota.
