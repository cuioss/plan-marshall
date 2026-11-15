envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=finding
created=2026-11-13T11:53:29Z

# review-gate refuses a CodeRabbit review body carrying a "Files with no reviewable changes" section, so landings report the review-body counts as unknown

Source: API-Sheriff epic `security-hardening-tier-1`, inbox message `plan-sec-06-tier-2-quick-wins-001.md` (plan `plan-sec-06-tier-2-quick-wins`, PR cuioss/API-Sheriff#607, plugin/executor 0.1.2106), drained 2026-11-13.

## Observation

- The landing's `landing-facts` block carried `review_body_findings_total=unknown` and `review_body_findings_handled=unknown`, so `inbox landing-check` reported `complete: false` on those two keys (plus `effort=unknown`).
- Re-running the producer on the merged PR reproduces the cause: `runbook_lane review-gate --pr-number 607` returns `merge_allowed: false`, `reason: undecidable_read`, with `detail: "unreadable review-body section: '<picture>…</picture> Files with no reviewable changes: 2'"`.
- The PR's three CodeRabbit review bodies are ordinary "Actionable comments posted" reviews; one of them carries the collapsible "Files with no reviewable changes" section CodeRabbit emits when a push touches files it skips (here, formatter-only or generated files). The parser treats the unrecognised section as unreadable and the whole read as undecidable.
- `ci pr comments --unresolved-only` shows zero rows with a non-empty `thread_id`, so the merge-gate state itself was clean; only the count read failed.

## Why it matters

A section CodeRabbit routinely emits makes the one parser that produces `unresolved_review_threads` / `review_body_findings_total` refuse the read. The lane then honestly writes `unknown`, every such landing drains as `complete: false`, and the orchestrator cannot re-verify the review-body count at all. The same parser path also gates `merge_allowed`, so a plan relying on it pre-merge would be blocked by a section that contains no finding.

## Suggested correction

Recognise CodeRabbit's "Files with no reviewable changes" (and the sibling "Files ignored due to path filters" / "Files selected for processing") sections as known non-finding sections and skip them, keeping `undecidable_read` for genuinely unparseable bodies. Add a fixture taken from a real review body carrying the section.

Related: `api-sheriff-security-hardening-tier-1-005` (the same two counts disagreeing with the provider re-read on PLAN-SEC-02/-04/-05). Here the count is not wrong but absent.
