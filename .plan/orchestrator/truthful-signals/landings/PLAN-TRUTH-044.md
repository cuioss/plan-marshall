# Landing Analysis: PLAN-TRUTH-044 — The Lesson-Retirement Path Fails Open in Three Independent Places

epic: truthful-signals
workstream: WS-01
pr: [#1113](https://github.com/cuioss/plan-marshall/pull/1113) — merged `4fde77e6f`

> Executed in the plan-marshall lifecycle (worktree `lesson-retirement-fails-open`). Claims below
> re-verified first-party against `origin/main`, the merged diff, and the stored PR comment bodies.

## Deliverable Fidelity vs Spec

Corroborated against `git show --stat 4fde77e6f` — **19 files, +3130/−299**.

| Area | Evidence |
|---|---|
| `manage-lessons` fail-open closure | `_lessons_query.py` (+597), `_lessons_io.py` (+119), `manage-lessons.py`, `SKILL.md` (+92) |
| `manage-status` lifecycle | `_cmd_lifecycle.py` (+306), `SKILL.md` (+77) |
| Store-resolution audit standard | new `standards/cwd-keyed-store-resolution-audit.md` (+223) plus a project-local mirror |
| Consumers | `finalize-step-lessons-housekeeping`, `plan-retrospective`, `plan-marshall/workflow/planning.md`, `marshall-steward` |
| Tests | 6 files, incl. two **new** suites: `test_lesson_store_resolution_fail_open.py` (+322) and `test_lesson_store_resolution_population.py` (+177) |

⭐ **The population suite is the notable one.** The spec's own diagnosis was that `list-stalled` keys
off `plan_source`, which is unset for every plan that *carries* lessons — so **its population is a
strict subset of the population that can exhibit the condition**. A dedicated
`..._population.py` suite is the right answer to that class, and matches the standing rule that every
set-guarding detector must be population-derived.

## Routing and Merge Behavior

**Real review, argued on the merits — the strongest reviewer engagement of any landing this epic.**
48 comments; `coderabbitai` filed substantive inline findings with citations.

- **Sharpest finding, accepted:** `cmd_restore_from_plan` returned the resolution of the store that
  *succeeded* (`plans_store`) while the **lessons corpus** was what failed — emitting a resolved
  `store_resolution` next to `error: plan_dir_unresolved`. The reviewer cited the sibling verb's own
  normative rule (`_stalled_payload` lines 559-564, implemented at 671-672) showing this branch
  contradicted it. ⭐ **That is the epic's exact archetype found in the plan closing the epic's exact
  archetype** — a payload reporting a clean resolution for a store nothing ever reached. Fixed.
- **Scope discipline held under review pressure, twice.** (a) The reviewer proposed extracting the
  override predicate into `script-shared/marketplace_paths.py`; the operator **declined as
  out-of-footprint** against the plan's non-goal 4 and took the in-footprint remedy instead
  (correct the false docstring claim + pin the mirroring with a test). (b) The reviewer suggested a
  fifth `action` value; declined because `RESTORE_ACTIONS` is a deliberately closed four-value
  vocabulary, and a new `unresolved_store` field carried the distinction without the contract change.
  Both refusals are reasoned and recorded on-thread.
- ✅ **The 10 "unresolved" threads were checked and carry NO open work.** Composition, read
  first-party: 1 Sourcery decline, 1 CodeRabbit rate-limit decline, 1 PR-Agent review body, and
  **6 of the operator's own** comments (the non-goals restatement, two copies of the triage
  dispositions, `/review`, `@coderabbitai review`, and a CodeRabbit ack). ⛔ **An unresolved-thread
  count is not a finding count** — here it is 60% the author's own notes.
- ✅ **The two substantive findings were verified FIXED IN MERGED MAIN, not merely dispositioned:**
  - **TOCTOU symlink/overwrite hazard** (`cuioss-review-bot`, security): flagged because
    `os.close(claim_fd)` preceded `shutil.copyfile(path)`, letting a concurrent process swap a
    symlink under the claimed name. Merged code writes **through the claim fd**
    (`os.fdopen(claim_fd, 'wb')` + `copyfileobj`, `_cmd_lifecycle.py:671-672`), and the comment at
    `:655-665` names the exact hazard and why a descriptor closes it. Fixed.
  - **`DIR_LESSONS` hardcoded in both test stubs** (CodeRabbit): merged
    `test_list_stalled.py` now does `from _lessons_io import DIR_LESSONS` and uses it as the default
    in both stubs (4 occurrences, 1 remaining literal). Fixed.
  ⭐ **The inverse of correction C4:** an artifact observed after a fix is not one produced after a
  fix — and equally, **an open thread is not proof of an unfixed defect.** Both needed checking
  against the source, not the thread state.

## ⚠ Leads, not findings

1. **`uv.lock` changed (+176/−…) in this diff.** Two cloud runs hit lockfile churn from `./pw`
   bootstrapping under a session interpreter below the project floor, and both reverted it. This is a
   **local** run, where a legitimate dependency change is equally plausible. ⛔ **Do not record this as
   a third instance without checking** whether the plan touched dependencies — the two situations are
   indistinguishable from the stat line alone, and asserting the defect from a filename is the
   sample-as-enumeration error. Settle it against the commit's `pyproject.toml`/dependency diff.
2. **The plan's stated surface was narrower than its real one.** Its spec listed `manage-lessons`,
   `finalize-step-lessons-housekeeping`, and `plan-retrospective`; the landed diff also touches
   `manage-status` (two files), `marshall-steward`, and `plan-marshall/workflow/planning.md`. That
   widening is why `PLAN-TRUTH-055` was withdrawn mid-flight — recorded here so the next pairing
   decision uses the *observed* surface, not the declared one.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` → `1113`; `landing` → `landings/PLAN-TRUTH-044.md`
- [x] epic.md reconciled; resume_anchor updated
- [x] **`PLAN-TRUTH-055` unblocked** — its collision was with this plan's live `manage-status`
      surface, which has now landed. Re-emittable.

## Follow-Ups

1. ✅ **Post-merge revisit DONE, not owed** — the unresolved threads were read and both substantive
   findings verified fixed in merged main (above). Nothing outstanding on this PR.
2. **`PLAN-TRUTH-055` may be re-emitted.** It was withdrawn only because of the collision above.
3. **Settle the `uv.lock` lead** before it is counted as a recurrence.
4. ⛔ **NEW BOT-PARTICIPATION AXIS — routed to `review-apparatus`.** `sourcery-ai` declined this PR
   with *"your pull request is larger than the review limit of 150000 diff characters"* — a
   **size-based** refusal, structurally distinct from the weekly-quota and rate-window axes already
   catalogued. It is the first axis that is a **function of the plan's own scope**: a large plan
   buys itself less review, and the bigger the change the less it is looked at. CodeRabbit
   additionally hit its rate limit on a re-review here, so this landing is a two-decline PR.


---

## ⛔ CORRECTION 2026-08-08 — the coverage figure in this record used the WRONG DENOMINATOR

This landing reports review coverage against the **enumerated roster** (`coderabbitai`,
`sourcery-ai`, `cuioss-review-bot`). That is not the quorum. Read first-party from
`.plan/marshal.json` (`plan.phase-6-finalize.steps.plan-marshall:automatic-review`):

    required_bots = 'pr-agent'          optional_bots = 'coderabbit,sourcery'
    bot_lists_provenance = 'answered'   # a deliberate operator answer, not an unset default

Per `automatic-review/standards/bot-participation-contract.md`, an **optional** bot's silence "never
blocks" and is "not a failure". ⇒ **`cuioss-review-bot` (pr-agent) reviewing is a satisfied quorum,
1 of 1.** The "N of 3" framing above overstates a shortfall that did not exist. The operator
confirmed the classification on 2026-08-08: *sourcery stays optional for this project.*

⭐ **What the error produced that is worth keeping:** `PLAN-TRUTH-061`'s shipped disclosure derives
its population from the registry **roster** and never reads `required_bots`/`optional_bots` — so the
mechanism computes shortfalls against this same wrong denominator. That defect is real, is routed to
`review-apparatus` (`truthful-signals-022.md`), and was only visible because the arithmetic was wrong
here first.
