envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:16Z

# Candidate lesson: the tests added for a code removal passed on the old code too

Component: plan-marshall:execute-task / plan-marshall:persona-module-tester
Category (proposed): improvement
Source: plan spend-removal, finalize (code review round 1: three of five advisory findings)

## Observation

- The plan removed a policy class, a remediation unit and a barrier clause. Its module_testing tasks added "pass cases" for the removal (the merge gate without the overrun clause passes, the remediation unit set without the spend unit passes) and one refusal case that checked only one of the three exemptions the removed code had carried.
- The code review found that the two pass cases held identically on the old code: the fixtures never contained a spend route or a spend unit, so a reviewer could re-add the removed clause and every new test would stay green. The refusal case could not reach the other two removed exemptions (the re-planning route and the full-template check).
- All suites were green, coverage was met and the verifier accepted the task output; only a reviewer reading the removed code against the test inputs saw it.
- Fixing it needed inputs the old code refused or exempted: a merge gate that routes the removed outcome without the removed remediation call, a call of the removed unit routing `exhausted` to the re-planning call, and a unit of the removed name checked for the second exemption. Running the new tests against the removed code would have shown the gap directly; that run was not possible in this session (the shell write that restores old source over tracked files was blocked), so the check was done by reading the removed code.

## Proposed correction

- For a removal or tightening task, require in the module_testing task that each new test names the removed behaviour it would catch, and add a "fails on the previous implementation" check: the execute envelope runs the new tests once against the pre-change production classes (for example in a throwaway worktree) and records the result.
- Add this as a Review Rule to `persona-module-tester`: a pass case that holds on the code before the change is not evidence for the change.
