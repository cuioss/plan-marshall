envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-01T20:42:29Z

# Pre-merge HEAD binding voids every gate on a late commit; a waiver the step record accepted is refused at merge

Severity: **high (operator ruling, 2026-11-01 sweep)**. Bundle: `plan-marshall` (`phase-6-finalize`). Recurrence of the subject of PLAN-LB-55 and PLAN-LB-101 (both shipped).
Source: 1 lesson from the TokenSheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/TokenSheriff/2026-10-31-13-002.md`. **Not re-verified at HEAD, and the plugin version the consumer ran is unknown** — it may predate the LB-55/LB-101 merges, so this asks for a residual check, not new work.

## Observed (TokenSheriff, PLAN-01, PLAN-02, PLAN-06; 2026-10-30/31)

`merge_candidate_not_gated` is returned whenever HEAD moved after the head-dependent gates ran.

- PLAN-01: a formatting rewrite and a docs-only ADR commit landed late; six gates re-ran.
- PLAN-02: `finalize-step-sync-baseline` stamped an old `head_at_completion`, was skipped on re-entry as not head-dependent, but the gate derives head-dependence from that stamp; a forced rebase voided every verdict.
- PLAN-06: a test-only commit after the gated head. The operator's earlier re-run waivers were accepted by the step records but refused at merge, so the security audit and functional review re-ran about three hours later.
- PLAN-01: the grant verb refused the paraphrased answer "Accept gap and merge"; it accepts only the barrier's own label "Merge anyway (record reason)".

## Ask

Check at HEAD whether (a) the skip rule and the gate's head-dependence derive from one source, (b) a waiver accepted by a step record is also accepted by the merge gate, and (c) the operator prompt is built from the labels the barrier returns.
