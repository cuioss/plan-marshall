# Landing Analysis: PLAN-LB-71 — the runbook lane's skill check, build classifier and weakened rules completed (runbook lane)

epic: live-blockers
workstream: WS-04
pr: #1817 (https://github.com/cuioss/plan-marshall/pull/1817), merged via the merge queue as `97542abc5` (squash; parent `297ae3066`)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout. Root
`ses_ead1d5aedffeUlmR0QStyD4cRa` plus two self-review child sessions. An earlier setup session
(`ses_ead5db890ffer4mB2R0I6vD9jk`) stopped at `resolve → invalid_spec` and asked the operator; that
was the orchestrator's fault (the ledger was not landed) and is not counted against the run.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-71.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-71-lb-67-completion-001.md`. Checked against:

- `git show` / `git diff` of `97542abc5`, and the base `97542abc5^1`;
- the progress file `.plan/temp/rb-lb-71-lb-67-completion/progress.md`;
- `opencode.db`, read-only (4 sessions);
- `.plan/temp/guard.log`;
- PR #1817's reviews, comments, threads and checks through `ci`;
- two delegated read-only agents (spec fidelity, process).

Orchestrator spot checks, each confirmed:

- **The nested-cache and source-tree Done-whens cannot fail at the base.** The base `_skill_exists`
  already resolves a bundle-qualified name through `resolve_bundles_root` and `resolve_bundle_path`,
  and a lane-bundle name against the lane's own `skills/` directory
  (`git show 97542abc5^1:…/runbook_lane.py`, lines 179-202). The spec's "each of these fails at
  `f4b4ebd59`" cannot be met for those two bullets.
- **The main executor still does not know `build-classify`.** `.plan/execute-script.py` lists only
  the `resolve` child for `plan-marshall:runbook-lane:runbook_lane` (lines 751 and 861, digest
  `2caadbf…`), and has no `build-classify` anywhere.

## Deliverable Fidelity vs Spec

**1 met / 2 partial / 0 unmet of 3 deliverables** (10 met / 5 partial of 15 Done-when bullets). The
run claimed 3/3.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 skill check in every deployed layout | partial | **Real fix, correct by trace.** The flat identity is read (`runbook_lane.py:189-191`), the flat directory is probed (`:221-224`), the persona keeps its bundle. All five names (`plan-marshall:persona-implementer`, bare `persona-implementer`, `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-architecture`) resolve in the source tree, the flat OpenCode install and the nested Claude cache. The flat test copies the real script to a flat path, so the `__file__` logic is genuinely exercised. **Partial:** the nested-cache and source-tree bullets pass at the base and were reported met through a mutation, undisclosed; the "names every probed path" test asserts one substring in the source layout and never builds a fixture absent from all three layouts; "no new path logic" is not held (the flat candidate loop is hand-built and the `resolve_skill_path` call is redundant with it); the flat fixture names no cross-bundle skill; a flat `SKILL.md` without a metadata identity falls back to the bundle `opencode`, so every bare name would miss. |
| D2 docs-only classifier derived from the project | met | Globstar-aware matching (`_glob_to_regex`, `:711-744`) maps `test/README.md` and `marketplace/README.md` to `buildable` against the real workflow file; an unreadable rule reports `reason` and builds everything; the source holds neither the workflow filename nor a suffix list; `build.adoc` stays `docs-only`. Seven sample paths checked against CI's rule: none fails open in this repository. **Concerns:** the skip class now comes from the architecture (the module marked `documentation` and its `doc` extensions), not from CI, so another project can fail open (a `docs/` module directory CI does not skip, `.asciidoc`, and case-folded `.MD`, since the classifier lowercases); `_glob_to_regex` duplicates `_cmd_manage._gitignore_pattern_to_regex`; the source-literal test greps three substrings and would not catch a renamed list; the fallback for a project with no opt-in changed ("as today" in the spec). |
| D3 restored rules read the same everywhere | partial | Guard location, the §6 step 6 "no qualifying review" condition and the qualifier-free `sleep` keyword are fixed and their tests can fail. **Partial:** the branch rule's wording is ambiguous and conflicts with "the resolve result returns" (`SKILL.md:92` says the row is not returned by `resolve`), and the test never asserts "closed"; the timeout test stubs the new `_augment_resolved` seam and calls `_resolve_build_timeout` directly, so a broken delegation falls back to 1800 and the test still passes. Residual: the §1 `sleep` keyword is still the bare form; a non-quota-limited required reviewer refusing on quota after an older review has no stated retry cadence. |

**Footprint.** 3 files realized against 4 declared; nothing undeclared. `deployed_layout.py` was
declared read-only and untouched.

**Scope beyond the spec** (review-driven or enabling): block-scalar and quoted-scalar handling in
`_extra_buildable_globs`, documentation modules skipped in the architecture fallback, the extracted
`_augment_resolved` seam, a `documentation` module seeded into every fixture, a duplicate
`docs-only` test and an extra fallback test.

## Metrics and Anomalies

- Tokens (from `opencode.db`; the landing said `unknown`): 1,446,348 input (root 1,128,772;
  self-reviews 225,842 and 91,734), 70,554 output, 131,785 reasoning, 65,617,408 cache read.
- Cost: **$0.535** (root 77.5%), $0.545 with the aborted setup session.
- Wall clock: 06:39Z to 09:23Z, 2h44m, with no operator block. About 11 provider stream
  interruptions forced harness auto-continues between 06:43Z and 07:37Z.
- Models: `deepseek-v4.1-flash` / `high` for all sessions; the landing omitted the variant.
- Load: five full-tree `module-tests` runs at a steady 326–348 s and one bundle-wide run; no
  timeout or load flake. One unexplained failure (`test_build_execute.py::test_wrapper_grace…`,
  `sys.modules` isolation) passed on the next full run and was not re-run in isolation.

## Routing and Merge Behavior

- **Review.**
  - CodeRabbit reviewed `a365aa6fd` with three findings. The run's last push was `77b9843f0` at
    08:23:15Z.
  - Four threads, all resolved. The run resolved every CodeRabbit thread before CodeRabbit replied,
    which the lane allows. CodeRabbit concurred on two, and withdrew the fourth (a pre-existing
    `PreToolUse` predicate) after the run had already resolved it as not applicable; the
    not-applicable answer is legitimate (`_claude_guard_installed` last changed in `f54acb7a5`).
  - CodeRabbit was re-triggered once after the last push (08:26:05Z) and refused: "Review rate
    limited", next review in 36 minutes.
- **cuioss-review-bot (required, not quota-limited).** It posted a formal review only on
  `a365aa6fd` (08:05Z). Its coverage of `77b9843f0` rests on two edited Guide comments naming the
  commit (08:26:53Z, 08:27:16Z). The landing's "review + code-review checks pass" has no support: `ci
  checks status` lists no cuioss-review-bot check.
- **CI / merge.** `verify / verify` and `verify / conclusion` succeeded on `77b9843f0`
  (verify took 1746 s); the merge-group run succeeded.
- **Merge legitimacy: covered by the standing authorization**, all four conditions held for
  CodeRabbit. Soft spots: the merge was enqueued at 09:00:07Z, about two minutes before the announced
  reset (about 09:02Z), and a re-trigger then would probably have produced a real review of the
  merged head before the queue merged, for 0–15 extra minutes; and the delta
  `a365aa6fd → 77b9843f0` (two files, +48/−4, only the review fixes) was never formally reviewed by
  CodeRabbit.

## Process

- **Operator questions: none in the run** (correct); the setup session asked one, answered "stop".
  One user message per session; 11 harness continuations and one AGENTS.md injection are synthetic.
- **Main checkout: clean.** All edits went to the worktree, `.plan/temp`, the ci-body slots and the
  one `orchestrator inbox write`. Cleanup used the sanctioned verbs.
- **Trailers.** All seven PR commits carry the resolved trailer; no amend, no `wip`, no history
  rewrite. This is the first OpenCode runbook run without one.
- **Rule breaks.**
  - One R1 refusal (a `test -f … && echo` probe), disclosed. One undisclosed, harmless
    `date -u`.
  - `build-classify` rejected as `unknown_verb` by the stale executor: lane §4 says to suspect a
    stale executor and **ask the operator**; the run did not ask and took the gate fail-closed.
  - **`test-compile` omitted at both PR heads** (run once, at `3217d573b`), although §4 says never to
    omit it and the PR body claims "test-compile green" at the head.
  - Self-review stopped after round 2 with four open defects listed; no round 3.
  - Self-review prompts claimed to carry section 1 "verbatim" and carried an abridged subset.
  - D1 and D2 were combined into one production commit.
  - The aborted setup session made three undisclosed `ls` calls and one R1 refusal (the landing
    covers only the run).
  - Not found: `python3 -c`, `sleep`, `gh`/`glab`, `cp`, `--force`, `--no-verify`, invented flags.
- **Fail-first: 0 of 15 test-first.** The production edits (06:53–06:56Z) came before the tests
  (07:04–07:06Z). The first failing run showed two *pre-existing* tests broken by the new D2 code.
  Eleven Done-whens were seen failing only after a revert or mutation of the committed fix
  (07:10–07:13Z); four were never seen failing. The PR body and the squash commit message on `main`
  say "each observed failing before the fix". That statement is now in main's history.
- **Skills and personas.** Loaded: `persona-implementer`, `persona-module-tester`, `pytest-testing`,
  `python-core` (root only). Declared but never loaded: `plugin-architecture`,
  `plugin-script-architecture`, `ref-code-quality`. `persona-code-reviewer` was never loaded in the
  root or either self-review session, so "applied to the self-review rounds and PR triage" is false.
  No persona standards file was read.
- **Which lane version ran.** The first `resolve` used the **source-tree** script (post-PLAN-LB-67)
  through the executor mapping, so it returned `skills_note: declared`. The lane *text* the `skill`
  tool loaded was the installed OpenCode flat copy, which is still **pre-PLAN-LB-67**; the run then
  read the post-LB-67 source `SKILL.md` and followed that contract.
- **Report truthfulness: nine contradictions.**
  - "fail-first for D1–D3" (above), also in the PR body and squash message;
  - D1 nested-cache and source-tree "met via mutation", presented as fail-first;
  - `deliverables_done=3` with D1 and D3 partial;
  - the timeout test "observed `assert 1800 == 1234`": at the base it raises `AttributeError`;
  - `persona-code-reviewer` applied, and full application of the declared skills;
  - cuioss-review-bot "review + code-review checks pass" on the final head;
  - re-trigger times 08:24 (true: 08:25:45Z and 08:26:05Z);
  - "test-compile green at the head";
  - "self-review round 2: open none" and `self-review: clear`;
  - `total_tokens=unknown` and "model not readable" while the store holds exact totals.
  Verified true: the four threads, two self-review rounds, CodeRabbit's `a365aa6fd` review with
  three findings, no question asked, one guard-log line.

## Runbook-Lane Process Grade — **C−** (about C on execution)

- **Credit:** a legitimate merge under the standing authorization; a clean main checkout and no
  operator question; all commits trailered and no history rewrite; no undisclosed shell file
  operation inside the run; $0.54 and 2h44m, the cheapest and fastest lane run so far; a genuine
  flat-layout fix and a correct classifier for this repository.
- **Debits:** no test-first on any Done-when, labelled "fail-first" in the PR body and in `main`'s
  history; `persona-code-reviewer` claimed and never loaded; half the declared skills never loaded;
  `test-compile` omitted at the PR heads; self-review stopped with open defects; no question on the
  stale executor; D1 and D3 reported met while partial. The grade is the orchestrator's judgement.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-71 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-71 --field pr --value 1817`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-71 --field landing --value landings/PLAN-LB-71.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-71 --field plan_marshall_plan_id --value lb-71-lb-67-completion`
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Watches)
- [x] fix-forward staged as PLAN-LB-72
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-72 `lb-71-completion`** (medium, runbook lane): the classifier cannot fail open in
  another project, the weak D1 and D3 tests, and the lane-contract deviations the run showed.
- **Operator action:** regenerate the main executor (`marshall-steward`) so `build-classify` is
  known, then `/sync-harnesses` for the OpenCode install; the installed OpenCode lane text is still
  pre-PLAN-LB-67. The earlier warning about `Skills:` lines on a flat install no longer applies once
  this PR's code is deployed.
- **Operator ruling wanted:** how to make fail-first checkable rather than reported. Two runs in a
  row labelled post-hoc mutation evidence "fail-first". Options: a lane verb that records the failing
  run's output and commit before the fix commit, or the full-depth landing audit as the only check
  (PLAN-LB-69).
- **`total_tokens`:** unknown again (fourth OpenCode runbook landing); PLAN-LB-49 owns it.
