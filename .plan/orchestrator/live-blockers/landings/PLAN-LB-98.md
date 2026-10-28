# Landing Analysis: PLAN-LB-98 — The executor-skew check answers on a flat install

epic: live-blockers
workstream: WS-04
pr: #1876 (`b8961015b`, merge queue, base `main`, merged 2026-10-27T19:05:30Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not run on a real install (the sync that carries it has not
> been run): it rests on the PR's tests, green CI, the red job log and the merged diff of the probe and the layout module.

## Verdict

**Grade: B+.** Runbook lane, `deepseek-v4.1-flash/high` on all five sessions **(store)** (root plus four self-review
sub-agent sessions), 5 h 37 min wall clock (2026-10-27T14:04Z to 19:41Z; merged 5 h 01 min in).

All three deliverables are delivered and the code does what the spec asked **(re-read, diff read in full)**: on a flat install
the lane text version is the `version` of the sync's install stamp at the deploy root, found through `flat_deploy_root` and
`read_deploy_stamp_version` in `deployed_layout`; the verdict is `match` for an equal or newer executor and `skew` with the
remedy for an older one; an absent, unreadable or version-less stamp stays `could_not_check`; and the reason now names the path
that was probed instead of "not derivable from its install path". Eight files (+592/-36), CI green at every head, both review
threads resolved, main clean **(re-read)**. The lane's red job log exists and lists exactly the ten failing tests it claims
**(re-read, job log)**. Three of the debits are small; the one that matters is not the lane's.

Credits: every count is exact (questions 3, sub-agents 4, guard 3 against 3, read-class shell calls 8 against 8), no spoofed
identity, no restart, no main-checkout edit, the self-review ran to its limit and the operator authorized a verification round,
CodeRabbit reviewed the merged head, the fail-open case I would have missed was caught by the lane (a stamp version such as
`unknown` yields no version key and would have made every executor read as `match`; the probe now treats an unparseable version
as unmakeable), it also fixed the one flat target where the new leg could not answer (Antigravity published no install stamp),
and its residue is specific and honest.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 the lane text version is read from the install root's stamp | shipped-as-specified | `_lane_version_probe` (versioned → flat stamp → nested → unresolved), `flat_deploy_root`, `read_deploy_stamp_version`; red log `6a6ce086…` lists `test_flat_install_stamp_matches_the_current_executor`, `…_reports_skew_with_the_remedy`, `…_matches_a_newer_executor`, `…_without_a_stamp_cannot_check`, `…_with_an_unreadable_stamp_cannot_check`, `…_with_a_versionless_stamp_cannot_check` **(re-read, job log)** |
| D2 the reason says what was probed; the lane text states the sources once | shipped-as-specified | `_unreadable_lane_text_reason` (flat: the stamp path; versioned; nested; unresolved) and `SKILL.md` § executor-skew; `test_source_checkout_still_cannot_check` is red in the same run |
| D3 the verdict is proved through the executor under the OpenCode runtime signal | shipped-as-specified | three tests through the executor (`match`, the stale-executor `skew`, `could_not_check` without a stamp), all red in the same run |

Claimed `deliverables_done=3` of 3; agrees.

**Labels.** The landing calls the evidence `test-first` and says the failing run is "worktree base `deb26f634` with the production
change reverted". That is the base with the fix removed, which is a revert-after run, not a run made before the fix existed.
The substance is the same (ten tests red without the change). It also lists `test_source_checkout_still_cannot_check` as a
regression guard "green at base by design" in the D1 row while the red log shows it failing; the test pins the new reason text
(a D2 clause), so the D1 row mislabels it. The lane's caveat that the fixture module "writes its own minimal `SKILL.md`" and so
does not exercise the real emitter output is accurate and was in my spec's wording ("built from the real emitter output").

**Surface.** The PR edits `marketplace/targets/sync.py`, `antigravity/templates/install.sh` and
`test/marketplace/targets/antigravity/test_emitter.py`, outside the declared surface, so that Antigravity publishes an install
stamp (CodeRabbit's finding: without it the new leg could not answer on the one other flat target). Disclosed, including that the
domain skills for that module were not loaded; the change mirrors the OpenCode root-asset pattern line for line.

## Findings by the orchestrator

- **Questions** **(store)**: three `question` calls (14:05Z, 15:33Z, 17:57Z) = the landing's three (executor-skew; the review
  round limit; the Sonar override).
- **Sub-agents** **(store)**: four `subagent` calls (14:59Z, 15:11Z, 15:23Z, 15:42Z), four child sessions, all completed = three
  self-review rounds plus the operator-authorized verification round.
- **Guard** **(re-read)**: `guard.log` holds three R1 lines, all in review children (`cd … && grep|sed`, `&& echo`, a
  `git status … | head`) = the landing's three, which it counts against the run.
- **Shell read-class calls** **(store)**: `tail` 5, `wc` 2, `du` 1 = 8, the landing's eight (it splits them 4/3/1).
- **Identity** **(store)**: none. **Restarts** **(store)**: none. **Main-checkout edits** **(store)**: 0. Main is clean **(re-read)**.
- **Relative `--project-dir`** (landing §7): one build was submitted with a relative path and fell back to `pwx`; every later
  build used an absolute path and ran routed. The known trigger, hit once and learned from within the run.
- **Executor interference** **(re-read, execution log)**: no `generate_executor generate` between 12:04Z and the end of the run.
- **PR threads** **(re-read)**: two review threads, six comments, all resolved. CodeRabbit's findings: Antigravity publishes no
  install stamp (fixed in `1375d5ba4`), two nitpicks (fixed), and on the merged head `bundle-components.json` missing from
  `root_assets` for both flat targets, answered as pre-existing and withdrawn by the reviewer.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `f9147f97e`, the merged head (`sourceCommitId = coveredCommitId`,
  `kind = reviewed`); no standing authorization needed. Sourcery approved `c057574f1` and `f9147f97e`.
- **CI**: `verify` failed once on `FRESHNESS SUSPECT` from the duration heuristic (208 files/s over the 200 ceiling) and was
  green on rerun. That is the false failure LB-93 D3 fixes, seen on LB-98's PR while LB-93's fix was not yet on
  its base. It confirms that the false failure was real and recurring.
- **Sonar**: never decidable on this PR either (five attempts, `analysis_revision_unavailable`); the operator chose to proceed.
  The lane's residue 1 gives the cause; see the epic's Sonar entry.

## Open Items

- Residue 1 (the lane's): Sonar gate unattainable. `.github/project.yml` has `sonar.enabled: false`, so CI submits no PR
  analysis, while the project's provider block resolves `sonar: configured`. Verified here (below in the epic): the provider
  holds three PR analyses, the newest from 2026-06-29.
- Residue 2: `bundle-components.json` is not a synced root asset for either flat target while both installers copy it, so a
  sync-installed flat tree falls back to heuristic bundle discovery; pre-existing, needs its own plan.
- Residue 3: two `test_harness_shape_guards.py` meta-tests time out locally under xdist; green serially and on CI.
- The fix is source-only until the next `/sync-harnesses`, an executor regeneration and, for Claude, a repin. After that a flat
  OpenCode or Antigravity install should answer `match` or `skew` and stop asking.
- The stamp is written once per sync, so an in-place edit of an installed lane text is invisible to the check; recorded in the
  probe's docstring and in `SKILL.md`.
- **Added after the sync (2026-10-27):** verified on this machine's installed flat tree at `0.1.2025`: the installed lane
  copy reads `0.1.2025` from the stamp, returns `skew` for the `0.1.2021` executor and `match` after the regeneration. In this
  repository's own lanes, however, the executor maps `runbook_lane` to the source tree, which is a "nested, no version
  directory" layout, so the check still answers `could_not_check` there (with the new reason). The lane's own pre-flight said
  so ("the reading checkout is a source tree"). The question therefore remains in this repository's lanes; see the epic's
  Open Defects. My spec's reproduction claim (an `OPENCODE=1` call selecting the flat copy) was wrong: it ran the source copy.

## Reconciliation actions

- Row PLAN-LB-98: `shipped`, pr `1876`, landing `landings/PLAN-LB-98.md`, plan id `rb-lb-98-flat-install-executor-skew`.
- Inbox message `rb-lb-98-flat-install-executor-skew-001.md` archived.
- Epic: queue annotation, the Open Defect closed in source, Decisions entry, model-comparison entry.
