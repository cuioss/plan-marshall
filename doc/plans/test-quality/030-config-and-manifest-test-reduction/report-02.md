# Run report — 030-config-and-manifest-test-reduction (run 02)

**Date (UTC):** 2026-08-16    **Branch:** `chore/config-manifest-test-reduction-02`    **PR:** —    **Outcome:** partial

A continuation run over the residue run 01 recorded. Run 01 landed D5 and D6 complete, D4 and D1
partial, and D2/D3 not started. **This run completes D4 and starts nothing else** — see the durability
failure below for why D1 did not proceed.

## Operator scope decision

The residue was re-measured before any work (see **Findings** F1) and put to the operator, because
"everything outstanding" measures far larger than run 01's summary implies. The operator scoped:

- **This PR:** D4 to completion, plus D1 across the three largest modules — the plan's own stated
  priority under a tight budget (§ Notes, "The largest single win in this slice is D1").
- **D2 for the campaign:** all 39 over-budget modules, not the 8 the plan names as a lead. This is a
  campaign-level decision recorded here so the follow-up plan inherits it; **no D2 work is in this PR.**

**D1 was not reached.** The operator's scope is therefore only half delivered, and that is a shortfall
of this run, not a re-scope.

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded as the first action)
- Plan read from `doc/plans/test-quality/030-config-and-manifest-test-reduction/plan.md`

Conditional skills for the Python-test surface were **not** loaded from the bundle paths in this run;
the conversions follow the shared-loader API documented in `test/conftest.py` itself. Recorded as not
done rather than claimed.

## Deliverables

| Deliverable | State | Detail |
|---|---|---|
| **D4 — one import preamble** | **COMPLETE** — 22 of 22 sites, 15 modules | Commits `e032a64` + `aba82de` |
| **D1 — parametrize the contract tables** | **not started** | Blocked by the durability failure below |
| D2 / D3 | not in this PR | Per the operator scope decision above |

### D4 — complete

All 22 sites across 15 modules converted off bespoke loaders onto the shared `test/conftest.py` API
(`load_script_module`, `get_script_path`, `add_skill_scripts_to_path`, `PROJECT_ROOT`).

**Done-when met.** A grep for `spec_from_file_location` and `Path(__file__).parent.parent.parent` over
the six slice directories returns **zero**. That zero was confirmed against a positive control — the
same glob run for `load_script_module` returns 228 occurrences across 83 files — so it is a real
absence rather than a mis-scoped query.

Line delta across both commits: **+92 / −235** (net −143).

**Every marketplace-script conversion preserves its original `sys.modules` registration name.** This is
the hazard run 01 paid 173 order-dependent failures for: `load_script_module`'s `module_name` defaults
to the script stem, and the marketplace config modules carry mutable module-level default dicts, so
collapsing distinct registration names onto a shared one makes previously-isolated modules share state.

**Two sibling-fixture loads were deliberately collapsed onto one shared registration.**
`test_classify_affected_files.py` and `test_manage_execution_manifest_compose.py` each loaded
`_execution_manifest_fixtures.py` under a unique name via `spec_from_file_location`; both now use the
bare `from _execution_manifest_fixtures import …`, which is the tree's actual convention (530 uses
across 389 files). This is safe **because it was checked**: that fixture module defines only a class and
four factory functions, with no module-level mutable state — so it is not subject to the hazard above.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → 15 modules changed, so the gate is owed and was run.

- **`./pw quality-gate`** → `issues[0]`, clean across mypy(production), ruff, SPDX, plugin-doctor.
  It first reported 2 ruff `I001` import-sorting errors, which were fixed before the commit.
- **`./pw verify`** (the full gate) → **SUCCESS**, `20322 passed, 14 skipped` in 481s, clean across all
  six dimensions **including `mypy(test)`** — the `test-compile` step that neither `quality-gate` nor a
  pytest run performs.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | This run, re-measurement | D2's scope is **39** modules over the landed 400-line budget, not the ~8 the plan lists. The plan flags its list as a lead to re-derive; re-derived, it is nearly 5× larger. | Reported to operator; scoped into the campaign, not this PR |
| F2 | This run | `_execution_manifest_fixtures.py`'s module docstring documents the import form `from test.plan_marshall.manage_execution_manifest._execution_manifest_fixtures import …`, which **cannot work** — the directories contain hyphens, which are not legal in a Python package path. The tree's real convention is the bare import, which this run adopted at both call sites. | **Open** — the docstring itself is still wrong and was not edited |
| F3 | This run, self-inflicted | Removing `import sys` from `test_get_module_context.py` broke 3 tests: the usage check grepped `sys\.` and missed `monkeypatch.setattr(sys, 'argv', …)`, which has no trailing dot. | Fixed; caught by the targeted run before commit |
| F4 | This run, environment | The session lost git push credentials mid-session. See **Durability failure** below. | **Open** — blocked D1 |

## Durability failure (blocking)

`git push` fails with `fatal: could not read Username for 'https://github.com'`, outside the sandbox as
well as inside. Established, not assumed:

- No credential helper in `.git/config`; no `GITHUB_TOKEN`/`GH_TOKEN` in the environment.
- The session's git proxy serves **reads** only — `git fetch origin main` succeeds throughout.
- `add_repo` with `access: push` returns `already_present`, pointing at `/workspace/plan-marshall`,
  which **does not exist**. The attach record is stale and attaches no credentials.
- Earlier in this same session, 16 commits were pushed successfully to a different branch, so the
  credentials were present and were lost mid-session rather than never having existed.

The GitHub MCP API is therefore the only write path. It works — `create_branch` created this run's
branch from `main` at `8872700`. But its file-write calls take **full file contents as a parameter**, so
every push costs the whole text of every changed file through the agent's context: ~175 KB for D4's 15
files against a 327-line diff.

**Why D1 did not proceed.** D1's three target modules total ~10,300 lines
(`test_manage_execution_manifest_compose.py` 5,355, `test_config_defaults.py` 3,662,
`test_decision_rules.py` 1,290). Parametrizing them requires reading them and then pushing them back —
both through the agent's context, and neither affordable under this constraint. Starting D1 and failing
to land it would have been worse than not starting it.

### The work is preserved as patches

The two D4 commits exist locally (`e032a64`, `aba82de`) on a VM that does not survive a reclaim, so they
were shipped to the branch as patch files instead:

| File | Covers |
|---|---|
| `wip-d4-import-preambles.patch` | Commit `e032a64` — 10 modules |
| `wip-d4-import-preambles-part2.patch` | Commit `aba82de` — 7 modules (2 overlap part 1) |

**Apply part 1 then part 2** — part 2's diff is computed against the post-part-1 tree. Both are
`git am`-able. **Delete both files after applying**: they are a durability workaround, not deliverables,
and must not reach `main`.

## Reviewer participation

Not applicable — **no PR was opened**, so no reviewer was invited and no coverage figure exists. This is
a shortfall to disclose, not a clean sheet: the § Step 7 participation table and the § Step 8 coverage
disclosure were never reached.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not recorded per-step. The two build gates took ~8 minutes (`verify`) and ~1 minute
  (`quality-gate`).
- **Population:** would be this single Claude Code cloud session's usage. Not comparable to a
  plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a
  different billing boundary.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Partial** — the lane was loaded; the conditional Python-test skills were not |
| 2 Branch | **Done** — `chore/config-manifest-test-reduction-02`, on `origin`, cut from `origin/main` |
| 3 Plan directory | **Done** — already established by run 01; resumed, not re-established |
| 4 Implement | **Partial** — D4 complete, D1 not started |
| 4 Per-commit gate | **Done** — `./pw quality-gate` clean before each `*.py` commit |
| 4 Pushed | **FAILED** — no commit could be pushed; content carried to the branch as patches instead |
| 5 Build gate | **Done** — full `./pw verify` SUCCESS |
| 6 Verification sub-agent | **NOT DONE** — no PR was being opened, and the run stopped before this gate |
| 7 PR cycle | **NOT DONE** — no PR exists |
| 8 Merge gate | **NOT DONE** — not reached |
| 9 This check | Done (this section) |

**GitHub access path:** GitHub MCP server (no `gh` CLI; local git push unavailable).

**Branch form:** run-created, `chore/` prefix from the closed set. The harness-assigned
`claude/config-manifest-test-reduction-0eod0y` was **not** reused: its PR is merged, the merged-PR rule
forbids stacking new work on merged history, and without push credentials the branch could not be
force-reset to `main`. The deviation from the lane's keep-the-assigned-branch rule is deliberate and
recorded here.

A cloud run never owes a `/sync-plugin-cache`; no `marketplace/bundles/**` file was touched in any case.

## What have we learned (Step 9)

**Proposed contract change: the lane assumes `git push` works, and says nothing about what to do when it
does not.** § Step 2 makes "the branch exists on `origin`" an absolute precondition and § Step 4 makes
per-commit push the durability mechanism, but every one of those instructions is a `git push`. This run
found that a cloud session can lose push credentials *mid-run* while the GitHub MCP write API keeps
working — a state the contract does not name, in which the durability rule is unsatisfiable as written
while durability itself is still achievable by another route.

The concrete gap: the lane's own § Cloud session affordances table lists the MCP server as the GitHub
path but treats it as a *review/merge* surface, never as a *write-the-tree* surface. It does not record
that `create_or_update_file`/`push_files` take full file contents, which makes them viable for a small
diff and prohibitive for a large one — the exact trade-off that decided what this run could deliver.

**Not self-approved.** Presented to the operator for a decision; if accepted it ships as a separate
`chore/` PR touching only the skill, per § Step 9.

## Residue

- **D4:** none — complete.
- **D1:** ~100 families, including `test_decision_rules.py`. The operator scoped the three largest
  modules into this PR; they were **not** done.
- **D2:** 39 modules over the 400-line budget — operator-scoped to the campaign.
- **D3:** not started; the `parse_ns` exception list remains empty **by non-attempt**.
- **F2:** the false import path in `_execution_manifest_fixtures.py`'s docstring is still there.
- The line-floor recommendation for `040`–`080` from run 01 stands, and F1 strengthens it: this plan's
  D2 scope was under-derived by the same margin its line floor was.

**Next session needs:** working git push credentials. Apply both patches, delete them, then D1.
