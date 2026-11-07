envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:37:00Z

# CodeRabbit declined a head that was only rebased, and the step then forced a "merge anyway" operator choice

- component: plan-marshall:automatic-review
- category: improvement
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

After a rebase that changed no reviewed code, the trigger-A re-review of branch-cleanup got "Already reviewed the last commit" from CodeRabbit (condition no_unreviewed_commit). Trigger A treated the reply as a decline (head_sha_verified false) and offered the operator only timeout dispositions, one of which is "Merge anyway - proceed unreviewed". The refusal-recovery branch of automatic-review already knows this reply is not a limit and accepts the review on record, but trigger A does not use it, so the operator was asked to waive a review that the bot had actually answered.

Evidence: the trigger-A decision-log lines of the plan (re-review declined, rereview-timeout-override granted) and the later recovery-action result accept_review_on_record for the same head.
