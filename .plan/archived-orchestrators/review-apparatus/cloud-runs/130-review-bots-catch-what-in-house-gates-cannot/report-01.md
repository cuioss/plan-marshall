# Run report — 130-review-bots-catch-what-in-house-gates-cannot (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/review-bots-catch-gates-gpb6oe`    **PR:** [#1239](https://github.com/cuioss/plan-marshall/pull/1239)    **Outcome:** completed

## Skills loaded

Read by bundle path (the plugin was not assumed present):

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `plan-marshall:ref-workflow-architecture` | workflow docs, dispatch topology |
| `plan-marshall:persona-implementer` | production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure |

Every skill resolved by path. None was unobtainable.

## Deliverables

### D0 — each gate states what its green does not evaluate — **done**

Commit `1b3cfa6`, refined in `61dd515`.

The plan labels D0 "GATE, mutates nothing" while its *Done when* requires each gate's **verdict** to carry a scope limit. Read as: the `automatic-review` completeness guard is read-only for D0 (the Expected-surface line says so, and that guard already satisfies the requirement via `proves: participation_only`), while the gates whose verdicts do **not** state a limit are changed. Recorded here because it is an interpretation, not a reading forced by the text.

Two gates changed, one confirmed already compliant:

- **Build gate** (`_gate_coverage.py`) — `AnalysisLimit` registry keyed by analysis kind, `dimension_stem` stripping the per-run scope suffix, `structural_limits` deriving from the dimensions a run **actually recorded**, rendered on both COMPLETE and PARTIAL. An uncharacterised dimension renders UNKNOWN rather than being omitted.
- **Self-review** (`self_review.py surface`) — a `structural_limit` field beside the existing `scope_statement`, kept distinct because scope is cured by widening the file set and the structural limit is not.
- **Participation guard** — already compliant (`proves: participation_only`); read-only, unchanged.

A later round added a third element after the verification agent observed that an analysis the gate **never ran** leaves no trace at all: `quality-gate` runs no pytest, so a reader could not tell "does not execute tests" from "tests were fine". The block now closes with a derived `not run in this gate at all: …` line.

Standards updated in lock-step: `ext-point-self-review-surfacing.md`, `ext-self-review-plan-marshall/SKILL.md`, `pre-submission-self-review.md`, `pre-push-quality-gate.md` § "A gate states what its green does not evaluate".

**Gate-set completeness is not claimed.** The plan says "the gates in scope" without enumerating them. Three are addressed. `default:ci-verify`, `finalize-step-plugin-doctor`'s own step verdict, and `sonar-roundtrip` carry no structural limit and were not changed — named here so the omission is a recorded boundary rather than an implied completeness.

### D1 — same-run reconciliation between a review commitment and the simplify step — **done**

Commit `e078807`, fixed in `61dd515`.

`review_commitments.py` (new, `phase-6-finalize/scripts/`) derives the run's line-level commitments from its `pr-comment` findings, parses the simplify pass's own deletions from its diff, and reports the intersection. `finalize-step-simplify.md` Step 3b consults it before `mark-step-done`, reverts a conflicting deletion, and records it as a finding — so a committed line either survives or its removal is **visible**.

Two undetermined states fail closed to a conflict: an untriaged (`pending`) finding, and a finding with a path but no line anchor (which binds its whole file — the shape `github_pr` files for the review-body comments carrying the bots' consolidated findings).

The seam reports and never decides: `gates_merge: false`, `proves: removal_conflict_only`. An error return carries no `verdict` field.

### D2 — the review-versus-gate delta as a measured signal — **shipped as an instrument; no rate emitted; stop condition partially fired**

Commit `b110b88`, substantially corrected in `61dd515`, `806c886`, `25f59d8`.

`review_gate_delta.py` (new, `automatic-review/scripts/`). Governing contract at `bot-participation-contract.md` § "The review-versus-gate delta". Consumer wired at `finalize-step-review-retrospective` Step 3b, persisted by Step 4.

**The stop condition and what this run did about it — read this before reading any figure.**

The plan's stop condition concerns the *empirical denominator*: the fourteen-lesson corpus is `.plan/`-local and absent from the clone. This run split the deliverable rather than treating it as all-or-nothing:

- **The instrument ships.** It needs no historical corpus — its population is per-PR data the pipeline already holds at finalize time.
- **No rate is emitted, and none was computed.** No corpus was assembled. The plan forbids hand-assembling one, and a GitHub sweep of merged PRs would have been exactly that: I would have chosen the PRs *and* hand-labelled the partition, which is the volume-read-as-coverage defect the plan exists to close.
- **So the empirical half is reported blocked on an unavailable population**, per the stop condition.

⛔ **A selection effect the instrument cannot remove, disclosed here as the plan's Verification requires.** `finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9) mutate source *after* the gates (5, 7) and before review (30), and the dispatcher's re-entry check only re-fires a step the loop **reaches** — a forward pass never returns to order 5. So on the current step ordering the only measurable PRs are those where **neither** post-gate mutating step committed anything. That is a biased population, not a sample, and **few or no measurements will accumulate until the finalize ordering changes.** A column of `excluded` rows means *those PRs were never measurable* — it does **not** mean the gates caught everything, and read as the latter it becomes the exact misreading this plan exists to prevent. The sentence is in `_PROVENANCE`, in the contract, and in the consumer's Step 3b.

**Population and provenance**, published on every verdict: `reviewer_coverage` (N-of-M), `enabled_bots`, `reviewed_bots`, `gate_head_sha`, `reviewed_head_sha`, and a `provenance` string naming how the escape set was derived.

**The partition**, per the plan's ⛔: every escape is `gate_addressable` (a gate could have caught it — a configuration finding), `gate_structural` (no gate class reaches it), or `unpartitioned`. An unpartitioned escape **withholds the share**; it is never bucketed by default.

**No parity claim is attached**, per the plan's Out-of-scope. Whether the gate-green / bot-finding pairing recurs is the hypothesis the instrument exists to test, and this run tested nothing.

### D3 — tests, each verified to fail pre-fix — **done, with one labelled exception**

Commit `f29756f` and throughout. 100 tests added across six files.

Every test of **new behaviour** was written first and observed red before the implementation existed. Mutation evidence, run and reverted:

| Mutation | Caught by |
|---|---|
| `pending` reads as a release (D1 fail-open) | 3 tests |
| any deletion in a reviewed file conflicts (D1 over-broad) | 1 test |
| partial coverage still yields a share (D2 inversion) | 2 tests — reproduced **`structural_share: 100.0`** at 1-of-3 coverage, the exact "gates are perfect" inversion the plan names |
| an unpartitioned escape no longer withholds | 2 tests |
| COMPLETE drops its structural-limit block (D0) | 2 tests |
| `in_progress` folded into the `absent` display bucket | 1 test |

⚠ **One class is a regression pin, not a red-first test, and is labelled as such.** `TestAbsentVersusInProgressDistinction` pins already-shipped behaviour, so it *cannot* fail pre-fix; the plan's "each verified to FAIL pre-fix" is **not** claimed for it. It is proven discriminating by mutation instead (folding the display buckets turns `1 in-progress` into `1 absent`). The verification agent was asked whether to drop it and recommended keeping it as the right residue for a dropped deliverable.

### Lesson retirement

| Lesson | Verdict | Evidence |
|---|---|---|
| *the completeness guard conflates an absent bot with an in-progress one* | **CLOSED — re-derived against current main** | `STATE_ABSENT` / `STATE_IN_PROGRESS` are distinct members with distinct `classify_bot` branches and distinct summary buckets; `not_triggered` refines `absent` further. The plan's claim label ("already shipped, DROPPED not re-scoped") is confirmed, not taken on trust. A regression pin was added. |
| *no same-run reconciliation contract exists between the simplify step and automatic-review* | **CLOSED by D1** | `review_commitments.py` + Step 3b. |

⚠ **Neither retirement could be performed.** The lessons corpus is `.plan/`-local and absent from this clone. Both are recorded here as *verified-closed*; removing the corpus entries is a machine-local action this run cannot take and does not claim to have taken.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (5 production scripts, 7 test files), so the gate ran.

Final `./pw verify`: **19748 passed, 14 skipped, 0 failed**. Quality gate clean (`ruff` all checks passed, `mypy` no issues in 401 source files, SPDX passed, plugin-doctor `issues[0]`), `test-compile` clean over 739 test files.

Read from the tools' own output, not the exit code. `./pw verify` was run in full each round rather than substituting the narrower calls — and that mattered: `test-compile` caught two errors (`unused-ignore`, `import-not-found`) in a new test file that `quality-gate` + `module-tests` both passed. Exactly the class the lane contract warns those narrower calls miss.

## Findings

Recorded **per instance**. Source `sub-agent` = the independent pre-PR verification agent; four rounds were run because each of the first three found real defects.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | sub-agent r1 | D2's "every finding on a green-gate PR is a gate escape, **by construction**" is false — simplify (8) and security-audit (9) mutate source between the gates and review | **fixed** — claim anchored to tree identity (`gate_head_sha` == `reviewed_head_sha`), two new exclusion reasons |
| 2 | sub-agent r1 | The delta ran *before* the pass producing its partition labels → share withheld on every PR forever | **fixed** — moved to Step 3b, after Step 3 |
| 3 | sub-agent r1 | The delta's output reached no artifact | **fixed** — Step 4 persists it |
| 4 | sub-agent r1 | The counting rule was re-derived and diverged (no review-body-summary carve-out) | **fixed** — see #10, #14 |
| 5 | sub-agent r1 | Step 3b wrote its diff to `{worktree}/.git/`, a pointer **file** in a linked worktree → reconciliation silently skipped | **fixed** — `.plan/temp/`, failure mode named |
| 6 | sub-agent r1 | `review_commitments` docstring claimed `fetch_findings` re-anchors findings; pre-filter 5 skips them | **fixed** — imprecision stated with its consequence |
| 7 | sub-agent r1 | An analysis the gate never ran leaves no trace → "does not run tests" reads as "tests fine" | **fixed** — derived un-run line |
| 8 | sub-agent r1 | Self-review told to quote a ~530-char limit verbatim into an 80-char `display_detail` with no envelope field — a documented remedy with no reachable invocation | **fixed** — read-from-the-surface rule mirroring the `scope_statement` carve-out |
| 9 | sub-agent r1 | No CLI tests for either new script; `review_gate_delta` hand-rolled its TOON emitter | **fixed** — `TestCLI` on both, `serialize_toon` |
| 10 | sub-agent r2 | **The #4 fix was dead code** — matched `title`/`detail`, where the body never reaches | **fixed** — matches the promoted top-level `body` |
| 11 | sub-agent r2 | The fixture hid it: it put the signature in `title`, a shape production never produces. `review_retrospective` had the identical defect and fixture — the two agreed *by being wrong the same way* | **fixed** — both corrected, fixtures rewritten to the real record shape |
| 12 | sub-agent r2 | `_SUMMARY_AUTHOR = 'coderabbitai'` hard-coded one directory from the registry that owns it | **fixed** — new registry field `review_body_summary_patterns` |
| 13 | sub-agent r2 | "must land in both" was an obligation with no mechanism | **fixed** — `test_counting_rule_parity.py` |
| 14 | sub-agent r2 | `_PROVENANCE` stale; omitted the tree condition and the selection effect | **fixed** |
| 15 | sub-agent r2 | Three enumerations not extended to the SHA fields | **fixed** |
| 16 | sub-agent r2 | The un-run verdict line undocumented in the governing standard | **fixed** — plus the `_ANALYSIS_LIMITS` dual role and its bound |
| 17 | sub-agent r2 | `reviewed_head_sha` under-specified for the multi-iteration case | **fixed** — disagree → pass nothing |
| 18 | sub-agent r3 | **The #10 anchor was backwards on both real shapes** — a real summary was counted, a same-line-substance body was dropped | **fixed** — begins-with; verified by running the predicate, not by reasoning |
| 19 | sub-agent r3 | `review_retrospective` still hard-coded the login and keyed on `author` while the sibling keyed on `bot_kind` → divergence on every GitLab finding | **fixed** — one implementation; `resolve_bot_kind` reads either key |
| 20 | sub-agent r3 | The parity corpus was blind on exactly that selector axis | **fixed** — corpus extended |
| 21 | sub-agent r3 | Six registry-field enumerations stale | **fixed** |
| 22 | sub-agent r3 | Two stale `title/detail` statements above the corrected function | **fixed** |
| 23 | sub-agent r3 | Registry comparison not normalised on both sides (house rule) | **fixed** |
| 24 | sub-agent r3 | The two consumers have **opposite loss functions**, so one shared fail-open default cannot suit both | **accepted, not resolved** — recorded in Residue. The shared rule errs toward counting, which is right for the gate-escape count and wrong for the reviewer's `%-resolved-as-fixed`. Resolving it means two predicates, which re-opens the drift the parity test just closed. |
| 25 | own | `test-compile` caught two type errors a `quality-gate` + `module-tests` pair passed | **fixed** |

**Cold read (the plan's mandated D0 check).** Run three times against real gate output. Verdict each time: *"Would I take this green as assurance the change is sound? **No.**"* The reader could name four defect classes still open after a green run, and after the un-run line was added could also state that no test ran. D0's wording is judged to have succeeded.

⭐ Worth recording as calibration: the plugin-doctor limit line — *"it cannot evaluate whether a documented claim is true … never that the remedy the doc prescribes is reachable, is invoked, or describes what the code does"* — printed **green** in the same runs that contained a carve-out that could not fire, two unreachable remedies, and eight stale enumerations. Three consecutive rounds where the structural limit correctly predicted the class of defect the review then found. That is the plan's own thesis, reproduced inside the plan's own work.

## Reviewer participation

Population derived from configuration — the `author_login` of each `automatic-review/standards/{bot_kind}.md` registry doc — never transcribed. Verdicts read from the stored comment **bodies** across all three surfaces (`get_comments`, `get_reviews`, `get_review_comments`), never from a check state:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | **reviewed** | Published its PR Reviewer Guide against the diff — *"PR contains tests / No security concerns identified / No major issues detected"*. A publish shape against this diff, so participation is proven; it filed no actionable finding. |
| `coderabbitai` | **rate-limited** | *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in: 13 minutes."* Re-triggered once after the window elapsed; the retry returned *"Action not completed — Review rate limited"* with the window grown to 20 minutes. |
| `sourcery-ai` | **rate-limited** | *"your pull request is larger than the review limit of 150000 diff characters."* A **size** refusal, not a quota one — it does not clear by waiting, so this reviewer is structurally unavailable for a diff this size. |

**Coverage: 1 of 3.**

**The § Step 8 shortfall disclosure fired**, and said: *Review coverage 1 of 3 — `cuioss-review-bot` reviewed and reported no major issues; `coderabbitai` rate-limited (quota; re-triggered once, refused again with a grown window); `sourcery-ai` rate-limited (diff-size ceiling, will not clear by waiting). Merging on 1-of-3.* Per the contract this is a disclosure and **not** a block: blocking would strand the landing behind a third party's quota.

**One re-trigger, not more.** The contract says an aborted review is re-requested when its window permits rather than banked as coverage, so CodeRabbit was re-triggered once after its stated window elapsed. It refused again *and the window grew from 13 to 20 minutes* — an adaptive backoff. The contract also warns that a premature trigger burns a recovery attempt and resets the window, so the run stopped at one attempt rather than chasing a receding target.

⭐ **This run is itself an instance of the plan's thesis.** The plan's Problem section says *"the proxy is weakest exactly when it is being leaned on hardest"*: a run reads self-review and the in-house gates as a proxy for review quality **precisely when a bot is unavailable**. On this PR — the largest and subtlest change in the epic, and the one that changes how review coverage is measured — two of three reviewers were unavailable and the third reported no major issues. The in-house evidence carrying the landing is the four-round verification agent (25 findings, three rounds of which found real defects), full CI, and a green `./pw verify`. That is exactly the evidence class D0 now forces to state its own limits, and exactly the situation D2 exists to make measurable.

## Cost

- **Tokens:** not available to the agent in this session; the harness does not expose a usage figure to the running model. The four verification sub-agent dispatches reported their own totals: **232k / 317k / 376k / 423k** subagent tokens (1.35M across the four), over 84 / 36 / 32 / 34 tool calls.
- **Wall-clock:** not separately instrumented; no run-start timestamp was recorded at Step 1, so any figure would be reconstructed rather than measured.
- **Population:** what the sub-agent figures count is *those dispatches only* — not this session's main context. ⛔ **Not comparable to a plan-marshall `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. A single interactive cloud session does not share that boundary, so the figures are not made comparable and no comparison is offered.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named above; all resolved by bundle path |
| 2 Branch | **done** — harness-assigned `claude/review-bots-catch-gates-gpb6oe`, kept as-is, pushed to `origin` before any edit |
| 3 Plan directory | **done** — `plan.md` in place, first-instruction block present (checked, no repair needed) |
| 4 Implement | **done** — 8 commits, all carrying the trailer |
| 4 Per-commit gate | **done** — every commit touching `*.py` preceded by a clean direct `./pw` gate (`ruff` passed, `mypy` no issues, SPDX passed) |
| 4 Pushed | **done** — pushed after every commit; no unpushed commit remains |
| 5 Build gate | **done** — Python-change verdict positive; full `./pw verify` green |
| 6 Verification sub-agent | **done** — four rounds; every finding dispositioned above |
| 7 PR cycle | **done** — PR [#1239](https://github.com/cuioss/plan-marshall/pull/1239), no `skip-bot-review` (the diff touches `*.py`, `.claude/skills/**` and `marketplace/bundles/**`, and a skill is code). All three comment surfaces read: **zero actionable comments, zero inline threads**; every reviewer's participation dispositioned above |
| 8 Merge gate | **done** — conditions 1–3 met, coverage shortfall disclosed, auto-merge armed. Condition 1: every required context green on head `2434192` (`verify / conclusion`, `verify / verify`, `verify / gate`, `review / review`, `dependency-review`, `generate-check`). Non-required and disclosed rather than blocking: `Sourcery review` concluded `skipped` on its size refusal |
| 8 Bridge | **done** — no write under `doc/plans/` outside this plan's own directory |
| 9 This check | **done** — this table |
| 9 What have we learned | below |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned. **Plugin cache sync:** not owed — a machine-local build step a cloud run never performs.

## What have we learned (Step 9)

**Proposed contract change, with this run's evidence.**

§ Step 6 tells the run to re-dispatch after fixing findings, and says a pass that found a defect has not finished. It does not say what this run repeatedly hit: **a fix can be verified by a test that cannot fail.** Twice — findings #10 and #18 — a fix passed its own new test while being dead or backwards in production, because the fixture encoded a shape the producer never emits. The second time, the sibling implementation had the *same* fixture, so a parity check confirmed both were wrong together.

The contract already tells the sub-agent to sweep for test fixtures that hardcode a *retired* value. That is the mirror case and it is not covered: a fixture that hardcodes a shape the producer **never emitted at all**, which makes a brand-new check look verified.

Concrete proposed edit — one bullet in § Step 6's dispatch list:

> - the instruction that when the change adds or repairs a **predicate over stored data**, it must confirm from the **producer** that the fields the predicate reads are fields the producer actually writes — and that the test fixture carries the producer's real record shape. A fixture asserting a shape production never emits makes a dead predicate look verified; two such fixtures in sibling implementations make them agree by being wrong together.

⛔ **Not self-approved and not shipped in this PR.** Per § Step 9 this is presented to the operator, and on approval ships as its own `chore/` branch touching only the skill — never coupled to whether this plan lands.

## Residue

- **Finding #24 — the opposite-loss-function question is open.** One shared predicate now drives both counters; erring toward counting is right for the gate-escape count and wrong for the reviewer's `%-resolved-as-fixed`. Resolving it means two predicates, which re-opens the drift the parity test just closed. Deliberately left as a recorded trade rather than decided in passing.
- **The finalize step ordering is the real unblocker for D2.** Until the gate re-fires after the post-gate `mutates_source` steps, the instrument measures almost nothing. That is a change to the finalize order, out of scope here, and named in the provenance so no reader mistakes the exclusions for clean gates.
- **The residual status-summary misclassification** (a body opening with the status line and carrying same-line substance) is pinned by a test and documented; narrowing it needs the registry's `contentless_review_markers` / `actionable_content_markers` pair, which CodeRabbit does not declare.
- **Three gates carry no structural limit** — `default:ci-verify`, `finalize-step-plugin-doctor`'s step verdict, `sonar-roundtrip`.
- **The sibling epic's zero-scoped-modules / null-test-scope branch was NOT reached.** The plan's Notes ask the run to say so if it did; it did not, and nothing in the diff touches it.
- **Both lesson retirements are recorded, not performed** — the corpus is machine-local.
