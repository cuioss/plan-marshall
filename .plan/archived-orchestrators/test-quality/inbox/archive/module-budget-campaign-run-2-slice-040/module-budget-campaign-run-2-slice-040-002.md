envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-run-2-slice-040
epic=test-quality
kind=candidate-lesson
created=2026-09-18T11:23:41Z

# Candidate lesson — remediated review-bot findings in-run

Source plan: module-budget-campaign-run-2-slice-040 (epic test-quality).

Observation: 3 actionable review-bot findings were fixed in-run (2 coderabbitai
inline, 1 cuioss-review-bot inline at 50% resolved-as-fixed); 18 acknowledged
without change (accepted/taken_into_account) at the loop-back ceiling with no
mis-triage (0 rejected). The slipped-then-caught class is the review signal
worth keeping: cuioss-review-bot's stale-suggestion detection (already-fixed-in
merged commit) had the highest per-comment value.

Candidate rule: keep the inline-bot signal as the merge-gate complement; bank
deferred hardening suggestions as future work, not plan defects.

Signal provenance: pr-comment store (23 findings, 3 measured reviewers),
review-retrospective artifact.
