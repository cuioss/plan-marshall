envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:33:26Z

# Lessons ingest: Sourcery review-budget refusal is still not a registered refusal pattern

Severity: high (refusal misclassification corrupts completion/wait; recurrence across three PRs). Bundle: `plan-marshall` (`automatic-review` refusal registry, `workflow-integration-github`, review wait logic).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-203`..`-286`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-204` | Sourcery review-budget refusal filed as a pending finding instead of a refusal (PR #50); forced manual triage. |
| `pm-mcp-core-m2-m4-218` | Same quota notice surfaced as pending a second time (exact duplicate of 204). |
| `pm-mcp-core-m2-m4-231` | Budget-exhausted notice misread as pending/clean instead of refusal (PR #54). |
| `pm-mcp-core-m2-m4-235` | Same budget wording misclassified as decline and misfiled (duplicate of 231 on PR #54). |
| `pm-mcp-core-m2-m4-245` | 7-day review-budget notice not recognised; wait logic misled. |
| `pm-mcp-core-m2-m4-254` | Same budget refusal misfiled as comment; bot reported not-refused (duplicate of 245). |

Asked for: register the Sourcery budget-exhausted wordings (including the 7-day and pronoun variants) as refusal patterns, so budget notices route to refusal handling instead of pending findings.

Owner today: none. Not re-checked at HEAD by the ingest.
