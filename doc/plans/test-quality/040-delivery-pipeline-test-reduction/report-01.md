# Run report — 040-delivery-pipeline-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/delivery-pipeline-test-reduction-igiwmw`    **PR:** #1257    **Outcome:** partial

The line-reduction floor was **not** reached: the slice dropped **0.58%** against a stated **25%**
floor. The operator was consulted at the point the shortfall became measurable and directed the run
to proceed on best effort rather than halt. D1's own done-when **is** met, and both non-negotiable
guards (collected count, coverage) hold exactly.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` (first action) |

The conditional skills in the contract's Step 1 table were **not** loaded, and this is reported
rather than glossed: the run went straight from the gating derivation into measurement and editing.
The surface it touched (Python tests) maps to `pm-dev-python:pytest-testing` and
`plan-marshall:persona-module-tester`, whose relevant content — the 400-line module budget, the
B1–B10 house style — was instead read directly out of
`persona-module-tester/standards/testing-methodology.md` and `doc/plans/test-quality/README.md` as
part of the gating checks. That is a weaker substitute for loading the skills and is recorded as a
process gap, not as an equivalent.

## Gating derivations (run before D1)

**Blocking dependency — plans `010` and `020` have landed.** Confirmed:
`test/conftest.py:569` defines `parse_ns`; `persona-module-tester/standards/testing-methodology.md`
§ "Module Budget: 400 lines" is present and states the budget is enforced by the
`test-module-line-budget` rule.

**Partition check — HALTING, and it fired.** Mechanically re-derived over all 101 population
entries (69 directories + 12 root files under `test/plan-marshall/`, plus 20 top-level `test/`
entries other than `plan-marshall/`). Result: 96 claimed exactly once, 0 double-claimed, **2
unclaimed**:

| Entry | Status |
|---|---|
| `test/pm-code-intelligence/` (1 `test_*.py`, 260 lines) | Claimed by **no** plan in `030`–`080`. Added by #1243, after the epic README was authored. |
| `test/test_shared_harness.py` (382 lines) | Named explicitly in plan `020`'s Expected surface, so owned — but a **fourth** exclusion the README's three-item list does not enumerate. |

Per the plan this is a halt-and-report condition. The operator was consulted and dispositioned both
entries as handled by another plan, so the run proceeded. Recorded here because the README's
exclusion list is now stale in two places, and the `pm-code-intelligence` case is the dangerous
one — an entry claimed by no plan looks exactly like a clean run.

## Deliverables

| # | Deliverable | Outcome | Commit |
|---|---|---|---|
| D1 | Strip history from docstrings and comments | **done** (done-when met) | `6a8729b`, `48910a0`, `115a5df` |
| D2 | One fixture corpus and one driver per module | **not done** | — |
| D3 | Collapse the duplicated assertion layer | **partial** | `7544567` |
| D4 | Split every module over the budget | **not done** | — |
| D5 | Normalise preambles and argument construction | **partial** | `bfffa68` |
| D6 | Report the measured deltas | **done** | this report |

### D1 — done

`plugin-doctor test-docstring-historical-prose` over the slice: **48 → 0**. Plan ids, deliverable
ids, `TASK-NNN`, `PR #NNN`, `plan-marshall#NNNN` and lesson ids were removed from docstrings,
comments and assert messages across 25 modules, each invariant restated in the present tense.
Two tests named after a PR number were renamed for what they assert
(`test_pr_410_regression_three_successes_one_skipped_is_success` →
`test_three_successes_one_skipped_is_success`, and the GitLab mirror).

**D1's line delta, stated separately as the plan requires: −159 lines** (66,146 → 65,987 across the
three D1 commits, before D3/D5). That is far below what the plan's problem statement anticipated,
and the reason is the single most useful finding of this run — see § "What the measurement says".

### D3 — partial

Only the two provider CLI-smoke tables were collapsed, because only they cleared the plan's gating
rule that a collapse must name the in-process test that subsumes it.

| Module | Collapsed | Into | Case count |
|---|---|---|---|
| `workflow-integration-github/test_github.py` | 31 subprocess smokes | 3 parametrized tables (help surface, missing-required exit, either-or structured refusal) | 40 → 40 |
| `workflow-integration-gitlab/test_gitlab.py` | 28 subprocess smokes | 3 parametrized tables | 31 → 31 |

One param per original test, so no case was lost. Every assertion is preserved including the
negative ones (`--body-file` and `--body` must NOT be advertised). 251 lines removed.

**The remaining 117 subprocess tests across 26 modules were surveyed and deliberately NOT
collapsed.** The survey (`run_script` call sites listed beside each module's in-process tests) is
the plan's gating derivation, and it did not produce the pairing evidence a collapse requires: the
largest remaining populations — `tools-integration-ci/test_ci.py` (22), `test_review_completeness.py`
(21), `test_structural_refusal.py` (8) — are router- and handler-behaviour tests driven through the
subprocess boundary, not smokes duplicating a same-module in-process test. Collapsing them without
that pairing would be deletion, which the plan forbids.

### D5 — partial

`test-module-preamble-boilerplate`: **42 → 24**. 15 modules converted from
`Path(__file__).parent`-chain + `spec_from_file_location` preambles to
`conftest.get_scripts_dir` / `load_script_module`, so resolution is by `(bundle, skill)` identity
rather than by the test file's own directory depth.

The 24 remaining are preamble shapes the AST transformer did not match (a script-path constant
consumed by an inline spec, loaders nested inside a test function). They are listed by
`plugin-doctor test-conventions` and are mechanical follow-up work.

**The `parse_ns` half of D5 was not started.** Census: the slice carries **384** `Namespace(`
constructions; `parse_ns` is used **9** times across all of `test/plan-marshall/`. The plan asks for
every hand-built namespace to be converted and every exception recorded with its script; neither was
done, so there is no exception list to report. This is the largest single piece of unstarted work
and the one with the clearest mechanical path.

### D2 and D4 — not done

D2 (fixture corpus + driver per module) was not started. D4 (split over-budget modules) was not
started and is correctly ordered last: `test-module-line-budget` is unchanged at **55** modules over
the 400-line budget. Because D1/D2 did not shrink the modules materially, D4's scope is essentially
what the plan estimated.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (30 files), so the gate ran.

`./pw verify` (full, all three sub-steps): **20272 passed, 14 skipped**, quality-gate clean
(`ruff … All checks passed!`, `mypy … Success: no issues found in 408 source files`,
`SPDX-header check passed`). Per-commit `./pw quality-gate` ran clean before each commit touching
`*.py`.

## Measured deltas (D6)

All seven figures, each with the command that produced it.

**1–2. Per-directory and slice-total line counts** — `wc -l` equivalent over the Expected surface,
before = `git show origin/main:<path>`:

| Directory | Before | After | Delta | % |
|---|---|---|---|---|
| `automatic-review` | 6291 | 6290 | 1 | 0.0% |
| `manage-ci-artifacts` | 812 | 796 | 16 | 2.0% |
| `phase-5-execute` | 2067 | 2067 | 0 | 0.0% |
| `phase-6-finalize` | 18371 | 18317 | 54 | 0.3% |
| `tools-integration-ci` | 5857 | 5857 | 0 | 0.0% |
| `workflow-integration-git` | 8200 | 8175 | 25 | 0.3% |
| `workflow-integration-github` | 16398 | 16234 | 164 | 1.0% |
| `workflow-integration-gitlab` | 3301 | 3188 | 113 | 3.4% |
| `workflow-integration-sonar` | 1521 | 1519 | 2 | 0.1% |
| `workflow-permission-web` | 615 | 615 | 0 | 0.0% |
| `workflow-pr-doctor` | 891 | 891 | 0 | 0.0% |
| `workflow-shared` | 134 | 134 | 0 | 0.0% |
| (root-level modules) | 1688 | 1687 | 1 | 0.1% |
| **SLICE TOTAL** | **66146** | **65761** | **385** | **0.58%** |

The plan's HYPOTHESIS of ~62,200 lines re-derives to **66,146** — the lead was ~6% low.

**3. Collected test count** — `pytest <slice> --collect-only -q`: **3038 → 3038**. No decrease.

**4. Coverage** — `pytest <slice> --cov=<11 skill paths> --cov-report=term`, precise figure from
`coverage report --precision=4`: **77.8270% → 77.8270%**, with statements/missing/branch/partial
identical at 8430 / 1760 / 3084 / 393. No decrease.

**5. D1 line delta, stated separately:** **−159 lines**.

**6. D3 collapse list:** the two modules in the D3 table above. No other collapse performed.

**7. `parse_ns` exception list:** **not produced** — the `parse_ns` conversion was not started
(384 `Namespace(` sites remain). Reported as unavailable rather than as an empty list, because an
empty list would falsely imply every call site converted cleanly.

**Per-rule `test-conventions` counts** — invocation from
`doc/plans/test-quality/README.md` § "Running the plugin-doctor test-conventions scope", run
per-directory and summed:

| Rule | Before | After |
|---|---|---|
| `test-docstring-historical-prose` | 48 | **0** |
| `test-module-preamble-boilerplate` | 42 | **24** |
| `test-module-line-budget` | 55 | 55 |
| `subprocess-pythonpath` | 1 | 1 |
| `unique-fixture-basenames` | 0 | 0 |
| `identifier-validator-corpus` | 0 | 0 |
| `test-helper-module-misnamed` | 0 | 0 |
| **TOTAL** | **146** | **80** |

## The three-part done-when

| # | Condition | Result |
|---|---|---|
| 1 | Collected test count does not decrease | **HOLDS** — 3038 → 3038 |
| 2 | Coverage does not decrease | **HOLDS** — 77.8270% → 77.8270%, identical to the statement |
| 3 | Line count drops ≥25% | **FAILS** — 0.58% (385 of 16,536 required); shortfall 16,151 lines |

## What the measurement says about the 25% floor

This is the finding the epic most needs, and it contradicts the plan's premise rather than merely
falling short of its target.

The slice's line composition, measured by AST over all 106 files:

| Kind | Lines | Share |
|---|---|---|
| Docstrings | 11,921 | 17.9% |
| Comments | 6,358 | 9.5% |
| Blank | 11,838 | 17.8% |
| Code | 36,499 | 54.8% |
| **Prose (docstring + comment)** | **18,279** | **27.4%** |

The 25% floor is 16,536 lines. **Total prose is 18,279 lines.** So the floor is only reachable by
deleting roughly 90% of every docstring and comment in the slice — or by removing code.

The plan's problem statement asserts that "a large share of that text is history, not invariant".
Re-derived, that share is small. The raw marker grep the plan specifies returns **175 lines** across
57 files, and the doctor's precise citation rule returns **48**. Once those are removed, what remains
is overwhelmingly present-tense rationale explaining why an invariant is load-bearing — which B3
explicitly says to **keep**, and which the plan's own D1 text says this slice "has a lot of … worth
keeping".

The cold read confirmed the risk is real in the other direction: of ten tests examined, four had
docstrings from which a maintainer could **not** recover why the contract matters, and in each case
that was because this run's own rewrite had removed the consequence along with the history. All four
were restored and re-read clean. That is the plan's stated largest risk materialising in practice,
and it bounds how aggressive D1 can be: prose in this slice is closer to its floor than the plan
assumed.

**Consequence for the epic:** on this slice a 25% line reduction is not achievable from prose, and is
achievable at all only from the 36,499 code lines — via D2 (fixture hoisting), D3 (the subprocess
layer, which the gating survey shows is mostly *not* duplicated), and D4 (splitting, which is
line-neutral to slightly positive). A revised floor for this slice should be set against code, not
prose, and probably in the 5–10% range unless D2 proves unusually productive.

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Gating partition derivation | `test/pm-code-intelligence/` is claimed by no plan in `030`–`080` | **Reported, not claimed.** Operator dispositioned as handled elsewhere. README exclusion list is stale. |
| 2 | Gating partition derivation | `test/test_shared_harness.py` is a fourth 020-owned exclusion the README's three-item list does not name | **Reported.** Same disposition. |
| 3 | Measurement | The plan's ~62,200-line HYPOTHESIS re-derives to 66,146 (~6% low) | Recorded; all figures use the re-derived total. |
| 4 | Cold read | `test_same_comment_id_distinct_bots_not_collided` docstring stated mechanism, not consequence | **Fixed** (`115a5df`) |
| 5 | Cold read | `test_second_fetch_dedupes_all_bot_kinds` docstring stated no consequence | **Fixed** (`115a5df`) |
| 6 | Cold read | `test_fixture_green_success_resolves_to_success` said what a red test implies, not what breaks | **Fixed** (`115a5df`) |
| 7 | Cold read | `test_mr_merge_delete_branch_does_not_touch_local_git` named the mechanism, never its cost | **Fixed** (`115a5df`) |
| 8 | Cold read | Same test: docstring said "both halves" then listed three | **Fixed** (`115a5df`) |
| 9 | Cold read | Same test: section header read "Worktree error case" over a body exercising neither a worktree nor an error | **Fixed** (`115a5df`) — header retitled to what the body does |
| 10 | Cold read | Same test: part (2) claimed "no git subprocess is ever spawned" but the trip-wire patches only `subprocess.run` | **Fixed** (`115a5df`) — claim narrowed to the seam actually guarded. The wider guard is left as a proposal, since widening it changes test behaviour. |
| 11 | Cold read | `test_three_successes_one_skipped_is_success` is not visibly distinct from two near-identical tests ~60 lines above | **Deferred** — a genuine redundancy candidate, but resolving it needs the D3-style pairing evidence this run did not produce for that module. |
| 12 | Build (pre-existing) | `github_ops` ↔ `_github_pr` circular import: collecting `phase-6-finalize` + `workflow-integration-github` together yields 20 collection errors | **Recorded, not fixed.** Reproduced identically on a clean `origin/main` worktree (same 20-file error set), so it is pre-existing and NOT introduced here. It is a `marketplace/bundles/**` defect, which the plan places out of scope. It does not affect `./pw verify`, which collects the whole tree in an order that resolves the import. |
| 13 | Own process | The contract's Step 1 conditional skills were not loaded | **Reported** in § Skills loaded. |
| 14 | Own process | An automated D5 rewrite initially placed a `from conftest import` below its first use and duplicated a name past a `# noqa` comment, breaking collection in 1 file | **Fixed before commit** — reverted, transformer corrected to check first-use position and strip trailing comments, re-applied, re-verified. |

## Reviewer participation

Expected population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | pending | — | PR opened at the end of this run; no review surface read yet |
| `cuioss-review-bot` | pending | — | as above |
| `sourcery-ai` | pending | — | as above |

**Coverage: not yet determinable (0 of 3 read).** The PR is opened as the run's final action, so no
reviewer has had the opportunity to publish. The § Step 8 shortfall disclosure therefore has nothing
to report yet; the review cycle is unfinished residue, recorded below.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** ~1h20m — first action ~10:28 UTC, report written ~11:52 UTC (source: session start
  and `git log` commit timestamps `6a8729b` 10:54 → `115a5df` 11:50).
- **Population:** this single Claude Code cloud session's usage. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a
  per-task billing boundary this session does not share. No comparable figure can be derived, so none
  is offered.

Two sub-agents were dispatched (cold read, cold re-read) plus one pre-PR verification agent; their
token usage is inside the same session population.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **partial** — `cloud-plan-lane` loaded first; conditional skills not loaded (§ Skills loaded) |
| 2 Branch | done — harness-assigned `claude/delivery-pipeline-test-reduction-igiwmw`, kept as-is, pushed to `origin` before the first edit |
| 3 Plan directory | done — `doc/plans/test-quality/040-delivery-pipeline-test-reduction/plan.md`, moved with `git mv`, `{NNN}-` prefix preserved, first-instruction block verified present |
| 4 Implement | done — 5 commits, all carrying the trailer, paths staged explicitly (no `git add -A`), no `uv.lock` churn |
| 4 Per-commit gate | done — `./pw quality-gate` clean before every `*.py` commit (`ruff`/`mypy`/SPDX each reporting clean) |
| 4 Pushed | done — pushed after every commit; `git status -sb` reports no `ahead` |
| 5 Build gate | done — Python changed, full `./pw verify` green (20272 passed, 14 skipped) |
| 6 Verification sub-agent | done — cold read (10 tests), cold re-read after fixes (4 tests, all PASS), pre-PR verification agent dispatched |
| 7 PR cycle | **incomplete** — PR opened as the final action; no review surface read (§ Reviewer participation) |
| 8 Merge gate | **not reached** — conditions 1–3 not met at time of writing; auto-merge NOT armed |
| 8 Bridge | done — no write under `doc/plans/` outside this plan's own directory |
| 9 This check | done — recorded here |
| 9 What have we learned | done — below |

**GitHub access path:** GitHub MCP server (cloud session; no `gh` CLI).
**Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a machine-local build step a cloud run neither performs nor records.

## What have we learned (Step 9)

**One contract change is proposed, with evidence from this run.**

*Evidence.* The contract's § Step 2 requires a clean tree and a published branch before any work, and
§ Step 5 requires a build gate — both are about the run's own hygiene. Nothing in the contract
requires a run to **re-derive the plan's own headline quantitative premise before committing to its
deliverables**. This run spent its first phase measuring, and that measurement (prose = 27.4% of the
slice, against a 25% line floor) showed the plan's central target was unreachable by the means the
plan named. Had that measurement come at the end, the run would have delivered the same work and
discovered only at reporting time that the floor was arithmetically out of reach.

*Proposed edit.* Add to § Step 4, before "Work the plan's deliverables in order":

> **Re-derive the plan's headline quantitative claim first.** When a plan states a numeric target
> (a percentage reduction, a count, a budget) and labels its own baseline a HYPOTHESIS or a lead,
> re-derive both the baseline and the target's feasibility **before** starting the first deliverable,
> and record the result in the report. A target that the re-derived baseline shows to be unreachable
> by the means the plan names is a finding to surface at the start — where the operator can re-scope —
> not at the end, where it is only an excuse.

*Status:* proposed to the operator, **not** self-approved. Not shipped in this PR — per § Step 9 it
belongs on its own `chore/` branch, so the contract amendment is not coupled to whether this plan
lands.

## Residue

| Item | Where it should go |
|---|---|
| D2 not started | A follow-up run on this slice, or a re-scoped `040`. |
| D4 not started — 55 modules still over the 400-line budget | Same; D4 is correctly last, and D1/D2 did not shrink modules enough to reduce its scope. |
| D5 `parse_ns` half not started — 384 `Namespace(` sites, 9 `parse_ns` uses tree-wide | Highest-value mechanical follow-up; also produces the exception list the plan wants for widening `parse_ns`. |
| D5 preamble remainder — 24 findings in shapes the transformer did not match | Mechanical; the doctor lists every site. |
| D3 — 117 subprocess tests surveyed, not paired | Needs per-module in-process pairing before any further collapse. |
| Finding 11 — three near-identical CI-aggregation tests | Redundancy candidate pending pairing evidence. |
| Finding 12 — `github_ops` ↔ `_github_pr` circular import | A production defect for a `marketplace/bundles/**` owner; out of scope here. |
| Epic README stale exclusion list (findings 1–2) | `doc/plans/test-quality/README.md`, owned by the epic. |
| The 25% floor is not achievable on this slice from prose | The epic should re-set this slice's floor against code volume (§ What the measurement says). |
| Review cycle unfinished | The PR is open; reviewer participation must be read and dispositioned before any merge gate. |
