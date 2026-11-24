envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:01Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: defer the criteria freeze until the outline's own open questions are answered
source_lesson=2026-11-18-07-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase-3-outline: defer the criteria freeze until the outline's own open questions are answered

# Candidate lesson: phase-3-outline froze the success criteria before the operator answered the outline questions

- Source signal: plan-retrospective, chat-history aspect (two `refreeze_requires_decision` returns from phase-3-outline, 2026-11-17)
- Resolution in run: operator approved a re-freeze twice; the second snapshot recorded 21 criteria

## What happened

The first phase-3-outline run wrote the outline, returned three `outline_prompt` questions with recommended answers filled in, and froze `work/criteria-snapshot.json` in the same run. The operator chose non-recommended answers for two of them (qualifier annotations for the fixtures, aligning the "with history" wording). Applying them changed the criteria, and `snapshot-criteria` refused to re-freeze without `criteria-refreeze-authorize`, so the leaf returned `status: error` and needed an operator prompt. The Q-Gate finding 9fe2d8 then added two more documents and the same re-freeze prompt came back a second time. 3-outline took three dispatches and two extra operator prompts that carried no new decision.

## Candidate rule

When phase-3-outline returns open `outline_prompt` questions, it should defer the criteria freeze until those answers are applied, or treat an answer to its own outline questions as authorizing the re-freeze. The re-freeze gate is meant to catch criteria drift after approval, and an outline that is still waiting for its own questions has not been approved yet.



## Recurrence in a later plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-011)

- Source signal: plan-retrospective (chat-history, plan-efficiency, log-analysis), work log ERROR 2026-11-18T20:27:47Z, confidence high.
- The first phase-3-outline dispatch wrote the outline, froze 16 success criteria, transitioned to 4-plan and only then returned four operator questions. The operator overrode two recommendations (a new public `releaseBranchReservation` operation, `WORKTREE_NOT_FOUND` instead of `IDENTITY_MISMATCH`); the revised 6-deliverable outline was then refused by `snapshot-criteria` with `refreeze_requires_decision`, which cost a fourth operator question and a third outline dispatch just to re-freeze and transition.
- Evidence: 3-outline was dispatched 3 times and used 731,687 tokens (24% of the plan), the second-largest phase.

Same root cause and same rule: do not freeze criteria or leave 3-outline while `outline_prompt.questions` is non-empty, or treat the operator's answers to the outline's own questions as the re-freeze authorization for the revision they cause.


## Recurrence in a later plan (plan-11-store-anchoring-signed, inbox plan-11-store-anchoring-signed-004)

Q-Gate finding d052b2 (phase 3-outline): the outline's Risks section had settled that `AnchorProvider.obtain` gains the subject's commit time as a parameter, but deliverable 1's per-file change still read "if the open question resolves that way". Tasks cannot be planned against two readings. The implementation chose the parameter. Rule restated: once the outline settles an open question anywhere (Risks included), write the decision into every affected deliverable's change description and remove the conditional phrasing before the Q-Gate.
