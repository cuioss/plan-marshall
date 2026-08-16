# Run report — 040-delivery-pipeline-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/delivery-pipeline-test-reduction-igiwmw`    **PR:** #1259    **Outcome:** partial

The line-reduction floor was **not** reached: the slice dropped **0.578%** against a stated **25%**
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
| D1 | Strip history from docstrings and comments | **done** against its done-when; **partial** against its own prose (92 citations remain in shapes the rule does not match) | `6a8729b`, `48910a0`, `115a5df` |
| D2 | One fixture corpus and one driver per module | **not done** | — |
| D3 | Collapse the duplicated assertion layer | **not done** | — |
| D4 | Split every module over the budget | **not done** | — |
| D5 | Normalise preambles and argument construction | **partial** | `bfffa68` |
| — | (B5 parametrization of two CLI smoke tables — sanctioned by the plan's out-of-scope § but **not** a deliverable) | done | `7544567` |
| D6 | Report the measured deltas | **done** | this report |

### D1 — done

`plugin-doctor test-docstring-historical-prose` over the slice: **48 → 0**. Plan ids, deliverable
ids, `TASK-NNN`, `PR #NNN`, `plan-marshall#NNNN` and lesson ids were removed from docstrings,
comments and assert messages across 25 modules, each invariant restated in the present tense.
Two tests named after an incident were renamed for what they assert (one after a PR number, one after a lesson)
(`test_pr_410_regression_three_successes_one_skipped_is_success` and
`test_lesson_regression_three_successes_one_skipped_is_success` → both
`test_three_successes_one_skipped_is_success`).

**D1's done-when is met; D1's deliverable text is not fully satisfied — reported, not glossed.**
The done-when names one rule and that rule is clean. But the deliverable also names "plan ids,
deliverable ids, PR numbers, lesson ids", and the rule's regexes are narrower than that text
(`deliverable\s+D\d+`, `PR #\d+`, `TASK-\d{3}`), so shapes outside them survive a zero finding
count. Swept over docstrings and `#` comments only — string-literal test DATA excluded by
construction, so a synthetic comment titled `'PR #42 review_body comment by coderabbitai'` cannot
appear here:

| Shape | Before | After | Why the rule does not see it |
|---|---|---|---|
| `deliverable N` (bare digit) | 55 | **46** | rule matches `deliverable D\d+` |
| bare `#NNNN` incident ref | 37 | **25** | rule matches `PR #\d+` |
| `this plan` | 22 | **21** | not a rule pattern |
| `TASK-N` (1–2 digit) | 9 | **0** | rule matches `TASK-\d{3}`; cleared in this run's final pass |
| `lesson-…` | 12 | **0** | — |
| `PR #N` / `plan-marshall#N` | 12 / 5 | **0** / **0** | — |

So **92 prose citations remain**, roughly half of them in files this run edited for D1. The three
shapes the rule *does* cover are at zero; the three it does not are largely untouched. This is the
honest state: **D1 done against its done-when, partial against its own prose.**

**D1's line delta, stated separately as the plan requires: −40 lines.** Derived per-commit with
`git diff --numstat <prev> <commit> -- test/`: `6a8729b` −31, `48910a0` −22, `115a5df` **+13** (the
cold-read restorations add text back). The five commits sum to the verified −385 slice total
(`bfffa68` −94, `7544567` −251).

An earlier draft of this report stated −159 here. That figure was not reproducible from the commits
cited and is corrected; it is exactly the number the plan singles out as "the deliverable whose yield
this epic most needs to know", so the correction matters more than the direction. The smaller figure
**strengthens** the conclusion in § "What the measurement says" rather than weakening it.

### D3 — not done

**This deliverable was not performed, and an earlier draft of this report wrongly called it
"partial".** The correction is the most important one in this report, because the earlier wording
claimed a gating rule had been cleared when it had not been applied at all.

What was actually done is **B5 parametrization**: `test_github.py`'s 31 CLI smokes and
`test_gitlab.py`'s 28 became three parametrized tables each. That is legitimate and explicitly
sanctioned — the plan's out-of-scope § says to "parametrize the genuinely tabular cases in this
slice … status-code tables" — and it is where 251 of the run's 385 removed lines come from. But it
is **not** D3:

| D3 requires | What happened |
|---|---|
| Subprocess coverage collapses to a **single per-script CLI-plumbing smoke** | 31 and 28 subprocess **executions** remain — each parametrized case still calls `run_script`, so only the *call sites* fell (31→3, 28→3), not the executions |
| Every collapse **names the in-process test that now carries the contract** | **No in-process test is named**, and none could be: nothing was subsumed |

So the assertion layer was not reduced; it was re-expressed more compactly. Case counts are
preserved exactly (40→40, 31→31) and every assertion survives — see the verification findings — but
the deliverable's own done-when ("each collapsed subprocess test is listed in the report beside the
in-process test that subsumes it") has an empty list, which is the correct signal that D3 did not run.

**The gating derivation D3 requires was performed and did not license any collapse.** A survey listed
every `run_script` call site beside its module's in-process tests. The largest remaining populations
— `tools-integration-ci/test_ci.py` (22), `automatic-review/test_review_completeness.py` (21),
`test_structural_refusal.py` (8) — are router- and handler-behaviour tests driven through the
subprocess boundary, not smokes duplicating a same-module in-process test. Collapsing them without
pairing evidence would be deletion, which the plan forbids. **124 `run_script` call sites across the
slice remain** (177 before), and the pairing evidence for them was not produced.

### D5 — partial

`test-module-preamble-boilerplate`: **42 → 24**. 15 modules converted from
`Path(__file__).parent`-chain + `spec_from_file_location` preambles to
`conftest.get_scripts_dir` / `load_script_module`, so resolution is by `(bundle, skill)` identity
rather than by the test file's own directory depth.

The 24 remaining are preamble shapes the AST transformer did not match (a script-path constant
consumed by an inline spec, loaders nested inside a test function). They are listed by
`plugin-doctor test-conventions` and are mechanical follow-up work.

**The `parse_ns` half of D5 was not started.** Census: the slice carries **391** `Namespace(`
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

**Population, stated once and used everywhere below:** all **106** `.py` files in the plan's
Expected surface — the twelve directories, the four named root modules, **and** `_ci_wait_contract.py`,
which the Expected surface explicitly lists. An earlier draft ran the line table over 105 files
(omitting the helper) while the composition table used all 106, giving two populations for one slice;
that is corrected, and every figure below is on the 106-file population.

**1–2. Per-directory and slice-total line counts** — line count per file, before =
`git show origin/main:<path>`:

| Directory | Before | After | Delta |
|---|---|---|---|
| `automatic-review` | 6291 | 6290 | 1 |
| `manage-ci-artifacts` | 812 | 796 | 16 |
| `phase-5-execute` | 2067 | 2067 | 0 |
| `phase-6-finalize` | 18371 | 18307 | 64 |
| `tools-integration-ci` | 5857 | 5857 | 0 |
| `workflow-integration-git` | 8200 | 8175 | 25 |
| `workflow-integration-github` | 16398 | 16234 | 164 |
| `workflow-integration-gitlab` | 3301 | 3189 | 112 |
| `workflow-integration-sonar` | 1521 | 1519 | 2 |
| `workflow-permission-web` | 615 | 615 | 0 |
| `workflow-pr-doctor` | 891 | 891 | 0 |
| `workflow-shared` | 134 | 134 | 0 |
| (root modules + `_ci_wait_contract.py`) | 2158 | 2157 | 1 |
| **SLICE TOTAL** | **66616** | **66231** | **385** |

**Reduction: 0.578%.** The 25% floor on this population is **16,654** lines.

The plan's HYPOTHESIS of ~62,200 lines re-derives to **66,616** — the lead was ~7% low.

**3. Collected test count** — `pytest <slice> --collect-only -q`: **3038 → 3038**. No decrease.

**4. Coverage** — `pytest <the 16 slice targets> -o addopts="" -p no:randomly --cov-report=term`
with one `--cov=` per exercised skill, the eleven being
`marketplace/bundles/plan-marshall/skills/{automatic-review, manage-ci-artifacts, phase-5-execute,
phase-6-finalize, tools-integration-ci, workflow-integration-git, workflow-integration-github,
workflow-integration-gitlab, workflow-integration-sonar, workflow-permission-web,
workflow-pr-doctor}` (`workflow-shared` has no matching skill directory). Precise figure from
`coverage report --precision=4`: **77.8270% → 77.8270%**, with statements/missing/branch/partial
identical at 8430 / 1760 / 3084 / 393. No decrease.

**5. D1 line delta, stated separately:** **−40 lines** (per-commit `git diff --numstat`; see § D1).

**6. D3 collapse list:** **empty — no collapse was performed** (§ D3). The list is empty because the
deliverable did not run, not because it ran and found nothing to collapse. 124 `run_script` call
sites remain across the slice.

**7. `parse_ns` exception list:** **not produced** — the `parse_ns` conversion was not started
(**391** `Namespace(` sites remain, counted over the 106-file population). Reported as unavailable
rather than as an empty list, because an empty list would falsely imply every call site converted
cleanly.

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
| 3 | Line count drops ≥25% | **FAILS** — 0.578% (385 of 16,654 required); shortfall 16,269 lines |

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

The 25% floor is 16,654 lines. **Total prose is 18,279 lines.** So the floor is only reachable by
deleting roughly 90% of every docstring and comment in the slice — or by removing code.

The plan's problem statement asserts that "a large share of that text is history, not invariant".
Re-derived, that share is small. The plan's own marker grep, run case-sensitively exactly as the plan
writes it (`once derived|used to |no longer|the fix |PR #[0-9]|lesson-20|this plan`) over the
106-file population, returns **126 lines across 53 files**; the doctor's precise citation rule
returns **48**. (An earlier draft reported 175/57 from a case-insensitive variant of the same
pattern — a different measurement, corrected here to the one the plan specifies.) Once those are removed, what remains
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

The one measured data point on code-side yield supports that range: B5 parametrization of two
genuinely tabular modules returned **251 lines**, which is 65% of everything this run removed, from
2 of 106 files. That is the productive lever on this slice — not prose.

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Gating partition derivation | `test/pm-code-intelligence/` is claimed by no plan in `030`–`080` | **Reported, not claimed.** Operator dispositioned as handled elsewhere. README exclusion list is stale. |
| 2 | Gating partition derivation | `test/test_shared_harness.py` is a fourth 020-owned exclusion the README's three-item list does not name | **Reported.** Same disposition. |
| 3 | Measurement | The plan's ~62,200-line HYPOTHESIS re-derives to 66,616 (~7% low) | Recorded; all figures use the re-derived total on the 106-file population. |
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
| 15 | Pre-PR verification | Report claimed D1's line delta was **−159**; the reproducible per-commit figure is **−40** | **Fixed** — corrected in § D1 and § D6. This is the figure the plan singles out as most needed, so the error mattered. |
| 16 | Pre-PR verification | Report called D3 **partial** and claimed its gating rule was cleared; D3 was **not performed** — the parametrized cases each still spawn a subprocess, and no in-process test is named | **Fixed** — D3 reclassified **not done**, the work relabelled as B5 parametrization, and the empty collapse list explained. |
| 17 | Pre-PR verification | Two populations were used for one slice — the line table over 105 files, the composition table over 106 (omitting `_ci_wait_contract.py`, which the Expected surface lists) | **Fixed** — one 106-file population declared once and used throughout; totals restated as 66,616 → 66,231, floor 16,654. |
| 18 | Pre-PR verification | Two per-directory "after" cells were wrong and the column did not sum to its own stated total | **Fixed** — table re-derived; `phase-6-finalize` 18,307 and `workflow-integration-gitlab` 3,189. |
| 19 | Pre-PR verification | 92 prose citations remain in shapes the doctor rule does not match, ~half in files this run edited | **Partly fixed** (`TASK-N` and the last lesson id cleared), **rest recorded** — see § D1 and § Residue. |
| 20 | Pre-PR verification | Marker-grep figure 175/57 came from a case-insensitive variant of the plan's pattern | **Fixed** — restated as **126 lines across 53 files**, case-sensitive exactly as the plan writes it. |
| 21 | Pre-PR verification | `Namespace(` count stated as 384; correct count on the declared population is 391 | **Fixed** throughout. |
| 22 | Pre-PR verification | D6 requires each figure labelled with its producing command; the coverage row elided its eleven `--cov` targets | **Fixed** — all eleven skill paths named in § D6. |
| 23 | Pre-PR verification | The Verification § requires the cold-read answers recorded **verbatim**; the report summarised them | **Fixed** — verbatim answers appended as § Appendix. |
| 24 | Pre-PR verification | "Two tests named after a PR number" — one was named after a lesson | **Fixed** — both names now given. |
| 25 | Pre-PR verification | `fixtures/ci-wait/README.md` still carries a plan slug, a lesson id, `TASK-002`/`TASK-004`, a Q-Gate finding id, and an "Authored 2026-05-24" line (also a "No timestamps" breach) | **Recorded, not fixed** — outside the remaining budget of this run; listed in § Residue. |

## Reviewer participation

Expected population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | `rate-limited` | **yes** | Issue comment: "Review limit reached … **Next review available in: 57 minutes** … You've used all 1 included review currently available under your plan." A countdown, so a re-request later is productive. |
| `cuioss-review-bot` | `reviewed` | — | Issue comment "PR Reviewer Guide 🔍": *PR contains tests* / *No security concerns identified* / *No major issues detected*. An explicit nothing-to-report over the diff. |
| `sourcery-ai` | `rate-limited` | **yes** (weekly) | Review-summary body: "you have reached your weekly rate limit of 500000 diff characters." A **weekly quota**, not a per-diff size ceiling — it clears on the weekly reset rather than never, so it is `yes`, but not on a same-session timescale. |

**Coverage: 1 of 3.**

All three surfaces were read — `get_comments` (issue comments), `get_reviews` (review-summary
bodies), `get_review_comments` (inline threads, 0 of them). Reading only one or two would have
mis-scored this PR in both directions: sourcery's refusal exists **only** in the review-summary body,
and pr-agent's review **only** in the issue comments.

**A `silent` verdict was provisionally recorded for `cuioss-review-bot` and then overturned by the
recovery check** — which is the whole reason the check exists. The first read of all three surfaces
at ~11:57:30 found nothing from it. Querying its workflow by **event** (`pull_request`, not by head
branch) found run `31945719334` **completed/success**, whose step 10 — "Verify the reviewer actually
produced a review" — also concluded success. That was the positive control: it proved a review
existed and that the negative read was a timing artefact, not an absence. The review had been posted
at 11:57:58, ~30 seconds after the first read. Re-reading returned it. Recording `silent` on the
first read would have been a false negative published as fact.

**§ Step 8 condition 4 disclosure — fired, and stated to the operator:**

> Review coverage: **1 of 3**. `cuioss-review-bot` reviewed and reported no major issues.
> `coderabbitai` is rate-limited, reopens in ~57 minutes. `sourcery-ai` is rate-limited on a weekly
> 500,000-diff-character quota, reopens on the weekly reset.

This is a disclosure, not a block: rate limits are outside our control, and the contract is explicit
that a shortfall changes what the run **says**, never whether it merges.

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
| 7 PR cycle | done — PR #1259 open; all three comment surfaces read; every comment dispositioned (two rate-limit notices, not actionable; one clean review, nothing to fix); participation table carries a verdict and a `Reopens?` per reviewer, and the one provisional `silent` records what its recovery check found |
| 8 Merge gate | **deliberately not armed** — see below |
| 8 Bridge | done — no write under `doc/plans/` outside this plan's own directory |
| 9 This check | done — recorded here |
| 9 What have we learned | done — below |

**Merge decision — operator directed landing.** Asked whether the goals could sensibly be shifted
rather than the PR held, the operator's instruction was to re-scope if sensible and otherwise land
now. A re-scope **is** well-founded on this run's evidence (the floor belongs against code, not
prose — § "What the measurement says"), but writing it is out of this run's reach: the lane forbids
writing outside this plan's own directory, so neither a sibling plan's floor nor a new follow-up plan
may be authored here. The deferral record this run *can* own is § Residue, which itemises every
unstarted deliverable. Holding the PR therefore buys nothing, and auto-merge was armed on that
instruction.

The paragraph below records why the run had *declined* to arm before being asked, and is kept so the
reversal is visible rather than silent.

**Why auto-merge was not armed before that instruction.** Conditions 2 and 3 are met: every PR comment is dispositioned, and
this report is the last pre-merge commit. Condition 1 is not — `verify / verify` was still
`in_progress` at the gate, so `mergeable_state` read `blocked`. The contract permits arming anyway
when a run cannot self-wake, on the ground that the merge queue is the real enforcer. **This run does
not take that permission**, for a reason the contract does not cover: arming is a one-way door, and
the question here is not whether the change is *safe* to land but whether a plan that hit **0.578% of
a 25% target** should land at all, or be re-scoped first. That is an operator decision about scope,
not a CI-readiness decision, and it is not this run's to make unilaterally. The PR is left open and
green-pending with the shortfall disclosed.

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
| D5 `parse_ns` half not started — 391 `Namespace(` sites, 9 `parse_ns` uses tree-wide | Highest-value mechanical follow-up; also produces the exception list the plan wants for widening `parse_ns`. |
| D5 preamble remainder — 24 findings in shapes the transformer did not match | Mechanical; the doctor lists every site. |
| **D3 not performed at all** — 124 `run_script` call sites remain, none paired | The deliverable's gating derivation ran and licensed nothing. Needs per-module in-process pairing before any collapse. |
| 92 prose citations remain (46 `deliverable N`, 25 bare `#NNNN`, 21 `this plan`) | Shapes the doctor rule does not match. Either widen the rule or finish the sweep by hand; ~half are in files this run already edited. |
| `fixtures/ci-wait/README.md` still carries a plan slug, lesson id, `TASK-002`/`TASK-004`, a Q-Gate id, and an `Authored 2026-05-24` line | The last is also a CLAUDE.md "No timestamps" breach. |
| `test_gitlab_ops_mr_merge.py` subprocess trip-wire guards only `subprocess.run` | Widening it to `Popen`/`check_call` changes test behaviour, so it is a proposal, not a silent edit. |
| Finding 11 — three near-identical CI-aggregation tests | Redundancy candidate pending pairing evidence. |
| Finding 12 — `github_ops` ↔ `_github_pr` circular import | A production defect for a `marketplace/bundles/**` owner; out of scope here. |
| Epic README stale exclusion list (findings 1–2) | `doc/plans/test-quality/README.md`, owned by the epic. |
| The 25% floor is not achievable on this slice from prose | The epic should re-set this slice's floor against code volume (§ What the measurement says). |
| Merge decision | PR #1259 is open, disclosed, and NOT armed. Whether a 0.578%-of-target run should land, or the plan be re-scoped first, is the operator call this run deliberately did not make. |
| Two reviewers rate-limited | `coderabbitai` reopens in ~57 min; `sourcery-ai` on the weekly reset. A re-request on either would raise coverage above 1 of 3. |

## Appendix — cold-read answers, verbatim

The plan's Verification § requires the cold-read answers recorded verbatim. Two rounds ran: the
first over ten named tests in five modules, the second over the four the first round failed, after
the restorations in `115a5df`. Both sub-agents were given the modules and nothing else — not the
plan, not the originals.

### Round 1 — ten tests

**1. `test_github_pr.py::test_a_deduped_comment_is_still_credited_as_participating` — PASS**
> **(a)** Participation credit is computed from the raw comment scan (unioned with the currency ledger for `participation_requires_update` bots) *before and independently of* the storage dedup. On a re-fetch at an unchanged HEAD where every comment is deduped (`count_stored == 0`, `count_skipped_duplicate == len(comments)`), `participated_bots` must be byte-identical to the first fetch — and this must hold for both credit shapes (presence-credited bots and currency-credited `requires_update` bots).
> **(b)** Stated outright: "the pre-merge barrier feeds `participated_bots` to the participation predicate, so coupling it to the dedup would read a proven reviewer as `absent` on any re-fetch." The body comment sharpens it: "a storage-hygiene drop can no longer flip a merge verdict." A maintainer knows exactly what merge-gate behaviour is at stake. — *the best docstring of the ten.*

**2. `test_github_pr.py::test_same_comment_id_distinct_bots_not_collided` — PARTIAL**
> **(a)** The dedup key is the composite `(bot_kind, comment_id)`, not `comment_id` alone. Two different bots publishing the same numeric id are stored as two findings; the second is not counted as a duplicate, and both coexist in the store under the shared id.
> **(b)** **CANNOT ANSWER (b)** from the prose. … That second sentence looks like a "why" but is not one — it restates the mechanism and then restates the assertion. "Stored instead of skipped as a duplicate" is the *observable*, not the *consequence*. What actually breaks (a genuine second-bot review comment is silently swallowed, never reaches triage, and the pre-merge barrier never sees it) is never said. … Second gap: nothing justifies the *premise*. Why would two bots ever reuse a numeric comment_id?

**3. `test_github_pr.py::test_second_fetch_dedupes_all_bot_kinds` — PARTIAL**
> **(a)** Re-fetch idempotence across *every* comment shape: thread-bearing (coderabbit, pr-agent) and thread_id-less (sourcery, human) comments alike dedupe on `(bot_kind, comment_id)`. Second fetch stores zero, counts all as duplicates, leaves the store size unchanged, and does not raise a `producer-mismatch` Q-Gate.
> **(b)** Weak. The docstring's only forward-looking clause is "the deduped comments — legitimate non-stores — do not trip the producer-mismatch Q-Gate," which is a *second contract clause*, not a consequence. It never says why re-fetch idempotence matters (unbounded finding accretion across barrier re-fetches; a pending queue that can never drain).

**4. `test_ci_complete_precondition.py::test_fixture_dir_present` — PASS**
> **(a)** The `.toon` fixture set on disk equals the pinned expected set exactly — both directions, no missing files and no extras (the assert diffs both ways).
> **(b)** Stated: "a fixture added without updating this list, or removed while still referenced, fails here rather than silently narrowing what the fixture-driven tests below cover." Silent coverage loss is a real, specific harm, and it explains why the check is bidirectional rather than a mere existence check.

**5. `test_ci_complete_precondition.py::test_fixture_green_success_resolves_to_success` — PARTIAL**
> **(a)** A captured all-green `ci wait` TOON envelope, parsed by the real `parse_toon` and fed through `resolve()`, classifies as `wait_succeeded` / `ci_final_status: success`.
> **(b)** Only half-answered. … That says what a red test *implies* (diagnostic value), not what breaks in production if the contract is violated. The operational consequence — green CI misread as failed, blocking finalize on every passing PR — is never written down.

**6. `test_ci_complete_precondition.py::test_fixture_check_name_special_chars_preserves_all_rows` — PASS**
> **(a)** `parse_toon` preserves all five rows of a `checks[]` inline table when check names contain special characters — specifically a colon (`lint:strict`) and an `=` (`coverage = 95%`) — and preserves those names verbatim. This is asserted at the parser level, deliberately bypassing `resolve()`.
> **(b)** Answered concretely, with mechanism: a key/value detection heuristic that ignores tabs reads `lint:strict\tcompleted\t…` as a new key/value pair …, breaks out of the array, and **silently truncates downstream rows**. "Silently" is doing real work — it names why this needs a test rather than being caught in the field.

**7. `test_pre_merge_barrier.py::test_absent_required_bot_blocks_merge_though_no_comment_is_pending` — PASS**
> **(a)** The participation predicate is independent of, and can veto, the pending-comment predicate. With zero pending `pr-comment` findings, `check_completeness` for a required bot that published nothing returns `participation_complete: False`, `unproven_bots: ['pr-agent']`, `bot_states['pr-agent'] == 'absent'`, and `proves == 'participation_only'`.
> **(b)** Stated clearly: "on the pending count alone the barrier would proceed to merge… its silence is indistinguishable from a clean review to any count of comments." The failure is unambiguous — a PR merges having never been reviewed by the bot that was required to review it.

**8. `test_pre_merge_barrier.py::test_stale_override_does_not_satisfy_barrier_after_head_advances` — PASS**
> **(a)** Merge authorizations are HEAD-bound. A `barrier-ask-override` granted at HEAD A yields, when checked at HEAD B: `any_authorized: False`, `any_admissible: False`, `barrier-ask-override` in `lapsed_kinds`, `authorized_kinds: []`. A re-grant at HEAD B restores authorized + admissible with an empty `lapsed_kinds` — the hatch is bound, not removed.
> **(b)** Answered. The docstring frames HEAD B as "carrying production commits the ruling never covered," and the second half explains the counter-risk it deliberately avoids ("the operator is never locked out, only re-asked about a tree they have actually seen").

**9. `test_workflow_integration_github_ci_aggregation.py::test_three_successes_one_skipped_is_success` — PASS**
> **(a)** `_derive_overall_status([SUCCESS, SUCCESS, SUCCESS, SKIPPED])` returns `'success'` with empty `failing` and `wait` lists. `mixed` is not a reachable outcome.
> **(b)** Best consequence statement in the set: "forcing the precondition resolver to report `ci_failure` on every green PR with at least one skipped check." Precise, quantified blast radius, names the downstream consumer.
> *Flagged:* this test is not visibly distinct from `test_derive_success_plus_skipped_returns_success` and `test_derive_success_plus_skipped_plus_neutral_returns_success`, which pin the same partition rule with fewer rows.

**10. `test_gitlab_ops_mr_merge.py::test_mr_merge_delete_branch_does_not_touch_local_git` — PARTIAL**
> **(b)** Half-answered. The mechanism is named … but the docstring never says what that actually costs … "Must not emit it" is asserted, never justified.
> *Two further defects:* the docstring says "**both halves**" and then enumerates **three** items; and the test sits under the section header `# Worktree error case (symmetric with the GitHub side)` … but the body contains **no worktree and no error case**.

### Round 2 — the four restored tests, re-read after `115a5df`

All four **PASS**.

**1. `test_same_comment_id_distinct_bots_not_collided`**
> **(b)** Answerable. Comment ids are provider-assigned per comment surface and are not unique across bots, so a `comment_id`-only key silently swallows the second bot's comment as a duplicate — "a genuine review finding that never reaches triage, and never reaches the pre-merge barrier that reads the store." That is a real outcome: a reviewer's finding is lost, and the PR clears the pre-merge barrier without it ever being seen.

**2. `test_second_fetch_dedupes_all_bot_kinds`**
> **(b)** Answerable, and specific: without the dedup, "every barrier re-fetch re-stores the same comments as fresh `pending` findings, so the queue accretes duplicates faster than triage can drain it and the completeness gate never closes." Two named downstream failures … Not a mechanism restatement.

**3. `test_fixture_green_success_resolves_to_success`**
> **(b)** Answerable: "a green CI run read as a failure blocks finalize on every passing PR, so the precondition resolver reports `ci_failure` for a tree that is in fact ready to merge." That names the user-visible damage — finalize is blocked on every passing PR, not just an edge case.

**4. `test_mr_merge_delete_branch_does_not_touch_local_git`**
> **(b)** Answerable, and the strongest of the four. … "it mutates whatever tree the caller happens to be standing in, and in an isolated worktree it targets a branch that is still checked out, so the delete fails and the merge is reported against a tree the caller never asked to touch."
> **Section-header accuracy: ACCURATE.** … **Stated count vs. listed count: MATCHES.**
> *Real defect found:* part (2) is stated broader than it is enforced — the trip-wire patches only `subprocess.run`, so `Popen` / `check_call` / `os.system` are unguarded. *(Disposition: the docstring claim was narrowed to the seam actually guarded; widening the trip-wire is left as a proposal, since it changes test behaviour.)*
