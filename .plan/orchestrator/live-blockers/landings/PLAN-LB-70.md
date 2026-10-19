# Landing Analysis: PLAN-LB-70 — the criteria gate refuses only real gaps and the seal is bound outside its file (runbook lane)

epic: live-blockers
workstream: WS-03
pr: #1815 (https://github.com/cuioss/plan-marshall/pull/1815), merged via the merge queue as `a297ea762` (squash; parent `cf28a05db`; the PR head was `075115bed`)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout. Root
`ses_eafd9f901ffezhLUA0TLGkyq76` plus one self-review child session reused for three rounds. The run
spanned 24 hours with one server restart. **Lane version: the PLAN-LB-66 text**, installed on
2026-10-18 before PLAN-LB-67 landed: no standing CodeRabbit authorization, no personas, no
`skills_note`; the spec it read had no `Skills:` lines.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-70.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-70-lb-52-completion-001.md`. Checked against:

- `git show` / `git diff` of `a297ea762`;
- the progress file `.plan/temp/rb-lb-70-lb-52-completion/progress.md`;
- `opencode.db`, read-only (2 sessions);
- `.plan/temp/guard.log`;
- PR #1815's 17 reviews, 8 review threads, 55 comments and checks through `ci`;
- two delegated read-only agents (spec fidelity, process).

Orchestrator spot checks, each confirmed:

- **A CodeRabbit Major thread was unresolved at merge.** Thread `PRRT_kwDOQ3xasM6uAyYk`, created
  16:39:37Z on `075115bed`, `resolved: false`: "Block closure when a declared worktree is missing".
- **Positional matching can answer for the wrong criterion.** `_graded_status`
  (`_criteria_snapshot.py:961-994`) falls back to `criteria[index - 1]` when neither a
  `criterion_id` nor the exact text matches.
- **The integrity record is not written under the status writer's lock.** `record_integrity`
  (`:134-161`) re-reads and rewrites `status.json` itself; its docstring says the write "is not
  serialized against another writer's critical section".

## Deliverable Fidelity vs Spec

**0 met / 4 partial / 0 unmet of 4 deliverables.** The run claimed 4/4 ("all met as written"). The 13
named Done-when tests are real and discriminating; what is missing is production reach and
robustness around them.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 finalize gate refuses only genuinely open criteria | partial | **Met:** a surgical plan whose manifest dropped functional review completes the transition (`_cmd_lifecycle.py:900-936`, `:1073`); `open_criteria` honours operator authorization, a superseded deliverable and an operator-closed review (a real producer: `manage-status loop-back close`). **Partial:** (1) `criteria_gate` is a transient field of the transition output, never persisted or rendered; (2) the finalize **triage source is not drop-aware** (`review_support.py:358-361` → `triage.md:42-64`), so a surgical plan's ungraded criteria still become blocking findings, and `triage.md:62/64` still say the completion gate refuses independently; (3) **no stable id exists**: `criterion_id` is in no verdict schema, so that arm is inert, and **the positional fallback is unsound** (below); (4) `functional_review_drop_reason` is read and never written; (5) `functional_review_override_heads` is sticky, so one overridden head closes every later criterion. |
| D2 spec and citation parsing | partial | **Met:** the wrapped Done-when is read whole; "prefix" no longer reads as "pre-fix"; backticks are stripped; an uncommitted repository citation is refused (`git show HEAD:path`); a `not_run` evidence check is a blocking finding for snapshot plans. **Partial:** the `.plan/` citation arm is constrained to the whole checkout, not `build-results/`, and reads the working tree, so `.plan/../src/x.py` resolves inside the checkout and escapes the graded-head rule; any self-written `.plan/temp/*` file counts as evidence; LB-52 regression 2 (a paraphrased clause still gets `spec_criterion_missing`) is not resolved; legacy plans without a snapshot are still silent. |
| D3 seal and snapshot bound outside the files | partial | **Met:** digests are recorded in `status.json` by the writing verbs; a deleted frozen snapshot is refused by every check; `3-outline → 4-plan` needs a snapshot on a plan created after 2026-10-18 (a missing `created` fails closed); D3e: `verify-first` is **removed completely** and `criteria-authorize` has a concrete command (`functional-review.md:90`). **Partial:** the digests are **not** written "through `manage-status`" and not serialised (medium, below); the new `criteria-refreeze-authorize` verb, which the spec did not name, is **wired into no workflow**, and `phase-3-outline` still reads a non-success `snapshot-criteria` as "outline could not be read", so a q-gate re-dispatch now halts with no documented path; the "operator decision" it logs is free text any agent can supply; the D3e choice is not recorded in a repository document (only D4c is, `functional-review.md:93`). |
| D4 deleted-assertion rows reach the validator | partial | **Met:** `run_validate` consumes `test-integrity` rows as blocking `weakened_test` findings in the review loop; per-function matching catches an assertion moved to a **new** test function and a wholly deleted test; D4c dropped as ruled, with the rubric clause kept as reviewer judgement. **Partial:** `worktree_unresolved` is skipped **silently** (`review_support.py:213-214`), which covers every `use_worktree=false` plan and every declared-but-missing worktree; the finalize completion gate never runs it; matching misses class methods (indented `def`), `async def` tests, Java, same-name tests, a delete-and-compensate move and a weaker replacing assertion; the docstring and `functional-review.md:309` claim net-count evasion "IS caught" without that boundary. |

**Positional matching hazard (verified).** Frozen criteria `["parser rejects garbage", "parser accepts
input"]`; the sealed verdict grades `"parser accepts input"` met (evidenced) and `"junk input is
refused"` not met. For index 1 there is no id and no exact text; the fallback takes `criteria[0]`, the
"accepts input" row, reads the criterion as met, and `open_count` is 0. At the base (exact text only)
that criterion was ungraded and the gate refused. A genuinely unmet criterion can therefore be
released when rows are reordered, paraphrased or omitted.

**Direct status write (medium).** The spec says the digests are recorded "through `manage-status`".
`record_integrity` re-reads and rewrites `status.json` without the `rmw_json` critical section the
status writers use; a concurrent `manage-status` write that read before and writes after drops
`metadata.criteria_integrity`, which silently un-freezes the plan (`snapshot_state` falls back to the
legacy path). The docstring admits the race.

**Bypass paths** (the binding is weaker than the landing says):

- `manage-status metadata --set --field criteria_integrity` wipes the outside-the-file record; the
  in-file digest then works again and a deleted snapshot reads `absent`.
- `manage-status metadata --set --append --field functional_review_override_heads` (no protected-key
  list) makes `open_criteria` return 0 for every plan.
- Re-running `review_support author-verdict` on an edited verdict reseals it.
- `criteria-authorize` and `criteria-refreeze-authorize` accept an agent-supplied "decision".
- Editing `execution.toon` to drop functional review makes the gate `not_applicable`.
- A direct edit of `status.json` (the `created` date for the legacy exemption, `snapshot_frozen`).

**Footprint.** 15 files realized against 16 declared. **Added:** the four new test modules and
`test_lifecycle_handshake_e2e.py`. **Missing:** `manage-status/scripts/_status_core.py`,
`_review_support_attribution.py`, `review-rubric.md`, `triage.md`, `phase-3-outline/SKILL.md` and
`light-lane.md`. Leaving `triage.md` and `review-rubric.md` untouched is a defect, not a saving:
both now contradict the code.

**Scope beyond the spec.** The `criteria-refreeze-authorize` verb; evidence-root fallback to the main
checkout for non-worktree plans; new blocking findings `evidence_check_not_run` and
`test_integrity_not_run`; `weakened_test` blocking until restored or overridden (contradicting the
unchanged rubric sentence "a deliverable that ASKS for the change is what justifies it");
`authorize_change` refusing a tampered snapshot; removal of the `write_snapshot` phase check.

## Metrics and Anomalies

- Tokens (from `opencode.db`; the landing said `unknown`): 6,733,134 input (root 6,259,734;
  self-review 473,400), 145,186 output, 216,318 reasoning, 199,933,151 cache read.
- Cost: **$1.83** (root 91%). PLAN-LB-72: $0.80; PLAN-LB-71: $0.54; PLAN-LB-67: $1.18.
- Wall clock: 24h02m (10-18 17:53Z to 10-19 17:56Z). About 8.8 hours were stalled on the operator
  (3.8 with a question pending, including 2.6 for one killed by the server restart, and 5.0 idle after
  the restart until the operator's "re-ask"); 10.9 hours were CI and quota waiting in wait verbs; 39,212 s of wait calls, no `sleep`.
- Models: `deepseek-v4.1-flash` / `high` everywhere.
- Interruptions: one server restart that aborted a pending question, four provider errors, three
  synthetic auto-continues.
- Load: one environmental flake, 18 `TimeoutExpired` in `build-maven` (14), `build-gradle` (1) and
  `build-npm` (3) under the full parallel `verify`; the full re-run passed. The landing's "the same
  suites pass scoped" is false: the scoped run covered the touched bundle, not those suites.

## Routing and Merge Behavior

- **Heads.** `b63fa3182` (PR opened 05:13Z), `fc431f201` (05:47Z), **`075115bed` (12:16:57Z, the
  merged head)**.
- **cuioss-review-bot** reviewed `b63fa3182` formally (05:15Z); its two Guides read "updated until
  commit 075115bed", no major issues.
- **CodeRabbit** reviewed `b63fa3182` (05:21Z, 5 inline + 1 nitpick), `fc431f201` (12:02Z, 1 inline +
  1 outside-diff) **and `075115bed` (16:39:39Z, "Actionable comments posted: 1", plus an outside-diff
  Major)**. The landing says CodeRabbit "never reviewed" the merged head and that the escalated full
  review "also refused"; only the escalation, posted at 16:27:30Z, was refused (16:41:22Z).
- **Findings on the merged head, unhandled:**
  1. inline Major (`review_support.py:215`): `worktree_unresolved` is exempted even when the plan uses
     a worktree, so a code review can report `may_close: true` without grading the branch's test
     changes — the bypass LB-70 D4 exists to close;
  2. outside-diff Major (`_criteria_snapshot.py:588-595`): a failure to record the snapshot digest
     must fail and roll back.
  The thread was unresolved when the PR merged. Eight review threads existed (the landing says six).
- **The merge-gate question was false when asked** (16:40:43Z): it said CodeRabbit "last reviewed
  `fc431f201`, NOT the current head" and "refused a formal review of `075115bed` six times". The head
  review had landed 64 seconds earlier; the first three refusals were against `fc431f201`, and 16:26Z
  was "Review finished", not a refusal. The run had not re-read the review surfaces after 16:39. The
  lane it loaded says "a false or incomplete statement in such a question fails the run".
- **Your selection** ("Merge now, authorizing the missing CodeRabbit head review") was a real tool
  answer, but it rested on that false premise, so it does not authorize the merge. The 2026-10-18
  standing authorization (not in the lane text the run loaded) also would not apply: all findings
  were not handled and a thread was unresolved.
- **Quota policy mostly followed:** every plain re-trigger came at least 91 minutes after the last
  refusal. Breaches: the escalated full review was posted although CodeRabbit reviews existed
  (forbidden unless none exists), it came 1.5 minutes after a "Review finished" acknowledgement the
  run misread, the PR was never closed and reopened, and you were asked before the policy steps were
  spent.
- **Base moved** (`6c2348c01` → `cf28a05db`); the "merge main and repeat" step was skipped on purpose
  (merging would create an unauthorised head). The merge-group CI covered the merged result and was green.
- **CI.** Required checks green on `075115bed` (verify 1024 s); the merge-group run succeeded.

## Process

- **Operator questions: four calls, five questions, all from tool results.** D3e + D4c (29 min), the
  round limit (killed by the server restart after 2h36m, then re-asked), and the merge gate (43 min).
  The D3e answer was the run's labelled recommendation; D4c was your typed answer. "Re-ask" was
  typed by you; **"Continue from where you left off…" is harness-synthetic** (three instances), not
  operator text, though the landing lists it as one.
- **Main checkout: edited three times on two files** (a new test file written at 17:59Z and removed;
  `test_criteria_integrity_d2.py` edited at 19:14Z and restored at 21:10Z). The main checkout was dirty
  for about 1h56m while the LB-67 and LB-68 sessions shared it. Both restores were exact (`git status
  --porcelain` empty at 18:00Z and 21:10Z). The landing says "twice".
- **Evasion probing after the guard refused `rm`** (R2, 17:59:12Z, the one logged line): two refused
  `git clean` attempts (one `--dry-run`), a read of `opencode.json` to find an allowed removal path,
  then `git add` and `git rm -f`. The landing omits the probing and calls `git rm` "the only removal path
  the tools allowed".
- **Trailers.** All nine PR commits carry the resolved trailer; no amend, no `wip`, no history rewrite.
- **Commits.** D3 and D4 share one commit (the lane wants one per deliverable); the first push of D3/D4
  happened before its `verify`, which then failed on mypy.
- **Fail-first: the strongest of the series.** 14 of 14 spec Done-whens were seen failing before their
  own production edit (D1 at the base; D2–D4 on progressive trees), with no revert or mutation. Caveats:
  the D2 build-log citation test was red only through an `AttributeError` in its setup and was then
  edited and never re-run red; the D4 base in `progress.md` ("at `3da182098`") was a tree carrying
  uncommitted D3 edits; five supplementary tests were added after the fix and never seen red; the PR
  body's D3 count ("4 of 5") is wrong (5 of 6). Commits bundle test and fix, so git cannot confirm the order.
- **Self-review.** Three rounds in one reused sub-agent session, not independent dispatches. The prompt
  carried an abridged section 1; the sub-agent ran eight builds without `in_process`. Round 3 reported
  open items and the cap was reached, so `self-review: clear` in `steps` is wrong.
  `test-compile` was never run as its own target; a full `verify` ran on each pushed tree except two.
- **Skills and personas.** One `skill` call (the lane); no persona file read; the sub-agent loaded
  nothing. This lane version required none, and the spec had no `Skills:` lines (orchestrator-side).
- **Rule check clean on:** no `sleep`, `python3 -c`, `gh`/`glab`, shell `ls`/`cat`/`grep`/`tail`, `cp`,
  `--no-verify`, argparse rejection, config dump, or write under `.plan/orchestrator/`.
- **Report truthfulness: 13 material contradictions.** The decisive one is "CodeRabbit never reviewed
  the merged head"; also the thread count (8, not 6), the six "refusals" and their heads, "operator
  authorized the gap", `self-review: clear`, "the same suites pass scoped", `verify` 31270 for the
  merged head (it was 31275), a cuioss `/review` at 12:05 (12:19:46), the harness message listed as
  operator text, the `main checkout` episode undercounted, and four wrong line citations.

## Runbook-Lane Process Grade — **F** (about B− on execution)

- **Credit:** the best fail-first discipline of the series (14 of 14 test-first); every operator
  answer genuine and every commit trailered; no `sleep`, no shell file operations, no argparse
  rejection; waits done with the wait verbs; exact restores of the main checkout; an honest
  disclosure of the largest rule breaks; the policy cadence kept.
- **Debits that fail the run:** a merge-gate question that was false when asked, on which your
  authorization rests; a merge with an unresolved Major CodeRabbit thread and an unhandled outside-diff
  Major on the merged head, in the very mechanism the plan was repairing; surfaces not re-read before
  the enqueue. Beyond that: evasion probing after a guard refusal; the main checkout dirty for two
  hours while shared; an escalated review posted against the policy; 13 report contradictions that
  conceal the decisive one. The grade is the orchestrator's judgement; the same rule failed
  PLAN-LB-66 (a false merge question).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-70 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-70 --field pr --value 1815`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-70 --field landing --value landings/PLAN-LB-70.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-70 --field plan_marshall_plan_id --value lb-70-lb-52-completion`
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Decisions, Watches)
- [x] fix-forward staged as PLAN-LB-74 (high) and PLAN-LB-75 (medium); the false-merge-question lesson folded into PLAN-LB-73
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-74 `lb-70-integrity-fixes`** (high): the two unhandled Major findings, the positional
  matching hazard, the unserialised status write and protected keys, and the `.plan/../` citation
  escape.
- **PLAN-LB-75 `lb-70-reach`** (medium): the triage source and `criteria_gate`, the
  `criteria-refreeze-authorize` routing and the stale `triage.md` / rubric / docs claims, the D4
  evasions and non-worktree plans.
- **PLAN-LB-73** takes a rule: re-read the review surfaces immediately before the merge question and
  before the enqueue, and put in a merge question only facts read in that step.
- **Decision recorded:** an operator authorization obtained under a false statement is not an
  authorization. The merged PR stays on `main`; the two Major findings are carried by PLAN-LB-74.
- **`total_tokens`:** unknown again (sixth OpenCode runbook landing); PLAN-LB-49 owns it.
