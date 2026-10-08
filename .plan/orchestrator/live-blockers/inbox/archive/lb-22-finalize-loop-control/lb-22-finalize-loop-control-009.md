envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:07Z

component=plan-marshall:automatic-review
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Trigger every stale bot in the re-review procedure, not only the first

## Context

After a fix commit, both required review bots (coderabbit, cuioss-review-bot) held reviews of the previous head. The numbered procedure for the re-review trigger in `automatic-review/SKILL.md` posts a trigger for the one bot the `trigger-bot` selector returns. On the first pass at head `57c5c8be3` that was coderabbit. cuioss-review-bot was never triggered, stayed `participated_stale` at the first participation check, and the document then prescribes `loop_back` for the pass.

The leaf improvised a second trigger for the stale bot, which re-reviewed within 101 s, but the pass had already been judged and the step recorded `loop_back` with nothing wrong. That spent one of the step's loop-back rounds and one full extra automatic-review pass. On the next fix commit a different leaf ran the selector twice before the participation check, and the step settled in one pass - by departing from the numbered procedure.

## Root cause

The section's introduction says a trigger is posted for each participating bot, and that an explicit trigger is cuioss-review-bot's only path to a re-review. The numbered steps beneath it trigger one bot. A leaf following the steps as written produces a stale required bot every time two bots are stale. The `participated_stale` branch also names the re-review trigger as its remedy without a command block.

## Proposed action

- Make the numbered procedure loop: call the selector until it returns no further stale bot, trigger and await each, then run the wait, the fetch and the participation check.
- Give the `participated_stale` branch its own command block, and let a stale bot that re-reviews inside the same pass be re-checked before the pass is judged, so the pass can end `done`.

## Evidence

- aspect: log_analysis - work-log entry at 2026-10-08T18:45:30Z: "participated_stale remediation: re-review matched for bot_kind=cuioss-review-bot at head_sha=57c5c8be3... (head_sha_verified=true) - re-entered FIND, recording loop_back for this pass", followed by "Loop-back iteration 1/5 for plan-marshall:automatic-review".
- aspect: chat_history_analysis - the third automatic-review hand-back: "Had I followed the numbered procedure alone, cuioss-review-bot would presumably have been participated_stale at the check and the document would prescribe loop_back".
- status record: `automatic-review` prior firings `done, loop_back, done`; `loop_back_budgets.plan-marshall:automatic-review.spent: 1`.
