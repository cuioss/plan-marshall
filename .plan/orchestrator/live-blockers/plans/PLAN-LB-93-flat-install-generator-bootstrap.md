# PLAN-LB-93: Executor, guard and gate fixes — the recovery command runs, a green build is not failed for being fast, a lane writes only its worktree, and the gate-truth half ships

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-93-flat-install-generator-bootstrap.md` and is queued as one row file, `queue/PLAN-LB-93.json`,
> in the epic ledger. The file name keeps the original slug. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-25 from the PLAN-LB-43, -53 and -55 landing analyses, and widened the same day on the operator's
> instruction ("create a single plan for fixing all of them at once"): it carries the flat-install generator bootstrap (found
> when the recovery command PLAN-LB-43 shipped failed on import), the `test-compile` freshness backstop (four false failures
> on two PRs), the stray main-checkout writes of lane runs (three of seven audited runs), and the gate-truth half of
> PLAN-LB-55 that did not ship. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** The operator-requested single plan overrides the usual one-theme split; the six deliverables
> share no code except where stated, so a run may order them freely and report each on its own.

## Objective

Four open defects, one plan:

1. The recovery command an executor refusal prints exits 1 on the OpenCode install it is printed for
   (`ModuleNotFoundError: No module named 'argparse_surface'`). PLAN-LB-94 (#1861) retired `executor_target_mismatch` for a
   target difference, so the refusal that still prints the command is the recovery refusal for an unreadable, absent or
   cannot-start executor; the command and its failure are unchanged.
2. `verify` fails closed on a green mypy run that finished fast, although the run is cold by construction.
3. A lane run edits tracked files in the main checkout before it switches to its worktree, and no guard refuses it.
4. The finalize gates still let a run merge a head its mandated gates did not see, and the barrier's operator policy is
   documented and not enforced: PLAN-LB-55 shipped D2, D3 and part of D1 and D4; this plan ships the rest.

## Deliverables

1. **The generator starts in a flat install and its `recover` verb runs there.**
   - The bootstrap resolves each library directory in the layout it finds: the nested layout (`skills/{lib}/scripts`) and
     the flat layout (`{prefix}-{lib}/scripts` beside the generator's own skill directory). The flat-layout helper that
     `deployed_layout` and `marketplace_bundles` already carry is reused; no second derivation is written.
   - An unresolvable library is reported by name and path, not as a bare `ModuleNotFoundError`.

   *Done when:* a test builds a flat-layout fixture (skill directories named `plan-marshall-{skill}`) and runs the generator's
   `recover --help` and a `recover` against a fixture checkout from it: exit 0 and the executor regenerated for the requested
   target; the same fixture with the `script-shared` directory removed names the missing library and its expected path. Both
   fail at HEAD (`ModuleNotFoundError`, observed in the real install).

2. **Every entry script that shares the bootstrap resolves its libraries the same way, and a guard keeps it so.**
   - Re-grounded at `ee00687b8`: `determine_mode.py`, `bootstrap_plugin.py` and `gitignore_setup.py` already resolve the
     flat layout (each carries its own `plan-marshall-{lib}` fallback, since #1528) and print `--help` in the synced OpenCode
     install. `permission_fix.py` has the same fallback but still fails in that install, for a different reason: it imports
     `permission_common`, which imports `platform_runtime`, and `platform_runtime` is not on `sys.path`
     (`ModuleNotFoundError`). So the open breakage is the generator (D1) and `permission_fix.py`, not all four.
   - `permission_fix.py` resolves `platform_runtime` in the flat layout; the four scripts that carry their own copy of the
     fallback take the D1 helper instead (one shared helper, not five copies).
   - A guard test finds every script that carries the bootstrap and asserts it uses the helper.

   *Done when:* the guard test fails at HEAD naming the four scripts and the generator (their private copies), and passes
   after; one flat-layout fixture starts each of the five scripts far enough to print its `--help`, and the `permission_fix.py`
   case fails at HEAD with the `platform_runtime` `ModuleNotFoundError` while the other three pass at HEAD (a forward guard,
   reported as such).

3. **A cold, green mypy run is not failed for being fast.**
   - The freshness backstop (`classify_check_duration`, ceiling `MAX_ANALYSIS_THROUGHPUT = 200.0` files/s) stops failing
     `verify` on runs that really analysed the tree, and still fails a run that analysed nothing.
   - The mechanism is chosen at outline and the reason recorded. The candidates: (a) recalibrate the ceiling from throughput
     measured at the current file count; (b) replace the throughput guess with the affirmative signal mypy prints (the file
     count in its `Success: no issues found in N source files` line equals the collected count, which also needs no clock);
     (c) re-run once on a suspect verdict and fail only if the second run is also suspect. Whatever is chosen must keep
     `compile` / `test-compile` without a boundary unchanged.

   *Done when:* tests: a verdict for 1801 files in 8.2 s (the CI measurement) is plausible; a verdict for 660 files in 0.05 s
   (the incident shape: success over a substantial set with no measurable work) is still implausible; a boundary-bearing
   `_run_mypy` call returns exit 0 for the first and `_FRESHNESS_SUSPECT_RC` for the second. The first fails at HEAD.

4. **A lane run cannot write a tracked file in the main checkout.**
   - The guard refuses an `edit` / `write` / `patch` / `apply_patch` call whose target resolves inside the main checkout
     but outside the sanctioned paths, when the call is a lane run's and that lane's worktree exists. Sanctioned: anything
     under `.plan/local/worktrees/`, `.plan/temp/` and `.plan/local/plans/` (progress file, PR bodies, guard log). The refusal
     names the worktree path to use.
   - The Claude hook and the OpenCode guard carry the same rule, with the parity test updated.
   - The binding is narrow on purpose (see Verify-first): a developer session in the main checkout, and a plan whose
     `use_worktree` is false, are not refused.

   *Done when:* tests (OpenCode guard under node, and the hook): a lane run's `edit` of a tracked main-checkout path is refused
   with the worktree named; the same edit with the worktree path passes; an edit of `.plan/temp/rb-*/progress.md` passes; with
   no lane marker the main-checkout edit passes; with a marker but no matching worktree it passes. The first fails at HEAD.

5. **No push, merge or armed merge of a head the gates did not see — the rest of PLAN-LB-55 D1.**
   - An armed auto-merge or merge-queue entry is bound to the head it was armed for: a push of a new head while armed
     disarms it, or the push verb refuses while armed, and the barrier must pass again on the new head.
   - `pre_merge_gate merge` runs the required-bot participation check against the merge candidate (`review_completeness
     check` with the configured roster) and refuses unless every required bot participated on that head, or a recorded grant
     covers the gap, or the standing authorization applies (see Verify-first). A run that skips the barrier step no longer
     merges unchecked.

   *Done when:* tests: a new head pushed while auto-merge is armed leaves it disarmed (or the push refuses); `pre_merge_gate
   merge` against a candidate a required bot did not review refuses without a covering grant and passes with one. Both fail
   at HEAD.

6. **The barrier states and enforces the operator's review policy — the rest of PLAN-LB-55 D4.**
   - When `automatic-review` cannot read its step params (`step-params get` failing, e.g. `execution.toon not found`), it
     returns an error, never an empty `--required-bots "" --optional-bots ""` roster.
   - A stale required bot (`participated_stale`) is re-triggered before the barrier asks the operator; the question states
     whether a trigger was attempted.
   - The barrier's options are generated, not authored: none moves a required bot to `optional_bots`, and none is marked
     recommended unless the script marks it. `branch-cleanup.md` still says the productive action for a `declined` or
     `refused_hard` required bot is to "move it to `optional`" (L1041), and its loop-back note (L1222) says to "move the bot
     to `optional_bots`"; both remedies are removed.
   - After a rate-window refusal the bot is re-triggered once the window has passed, through `merge_lock rate-window wait`
     (not a raw `sleep`), up to the configured cap, before any barrier question. The policy in
     `automatic-review/standards/coderabbit.md` (mandatory, 90-minute windows, up to ten, close and reopen when no reaction)
     becomes the loop.
   - A merge under a grant is recorded by script as `merged under {kind}, gap recorded`, never in clean-merge wording; the
     merge-anyway resume re-acquires the mutex and re-runs the baseline reconcile.
   - Every merge-path question tells the truth about what follows: when `final_merge_without_asking` is `true` the
     pre-enqueue option text says the PR will be merged without a second question.

   *Done when:* tests: `step-params get` failing makes `automatic-review` return an error, not an empty roster; a
   `participated_stale` required bot gets a trigger before the barrier question; the barrier's option set contains no "make
   required bot optional" and no shipped doc offers it; a refused bot is re-triggered after its window before the barrier
   asks; a granted merge's step record carries the merged-under-authorization wording; the merge-anyway resume re-acquires
   the mutex. Each fails at HEAD.

Split guard: six deliverables by operator instruction, in three clusters (D1-D2 the install layout, D3 the build gate, D4 the
guard, D5-D6 the finalize gates). A run may order and report them independently; none depends on another's code.

## Claim Labels

- OBSERVED (D1, D2): running the printed command in this checkout's OpenCode install exits 1 with `ModuleNotFoundError: No module named 'argparse_surface'` at `generate_executor.py` L210 (orchestrator-run, 2026-10-25, before and again after a sync of all harnesses). The module exists at `~/.config/opencode/skills/plan-marshall-script-shared/scripts/argparse_surface.py`.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Re-run 2026-10-25 after the sync at HEAD: python3 ~/.config/opencode/skills/plan-marshall-tools-script-executor/scripts/generate_executor.py recover --help exits 1 with ModuleNotFoundError argparse_surface at generate_executor.py L210.
- OBSERVED (D1): the bootstrap is `generate_executor.py` L176-193: `_SKILLS_DIR = _SCRIPTS_DIR.parent.parent`, then `_SKILLS_DIR / _lib / 'scripts'` for `ref-toon-format`, `tools-file-ops`, `script-shared`. In the flat install the sibling directories carry the `plan-marshall-` prefix, so the paths do not exist.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: generate_executor.py L180-183 still computes _SKILLS_DIR = _SCRIPTS_DIR.parent.parent and loops (ref-toon-format, tools-file-ops, script-shared) with no flat-layout fallback; LB-94 did not touch the bootstrap.
- OBSERVED (D2): the same loop (`_SKILLS_DIR / _lib / 'scripts'`) appears in `tools-permission-fix/scripts/permission_fix.py`, `marshall-steward/scripts/determine_mode.py`, `bootstrap_plugin.py` and `gitignore_setup.py` (orchestrator grep). Whether each fails the same way in a flat install is not run (HYPOTHESIS).
  - verdict: contradicted | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: yes | evidence: The four scripts already carry a flat-layout fallback (_SKILLS_DIR / plan-marshall-{lib}; since #1528): permission_fix.py L50-52, determine_mode.py L178-180, bootstrap_plugin.py L63-65, gitignore_setup.py L61-63. Run against the synced OpenCode install: determine_mode, bootstrap_plugin and gitignore_setup print --help (exit 0); permission_fix fails for a different cause (ModuleNotFoundError platform_runtime via permission_common.py L32). D2 narrows to the generator plus permission_fix.
- OBSERVED (D1): the same generator, run from the repository source with the same arguments, regenerated the executor for `claude`, so the verb works where its libraries resolve. `deployed_layout` and `marketplace_bundles` carry flat-layout handling and have tests (`test_deployed_layout.py`, `test_marketplace_bundles.py`); PLAN-LB-43 D4 gave the freshness verdict a flat-install route; the generator bootstrap was not part of it.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: The same generator run from the repository source regenerated the executor for claude twice today (recover --target claude). The four entry scripts reach flat-layout handling through marketplace_bundles.resolve_skills_root; deployed_layout.py and the tests named still exist.
- OBSERVED (D3): `build.py` L532-578 `_run_mypy` always passes `--no-incremental` ("a cache the gate never consults cannot produce a false-clean", its own docstring), then judges a boundary-bearing run with `classify_check_duration` and returns `_FRESHNESS_SUSPECT_RC` (3) when files/elapsed exceeds `MAX_ANALYSIS_THROUGHPUT = 200.0` (`script-shared/scripts/build/_gate_coverage.py` L109). The ceiling was calibrated against "417 files in 5.84 s = 71 files/s" cold, between that and the incident (660 files in 2-5 s).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: build.py: _FRESHNESS_SUSPECT_RC = 3 at L112, _run_mypy at L532, --no-incremental at L564, the suspect return at L576; _gate_coverage.py: MAX_ANALYSIS_THROUGHPUT = 200.0 at L109, classify_check_duration at L131.
- OBSERVED (D3): the tree is now larger than the calibration set; `verify / verify` failed three times on PR #1851 (1801 files in 8.2 s, 205-220 files/s) and once on PR #1857 (211 files/s), each cleared by a re-run with mypy reporting no issues (`landings/PLAN-LB-43.md`, `landings/PLAN-LB-53.md`).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Historical CI measurements (PR #1851 three failures, PR #1857 one) are recorded in landings/PLAN-LB-43.md and landings/PLAN-LB-53.md; the ceiling that produced them is unchanged at HEAD, but the file counts and timings were not re-measured.
- OBSERVED (D4): the OpenCode guard's decision table covers `edit` / `write` / `patch` / `apply_patch` with R3 only, which refuses the generated executor path (`guard.js` header L18 and L37-40, handler L1729-1737); no rule judges a path. A lane run's marker is `.plan/temp/rb-<plan>/progress.md` (fresh within 24 h, `isLaneRun` L1216), and `contextGate` L1237 is the plan-context predicate.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: guard.js: edit/write/patch/apply_patch guarded by R3 only (header L18, R3 text L37, handler L1731-1733, executor path only); isLaneRun at L1216 (rb- prefix test at L1227), contextGate at L1237.
- OBSERVED (D4, session store): lane roots wrote tracked files into the main checkout before switching to the worktree — PLAN-LB-43 twelve edits (`extension_api.py` and others), PLAN-LB-55 two edits of a tracked test plus an untracked draft, PLAN-LB-85 `sonar.py` fourteen times; PLAN-LB-88, -86, -80 and -53 none. The only main-checkout paths the clean runs touched are `.plan/temp/**` and `.plan/local/plans/NO_PLAN/work/ci-bodies/**`.
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Session-store history of PLAN-LB-43, -55 and -85 was not re-read in this pass. Two later runs (PLAN-LB-90, PLAN-LB-94) made zero main-checkout edits per their landings, so the incidence is 3 of 9 audited runs and the landed rule would have been exercised by none of the last two.
- OBSERVED (D5): PLAN-LB-55 shipped `_push_gate.py`, the `push` verb, the merge barrier's refusal of a candidate any head-dependent step record did not validate (`pre_merge_gate.py` `MERGE_HEAD_NOT_GATED`, `cmd_merge`), the `merge-authorization grant` operator-answer check, and D2 and D3 (`landings/PLAN-LB-55.md`). It did not ship the two D1 bullets above or any of D6.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: pre_merge_gate.py: MERGE_HEAD_NOT_GATED at L97 and cmd_merge at L449 exist; _push_gate.py exists at workflow-integration-git/scripts/. The merge-authorization grant operator-answer check was not read in this pass. The two D1 bullets are still unshipped: _push_gate.py has no armed or auto-merge handling and pre_merge_gate.py has no review_completeness or participation reference.
- OBSERVED (D5): PLAN-LB-60 merged `e4dc79f8e`, which `cuioss-review-bot` never reviewed, after replacing the barrier with a grep "execution skeleton"; PLAN-LB-50's auto-merge, armed for `f4ca42ab`, merged a force-pushed `779b035ab` 89 s later (spec of PLAN-LB-55, kept here as the origin of both bullets).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Historical incidents (PLAN-LB-60 merge of e4dc79f8e, PLAN-LB-50 auto-merge of 779b035ab) are recorded in the PLAN-LB-55 spec and landing; not re-derivable from the tree at HEAD.
- OBSERVED (D6): `branch-cleanup.md` L1041 still names "move it to `optional`" as the productive action for a `declined` required bot (and for `refused_hard`), after PLAN-LB-55 removed the demotion option from the structural prompt (L1355). `automatic-review/SKILL.md` reads the roster off `step-params get` at L1128 and L1186 and defaults an unreadable result to EMPTY. `merge_lock.py` carries `rate-window {claim,check,wait,release}`. The Branch E wording `merged under {kind}, gap recorded` is documented (`branch-cleanup.md` L2216-2231) and was not implemented as a script record by PLAN-LB-55.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: branch-cleanup.md L1041 still says move a declined required bot to optional; Branch E at L2216-2231 documents merged under {kind}, gap recorded; automatic-review SKILL.md reads the roster off step-params get at L1128 and L1186, defaulting to EMPTY; merge_lock.py carries rate-window claim/check/wait/release. UNDERSTATED: branch-cleanup.md L1222 also tells the operator to move the bot to optional_bots; D6 must remove both.
- OBSERVED (D5, D6): the runbook lane's skill names neither `pre_merge_gate` nor the barrier, so these gates bind the plan-marshall lifecycle lane only; the operator asked for them regardless.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: runbook-lane/SKILL.md has zero occurrences of pre_merge_gate or barrier (grep count 0).
- HYPOTHESIS: `test_generate_executor_bootstrap.py` and `test_flat_root_discovery_coverage.py` can host the D1 fixture; they do not catch this case today (verify-at-outline).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Both files exist under test/plan-marshall/tools-script-executor/ (test_generate_executor_bootstrap.py, test_flat_root_discovery_coverage.py). That they miss the flat-install case follows from the real install still failing at HEAD; their content was not read.
- HYPOTHESIS: a lane marker `rb-<name>` corresponds to the worktree `.plan/local/worktrees/<name>` (seen for `rb-lb-55-gate-head-truth`); confirm for every lane before D4 relies on it (verify-at-outline).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Lane markers rb-lb-* remain under .plan/temp (about 30, kept after their lanes ended), but .plan/local/worktrees now holds only _orchestrator, so the rb-<name> to worktree-<name> mapping cannot be confirmed from the tree; the outline must read it from a live lane. Note the markers outlive their worktree, which is the D4 stale-marker hazard.
- Verify-first clause (D1): the bootstrap runs before any library is importable. Decide how the helper is reachable from the first line of the script (a stdlib-only snippet inlined once per script, or a path computed without importing) and record the reason; five inlined copies are the failure D2's guard exists to prevent.
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: An outline-time decision (how the helper is reachable before any library imports), not a fact at HEAD. Input for it: the four sibling scripts already use a stdlib-only ancestor search for script-shared or plan-marshall-script-shared before importing marketplace_bundles.resolve_skills_root (permission_fix.py L38-48); the generator can take that snippet.
- Verify-first clause (D4): the lane marker is per checkout and lives for up to 24 h, and `use_worktree: false` plans legitimately edit the main checkout. A rule bound to the marker alone would refuse a developer's ordinary edit in the main checkout after a lane run, and a legitimate main-checkout plan. Bind it to the lane's own calls (the session identity, or the marker carrying it) and to the existence of the matching worktree; if the guard cannot tell the lane's session from another, say so in the rule's documentation and choose the narrower binding. Record the reason.
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: An outline-time binding decision for D4, not a fact at HEAD. Input: about 30 rb-lb-* markers remain under .plan/temp while only the _orchestrator worktree exists, so a marker-only binding would refuse edits long after a lane ended; guard.js isLaneRun (L1216) applies a 24 h freshness test on top.
- Verify-first clause (D5): the operator's ruling of 2026-10-25 stands — with at least one valid CodeRabbit review and the quota refusing the re-review, the merge proceeds without a question. The participation check inside `pre_merge_gate merge` must therefore admit a quota-limited required reviewer that has a qualifying review and handled findings; it refuses an unreviewed required bot that never reviewed any head. Record how the check tells the two apart.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: The 2026-10-25 ruling stands as recorded in epic.md Decisions and the resume anchor (a valid CodeRabbit review plus a quota refusal = move on). PLAN-LB-94 merged on exactly that basis (#1861).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — the bootstrap (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` and `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — the `platform_runtime` import that fails in the flat install (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` — the flat-layout rule the bootstrap reuses (verify-at-outline) (D1, D2)
- OBSERVED: `test/plan-marshall/tools-script-executor/` — `test_generate_executor_bootstrap.py` and a new flat-install fixture test (D1)
- HYPOTHESIS: `test/plan-marshall/script-shared/` — the bootstrap guard test (verify-at-outline) (D2)
- OBSERVED: `build.py` — `_run_mypy` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — `classify_check_duration`, the ceiling (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — the backstop's description (D3)
- OBSERVED: `test/plan-marshall/build-pyproject/test_gate_coverage.py` and `test/default/test_build_verify.py` (D3)
- OBSERVED: `.opencode/plugin/guard.js` — the edit-tool handler and the lane predicate (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` and `pretooluse_gate.py` — the mirror (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md` and `contract.md` — the decision table (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/` — `test_opencode_enforcement.py`, `test_guard_hook_parity.py`, `test_guard_cwd_and_worktree_scope.py`, `test_claude_pretooluse_hook.py` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `cmd_merge` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_push_gate.py` — the push verb, which carries no armed or auto-merge handling at `ee00687b8` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the barrier options, the stale-bot trigger, Branch E, the merge-anyway resume (D5, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` and `scripts/review_completeness.py` — the roster read error, the participation check (D5, D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — the policy as a loop (D6)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — the recovery cap and wait (verify-at-outline) (D6)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/`, `test/plan-marshall/automatic-review/`, `test/plan-marshall/manage-locks/` — gate, barrier and recovery tests (verify-at-outline) (D5, D6)

## Dependencies and Sequencing

- Depends on: PLAN-LB-43 (shipped, #1851), PLAN-LB-53 (shipped, #1857) and PLAN-LB-55 (shipped, #1856): this plan completes their unshipped or unreachable parts.
- Follows: PLAN-LB-94 (shipped, #1861), which rewrote `generate_executor.py` and the executor template; D1-D2 start from the merged text (the bootstrap at L180-193 is unchanged). D5 and D6 touch `phase-6-finalize` and `manage-status` files that the staged PLAN-LB-58 and PLAN-LB-82 also declare, and D4 touches the guard files PLAN-LB-79 and PLAN-LB-88 shipped; the corpus cross-check at admission decides and the gate will ask. Not measured at staging.
- Adjacent to: PLAN-LB-92 (shipped, #1850), which produces a per-worktree executor through the generator; its refresh verb and the lane's bootstrap route call the generator and are not changed here. PLAN-LB-90 (shipped, #1859) edited the lane's skill and `runbook_lane.py`, which no deliverable here touches.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-93-flat-install-generator-bootstrap.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
