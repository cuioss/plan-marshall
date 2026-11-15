envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=finding
created=2026-11-10T07:29:57Z
revision=1
amended=2026-11-10T12:54:54Z

# Landing facts report review-body and Sonar counts that the provider re-read does not reproduce

Source: API-Sheriff epic `security-hardening-tier-1`, inbox message `sec-02-upstream-attribution-forward-headers-002.md` (plan `sec-02-upstream-attribution-forward-headers`, PR cuioss/API-Sheriff#590, plugin/executor 0.1.2090), drained 2026-11-10.

## Observation

The `analyze` verb re-reads the landing's review and Sonar numbers from the provider, as `analyze.md` Step 4 requires. Two of them did not match:

- `review_body_findings_total`: landing `2`; `runbook_lane review-gate --pr-number 590` on the merged head reports `13`, all `coderabbit` section `inline` (ids `inline-1` .. `inline-13`), with `review_body_findings_handled: 0` and `merge_allowed: false, reason: body_findings_undisposed`. The plan's findings ledger (`pr-comment.jsonl`) files those same 13 items as kind `inline`, all resolved `fixed`, and only 2 as `review_body`. The emitter counts by the ledger's kind; the review-gate parser counts CodeRabbit's inline items embedded in review bodies as body findings. The two producers classify the same items differently.
- `sonar_open_new_issues`: landing `0`; `sonar_rest search --project cuioss_API-Sheriff --pr 590` after the merge returns 6 issues. All six are addressed in the merged code (3 fixed, 3 suppressed in code with rationale) and the PR gate is `OK`. The search most likely reflects the last PR analysis before the fix push. The landing's `0` came from the plan's own disposition ledger, not from a provider read at the merged head.

## Why it matters

`analyze.md` tells the orchestrator to record any difference as a **false claim**. Here both differences are classification or staleness artifacts, not untrue landings, so a reader of the landing report is told the plan misreported when it did not. The opposite failure is also possible: a real undisposed finding would look like the same artifact.

## Suggested correction

- Make `emit-landing` derive `review_body_findings_total` / `_handled` from the same parser `review-gate` uses (or have `review-gate` read the plan's disposition ledger), so the two producers count the same population.
- Give `analyze` a Sonar re-read that answers "open at the merged head" (or reports the analysis sha it read), so a stale PR analysis is distinguishable from an open issue.

## Recurrence — PLAN-SEC-04 (PR cuioss/API-Sheriff#589, drained 2026-11-10)

Same two differences on the next landing of the same epic (plugin/executor 0.1.2090):

- `review_body_findings_total`: landing `4`; `runbook_lane review-gate --pr-number 589` reports `6`, all `coderabbit` section `inline` (`inline-1` .. `inline-6`), `review_body_findings_handled: 0`, `merge_allowed: false, reason: body_findings_undisposed`. The plan's `pr-comment.jsonl` files those 6 as kind `inline`, all `fixed`, and 4 as `review_body` (2 fixed, 2 taken_into_account) — the landing's `4`.
- `sonar_open_new_issues`: landing `0`; `sonar_rest search --project cuioss_API-Sheriff --pr 589` returns 5 issues. New evidence for the staleness reading: the plan's own `artifacts/findings/sonar-scan-summary.jsonl` records four PR analyses, and the 5 issues belong to the FIRST (`analysis_revision` 533886a7, `new_code_issue_count: 5`); the three later analyses, the last at the final head 728062ea, all report `new_code_issue_count: 0`. All five are fixed in the merged code. So `search --pr` returned issues the latest analysis no longer reports — the "open at the merged head" read the suggested correction asks for is exactly what is missing.
