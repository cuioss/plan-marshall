envelope_version=1
sender_type=plan
sender_id=oc-lb-64-lb-50-completion
epic=live-blockers
kind=landing
created=2026-10-17T13:31:30Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-64-lb-50-completion
epic=live-blockers
pr=#1794
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/unknown
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

# Landing: PLAN-LB-64 (lb-64-lb-50-completion)

Spec: `.plan/orchestrator/live-blockers/plans/PLAN-LB-64-lb-50-completion.md`
Branch `fix/lb-64-lb-50-completion` → merged to main as `24475924b51250807ef5cdab6d61e4e7b827882d` (PR #1794).

## 1. Deliverables

### D1 — the bridge has its own file, and setup never writes the installed target rules

- **Done when — setup over a fixture holding the full emitted rules leaves that file byte-identical and writes the bridge to its own path: MET.** `test_project_initial_setup_never_writes_installed_target_rules` (`test/plan-marshall/platform-runtime/test_opencode_runtime.py`, `test_antigravity_runtime.py`). Failing at base (logs `python-2026-10-17-070619.log`, `-070724.log`): the installed file was replaced by the two-line bridge stub and `bridge_written` was False. Passing after: opencode 122 (`-071339.log`), antigravity 60 (`-071442.log`). Commit `44599ce8b`.
- **Done when — a fixture whose target-rules file holds the stub is reported as clobbered, with the restore command: MET.** `test_configure_harness_reports_clobbered_target_rules` (`test/plan-marshall/marshall-steward/test_harness_config.py`) asserts `installed_rules_clobbered is True`, `installed_rules_restore_command == './install.sh --emit-rules'`, and the stub byte-preserved. Base: `KeyError: 'installed_rules_clobbered'` (`-070357.log`). Passing: steward 23 (`-071842.log`). Commit `44599ce8b`.
- **Done when — the steward verdict for full rules plus a present bridge is `current`: MET.** `test_configure_harness_full_rules_with_bridge_is_current`. Base: `assert 'damaged' == 'current'` (`-070357.log`). Passing: steward 20 (`-071233.log`). Commit `44599ce8b`.
- Doc surface: `antigravity-rules.md` §7 and the HYPOTHESIS file `opencode-rules.md` §5 now describe the two files (installed `plan-marshall-target-rules.md` vs bridge `plan-marshall-standing-rules.md`); `upgrade-flow.md` names the clobber surfaces.

### D2 — harness setup always runs the setup writers

- **Done when — configure-harness on a fixture with the full install.sh rules (no marker) calls `opencode_enforcement_apply` and `project_install_hook` and reports the bridge verdict: MET.** `test_configure_harness_always_runs_setup_writers` asserts call order `['project_initial_setup', 'project_install_hook', 'opencode_enforcement_apply']` and verdict `current`. Base: `calls == []` — the PLAN-LB-50 early return skipped the writers (`-070357.log`). Passing: steward 23 (`-071842.log`). Commit `9251b2dff`.
- **Done when — the approval warnings are in the returned payload, not only on stderr: MET.** `test_configure_harness_persisted_approval_warnings_in_result` asserts `warnings[0]['pattern'] == 'ls'`. Base: `KeyError: 'persisted_approval_warnings'` with the warning visible in captured stderr (`-070357.log`). Passing: steward (`-071842.log`). Commit `9251b2dff`.
- Setup-failure clause: `test_configure_harness_reports_failed_setup` (a raising setup → `setup_failed: True`, verdict `missing`) and, added during review, `test_configure_harness_stops_writers_when_setup_reports_failure` (a returned non-success status → later writers stop, commit `c531891a7`).
- Review-fix commits on the branch: `0093412a4`, `b6d6309d7` (self-review wording), `a4374ce4b` (CodeRabbit doc fix), `c531891a7` (CodeRabbit decode + writers guard); plus two merges of `origin/main` (`c3eeae0ab`, `f3b105ba7`).

## 2. Hypotheses

- **HYPOTHESIS (spec): `opencode-rules.md` carries the same wrong bridge text as `antigravity-rules.md`: CONFIRMED.** At base, `opencode-rules.md:55-59` said the workspace rules file "is bridged at project setup" — naming `plan-marshall-target-rules.md`, the same defect as `antigravity-rules.md:58-62`. Both corrected.
- The spec's OBSERVED labels were re-verified at base: `_bridge_rules_path` returned `…/rules/plan-marshall-target-rules.md` (`opencode_runtime.py:86-88`, `antigravity_runtime.py:60-62`); `configure_harness.py:128-134` returned `'damaged'` before the setup writers.

## 3. Findings

Self-review (subagent, 3 rounds, RUNBOOK §5):
- Round 1: all Done-whens met; findings — rules docs overstated `--emit-rules` as the only writer; the dispatch docstring overstated the hook/enforcement; the upgrade-flow pointer was incomplete; the healed-stub outcome was unpinned → fixed in `0093412a4`.
- Round 2: PASS; closed the emit-path docstrings and the stale "settings/grant surface" phrases in `b6d6309d7`.
- Round 3: PASS (delta was docstring-only; all four commit subjects/trailers exact).

CI:
- On the merged head `c3eeae0ab` the first run failed `verify / verify` on the **test-compile freshness backstop** — mypy reported success over 1759 files in 8.671 s = 203 files/s against a 200 files/s ceiling, with no type error (0.12 s margin). `ci checks rerun --run-id 39022911935` → green (1381 s). Not a code failure.

PR comments — CodeRabbit raised six; every one handled:
1. `upgrade-flow.md` "not healed" self-contradiction → **fixed** (`a4374ce4b`); thread resolved.
2. The clobber report's restore command should target the consumer project → **replied not-applicable** (PLAN-LB-64 D1 prescribes `install.sh --emit-rules`; the installer's absolute path is not knowable across curl-pipe and retained-global installs); thread resolved; carried as residue.
3. `UnicodeDecodeError` escapes `installed_rules_clobbered` on a non-UTF-8 installed rules file (both runtimes) → **fixed** (`c531891a7`): `errors='replace'` in both `installed_rules_clobbered` functions and in the bridge reconcile, with tests; thread resolved.
4. A bridge-write failure should be reported as a setup failure (inline opencode + outside-diff antigravity) → **replied not-applicable**: a failed write leaves the bridge absent or markerless and the post-setup verdict reports `missing`/`damaged` plus the re-emit command; making the write raise would leave `damaged` unreachable in production, which PLAN-LB-64 D1 requires it to be. Thread resolved; carried as residue.
5. Later writers still run when `project_initial_setup` **returns** a non-success status → **fixed** (`c531891a7`): both later writers guarded by `setup_ok`, with a test.
- cuioss-review-bot raised no findings (guides only).
- sourcery was unavailable (see Reviewers).

## 4. Reviewers

- **cuioss-review-bot (required): reviewed.** Head reviewed: `f3b105ba7` ("Review updated until commit …f3b105ba7", 12:11Z; no findings). Triggered with `/review` on every push (08:36Z, 08:57Z, 09:49Z, 10:59Z, 12:09Z).
- **coderabbit (required): reviewed.** Head reviewed: `f3b105ba7` (coverage `sourceCommitId = coveredCommitId = f3b105ba7`, 13:03Z, "No actionable comments were generated in the recent review"). History: reviewed `b6d6309d7` (08:39Z, 2 comments), refused 08:57Z ("review limit reached", reset in 37 min), reviewed `a4374ce4b` (09:40Z, clean) after a 700 s + 33 s + 191 s `ci pr wait-for-comments` wait and a re-trigger, refused 09:55Z (reset in 41 min), reviewed `c3eeae0ab` (10:49Z, 4 comments) after a 2053 s wait, refused 10:59Z and 12:10Z, reviewed `c531891a7` (11:55Z, clean) after a 1116 s wait, reviewed `f3b105ba7` (13:03Z, clean). No quota step (2) or (3) was needed; no operator question was asked.
- **sourcery (optional): refused.** "You've used your own review budget of 250,000 diff characters for the last 7 days … another review in 2 days and 16 hours." No action was available for an optional reviewer.

## 5. Operator questions

None. No blocking condition, no rule bend, and no unavailable required reviewer arose, so the operator was never consulted (the `question` tool was not used).

## 6. Rule check

- `.plan/temp/guard.log` does not exist — there is no guard-log line for this run's sessions, so no guard refusals are listed.
- Disclosed deviations (no Section 1 rule knowingly broken):
  - PR and PR-comment bodies were written to the CI tool's own script-allocated slots under `.plan/local/plans/NO_PLAN/work/ci-bodies/` (the mechanism RUNBOOK §6.1 prescribes) rather than `.plan/temp/`; apart from those slots, every `.plan/` write was a `.plan/temp/` file or the single inbox message.
  - `git worktree remove` (the prescribed cleanup command) refused because the worktree carried environment churn (the worktree-prep `uv.lock` bump and untracked build outputs); the removal used `git worktree remove --force`. `--force` on worktree removal is not in the forbidden set (only `git push --force`/`--force-with-lease` are), and the discarded content was tool-generated, uncommitted, and on an already-merged branch.
  - Timestamps were read with `date -u` (not a forbidden command).
- Model: the session model was `deepseek-v4.1-flash` (provider `opencode-go`); its variant was not readable, so the facts block records `deepseek-v4.1-flash/unknown`. Three `general` sub-agents were dispatched for self-review; their pinned models were not recorded by this session and are therefore not listed.
- Commit trailers: every commit on the branch, including both merges, ends with exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`; the PR body carries no attribution footer.

## 7. Residue

- Two CodeRabbit notes were dispositioned not-applicable and carried as follow-up candidates: (a) the clobber report names the canonical `./install.sh --emit-rules` and cannot identify the installer's absolute path; (b) a bridge-write failure inside an otherwise-successful `project_initial_setup` is reported through the bridge verdict (`missing`/`damaged` + re-emit command), not through `setup_failed`.
- `doc/developer/opencode.adoc:272` still claims `OpenCodeRuntime.opencode_enforcement_apply()` is invoked; no production runtime defines that method (the D2 test drives a fake runtime). Outside this spec's scope.
- The clobber detector is a marker heuristic: an emitted rules file containing a literal `bridge-version: N` would false-positive (none does today).
- The `verify` test-compile freshness backstop is machine-speed-calibrated (200 files/s ceiling vs 71 files/s measured cold) and produced one 0.12 s-margin false positive on CI; a rerun cleared it.
- The worktree's `uv.lock` ruff bump (0.16.10 → 0.17.1) was worktree-prep churn; never committed; discarded with the worktree.
