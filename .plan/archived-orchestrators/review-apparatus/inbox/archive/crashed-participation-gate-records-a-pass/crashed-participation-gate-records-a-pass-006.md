envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:44Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# Trigger-B contradicts itself and can make the REQUIRED bot structurally untriggerable

Inside the automatic-review Trigger-B path, the prose and the numbered steps disagree:

- The **prose** says: trigger each bot in `required` UNION `optional`.
- **Numbered step 3** triggers only the **single bot from the most recent finding**.

When that most-recent-finding bot is an **optional** bot, the required bot is never triggered at all. It is not merely skipped on this pass — it is structurally untriggerable on this path, so the loop-back that waits on the required bot's participation **can never clear**.

Same-document normative contradiction: two directives in one file that cannot both be followed, with no precedence rule stated. This was found on plan `crashed-participation-gate-records-a-pass` and deliberately left unfixed (PLAN-PR-008 territory).

## Solution

Pick one directive and delete the other — do not "clarify" both into coexistence:

- If the union semantics are correct, rewrite step 3 to iterate `required` UNION `optional` and drop the most-recent-finding narrowing.
- If the narrowing is correct, the prose must state that Trigger-B is a per-finding retrigger and that required-bot coverage is guaranteed elsewhere — and that elsewhere must actually exist.

Add a test that drives the exact live shape: most recent finding belongs to an optional bot, a required bot has not participated. The required bot must be triggered.

## Impact

Any run whose latest review finding comes from an optional bot. The visible symptom is a loop-back that never clears — or, worse, an operator force-completing it, which is precisely the escape hatch PR #1070 withdrew from the UNKNOWN verdict.

The general rule: when a document's prose and its numbered steps describe different populations, the numbered steps are what executes and the prose is what reviewers believe. A same-document contradiction is a live defect, not a documentation nit.
