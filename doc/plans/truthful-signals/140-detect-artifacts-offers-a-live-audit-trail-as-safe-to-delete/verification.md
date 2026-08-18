# Verification — 140-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete

**Verified against:** commit `0314cc4db5fa28fa8b478334c35583a0262060b7`   **Landed as:** PR #1171, commit `fb41f0148babfb57cff5324b8c756102371f482a`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding list is distinguishable from an empty check:

**Read.** `plan.md` and `report-01.md` in full. The landed squash commit `fb41f014` (`git show --stat`, then the full diff for each of the three source files). At HEAD: `git-workflow.py` lines 531-742 (`get_gitignored_files`, `_is_nested_git_boundary`, `_split_ignored`, `_is_ignored`, `scan_artifacts`, `cmd_detect_artifacts`), its argparse declaration (lines 2017-2028), `SKILL.md` lines 97-100 and 273-296, `standards/artifact-patterns.json`, `test_git_workflow.py` lines 71-95 and 902-1050, `.gitignore`, `tools-file-ops/scripts/file_ops.py` (`get_base_dir`, `_resolve_plan_root`), `script-shared/scripts/marketplace_paths.py` (`resolve_main_anchored_path`), `ref-workflow-architecture/standards/artifacts.md`, `git_provider.run_git`.

**Executed (git, git 2.43.0).** Built controlled temp repositories and ran `git ls-files --others --ignored --exclude-standard` to re-derive the collapse mechanism the plan's premise rests on — independently confirming (a) an individually-ignored file is enumerated (`.plan/local/plans/EXAMPLE-PLAN/logs/work.log`), (b) a linked worktree collapses to one trailing-slash entry (`.plan/local/worktrees/EXAMPLE-PLAN/`), and (c) in a repo with `build/` and `ignored-dir/` ignored, plain ignored directories are still enumerated file-by-file — **only a nested git repository ever produces a trailing-slash entry**.

**Executed (the real function).** Loaded `git-workflow.py` through `test/conftest.py`'s `load_script_module` and ran `scan_artifacts` against purpose-built trees:
- scan root = main repo, live worktree nested at `.plan/local/worktrees/EXAMPLE-PLAN/` → `{'safe': ['scratch.temp'], ...}`; no worktree path offered.
- scan root = the worktree itself, plan state at the production location `<worktree>/.plan/local/plans/{id}/logs/work.log` → `{'safe': ['.mypy_cache/…', 'scratch2.temp']}`; `work.log` excluded.
- same tree, `respect_gitignore=False` → `{'safe': ['.mypy_cache/…', '.plan/local/plans/EXAMPLE-PLAN/logs/work.log', 'scratch2.temp']}` — **the running plan's own work log offered as safe-to-delete.**
- scan root outside any repo → `get_gitignored_files` returns `set()`, everything matching a pattern offered (residue item confirmed still open).

**Tests.** `uv run python -m pytest test/plan-marshall/workflow-integration-git/test_git_workflow.py -o addopts="" -q` → `96 passed` at HEAD.

**Mutations (both restored from saved bytes; `git status --porcelain` re-checked, md5 of the restored file equal to the pre-mutation md5).**
- **Mutation A** — reverted the exclusion test in `scan_artifacts` to the pre-fix exact-string form (`rel.replace(os.sep,'/') in ignored_files`), keeping boundary pruning: **96 passed, 0 failed.** No test detects the removal of the prefix-aware exclusion.
- **Mutation B** — removed the nested-boundary pruning, keeping prefix-aware exclusion: **3 failed, 93 passed** (`test_live_plan_worklog_never_offered_as_safe`, `test_exposure_derivation_nonempty_and_excludes_live_member`, `test_worklog_excluded_independent_of_gitignore`).

**Re-derived counts.** The D4 caller population (`grep -rnE 'detect-artifacts|detect_artifacts|scan_artifacts'` over the tracked tree, `.plan/` excluded) → 8 files at HEAD, of which one (`doc/plans/.../210-…/report-01.md`) post-dates this run and two are this plan's own files; that is the report's 6 files plus the later report and this plan's own `report-01.md`. Test count at the landed commit: 79 `def test_` + 2 `parametrize` decorators, consistent with the reported 95 collected; 80 defs / 96 collected today after two later commits (`60e5fd81`, `d3ba81fd`).

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: re-establish the defect at HEAD, derive exposure | contract text and behaviour quoted from source; exposure derived with method stated | yes | yes | yes | yes | Contract at `SKILL.md:100`, `SKILL.md:276`, `git-workflow.py:652` docstring. Collapse mechanism independently reproduced: `git ls-files --others --ignored --exclude-standard` in a temp repo returns `.plan/local/worktrees/EXAMPLE-PLAN/` for a linked worktree and enumerates plain ignored files individually. STOP CONDITION correctly not triggered. |
| D2 | Decide direction, record why | one direction chosen, rationale recorded | yes | yes | yes | yes | Direction (a) recorded in `report-01.md` § "Direction chosen (D2)"; implemented as `_split_ignored`/`_is_ignored` (`git-workflow.py:626,641`) plus the doc alignment in `SKILL.md:100,276`. |
| D3 | An active plan's own artifacts are never offered | invariant holds and is pinned by a test | partly | **no** | **no** | **no** | Holds for the nested case (`_is_nested_git_boundary`, `git-workflow.py:613`; mutation B → 3 red). Fails when the plan's own worktree is the scan root and `--no-gitignore` is passed: executed `scan_artifacts(<worktree>, False)` → `safe` contains `.plan/local/plans/EXAMPLE-PLAN/logs/work.log`. `SKILL.md:100` states the invariant without that condition. |
| D4 | Find the callers; latent or active | caller set derived, not sampled, with query stated | yes | yes | yes | yes | Query re-run at HEAD; only behavioural consumer is `SKILL.md:100` ("For safe artifacts, delete them"). `test/conftest.py` and `persona-plan-marshall-agent/standards/argument-naming.md` are documentation mentions. **Latent** confirmed. |
| D5(a) | Gitignored path excluded per the contract | test holds, seen red first | yes (test exists) | **no** | **no** | no | `test_gitignored_worktree_contents_excluded_per_contract` (`test_git_workflow.py:946`) survives mutation A — the exact pre-fix defect its own docstring names — because boundary pruning covers the same fixture. Nothing in the suite exercises the prefix-aware exclusion inside `scan_artifacts`. |
| D5(b) | A live plan's own `logs/work.log` is never in `safe` | test holds, seen red first | yes | yes | yes | yes | `test_live_plan_worklog_never_offered_as_safe` (`test_git_workflow.py:917`); mutation B turns it and two siblings red with the message `live plan's work.log offered as safe without gitignore: ['nested-wt/logs/work.log', 'scratch.temp']`. Genuinely non-vacuous. |
| D5(c) | Exposure derivation asserted non-empty with a known member | test holds, seen red first | yes | yes | yes | yes | `test_exposure_derivation_nonempty_and_excludes_live_member` (`test_git_workflow.py:976`) asserts `result['safe']` truthy **and** `'scratch.temp' in result['safe']` before the negative. Red under mutation B. |

**D3.** `git-workflow.py:689-696` prunes `dirnames` at a nested git boundary, which never applies to the scan root itself. When a phase-5+ task runs `detect-artifacts` from its pinned worktree cwd, `cmd_detect_artifacts` (`git-workflow.py:725`) defaults `root` to `Path.cwd()` — the worktree. In that configuration the only thing keeping the plan's own `.plan/local/plans/{id}/logs/work.log` out of `safe` is `.gitignore`; `--no-gitignore` removes it. Verified by execution, not by reading. The report's D3 row asserts the invariant "holds with `respect_gitignore=False` (pinned by `test_worklog_excluded_independent_of_gitignore`)"; that test (`test_git_workflow.py:1004`) covers only the *nested* worktree, so it does not support the unconditional claim.

**D5(a).** The test's own docstring names the defect it is supposed to catch: *"Red pre-fix: the collapsed `.plan/local/worktrees/EXAMPLE-PLAN/` entry does not exclude its descendants."* Restoring exactly that defect (mutation A) leaves the whole file green. The test was genuinely red pre-fix — both mechanisms were absent then — but it pins the boundary-pruning mechanism, not the gitignore one. Compounding this: my git probes show a trailing-slash entry is emitted *only* for a nested git repository, and every such directory is pruned before the ignore test is reached, so the `ignored_dirs` prefix branch of `_is_ignored` (`git-workflow.py:649`) is currently unreachable from `scan_artifacts`. It is defensible as defence-in-depth, but it is untested and unobservable, and the report presents it as the D2(a) fix that D5(a) verifies.

## Report accuracy

Re-derived at the moment of statement:

- **CONFIRMED** — the three contract-text locations quoted in § "The defect" all exist and read as quoted (`SKILL.md:100`, `SKILL.md:276`, `scan_artifacts` docstring).
- **CONFIRMED** — "plain gitignored files and plain gitignored directories are enumerated individually … a nested git worktree collapses to a single trailing-slash entry." Independently reproduced on git 2.43.0.
- **CONFIRMED** — D4's caller set and the **latent** verdict. Only `SKILL.md` Step 3 acts on the list, and it is agent-followed.
- **CONFIRMED** — "10 new tests", "95 tests pass" at the landed commit (79 test defs + 2 parametrize decorators; 96 collected today after two later unrelated commits).
- **CONTRADICTED** — D3 row: *"this holds with `respect_gitignore=False` (pinned by `test_worklog_excluded_independent_of_gitignore`)."* The cited test covers only a worktree nested below the scan root. Executed `scan_artifacts(<plan worktree>, respect_gitignore=False)` returns the plan's own `.plan/local/plans/{id}/logs/work.log` in `safe`. The invariant is conditional, and the report states it unconditionally.
- **CONTRADICTED (in force, not in wording)** — the D5 table's claim that `test_gitignored_worktree_contents_excluded_per_contract` verifies D5(a). The test does not distinguish the gitignore mechanism from boundary pruning; it survives a revert of the former (mutation A). The literal claim "seen red first" is not contradicted.
- **NOT CONTRADICTED, NOT VERIFIABLE** — the branch commits `104b984`, `ee780ed`, `f09eb37` (squash-merged; absent from `main`), the `15982 passed, 1 skipped` figure, and the reviewer-participation table (a GitHub surface, not a tree fact).
- **Unrelated pre-existing drift found while checking D1** — `get_gitignored_files` (`git-workflow.py:534`) documents itself as *"Uses `git check-ignore`"* while it runs `git ls-files --others --ignored --exclude-standard` (line 539). Introduced by `87c677bb` (#823), long before this plan; the plan's own re-documentation pass did not correct it. See gaps G3.

## Out-of-scope compliance

Clean. The landed diff touches five paths: the plan file (a `git mv`), the run report, `workflow-integration-git/SKILL.md`, `workflow-integration-git/scripts/git-workflow.py`, and `test/plan-marshall/workflow-integration-git/test_git_workflow.py` — exactly the "Expected surface". No retention policy was introduced. The `worktree-remove` timeout was not touched: `cmd_worktree_remove` (`git-workflow.py:1392`) still calls `run_git`, whose default `timeout=60` lives in `git_provider.py:29-33` — the out-of-scope item is intact and untouched, as the report states.

## Residue carried forward

| Report residue item | Status in today's tree |
|---|---|
| Non-git-root secondary exposure: a `--root` outside a git repo excludes nothing | **Still open.** Executed `get_gitignored_files(<non-repo tmpdir>)` → `set()`; `scan_artifacts` then offers `a.log` and `sub/b.pyc`. Behaviour unchanged since the landing. |
| Worktree teardown timeout left out of scope | **Still open, correctly out of scope.** Hardcoded 60s default in `git_provider.run_git`. |
| `/sync-plugin-cache` not owed by a cloud run | Not applicable to the tree; nothing to verify. |
| F2 (stray `.git` file treated as a boundary) — rejected | Still true of the code (`git-workflow.py:622`); the rejection rationale is consistent with git's own handling. Not raised as a gap. |
| F3 (`artifact-patterns.json` `_note` silent on the boundary skip) — rejected | Still true (`standards/artifact-patterns.json:2`). The `_note` does describe only the config fields, so the rejection rationale holds on inspection. Not raised as a gap. |

## What could NOT be verified

- The intra-branch commits `104b984`, `ee780ed`, `f09eb37` and the per-commit gate results attributed to them — the PR was squash-merged and the branch is not present in this clone.
- The `./pw verify plan-marshall` figures (`15982 passed, 1 skipped`; quality-gate output) — not re-run; only the single test file was executed.
- The reviewer-participation table, the 1-of-3 coverage disclosure, and the merge-gate condition checks — GitHub state, not tree state.
- The "111,433 entries / 19.9 MB" motivating figure — the plan itself labels it unverifiable from this clone, and the report correctly declines to restate it as its own finding.
- Whether the pre-fix runs were red *for the reasons stated* — pre-fix redness is re-derivable only by mutation, and mutation A shows at least one attribution (D5(a) → the gitignore mechanism) does not hold.
