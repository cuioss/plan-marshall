> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Reduce the delivery-pipeline test slice

**Epic:** test-quality
**Branch prefix:** chore — maintenance-refactor-docs

> **Blocking dependency.** This plan may not start until plans `010` (test-authoring standards and
> enforcement) and `020` (shared test harness) have **landed on `main`**. Confirm both are present in
> your clone before D1 — `grep -n 'def parse_ns' test/conftest.py` and read the module-budget section
> of `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`.
> If either is absent, **stop and report the run blocked**; do not invent a local substitute, because
> five sibling plans are converging on the same harness.
>
> **Read next.** `doc/plans/test-quality/README.md` — the epic's scoping brief, a git-tracked sibling
> in your clone. It carries the corpus census, the ten house-style rules **B1**–**B10** this plan
> applies, and the concurrency contract. The landed skills are the authority where they and the README
> disagree.

## Problem

The delivery-pipeline slice — the CI, git-provider, review and finalize surfaces — carries roughly
62,200 lines of `test_*.py` across twelve directories. Its bloat has a different shape from the
configuration slice's, and the difference decides what work actually pays here.

These tests are **scenario tests**, not table tests. A single test in
`workflow-integration-github/test_github_pr.py` stages a mixed-bot comment set, patches the provider
surface, drives a fetch, re-drives it, and asserts on dedup counters and participation sets across
both rounds. That is legitimately more than fifteen lines of work, and parametrizing it would destroy
it. The better modules in this slice already know this: `test_github_pr.py` shares one `_COMMENTS`
corpus, one `_patch_provider` helper, and one `_run_fetch` driver across its ~66 tests (a lead —
re-derive with `grep -c '^def test_' test/plan-marshall/workflow-integration-github/test_github_pr.py`,
and note the module also carries class-nested tests the module-level count misses).

What the slice spends its lines on instead is **prose**. Test docstrings here routinely run eight to
fifteen lines and are longer than the test bodies they document — and a large share of that text is
history, not invariant: which defect the test is named after, what the code "once derived", what "the
fix" now does, which plan or PR changed it. That is precisely the class of prose `CLAUDE.md`
§ Documentation Standards forbids ("No version history", "Current state only") and that
`plugin-doctor` already lints out of `marketplace/bundles/**` — but no rule has ever been scoped over
`test/`, so it accumulated here unchecked.

Two structural costs sit alongside it. The slice has the corpus's heaviest concentration of
provider-shaped fixture staging repeated per test rather than hoisted, and it is one of the heaviest
users of the subprocess `run_script` layer — in several modules re-asserting behaviour an in-process
test in the same file already covers, which is a second full assertion surface to maintain for one
contract.

## Goal

This slice's scenario tests read as scenarios: a shared, named fixture corpus per module; a driver
helper per entry point; a docstring that states the invariant in one present-tense line and adds a
second paragraph only where the invariant is genuinely non-obvious. The contracts pinned today are
still pinned, the history moves out of the test tree, and one contract is asserted at one layer.

## Deliverables

Work the slice **largest module first**.

1. **D1 — Strip history from docstrings and comments** — the slice's single largest reduction, and the
   one to do first. Apply **B3** across all twelve directories: remove plan ids, deliverable ids, PR
   numbers, lesson ids, and superseded-behaviour narration ("once derived", "the fix derives", "the
   defect this plan is named after", "PR #NNN removed") from test docstrings and comments. **Keep**
   present-tense rationale that says why an invariant is load-bearing — that is a docstring's job, and
   this slice has a lot of it worth keeping. Where a stripped paragraph carries genuine design
   rationale, hoist it into the module docstring **once** instead of repeating it per function.
   *Done when:* the `plugin-doctor` `test-docstring-historical-prose` rule (landed by `010`) reports
   zero findings over this slice, and the report carries the before/after finding count and the line
   delta attributable to D1 alone.

2. **D2 — One fixture corpus and one driver per module** — apply **B4**. Every module in the slice
   gets a single named fixture corpus for its domain objects (comment sets, check-run payloads, PR
   states, finalize-step maps) and a single driver helper per entry point it exercises, in place of
   per-test staging. `workflow-integration-github/test_github_pr.py`'s `_COMMENTS` / `_patch_provider`
   / `_run_fetch` trio is the shape to copy — it already exists in this slice and works; the deliverable
   is making it the norm rather than the exception. Where a corpus is used by three or more modules in
   the same directory, it moves into that directory's `_{domain}_fixtures.py`.
   *Done when:* no module in the slice stages the same provider or payload shape inline in three or
   more tests, and the report names each corpus and the modules that consume it.

3. **D3 — Collapse the duplicated assertion layer** — apply **B9**. Where a `run_script` subprocess
   test and an in-process test in the same module assert the same behaviour, the in-process test is
   authoritative and the subprocess coverage collapses to a **single per-script CLI-plumbing smoke**
   that proves the entry point wires up: it parses argv, it emits the declared output shape, it exits
   with the declared code. Do **not** delete subprocess coverage where it is the only coverage, and do
   **not** delete it where the subprocess boundary is itself the subject (environment propagation,
   exit-code contracts, stdout/stderr separation). Every collapse must name the in-process test that
   now carries the contract.
   *Done when:* each collapsed subprocess test is listed in the report beside the in-process test that
   subsumes it, and the collected test count for the slice has not decreased.

4. **D4 — Split every module over the budget** — the module budget landed by plan `010`, split by
   behaviour cluster into `test_{unit}_{cluster}.py`. The slice's known over-budget modules include
   `workflow-integration-github/test_github_pr.py` (~2,750),
   `phase-6-finalize/test_ci_complete_precondition.py` (~2,570),
   `tools-integration-ci/test_ci_base.py` (~2,470),
   `automatic-review/test_review_completeness.py` (~2,200),
   `workflow-integration-github/test_github_ops_pr_merge.py` (~1,840),
   `test_comments_stage.py` (~1,720), `test_github_ops.py` (~1,670) and
   `test_re_review_strategy.py` (~1,540) — **re-derive the full list**, this one is a lead. Do the
   split **after** D1 and D2, because both shrink modules and several will no longer need splitting.
   *Done when:* every `test_*.py` in the slice is within the landed budget, each new module's name
   states its cluster, and every module that moved kept its fixture corpus reachable.

5. **D5 — Normalise preambles and argument construction** — apply **B6** and **B7** across the slice:
   `conftest.load_script_module` / `get_scripts_dir` for every module preamble, `020`'s `parse_ns` for
   every `argparse.Namespace`. Where `parse_ns` cannot serve a call site, leave the hand-built
   namespace and **record the call site** — the aggregate tells the operator whether `parse_ns` needs
   widening.
   *Done when:* no `spec_from_file_location` or deep `Path(__file__).parent` chain remains in the
   slice, and every `parse_ns` exception is listed with its script.

6. **D6 — Report the measured deltas** — per-directory and slice-total line counts before and after;
   collected test count before and after; coverage before and after for the bundle paths the slice
   exercises; the D1 line delta stated separately, because it is the deliverable whose yield this epic
   most needs to know; the D3 collapse list; the `parse_ns` exception list; and the per-rule
   `test-conventions` finding counts.
   *Done when:* the report carries all seven figures, each labelled with the command that produced it.

## Out of scope

* **`test/conftest.py` and `test/_shared/**`.** Owned by plan `020` and consumed read-only here.
  Excluded because five sibling reduction plans run concurrently against the same harness, and a
  concurrent edit to it is a guaranteed collision. Note that this slice already imports
  `test/_shared/_bot_flag_derivation.py` and `_pr_agent_guide_bodies.py` — **use them, do not change
  them**; a needed change is a proposal in the report.
* **Any file under `marketplace/bundles/**`.** Excluded because test refactoring that changes
  production code is not test refactoring. A production defect found while refactoring is **recorded**,
  not fixed — and this slice, which tests the merge gate and the review barrier, is the worst place in
  the corpus to make an incidental production change.
* **Any test directory outside this plan's list.** Excluded because the neighbouring directory belongs
  to a concurrently-running sibling plan.
* **Deleting a test because it looks redundant.** Excluded because "redundant" is the judgement a line
  target corrupts. D3's subprocess collapse is the *only* sanctioned removal, it is bounded by the
  rule that every collapse names the in-process test that subsumes it, and it must not lower the
  collected count.
* **Parametrizing the scenario tests.** Excluded deliberately, and this is the difference between this
  plan and plan `030`: a two-round dedup-and-participation scenario is not a table row, and forcing it
  into `@pytest.mark.parametrize` produces an unreadable case matrix that hides which arm failed.
  Parametrize the genuinely tabular cases in this slice — bot-shape matrices, marker conjunctions,
  status-code tables — and leave the scenarios as scenarios.

## Expected surface

Exactly these directories under `test/plan-marshall/`, plus the four named root-level modules, and
nothing else:

- `automatic-review/`, `manage-ci-artifacts/`, `phase-5-execute/`, `phase-6-finalize/`
- `tools-integration-ci/`
- `workflow-integration-git/`, `workflow-integration-github/`, `workflow-integration-gitlab/`,
  `workflow-integration-sonar/`, `workflow-permission-web/`, `workflow-pr-doctor/`, `workflow-shared/`
- `test_phase_6_finalize_step_id_consistency.py`, `test_triage_loop_back_target.py`,
  `test_workflow_integration_github_ci_aggregation.py`,
  `test_workflow_integration_gitlab_ci_aggregation.py`
- `_ci_wait_contract.py` (the slice's own shared contract module — in scope, unlike `test/_shared/**`)

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The slice is ~62,200 lines across the twelve listed directories plus the named root modules | HYPOTHESIS | Re-derive with `wc -l` over the Expected surface list |
| `test_github_pr.py` already uses a shared `_COMMENTS` corpus, `_patch_provider`, and `_run_fetch`, and its docstrings routinely exceed its test bodies | OBSERVED | the file itself, roughly its first 220 lines |
| The slice carries historical narrative at scale in test prose | HYPOTHESIS | Re-derive over this slice only: `grep -rn 'once derived\|used to \|no longer\|the fix \|PR #[0-9]\|lesson-20\|this plan' ` across the Expected surface. Report the count; it is D1's baseline. |
| Some subprocess `run_script` tests in this slice duplicate an in-process test in the same module | HYPOTHESIS — **gating for D3; settle it per module before collapsing anything** | Per module, list its `run_script` call sites beside its in-process tests and identify the pairs that assert the same behaviour. A collapse performed without that pairing is a deletion, not a collapse. |
| No test in this slice is the *only* coverage of a subprocess-boundary contract that D3 would remove | HYPOTHESIS — **asserted absence, the higher-risk half** | For every candidate collapse, confirm the in-process test asserts the same contract, and name it in the report. If no in-process test does, the subprocess test stays. |
| The partition holds — every directory under `test/plan-marshall/*/` and every top-level `test/` entry appears in exactly one of `030`–`080`'s Expected surface | HYPOTHESIS — **gating and halting; run it before D1** | List the directories and check each against the six plans' Expected-surface lists; `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time" states the procedure and the two deliberate exclusions. A directory in two lists, or in **none**, is a partition defect: **halt and report it**, do not claim or skip it unilaterally |
| Plans `010` and `020` have landed and their surfaces are present in this clone | HYPOTHESIS — **gating; this plan cannot start without it** | `grep -n 'def parse_ns' test/conftest.py`; the module-budget section of `persona-module-tester/standards/testing-methodology.md`. Absent → stop and report blocked. |

## Verification

**The three-part done-when. All three must hold; the third alone is not success.**

1. **Collected test count does not decrease.** Capture pytest's collected-item count for the slice
   before the first commit and again before the PR. Record both.
2. **Coverage does not decrease** for the bundle paths this slice exercises. Record before/after and
   the command. This matters more here than anywhere else in the epic, because D3 removes assertion
   sites — coverage is the check that says whether it removed a duplicate or a contract.
3. **Line count drops by at least 25%** of the slice's starting total. The floor is lower than plan
   `030`'s because this slice's content is scenario-shaped and resists collapse; the reduction comes
   from prose, fixture hoisting, and the duplicated layer rather than from tabular collapse. If the
   floor cannot be reached without violating (1) or (2), **report the shortfall and stop**.

**Executable.** `./pw verify` (the lane's build gate; this plan changes Python). Plus the
`plugin-doctor test-conventions` scope over each directory in the slice, before and after, with the
per-rule counts recorded. Invoke the **git-tracked** script — `.plan/execute-script.py` is
git-ignored and absent from a fresh clone, so do not go looking for it:

```bash
python3 marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py test-conventions --test-root {directory}
```

Confirm the argument spelling against that script's own `--help` before relying on it. If the doctor
cannot be invoked, report the affected measurement **unavailable** rather than substituting a weaker
check.

**By reading — cold read, required for D1.** D1 rewrites text whose value is what a later reader takes
from it, and the risk is not that too much is removed but that the *invariant* is removed along with
the history. Dispatch the lane's pre-PR verification sub-agent with **five rewritten test modules and
no other context** — not this plan, not the originals — and ask, for each of ten named tests: "What
contract does this test pin, and why does it matter?" A test whose rewritten docstring cannot answer
both has been over-stripped; restore the invariant (not the history) and re-read. Record the answers
verbatim.

## Notes

* **Concurrency.** Plans `030` through `080` are mutually parallel by construction, each owning a
  disjoint slice. `doc/plans/test-quality/README.md` § "The plans, and what may run at the same time"
  carries the full partition.
* **Order within the plan matters.** D1 and D2 before D4: both shrink modules, and splitting first
  produces modules that then have to be split again.
* **D1 is the slice's largest single win and its largest single risk.** It is worth doing carefully
  and reporting separately. If the run's budget is tight, D1 plus D2 across the eight largest modules
  is worth more than every other deliverable across everything.
