envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:30Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-10-09

# Sweep the whole diff for sibling sites before fixing a reviewer defect class

## Context

On PR #1724 of plan `plan-lb-29-harness-sync` CodeRabbit found one defect class, acting through symbolic links, at four sites over two review passes:

1. the emit output directory (finding 6f5e93), fixed in round 6;
2. the source walk (finding c6930c), fixed in round 6, widened to the Claude emitter at the operator's direction;
3. the install sync and the Claude cache sync (finding 7b7c8c), fixed in round 7;
4. the repin script (symlinked registry file, symlinked cache directories), found by the round-7 implementers themselves while fixing site 3.

Both rounds were past the limit of five and each needed an operator decision. Each fix report had named the next unfixed sibling: the round-6 implementer listed remaining exposure in other functions, and the round-7 implementer reported the repin script's behaviour "report only, not edited" before a further dispatch fixed it.

## Root cause

The triage step turns each reviewer comment into a fix task scoped to the commented file. Nothing asks, once a comment is confirmed as a real defect, which other sites in the same change have the same shape. The project's own rule that a correction names a family, and that every sibling is closed and reported, is applied to operator nudges but not to confirmed reviewer findings.

## Proposed action

In the verification-feedback (triage) workflow, when a finding is confirmed as a real code defect:

- name the defect class in one line;
- sweep the plan's whole changed-file set for sites of that class before creating the fix task, and list every site in the task with a per-site disposition (fix, or exempt with a reason);
- have the fix report state the swept population and the outcome per site.

One round then closes the class instead of one site.

## Evidence

- aspect: chat_history_analysis — triage report for round 6 (two fix tasks, each scoped to the commented files); triage report for round 7 naming five sibling sites in `sync.py` and `cache_sync.py`; implementer reports naming the repin script's link handling as unfixed.
- aspect: request_result_alignment — 7 of the 26 undeclared modified files come from these two rounds.
- decision log — two WARNING entries recording the loop-back limit (5) overridden by the operator for iterations 6 and 7.
