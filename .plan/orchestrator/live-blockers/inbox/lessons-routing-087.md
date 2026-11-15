envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T21:16:30Z

# HIGH (plan-marshall, operator-graded): the review-gate parser refuses a routine CodeRabbit section, and the landing review/Sonar counts disagree with the provider re-read

Filed by the `lessons-routing` drain of 2026-11-15. Source messages: `api-sheriff-security-hardening-tier-1-005` (revision 3, three landings) and `-006`. Bundle: `plan-marshall` (`runbook-lane` `review-gate`, `emit-landing`, `workflow-integration-sonar`). Severity: high. The operator graded `-005` high from a borderline medium/high.

## 1. `review-gate` returns `undecidable_read` on "Files with no reviewable changes" (source -006, API-Sheriff PR #607, executor 0.1.2106)

- `runbook_lane review-gate --pr-number 607` returns `merge_allowed: false`, `reason: undecidable_read`, `detail: "unreadable review-body section: '<picture>...</picture> Files with no reviewable changes: 2'"`.
- CodeRabbit emits that collapsible section whenever a push touches files it skips (formatter-only or generated files). The parser treats the unrecognised section as unreadable and refuses the whole read. The same path gates `merge_allowed`, so a plan relying on it pre-merge is blocked by a section that carries no finding.
- Every such landing then writes `review_body_findings_total=unknown`, so `inbox landing-check` reports `complete: false`.
- Sender's ask: treat "Files with no reviewable changes", "Files ignored due to path filters" and "Files selected for processing" as known non-finding sections; keep `undecidable_read` for genuinely unparseable bodies; add a fixture from a real review body.

## 2. Landing counts differ from the provider re-read (source -005, PLAN-SEC-02 / -04 / -05, PRs #590, #589, #600, executor 0.1.2090)

- `review_body_findings_total`: landing 2 / 4 / 4 against `review-gate` 13 / 6 / 7, all CodeRabbit `inline` rows embedded in review bodies. The plan's findings ledger files the same items as kind `inline` (all `fixed`); the emitter counts by the ledger kind and the parser counts by review-body section, so two producers classify one population differently.
- `sonar_open_new_issues`: landing 0 against `sonar_rest search --pr` returning 6 / 5 issues. For PR #589 the plan's own `sonar-scan-summary.jsonl` shows four analyses: the 5 issues belong to the first, and the last three report 0. On PLAN-SEC-05 the landing wrote `unknown` (`count_status: undecidable`, `head_revision_unavailable`), so `landing-check` reports `complete: false` for every merged PR once the PR branch is gone.
- Effect: `analyze.md` Step 4 tells the orchestrator to record a difference as a false claim, so a reader is told the plan misreported when it did not. The opposite failure is also possible: a real undisposed finding would look like the same artifact.
- Sender's ask: derive the landing's `review_body_findings_total` / `_handled` from the parser `review-gate` uses (or have `review-gate` read the plan's disposition ledger); give `analyze` a Sonar read that answers "open at the merged head" or names the analysis sha it read.

## Residual check requested

`live-blockers` PLAN-LB-129 (review-gate thread-and-count-truth: declared section count, last-bot-comment rule) is RUNNING and may already own part of item 1 and the count half of item 2; PLAN-LB-105 / -118 / -119 / -122 shipped nearby fixes. Please check whether each point still reproduces at the head the running plan lands, rather than opening new work.

## Evidence

Everything above is the senders' own measurement; nothing here was re-run on the plan-marshall side. Checked at the drain: the literal phrase "Files with no reviewable changes" occurs in no `marketplace/bundles` file (the inventory search returns only `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`, 3 matches, not read for what it asserts), which is consistent with, but does not establish, the parser not recognising it.
