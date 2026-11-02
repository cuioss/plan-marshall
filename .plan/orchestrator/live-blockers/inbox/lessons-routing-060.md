envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-01T20:42:29Z
revision=1
amended=2026-11-02T10:27:02Z

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

## Added 2026-11-02 sweep — item (b) recurs after LB-55/LB-101, and the code says it is still open

- **Recurrence (API-Sheriff, 2026-10-30):** `api-sheriff-api-sheriff-0-2-0-078` (plan-v02-48-adr-corpus-cleanup-part-2): `loop-back close --step code-review --waive-refire functional-review --waive-refire finalize-step-simplify` recorded a `refire_waiver` with head and basis on both steps; `pre_merge_gate merge` then refused with `merge_candidate_not_gated` naming exactly those two steps, after CI, bots and Sonar had finished. Also `lessons-routing-009` (same refusal) and `lessons-routing-001` (PR cuioss/API-Sheriff#527: operator narrowed the re-fire set, the push went through, then branch-cleanup refused; a full functional-review round plus simplify and security-audit re-ran about an hour after the override). Bodies verbatim in `lessons-routing/inbox/archive/`.
- **Ground truth (c431a8193):** `architecture search --content --pattern refire_waiver` finds the field only in `manage-status` (`_cmd_loop_back.py`, `_cmd_mark_step.py`, `manage-status.py`, SKILL.md) and `phase-6-finalize/SKILL.md` — **no `pre_merge_gate` source reads it**. Found by content search, not by running the gate.
- Either the gate honours a waiver bound to the candidate head, or `loop-back close` refuses the waiver up front and says the merge gate will not accept it.
