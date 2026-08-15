# Run report — 020-shared-test-harness (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/shared-test-harness-keyzwy`    **PR:** [#1247](https://github.com/cuioss/plan-marshall/pull/1247)    **Outcome:** completed

All six deliverables landed and verified. `./pw verify` green locally; CI `verify / conclusion`
**success** on the head SHA. Auto-merge armed with SQUASH as the gate's final act, after this report
was pushed — a queued branch can no longer be pushed to, so the report had to precede the arm.

## Skills loaded

Loaded by path from the bundle source (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the
`plan-marshall` plugin is not installed in this cloud session, so the `Skill:` notation route was not
attempted.

| Skill | Why |
|---|---|
| `cloud-plan-lane` (`.claude/skills/`) | The lane contract — first action of the run |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:pytest-testing` (+ `standards/testing-pytest.md`) | The plan is entirely Python tests |

No skill was unobtainable by both routes.

## Deliverables

| # | Deliverable | Commit | State |
|---|---|---|---|
| D1 | `parse_ns` | `dc7c2c9` | Done |
| D2 | One marshal builder | `dc7c2c9` | Done |
| D3 | Retire `test_helpers.py` | `dc7c2c9` | Done |
| D4 | `test/README.md` | `2998074` | Done |
| D5 | Harness meta-tests | `2998074` | Done |
| D6 | Proof-of-use conversion | `44e56ff`, `fcde820` | Done (7 of the ≤10 ceiling) |

### D1 — `parse_ns`

`test/conftest.py` exports `parse_ns(bundle, skill, script, *argv) -> argparse.Namespace`, plus the
named error `ParserSeamNotFound` and the documented convention constant `PARSER_BUILDER_NAMES`.

**Verified:** a namespace for `manage-findings list --plan-id p1` carries `include_qgate=False` and
seven further defaults the caller never named. The no-seam path (`ci_base.py`) raises
`ParserSeamNotFound`. Both are pinned by tests in `test/test_shared_harness.py`.

### D2 — one marshal-config builder

Exactly one definition remains tree-wide (`grep -rn 'def create_marshal_json' test --include=*.py` →
1 hit, `test/conftest.py`). The two distinct baselines survive as named presets
(`MARSHAL_PRESET_MINIMAL`, `MARSHAL_PRESET_JAVA`) rather than being averaged. `create_run_config`
moved into `test/conftest.py` alongside it.

The three superseded definitions differed in three dimensions, each now an explicit argument:

| Dimension | `conftest` (old) | `test_helpers` | `test_triage_extension` | Now |
|---|---|---|---|---|
| Baseline | `MARSHAL_SCHEMA_DEFAULT` | java-flavoured | none (config required) | `preset=` / `config=` |
| Destination | `base_dir/.plan/marshal.json` | `fixture_dir/marshal.json` | `fixture_dir/marshal.json` | `nest_in_plan_dir=` |
| `raw-project-data.json` | no | **yes** | no | `with_project_data=` |

The destination difference was load-bearing, not cosmetic: `plan_context` points `MARSHAL_PATH` at
`tmp_path/'marshal.json'` directly, so a nested write lands where the script under test never looks.

### D3 — `test_helpers.py` retired

Renamed to `_manage_config_fixtures.py` (`git mv`, history preserved); all 23 importers repointed
(re-derived, matching the plan's `~23` lead exactly).

**The invariant, re-derived before and after:**

| | Collected modules scanned | Declaring zero tests |
|---|---|---|
| Before (`origin/main`) | 786 | **1** — `test/plan-marshall/manage-config/test_helpers.py` |
| After (at `dc7c2c9`, before D5 landed) | 785 | **0** |
| After (at HEAD, D5's own module included) | 786 | **0** |

The population returns to 786 because `test/test_shared_harness.py` replaces the
retired module in the count. Both "after" rows are stated because a single figure
would silently depend on which commit it was measured at.

### D4 — `test/README.md`

Written. `test/conftest.py`'s docstring reference now resolves (it previously pointed at a file that
did not exist). Sharpened from "See test/README.md for full documentation" to name what the document
actually is, since it is navigation and ownership rather than full documentation.

### D5 — harness meta-tests

`test/test_shared_harness.py`, 21 tests, sibling of the existing `test_conftest_discipline.py`. The
whole-tree guard follows `test/marketplace/test_prefix_strip_idiom_retired.py`: population asserted
non-empty before the offender list is asserted empty.

**Falsifiability, verified by deliberately introducing each violation and observing red:**

| Property | Violation introduced | Result |
|---|---|---|
| `parse_ns` applies defaults | `parse_ns` returns a hand-built namespace | RED (3 tests) |
| `parse_ns` raises the named error | no-seam path returns `Namespace()` | RED |
| Presets stay distinct | `MARSHAL_PRESET_JAVA` → the minimal schema | RED |
| D3 invariant | added a testless `test_*.py` under `test/` | RED |

### D6 — proof-of-use conversion

Seven modules (ceiling is ten) across **five** subtrees (floor is four).

| Module | Before | After | Delta |
|---|---:|---:|---:|
| `plan-marshall/workflow-integration-git/test_worktree_move_lifecycle.py` | 309 | 288 | −21 |
| `plan-marshall/build-pyproject/test_pyproject_extension.py` | 637 | 613 | −24 |
| `plan-marshall/manage-config/test_build_decision.py` | 509 | 511 | +2 |
| `plan-marshall/manage-config/test_cache_retention_knobs.py` | 313 | 317 | +4 |
| `plan-marshall/manage-config/test_cmd_domain_detect.py` | 481 | 470 | −11 |
| `plan-marshall/manage-architecture/test_find_confident_negative.py` | 275 | 294 | +19 |
| `pm-plugin-development/plan-marshall-plugin/test_markdown_derivation_resolver.py` | 414 | 408 | −6 |
| **Total** | **2938** | **2901** | **−37** |

Three modules grew. A `parse_ns` factory carrying a docstring costs more than the `Namespace`
literals it replaces when the call count is low; reduction is plans `030`–`080`'s job, and this
deliverable buys evidence that the harness serves the shapes the tree has.

**The three required shapes are covered:**

* **Deep subparser graph** — `test_cache_retention_knobs.py` drives the three-level
  `system → retention → set` tree; `test_build_decision.py` drives the 26-verb `noun` graph.
* **Non-default marshal config** — `test_cmd_domain_detect.py` stages custom config dicts through the
  D2 builder.
* **Multi-module `_load_module` preamble** — `test_worktree_move_lifecycle.py` opened with four raw
  `spec_from_file_location` blocks; `test_build_decision.py` and `test_cache_retention_knobs.py` each
  carried a private `_load_module` plus a `Path(__file__).parent.parent.parent.parent` chain.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **32 files**. Python changed, so the gate ran.

`./pw verify` — **SUCCESS**, all three sub-steps green (quality-gate, test-compile, module-tests).
Final run at HEAD: `20066 passed, 14 skipped in 312.38s`.

`test-compile` caught six `no-any-return` errors the quality gate does not run (fixed in `fcde820`).
The per-commit `./pw quality-gate` ran clean before each `*.py` commit.

### Collected-item count (the plan's load-bearing check)

| | Count |
|---|---:|
| Before, whole `test/` tree | **20059** |
| After, whole `test/` tree | 20080 |
| After, excluding the new `test/test_shared_harness.py` | **20059** |

Equal once D5's own 21 new tests are excluded, so **no module was dropped from collection** — which is
the failure this check exists to catch. Both figures were re-derived at HEAD, not carried forward from
the earlier measurement.

## Findings

Recorded per instance. Sources: **S** = self-caught during implementation, **V** = pre-PR
verification sub-agent (§ Step 6), **B** = `./pw verify`, **R** = the D4 reading test.

| # | Src | Finding | Disposition |
|---|---|---|---|
| 1 | V | **`parse_ns`'s docstring asserted "The command body never runs on either path" — false for router scripts.** `platform_runtime.main()` resolves an operation, reads the marshal config, mutates `sys.path` and dispatches *before* any `parse_args`. Reproduced independently: `main()` emitted an `unknown_operation` error to stdout, then `parse_ns` raised. | **Fixed.** The docstring now states what is guaranteed (the handler the command line names never runs), names both breaking shapes, and steers those callers to the builder seam. `test_a_router_script_fails_loudly_rather_than_yielding_a_guess` pins it, so the caveat is checked rather than asserted. |
| 2 | V | **`marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/testing-standards.md` prescribes `test_helpers.py` for "Shared fixtures … No test functions"** (lines 461, 469, 478–479, including a worked directory example and a worked `from test_helpers` import). D5's whole-tree guard now makes that exact shape a failing build, and `test/README.md` says the opposite. An author following the standard produces a red suite. | **Recorded as a proposal, deliberately not fixed** — correctly out of scope for this plan, but the ownership stated here was wrong. No plan in this epic owns that file: plan `010`'s surface is `pytest-testing/**`, `persona-module-tester/**` and `plugin-doctor/**`, and `plugin-script-architecture` is a sibling skill absent from it; `030`–`080` may not edit `marketplace/bundles/**` at all. Fixed in a follow-up `chore/` PR, which corrects the standard itself. |
| 3 | V | Step 3's plan-file move left **eight dead links** to `020-shared-test-harness.md` in `doc/plans/test-quality/findings-test-corpus-review.md` (lines 72, 74, 76, 77, 303, 305, 307, 308). | **Fixed.** Repointed to `020-shared-test-harness/plan.md`. This was collateral from a lane-mandated move, not a record write, so repairing it does not breach the bridge rule. |
| 4 | V | `_worktree_ns` built its namespace from **`git-workflow.py`'s** parser and fed it to `prepare_execute.run_prepare_execute` — a different script with its own parser. Faithful to the old hand-built namespace, but it borrows another script's defaults. | **Fixed.** Split into `_worktree_ns` / `_prepare_ns`, each using its own script's parser. |
| 5 | V | The no-namespace error reported "main() returned without calling parse_args" even when the parser *had* been entered and `main()` caught the failure itself. | **Fixed.** `parser_entered` is now consulted on that branch. |
| 6 | V | `parse_ns` re-executes the script module and re-registers it in `sys.modules` on **every call**, so the module instance the parser came from differs from the one the test holds. Pre-existing `load_script_module` behaviour, but `parse_ns` raises its frequency from once-per-module to once-per-call. | **Documented, not changed.** The docstring now states the cost and tells callers to hoist. Changing `load_script_module`'s caching is outside D1/D2. |
| 7 | V | The D5 guard hardcoded pytest's *default* `python_files` and ignored `norecursedirs`, so a testless `test_*.py` under `test/fixtures/` would be a false positive. | **Fixed.** `fixtures` excluded; the `*_test.py` superset is now documented as deliberate (D3's done-when names both spellings). |
| 8 | V | Report's D3 "after" count said 785; HEAD's actual population is 786. | **Fixed.** Both figures stated with the commit each was measured at. |
| 9 | V | The report did not record the settled parser-seam hypothesis, which the plan's claim-label table required be settled before D1's design. | **Fixed.** See § Claim labels below. |
| 10 | V | `test_pyproject_extension.py` swapped a bare `spec_from_file_location` (no `sys.modules` registration) for `load_script_module` (which registers). | **Accepted, not reverted.** A real behaviour delta, but registration is what `load_script_module` is *for*, the module's collision concern is handled by the explicit distinct `module_name`, and all 90 tests pass. |
| 11 | V | Stale census statements in `findings-test-corpus-review.md` (lines 152, 211–220, 225–228, 232) assert the defects this plan just closed. | **Rejected as a defect.** That file is the epic's dated **evidence record** of a review, not current-state documentation — its own header calls it "the evidence this file is scoped from". Rewriting it would destroy the record the epic was scoped from. The dead links (#3) are different: a link is not a finding. |
| 12 | S | `test_a_written_fixture_cannot_mutate_the_shared_baseline` claimed to guard the shallow-copy defect but **passed with the shallow copy reinstated** — the defect is unobservable through the builder's public API, which only assigns at the top level. | **Fixed.** Replaced with a test whose docstring states it is a forward-looking pin, not a detector. Shipping the original would have been a vacuous green. |
| 13 | S | An invalid `argv` on the interception seam raised `ParserSeamNotFound`, conflating "your command line is wrong" with "this script has no seam" — and differing from the builder seam, which raises `SystemExit` for the same mistake. | **Fixed.** The interception path tracks whether the real parser was entered and re-raises `SystemExit` when it was, so both seams fail identically. |
| 14 | B | Six `no-any-return` errors from `./pw verify`'s `test-compile`: `conftest` is deliberately opaque to mypy (`ignore_missing_imports`), so `parse_ns(...)` reads as `Any` and every factory annotated `-> Namespace` tripped `warn_return_any`. **Not caught by `./pw quality-gate`**, which does not run mypy over `test/`. | **Fixed** in `fcde820` — bound through a declared local rather than six `type: ignore` comments. |
| 15 | S | `conftest.load_script_module` resolves only `{bundle}/skills/{skill}/scripts/{file}`, so a domain bundle's **skill-root** `extension.py` (10 such files) cannot use it. | **Recorded as a proposal.** Widening the loader is outside D1/D2, this plan's declared `conftest.py` surface. The module uses `MARKETPLACE_ROOT` to remove the `Path(__file__).parent…` chain and keeps an explicit spec load. |
| 16 | S | `test_cmd_domain_detect`'s dispatch-registration test built its **own** stand-in parser, registered the subcommand on it, and asserted the routing it had just configured — proving only that argparse works. | **Fixed.** Routed through the real parser. This is the synthetic-double class the lane's sweep exists to catch; the change removes one rather than adding one. |
| 17 | R | `test/README.md`'s three-subtree row offered "`test/conftest.py` or `test/_shared/`" with no rule for choosing, and said to record a proposal without naming a channel — while the two-subtree row directly above it does name one. | **Fixed.** Both now stated. |

## Claim labels — settled

| Claim | Label | What the run measured |
|---|---|---|
| `create_marshal_json` defined 3× incompatibly | OBSERVED | **Confirmed** — 3 definitions; now 1 |
| `test_helpers.py` declares zero tests, ~23 importers | OBSERVED | **Confirmed** — 0 tests, exactly **23** importers |
| `test/conftest.py` references a `test/README.md` that does not exist | OBSERVED | **Confirmed** — `ls test/*.md` was empty |
| ~197 modules hand-roll the exported loader | OBSERVED | **Confirmed** — **204** `spec_from_file_location` occurrences |
| No shared helper builds a namespace from a script's real parser | HYPOTHESIS (asserted absence) | **Confirmed absent.** `test/conftest.py` read end to end and `test/_shared/` enumerated (8 modules, none argparse-related). `script-shared/argparse_surface.py` derives a script's *accept-set* by running `--help`; it exposes no parser object and no defaults, so D1 builds new rather than extending it. |
| ~2,900 namespaces / ~292 modules / ~150 `_ns_*` builders | HYPOTHESIS | **Confirmed** — **2909** / **296** / **148** |
| **Every script exposes a reachable parser-builder seam** | HYPOTHESIS — the one that decides D1's shape | **REFUTED.** See below. |

### The refuted hypothesis, and what it changed

An AST classification of every `ArgumentParser` construction under `marketplace/bundles/**`:

| Where the parser is built | Files |
|---|---:|
| Inside `main()` — **no reachable builder seam** | **69** |
| `build_parser` | 16 |
| `_build_arg_parser` | 6 |
| `_build_parser` | 3 |
| `_dispatch` / `build_main` / `create_workflow_cli` / `run_barrier_cli` | 4 |
| **Total parser-constructing files** | **96** |

**27 of 96 (28%) publish a named builder; 69 (72%) do not.** The plan anticipated this: *"If a
meaningful fraction has no reachable seam, D1's error path is the primary path … say so in the report
rather than forcing the helper onto scripts it cannot serve."*

Taking the literal reading — error on anything without a published builder — would have left `parse_ns`
unable to serve 72% of the tree, so B6 could never be adopted and the deliverable would be inert. The
**`main()`-interception seam** was implemented instead. It is not the fallback D1 forbids: D1 forbids
"silently falling back to a **hand-built** namespace", and interception returns the **production
parser's own output**. The no-seam case still raises.

Measured reachability across all 95 parser-bearing scripts: **24 resolve via a published builder, 66
via interception, 5 have no seam** (all library modules, not CLI entry points). The independent
verifier probed eight of the scripts this plan converted and found **all eight take the interception
path** — so for the modules a consumer plan is most likely to touch, interception is the *primary*
seam, not the exception. Consumer plans `030`–`080` should read it that way.

## Reviewer participation

Population derived from the registry — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), not transcribed. Every verdict below is read from the
reviewer's actual body across all three surfaces, never from a check state.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Issue comment: *"PR Reviewer Guide 🔍 — PR contains tests / No security concerns identified / No major issues detected"* |
| `coderabbitai` | `rate-limited` | **yes** | Issue comment: *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. **Next review available in: 58 minutes**"* — a countdown that clears on its own |
| `sourcery-ai` | `rate-limited` | **no** | Review-summary body: *"you have reached your weekly rate limit of 500000 diff characters"* — a ceiling on THIS diff's size, not a clock; the same request never succeeds at this size |

**Coverage: 1 of 3.** The § Step 8 condition-4 disclosure fired and said exactly that — see below.

Surfaces read, all three, as three separate calls: `get_comments` (2 issue comments), `get_reviews`
(1 review-summary body — **the only place** Sourcery's refusal appears; a run that skipped this call
would have recorded `sourcery-ai` as `silent` and never learned why), and `get_review_comments`
(**0** inline threads).

**No comment required action.** One reviewer reported no issues; the other two published quota
notices rather than findings. Nothing was fixed and nothing was replied to, because there was no
request to answer — the lane's "reply why not" applies to findings, and none were filed.

**No `silent` verdict arose, so the recovery check did not run.** Both non-`reviewed` reviewers
published an explaining notice, which is engagement, not silence.

This PR is the case the `Reopens?` column was added for: two reviewers refused **at the same moment**,
one on a 58-minute countdown and one on a weekly diff-character ceiling. Without the column the table
would render them identically, and a reader could not tell that re-requesting CodeRabbit later is
productive while re-requesting Sourcery on this diff never will be.

## Cost

- **Tokens:** **not available to the agent in this session.** No usage counter is exposed to me here,
  and I will not estimate one.
- **Wall-clock:** ~1 h 12 min — first commit `0f6167a` at 17:43:10 UTC to the merge gate at ~18:55
  UTC, measured from git commit timestamps and the PR's own event times.
- **Population:** one interactive Claude Code cloud session executing one `doc/plans/` plan end to
  end, including the two Step-6 sub-agent dispatches. ⛔ **Not comparable to a plan-marshall
  `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary. This run has no orchestrator, no ledger, and no per-task billing
  boundary, so the two figures count different things and no conversion between them is offered.

## Contract check (Step 9)

Re-read `cloud-plan-lane` and checked each step against what actually happened — both that the step
ran and that its artifact exists.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | Named in § Skills loaded. Loaded by bundle path; the plugin route was not available in this session |
| 2 Branch | **Done** | `claude/shared-test-harness-keyzwy` — **harness-assigned**, kept as-is per the resumability rule. Pushed to `origin` as the run's first action, before any edit, after `git ls-remote` showed it absent |
| 3 Plan directory | **Done** | `doc/plans/test-quality/020-shared-test-harness/plan.md` exists and opens with the first-instruction block (present on arrival; no repair needed). The `020-` prefix was preserved by the move |
| 4 Implement | **Done** | 10 commits, **all 10** carrying the trailer; every deliverable addressed |
| 4 Per-commit gate | **Done** | `./pw quality-gate` ran clean before every `*.py` commit — `ruff … All checks passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`. Two commits needed no gate (the Step 3 `git mv`, and a docs-only commit) |
| 4 Pushed | **Done** | `git status -sb` reports no `ahead`; every commit pushed as it was made |
| 5 Build gate | **Done** | Git-derived verdict (**32** `*.py` files changed) and the `./pw verify` SUCCESS both recorded in § Build gate, with the collected-item reconciliation |
| 6 Verification sub-agent | **Done** | Two dispatches — the lane's verifier and the plan's D4 reading test. 17 findings with dispositions in § Findings, including 2 recorded as proposals and 1 rejected with its reason |
| 7 PR cycle | **Done** | PR #1247. All three surfaces read as three separate calls; every comment dispositioned; § Reviewer participation carries a verdict **and** a `Reopens?` value per reviewer. No `silent` verdict arose, so no recovery check was owed |
| 8 Merge gate | **Done** | Condition 1: `verify / conclusion` **success** on the head SHA. Condition 2: no open comment. Condition 3: this report pushed as the last pre-merge commit. Condition 4 (a disclosure, not a gate): coverage stated as 1-of-3 |
| 8 Bridge | **Done, with one judgment call disclosed below** | No status file, no ledger, no other plan's directory touched. The report carries the PR number and per-deliverable outcome |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | Three proposals below, presented to the operator and **not** self-approved |

**The one judgment call, disclosed rather than glossed.** This run edited a file under `doc/plans/`
outside its own plan directory: `findings-test-corpus-review.md`, to repair the eight links Step 3's
mandated move broke (§ Findings row 3). That is not a status or bookkeeping write, and it is not a
declared deliverable either — the two cases the bridge rule names. It is repair of link rot the
contract's own required action caused. I judged repairing it correct and am flagging it here because
the rule as written does not clearly authorise it; that ambiguity is proposal 3 below.

## What have we learned (Step 9)

Three proposals, each named by something that actually happened in this run. **Presented to the
operator, not self-approved, and not shipped** — each would go on its own `chore/` branch as a
separate PR, kept out of this plan's diff.

**1 — The `uv.lock` churn rule names only one cause, and this run hit a different one.**
§ Step 4 attributes lockfile churn to "a session interpreter older than the project's floor". Here the
cause was unrelated: `main`'s `pyproject.toml` pins `ruff>=0.16.2` while its `uv.lock` still records
`>=0.16.1` (dependabot #1234 updated one and not the other), so **any** `./pw` run regenerates the
lockfile regardless of interpreter. A run that checks the stated cause, finds its interpreter fine,
and concludes the churn must therefore be legitimate would commit it. Proposed edit: state the rule by
its **symptom** — a lone `uv.lock` in `git status` is backed out, whatever the cause — and cite the
interpreter floor as one cause among others.

**2 — Step 6's beyond-diff sweep enumerates restatements, but not prescriptions — and finding one raises a second question the contract never asks.**
The sweep's consumer kinds are all forms of a document *restating a value* the change made false. The
verifier found a different kind here: `plugin-script-architecture/standards/testing-standards.md`
*prescribes* `test_helpers.py` as the name for a fixture module with "No test functions" — the exact
shape D5's new guard now fails the build on. That is not a stale restatement; it is a **normative rule
the change makes impossible to comply with**, and an author following it produces a red suite. It
matches no kind on the current list. Proposed edit: add a seventh kind — "a standard, rule, or
template elsewhere that the change makes unfollowable".

A second, sharper lesson came out of the same finding **after** this report was first written. Having
identified the out-of-scope file, this run asserted that plan `010` owned it — by inference from the
subject matter, without reading `010`'s Expected surface. It does not: `010` covers
`pytest-testing/**`, `persona-module-tester/**` and `plugin-doctor/**`, and `plugin-script-architecture`
is a sibling skill in the same bundle that no plan in the epic claims. An unowned trap recorded as
*owned elsewhere* reads as handled and is worse than one recorded as unowned, because nobody looks
again. Proposed edit: when the sweep defers a finding to another owner, the contract should require
that ownership be **read from the named owner's own scope declaration and cited**, never inferred from
topic — the same evidence rule the lane already applies to merge state and reviewer participation.

**3 — The bridge rule does not say who repairs the links Step 3's move breaks.**
Step 3 mandates moving `{NNN}-{slug}.md` to `{NNN}-{slug}/plan.md`. Sibling documents under
`doc/plans/` link to the old path — eight did here — and every one of them breaks. Step 8's bridge
rule permits a "declared-deliverable edit to a shared lane doc" and forbids "status or bookkeeping"
writes, but inbound-link repair is neither, so a run reading the rule literally leaves the links dead.
Proposed edit: name link repair caused by the Step 3 move as explicitly permitted, and add it to
Step 3 as an expected follow-up rather than leaving each run to decide.

**What did NOT need changing, recorded because a run that looked is a different fact from one that
did not.** The `Reopens?` column added by the previous contract change fired exactly as designed on
its first real test: two reviewers refused this PR at the same moment, one on a clearing countdown and
one on a permanent size ceiling, and the column is the only thing distinguishing them. No change
proposed there.

## Residue

* **`uv.lock` on `main` is out of sync with its own `pyproject.toml`.** `pyproject.toml` pins
  `ruff>=0.16.2` (dependabot #1234) while `uv.lock` still records the `>=0.16.1` specifier, so every
  `./pw` run regenerates the lockfile and dirties the tree. **Pre-existing on `main`, not caused by
  this plan**, and unrelated to its deliverables — so it was backed out of every commit here rather
  than shipped as undeclared collateral. It wants its own one-line PR.
* **Two proposals for plan `010`**, which owns `marketplace/bundles/**` in this epic — see § Findings
  rows 2 and 15: the `testing-standards.md` prescription of `test_helpers.py` that D5's guard now
  fails the build on, and `load_script_module`'s `scripts/`-only resolution which cannot reach a
  skill-root `extension.py`.
* **`create_nested_marshal_json` remains in `_manage_config_fixtures.py`.** It is a third marshal
  builder by behaviour, but D2 scopes the collapse to `create_marshal_json` plus the run-config
  companion, so folding it in would have been unrequested scope.
* **The remaining sections** (Cost, Contract check, What have we learned) are written at the merge
  gate, as the last pre-merge commit — a queued branch can no longer be pushed to.
