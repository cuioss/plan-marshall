# Run report — test-quality epic authoring (run 01)

**Date (UTC):** 2026-08-15  **Branch:** `claude/test-corpus-review-quality-lstvf7`  **PR:** #1240
**Outcome:** completed

> **This run authored an epic; it did not execute a plan.** The `cloud-plan-lane` contract assumes one
> plan per run, so two of its steps have no counterpart here and are reported as not-applicable rather
> than narrated as done — see § Contract check. This report therefore lives at the epic root rather
> than in a `{plan-name}/` directory, because no plan directory exists to own it: every plan in this
> epic is still a flat `{NNN}-{slug}.md`, which the tree's own status model defines as "authored and
> waiting". That location is a deliberate deviation, disclosed here.

## Skills loaded

| Skill | Route |
|---|---|
| `plan-marshall:ref-code-quality` | read from `marketplace/bundles/…/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | read from `marketplace/bundles/…/SKILL.md` |
| `.claude/skills/cloud-plan-lane` | loaded as the first action, per the mandatory block |
| `.claude/skills/author-cloud-plan` | loaded at authoring time — this run's subject |

No conditional skill applied: the diff is `doc/**` markdown only. Both "always" skills were read via
the bundle path (the plugin-notation route was not attempted).

## Deliverables

The deliverable was the epic itself: a scoping brief and eight plans, authored against
`author-cloud-plan` and `doc/plans/_template/plan.md`.

| Artifact | Commit | State |
|---|---|---|
| `doc/plans/test-quality/README.md` — census, house style **B1**–**B10**, concurrency contract | `40096ba` … `d508c58` | complete |
| `010` — test-authoring standards + four `plugin-doctor` rules | `40096ba` … `d508c58` | complete |
| `020` — shared test harness | `40096ba` … `d508c58` | complete |
| `030`–`080` — six reduction plans over disjoint slices | `40096ba` … `d508c58` | complete |
| `doc/plans/README.md`, `cloud-bridge.md`, `_template/plan.md` — admit the standalone-epic concept | `40096ba`, `404dadc` | complete |

**Partition, re-derived at report time.** 69 directories under `test/plan-marshall/*/` and 12
root-level files there, each claimed by exactly one of `030`–`080`; every top-level `test/` entry
claimed or on the three-item exclusion list. The six slice totals — 53,767 / 62,192 / 79,402 / 61,369
/ 61,324 / 58,877 — sum to **376,931**, exactly the corpus total over 770 `test_*.py` files. Complete
and non-overlapping.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty**. No buildable footprint; local build
skipped per the lane's `*.py`-only gate. The merge queue's `merge_group` run is the net for a
docs-only change, and CI confirmed the designed path: `verify / gate` **success**, `verify / verify`
**skipped** (the `skip-on-docs-only` footprint gate), with `verify / conclusion` still reporting.

## Findings

Four independent pre-PR verification passes were dispatched, each after fixing the previous one's
findings. Counts: **30 → 11 (+5 nits) → 8 → 6**. Findings are recorded per instance below in
aggregate form, with the per-instance detail in the four fix commits' messages
(`404dadc`, `1ad419a`, `0299b48`, `d508c58`).

### By disposition

| Disposition | Count | Notes |
|---|---|---|
| Fixed | 48 | across the four fix commits |
| Deferred as operator proposal | 2 | contract edits this run may not self-approve — see § What have we learned |
| Rejected with reason | 1 | uniform six-deliverable count — see below |

### The findings that mattered

**Two were only findable by execution, not by reading.** Both concerned commands the plans instruct
future runs to invoke:

1. The `plugin-doctor` invocation did not run at all — `doctor-marketplace.py` has no `sys.path`
   bootstrap and its import chain reaches into other skills' scripts directories, so a bare call dies
   with `ModuleNotFoundError: No module named '_dep_detection'`. Fixed once **incorrectly** (see 2),
   then fixed by supplying the five required scripts directories on `PYTHONPATH` in one command.
   Verified by running it: `status: fail`, `total_issues: 17`, three rules reporting.
2. That first fix made the command work by generating `.plan/execute-script.py` — which
   `cloud-plan-lane` forbids in three separate places ("this lane never touches `.plan/`"). A working
   command that violates the contract governing all eight runs is not a fix. The replacement touches
   no `.plan/`, uses no shell substitution, writes nothing, and leaves the tree clean.

**One was a mechanism error in a fix.** Plan `010`'s zero-match-invariant compliance was routed
through `record_fired()`, which populates a module-level `_EXTRA_FIRED` set — process-local, while the
canonical gate runs under `pytest-xdist` (`-n auto --dist=loadgroup`). `fired_rule_ids()` executes
`build_fixture_corpus()` in-process, so a `FIXTURE_CORPUS` entry is the process-independent route. The
stated reason for avoiding `_fixtures.py` was also wrong: plan `080` renames that file, but `080`
cannot start until `010` has landed, so the two are sequential and there was never a collision.

**Three factual claims in the authored text were overstated**, each corrected with its re-derivation
rather than merely softened:

| Claim as authored | Actual | Consequence |
|---|---|---|
| `_includes_{knob}` family is ~11 pairs asserting the same default twice | 22 functions share the naming shape; **only 3 knobs** are crossed against both accessors | This was the epic's headline exemplar in two documents and it shaped plan `030` D1's design. D1 now derives the family's real membership before collapsing. |
| `build_test_helpers.py` serves the six `build-*` directories | **four** of six | Plan `070` D1 is two jobs — consolidate four, onboard two — not one. |
| `080` ~60 modules; `040` ~50 tests; `020` ~253 call sites | 79 / 66 / 231 | Each sizes a deliverable; each now carries a re-derivation. |

**One structural finding stands out.** The **partition** — the epic's load-bearing premise — was a
hand-written list with no derivation and no completeness check, while every other count carried one. A
directory added between authoring and a run would have belonged to no plan and been silently skipped.
It is now a gating, halting derivation in all six reduction plans. Two subsequent passes then found
that check itself false-halting, first on `test/conftest.py` and then on the top-level
`test/plan-marshall/` entry; both are now named exclusions.

### Rejected, with reason

**All eight plans sit at exactly six deliverables**, which the template calls a signal to split. Not
split, for two reasons: the epic already carries eight plans gated on two blocking predecessors, and
deepening that graph costs more coordination than it buys; and the genuinely code-changing count is
five per plan (each D6 is report-only), or four for `060` and `080`. The reviewer's counter — that a
*sequential* split within one slice would preserve disjointness — is correct and is recorded here as a
live option for `050` and `070`, whose D1 each carry most of their plan's value.

## Reviewer participation

Population derived from configuration — the `author_login` of every registry doc under
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/` — not transcribed:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | **reviewed** | Issue comment "PR Reviewer Guide 🔍" over the diff: *No relevant tests / No security concerns identified / No major issues detected*. An explicit nothing-to-report against this diff. |
| `coderabbitai` | **rate-limited** | Issue comment: *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in: 42 minutes."* A refusal notice in place of a review — it engaged but did not review this diff. |
| `sourcery-ai` | **rate-limited** | Review-summary body: *"your pull request is larger than the review limit of 150000 diff characters."* A size refusal, not a quota one. The `Sourcery review` check's `skipped` conclusion is the same event; the check state alone is not the evidence, the body is. |

**Coverage: 1 of 3.** Verdicts are derived from the stored comment bodies across all three surfaces —
`get_reviews` (where Sourcery's refusal arrived and nowhere else), `get_comments` (CodeRabbit's
refusal and the review-bot's guide), and `get_review_comments` (zero threads). No check state was used
as a verdict.

**No actionable comment was raised**, so none required a fix or a thread reply: the one reviewer that
participated reported no issues, and the other two published refusals rather than findings. Both
refusals are routine and outside this run's control, so per § Step 8 condition 4 they are **disclosed,
not blocked on** — the shortfall changes what this run says, never whether it merges.

One of the two refusals is worth carrying forward rather than filing as noise: Sourcery declined on
**diff size**, not quota. This PR is ~2,400 added lines of prose. A future epic authored as one PR of
comparable size will hit the same ceiling, so an author who wants Sourcery's coverage should split the
authoring PR — recorded in § Residue.

Coverage is stated to the operator at the merge gate, per § Step 8 condition 4. The PR deliberately
carries **no** `skip-bot-review` label: the diff is `doc/**` only, which the contract's path rule
would permit skipping, but these files are behavioural prose that governs eight future runs and two of
them (`cloud-bridge.md`, `_template/plan.md`) are lane-contract documents. Suppressing review there
would suppress scrutiny, not waste. That reading is itself a proposed contract clarification — see
§ What have we learned.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately instrumented. Four verification sub-agents ran to completion,
  reporting 205k / 203k / 129k / 125k subagent tokens and 69 / 91 / 67 / 54 tool calls respectively —
  those four figures are the sub-agents' own self-reported usage, not the session total.
- **Population:** the four sub-agent figures count only those dispatched agents. They are **not**
  comparable to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch
  tree under a per-task billing boundary this interactive cloud session does not share. No session
  total is reported because none was available; a derived number would imply a parity that does not
  exist.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **done** — named above |
| 2 Branch | **done** — harness-assigned `claude/test-corpus-review-quality-lstvf7`, kept as-is; confirmed on `origin` before the first edit; clean tree asserted at start |
| 3 Plan directory | **not applicable** — this run authored plans rather than executing one. A flat `{NNN}-{slug}.md` is the tree's own "authored and waiting" state; creating eight `{plan-name}/` directories would falsely signal eight started runs. Not narrated as done. |
| 4 Implement | **done** — five commits, each with the trailer |
| 4 Per-commit gate | **not applicable** — no commit touched `*.py` |
| 4 Pushed | **done** — pushed after every commit; no unpushed commit remains |
| 5 Build gate | **done** — git-derived verdict: no `*.py`; build skipped, recorded above |
| 6 Verification sub-agent | **done** — four passes, findings and dispositions above |
| 7 PR cycle | **done** — PR #1240; comment dispositions in § Residue until the cycle closes |
| 8 Merge gate | see § Residue |
| 8 Bridge | **done** — no status or bookkeeping write landed under `doc/plans/` outside this epic. The edits to `doc/plans/README.md`, `cloud-bridge.md` and `_template/plan.md` are **declared deliverables** (shared lane docs), which the bridge rule permits. |
| 9 This check | **done** — this table |
| 9 What have we learned | **done** — below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this session).
**Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a cloud run never performs or records one.

**Commit trailer deviation, disclosed.** The contract specifies `Co-Authored-By: Claude
<noreply@anthropic.com>` and no other footer. This session's harness mandates a different trailer pair
(a model-qualified `Co-Authored-By` plus a `Claude-Session:` line). The harness instruction was
followed and the divergence is recorded here rather than resolved unilaterally.

## What have we learned (Step 9)

Three contract-change proposals, each grounded in something this run hit. **None is applied** — the
lane forbids self-approving a change to the contract that governs the run, and each would ship as its
own `chore/` PR touching only the skill.

1. **`cloud-plan-lane` assumes an orchestrator collect step that a standalone epic has no counterpart
   for.** Four sites: the arm-and-hand-off completion is defined as handing the `MERGED` confirmation
   "to the orchestrator's collect step"; two further sites say the orchestrator collects the landing
   from the PR and from the report; the Step 9 self-check row restates it. A `test-quality` run that
   cannot self-wake takes that path and hands off to nothing. *Evidence: this run created the first
   epic with no ledger counterpart.*

2. **`author-cloud-plan` § OWNED-ELSEWHERE assumes derive-from-an-orchestrator-spec.** It names the
   derive-from-spec order, the carry-across set from the orchestrator spec, and "do not delete the
   orchestrator spec" as owned rules, and its authoring order opens with "derive from the orchestrator
   spec". None applies to a standalone epic, and the next author of one will read it as binding.
   `cloud-bridge.md` was updated for this in the present PR; the authoring skill that points at it was
   not, because it is a governing contract. *Evidence: this run authored a standalone epic against a
   skill that has no path for one.*

3. **The `skip-bot-review` rule is path-based in a way that mis-classifies `doc/plans/**`.** The
   contract permits the label for "genuinely nothing but `doc/**` prose, run reports, or ledger
   bookkeeping", and reasons that a skill is code because it is "behavioural prose that governs how
   every future run acts". By that same reasoning a **plan** is behavioural prose — eight runs will
   execute these files — and `cloud-bridge.md` and `_template/plan.md` are lane-contract documents
   that happen to live under `doc/`. This run resolved the tension toward the stated intent (review
   it) over the stated path rule (skip it). Proposal: scope the label by *what the file governs*
   rather than by its directory, or name `doc/plans/**` as an explicit exception. *Evidence: this run
   had to choose between the rule's letter and its own stated rationale.*

## Merge gate

| Condition | State |
|---|---|
| 1 — every required context present on the head SHA and concluded successfully | **met.** `verify / conclusion` **success**, `verify / gate` success, `review / review` success, `dependency-review` success. `verify / verify` **skipped** — the `skip-on-docs-only` footprint gate, working as designed for a change with no buildable source; `auto-merge` skipped pre-arm. `mergeable_state` read from GitHub's own ruleset computation, never from a ruleset-config call. |
| 2 — every PR comment handled | **met.** Three surfaces read; zero actionable comments. Two refusal notices and one nothing-to-report guide, none requiring a fix or a reply. |
| 3 — report finalized and pushed as the last pre-merge commit | **met** — this commit. |
| 4 — review-coverage shortfall disclosed *(a disclosure, not a gate)* | **fired: 1 of 3.** Stated above and to the operator before arming. |

## Residue

- **The landing itself.** Auto-merge is armed after this commit; the merge outcome is read back from
  the PR rather than asserted. The squash SHA does not exist until the queue lands it, so it is
  reported to the operator rather than embedded here.
- **A fifth verification pass was not run.** Four passes converged 30 → 11 → 8 → 6, with the residual
  class shifting from substance to prose-consistency drift. That class is what the review cycle is
  designed to catch, and each plan is additionally re-read by its own future run, which re-derives
  every count and halts on partition defects. Stopping at four is a judgement, recorded as one.
- **A sequential split of `050` and `070`** remains a live option (see § Rejected, with reason), to be
  taken before those plans are handed over rather than during their runs.
- **Sourcery's diff-size ceiling (150,000 characters) binds an authoring PR of this shape.** This one
  is ~2,400 added lines of prose and was refused on size. An author wanting that reviewer's coverage
  on a future epic should split the authoring PR — for instance the scoping brief and the two blocking
  plans in one, the six reduction plans in another.
