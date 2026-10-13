# Landing Analysis: PLAN-LB-37 — The review splits in two: a functional review and a code review

epic: live-blockers
workstream: WS-01
pr: #1759 (https://github.com/cuioss/plan-marshall/pull/1759), last part of the stack #1754, #1755, #1757, #1758, #1759

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-37.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-37-functional-review-009.md` (kind `landing`, `landing-check`
`complete: true`; surface delta `unmeasured`). Checked against:

- `ci pr queue-state --pr-number 1759`: `pr_state: merged`,
  `merge_commit_sha: d5c1e869ff262a458be63ddf0bf237e1cdae8f9e`, merge-group run `success`.
- The five squash merges on `main`: #1754 `fc0090a24`, #1755 `730f37a2f`, #1757 `77ef084ad`,
  #1758 `47d21e1bf`, #1759 `d5c1e869f`.
- A read-only review of `main` at `7f35dca9a` against both spec documents by a delegated agent
  that ran nothing.

Not read by that review: the plan's outline and logs, the PR comments of the stack, the
generated code-review packs' content. The D14 mapping table lived in the plan's outline and is
not on `main`, so the mapping was judged by content only. The skill count in `CLAUDE.md` was not
re-counted.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — functional-review step | shipped | `phase-6-finalize/workflow/functional-review.md:1-36` (order 6, head-dependent, default on); `_manifest_rules.py:247,444,622-640`; Java-only and Python-only plans give the same output shape (`test_review_support.py:554`) |
| D2 — verdicts and validator | shipped | `_review_support_validate.py:27,191-199`: a criterion graded met without evidence is rewritten to unevidenced |
| D3 — unrequested changes, false self-reports | shipped | `test_review_support.py:241,254,277` |
| D4 — rubric and loop-back | shipped | `standards/review-rubric.md` §2, §6, §7 |
| D5 — bounded cost, delta rounds | shipped | `functional-review.md:17-19`; `test_review_support.py:367,384` |
| D6 — surfacer apparatus removed | shipped | no reader of `pre-submission-self-review` remains in `marketplace/bundles`; only the migration's retired-id list and its docs name it |
| D7 — configuration and landing facts | shipped | `.plan/marshal.json:97,100`; `landing-payload-spec.md:144-180`; `emit-landing.md:252-265` |
| D8 — config migration | shipped | `marshall-steward/scripts/upgrade.py:688` `migrate_review_steps`, first Stage-2 sub-step (`:175`) |
| D9 — consumer rollout | **not shipped — owed** | TASK-26, `blocked` by operator decision; runs after landing |
| D10 — code-review packs | shipped | `marketplace/targets/cuioss_review_bot/target.py:136-162,838-978` |
| D11 — code-review step | shipped | `workflow/code-review.md:131-149,266-298`; reads the skills' `## Review Rules` blocks directly, not the generated packs |
| D12 — a finding must cite a rule | shipped | `_review_support_validate.py:273-284` |
| D13 — one shared rubric | **partial** | the rubric is the only place the blocking line is stated, but neither step's own tests read `review-rubric.md` as the done-when asks; only `test_charter_invariants.py` does |
| D14 — old checks mapped | shipped (content) | `ref-code-quality/SKILL.md:81-119`; `plugin-architecture/SKILL.md:148-161` |
| D15 — the bot reads the same rulebook | **not shipped — owed** | TASK-27, `blocked` by operator decision; CI already publishes the `code-review-*` packs (`cuioss-review-bot-packs-publish.yml:120`), the bot's composition is not switched |
| D16 — migration covers both steps | shipped | `upgrade.py:585,735-739`; `test_review_step_migration.py:76-372` |

The plan's own count is 18 of 20 (its renumbered deliverables); the two undone are D9 and D15.

## What the plan achieved against its objective

- **The old self-review is gone and two reviews replace it.** One asks whether the request was
  met, criterion by criterion, with evidence; the other whether the code is sound, citing a rule.
  Both are language-agnostic.
- **The functional review does not catch a plan that rewrote its own criteria, nor a weakened
  test.** It grades the outline's current criteria (`functional-review.md:210-215, 298`) and
  never compares them with the request or an earlier outline; a test identifier counts as
  evidence (`review-rubric.md:66`) whether or not its assertions were relaxed. This answers the
  open question in the `-015`/`-026` Open Defect: the gap stands, and PLAN-LB-39 D6 owns it.
- **The rollout is not done.** No consumer repository is on the new steps yet, and the review bot
  still composes from the old rulebook.

## Metrics and Anomalies

- Tokens: 12,262,752. Wall 335,628 s (about 93 hours, spanning the operator's stack rebuild).
  Finalize alone 4.1M tokens, most of it the stack rebuild and per-part review cycles.
- **Landed as a five-PR stack.** CodeRabbit (required) refused the original PR #1753 at its
  100-file cap (198 files); `pr-decision` had advised a split, advisory only. automatic-review
  filed the refusal as an ordinary finding and looped back twice instead of escalating. Parts 1–4
  were landed from a separate stack worktree under `NO_PLAN`, so their review comments are not in
  the plan's findings store. Lessons `2026-10-13-14-001`, `-003`.
- **Closed by operator override.** functional-review, code-review and automatic-review carry
  `may_close=operator_override` at `31eb67a3c` ("there are enough coderabbit reviews. Land now");
  the merge went through a barrier-ask override (cuioss-review-bot `participated_stale`). The last
  commit was not re-reviewed by CodeRabbit (rate-limited).
- **The retrospective's coverage figures are wrong for a stack.** The footprint resolver saw only
  #1759's 31 paths: recall 11 percent, 179 of 200 assessments "unrealised". Lesson
  `2026-10-13-14-002`.
- **Finalize re-fires left no log rows**: 11–12 firings per review step, 17 execution-log rows,
  3 dispatch-boundary rows. Lesson `2026-10-13-14-004`.
- `emit-landing` in progress, `archive-plan` pending.
- Installed plugin cache still lists `pm-plugin-development:ext-self-review-plan-marshall` (the
  review saw it); the landing says the harness sync ran — a sync that mirrors without pruning.

## Points from the review of #1759

- `manage-logging` `work`/`decision` now exit 1 with `write_failed` (`manage-logging.py:197-220`),
  against the plugin rule "exit 0 with `status: error`" (`plugin-architecture/SKILL.md:159`).
- In the migration, a legacy `self_review: always` overrides an explicit current `lane`
  (`upgrade.py:640-642`) — tested and documented, but the retired spelling wins.
- `carried` and `dropped_params` report the same value in two quotings (`upgrade.py:745`).

## Collisions with plans in flight

- PLAN-LB-39 (staged, held behind this plan) declares `functional-review.md` and the
  `phase-6-finalize` / `manage-execution-manifest` test directories; it must start from `d5c1e869f`
  or later. Its hold is released.
- PLAN-LB-26 (staged) waits for this plan; its re-scope note asks it to re-read both review steps
  before outlining.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1759; `landing`; `plan_marshall_plan_id` lb-37-functional-review
- [x] epic.md: queue annotation; the `-015`/`-026` question answered; shell-quoting defect given
  its remaining sites; new Open Defects; the migration Watch tied to the owed rollout
- [x] four candidate lessons promoted (`2026-10-13-14-001` to `-004`)
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- OWED, operator: D9 — run `marshall-steward upgrade` in the 8 configured consumer repositories;
  D15 — switch the cuioss-review-bot settings repository to the code-review rulebook.
- Then the Watch: remove `migrate-review-steps`.
- D13 — have each step's tests read `review-rubric.md`.
- Prune retired skills from the installed plugin cache.
