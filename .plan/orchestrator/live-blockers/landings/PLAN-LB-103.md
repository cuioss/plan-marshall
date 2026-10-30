# Landing Analysis: PLAN-LB-103 — Tests never read the project config, and a config-only change no longer forces the full verify

epic: live-blockers
workstream: WS-04
pr: #1894 (merge commit ce5e44e6c, merge queue, merge-group run 41070557864 success)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-103.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Grade **B+**. Runbook lane, `deepseek-v4.1-flash/high`, one session tree (`ses_e78742038ffe4dhcj2StmDnbSn` and two self-review sub-agents),
about 27 h from 2026-10-29 12:04 UTC to 2026-10-30 15:08 UTC. Both deliverables are in the merged diff as specified. The cost to the grade
is a wrong cleanup claim (two probe branches are still on the remote), a final-head census pair that was never re-obtained, and several
small under-disclosures.

## Deliverable Fidelity vs Spec

Verified against the merged diff (`ce5e44e6c^..ce5e44e6c`: 20 files, 570 insertions, 516 deletions), the PR body and the PR's review and
merge state. The lane's census runs (a named failing and passing job per file set) were NOT re-run by me: each is a full `module-tests`
of about 30 minutes, and the orchestrator runs no implementation builds. They stand as the lane's own report.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 no test's verdict depends on this repository's own `.plan/marshal.json` | shipped-as-specified (census set larger than the spec's) | The merged diff converts or deletes the readers in eleven files, against the three the spec named; a search of the inventory finds neither `_COMMITTED_MARSHAL_PATH` nor `git show HEAD:.plan/marshal.json` any more. The PR body lists every converted file with the fixture that replaces it or the reason it was removed, and eight dropped properties |
| D2 a change to `.plan/marshal.json` alone skips the heavy verify build | shipped-as-specified | `python-verify.yml` diff read directly: only `.plan/marshal.json` leaves `extra-buildable`, the comment names the three that remain; `CLAUDE.md` and `doc/developer/build.adoc` carry the same three-path list. The probe PR #1897 (draft, closed unmerged) reads `verify / gate` success, `verify / verify` skipped, `verify / conclusion` success through `ci checks status`. The lane's own first probe (#1891, closed unmerged, run before the fix merged) is not in the landing message |

**The spec's census hypothesis was refuted, as the spec's verify-first clause intended.** The spec labelled "three files are the complete
set" a HYPOTHESIS and told the lane to add every reader the census finds; the census found eight more. That is the clause working, not a
lane error and not a collision.

**Surface reconciliation** (`inbox landing-check`, declared against realized): 7 declared entries, 20 realized paths, **13 added**, 0
declared and untouched, state `expansion_detected`. Twelve of the thirteen are the census delta under `test/` (the finalize-step roster
helper `test/_shared/_finalize_step_roster.py`, the three bot-participation sibling files, the two finalize-routing files, three
dispatch-roster files, `test_project_steps_extraction.py`, `test_parser_seam_coverage.py`, plus `test_bot_participation_contract_config.py`
itself). The thirteenth is `test/test_harness_shape_guards.py`, which is NOT a reader: the lane added a 900 s `pytest.mark.timeout` to the
two whole-tree predicate sweeps because they crossed the suite's 300 s hang detector under `-n auto`. That is outside both deliverables.
The landing message does not mention it; the PR body does ("not a reader ... no assertion is relaxed"), and it is the robustness gap the
PLAN-LB-101 and PLAN-LB-104 landings recorded as residue. The PR body's own counts (17 paths touched, ten extra) are lower than the merged
diff (20 and 13): later fix commits added files after the body was written. No collision resulted: no file of PLAN-LB-104, of PR 1896
(`build.py`, `test_build_cmd_coverage.py`, `test_build_xdist_workers.py`) or of PLAN-LB-101 (`test_pre_merge_gate.py`) is in this diff.

## Metrics and Anomalies

- Tokens: `unknown` (the landing carries no figure; token measurement is out of scope under the focus rule).
- Duration: about 27 h wall clock across one operator question and several host-infrastructure failures.
- Self-review: two rounds, both as sub-agent sessions (round 1 four open findings, round 2 six), recorded `clear`. The session store holds
  exactly the root and two self-review children, which matches.
- Host failures the lane reports, and the PR body repeats: five attempts to re-obtain the census pair at the final head were defeated, two
  by xdist workers OOM-killed at 99 %, two by the 1745 s bound and one by a hang to the 2400 s bound. Those OOM kills are the mechanism the
  build-slot cap of 2 and PR 1896 (the xdist worker bound, which also covers `coverage`) address. The green pair stands at `2dd2f1382`; every
  later head had a full `verify`, so the gap is the pair itself, not the later heads' tests.

## Routing and Merge Behavior

- Review: CodeRabbit is required (`quota_limited`). The PR carries 36 formal reviews, 21 of them by `coderabbitai` between 07:30 and 13:48
  UTC on 2026-10-30 (the other 15 are the lane's own replies), so formal reviews exist on several heads. The lane records its findings per head, all fixed or answered, two answered
  and withdrawn by the bot. Its quota refusals (five, the last at 14:15 UTC) are on the PR as the lane states; whether the merged head is
  the one the last review covered I did not re-derive. The standing authorization applies; recorded as a note, not a finding. Sourcery
  is optional and refused on its 7-day budget.
- CI/merge: merged through the merge queue; `pr queue-state` reads `pr_state: merged`, `merge_commit_sha: ce5e44e6c`, `in_queue: false`,
  merge-group run `success`. The main checkout is clean and level with `origin/main` at that commit; the lane worktree is gone.
- Sonar: `n/a`, not enabled for this project.
- **Build routing.** The lane reports one `in_process_fallback` ("the daemon was briefly unreachable at 16:05Z") and every other build
  `daemon_longpoll`. The timestamp cannot be UTC: the message is stamped 15:08 UTC. The lane's worktree journal is gone, so neither the
  count nor the time is corroborated. A real datapoint for PLAN-LB-104 sits in the same section: the lane's first routed `module-tests`
  failed `execution_failed` with the relative `--project-dir`, and the same build re-run once with an absolute `--project-dir` was green.
  That is the trigger LB-104 fixes, seen again from a lane whose own tree predates the fix; it shows the trigger and the cure, not that
  the fix works.

## Session-Database Check

This is the first landing of the run checked against the OpenCode session store (read-only). The lane's sessions are keyed to the MAIN
checkout directory, not to the worktree, so the tree is found by title and by `parent_id`.

| Landing claim | Store |
|---------------|-------|
| two self-review rounds, sub-agents | root plus two children (`Self-review of LB-103 diff`, `Self-review round 2 of LB-103`): matches |
| one operator question | one `question` tool call: matches |
| model `deepseek-v4.1-flash`, variant `high` | the assistant messages carry exactly that: matches |
| shell breaks: one `grep -c`, `nproc`, `df -h .`, `free -g`, one `git clean -f`, one refused `mv` | 407 shell calls, 282 through the executor, 117 `git`; outside the executor: one `grep -c`, one `nproc`, one `df -h .`, **two** `free -g`, **two** `date -Iseconds`, one `mv` and **two** `git clean -f -- .plan/marshal.json`. Disclosed in kind, understated in count (`free` twice, `git clean` twice, `date` not mentioned) |
| no force push, no stash, restore, rebase, reset | none found among the 117 git calls; four `git merge` of main, 17 pushes (14 from the lane worktree, three from the probe worktrees), none forced |
| edits stayed inside the worktree | 217 edit and write calls; 58 outside the worktree, every one under `.plan/temp/` (the lane's progress file and commit-message scratch), `.plan/local/` (the probe worktrees and the CI body scratch): none to a tracked file of the main checkout |
| restarts (two) and lane-text re-reads | not measured: the store does not separate a restart from an idle gap cleanly enough to count one |

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-103 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-103 --field pr --value 1894`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-103 --field landing --value landings/PLAN-LB-103.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-103 --field plan_marshall_plan_id --value rb-lb-103-tests-use-fixtures-not-live-config`
- [x] epic.md narrative entry for the landing and a Watch for the leftover probe branches; the `total_tokens` gap folded into the entry, out of scope under the focus rule
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **Two throwaway probe branches were still on the remote** (deleted at the operator's request on 2026-10-30, `ls-remote` shows none; `chore/footprint-probe-lb103` and `chore/lb103-footprint-probe-2`), although the
  landing says the probe branch was pruned and `cleanup_owed=false`. Both PRs (#1891, #1897) are closed unmerged. Deleting a remote branch is
  not an orchestrator write, so the operator had them deleted; the Watch is retired.
- **The two other live-file reads of the real `python-verify.yml`** (`test_python_verify_buildable_paths.py` and the D5 cases of
  `test_runbook_lane.py`) were left alone as the spec required and are recorded in the PR as an adjacent coupling. That answers pending
  decision (4); whether to stage a follow-up stays the operator's.
- **Properties dropped by the operator's ruling that a live-config read is a bug**, recorded in the PR: nothing now checks the tracked
  `.plan/marshal.json` for machine-local keys or secrets, its canonical key order, this project's orchestrator tunings, the reviewer roster
  or provenance values, or the retired `enabled_bots` key, and a finalize step whose body document is missing can no longer be detected
  by the roster suites. A note, not a defect.
- **The final-head census pair was not re-obtained.** The lane's evidence is the pair at `2dd2f1382` plus a full `verify` on every later head.
  Re-running the pair now, on a host with the worker bound and the slot cap in place, is possible but costs two full runs; not staged.
- **`runbook_lane.py::_classify_path`** still classifies `.plan/marshal.json` as buildable for the lane's local gate (costs a local build,
  never skips one CI would run); left untouched per the spec.
- **Surface under-declaration** of the shipped spec is not edited: the row is terminal, so the gate no longer reads it.
- Fix-forward: none staged.
