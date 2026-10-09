envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:29Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-09

# File seen-but-unsurfaced defects from self-review instead of dropping them

## Context

The pre-submission self-review of plan `plan-lb-29-harness-sync` ran six rounds and filed 29 findings, nearly all of them over-wide prose claims. In round 6 the code reviewer also wrote, under "Seen, not fileable": `sync.py:427-428 and 460 — a destination symlink-to-file survives _remove_absent_from_source and shutil.copy2 then writes through it`. It was not filed, because the workflow only admits findings on the candidates the surfacer lists. Earlier rounds listed similar real gaps the same way (a single-target run ending in a traceback, a sentinel that is not a JSON object).

After the pull request opened, CodeRabbit filed exactly that symlink write-through as a Major finding (7b7c8c). Fixing it took a seventh, operator-authorised round past the limit of five, and the re-review was held up for about three and a half hours by the bot's hourly quota.

## Root cause

The surface-only rule treats a real defect a reviewer has already found as out of reach when it does not sit on a surfaced candidate. The reviewer's observation is then only prose in a return report, which nothing downstream reads. The rule protects the round from scope growth but throws away detection that was already paid for.

## Proposed action

- Give the self-review a second output list for defects seen outside the surfaced candidates, and have the dispatcher file each entry as a finding of its own type so it reaches triage and the operator. It need not count toward the round's convergence verdict.
- State in the workflow that a code defect with a concrete file, line and failure mode is never left only in the return text.
- Consider letting the convergence check close a round whose remaining findings are all of the prose-claim class once the same class has been swept twice, so the round budget is not spent on wording while code defects wait.

## Evidence

- aspect: chat_history_analysis — round 6 code-half report, "Seen, not fileable" item 7; CodeRabbit finding 7b7c8c on `marketplace/targets/sync.py:459`; operator decision admitting round 7 of 5.
- aspect: plan_efficiency — six self-review rounds spent 3,220,593 tokens in author and verifier dispatches; no round could close (each returned findings and left about 214 schema-bearing files unread).
- status record — `pre-submission-self-review`: 7 firings, 6 loop-backs, "closed by operator at round limit; last 7 fixes not re-reviewed".
