envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:51Z

# An acceptance criterion known unreachable at execute time surfaced only at the finalize verifier

**Component:** plan-marshall:phase-5-execute / plan-marshall:execute-task (escalation of unreachable criteria), plan-marshall:phase-3-outline Q-Gate (criterion reachability), plus local: pm-mcp-core CLAUDE.md
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores (PR #93), from plan-retrospective

## Observation

The outline copied CLAUDE.md's link criterion `BROKEN LINKS 0` into the Verification blocks of D1, D7 and D8. TASK-1 (envelope 1) already saw `BROKEN LINKS 1` from a pre-existing break outside this repository (`plan-marshall-documentation` `roadmap.adoc:233`) and logged it as a decision. No operator question followed. Envelope 3 and the TASK-13 leaf reported the same gap. Only in finalize did the functional-review verifier refuse the `met` grading (`grading_supported: false`). That cost an operator question ("the link check is gone. Rebase on main and land") and another full review chain. Meanwhile #88 had removed `links.yml` on main mid-plan, and CLAUDE.md still prescribes `trace.py` and `BROKEN LINKS 0`.

## Suggested corrective action

- When an execute leaf finds that a success criterion cannot be met for a reason outside the plan, it returns a prompt-required envelope at once instead of only logging a decision. The operator then rules on it before finalize spends a review round.
- The outline Q-Gate could check literal verification outputs such as `BROKEN LINKS 0` against the base branch and flag a criterion the base already fails.
- Local to pm-mcp-core: update CLAUDE.md so it no longer prescribes the removed link check (`links.yml` was deleted by #88).
