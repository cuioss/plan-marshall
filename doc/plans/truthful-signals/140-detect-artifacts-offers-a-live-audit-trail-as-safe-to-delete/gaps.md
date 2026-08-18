# Gaps — 140-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete

**Source:** verification.md (same directory)   **Open items:** 4

## G1 — Close the `--no-gitignore` hole in the live-plan invariant

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:652` — `scan_artifacts` (and `cmd_detect_artifacts`, line 723); the false absolute is at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md:100`
- **What is wrong:** the nested-boundary pruning never applies to the scan **root** itself. During phase-5+ the working directory is pinned to the plan's own worktree and `cmd_detect_artifacts` defaults `--root` to `Path.cwd()`, so the plan's own checkout *is* the scan root. Executing `scan_artifacts(<plan worktree>, respect_gitignore=False)` against a tree holding the production plan state returns `safe = ['.mypy_cache/3.11/b.json', '.plan/local/plans/EXAMPLE-PLAN/logs/work.log', 'scratch2.temp']` — the running plan's live audit trail offered for deletion. With gitignore on it is excluded only because `.plan/*` happens to be ignored, which is precisely the dependency D3 was written to remove ("whichever direction D2 takes").
- **Why it matters:** `SKILL.md:100` instructs the agent "For safe artifacts, delete them" and documents `--no-gitignore` as a supported flag. One `detect-artifacts --no-gitignore` from inside a plan's worktree reproduces the exact data-loss path this plan exists to close, and `SKILL.md:100` tells the reader it cannot happen ("Between the two mechanisms a plan's finalize never offers the run's own live artifacts").
- **Fix:** make the exclusion of plan-runtime state unconditional in `scan_artifacts` rather than a consequence of gitignore — e.g. drop any relative path whose first segment is the plan-state directory (`.plan/`), or resolve the active plan directory via the existing `file_ops.get_base_dir()` / `get_plan_dir()` helpers and exclude it, applied before the `respect_gitignore` branch so `--no-gitignore` cannot defeat it. Then correct `SKILL.md:100` so the sentence describes what the code guarantees.
- **Done when:** a test in `test/plan-marshall/workflow-integration-git/test_git_workflow.py` builds a repo whose scan root is the plan's own worktree, places `.plan/local/plans/{id}/logs/work.log` under it, calls `scan_artifacts(root, respect_gitignore=False)`, asserts `work.log` is in neither `safe` nor `uncertain` **and** that a control artifact is in `safe`; and reverting the new exclusion turns that test red.
- **Module/topic:** `plan-marshall:workflow-integration-git` — `detect-artifacts` classification

## G2 — Give the prefix-aware gitignore exclusion a test that fails without it

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/plan-marshall/workflow-integration-git/test_git_workflow.py:946` — `TestDetectArtifactsLivePlanArtifacts::test_gitignored_worktree_contents_excluded_per_contract`; code under test at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:641` — `_is_ignored`
- **What is wrong:** the test's docstring names the exact-match defect ("the collapsed `.plan/local/worktrees/EXAMPLE-PLAN/` entry does not exclude its descendants"), but its fixture is a nested git worktree, which `_is_nested_git_boundary` prunes before the ignore test runs. Reverting `scan_artifacts` to the pre-fix exact-string membership test (`rel.replace(os.sep,'/') in ignored_files`) leaves the whole file green: **96 passed, 0 failed**. Removing the boundary pruning instead turns 3 tests red — so every live-plan test in the class is pinned by pruning alone. The `ignored_dirs` prefix branch has no integration coverage at all; measured on git 2.43.0, a trailing-slash entry is emitted *only* for a nested git repository (a plain fully-ignored directory such as `build/` is still enumerated file-by-file), and every such directory is pruned first — so the branch is currently unreachable from `scan_artifacts`.
- **Why it matters:** the report presents this test as the verification of D5(a)/D2 direction (a). A test that passes against the defect it names is the epic's namesake failure, and it means the prefix-aware exclusion could be deleted or broken by a future refactor with no signal.
- **Fix:** either (i) add an integration test that reaches the prefix branch without the boundary — construct the ignored-directory entry deterministically, e.g. by monkeypatching `git_workflow.get_gitignored_files` to return `{'ignored-tree/'}` for a plain (non-repo) ignored directory containing a matching artifact, and assert nothing under `ignored-tree/` is offered; and rename/rescope `test_gitignored_worktree_contents_excluded_per_contract` so its docstring names the mechanism it actually pins — or (ii) if the prefix branch is judged genuinely unreachable, delete `_split_ignored`/`_is_ignored` together with `TestIgnoreExclusionHelpers` and state in the `scan_artifacts` docstring that the collapsed-directory case is handled by boundary pruning alone.
- **Done when:** reverting the exclusion test in `scan_artifacts` to the pre-fix exact-string form makes at least one test in `test_git_workflow.py` fail — or the code path and its unit tests are removed and the docstring no longer claims a mechanism the tree does not exercise.
- **Module/topic:** `plan-marshall:workflow-integration-git` — `detect-artifacts` tests

## G3 — Correct the `get_gitignored_files` docstring: it uses `git ls-files`, not `git check-ignore`

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:534` — `get_gitignored_files`
- **What is wrong:** the docstring reads *"Uses `git check-ignore` to respect .gitignore rules"* while line 539 runs `['git', 'ls-files', '--others', '--ignored', '--exclude-standard']`. Introduced by `87c677bb` (#823); this plan re-documented the surrounding contract and left it. The two commands differ in exactly the property this plan turns on — `git ls-files` collapses a nested-repository directory to a single trailing-slash entry, while `git check-ignore` answers per queried path and never collapses.
- **Why it matters:** a reader debugging the exclusion behaviour (the audience this plan created) is pointed at the wrong command and would not find the collapse mechanism the fix is built around; it also makes the `_split_ignored` rationale (line 626, which correctly names `git ls-files`) read as contradicting the function it partitions.
- **Fix:** replace the sentence with one naming the actual command and its two relevant properties — `git ls-files --others --ignored --exclude-standard`, which enumerates ignored files individually but reports a nested repository as a single trailing-slash directory entry — and keep the existing "returns empty set if not inside a git repo or git is unavailable" clause.
- **Done when:** the docstring names `git ls-files` and no occurrence of `check-ignore` remains in `git-workflow.py`.
- **Module/topic:** `plan-marshall:workflow-integration-git` — `detect-artifacts` documentation

## G4 — State the unconditional nested-boundary skip where `--no-gitignore` is documented

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:2025` — the `--no-gitignore` argparse `help=`; and `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md:285` — the `--no-gitignore` parameter line
- **What is wrong:** both say only "Include gitignored files in results". Since `fb41f014` the nested git repository/worktree skip is unconditional — `--no-gitignore` does **not** make a nested worktree's contents appear. Both strings promise a completeness the flag no longer delivers.
- **Why it matters:** these are the two places a caller reads before passing the flag; a user who passes `--no-gitignore` expecting the full untracked set gets a silently narrower one, and has no documented reason why.
- **Fix:** extend both strings, e.g. "Include gitignored files in results (nested git repositories and worktrees are still never traversed)".
- **Done when:** `git-workflow.py:2025` and `SKILL.md:285` both mention that the nested-boundary skip is unaffected by the flag.
- **Module/topic:** `plan-marshall:workflow-integration-git` — `detect-artifacts` documentation
