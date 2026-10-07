# Run report — 030-config-and-manifest-test-reduction (run 02)

**Date (UTC):** 2026-08-16    **Branch:** `chore/config-manifest-d4-and-d1`    **PR:** #1270    **Outcome:** partial

A continuation run over the residue run 01 recorded. Run 01 landed D5 and D6 complete, D4 and D1
partial, D2/D3 not started. **This run completes D4** and establishes, with evidence, that **D1 as
scoped was already substantially done** — see F5.

## Operator scope decision

The residue was re-measured before any work (F1) and put to the operator, because "everything
outstanding" measures far larger than run 01's summary implies. The operator scoped:

- **This PR:** D4 to completion, plus D1 across the three largest modules.
- **D2 for the campaign:** all 39 over-budget modules, not the 8 the plan names as a lead. Recorded here
  so the follow-up inherits it; **no D2 work is in this PR.**

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded as the first action)

Conditional skills for the Python-test surface were **not** loaded from the bundle paths; the
conversions follow the shared-loader API documented in `test/conftest.py` itself. Recorded as not done
rather than claimed.

## Deliverables

| Deliverable | State | Detail |
|---|---|---|
| **D4 — one import preamble** | **COMPLETE** — 22/22 sites, 15 modules | `d2c12b7` + `60526ac` |
| **D1 — parametrize the contract tables** | **No collapsible family remains in the scoped modules** | See F5 — measured, not assumed |
| D2 / D3 | not in this PR | Per the operator scope decision |

### D4 — complete

All 22 sites across 15 modules moved off bespoke loaders onto the shared `test/conftest.py` API
(`load_script_module`, `get_script_path`, `add_skill_scripts_to_path`, `PROJECT_ROOT`).

**Done-when met.** A grep for `spec_from_file_location` and `Path(__file__).parent.parent.parent` over
the six slice directories returns **zero** — confirmed against a positive control, since the same glob
for `load_script_module` returns 228 occurrences across 83 files. The zero is a real absence, not a
mis-scoped query.

Line delta: **+92 / −235** (net −143).

**Every marketplace-script conversion preserves its original `sys.modules` registration name.** This is
the hazard run 01 paid 173 order-dependent failures for: `load_script_module`'s `module_name` defaults
to the script stem, and the marketplace config modules carry mutable module-level default dicts, so
collapsing distinct registrations onto a shared one makes previously-isolated modules share state.

**Two sibling-fixture loads were deliberately collapsed** onto one shared registration.
`test_classify_affected_files.py` and `test_manage_execution_manifest_compose.py` each loaded
`_execution_manifest_fixtures.py` under a unique name; both now use the bare
`from _execution_manifest_fixtures import …`, the tree's actual convention (530 uses across 389 files).
Safe **because it was checked**: that module defines only a class and four factories, with no
module-level mutable state, so the hazard above does not apply to it.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → 15 modules changed; gate owed and run.

- **`./pw quality-gate`** → `issues[0]`, clean across mypy(production), ruff, SPDX, plugin-doctor. It
  first reported 2 ruff `I001` import-sorting errors, fixed before the commit.
- **`./pw verify`** → **SUCCESS**, `20322 passed, 14 skipped` in 481s, clean across all six dimensions
  **including `mypy(test)`** — the `test-compile` step neither `quality-gate` nor a pytest run performs.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | Re-measurement | D2's scope is **39** modules over the landed 400-line budget, not the ~8 the plan lists. The plan flags its list as a lead to re-derive; re-derived it is nearly 5× larger. | Reported; operator scoped it to the campaign |
| F2 | This run; independently by `sourcery-ai` | `_execution_manifest_fixtures.py`'s docstring documents the import form `from test.plan_marshall.manage_execution_manifest._execution_manifest_fixtures import …`, which **cannot work** — the directories contain hyphens, illegal in a Python package path. | **Fixed** — docstring now shows the bare form and says why it is the only one that works |
| F6 | `sourcery-ai` review | Centralize the scattered `add_skill_scripts_to_path(…)` calls into a shared fixture. | **Rejected** — the shared helper *is* `add_skill_scripts_to_path`; centralizing further means editing `test/conftest.py`, which this plan's Out of scope excludes (owned by plan `020`, with five sibling plans running concurrently against it) |
| F7 | `sourcery-ai` review | Add a guard test asserting `_execution_manifest_fixtures` stays free of mutable module-level state, so the shared-registration collapse cannot silently regress. | **Rejected** — the proposed guard inspects only *public, non-callable* module attributes, so it would miss the two shapes that actually matter: a mutable default bound inside a function, and mutable state in the marketplace script a test registers under a shared name. A partial guard on this invariant reads as assurance it does not provide. The invariant is real; a check worth having would have to target the registration/state pair, not one module's globals |
| F3 | Self-inflicted | Removing `import sys` from `test_get_module_context.py` broke 3 tests: the usage check grepped `sys\.` and missed `monkeypatch.setattr(sys, 'argv', …)`, which has no trailing dot. | Fixed before commit |
| F4 | Environment | Push credentials failed mid-session, then recovered without intervention. Cost the run its D1 window. | Closed; shipped as the § Step 9 proposal, PR #1269 |
| F5 | Re-measurement | **D1's named targets no longer carry a collapsible family.** See below. | Reported; no code change made |

### F5 — D1's premise, re-derived

The plan's D1 exemplar is `test_config_defaults.py`'s `_includes_{knob}` family: "roughly 22 of those
functions", of which "only **three** knobs are genuinely crossed against both accessors". The plan is
explicit that the naming shape is not the evidence and that membership must be re-derived before
collapsing. Re-derived:

| Prefix | Count |
|---|---|
| `test_default_plan_finalize_includes_*` | **0** |
| `test_get_default_config_includes_*` | **6** |

The first prefix is **gone entirely**, and the surviving six are exactly the members the plan itself
says are *not* table rows — `orchestrator_block`, `project_block`, `working_prefixes`,
`plan_wide_coverage`, `pr_strategy_and_ceiling`, `finalize_flow_hardening_knobs` — each asserting an
unrelated subject. Run 01's 13 collapsed families already consumed this surface.

`test_decision_rules.py`, the module the plan names as remaining, likewise carries **no family of three
or more** near-identical functions: grouping its test functions by name shape, the largest group is
**2**, and the module already contains 6 `@pytest.mark.parametrize` blocks.

**So D1's done-when — "no `test_*_includes_{knob}`-shaped family of three or more near-identical
functions remains in the slice" — holds for the scoped modules without further work.** What run 01
counted as "~100 families remaining" was its AST scan under a *looser body-shape* signature, not the
name-shape family D1 actually specifies; run 01 recorded that figure as an upper bound and measured its
true yield at 996 collapsible lines under exact-shape matching. That is a different, riskier
deliverable — collapsing by body shape can silently drop a distinguishing assertion, which is precisely
what the plan's "asserted absence of a difference" claim label warns about.

**No D1 code change was made, and this is reported rather than claimed as completion.** The honest
statement is that the deliverable as written is satisfied in the scoped modules and that the residual
body-shape work needs re-specifying before anyone attempts it.

## Reviewer participation

Population derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc — not
transcribed here.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `sourcery-ai[bot]` | `reviewed` | — | Published a review on head `32c4a67` with 1 inline issue and 2 overall comments; dispositioned as F2 (fixed), F6 and F7 (rejected with reasons) |
| `coderabbitai[bot]` | `silent` | `unknown` | No review, no notice, on either surface |
| `cuioss-review-bot` | `silent` | `unknown` | No review, no notice |

**Coverage: 1 of 3.** The two `silent` verdicts are recorded **without** the § Step 7 recovery check
having been run — the `trigger_comment` re-invite was not attempted, so this is an unexplained silence
that was not investigated, not one established as unrecoverable. That is a gap in this run, disclosed
rather than papered over.

The § Step 8 shortfall disclosure fired before arming: stated to the operator as 1-of-3 with both
silences flagged as un-recovered.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not recorded per-step; the build gates took ~8 min (`verify`) and ~1 min (`quality-gate`).
- **Population:** this single Claude Code cloud session. **Not** comparable to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a different billing
  boundary.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Partial** — lane loaded; conditional Python-test skills not |
| 2 Branch | Done — `chore/config-manifest-d4-and-d1`, cut from `origin/main`, pushed before any edit |
| 3 Plan directory | Done — established by run 01; resumed |
| 4 Implement | Done for D4; D1 reported rather than changed (F5) |
| 4 Per-commit gate | Done — `./pw quality-gate` clean before each `*.py` commit |
| 4 Pushed | Done — after the credential failure recovered (F4) |
| 5 Build gate | Done — full `./pw verify` SUCCESS |
| 6 Verification sub-agent | **NOT DONE** — the independent pre-PR verification dispatch was skipped |
| 7 PR cycle | Done — PR #1270; all three comment surfaces read, every finding dispositioned, participation table above. The `silent` recovery check was **not** run |
| 8 Merge gate | Conditions 1–3 met; coverage shortfall disclosed at 1-of-3; auto-merge armed (SQUASH) |
| 9 This check | Done (this section) |

**GitHub access path:** GitHub MCP server for PR operations; `git push` directly once credentials
recovered. **Branch form:** run-created, `chore/` prefix from the closed set, at operator instruction to
cut from `main`. The harness-assigned `claude/config-manifest-test-reduction-0eod0y` was not reused —
its PR is merged, and the merged-PR rule forbids stacking new work on merged history.

An earlier branch, `chore/config-manifest-test-reduction-02`, carries two `.patch` files written while
push was down. It is **superseded by this branch** and should be deleted unmerged; those patches must
never reach `main`.

A cloud run never owes a `/sync-plugin-cache`; no `marketplace/bundles/**` file was touched.

## What have we learned (Step 9)

Proposed and shipped as **PR #1269** — the lane assumes `git push` works and never names the mid-run
credential failure this run hit, nor records the GitHub MCP API as a write-the-tree fallback whose cost
scales with file size rather than diff size.

## Residue

- **D4:** none — complete.
- **D1:** the name-shape deliverable is satisfied in the scoped modules (F5). The body-shape residue
  (~996 collapsible lines by run 01's exact-shape measurement) **needs re-specifying** before it is
  attempted; it is not the deliverable D1 describes.
- **D2:** 39 modules over budget — operator-scoped to the campaign.
- **D3:** not started; the `parse_ns` exception list remains empty **by non-attempt**.
- **F7:** the mutable-state invariant behind the shared-registration collapse has no automated guard.
  The reviewer's proposed guard was rejected as too narrow to protect it; a real one would key on the
  registration/state pair, and does not exist.
- Run 01's line-floor recommendation for `040`–`080` stands, and F1 and F5 both strengthen it: this
  plan's D2 scope was under-derived and its D1 scope over-derived. Both were flagged in the plan as
  leads to re-derive, and both were wrong in the direction the plan warned about.

## Disposition update (2026-08-17) — appended by the epic re-scoping run

Appended after this run closed, by the run that read every landed report in this epic and re-scoped
the remaining plans. It covers the residue of **both** runs of plan `030` and does not revise anything
above.

| Item from run 01 or run 02 | Disposition |
|---|---|
| Run 01 § "Why — the plan's premise for this floor is refuted by measurement", and its recommendation to re-derive the floor for `040`–`080` | **Acted on, epic-wide.** Every percentage line floor in the epic is retired. The epic README § "Why there is no line floor" carries the arithmetic for all six slices and finds that **three of the six floors exceed that slice's entire comment-and-docstring volume**. A run now reports its line delta rather than targeting it. This report's recommendation is the reason the change was made |
| D2 — 39 modules over the 400-line budget, unstarted | **Owner assigned: plan `100`**, which owns the module-budget campaign across all six slices, one slice per run. The split is no longer a reduction plan's deliverable at all: four plans sequenced it last and none reached it, and the whole-tree count moved 315 → 313 in consequence |
| Run 02 § Findings F7 — the mutable-state invariant behind the shared-registration collapse has no automated guard, and the reviewer's proposed guard was too narrow | **Owner assigned: plan `090` § D3.** That deliverable builds the guard this report said would have to key on the registration/state pair rather than on one module's globals, and requires it be demonstrated failing before it is accepted |
| D3 — arrange-into-fixtures, unstarted; the `parse_ns` exception list **empty by non-attempt** | **Still open in this plan's slice, and indexed** in the epic README § "What the executed half left open" so a follow-up run can be commissioned without re-reading this report. The README quotes this report's warning that an empty list produced by not attempting the sweep must not be read as a clean result |
| Run 02 § Findings F5 — D1's named targets no longer carry a collapsible family; the body-shape residue needs re-specifying | **Recorded as-is.** No plan re-specifies it, deliberately: collapsing by body shape can drop a distinguishing assertion, which is the risk this report named. Indexed in the README as open |
| Run 01 § Findings 5 — `test-docstring-historical-prose` fires on `TASK-001` when it names a real fixture artifact | **Closed**, by plan `050`'s second run, which taught the rule to exempt a match inside a backtick span or a quoted string |
| Run 01 § Residue — the `subprocess-pythonpath` pair in `marshall-steward` | **Still open.** Re-derived whole-tree: that rule now reports 15 findings. Unowned |
