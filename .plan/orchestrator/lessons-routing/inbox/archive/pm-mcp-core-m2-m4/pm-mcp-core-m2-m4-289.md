envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:15Z

# Candidate lesson: an outline success criterion about the pull request body cannot be evidenced before the push

Component: plan-marshall:phase-3-outline / plan-marshall:phase-6-finalize (functional-review)
Category (proposed): improvement
Source: plan spend-removal, finalize (functional review round 1)

## Observation

- Deliverable 5 carried the success criterion "the pull request body lists the roadmap check-off and the token-usage 'remaining' statement under Owed to the milestone exit". The functional review runs at order 6, before the push and before `create-pr`, so no pull request existed and the criterion could only be graded `unevidenced`.
- An `unevidenced` criterion is blocking, and replaying the review cannot clear it: the loop-back target is `6-finalize` and the evidence appears only later in the same run. The run needed an operator override (`loop-back close`) with two filed findings to get past it, and the criterion was met once the pull request existed and the review re-ran after a later commit.
- The outline Q-Gate (both passes) did not flag the criterion, although it names an artifact that is created by a later finalize step.

## Proposed correction

- Make the outline or plan Q-Gate flag success criteria whose evidence is produced by a finalize step that runs after the functional review (the pull request body, the merge, the landing record), and move them to a post-`create-pr` check or reword them to what the plan can show before the push (for example, "the plan records the owed items for the pull request body").
- Alternatively let the functional review grade such a criterion `deferred_to_pr` with a recorded owner, instead of `unevidenced`.
