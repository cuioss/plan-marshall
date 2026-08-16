# Run report — 030-config-and-manifest-test-reduction (run 02)

**Date (UTC):** 2026-08-16    **Branch:** `chore/config-manifest-test-reduction-02`    **PR:** —    **Outcome:** in progress

A continuation run over the residue run 01 recorded. Run 01 landed D5 and D6 complete, D4 and D1
partial, and D2/D3 not started.

## Operator scope decision

The residue was re-measured before any work (see **Findings** F1) and put to the operator, because
"everything outstanding" measures far larger than run 01's summary implies. The operator scoped:

- **This PR:** D4 to completion, plus D1 across the three largest modules — the plan's own stated
  priority under a tight budget (§ Notes, "The largest single win in this slice is D1").
- **D2 for the campaign:** all 39 over-budget modules, not the 8 the plan names as a lead. This is a
  campaign-level decision recorded here so the follow-up plan inherits it; **no D2 work is in this
  PR.**

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded as the first action)
- Plan read from `doc/plans/test-quality/030-config-and-manifest-test-reduction/plan.md`

Conditional skills for the Python-test surface were not loaded from the bundle paths in this run; the
conversions follow the shared-loader API documented in `test/conftest.py` itself. Recorded here rather
than claimed as done.

## Deliverables

| Deliverable | State | Detail |
|---|---|---|
| **D4 — one import preamble** | 15 of 22 sites, 10 modules | Commit `e032a64` |
| **D1 — parametrize the contract tables** | not started in this run | Blocked on the durability failure below |
| D2 / D3 | not in this PR | Per the operator scope decision above |

### D4 detail

Ten modules converted off bespoke loaders onto the shared `test/conftest.py` API:

| Module | Sites | Converted to |
|---|---|---|
| `manage-config/test_effort_read.py` | 3 | `load_script_module` + `add_skill_scripts_to_path` |
| `manage-config/test_cmd_skill_domains.py` | 1 | `PROJECT_ROOT` |
| `manage-execution-manifest/test_parse_verification_command.py` | 2 | `load_script_module` |
| `manage-execution-manifest/test_derive_verification_outcomes.py` | 1 | dead `_REPO_ROOT` removed |
| `manage-execution-manifest/test_no_orphaned_advisory_refs.py` | 1 | `PROJECT_ROOT` |
| `manage-solution-outline/test_get_module_context.py` | 3 | `load_script_module` ×2 |
| `marshall-steward/test_effort_menu.py` | 1 | `load_script_module` + `add_skill_scripts_to_path` |
| `marshall-steward/test_steward_determine_mode.py` | 1 | `load_script_module` + `get_script_path` |
| `marshall-steward/test_default_step_detection.py` | 1 | `load_script_module` + `add_skill_scripts_to_path` ×2 |
| `marshall-steward/test_bootstrap_plugin.py` | 1 | `load_script_module` |

**Every converted call preserves its original `sys.modules` registration name.** This is the hazard
run 01 paid 173 order-dependent failures for: `load_script_module`'s `module_name` defaults to the
script stem, and the marketplace config modules carry mutable module-level default dicts, so
collapsing distinct registration names onto a shared one makes previously-isolated modules share
state.

**Remaining 7 sites, 5 modules:** `test_classify_affected_files.py` (3),
`test_manage_execution_manifest_compose.py` (1), `test_plan31_docs_only_deadlock_regression.py` (1),
`manage-run-config/test_run_config.py` (1), `manage-solution-outline/test_manage_solution_outline.py` (1).

Line delta for the commit: **+61 / −159** (net −98).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → 10 modules changed, so the gate is owed.

**Full `./pw verify` has NOT been run.** Targeted verification only: all ten converted modules plus the
whole `marshall-steward/` directory, via
`uv run python -m pytest <paths> -o addopts=""` → **368 passed**. The lane is explicit that the
narrower calls do not substitute for `./pw verify` (`test-compile` type-checks the test tree and
neither `quality-gate` nor `module-tests` runs it). Recorded as **not done**, not as passed.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | This run, re-measurement | D2's scope is **39** modules over the landed 400-line budget, not the ~8 the plan lists. The plan flags its list as a lead to re-derive; re-derived, it is nearly 5× larger. | Reported to operator; scoped into the campaign, not this PR |
| F2 | This run | `_execution_manifest_fixtures.py`'s module docstring documents the import form `from test.plan_marshall.manage_execution_manifest._execution_manifest_fixtures import …`, which **cannot work** — the directories contain hyphens, which are not legal in a Python package path. The tree's real convention is the bare `from _execution_manifest_fixtures import …` (530 uses across 389 files). | Open — not yet fixed |
| F3 | This run, self-inflicted | Removing `import sys` from `test_get_module_context.py` broke 3 tests: the usage check grepped `sys\.` and missed `monkeypatch.setattr(sys, 'argv', …)`, which has no trailing dot. | Fixed; caught by the targeted run before commit |
| F4 | This run, environment | The session lost git push credentials mid-session. See **Durability failure** below. | Open — blocks the run |

## Durability failure (blocking)

`git push` fails with `fatal: could not read Username for 'https://github.com'`, outside the sandbox
as well as inside. Established, not assumed:

- No credential helper in `.git/config`; no `GITHUB_TOKEN`/`GH_TOKEN` in the environment.
- The session's git proxy serves **reads** only — `git fetch origin main` succeeds throughout.
- `add_repo` with `access: push` returns `already_present`, pointing at `/workspace/plan-marshall`,
  which **does not exist**. The attach record is stale and attaches no credentials.
- Earlier in this same session, 16 commits were pushed successfully to a different branch, so the
  credentials were present and were lost mid-session rather than never having existed.

The GitHub MCP API is therefore the only write path. It works — `create_branch` created this run's
branch from `main` at `8872700`. But its file-write calls take **full file contents as a parameter**,
so every push costs the whole text of every changed file through the agent's context. That is
affordable for this report and roughly affordable for the D4 commit (~4,500 lines); it is **not**
affordable for D1 on the big three, whose modules total ~10,300 lines before any edit.

**Consequence for the operator:** the D4 work is committed locally as `e032a64` and exists only on this
VM, which does not survive a reclaim.

## Reviewer participation

Not applicable yet — no PR has been opened.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not recorded per-step.
- **Population:** would be this single Claude Code cloud session's usage. Not comparable to a
  plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a
  different billing boundary.

## Contract check (Step 9)

Deferred — the run has not reached its merge gate.

Recorded so far: **GitHub access path** — GitHub MCP server (no `gh` CLI in this session; local git
push unavailable). **Branch form** — run-created, `chore/` prefix from the closed set, cut from
`origin/main`. The harness-assigned `claude/config-manifest-test-reduction-0eod0y` was **not** reused:
its PR is merged, the merged-PR rule forbids stacking new work on merged history, and without push
credentials the branch could not be force-reset to `main`. The deviation from the lane's
keep-the-assigned-branch rule is deliberate and recorded here.

## Residue

Everything run 01 recorded, minus the 15 D4 sites closed here:

- **D4:** 7 sites across 5 modules (listed above).
- **D1:** ~100 families, including `test_decision_rules.py`.
- **D2:** 39 modules over the 400-line budget — operator-scoped to the campaign.
- **D3:** not started; the `parse_ns` exception list remains empty **by non-attempt**.
- The line-floor recommendation for `040`–`080` from run 01 stands, and F1 strengthens it: this
  plan's D2 scope was under-derived by the same margin its line floor was.
