envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:13Z

component=plan-marshall:execute-task
category=bug

# Two numbered lists in one document made "step 5" name two different actions

Source: Q-Gate finding 484462 (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class ordinal_reference_stale — 1 finding in this class this round.

execute-task/SKILL.md's status table uses bare ordinals — "Read passed - step 4 or step
5" at line 313, "Step 6 - re-supply the right log" at 314 — naming the INNER numbered
list whose items sit at 318, 319 and 327. The same sub-step block uses identical step-N
notation for the OUTER workflow list at 299 and 301, disambiguated there only by a
parenthetical gloss. The inner references carry no gloss, and the outer list has its own
steps 4, 5 and 6.

The readings diverge on the FAILURE path: outer step 5 is Run Verification, while inner
item 5 is "do NOT mark done, mark requires_attention". An agent taking the outer reading
re-runs verification instead of flagging the silent skip this sub-step exists to catch.

## Solution

Rephrase ordinal references to CONTENT anchors so a future renumber cannot re-strand
them. A bare ordinal is only unambiguous while exactly one numbered list is in scope; a
gloss on some references and not others is worse than none, because it signals that the
unglossed ones need no disambiguation.

## Impact

The ambiguity resolves the wrong way precisely on the path the instruction exists to
govern.
