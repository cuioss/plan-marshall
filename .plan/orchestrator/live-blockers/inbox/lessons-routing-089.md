envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T21:16:30Z

# HIGH (plan-marshall, operator-graded): the review-gate parser refuses a routine CodeRabbit section, and the landing review-body counts disagree with the provider re-read

Filed by the `lessons-routing` drain of 2026-11-15 (second grading of messages the Linux session's 38-message drain of the same day also read). Source messages: `api-sheriff-security-hardening-tier-1-005` (revision 3, three landings) and `-006` (arrived after that drain, so only graded here). Bundle: `plan-marshall` (`runbook-lane` `review-gate`, `emit-landing`). Severity: high. The operator graded `-005` high from a borderline medium/high; the Linux session's operator ruling filed it medium and unfiled (its Sonar half ignored because Sonar is not enabled for this project). This filing therefore carries NO Sonar claim.

## 1. `review-gate` returns `undecidable_read` on "Files with no reviewable changes" (source -006, API-Sheriff PR #607, executor 0.1.2106)

- `runbook_lane review-gate --pr-number 607` returns `merge_allowed: false`, `reason: undecidable_read`, `detail: "unreadable review-body section: '<picture>...</picture> Files with no reviewable changes: 2'"`.
- CodeRabbit emits that collapsible section whenever a push touches files it skips (formatter-only or generated files). The parser treats the unrecognised section as unreadable and refuses the whole read. The same path gates `merge_allowed`, so a plan relying on it pre-merge is blocked by a section that carries no finding.
- Every such landing then writes `review_body_findings_total=unknown`, so `inbox landing-check` reports `complete: false`.
- Sender's ask: treat "Files with no reviewable changes", "Files ignored due to path filters" and "Files selected for processing" as known non-finding sections; keep `undecidable_read` for genuinely unparseable bodies; add a fixture from a real review body.

## 2. Landing review-body counts differ from the provider re-read (source -005, PLAN-SEC-02 / -04 / -05, PRs #590, #589, #600, executor 0.1.2090)

- `review_body_findings_total`: landing 2 / 4 / 4 against `review-gate` 13 / 6 / 7, all CodeRabbit `inline` rows embedded in review bodies. The plan's findings ledger files the same items as kind `inline` (all `fixed`); the emitter counts by the ledger kind and the parser counts by review-body section, so two producers classify one population differently.
- Effect: `analyze.md` Step 4 tells the orchestrator to record a difference as a false claim, so a reader is told the plan misreported when it did not. The opposite failure is also possible: a real undisposed finding would look like the same artifact.
- Sender's ask: derive the landing's `review_body_findings_total` / `_handled` from the parser `review-gate` uses (or have `review-gate` read the plan's disposition ledger).
- Not re-checked: `#1992` (review-gate contract and single read) landed after the sender's observations; whether it already makes the two producers agree was not verified.

## Residual check requested

`live-blockers` PLAN-LB-129 (review-gate thread-and-count-truth: declared section count, last-bot-comment rule) is RUNNING and may already own part of item 1 and the count half of item 2; PLAN-LB-105 / -118 / -119 / -122 shipped nearby fixes. Please check whether each point still reproduces at the head the running plan lands, rather than opening new work.

## Evidence

Everything above is the senders' own measurement; nothing here was re-run on the plan-marshall side. Checked at the drain: the literal phrase "Files with no reviewable changes" occurs in no `marketplace/bundles` file (the inventory search returns only `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`, 3 matches, not read for what it asserts), which is consistent with, but does not establish, the parser not recognising it.
